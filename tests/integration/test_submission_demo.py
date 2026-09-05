from pathlib import Path
from unittest.mock import Mock

import pytest

from src.book_search import search_and_assess_book
from src.config import Settings
from src.graph import run_recommendation_graph
from src.llm.factory import create_learning_provider, create_llm_provider
from src.models import LearningGoal, UserProfile
from src.services.recommendation import search_live_candidates_with_telemetry


def demo_context(tmp_path, language):
    settings = Settings(
        _env_file=None, app_mode="demo", llm_provider="bedrock",
        bedrock_model_id="must-not-be-used", database_path=str(tmp_path / "demo.db"),
    )
    profile = UserProfile(
        user_id="submission-demo", education_level="undergraduate", major="EEE",
        background_knowledge=["Python", "Machine Learning", "Control theory"],
        interface_language=language, language_preferences=[language],
    )
    goal = LearningGoal(
        topic="具身智能" if language == "zh" else "Embodied Intelligence",
        purpose="Build an interdisciplinary foundation", duration_weeks=6, hours_per_week=4,
        preferred_difficulty="intermediate", required_perspectives=["Robotics", "Cognitive Science", "Ethics"],
        interface_language=language, book_language_preferences=[language],
    )
    return settings, profile, goal


@pytest.mark.parametrize("language", ["zh", "en"])
def test_demo_blocks_catalogues_and_model_even_with_live_config(tmp_path, monkeypatch, language):
    from src.tools.google_books import GoogleBooksClient
    from src.tools.open_library import OpenLibraryClient

    forbidden = Mock(side_effect=AssertionError("Demo must not call external services"))
    monkeypatch.setattr(GoogleBooksClient, "search", forbidden)
    monkeypatch.setattr(OpenLibraryClient, "search", forbidden)
    settings, profile, goal = demo_context(tmp_path, language)
    assert create_llm_provider(settings) is None
    assert create_learning_provider(settings) is None
    result = run_recommendation_graph(
        profile, goal, settings, allow_cached_fallback=False,
        search_function=forbidden, provider=forbidden,
    )
    assert result.data_mode == "cached_demo"
    assert len(result.reading_path.stages) == 3
    assert result.reading_path.constraints_satisfied
    books, warnings, telemetry = search_live_candidates_with_telemetry(goal, settings)
    assert not books and warnings and telemetry.network_calls == 0
    evaluation = search_and_assess_book(result.selected_books[0].title, goal, profile, settings, provider=forbidden)
    assert not evaluation.used_live_model
    assert "queried Google Books" not in evaluation.execution_trace[0]
    assert "已在 Google Books" not in evaluation.execution_trace[0]
    with pytest.raises(LookupError):
        search_and_assess_book("unavailable-book-928317", goal, profile, settings, provider=forbidden)
    forbidden.assert_not_called()


@pytest.mark.parametrize("language", ["zh", "en"])
def test_fresh_submission_demo_creates_a_path_from_explicit_example(tmp_path, monkeypatch, language):
    from streamlit.testing.v1 import AppTest

    from src import config

    settings, _, _ = demo_context(tmp_path, language)
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "app.py"), default_timeout=60)
    app.query_params.update({"ui_language": language, "user_id": "submission-demo"})
    app.run()
    assert not app.exception
    assert app.text_input(key=f"topic_{language}_submission-demo").value == ""
    assert any(("演示模式" if language == "zh" else "DEMO MODE") in item.value for item in app.info)
    app.button(key="fill_demo_goals").click().run()
    assert not app.exception
    assert app.text_input(key=f"topic_{language}_submission-demo").value
    submit = "生成学习路径" if language == "zh" else "Create a source-verified reading path"
    next(item for item in app.button if item.label == submit).click().run()
    assert not app.exception
    assert app.session_state["recommendation"].data_mode == "cached_demo"
    assert len(app.session_state["recommendation"].selected_books) == 3
