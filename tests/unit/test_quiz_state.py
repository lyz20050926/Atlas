"""State-preservation contracts for partial, mixed-format practice submissions."""
from __future__ import annotations

import pytest

from src.diagnostic import build_mixed_diagnostic, diagnostic_scope_key
from src.learning_review import AnswerReview, review_mastery
from src.models import BookCandidate, ConceptMastery, LearningGoal, ReadingStage, UserProfile
from src.quiz_ui import merge_mastery, same_question_set


def _mastery(concept: str, score: float) -> ConceptMastery:
    return ConceptMastery(concept=concept, mastery_score=score, confidence=.5,
                          evidence=[f"Evidence for {concept}"])


def test_partial_mastery_merge_preserves_unanswered_concepts_without_mutating_inputs():
    previous = [_mastery("Memory", .8), _mastery("Causality", .5)]
    assessed = [_mastery("Causality", .8), _mastery("Validity", .2)]
    before_previous = [item.model_dump() for item in previous]
    before_assessed = [item.model_dump() for item in assessed]
    merged = merge_mastery(previous, assessed)
    assert [(item.concept, item.mastery_score) for item in merged] == [
        ("Memory", .8), ("Causality", .8), ("Validity", .2),
    ]
    assert [item.model_dump() for item in previous] == before_previous
    assert [item.model_dump() for item in assessed] == before_assessed


def test_empty_assessment_does_not_lower_or_discard_prior_mastery():
    previous = [_mastery("Memory", .8), _mastery("Causality", .5)]
    assert merge_mastery(previous, []) == previous
    assert merge_mastery([], []) == []


def test_new_explanation_or_shuffled_choices_is_not_a_new_set():
    goal = LearningGoal(topic="Psychology", purpose="Understand memory", duration_weeks=6, hours_per_week=4)
    questions = build_mixed_diagnostic(goal, UserProfile(education_level="undergraduate"))
    regenerated = [q.model_copy(deep=True) for q in questions]
    regenerated[0].options.reverse()
    regenerated[0].explanation = "A clearer explanation of the same correct answer."
    regenerated[2].rubric = "Updated wording, same reasoning task."
    assert same_question_set(questions, regenerated)
    regenerated[2].prompt = "A genuinely different reasoning task"
    assert not same_question_set(questions, regenerated)
    assert not same_question_set([], [])


def test_mixed_partial_review_preserves_existing_signals_for_unanswered_items():
    goal = LearningGoal(topic="心理学", purpose="理解研究证据", duration_weeks=6,
                        hours_per_week=4, interface_language="zh")
    questions = build_mixed_diagnostic(goal, UserProfile(education_level="undergraduate"))
    previous = [_mastery(question.concept, .8) for question in questions]
    reviews = [
        AnswerReview(question_number=index, verdict="misconception" if index == 1 else "insufficient",
                     answer_quote="某个选项" if index == 1 else "", feedback="解释已保存，指出证据边界。",
                     model_answer="参考思路需要区分相关与因果。", follow_up="什么证据才能确定因果方向？",
                     assessment_method="objective" if index < 3 else "unavailable")
        for index in range(1, 4)
    ]
    assessed = review_mastery(questions, reviews)
    assert len(assessed) == 1
    merged = merge_mastery(previous, assessed)
    assert [item.mastery_score for item in merged] == [.2, .8, .8]


@pytest.mark.parametrize("changed", ["book", "focus", "language", "stage"])
def test_practice_scope_changes_when_answer_context_changes(changed):
    goal = LearningGoal(topic="Psychology", purpose="Understand memory", duration_weeks=6,
                        hours_per_week=4, interface_language="en", focus_details="Retrieval practice")
    profile = UserProfile(education_level="undergraduate", background_knowledge=["Introductory psychology"])
    book = BookCandidate(canonical_id="book-one", title="Memory", authors=["Author"])
    stage = ReadingStage(stage_number=1, title="Memory", learning_objective="Understand retrieval",
                         concepts=["Retrieval"], estimated_hours=3)
    original_scope = diagnostic_scope_key(goal, profile, book, stage)
    if changed == "book":
        book = book.model_copy(update={"canonical_id": "book-two"})
    elif changed == "focus":
        goal = goal.model_copy(update={"focus_details": "Working-memory mechanisms"})
    elif changed == "language":
        goal = goal.model_copy(update={"interface_language": "zh"})
    else:
        stage = stage.model_copy(update={"stage_number": 2})
    assert diagnostic_scope_key(goal, profile, book, stage) != original_scope
