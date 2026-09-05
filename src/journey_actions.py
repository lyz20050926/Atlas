from __future__ import annotations

from src.models import BookAssessment, BookCandidate, RecommendationResult
from src.services.time_estimation import estimate_focused_hours


def should_accept_progress_update(
    current_percent: int,
    requested_percent: int,
    learner_message: str,
) -> bool:
    """Reject accidental progress regressions unless the learner clearly corrects them."""
    if requested_percent >= current_percent:
        return True
    correction_terms = (
        "correction",
        "correct that",
        "actually",
        "set it back",
        "change it back",
        "更正",
        "纠正",
        "改成",
        "实际是",
        "其实是",
        "退回",
    )
    normalized = learner_message.casefold()
    return any(term in normalized for term in correction_terms)


def normalize_reading_state(progress_percent: int, status: str) -> tuple[int, str]:
    """Keep progress and status consistent when the learner saves either control."""
    if not 0 <= progress_percent <= 100:
        raise ValueError("progress_percent must be between 0 and 100")
    if status not in {"planned", "reading", "paused", "completed"}:
        raise ValueError("Unsupported reading status")
    if status == "completed" or progress_percent == 100:
        return 100, "completed"
    if progress_percent > 0 and status == "planned":
        return progress_percent, "reading"
    return progress_percent, status


def resolve_current_book_id(
    result: RecommendationResult,
    progress_by_book: dict[str, dict[str, object]],
) -> str:
    """Resolve the active book, automatically skipping completed stages."""
    ordered_ids = [stage.books[0] for stage in result.reading_path.stages if stage.books]
    if not ordered_ids:
        raise ValueError("The reading path has no books")
    explicit = next(
        (
            canonical_id
            for canonical_id in ordered_ids
            if progress_by_book.get(canonical_id, {}).get("is_current")
            and int(progress_by_book.get(canonical_id, {}).get("progress_percent", 0)) < 100
        ),
        None,
    )
    if explicit:
        return explicit
    return next(
        (
            canonical_id
            for canonical_id in ordered_ids
            if int(progress_by_book.get(canonical_id, {}).get("progress_percent", 0)) < 100
        ),
        ordered_ids[-1],
    )


def resolve_stage_view_number(
    result: RecommendationResult,
    requested_stage_number: object,
    active_stage_number: int,
) -> int:
    """Resolve a view-only stage selection without changing learner progress."""
    available = {
        stage.stage_number
        for stage in result.reading_path.stages
        if stage.books
    }
    try:
        requested = int(str(requested_stage_number).strip())
    except (TypeError, ValueError):
        return active_stage_number
    return requested if requested in available else active_stage_number


def next_stage_book_id(
    result: RecommendationResult,
    stage_number: int,
) -> str | None:
    """Return the first book in the next stage, if one exists."""
    later = sorted(
        (
            stage
            for stage in result.reading_path.stages
            if stage.stage_number > stage_number and stage.books
        ),
        key=lambda stage: stage.stage_number,
    )
    return later[0].books[0] if later else None


def stage_progress_values(
    result: RecommendationResult,
    progress_by_book: dict[str, dict[str, object]],
) -> list[int]:
    return [
        int(progress_by_book.get(stage.books[0], {}).get("progress_percent", 0))
        if stage.books
        else 0
        for stage in result.reading_path.stages
    ]


def replace_stage_book(
    result: RecommendationResult,
    book: BookCandidate,
    assessment: BookAssessment,
    stage_number: int,
    *,
    available_hours: float | None = None,
) -> RecommendationResult:
    """Return a new recommendation result with one stage book replaced."""
    if assessment.canonical_id != book.canonical_id:
        raise ValueError("The assessment does not belong to the replacement book")

    stages = [stage.model_copy(deep=True) for stage in result.reading_path.stages]
    target = next((stage for stage in stages if stage.stage_number == stage_number), None)
    if target is None or not target.books:
        raise ValueError("The selected reading stage does not exist")

    old_canonical_id = target.books[0]
    original_assessment = next((item for item in result.assessments if item.canonical_id == old_canonical_id), None)
    role_changed = bool(original_assessment and original_assessment.evaluated_role != assessment.evaluated_role)
    # A user-selected substitution does not silently redefine this stage's purpose.
    # Keep its role stable and flag unverified role coverage in the new plan.
    if role_changed:
        assessment = assessment.model_copy(update={
            "evaluated_role": original_assessment.evaluated_role,
            "meets_stated_requirements": False,
        })
    selected_in_another_stage = any(
        stage.stage_number != stage_number and book.canonical_id in stage.books
        for stage in stages
    )
    if selected_in_another_stage:
        raise ValueError("This book is already used in another reading stage")

    target.books = [book.canonical_id]
    # Stage titles include the book name and are also sent to the tutor.
    separator = "：" if "：" in target.title else ": "
    target.title = f"{target.title.split(separator, 1)[0]}{separator}{book.title}"
    target.estimated_hours = estimate_focused_hours(book)

    selected_books = [
        book if item.canonical_id == old_canonical_id else item
        for item in result.selected_books
    ]
    if all(item.canonical_id != book.canonical_id for item in selected_books):
        selected_books.append(book)
    selected_books = list({item.canonical_id: item for item in selected_books}.values())

    assessments = [
        assessment if item.canonical_id == old_canonical_id else item
        for item in result.assessments
    ]
    if all(item.canonical_id != assessment.canonical_id for item in assessments):
        assessments.append(assessment)
    assessments = list({item.canonical_id: item for item in assessments}.values())

    candidates = list({item.canonical_id: item for item in [*result.candidates, book]}.values())
    total_hours = round(sum(stage.estimated_hours for stage in stages), 1)
    path = result.reading_path.model_copy(
        update={
            "stages": stages,
            "version": result.reading_path.version + 1,
            "total_estimated_hours": total_hours,
            "constraints_satisfied": result.reading_path.constraints_satisfied
            and (available_hours is None or total_hours <= available_hours)
            and assessment.goal_relevance >= 0.3 and assessment.overall_rank_score >= 0.35
            and assessment.meets_stated_requirements is not False,
        }
    )
    return result.model_copy(
        update={
            "candidates": candidates,
            "selected_books": selected_books,
            "assessments": assessments,
            "reading_path": path,
            "execution_trace": [
                *result.execution_trace,
                f"USER · replaced {old_canonical_id} with {book.canonical_id} in stage {stage_number}",
            ],
        }
    )
