from pathlib import Path
from unittest.mock import Mock

import pytest

from src.config import Settings
from src.database import AtlasDatabase
from src.models import BookCandidate, ReadingPath, ReadingStage, RecommendationResult
from src.services.scoring import SCORING_VERSION


@pytest.mark.parametrize("language,details", [
    ("zh", "认知心理学：注意力与工作记忆。想设计简单实验，不想读心灵鸡汤。"),
    ("en", "Cognitive psychology: attention and working memory. I'd like practical experiments, not self-help books."),
])
def test_free_form_focus_creates_reloads_and_edits_without_forcing_preset_disciplines(tmp_path, monkeypatch, language, details):
    import httpx
    from streamlit.testing.v1 import AppTest

    from src import config, graph

    profile_id = "focus-reader"
    database = AtlasDatabase(tmp_path / "learning-focus.db")
    settings = Settings(_env_file=None, llm_provider="mock", database_path=str(database.path), google_books_api_key="")
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    monkeypatch.setattr(httpx.Client, "send", Mock(side_effect=AssertionError("UI regression must not use external services")))
    captured_goals = []

    def recommend(profile, learning_goal, *_args, **_kwargs):
        captured_goals.append(learning_goal)
        book = BookCandidate(canonical_id="memory-book", title="Working memory", authors=["Author"], language=language)
        return RecommendationResult(
            scoring_version=SCORING_VERSION, data_mode="cached_demo", concepts=[], candidates=[book], selected_books=[book],
            assessments=[], reading_path=ReadingPath(
                path_id="focus-path", user_id=profile.user_id, version=len(captured_goals), total_weeks=6,
                total_estimated_hours=4, constraints_satisfied=True,
                stages=[ReadingStage(stage_number=1, title="Memory", books=[book.canonical_id],
                                     learning_objective="Understand working memory", estimated_hours=4)],
            ),
        )

    monkeypatch.setattr(graph, "run_recommendation_graph", recommend)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "app.py"), default_timeout=45)
    app.query_params.update({"ui_language": language, "user_id": profile_id, "new_profile": "1"})
    app.run()
    assert not app.exception
    assert app.text_area(key=f"focus_details_{language}_{profile_id}").value == ""
    app.text_input(key=f"topic_{language}_{profile_id}").set_value("心理学" if language == "zh" else "Psychology")
    app.text_input(key=f"major_{language}_{profile_id}").set_value("设计" if language == "zh" else "Design")
    app.text_input(key=f"purpose_{language}_{profile_id}").set_value("理解记忆机制" if language == "zh" else "Understand memory")
    app.text_area(key=f"focus_details_{language}_{profile_id}").set_value(details)
    # Leave the now-optional multiselect empty: a freely described subfield must
    # not be blocked by a fixed list that happens not to contain that subfield.
    label = "生成学习路径" if language == "zh" else "Create a source-verified reading path"
    next(button for button in app.button if button.label == label).click()
    app.run()
    assert not app.exception
    assert captured_goals and captured_goals[-1].focus_details == details
    assert captured_goals[-1].required_perspectives == []
    assert database.load_user(profile_id, language)[1].focus_details == details
    assert app.text_area(key=f"focus_details_{language}_{profile_id}").value == details

    database.save_reading_progress(profile_id, "memory-book", 35, "reading", language=language)
    saved_progress = database.load_reading_progress(profile_id, language)
    app = AppTest.from_file(str(Path(__file__).resolve().parents[2] / "app.py"), default_timeout=45)
    app.query_params.update({"ui_language": language, "user_id": profile_id})
    app.run()
    assert not app.exception
    assert app.text_area(key=f"focus_details_{language}_{profile_id}").value == details
    updated_details = "工作记忆和决策偏差" if language == "zh" else "Working memory and decision biases"
    app.text_area(key=f"focus_details_{language}_{profile_id}").set_value(updated_details)
    label = "保存更改并重新规划" if language == "zh" else "Save changes and rebuild the path"
    next(button for button in app.button if button.label == label).click()
    app.run()
    assert not app.exception
    assert captured_goals[-1].focus_details == updated_details
    assert database.load_user(profile_id, language)[1].focus_details == updated_details
    assert database.load_reading_progress(profile_id, language) == saved_progress
