import json

import pytest
from pydantic import ValidationError

from src.models import BookCandidate, LearningGoal, UserProfile
from src.services.goal_alignment import explicit_exclusions, plan_catalog_queries, review_selection
from src.services.learning_focus import focus_search_phrases, focused_topic
from src.services.recommendation import ROLES, build_concept_requirements, build_query_variants
from src.services.scoring import assess_book


def goal(**updates):
    return LearningGoal(topic="心理学", purpose="理解思维过程", duration_weeks=6,
                        hours_per_week=4, interface_language="zh", book_language_preferences=["zh"], **updates)


def test_existing_goal_records_default_to_empty_focus_and_new_details_are_bounded():
    original = goal().model_dump()
    original.pop("focus_details")
    assert LearningGoal.model_validate(original).focus_details == ""
    assert LearningGoal.model_validate_json(goal(focus_details="注意力与工作记忆").model_dump_json()).focus_details == "注意力与工作记忆"
    with pytest.raises(ValidationError):
        goal(focus_details="x" * 2001)


@pytest.mark.parametrize("focus", [
    "我想深入学习认知心理学，重点了解注意力和工作记忆。不想读心灵鸡汤类书籍。",
    "认知心理学；注意力；工作记忆。不要心灵鸡汤。",
])
def test_free_form_psychology_details_narrow_every_catalogue_role(focus):
    learning_goal = goal(focus_details=focus)
    phrases = focus_search_phrases(learning_goal)
    assert phrases == ["认知心理学", "注意力", "工作记忆"]
    for variants in build_query_variants(learning_goal).values():
        assert all("工作记忆" in query and "心灵鸡汤" not in query for query, _ in variants)
        assert all(len(query) < 150 for query, _ in variants)
    concepts = build_concept_requirements(learning_goal, UserProfile(education_level="beginner", interface_language="zh"))
    assert all("工作记忆" in concept.concept for concept in concepts)


def test_english_focus_is_short_and_never_searches_exclusions_or_whole_paragraphs():
    learning_goal = LearningGoal(topic="Psychology", purpose="Understand cognition", duration_weeks=6, hours_per_week=4,
        focus_details="I want to go deeper into cognitive psychology, especially attention and working memory. No self-help books. " + "A long explanation " * 40)
    query = focused_topic(learning_goal)
    assert "working memory" in query
    assert "self-help" not in query
    assert len(query) <= 110


@pytest.mark.parametrize("details,expected,excluded", [
    ("Working memory, not self-help books.", ["Working memory"], "self-help"),
    ("Attention. Not clinical therapy.", ["Attention"], "clinical therapy"),
    ("工作记忆；不想学习临床治疗。", ["工作记忆"], "临床治疗"),
    ("注意力，不涉及临床治疗。", ["注意力"], "临床治疗"),
    ("认知心理学；不包含心理咨询。", ["认知心理学"], "心理咨询"),
])
def test_plain_negations_never_become_positive_catalogue_hints(details, expected, excluded):
    learning_goal = goal(focus_details=details)
    assert focus_search_phrases(learning_goal) == expected
    assert excluded not in focused_topic(learning_goal)
    assert learning_goal.focus_details == details
    for variants in build_query_variants(learning_goal).values():
        assert all(excluded not in query for query, _ in variants)


@pytest.mark.parametrize("details,excluded,expected", [
    ("I want to go deeper into cognitive psychology, especially attention and working memory. I'd like research-based books and experiments I can try, not self-help books.", "self-help", ["cognitive psychology", "attention working memory"]),
    ("我想深入学习认知心理学，重点了解注意力和工作记忆。希望读有研究依据的书，试着设计小实验，不想读心灵鸡汤类书籍。", "心灵鸡汤", ["认知心理学", "注意力", "工作记忆"]),
])
def test_bilingual_form_examples_keep_original_brief_but_drop_excluded_subjects(details, excluded, expected):
    learning_goal = goal(focus_details=details)
    phrases = focus_search_phrases(learning_goal)
    assert phrases == expected
    assert any("工作记忆" in item or "working memory" in item for item in phrases)
    assert all(excluded not in item for item in phrases)
    assert excluded not in focused_topic(learning_goal)
    assert learning_goal.model_dump()["focus_details"] == details


def test_focus_exclusions_and_positive_learning_questions_stay_separate():
    learning_goal = goal(focus_details="工作记忆；不想读心灵鸡汤类书籍。理解如何避免记忆偏差。")
    assert any("心灵鸡汤" in term for term in explicit_exclusions(learning_goal))
    assert not any("记忆偏差" in term for term in explicit_exclusions(learning_goal))
    excluded_book = BookCandidate(canonical_id="no", title="心灵鸡汤类书籍", authors=["A"], language="zh")
    assert assess_book(excluded_book, learning_goal, UserProfile(education_level="beginner"), ROLES[0]).goal_relevance == 0


@pytest.mark.parametrize("details", ["中文优先，每周可以读两小时。不要英文书。", "Books in English. I have 4 hours each week."])
def test_format_and_scheduling_preferences_do_not_become_subject_queries(details):
    learning_goal = goal(focus_details=details)
    assert focus_search_phrases(learning_goal) == []
    assert focused_topic(learning_goal) == learning_goal.topic


def test_specific_subfield_changes_rank_and_flags_unconfirmed_coverage():
    learning_goal = goal(focus_details="工作记忆与注意力")
    profile = UserProfile(education_level="undergraduate", interface_language="zh")
    generic = BookCandidate(canonical_id="broad", title="心理学导论", authors=["Author"], language="zh",
        description="心理学基础理论概念与研究方法，日常案例及社会行为。", search_roles=list(ROLES))
    specific = generic.model_copy(update={"canonical_id": "focused", "title": "认知心理学：工作记忆与注意力",
        "description": "工作记忆模型与注意力的基础概念、实验方法、实际应用、证据局限与评估。"})
    broad_score = assess_book(generic, learning_goal, profile, ROLES[0])
    focused_score = assess_book(specific, learning_goal, profile, ROLES[0])
    assert focused_score.goal_relevance > broad_score.goal_relevance
    assert focused_score.overall_rank_score > broad_score.overall_rank_score
    assert broad_score.meets_stated_requirements is False
    assert any("细分方向" in note for note in broad_score.reservations)


def test_complete_focus_reaches_query_and_semantic_selection_without_loss():
    learning_goal = goal(focus_details="我想研究工作记忆容量与注意力控制的关系；不要心灵鸡汤。")
    profile = UserProfile(education_level="undergraduate")
    calls = []

    class Provider:
        def generate_structured(self, system, user, output_model):
            payload = json.loads(user)
            calls.append((system, payload))
            assert payload["goal"]["focus_details"] == learning_goal.focus_details
            if output_model.__name__ == "RetrievalBrief":
                return output_model(foundation_query="工作记忆 认知心理学", application_query="注意力 实验方法", perspective_query="记忆 可重复性")
            return output_model(requirements_met=False, foundation_id="", foundation_reason="", application_id="",
                application_reason="", perspective_id="", perspective_reason="", gaps="需要更细分的资料")

    queries = plan_catalog_queries(learning_goal, profile, Provider())
    assert queries[ROLES[1]] == "注意力 实验方法"
    review_selection({role: [] for role in ROLES}, learning_goal, profile, Provider())
    assert len(calls) == 2
