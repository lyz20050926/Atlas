from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from src.models import BookCandidate, EvidenceRecord

LOGGER = logging.getLogger(__name__)
OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"


def _pick_isbn(values: list[str], length: int) -> str | None:
    for value in values:
        cleaned = str(value).replace("-", "").strip()
        if len(cleaned) == length:
            return cleaned
    return None


def normalize_open_library_doc(doc: dict[str, Any], role: str | None = None) -> BookCandidate:
    title = str(doc.get("title") or "").strip()
    authors = [str(value).strip() for value in doc.get("author_name") or [] if str(value).strip()]
    isbns = [str(value) for value in doc.get("isbn") or []]
    isbn_10 = _pick_isbn(isbns, 10)
    isbn_13 = _pick_isbn(isbns, 13)
    work_key = str(doc.get("key") or "")
    cover_id = doc.get("cover_i")
    cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None
    verified = ["title"]
    for name, value in {
        "authors": authors,
        "isbn_10": isbn_10,
        "isbn_13": isbn_13,
        "language": doc.get("language"),
        "categories": doc.get("subject"),
        "average_rating": doc.get("ratings_average"),
        "ratings_count": doc.get("ratings_count"),
    }.items():
        if value not in (None, [], ""):
            verified.append(name)
    return BookCandidate(
        canonical_id=isbn_13 or isbn_10 or f"openlibrary:{work_key}",
        title=title,
        authors=authors,
        isbn_10=isbn_10,
        isbn_13=isbn_13,
        # Open Library search documents describe a work and expose the first
        # publication year plus a list of ISBNs across editions. Treating that
        # work-level year as the year of one arbitrarily selected ISBN creates
        # false edition conflicts, so edition year/pages are left to an
        # edition-level source such as Google Books.
        published_year=None,
        description=None,
        language=(doc.get("language") or [None])[0],
        page_count=None,
        categories=[str(value) for value in (doc.get("subject") or [])[:12]],
        average_rating=doc.get("ratings_average"),
        ratings_count=doc.get("ratings_count"),
        cover_url=cover_url,
        source_records=[
            EvidenceRecord(
                source_name="Open Library",
                source_url=f"https://openlibrary.org{work_key}" if work_key else None,
                source_book_id=work_key or None,
                retrieved_at=datetime.now(UTC),
                fields_verified=verified,
            )
        ],
        verification_status="verified_single_source",
        search_roles=[role] if role else [],
    )


class OpenLibraryClient:
    def __init__(
        self,
        timeout: float = 10,
        max_retries: int = 2,
        client: httpx.Client | None = None,
    ) -> None:
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
        language_code = {"zh": "chi", "en": "eng"}.get(language or "")
        strict_query = f"{query} language:{language_code}" if language_code else query
        params = {
            "q": strict_query,
            "limit": min(max_results, 10),
            "fields": (
                "key,title,author_name,isbn,first_publish_year,language,subject,"
                "ratings_average,ratings_count,number_of_pages_median,cover_i"
            ),
        }
        if language:
            params["lang"] = language
        LOGGER.info("open_library.search query=%r limit=%s", query, max_results)
        response = self.client.get(OPEN_LIBRARY_SEARCH_URL, params=params)
        response.raise_for_status()
        candidates: list[BookCandidate] = []
        for doc in response.json().get("docs") or []:
            try:
                candidates.append(normalize_open_library_doc(doc, role=role))
            except ValueError as exc:
                LOGGER.warning("Skipping invalid Open Library item: %s", exc)
        return candidates

    def close(self) -> None:
        if self._owns_client:
            self.client.close()
