from __future__ import annotations

from src.config import Settings
from src.graph import run_recommendation_graph
from src.mentor import (
    _trim_mentor_reply,
    book_conversation_scope,
    find_stage_replacement,
    generate_mentor_response,
)
from src.models import LearningGoal, MentorResponse, UserProfile
from src.services.recommendation import load_demo_candidates


def _context():
    profile = UserProfile(user_id="mentor-reader", education_level="undergraduate")
    goal = LearningGoal(
        topic="Embodied Intelligence",
        purpose="Build a reliable foundation",
        duration_weeks=6,
        hours_per_week=4,
    )
    candidates = load_demo_candidates()
    result = run_recommendation_graph(
        profile,
        goal,
        Settings(),
        search_function=lambda goal, settings: (candidates, []),
    )
    return profile, goal, result, result.selected_books[0]


def test_book_conversation_scope_follows_the_book_not_the_stage() -> None:
    _, _, _, first_book = _context()
    second_book = first_book.model_copy(update={"canonical_id": "another-edition"})

    assert book_conversation_scope(first_book) == f"book:{first_book.canonical_id}"
    assert book_conversation_scope(second_book) == f"book:{second_book.canonical_id}"
    assert book_conversation_scope(first_book) != book_conversation_scope(second_book)


def test_local_mentor_fallback_understands_progress_and_completion() -> None:
    profile, goal, result, book = _context()
    progress, live, warnings = generate_mentor_response(
        "I am 45% through this book",
        profile=profile,
        goal=goal,
        result=result,
        stage_number=1,
        book=book,
        progress_percent=0,
        history=[],
        provider=None,
    )
    completed, _, _ = generate_mentor_response(
        "I finished this stage",
        profile=profile,
        goal=goal,
        result=result,
        stage_number=1,
        book=book,
        progress_percent=45,
        history=[],
        provider=None,
    )

    assert progress.intent == "progress_update"
    assert progress.progress_percent == 45
    assert progress.reading_status == "reading"
    assert completed.progress_percent == 100
    assert completed.reading_status == "completed"
    assert live is False and warnings == []


def test_accuracy_percentages_do_not_update_reading_progress():
    profile, goal, result, book = _context()
    for message in ("训练准确率100%是不是说明泛化很好？", "Does 100% training accuracy imply good generalization?", "概率百分之80是什么意思？"):
        reply, _, _ = generate_mentor_response(message, profile=profile, goal=goal, result=result,
            stage_number=1, book=book, progress_percent=15, history=[], provider=None)
        assert reply.progress_percent == -1 and reply.reading_status == "unchanged"
    for message, expected in (("我读到40%，但没看懂", 40), ("I am 45% through this book", 45), ("阅读进度80%", 80)):
        reply, _, _ = generate_mentor_response(message, profile=profile, goal=goal, result=result,
            stage_number=1, book=book, progress_percent=15, history=[], provider=None)
        assert reply.progress_percent == expected


def test_mentor_reply_does_not_repeat_structured_next_step() -> None:
    english = _trim_mentor_reply(
        "The body and environment form a perception-action loop. "
        "Next step: Compare this with a traditional pipeline.",
        chinese=False,
    )
    chinese = _trim_mentor_reply(
        "身体与环境共同形成感知—行动回路。下一步：画出这个回路。",
        chinese=True,
    )

    assert english == "The body and environment form a perception-action loop."
    assert chinese == "身体与环境共同形成感知—行动回路。"


def test_local_mentor_does_not_mark_negated_completion_as_complete() -> None:
    profile, goal, result, book = _context()
    english, _, _ = generate_mentor_response(
        "I have not finished this stage",
        profile=profile,
        goal=goal,
        result=result,
        stage_number=1,
        book=book,
        progress_percent=45,
        history=[],
        provider=None,
    )
    chinese_goal = goal.model_copy(update={"interface_language": "zh"})
    chinese, _, _ = generate_mentor_response(
        "我还没读完",
        profile=profile,
        goal=chinese_goal,
        result=result,
        stage_number=1,
        book=book,
        progress_percent=45,
        history=[],
        provider=None,
    )

    assert english.progress_percent == -1
    assert english.reading_status == "unchanged"
    assert chinese.progress_percent == -1
    assert chinese.reading_status == "unchanged"


def test_local_mentor_does_not_complete_a_book_when_only_a_chapter_is_done() -> None:
    profile, goal, result, book = _context()
    response, _, _ = generate_mentor_response(
        "I finished chapter 2 and have a question",
        profile=profile,
        goal=goal,
        result=result,
        stage_number=1,
        book=book,
        progress_percent=30,
        history=[],
        provider=None,
    )

    assert response.intent == "question"
    assert response.progress_percent == -1
    assert response.reading_status == "unchanged"


def test_local_mentor_extracts_weekly_hours_for_replanning() -> None:
    profile, goal, result, book = _context()
    response, _, _ = generate_mentor_response(
        "Please adjust my plan; I only have 2 hours per week",
        profile=profile,
        goal=goal,
        result=result,
        stage_number=1,
        book=book,
        progress_percent=30,
        history=[],
        provider=None,
    )

    assert response.intent == "replan"
    assert response.should_replan is True
    assert response.revised_hours_per_week == 2


def test_local_mentor_fallback_limits_replacement_to_explicit_request() -> None:
    profile, goal, result, book = _context()
    question, _, _ = generate_mentor_response(
        "Why is this chapter difficult?",
        profile=profile,
        goal=goal,
        result=result,
        stage_number=1,
        book=book,
        progress_percent=20,
        history=[],
        provider=None,
    )
    replacement, _, _ = generate_mentor_response(
        "This is too difficult; replace it with another book",
        profile=profile,
        goal=goal,
        result=result,
        stage_number=1,
        book=book,
        progress_percent=20,
        history=[],
        provider=None,
    )

    assert question.intent == "question"
    assert question.replace_book is False
    assert replacement.intent == "replace_book"
    assert replacement.replace_book is True


class FixtureProvider:
    def generate_structured(self, system, user, output_model):
        assert output_model is MentorResponse
        assert "coaching_preferences" in user
        return MentorResponse(
            reply="I updated your progress.",
            intent="progress_update",
            progress_percent=70,
            reading_status="reading",
            replace_book=False,
            replacement_reason="none",
            replacement_query="",
            should_replan=False,
            revised_hours_per_week=0,
            too_theoretical=False,
            low_mastery_concept="",
            next_step="Finish chapter four.",
            encouragement="You are making steady progress.",
            next_check_in_days=1,
        )


def test_live_mentor_receives_coaching_preferences() -> None:
    profile, goal, result, book = _context()
    response, live, warnings = generate_mentor_response(
        "I reached 70%",
        profile=profile,
        goal=goal,
        result=result,
        stage_number=1,
        book=book,
        progress_percent=45,
        history=[],
        provider=FixtureProvider(),
        mentor_preferences={
            "cadence": "three_times_weekly",
            "tone": "direct",
            "target_minutes": 30,
        },
    )

    assert live is True
    assert warnings == []
    assert response.next_step == "Finish chapter four."
    assert response.next_check_in_days == 2


def test_local_mentor_respects_coaching_tone() -> None:
    profile, goal, result, book = _context()
    supportive, _, _ = generate_mentor_response(
        "I read today",
        profile=profile,
        goal=goal,
        result=result,
        stage_number=1,
        book=book,
        progress_percent=10,
        history=[],
        provider=None,
        mentor_preferences={"tone": "supportive"},
    )
    direct, _, _ = generate_mentor_response(
        "I read today",
        profile=profile,
        goal=goal,
        result=result,
        stage_number=1,
        book=book,
        progress_percent=10,
        history=[],
        provider=None,
        mentor_preferences={"tone": "direct"},
    )

    assert supportive.encouragement != direct.encouragement
    assert "blocker" in direct.encouragement


def test_question_cannot_echo_context_progress_into_an_update() -> None:
    profile, goal, result, book = _context()
    response, live, _ = generate_mentor_response(
        "Why is sensor fusion useful?",
        profile=profile,
        goal=goal,
        result=result,
        stage_number=2,
        book=book,
        progress_percent=70,
        history=[],
        provider=FixtureProvider(),
    )

    assert live is True
    assert response.progress_percent == -1
    assert response.reading_status == "unchanged"


def test_replacement_changes_only_the_requested_stage(monkeypatch) -> None:
    profile, goal, result, _ = _context()
    original_ids = [stage.books[0] for stage in result.reading_path.stages]
    alternative = result.selected_books[0].model_copy(
        update={
            "canonical_id": "verified-stage-one-alternative",
            "title": "Embodied Cognition: A Practical Introduction",
            "search_roles": ["Conceptual Foundation"],
        }
    )
    monkeypatch.setattr(
        "src.mentor.search_live_candidates", lambda goal, settings: ([alternative], [])
    )
    monkeypatch.setattr("src.mentor.load_fallback_candidates", lambda goal: [])

    replacement = find_stage_replacement(
        result,
        goal,
        profile,
        Settings(),
        stage_number=1,
        reason="too_difficult",
    )
    updated_ids = [stage.books[0] for stage in replacement.result.reading_path.stages]

    assert updated_ids[0] == alternative.canonical_id
    assert updated_ids[1:] == original_ids[1:]
