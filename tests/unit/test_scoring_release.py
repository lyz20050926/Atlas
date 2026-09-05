"""Conceptual-role regressions with unchanged catalogue/evaluation snapshots."""
import json

import pytest

from src.config import PROJECT_ROOT
from src.models import BookCandidate, LearningGoal, UserProfile
from src.services.recommendation import ROLES, _select_complementary
from src.services.scoring import assess_book


def ethics_books() -> list[BookCandidate]:
    payload = json.loads((PROJECT_ROOT / "data/fixtures/evaluation_books.json").read_text(encoding="utf-8"))
    ids = {"9780262534635", "9780195374049", "9780190652951"}
    return [BookCandidate.model_validate(book) for book in payload["books"] if book["canonical_id"] in ids]


def ethics_goal() -> LearningGoal:
    return LearningGoal(topic="Human-Robot Ethics", purpose="Develop an interdisciplinary foundation",
                        duration_weeks=6, hours_per_week=3,
                        required_perspectives=["Ethics", "Robotics", "Cognitive Science"])


def test_philosophical_analysis_of_moral_subjects_has_a_conceptual_role():
    book = next(book for book in ethics_books() if book.title == "The Machine Question")
    assessment = assess_book(book, ethics_goal(), UserProfile(education_level="undergraduate"), ROLES[0])
    assert assessment.goal_relevance >= 0.3
    assert assessment.overall_rank_score >= 0.35
    assert assessment.perspective_value >= 0.35
    # Missing page count remains an explicit uncertainty, not fabricated evidence.
    assert book.page_count is None
    assert any("Page count is unavailable" in note for note in assessment.reservations)


@pytest.mark.parametrize("case", [
    case for case in json.loads((PROJECT_ROOT / "data/evaluation_cases.json").read_text(encoding="utf-8"))
    if case["id"].startswith("ethics-")
], ids=lambda case: case["id"])
def test_existing_ethics_snapshots_supply_three_genuinely_distinct_roles(case):
    goal = LearningGoal(topic=case["topic"], purpose="Develop an interdisciplinary foundation",
                        duration_weeks=case["weeks"], hours_per_week=case["hours"],
                        required_perspectives=case["perspectives"])
    profile = UserProfile(education_level="undergraduate", major=case["major"],
                          background_knowledge=case["background"], interests=case["perspectives"])
    selected, assessments, _ = _select_complementary(ethics_books(), goal, profile)
    assert [book.canonical_id for book in selected] == ["9780262534635", "9780195374049", "9780190652951"]
    assert [assessment.evaluated_role for assessment in assessments] == list(ROLES)


def test_role_labels_and_topic_mentions_alone_do_not_establish_foundational_coverage():
    book = BookCandidate(canonical_id="news", title="Robot Ethics News", authors=["Editorial team"],
                         description="Recent news about robots, social impacts, ethics and public policy.",
                         categories=["Robot Ethics"], language="en", search_roles=[ROLES[0]])
    assessment = assess_book(book, ethics_goal(), UserProfile(education_level="undergraduate"), ROLES[0])
    assert assessment.goal_relevance >= 0.3
    assert assessment.perspective_value < 0.35
    assert _select_complementary([book], ethics_goal(), UserProfile(education_level="undergraduate"))[0] == []


def test_generic_conceptual_wording_cannot_make_an_off_topic_book_relevant():
    book = BookCandidate(canonical_id="unrelated", title="The Philosophy of Garden Design", authors=["Author"],
                         description="Philosophical and theoretical frameworks for conceptual garden design.",
                         categories=["Philosophy", "Landscape design"], language="en", search_roles=[ROLES[0]])
    assessment = assess_book(book, ethics_goal(), UserProfile(education_level="undergraduate"), ROLES[0])
    assert assessment.goal_relevance < 0.3
    assert _select_complementary([book], ethics_goal(), UserProfile(education_level="undergraduate"))[0] == []


def test_conceptual_frameworks_are_not_limited_to_books_labelled_introduction():
    goal = LearningGoal(topic="Social psychology", purpose="Understand group behaviour",
                        duration_weeks=6, hours_per_week=4)
    book = BookCandidate(canonical_id="conceptual-groups", title="Social Psychology: Group Behaviour", authors=["Author"],
                         description="Conceptual frameworks and theoretical accounts of conformity and persuasion in social psychology.",
                         categories=["Social psychology"], language="en", search_roles=[ROLES[0]])
    assessment = assess_book(book, goal, UserProfile(education_level="undergraduate"), ROLES[0])
    assert assessment.goal_relevance >= 0.3
    assert assessment.perspective_value >= 0.35
