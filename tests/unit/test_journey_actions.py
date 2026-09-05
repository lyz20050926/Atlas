from __future__ import annotations

import pytest

from src.config import Settings
from src.graph import run_recommendation_graph
from src.journey_actions import (
    next_stage_book_id,
    normalize_reading_state,
    replace_stage_book,
    resolve_current_book_id,
    resolve_stage_view_number,
    should_accept_progress_update,
    stage_progress_values,
)
from src.models import LearningGoal, UserProfile
from src.services.recommendation import ROLES, load_demo_candidates
from src.services.scoring import assess_book


def _result_fixture():
    profile = UserProfile(user_id="replace-reader", education_level="undergraduate")
    goal = LearningGoal(
        topic="Embodied Intelligence",
        purpose="Learn",
        duration_weeks=6,
        hours_per_week=4,
        required_perspectives=["Robotics", "Cognitive Science", "Ethics"],
    )
    candidates = load_demo_candidates()

    def fixture_search(goal, settings):
        return candidates, []

    result = run_recommendation_graph(
        profile,
        goal,
        Settings(),
        search_function=fixture_search,
    )
    replacement = result.selected_books[0].model_copy(
        update={
            "canonical_id": "manual-replacement",
            "title": "A Verified Replacement",
            "isbn_13": "9780000000002",
        }
    )
    assessment = assess_book(replacement, goal, profile, ROLES[0])
    return result, replacement, assessment


def test_replacing_a_stage_updates_book_assessment_hours_and_version() -> None:
    result, replacement, assessment = _result_fixture()
    old_id = result.reading_path.stages[0].books[0]

    updated = replace_stage_book(result, replacement, assessment, 1)

    assert updated.reading_path.stages[0].books == [replacement.canonical_id]
    assert replacement.title in updated.reading_path.stages[0].title
    assert result.selected_books[0].title not in updated.reading_path.stages[0].title
    assert updated.reading_path.version == result.reading_path.version + 1
    assert replacement.canonical_id in {book.canonical_id for book in updated.selected_books}
    assert old_id not in {book.canonical_id for book in updated.selected_books}
    assert replacement.canonical_id in {item.canonical_id for item in updated.assessments}
    assert updated.reading_path.total_estimated_hours == round(
        sum(stage.estimated_hours for stage in updated.reading_path.stages), 1
    )


def test_replacement_rejects_an_assessment_for_another_book() -> None:
    result, replacement, assessment = _result_fixture()
    wrong = assessment.model_copy(update={"canonical_id": "another-book"})

    with pytest.raises(ValueError, match="does not belong"):
        replace_stage_book(result, replacement, wrong, 1)


def test_replacement_rechecks_time_budget():
    result, replacement, assessment = _result_fixture()
    updated = replace_stage_book(result, replacement, assessment, 1, available_hours=1)
    assert not updated.reading_path.constraints_satisfied


def test_manual_replacement_preserves_stage_role_and_does_not_certify_mismatch():
    result, replacement, assessment = _result_fixture()
    other_role = assessment.model_copy(update={"evaluated_role": ROLES[2]})
    updated = replace_stage_book(result, replacement, other_role, 1)
    saved = next(item for item in updated.assessments if item.canonical_id == replacement.canonical_id)
    assert saved.evaluated_role == ROLES[0]
    assert saved.meets_stated_requirements is False
    assert not updated.reading_path.constraints_satisfied
    assert updated.reading_path.stages[1:] == result.reading_path.stages[1:]


def test_reading_state_normalizes_progress_and_status() -> None:
    assert normalize_reading_state(45, "planned") == (45, "reading")
    assert normalize_reading_state(45, "paused") == (45, "paused")
    assert normalize_reading_state(45, "completed") == (100, "completed")
    assert normalize_reading_state(100, "reading") == (100, "completed")


def test_completed_current_stage_resolves_to_next_incomplete_book() -> None:
    result, _, _ = _result_fixture()
    first = result.reading_path.stages[0].books[0]
    second = result.reading_path.stages[1].books[0]
    progress = {
        first: {"progress_percent": 100, "status": "completed", "is_current": True},
        second: {"progress_percent": 15, "status": "reading", "is_current": False},
    }

    assert resolve_current_book_id(result, progress) == second
    assert next_stage_book_id(result, 1) == second
    assert stage_progress_values(result, progress)[:2] == [100, 15]


def test_progress_regression_requires_an_explicit_correction() -> None:
    assert should_accept_progress_update(70, 85, "I reached 85%") is True
    assert should_accept_progress_update(70, 35, "I am at 35%") is False
    assert should_accept_progress_update(70, 35, "Correction: set it to 35%") is True
    assert should_accept_progress_update(70, 35, "更正为 35%") is True


def test_stage_view_selection_is_view_only_and_falls_back_to_active_stage() -> None:
    result, _, _ = _result_fixture()

    assert resolve_stage_view_number(result, "1", 2) == 1
    assert resolve_stage_view_number(result, "not-a-stage", 2) == 2
    assert resolve_stage_view_number(result, "99", 2) == 2
