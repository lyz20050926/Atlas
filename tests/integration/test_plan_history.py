from __future__ import annotations

import pytest

from src.database import AtlasDatabase
from src.models import (
    BookCandidate,
    LearningGoal,
    ReadingPath,
    ReadingStage,
    RecommendationResult,
    UserProfile,
)


def fixture_plan(language: str, version: int = 1) -> tuple:
    profile = UserProfile(user_id='history-test', education_level='undergraduate', interface_language=language)
    goal = LearningGoal(topic=f'Topic {version}', purpose='Learn safely', duration_weeks=6,
                        hours_per_week=version + 1, interface_language=language)
    book = BookCandidate(canonical_id=f'book-{version}', title=f'Book {version}', authors=['Author'])
    path = ReadingPath(path_id=f'path-{language}', user_id=profile.user_id, version=version, total_weeks=6,
                       total_estimated_hours=5, constraints_satisfied=True,
                       stages=[ReadingStage(stage_number=1, title=book.title, books=[book.canonical_id],
                                            learning_objective=f'Learn {version}', estimated_hours=5)])
    result = RecommendationResult(data_mode='cached_demo', concepts=[], candidates=[book],
                                  selected_books=[book], assessments=[], reading_path=path)
    return profile, goal, result


@pytest.mark.parametrize('language', ['en', 'zh'])
def test_dismiss_followup_preserves_report_and_other_path(tmp_path, language):
    db = AtlasDatabase(tmp_path / 'dismiss.db')
    profile, goal, original = fixture_plan(language)
    db.save_user(profile, goal, language)
    db.save_recommendation(profile.user_id, original, language)
    db.save_reading_progress(profile.user_id, 'book-1', 30, 'reading', language=language)
    report = {'book_id': 'book-1', 'progress_percent': 30, 'note': 'A saved reflection'}
    db.save_mentor_settings(profile.user_id, {'pending_session_followup': report, 'last_reading_session': report,
                                            'quick_question_history': [{'question': 'Already seen?'}]}, language=language)
    _, new_goal, changed = fixture_plan(language, 2)
    db.save_user(profile, new_goal, language)
    db.save_recommendation(profile.user_id, changed, language)
    db.save_mentor_settings(profile.user_id, {'pending_session_followup': {'book_id': 'book-2'}}, language=language)
    db.dismiss_reading_followup(profile.user_id, language=language, path=original.reading_path)
    old = db.load_mentor_settings(profile.user_id, language=language, path=original.reading_path)
    assert 'pending_session_followup' not in old
    assert old['last_reading_session'] == report
    assert old['quick_question_history'] == [{'question': 'Already seen?'}]
    assert db.load_mentor_settings(profile.user_id, language=language)['pending_session_followup']['book_id'] == 'book-2'
    assert db.load_reading_progress(profile.user_id, language)['book-1']['progress_percent'] == 30


@pytest.mark.parametrize('language', ['en', 'zh'])
def test_preview_and_activation_preserve_progress_and_exact_context(tmp_path, language):
    db = AtlasDatabase(tmp_path / 'history.db')
    profile, goal, original = fixture_plan(language)
    db.save_user(profile, goal, language)
    db.save_recommendation(profile.user_id, original, language)
    first_id = db.snapshot_id(original)
    db.save_reading_progress(profile.user_id, 'book-1', 40, 'reading', language=language)
    db.save_mentor_message(profile.user_id, 'path', 'user', 'Original discussion', language=language)
    db.save_mentor_settings(profile.user_id, {'next_step': 'Original task', 'mastery_by_context': {'first': []}}, language=language)
    _, changed_goal, changed = fixture_plan(language, 2)
    db.save_user(profile, changed_goal, language)
    db.save_recommendation(profile.user_id, changed, language)
    db.save_mentor_message(profile.user_id, 'path', 'user', 'New discussion', language=language)
    db.save_mentor_settings(profile.user_id, {'next_step': 'New task'}, language=language)
    before = db.load_reading_progress(profile.user_id, language)
    entries = db.list_plan_snapshots(profile.user_id, language)
    old = next(item for item in entries if item['snapshot_id'] == first_id)
    assert old['goal'] == goal
    assert old['result'] == original
    assert old['restorable']
    assert len(entries) == 2
    assert db.load_recommendation(profile.user_id, language) == changed
    assert db.load_user(profile.user_id, language)[1] == changed_goal
    assert db.load_reading_progress(profile.user_id, language) == before
    assert db.load_mentor_settings(profile.user_id, language=language, path=original.reading_path)['next_step'] == 'Original task'
    db.activate_plan_snapshot(profile.user_id, language, first_id)
    assert db.load_recommendation(profile.user_id, language) == original
    assert db.load_user(profile.user_id, language)[1] == goal
    assert db.load_reading_progress(profile.user_id, language) == before
    assert [m['content'] for m in db.load_mentor_messages(profile.user_id, 'path', language=language)] == ['Original discussion']
    assert db.load_mentor_settings(profile.user_id, language=language)['next_step'] == 'Original task'
    db.activate_plan_snapshot(profile.user_id, language, db.snapshot_id(changed))
    assert db.load_mentor_settings(profile.user_id, language=language)['next_step'] == 'New task'
    assert len(db.list_plan_snapshots(profile.user_id, language)) == 2
    other = 'zh' if language == 'en' else 'en'
    assert db.list_plan_snapshots(profile.user_id, other) == []
    with pytest.raises(ValueError):
        db.activate_plan_snapshot(profile.user_id, other, first_id)
    with pytest.raises(ValueError):
        db.activate_plan_snapshot('someone-else', language, first_id)


def test_legacy_outline_is_retained_but_never_restored_with_wrong_books(tmp_path):
    db = AtlasDatabase(tmp_path / 'history.db')
    profile, _, old = fixture_plan('en')
    db.save_path(old.reading_path)
    _, goal, current = fixture_plan('en', 2)
    db.save_user(profile, goal, 'en')
    db.save_recommendation(profile.user_id, current, 'en')
    entries = db.list_plan_snapshots(profile.user_id, 'en')
    legacy = next(item for item in entries if not item['restorable'])
    assert legacy['path'] == old.reading_path
    assert legacy['result'] is None
    with pytest.raises(ValueError):
        db.activate_plan_snapshot(profile.user_id, 'en', legacy['snapshot_id'])
    assert db.load_recommendation(profile.user_id, 'en') == current


def test_reediting_restored_version_does_not_overwrite_existing_history(tmp_path):
    db = AtlasDatabase(tmp_path / 'history.db')
    profile, goal, original = fixture_plan('en')
    db.save_user(profile, goal, 'en')
    db.save_recommendation(profile.user_id, original, 'en')
    _, _, second = fixture_plan('en', 2)
    db.save_recommendation(profile.user_id, second, 'en')
    db.activate_plan_snapshot(profile.user_id, 'en', db.snapshot_id(original))
    branch = second.model_copy(deep=True)
    branch.reading_path.stages[0].learning_objective = 'A different revision'
    db.save_recommendation(profile.user_id, branch, 'en')
    entries = db.list_plan_snapshots(profile.user_id, 'en')
    assert len(entries) == 3
    assert len({item['snapshot_id'] for item in entries}) == 3


@pytest.mark.parametrize('language', ['zh', 'en'])
@pytest.mark.parametrize('score', [.5, None])
def test_history_preview_renders_without_mutation(tmp_path, language, score):
    from streamlit.testing.v1 import AppTest

    db = AtlasDatabase(tmp_path / 'history.db')
    profile, goal, first = fixture_plan(language)
    db.save_user(profile, goal, language)
    db.save_recommendation(profile.user_id, first, language)
    db.save_mentor_message(profile.user_id, 'path', 'user', 'Saved discussion', language=language)
    db.save_mentor_message(profile.user_id, 'book:book-1', 'assistant', 'Saved answer', language=language)
    db.save_mentor_settings(profile.user_id, {'quick_check_history': [dict(book_title='Book 1', question='Question', answer='Answer', score=score)]}, language=language)
    _, _, second = fixture_plan(language, 2)
    db.save_recommendation(profile.user_id, second, language)
    script = f'''
import streamlit as st
from src.database import AtlasDatabase
from src.plan_history import render_plan_history
db = AtlasDatabase({str(db.path)!r})
if not render_plan_history(db, 'history-test', {language!r}):
    st.write('Active plan')
'''
    app = AppTest.from_string(script)
    app.query_params['preview_plan'] = db.snapshot_id(first)
    app.run(timeout=20)
    assert not app.exception
    assert db.load_recommendation(profile.user_id, language) == second
    assert any('v1' in heading.value for heading in app.subheader)
    assert any('Saved discussion' in text.value for text in app.markdown)
    assert any('Saved answer' in text.value for text in app.markdown)
