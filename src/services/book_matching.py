from __future__ import annotations

import re
import unicodedata
from copy import deepcopy

from src.models import BookCandidate


def normalize_text(value: str) -> str:
    value = "".join(
        character
        for character in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(character)
    ).casefold()
    return re.sub(r"[^\w]+", " ", value, flags=re.UNICODE).strip()


def identity_matches(left: BookCandidate, right: BookCandidate) -> bool:
    left_isbns = {value for value in (left.isbn_10, left.isbn_13) if value}
    right_isbns = {value for value in (right.isbn_10, right.isbn_13) if value}
    if left_isbns & right_isbns:
        return True
    # The same title and authors can identify a work, not a specific edition.
    # If both records provide ISBNs and none agree, keep the editions separate
    # instead of creating a misleading multi-source "verified" record.
    if left_isbns and right_isbns:
        return False
    title_match = normalize_text(left.title) == normalize_text(right.title)
    left_authors = {normalize_text(value) for value in left.authors}
    right_authors = {normalize_text(value) for value in right.authors}
    return title_match and bool(left_authors & right_authors)


def _prefer(current, incoming):
    return current if current not in (None, "", []) else incoming


def merge_two(left: BookCandidate, right: BookCandidate) -> BookCandidate:
    merged = deepcopy(left)
    conflicts: list[str] = []
    if left.published_year and right.published_year and left.published_year != right.published_year:
        conflicts.append(f"published_year: {left.published_year} vs {right.published_year}")
    merged.title = _prefer(left.title, right.title)
    merged.authors = list(dict.fromkeys([*left.authors, *right.authors]))
    merged.isbn_10 = _prefer(left.isbn_10, right.isbn_10)
    merged.isbn_13 = _prefer(left.isbn_13, right.isbn_13)
    merged.published_year = _prefer(left.published_year, right.published_year)
    merged.description = _prefer(left.description, right.description)
    merged.language = _prefer(left.language, right.language)
    merged.page_count = _prefer(left.page_count, right.page_count)
    merged.cover_url = _prefer(left.cover_url, right.cover_url)
    merged.categories = list(dict.fromkeys([*left.categories, *right.categories]))[:20]
    if right.ratings_count and (not left.ratings_count or right.ratings_count > left.ratings_count):
        merged.average_rating = right.average_rating
        merged.ratings_count = right.ratings_count
    records = {}
    for record in [*left.source_records, *right.source_records]:
        key = (record.source_name, str(record.source_url), record.source_book_id)
        if key in records:
            previous = records[key]
            previous.fields_verified = list(dict.fromkeys([*previous.fields_verified, *record.fields_verified]))
            previous.conflicts = list(dict.fromkeys([*previous.conflicts, *record.conflicts]))
        else:
            records[key] = deepcopy(record)
    merged.source_records = list(records.values())
    if conflicts:
        merged.source_records[-1].conflicts.extend(conflicts)
    merged.search_roles = list(dict.fromkeys([*left.search_roles, *right.search_roles]))
    merged.canonical_id = merged.isbn_13 or merged.isbn_10 or merged.canonical_id
    source_count = len({record.source_name for record in merged.source_records})
    merged.verification_status = (
        "verified_two_sources" if source_count >= 2 else "verified_single_source"
    )
    return merged


def merge_candidates(candidates: list[BookCandidate]) -> list[BookCandidate]:
    merged: list[BookCandidate] = []
    for candidate in candidates:
        for index, existing in enumerate(merged):
            if identity_matches(existing, candidate):
                merged[index] = merge_two(existing, candidate)
                break
        else:
            merged.append(deepcopy(candidate))
    return merged
