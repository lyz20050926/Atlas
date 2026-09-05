from __future__ import annotations

import json
from pathlib import Path

from src.services.book_matching import identity_matches, merge_candidates, normalize_text
from src.tools.google_books import normalize_google_volume
from src.tools.open_library import normalize_open_library_doc

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"


def test_google_books_normalization_preserves_provenance() -> None:
    payload = json.loads((FIXTURES / "google_books_response.json").read_text(encoding="utf-8"))
    payload["items"][0]["volumeInfo"]["imageLinks"] = {
        "thumbnail": "http://books.google.com/cover.jpg"
    }
    book = normalize_google_volume(payload["items"][0], "Technical/Application")
    assert book.isbn_13 == "9781234567897"
    assert book.authors == ["Ada Example"]
    assert book.ratings_count == 50
    assert str(book.cover_url) == "https://books.google.com/cover.jpg"
    assert book.source_records[0].source_name == "Google Books"


def test_open_library_normalization_and_isbn_extraction() -> None:
    payload = json.loads((FIXTURES / "book_api_responses.json").read_text(encoding="utf-8"))
    doc = payload["open_library"]["Critical/Cross-disciplinary"]["docs"][0]
    doc["cover_i"] = 12345
    book = normalize_open_library_doc(doc, "Critical/Cross-disciplinary")
    assert book.title == "Robot Ethics"
    assert book.isbn_10 == "0262016664"
    assert book.isbn_13 == "9780262016667"
    assert book.average_rating is None
    assert book.published_year is None
    assert book.page_count is None
    assert str(book.cover_url) == "https://covers.openlibrary.org/b/id/12345-L.jpg"


def test_identity_merge_uses_isbn_and_keeps_sources() -> None:
    google = normalize_google_volume(
        {
            "id": "g1",
            "volumeInfo": {
                "title": "Robot Ethics",
                "authors": ["Patrick Lin"],
                "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9780262016667"}],
                "imageLinks": {"thumbnail": "https://books.google.com/robot-ethics.jpg"},
            },
        },
        "Critical/Cross-disciplinary",
    )
    open_library = normalize_open_library_doc(
        {
            "key": "/works/test",
            "title": "Robot Ethics",
            "author_name": ["Patrick Lin"],
            "isbn": ["9780262016667"],
        },
        "Critical/Cross-disciplinary",
    )
    assert identity_matches(google, open_library)
    merged = merge_candidates([google, open_library])
    assert len(merged) == 1
    assert merged[0].verification_status == "verified_two_sources"
    assert str(merged[0].cover_url) == "https://books.google.com/robot-ethics.jpg"
    assert {record.source_name for record in merged[0].source_records} == {
        "Google Books",
        "Open Library",
    }


def test_normalize_text_is_stable() -> None:
    assert normalize_text("Robot Ethics: 2.0") == "robot ethics 2 0"


def test_same_title_with_disjoint_isbns_stays_as_separate_editions() -> None:
    first = normalize_google_volume(
        {
            "id": "edition-1",
            "volumeInfo": {
                "title": "The Routledge Handbook of Embodied Cognition",
                "authors": ["Lawrence Shapiro"],
                "publishedDate": "2014",
                "industryIdentifiers": [
                    {"type": "ISBN_13", "identifier": "9780415623612"}
                ],
            },
        }
    )
    second = normalize_google_volume(
        {
            "id": "edition-2",
            "volumeInfo": {
                "title": "The Routledge Handbook of Embodied Cognition",
                "authors": ["Lawrence Shapiro"],
                "publishedDate": "2024",
                "industryIdentifiers": [
                    {"type": "ISBN_13", "identifier": "9781032859347"}
                ],
            },
        }
    )

    assert not identity_matches(first, second)
    assert len(merge_candidates([first, second])) == 2
