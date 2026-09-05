from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from src.models import BookCandidate, EvidenceRecord

LOGGER = logging.getLogger(__name__)
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"


def _isbn(identifiers: list[dict[str, str]], kind: str) -> str | None:
    for item in identifiers:
        if item.get("type") == kind:
            return item.get("identifier")
    return None


def normalize_google_volume(item: dict[str, Any], role: str | None = None) -> BookCandidate:
    info = item.get("volumeInfo") or {}
    title = str(info.get("title") or "").strip()
    authors = [str(value).strip() for value in info.get("authors") or [] if str(value).strip()]
    identifiers = info.get("industryIdentifiers") or []
    isbn_10 = _isbn(identifiers, "ISBN_10")
    isbn_13 = _isbn(identifiers, "ISBN_13")
    published = str(info.get("publishedDate") or "")
    published_year = int(published[:4]) if published[:4].isdigit() else None
    volume_id = str(item.get("id") or "")
    image_links = info.get("imageLinks") or {}
    cover_url = next(
        (
            str(image_links[key]).replace("http://", "https://", 1)
            for key in ("extraLarge", "large", "medium", "small", "thumbnail", "smallThumbnail")
            if image_links.get(key)
        ),
        None,
    )
    verified = ["title"]
    for name, value in {
        "authors": authors,
        "isbn_10": isbn_10,
        "isbn_13": isbn_13,
        "published_year": published_year,
        "description": info.get("description"),
        "page_count": info.get("pageCount"),
        "average_rating": info.get("averageRating"),
        "ratings_count": info.get("ratingsCount"),
    }.items():
        if value not in (None, [], ""):
            verified.append(name)
    return BookCandidate(
        canonical_id=isbn_13 or isbn_10 or f"google:{volume_id}",
        title=title,
        authors=authors,
        isbn_10=isbn_10,
        isbn_13=isbn_13,
        published_year=published_year,
        description=info.get("description"),
        language=info.get("language"),
        page_count=info.get("pageCount"),
        categories=[str(value) for value in info.get("categories") or []],
        average_rating=info.get("averageRating"),
        ratings_count=info.get("ratingsCount"),
        cover_url=cover_url,
        source_records=[
            EvidenceRecord(
                source_name="Google Books",
                source_url=f"https://books.google.com/books?id={volume_id}" if volume_id else None,
                source_book_id=volume_id or None,
                retrieved_at=datetime.now(UTC),
                fields_verified=verified,
            )
        ],
        verification_status="verified_single_source",
        search_roles=[role] if role else [],
    )


class GoogleBooksClient:
    def __init__(
        self,
        api_key: str = "",
        timeout: float = 10,
        max_retries: int = 2,
        client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key
        self._owns_client = client is None
        self.client = client or httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            transport=httpx.HTTPTransport(retries=max_retries),
        )

    def search(
        self,
        query: str,
        max_results: int = 6,
        role: str | None = None,
        language: str | None = None,
    ) -> list[BookCandidate]:
        params: dict[str, str | int] = {
            "q": query,
            "maxResults": min(max_results, 10),
            "printType": "books",
            "projection": "full",
        }
        if language:
            params["langRestrict"] = language
        if self.api_key:
            params["key"] = self.api_key
        LOGGER.info("google_books.search query=%r limit=%s", query, max_results)
        response = self.client.get(GOOGLE_BOOKS_URL, params=params)
        response.raise_for_status()
        candidates: list[BookCandidate] = []
        for item in response.json().get("items") or []:
            try:
                candidates.append(normalize_google_volume(item, role=role))
            except ValueError as exc:
                LOGGER.warning("Skipping invalid Google Books item: %s", exc)
        return candidates

    def close(self) -> None:
        if self._owns_client:
            self.client.close()
