from __future__ import annotations

from src.models import BookCandidate


def estimate_focused_hours(book: BookCandidate) -> float:
    """Estimate a selective reading workload, not a claim about completion time."""
    if not book.page_count:
        return 6.0
    return round(max(3.0, min(12.0, book.page_count * 0.35 / 25)), 1)

