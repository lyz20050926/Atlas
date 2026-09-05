from __future__ import annotations

from src.models import BookCandidate, LearningGoal, UserProfile
from src.services.recommendation import (
    ROLES,
    _select_complementary,
    build_queries,
    load_demo_candidates,
)
from src.services.scoring import WEIGHTS, assess_book


def profile() -> UserProfile:
    return UserProfile(
        user_id="test",
        education_level="undergraduate",
        major="EEE",
        background_knowledge=["Python", "Machine Learning", "Control theory"],
        interests=["Robotics", "Cognitive Science", "Ethics"],
    )


def goal() -> LearningGoal:
    return LearningGoal(
        topic="Embodied Intelligence",
        purpose="Learn a new field",
        duration_weeks=6,
        hours_per_week=4,
        required_perspectives=["Robotics", "Cognitive Science", "Ethics"],
        preferred_difficulty="intermediate",
        desired_balance="theory and application",
    )


def test_scoring_weights_sum_to_one() -> None:
    assert sum(WEIGHTS.values()) == 1.0


def test_assessment_is_bounded_and_explained() -> None:
    book = load_demo_candidates()[0]
    assessment = assess_book(book, goal(), profile(), ROLES[0])
    assert 0 <= assessment.overall_rank_score <= 1
    assert assessment.recommendation_reason
    assert assessment.book_overview
    assert assessment.why_now
    assert assessment.confidence == "medium"


def test_selection_returns_one_book_per_role() -> None:
    books = load_demo_candidates()
    selected, assessments, warnings = _select_complementary(books, goal(), profile())
    assert len(selected) == 3
    assert len({book.canonical_id for book in selected}) == 3
    assert len(assessments) == 3
    assert warnings == []
    assert len({item.recommendation_reason for item in assessments}) == 3


def test_embodied_demo_uses_role_specific_queries() -> None:
    queries = build_queries(goal())
    assert queries[ROLES[0]] == "embodied cognition"
    assert queries[ROLES[1]] == "autonomous mobile robots"
    assert queries[ROLES[2]] == "robot ethics"


def test_selection_does_not_force_an_unrelated_book_into_a_role() -> None:
    biography = BookCandidate(
        canonical_id="biography",
        title="A Technology Founder",
        authors=["Example Author"],
        description="A biography about entrepreneurship, business, and personal ambition.",
        categories=["Biography", "Business"],
        language="en",
        search_roles=[ROLES[1]],
    )

    selected, assessments, warnings = _select_complementary([biography], goal(), profile())

    assert selected == []
    assert assessments == []
    assert any("not forced into the path" in warning for warning in warnings)


def test_selection_skips_a_topic_match_that_does_not_fit_the_stage_role() -> None:
    conceptual = BookCandidate(
        canonical_id="concept-only",
        title="Embodied Cognition Theory",
        authors=["Example Author"],
        description="A conceptual and philosophical account of embodied cognition theory.",
        categories=["Cognitive Science", "Philosophy"],
        language="en",
        search_roles=[ROLES[1]],
    )
    technical = BookCandidate(
        canonical_id="technical",
        title="Embodied Robotics Methods",
        authors=["Example Author"],
        description="Algorithms, control methods, robot systems, and engineering applications.",
        categories=["Robotics", "Engineering"],
        language="en",
        search_roles=[ROLES[1]],
    )

    selected, _, _ = _select_complementary([conceptual, technical], goal(), profile())

    assert [book.canonical_id for book in selected] == ["technical"]


def test_generic_technical_vocabulary_cannot_replace_topic_relevance() -> None:
    generic_technology_book = BookCandidate(
        canonical_id="generic-smart-system",
        title="Smart Safety Monitoring Technology",
        authors=["Example Author"],
        description=(
            "A practical engineering handbook about internet-of-things monitoring, "
            "industrial safety systems, sensors, and applications."
        ),
        categories=["Technology", "Engineering"],
        language="en",
        search_roles=[ROLES[1]],
    )

    assessment = assess_book(generic_technology_book, goal(), profile(), ROLES[1])

    assert assessment.goal_relevance < 0.3
    assert assessment.overall_rank_score < 0.35
    assert "should not be included" in assessment.recommendation_reason


def test_short_chinese_overlap_cannot_make_public_health_relevant_to_time_series() -> None:
    time_series_goal = goal().model_copy(
        update={
            "topic": "时间序列预测",
            "purpose": "使用时间序列模型预测能源需求",
            "required_perspectives": ["数据科学", "能源系统", "机器学习工程"],
            "interface_language": "zh",
            "book_language_preferences": ["zh"],
        }
    )
    chinese_profile = profile().model_copy(
        update={
            "major": "数据科学",
            "interests": time_series_goal.required_perspectives,
            "interface_language": "zh",
        }
    )
    public_health = BookCandidate(
        canonical_id="public-health",
        title="公共卫生应急与管理案例",
        authors=["示例作者"],
        description="讨论突发事件期间的公共卫生管理、组织协调和应急响应。",
        categories=["公共卫生", "管理"],
        language="zh",
        search_roles=[ROLES[1]],
    )
    relevant = BookCandidate(
        canonical_id="time-series",
        title="时间序列分析简明教程",
        authors=["示例作者"],
        description="介绍时间序列建模、预测、误差评估与实际应用。",
        categories=["数据科学", "统计学"],
        language="zh",
        search_roles=[ROLES[1]],
    )

    rejected = assess_book(public_health, time_series_goal, chinese_profile, ROLES[1])
    accepted = assess_book(relevant, time_series_goal, chinese_profile, ROLES[1])

    assert rejected.goal_relevance < 0.3
    assert rejected.overall_rank_score < 0.35
    assert accepted.goal_relevance >= 0.3
    assert accepted.overall_rank_score >= 0.35


def test_promotional_health_claims_cannot_ride_on_a_topic_keyword() -> None:
    suspicious = BookCandidate(
        canonical_id="suspicious",
        title="具身AI供养配方学",
        authors=["示例作者"],
        description=(
            "以系统生理年轻化与延寿为根本使命，形成自动进化的永动飞轮，"
            "并承诺让健康寿命最大化。"
        ),
        categories=["Computers"],
        language="zh",
        search_roles=[ROLES[1]],
    )
    assessment = assess_book(
        suspicious,
        goal().model_copy(
            update={
                "topic": "具身智能",
                "interface_language": "zh",
                "book_language_preferences": ["zh"],
            }
        ),
        profile().model_copy(update={"interface_language": "zh"}),
        ROLES[1],
    )

    assert assessment.goal_relevance < 0.3
    assert assessment.overall_rank_score < 0.35
    assert any("宣传性" in item for item in assessment.reservations)
