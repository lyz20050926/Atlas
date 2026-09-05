from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from src.config import Settings
from src.database import AtlasDatabase
from src.models import LearningGoal, UserProfile


@pytest.mark.parametrize("language", ["zh", "en"])
def test_new_profile_is_blank_and_duplicate_name_cannot_overwrite_saved_records(
    tmp_path, monkeypatch, language: str
) -> None:
    from streamlit.testing.v1 import AppTest

    from src import config, graph

    database = AtlasDatabase(tmp_path / "profile-creation.db")
    existing_id = "existing-profile"
    draft_id = "learner-0123456789ab"
    original_profile = UserProfile(
        user_id=existing_id,
        education_level="undergraduate",
        major="Existing field",
        interface_language=language,
    )
    original_goal = LearningGoal(
        topic="Original topic",
        purpose="Original purpose",
        duration_weeks=6,
        hours_per_week=4,
        interface_language=language,
    )
    database.save_user(original_profile, original_goal, language)
    database.save_reading_progress(existing_id, "old-book", 45, "reading", language=language)
    original_progress = database.load_reading_progress(existing_id, language)
    settings = Settings(_env_file=None, llm_provider="mock", database_path=str(database.path))
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    recommendation = Mock(side_effect=AssertionError("Duplicate-name validation must run before recommendations"))
    monkeypatch.setattr(graph, "run_recommendation_graph", recommendation)

    app = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "app.py"), default_timeout=45)
    app.query_params.update({
        "ui_language": language,
        "user_id": draft_id,
        "new_profile": "1",
        "return_profile": existing_id,
        "return_language": language,
    })
    app.run()
    assert not app.exception
    for field in ("topic", "major", "purpose"):
        assert app.text_input(key=f"{field}_{language}_{draft_id}").value == ""
    assert app.text_area(key=f"background_{language}_{draft_id}").value == ""
    assert app.multiselect(key=f"perspectives_{language}_{draft_id}").value == []
    assert database.load_user(draft_id, language) is None

    app.text_input(key=f"goal_user_id_{language}_{draft_id}").set_value(existing_id)
    app.text_input(key=f"topic_{language}_{draft_id}").set_value("A different topic")
    app.text_input(key=f"major_{language}_{draft_id}").set_value("A different field")
    app.text_input(key=f"purpose_{language}_{draft_id}").set_value("A different purpose")
    app.multiselect(key=f"perspectives_{language}_{draft_id}").select(
        "计算机科学" if language == "zh" else "Computer Science"
    )
    submit_label = "生成学习路径" if language == "zh" else "Create a source-verified reading path"
    next(button for button in app.button if button.label == submit_label).click()
    app.run()
    assert not app.exception
    expected_error = "这个档案名称已经用过了" if language == "zh" else "That profile name is already in use"
    assert any(expected_error in error.value for error in app.error)
    recommendation.assert_not_called()
    assert database.load_user(existing_id, language) == (original_profile, original_goal)
    assert database.load_reading_progress(existing_id, language) == original_progress
    assert database.load_user(draft_id, language) is None
