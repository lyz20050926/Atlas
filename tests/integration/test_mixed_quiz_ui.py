from pathlib import Path
from unittest.mock import Mock

import pytest

from src.config import Settings
from src.database import AtlasDatabase
from src.diagnostic import diagnostic_scope_key
from src.models import (
    BookCandidate,
    LearningGoal,
    ReadingPath,
    ReadingStage,
    RecommendationResult,
    UserProfile,
)
from src.services.scoring import SCORING_VERSION


@pytest.mark.parametrize("language", ["zh", "en"])
def test_mixed_quiz_is_unanswered_then_saved_and_identical_regeneration_keeps_feedback(tmp_path, monkeypatch, language):
    import httpx
    from streamlit.testing.v1 import AppTest

    from src import config

    database = AtlasDatabase(tmp_path / "quiz-ui.db")
    profile = UserProfile(user_id="quiz-reader", education_level="undergraduate", major="Design", interface_language=language)
    goal = LearningGoal(topic="心理学" if language == "zh" else "Psychology", purpose="Understand memory",
                        focus_details="Cognitive psychology: attention and working memory", duration_weeks=6,
                        hours_per_week=4, interface_language=language)
    book = BookCandidate(canonical_id="memory-book", title="Working memory", authors=["Author"], language=language)
    stage = ReadingStage(stage_number=1, title="Memory", books=[book.canonical_id],
                         learning_objective="Understand working memory", estimated_hours=4)
    result = RecommendationResult(scoring_version=SCORING_VERSION, data_mode="cached_demo", concepts=[],
        candidates=[book], selected_books=[book], assessments=[], reading_path=ReadingPath(
            path_id="quiz-path", user_id=profile.user_id, version=1, total_weeks=6,
            total_estimated_hours=4, constraints_satisfied=True, stages=[stage]))
    database.save_user(profile, goal, language)
    database.save_recommendation(profile.user_id, result, language)
    settings = Settings(_env_file=None, llm_provider="mock", database_path=str(database.path), google_books_api_key="")
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    network = Mock(side_effect=AssertionError("Offline practice must not make external calls"))
    monkeypatch.setattr(httpx.Client, "send", network)
    path = str(Path(__file__).resolve().parents[2] / "app.py")
    app = AppTest.from_file(path, default_timeout=45)
    app.query_params.update({"ui_language": language, "user_id": profile.user_id})
    app.run()
    assert not app.exception
    generate_label = "生成 3 道练习" if language == "zh" else "Create 3 practice questions"
    next(b for b in app.button if b.label == generate_label).click()
    app.run()
    assert not app.exception
    scope = diagnostic_scope_key(goal, profile, book, stage)
    settings_record = database.load_mentor_settings(profile.user_id, language=language)
    record = settings_record["question_bank"][scope]
    assert [q["question_type"] for q in record["questions"]] == ["single_choice", "true_false", "short_answer"]
    prefix = f"diag_{language}_{profile.user_id}_{scope}_{record['revision']}"
    assert app.radio(key=f"{prefix}_0").value is None
    assert app.radio(key=f"{prefix}_1").value is None
    app.radio(key=f"{prefix}_0").set_value(record["questions"][0]["correct_answer"])
    wrong = next(o for o in record["questions"][1]["options"] if o != record["questions"][1]["correct_answer"])
    app.radio(key=f"{prefix}_1").set_value(wrong)
    submit = "提交答案，查看点评" if language == "zh" else "Check answers and get feedback"
    next(b for b in app.button if b.label == submit).click()
    app.run()
    assert not app.exception
    saved = database.load_mentor_settings(profile.user_id, language=language)["answer_reviews"][scope]
    assert [r["verdict"] for r in saved["reviews"]] == ["sound", "misconception", "insufficient"]
    assert saved["answers"] == [record["questions"][0]["correct_answer"], wrong, ""]
    # Restarting the page restores exactly this revision's submitted answers.
    app = AppTest.from_file(path, default_timeout=45)
    app.query_params.update({"ui_language": language, "user_id": profile.user_id})
    app.run()
    assert app.radio(key=f"{prefix}_0").value == saved["answers"][0]
    assert app.radio(key=f"{prefix}_1").value == wrong
    again = "换一组练习" if language == "zh" else "Try a new set"
    next(b for b in app.button if b.label == again).click()
    app.run()
    assert not app.exception
    after = database.load_mentor_settings(profile.user_id, language=language)
    assert after["question_bank"][scope]["revision"] == record["revision"]
    assert after["answer_reviews"][scope] == saved
    assert app.session_state["mastery"]
    # A new plan version with the same book must not retain session-only
    # assessments which disappear on refresh and are absent from that version.
    new_result = result.model_copy(deep=True)
    new_result.reading_path.version = 2
    database.save_recommendation(profile.user_id, new_result, language)
    app.session_state["recommendation"] = new_result
    app.run()
    assert not app.exception
    assert app.session_state["mastery"] == []
    assert database.load_mentor_settings(profile.user_id, language=language).get("mastery_by_context", {}) == {}
    assert not network.called
