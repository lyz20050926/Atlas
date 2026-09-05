from __future__ import annotations

import sqlite3

import pytest

from src.database import AtlasDatabase
from src.graph import run_recommendation_graph
from src.models import LearningGoal, UserProfile
from src.replanning import replan_path
from src.services.recommendation import (
    _build_path,
    _select_complementary,
    build_concept_requirements,
    load_chinese_demo_candidates,
    load_demo_candidates,
)


def test_sqlite_round_trip_keeps_path_versions(tmp_path) -> None:
    database = AtlasDatabase(tmp_path / "atlas.db")
    profile = UserProfile(
        user_id="persisted",
        education_level="undergraduate",
        major="EEE",
        background_knowledge=["Python"],
        interests=["Robotics", "Ethics"],
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
    books = load_demo_candidates()
    selected, assessments, _ = _select_complementary(books, goal, profile)
    path = _build_path(selected, assessments, build_concept_requirements(goal, profile), goal, profile)
    revised, revision = replan_path(path, goal, 2, True, "enactivism")
    database.save_user(profile, goal)
    database.save_path(path)
    database.save_path(revised)
    database.save_revision(path.path_id, revision)
    loaded = database.load_user(profile.user_id)
    assert loaded is not None and loaded[0].major == "EEE"
    versions = database.load_paths(path.path_id)
    assert [item.version for item in versions] == [1, 2]
    assert versions[1].total_estimated_hours <= 12


def test_saved_recommendation_can_restore_demo(tmp_path) -> None:
    database = AtlasDatabase(tmp_path / "atlas.db")
    profile = UserProfile(user_id="restore", education_level="undergraduate")
    goal = LearningGoal(
        topic="Embodied Intelligence",
        purpose="Learn",
        duration_weeks=6,
        hours_per_week=4,
        required_perspectives=["Robotics", "Cognitive Science", "Ethics"],
        preferred_difficulty="intermediate",
        desired_balance="balanced",
    )

    def fixture_search(goal, settings):
        return load_demo_candidates(), []

    from src.config import Settings

    result = run_recommendation_graph(profile, goal, Settings(), search_function=fixture_search)
    database.save_user(profile, goal)
    database.save_recommendation(profile.user_id, result)
    loaded = database.load_recommendation(profile.user_id)
    assert loaded is not None
    assert loaded.reading_path.path_id == result.reading_path.path_id


def test_api_cache_round_trip_and_expiry(tmp_path) -> None:
    database = AtlasDatabase(tmp_path / "atlas.db")
    payload = [{"title": "A verified API result", "source": "Google Books"}]

    database.save_api_cache("query-key", payload, "Google Books")

    assert database.load_api_cache("query-key", max_age_hours=24) == payload
    with sqlite3.connect(database.path) as connection:
        connection.execute(
            "UPDATE api_cache SET retrieved_at='2000-01-01 00:00:00' WHERE cache_key=?",
            ("query-key",),
        )
    assert database.load_api_cache("query-key", max_age_hours=24) is None


def test_same_user_keeps_english_and_chinese_journeys_independent(tmp_path) -> None:
    database = AtlasDatabase(tmp_path / "atlas.db")

    def fixture_search(goal, settings):
        candidates = load_chinese_demo_candidates() if goal.interface_language == "zh" else load_demo_candidates()
        return candidates, []

    from src.config import Settings

    english_profile = UserProfile(user_id="bilingual", education_level="undergraduate", interface_language="en")
    english_goal = LearningGoal(
        topic="Embodied Intelligence",
        purpose="Learn the foundations",
        duration_weeks=6,
        hours_per_week=4,
        required_perspectives=["Robotics", "Cognitive Science", "Ethics"],
        interface_language="en",
    )
    chinese_profile = english_profile.model_copy(update={"interface_language": "zh"})
    chinese_goal = english_goal.model_copy(
        update={
            "topic": "具身智能",
            "purpose": "建立跨学科基础",
            "required_perspectives": ["机器人学", "认知科学", "伦理学"],
            "interface_language": "zh",
            "book_language_preferences": ["zh"],
        }
    )
    english_result = run_recommendation_graph(
        english_profile, english_goal, Settings(), search_function=fixture_search
    )
    chinese_result = run_recommendation_graph(
        chinese_profile, chinese_goal, Settings(), search_function=fixture_search
    )

    database.save_user(english_profile, english_goal, "en")
    database.save_recommendation("bilingual", english_result, "en")
    database.save_user(chinese_profile, chinese_goal, "zh")
    database.save_recommendation("bilingual", chinese_result, "zh")

    loaded_english = database.load_user("bilingual", "en")
    loaded_chinese = database.load_user("bilingual", "zh")
    assert loaded_english is not None and loaded_english[1].topic == "Embodied Intelligence"
    assert loaded_chinese is not None and loaded_chinese[1].topic == "具身智能"
    assert database.load_recommendation("bilingual", "en").reading_path.path_id == english_result.reading_path.path_id
    assert database.load_recommendation("bilingual", "zh").reading_path.path_id == chinese_result.reading_path.path_id


def test_progress_and_feedback_are_saved_per_language_workspace(tmp_path) -> None:
    database = AtlasDatabase(tmp_path / "atlas.db")

    database.save_reading_progress(
        "reader",
        "book-en",
        45,
        "reading",
        is_current=True,
        language="en",
    )
    database.save_reading_progress(
        "reader",
        "book-zh",
        100,
        "completed",
        is_current=True,
        language="zh",
    )
    database.save_book_feedback(
        "reader",
        "book-zh",
        2,
        "too_difficult",
        "希望换一本更适合入门的书",
        language="zh",
    )

    english = database.load_reading_progress("reader", "en")
    chinese = database.load_reading_progress("reader", "zh")
    assert english["book-en"]["progress_percent"] == 45
    assert "book-zh" not in english
    assert chinese["book-zh"]["status"] == "completed"
    assert chinese["book-zh"]["is_current"] is True
    feedback = database.load_book_feedback("reader", "zh")
    assert feedback[0]["reason"] == "too_difficult"
    assert feedback[0]["note"] == "希望换一本更适合入门的书"


def test_mentor_conversations_and_preferences_are_language_and_scope_isolated(tmp_path) -> None:
    database = AtlasDatabase(tmp_path / "atlas.db")
    database.save_mentor_message(
        "reader",
        "path",
        "user",
        "I am 40% done",
        language="en",
    )
    database.save_mentor_message(
        "reader",
        "book:zh-book",
        "assistant",
        "我会只替换这一本。",
        {"next_step": "确认替代书"},
        language="zh",
    )
    database.save_mentor_settings(
        "reader",
        {"cadence": "daily", "tone": "supportive", "target_minutes": 25},
        language="zh",
    )

    assert database.load_mentor_messages("reader", "path", language="zh") == []
    english = database.load_mentor_messages("reader", "path", language="en")
    chinese = database.load_mentor_messages("reader", "book:zh-book", language="zh")
    assert english[0]["content"] == "I am 40% done"
    assert chinese[0]["action"]["next_step"] == "确认替代书"
    assert database.load_mentor_settings("reader", language="en") == {}
    assert database.load_mentor_settings("reader", language="zh")["target_minutes"] == 25


@pytest.mark.parametrize("language", ["en", "zh"])
def test_path_coach_excludes_legacy_and_previous_plan_state(tmp_path, language) -> None:
    from src.config import Settings

    database = AtlasDatabase(tmp_path / "atlas.db")
    profile = UserProfile(user_id="reader", education_level="undergraduate")
    goal = LearningGoal(topic="Embodied Intelligence", purpose="Learn", duration_weeks=6, hours_per_week=4)
    result = run_recommendation_graph(
        profile, goal, Settings(), search_function=lambda *_: (load_demo_candidates(), []),
    )
    # Existing installations have unscoped history and timers from an unknown old path.
    database.save_mentor_message("reader", "path", "user", "Old Python book report", language=language)
    database.save_mentor_settings("reader", {
        "tone": "supportive", "target_minutes": 25,
        "next_step": "Read the old Python book",
        "pending_session_followup": {"book_id": "old"},
        "active_reading_session": {"book_id": "old"},
    }, language=language)
    database.save_recommendation("reader", result, language)
    assert database.load_mentor_messages("reader", "path", language=language) == []
    assert database.load_mentor_settings("reader", language=language) == {
        "tone": "supportive", "target_minutes": 25,
    }
    database.save_mentor_message("reader", "path", "user", "Current book question", language=language)
    database.save_mentor_settings("reader", {
        "tone": "concise", "next_step": "Current book task",
        "active_reading_session": {"book_id": "current"},
    }, language=language)
    # Harmless re-saving or restarting preserves the active conversation and timer.
    database.save_recommendation("reader", result, language)
    reopened = AtlasDatabase(database.path)
    assert reopened.load_mentor_messages("reader", "path", language=language)[0]["content"] == "Current book question"
    assert reopened.load_mentor_settings("reader", language=language)["next_step"] == "Current book task"
    revised = result.model_copy(deep=True)
    revised.reading_path.version += 1
    revised.reading_path.stages[0].books = ["new-matlab-book"]
    reopened.save_recommendation("reader", revised, language)
    assert reopened.load_mentor_messages("reader", "path", language=language) == []
    assert reopened.load_mentor_settings("reader", language=language) == {
        "tone": "concise", "target_minutes": 25,
    }
    history = reopened.load_mentor_messages("reader", "path", language=language, archived=True)
    assert [m["content"] for m in history] == ["Old Python book report", "Current book question"]
    other_language = "en" if language == "zh" else "zh"
    assert reopened.load_mentor_messages("reader", "path", language=other_language, archived=True) == []
    assert reopened.load_mentor_settings("reader", language=other_language) == {}
    # Returning to an earlier saved path retrieves its own state without losing history.
    reopened.save_recommendation("reader", result, language)
    assert reopened.load_mentor_settings("reader", language=language)["next_step"] == "Current book task"
