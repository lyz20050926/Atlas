from __future__ import annotations

from src.diagnostic import build_diagnostic, diagnostic_scope_key, score_diagnostic
from src.models import BookCandidate, LearningGoal, ReadingStage, UserProfile


def test_diagnostic_distinguishes_explanation_from_skip() -> None:
    profile = UserProfile(education_level="undergraduate", major="EEE")
    goal = LearningGoal(
        topic="Embodied Intelligence",
        purpose="Learn",
        duration_weeks=6,
        hours_per_week=4,
        required_perspectives=[],
        preferred_difficulty="intermediate",
        desired_balance="balanced",
    )
    questions = build_diagnostic(goal, profile)
    answers = [
        "A body interacts with its environment through sensorimotor feedback.",
        "A sensor triggers action, feedback updates the next action.",
        "The claim has supporting evidence, applies under stated conditions, and has limits.",
    ]
    scored = score_diagnostic(questions, answers)
    skipped = score_diagnostic(questions, ["", "", ""], skipped=True)
    assert min(item.mastery_score for item in scored) > 0.25
    assert max(item.confidence for item in skipped) == 0.25


def test_diagnostic_follows_the_current_book_and_stage() -> None:
    profile = UserProfile(education_level="undergraduate", major="EEE")
    goal = LearningGoal(
        topic="Machine Learning",
        purpose="Apply it in research",
        duration_weeks=6,
        hours_per_week=4,
    )
    stage = ReadingStage(
        stage_number=1,
        title="Foundations",
        learning_objective="Understand transfer learning foundations",
        concepts=["transfer learning", "domain adaptation"],
        books=["book-a"],
        estimated_hours=4,
    )
    first_book = BookCandidate(canonical_id="book-a", title="Transfer Learning", authors=["A"])
    second_book = BookCandidate(canonical_id="book-b", title="Practical ML", authors=["B"])

    first_questions = build_diagnostic(goal, profile, first_book, stage)
    second_questions = build_diagnostic(goal, profile, second_book, stage)

    assert all(first_book.title in question.prompt for question in first_questions)
    assert all(second_book.title in question.prompt for question in second_questions)
    assert first_questions != second_questions
    assert diagnostic_scope_key(goal, profile, first_book, stage) != diagnostic_scope_key(
        goal, profile, second_book, stage
    )


def test_chinese_technical_answers_are_not_penalized_for_missing_generic_labels() -> None:
    profile = UserProfile(education_level="undergraduate", major="电子与电气工程")
    goal = LearningGoal(
        topic="具身智能",
        purpose="用于机器人研究",
        duration_weeks=6,
        hours_per_week=4,
        interface_language="zh",
    )
    stage = ReadingStage(
        stage_number=2,
        title="技术原理与应用",
        learning_objective="理解移动机器人的感知、规划与控制",
        concepts=["感知—规划—控制闭环", "方法与应用"],
        books=["robotics"],
        estimated_hours=4,
    )
    book = BookCandidate(canonical_id="robotics", title="自主移动机器人", authors=["A"])
    questions = build_diagnostic(goal, profile, book, stage)
    answers = [
        "机器人通过传感器感知环境，完成定位和规划，再由控制器执行动作并根据反馈更新。",
        "例如 SLAM 先融合激光与视觉传感器估计位姿并建立地图，然后规划路径，控制机器人导航。",
        "依据是真实环境中的定位误差；方法依赖传感器同步，在动态遮挡条件下可能失效，这是它的限制。",
    ]

    scored = score_diagnostic(questions, answers)

    assert min(item.mastery_score for item in scored) >= 0.67
    assert all("边界线索" in item.evidence[0] for item in scored)


def test_short_non_answer_remains_a_starting_point() -> None:
    profile = UserProfile(education_level="undergraduate")
    goal = LearningGoal(
        topic="机器学习",
        purpose="科研应用",
        duration_weeks=4,
        hours_per_week=3,
        interface_language="zh",
    )
    questions = build_diagnostic(goal, profile)

    scored = score_diagnostic(questions, ["不知道", "没学过", "不清楚"])

    assert max(item.mastery_score for item in scored) <= 0.25
