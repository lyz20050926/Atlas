from __future__ import annotations

from src.models import LearningGoal, UserProfile
from src.replanning import replan_path
from src.services.recommendation import (
    _build_path,
    _select_complementary,
    build_concept_requirements,
    load_demo_candidates,
)


def test_fixed_demo_replan_compresses_and_preserves_perspectives() -> None:
    profile = UserProfile(
        user_id="demo",
        education_level="undergraduate",
        major="EEE",
        background_knowledge=["Python", "Machine Learning", "Control theory"],
        interests=["Robotics", "Cognitive Science", "Ethics"],
    )
    goal = LearningGoal(
        topic="Embodied Intelligence",
        purpose="Learn",
        duration_weeks=6,
        hours_per_week=4,
        required_perspectives=["Robotics", "Cognitive Science", "Ethics"],
        preferred_difficulty="intermediate",
        desired_balance="balanced",
    )
    selected, assessments, _ = _select_complementary(load_demo_candidates(), goal, profile)
    path = _build_path(selected, assessments, build_concept_requirements(goal, profile), goal, profile)
    revised, revision = replan_path(path, goal, 2, True, "enactivism")
    assert revised.version == 2
    assert revised.total_estimated_hours <= 12
    assert "Practice first" in revised.stages[0].title
    assert [stage.stage_number for stage in revised.stages] == [1, 2, 3]
    assert any("enactivism" in item for stage in revised.stages for item in stage.selected_chapters)
    assert revision.preserved_goals == ["Robotics", "Cognitive Science", "Ethics"]


def test_replan_rounding_never_exceeds_small_budget() -> None:
    profile = UserProfile(user_id="rounding", education_level="undergraduate")
    goal = LearningGoal(
        topic="Embodied Intelligence",
        purpose="Learn",
        duration_weeks=4,
        hours_per_week=4,
        required_perspectives=["Robotics", "Cognitive Science", "Ethics"],
        preferred_difficulty="intermediate",
        desired_balance="balanced",
    )
    selected, assessments, _ = _select_complementary(load_demo_candidates(), goal, profile)
    path = _build_path(selected, assessments, build_concept_requirements(goal, profile), goal, profile)
    revised, _ = replan_path(path, goal, 2, True, "enactivism")
    assert revised.total_estimated_hours <= 8
    assert revised.constraints_satisfied


def test_replan_does_not_claim_scope_reduction_when_existing_scope_still_fits() -> None:
    profile = UserProfile(user_id="schedule-only", education_level="undergraduate")
    goal = LearningGoal(
        topic="Embodied Intelligence",
        purpose="Learn",
        duration_weeks=6,
        hours_per_week=4,
        required_perspectives=["Robotics", "Cognitive Science", "Ethics"],
    )
    selected, assessments, _ = _select_complementary(load_demo_candidates(), goal, profile)
    path = _build_path(selected, assessments, build_concept_requirements(goal, profile), goal, profile)

    revised, revision = replan_path(path, goal, 3, False, None)

    assert revised.total_estimated_hours == path.total_estimated_hours
    assert "existing reading scope already fits" in revision.explanation
    assert "scope was reduced" not in revision.explanation


def test_replan_cannot_turn_incomplete_book_coverage_into_a_pass():
    profile = UserProfile(user_id="partial", education_level="beginner")
    goal = LearningGoal(topic="Machine learning", purpose="A classification experiment", duration_weeks=6, hours_per_week=4)
    selected, assessments, _ = _select_complementary(load_demo_candidates(), goal, profile)
    path = _build_path(selected, assessments, build_concept_requirements(goal, profile), goal, profile)
    path.constraints_satisfied = False
    path.warnings = ["Research methods remain uncovered."]
    revised, revision = replan_path(path, goal, 1, False, None)
    assert not revised.constraints_satisfied
    assert "Research methods remain uncovered." in revised.warnings
    assert "All requested perspectives" not in revision.explanation
