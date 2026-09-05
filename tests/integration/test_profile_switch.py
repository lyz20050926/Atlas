from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from src.config import Settings
from src.database import AtlasDatabase
from src.models import (
    BookCandidate,
    LearningGoal,
    ReadingPath,
    ReadingStage,
    RecommendationResult,
    UserProfile,
)
from src.services.recommendation import ensure_detailed_assessments

SAVED_ID = "saved-reader"
DRAFT_ID = "learner-0123456789ab"
STALE_NAVIGATION = {
    "book_query": "Previous book",
    "stage_view": "9",
    "preview_plan": "previous-plan",
    "history": "1",
    "new_profile": "1",
    "return_profile": "previous-reader",
    "return_language": "en",
}


def saved_plan(database: AtlasDatabase, language: str) -> tuple:
    profile = UserProfile(
        user_id=SAVED_ID,
        education_level="undergraduate",
        major="Computer Science",
        interface_language=language,
    )
    goal = LearningGoal(
        topic="Machine learning",
        purpose="Understand reliable predictions",
        duration_weeks=6,
        hours_per_week=4,
        interface_language=language,
    )
    book = BookCandidate(canonical_id="saved-book", title="Saved book", authors=["Author"])
    path = ReadingPath(
        path_id=f"saved-path-{language}",
        user_id=SAVED_ID,
        version=1,
        total_weeks=6,
        total_estimated_hours=5,
        constraints_satisfied=True,
        stages=[ReadingStage(
            stage_number=1,
            title="Foundational concepts",
            books=[book.canonical_id],
            learning_objective="Understand reliable predictions",
            estimated_hours=5,
        )],
    )
    result = RecommendationResult(
        data_mode="cached_demo", concepts=[], candidates=[book], selected_books=[book],
        assessments=ensure_detailed_assessments([book], [], goal, profile), reading_path=path,
    )
    database.save_user(profile, goal, language)
    database.save_recommendation(SAVED_ID, result, language)
    database.save_reading_progress(SAVED_ID, book.canonical_id, 35, "reading", language=language)
    database.save_mentor_message(SAVED_ID, "path", "user", "Keep my reflection", language=language)
    database.save_mentor_message(
        SAVED_ID, "book:saved-book", "assistant", "Keep my book discussion", language=language,
    )
    return profile, goal, result


def app_for_profile(tmp_path, monkeypatch, language: str, user_id: str):
    import httpx
    from streamlit.testing.v1 import AppTest

    from src import config, graph

    database = AtlasDatabase(tmp_path / "profile-switch.db")
    profile, goal, result = saved_plan(database, language)
    settings = Settings(
        _env_file=None, llm_provider="mock", database_path=str(database.path),
        google_books_api_key="",
    )
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    # Loading a profile is local navigation, not a new recommendation request.
    network_guard = Mock(side_effect=AssertionError("Profile loading must not run recommendations"))
    monkeypatch.setattr(graph, "run_recommendation_graph", network_guard)
    monkeypatch.setattr(httpx.Client, "send", network_guard)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "app.py"), default_timeout=45)
    app.query_params.update({"ui_language": language, "user_id": user_id})
    app.run()
    assert not app.exception
    return app, database, profile, goal, result, network_guard


def saved_records(database: AtlasDatabase, language: str) -> tuple:
    return (
        database.load_user(SAVED_ID, language),
        database.load_reading_progress(SAVED_ID, language),
        database.load_mentor_messages(SAVED_ID, "path", language=language),
        database.load_mentor_messages(SAVED_ID, "book:saved-book", language=language),
    )


@pytest.mark.parametrize("language", ["zh", "en"])
def test_one_load_click_updates_every_profile_surface_without_manual_refresh(tmp_path, monkeypatch, language):
    app, database, profile, goal, result, network_guard = app_for_profile(
        tmp_path, monkeypatch, language, DRAFT_ID,
    )
    before = saved_records(database, language)
    # Simulate remnants of a draft, a book assessment and a history view.
    app.query_params.update(STALE_NAVIGATION)
    app.text_input(key=f"saved_user_id_{language}_{DRAFT_ID}").set_value(f"  {SAVED_ID}  ")
    load_label = "加载已保存路径" if language == "zh" else "Load saved journey"
    next(button for button in app.button if button.label == load_label).click()
    app.run()

    assert not app.exception
    assert app.query_params["user_id"] == [SAVED_ID]
    assert app.query_params["ui_language"] == [language]
    assert not set(STALE_NAVIGATION).intersection(app.query_params)
    assert app.session_state["profile"] == profile
    assert app.session_state["goal"] == goal
    assert app.session_state["recommendation"].reading_path == result.reading_path
    assert app.session_state["_rendered_workspace_key"] == f"{language}::{SAVED_ID}"

    sidebar = "\n".join(item.value for item in app.sidebar.markdown)
    assert f"<strong>{SAVED_ID}</strong>" in sidebar
    assert f"user_id={SAVED_ID}&amp;history=1" in sidebar
    assert DRAFT_ID not in sidebar
    content = "\n".join(item.value for item in app.markdown)
    aria_label = "当前用户：" if language == "zh" else "Current profile: "
    assert f'aria-label="{aria_label}{SAVED_ID}"' in content
    assert f"{aria_label}{DRAFT_ID}" not in content
    assert app.text_input(key=f"goal_user_id_{language}_{SAVED_ID}").value == SAVED_ID
    assert app.text_input(key=f"topic_{language}_{SAVED_ID}").value == goal.topic
    assert app.text_input(key=f"saved_user_id_{language}_{SAVED_ID}").value == SAVED_ID
    assert app.text_input(key=f"atlas_search_input_{language}_{SAVED_ID}").value == ""
    assert not any(item.key == f"goal_user_id_{language}_{DRAFT_ID}" for item in app.text_input)

    notice = "已切换到学习档案" if language == "zh" else "Switched to learning profile"
    assert sum(notice in item.value for item in app.success) == 1
    assert saved_records(database, language) == before
    assert database.load_user(DRAFT_ID, language) is None
    network_guard.assert_not_called()
    app.run()
    assert not app.exception
    assert not any(notice in item.value for item in app.success)
    assert saved_records(database, language) == before


@pytest.mark.parametrize("language", ["zh", "en"])
def test_missing_profile_keeps_current_profile_and_saved_records(tmp_path, monkeypatch, language):
    app, database, profile, goal, result, network_guard = app_for_profile(
        tmp_path, monkeypatch, language, SAVED_ID,
    )
    before = saved_records(database, language)
    app.text_input(key=f"saved_user_id_{language}_{SAVED_ID}").set_value("not-a-saved-profile")
    load_label = "加载已保存路径" if language == "zh" else "Load saved journey"
    next(button for button in app.button if button.label == load_label).click()
    app.run()

    assert not app.exception
    assert app.query_params["user_id"] == [SAVED_ID]
    assert app.session_state["profile"] == profile
    assert app.session_state["goal"] == goal
    assert app.session_state["recommendation"].reading_path == result.reading_path
    warning = "未找到该用户" if language == "zh" else "No saved journey exists"
    assert any(warning in item.value for item in app.warning)
    sidebar = "\n".join(item.value for item in app.sidebar.markdown)
    assert f"<strong>{SAVED_ID}</strong>" in sidebar
    assert saved_records(database, language) == before
    assert database.load_user("not-a-saved-profile", language) is None
    network_guard.assert_not_called()
