"""Read-only history preview, separate from all active-plan mutation controls."""
from __future__ import annotations

from html import escape
from urllib.parse import urlencode

import streamlit as st

from src.database import AtlasDatabase
from src.language import reading_stage_title
from src.mentor import book_conversation_scope
from src.ui import book_cover_html, mentor_conversation_html


def history_url(user_id: str, language: str, **params: str) -> str:
    return '?' + urlencode(dict(ui_language=language, user_id=user_id, **params))


def render_plan_history(database: AtlasDatabase, user_id: str, language: str) -> bool:
    """Return True when the normal, editable application must not be rendered."""
    zh = language == 'zh'
    def tr(en: str, cn: str) -> str:
        return cn if zh else en

    preview_id = str(st.query_params.get('preview_plan', ''))
    opened = st.query_params.get('history') == '1'
    if not preview_id and not opened:
        return False
    st.markdown('''<style>
      [role="dialog"]:has(.atlas-history-confirm) {background:#fff!important;color:#0f172a;}
      .atlas-history-link {display:inline-flex;align-items:center;min-height:44px;padding:8px 16px;
        border:1px solid #dce5f2;border-radius:10px;background:#fff;text-decoration:none!important;}
      .atlas-history-link:focus-visible {outline:3px solid #2563eb;outline-offset:3px;}
    </style>''', unsafe_allow_html=True)
    entries = database.list_plan_snapshots(user_id, language)
    active = database.load_recommendation(user_id, language)
    active_id = database.snapshot_id(active) if active else ''
    base_url = history_url(user_id, language)

    if opened:
        st.markdown('''<style>
        [role="dialog"]:has(.atlas-history-drawer) {position:fixed;right:0;top:0;
          margin:0!important;height:100dvh;max-height:100dvh;width:min(460px,100vw);
          border-radius:20px 0 0 20px;overflow-y:auto;background:#fff!important;
          color:#0f172a;box-shadow:-16px 0 48px rgba(15,23,42,.16);}
        [role="dialog"]:has(.atlas-history-drawer) [data-testid="stVerticalBlockBorderWrapper"] {
          background:#f5f8fc;border-color:#dce5f2;}
        </style>''', unsafe_allow_html=True)

        def close_history() -> None:
            st.query_params.pop('history', None)

        @st.dialog(tr('Plan history', '历史方案'), on_dismiss=close_history)
        def drawer() -> None:
            st.markdown('<span class="atlas-history-drawer"></span>', unsafe_allow_html=True)
            st.caption(tr('Choose a plan to preview. Your current plan stays unchanged.',
                          '选择一个方案查看；预览不会改变当前计划。'))
            if not entries:
                st.info(tr('Your saved plans will appear here after you create a reading path.',
                           '生成阅读路径后，保存的方案会出现在这里。'))
            for item in entries:
                path = item['path']
                title = item['goal'].topic if item['goal'] else tr('Earlier plan', '早期方案')
                status = tr('Current plan', '当前方案') if item['snapshot_id'] == active_id else tr('Saved plan', '已保存')
                with st.container(border=True):
                    st.markdown(f"**{escape(title)} · v{path.version}**")
                    st.markdown(f"<p style='font-size:14px;color:#475569'>{escape(status)} · {escape(item['created_at'])} UTC</p>", unsafe_allow_html=True)
                    st.write(item['reason'] or tr('Saved reading path', '已保存的阅读路径'))
                    st.caption(tr(f'{len(path.stages)} stages · {path.total_estimated_hours:g} hours',
                                  f'{len(path.stages)} 个阶段 · {path.total_estimated_hours:g} 小时'))
                    if not item['restorable']:
                        st.caption(tr('Legacy outline · preview only', '早期记录 · 仅可查看路径摘要'))
                    if st.button(tr('View plan', '查看方案'), key=f"history_{item['snapshot_id']}", use_container_width=True):
                        st.query_params['preview_plan'] = item['snapshot_id']
                        st.query_params.pop('history', None)
                        st.rerun()
        drawer()

    if not preview_id:
        return False
    item = next((entry for entry in entries if entry['snapshot_id'] == preview_id), None)
    st.markdown(f'<a href="{escape(base_url, quote=True)}" target="_self">← {tr("Return to current plan", "返回当前方案")}</a>', unsafe_allow_html=True)
    if not item:
        st.warning(tr('This plan is unavailable in this workspace.', '当前用户或语言下没有这个方案。'))
        return True
    path, result, goal = item['path'], item['result'], item['goal']
    is_current = preview_id == active_id
    st.info(tr('Read-only plan preview — your active plan and progress are unchanged.',
               '正在查看历史方案 · 仅供预览，当前计划和阅读进度未改变。'))
    title_col, action_col = st.columns([3, 1])
    with title_col:
        st.subheader(f"{goal.topic if goal else tr('Earlier plan', '早期方案')} · v{path.version}")
        st.caption(f"{item['created_at']} UTC · {len(path.stages)} {tr('stages', '个阶段')}")
    with action_col:
        other_url = history_url(user_id, language, preview_plan=preview_id, history='1')
        st.markdown(f'<a class="atlas-history-link" target="_self" href="{escape(other_url, quote=True)}">{tr("Choose another plan", "查看其他方案")}</a>', unsafe_allow_html=True)
    if goal:
        st.write(goal.purpose)
        st.caption(tr(f'{goal.duration_weeks} weeks · {goal.hours_per_week:g} hours/week',
                      f'{goal.duration_weeks} 周 · 每周 {goal.hours_per_week:g} 小时'))
    if item['reason']:
        st.write(tr('Reason: ', '调整原因：') + item['reason'])
    if result and active and not is_current:
        old_titles = {book.canonical_id: book.title for book in result.selected_books}
        active_titles = {book.canonical_id: book.title for book in active.selected_books}
        with st.expander(tr('Compare with current plan', '与当前方案比较')):
            st.write(tr('In this plan: ', '此方案包含：') + '、'.join(old_titles.values()))
            st.write(tr('In your current plan: ', '当前方案包含：') + '、'.join(active_titles.values()))
            st.caption(tr('Stage order and reading scope are shown below.', '阶段顺序和阅读范围见下方预览。'))

    if not item['restorable']:
        st.warning(tr('This early record contains only the path outline, not its complete books and learning goal. It cannot safely be restored.',
                      '这个早期版本只保留了路径摘要，没有完整书目和当时的学习需求，因此不能直接恢复。新保存的方案支持完整预览和重新使用。'))
    elif is_current:
        st.caption(tr('This is already your current plan.', '这已经是当前正在使用的方案。'))
    else:
        @st.dialog(tr('Use this plan?', '继续使用此方案？'))
        def confirm() -> None:
            st.markdown('<span class="atlas-history-confirm"></span>', unsafe_allow_html=True)
            st.write(tr('This changes your learning goal and reading path to this saved version. Book progress stays saved; conversations and self-checks use this plan’s context.',
                        '确认后将使用这个版本的学习目标和阅读路径。书籍进度仍会保留，对话和自测回到这个方案对应的记录。'))
            st.caption(tr('Your current plan stays in history. You can return to it later.',
                          '现在的方案也会保留在历史中，之后仍可切换回来。'))
            yes, no = st.columns(2)
            if yes.button(tr('Confirm switch', '确认切换'), type='primary', use_container_width=True):
                database.activate_plan_snapshot(user_id, language, preview_id)
                for key in ('recommendation', 'profile', 'goal', 'mastery', 'mastery_context',
                            'previous_path', 'revised_path', 'plan_revision', 'plan_notice',
                            'book_search_evaluation', 'book_search_key', 'book_search_error'):
                    st.session_state.pop(key, None)
                for key in ('preview_plan', 'history', 'stage_view', 'book_query'):
                    st.query_params.pop(key, None)
                st.session_state['history_switch_notice'] = tr('Plan switched. Your reading progress has been preserved.', '已切换学习方案，原有阅读进度已保留。')
                st.rerun()
            if no.button(tr('Cancel', '取消'), use_container_width=True):
                st.rerun()
        if st.button(tr('Continue with this plan', '继续使用此方案'), type='primary'):
            confirm()

    progress = database.load_reading_progress(user_id, language)
    books = {book.canonical_id: book for book in result.selected_books} if result else {}
    assessments = {entry.canonical_id: entry for entry in result.assessments} if result else {}
    if result:
        st.caption(tr('Progress below is the latest saved progress for each book, not a historical percentage.',
                      '以下进度为各本书最近保存的进度，不是生成方案时的历史百分比。'))
    for stage in path.stages:
        with st.container(border=True):
            st.subheader(f"{tr('Stage', '阶段')} {stage.stage_number} · {reading_stage_title(stage.title, language)}")
            st.write(stage.learning_objective)
            st.caption(tr(f'Estimated reading time: {stage.estimated_hours:g} hours',
                          f'预计阅读时间：{stage.estimated_hours:g} 小时'))
            for book_id in stage.books:
                book = books.get(book_id)
                if not book:
                    st.caption(tr('Book details were not saved in this early record.', '早期记录未保存这本书的完整资料。'))
                    continue
                cover, body = st.columns([1, 4])
                with cover:
                    st.markdown(book_cover_html(book, zh), unsafe_allow_html=True)
                with body:
                    st.markdown(f'**{escape(book.title)}**')
                    st.write(' · '.join(book.authors))
                    st.progress(int(progress.get(book_id, {}).get('progress_percent', 0)) / 100)
                    st.caption(f"{int(progress.get(book_id, {}).get('progress_percent', 0))}%")
                    assessment = assessments.get(book_id)
                    if assessment:
                        st.write(assessment.recommendation_reason)
                    if book.description:
                        with st.expander(tr('Book description', '内容简介')):
                            st.write(book.description)
                messages = database.load_mentor_messages(user_id, book_conversation_scope(book), language=language, limit=100)
                with st.expander(tr('Saved conversations for this book', '这本书的已保存对话')):
                    if messages:
                        st.markdown(mentor_conversation_html(messages, is_zh=zh), unsafe_allow_html=True)
                    else:
                        st.caption(tr('No saved conversations.', '暂无已保存的对话。'))
            if stage.selected_chapters:
                st.write(tr('Reading scope: ', '阅读范围：') + ' / '.join(stage.selected_chapters))
            if stage.guiding_questions:
                with st.expander(tr('Guiding questions', '阅读思考题')):
                    for question in stage.guiding_questions:
                        st.write(question)
    if result:
        with st.expander(tr('Learning coach conversations for this plan', '这个方案的学习陪练记录')):
            messages = database.load_mentor_messages(user_id, database.mentor_scope_for_path(path), language=language, limit=100)
            if messages:
                st.markdown(mentor_conversation_html(messages, is_zh=zh), unsafe_allow_html=True)
            else:
                st.caption(tr('No conversations saved for this plan.', '暂无明确归属于这个方案的对话记录。'))
        saved_settings = database.load_mentor_settings(user_id, language=language, path=path)
        with st.expander(tr('Self-check records for this plan', '这个方案的自测记录')):
            checks = saved_settings.get('quick_check_history', [])
            mastery = saved_settings.get('mastery_by_context', {})
            if checks or mastery:
                for check in checks:
                    st.markdown(f"**{escape(str(check.get('book_title', '')))}**")
                    st.write(check.get('question', ''))
                    st.write(tr('Your answer: ', '你的回答：') + str(check.get('answer', '')))
                    labels = {'sound': tr('Sound reasoning', '理解到位'), 'partial': tr('Needs more detail', '还需补充'),
                              'misconception': tr('Misconception to revisit', '需要纠正'), 'insufficient': tr('Not assessed', '暂不判断')}
                    if check.get('verdict') in labels:
                        st.caption(tr('Feedback: ', '点评：') + labels[check['verdict']])
                    elif check.get('score') is not None:
                        st.caption(tr('Earlier estimated result: ', '历史估计结果：') + f"{float(check['score']):.0%}")
                for results in mastery.values():
                    for assessment in results:
                        st.progress(float(assessment.get('mastery_score', 0)), text=str(assessment.get('concept', '')))
                        for evidence in assessment.get('evidence', []):
                            st.caption(str(evidence))
            else:
                st.caption(tr('No self-check results saved for this plan.', '这个方案暂无已保存的自测结果。'))
    return True
