from __future__ import annotations

import logging
from datetime import UTC, datetime
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from src.book_search import (
    SEARCH_EVALUATION_VERSION,
    is_search_identity_match,
    search_and_assess_book,
)
from src.config import get_settings
from src.database import AtlasDatabase
from src.diagnostic import diagnostic_scope_key
from src.graph import run_recommendation_graph
from src.journey_actions import (
    next_stage_book_id,
    normalize_reading_state,
    replace_stage_book,
    resolve_current_book_id,
    resolve_stage_view_number,
    should_accept_progress_update,
    stage_progress_values,
)
from src.language import (
    DEFAULT_INTERFACE_LANGUAGE,
    SUPPORTED_INTERFACE_LANGUAGES,
    interface_language,
    localize_catalog_text,
    localize_system_message,
    metadata_field_label,
    reading_stage_title,
    resource_type_label,
)
from src.learning_review import (
    generate_questions,
    generate_quick_question,
    learning_context,
    review_answers,
    review_mastery,
)
from src.llm.factory import create_learning_provider, create_llm_provider
from src.mentor import book_conversation_scope, find_stage_replacement, generate_mentor_response
from src.models import (
    BookCandidate,
    BookSearchEvaluation,
    ConceptMastery,
    DiagnosticQuestion,
    LearningGoal,
    ReadingPath,
    ReadingSessionInput,
    RecommendationResult,
    UserProfile,
)
from src.plan_history import render_plan_history
from src.purchase_links import build_purchase_links
from src.quiz_ui import merge_mastery, question_inputs, same_question_set, saved_feedback
from src.reading_support import support_reading
from src.replanning import replan_path
from src.services.recommendation import ensure_detailed_assessments
from src.services.scoring import SCORING_VERSION
from src.ui import (
    accountability_card_html,
    atlas_theme_css,
    book_cover_html,
    book_fit_result_html,
    brand_html,
    companion_preview_html,
    concept_card_html,
    execution_trace_html,
    fit_score_dimensions,
    form_scroll_restoration_html,
    hash_navigation_html,
    hero_html,
    interaction_result_html,
    learning_goal_editor_html,
    mentor_conversation_html,
    mobile_navigation_html,
    navigation_empty_state_html,
    profile_return_html,
    provider_html,
    purchase_links_html,
    reading_dashboard_html,
    reading_session_completion_html,
    reading_session_timer_html,
    score_grid_html,
    section_anchor,
    section_header,
    sidebar_navigation_html,
    status_html,
    topbar_html,
    workspace_intro_html,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)

PROJECT_ROOT = Path(__file__).resolve().parent

st.set_page_config(
    page_title="NexMind Atlas",
    page_icon=str(PROJECT_ROOT / "assets" / "nexmind-mark.svg"),
    layout="wide",
    initial_sidebar_state="auto",
)
st.markdown(atlas_theme_css(), unsafe_allow_html=True)
st.sidebar.markdown(brand_html(), unsafe_allow_html=True)
requested_ui_language = str(st.query_params.get("ui_language", "")).strip().lower()
requested_search_user_id = str(st.query_params.get("user_id", "demo-eee")).strip()[:120] or "demo-eee"
requested_language_change = str(st.query_params.get("set_language", "")).strip().lower()
if requested_language_change in SUPPORTED_INTERFACE_LANGUAGES:
    st.session_state["ui_language"] = requested_language_change
    requested_ui_language = requested_language_change
    st.query_params["ui_language"] = requested_language_change
    del st.query_params["set_language"]
if "ui_language" not in st.session_state and requested_ui_language in SUPPORTED_INTERFACE_LANGUAGES:
    st.session_state["ui_language"] = requested_ui_language
sidebar_language = st.session_state.get("ui_language", DEFAULT_INTERFACE_LANGUAGE)
sidebar_is_zh = sidebar_language == "zh"
st.sidebar.markdown(
    sidebar_navigation_html(sidebar_is_zh, requested_search_user_id, preview=bool(st.query_params.get("preview_plan"))),
    unsafe_allow_html=True,
)
sidebar_settings = st.sidebar.expander("设置" if sidebar_is_zh else "Settings", expanded=False)
with sidebar_settings:
    ui_language = st.selectbox(
        "界面语言" if sidebar_is_zh else "Interface language",
        list(SUPPORTED_INTERFACE_LANGUAGES),
        format_func=lambda value: "中文" if value == "zh" else "English",
        key="ui_language",
    )
is_zh = ui_language == "zh"


def tr(english: str, chinese: str) -> str:
    return chinese if is_zh else english


label_separator = "：" if is_zh else ":"


LANGUAGE_BOUND_SESSION_KEYS = (
    "profile",
    "goal",
    "recommendation",
    "mastery",
    "mastery_context",
    "reading_support",
    "previous_path",
    "revised_path",
    "plan_revision",
    "plan_notice",
    "book_search_evaluation",
    "book_search_error",
    "book_search_not_found",
    "book_search_key",
    "progress_notice",
    "replacement_notice",
)


def clear_language_bound_state() -> None:
    for key in LANGUAGE_BOUND_SESSION_KEYS:
        st.session_state.pop(key, None)


previous_ui_language = st.session_state.get("_rendered_ui_language")
if previous_ui_language is not None and previous_ui_language != ui_language:
    clear_language_bound_state()
    for query_key in ("book_query", "stage_view", "preview_plan", "history"):
        if query_key in st.query_params:
            del st.query_params[query_key]
st.session_state["_rendered_ui_language"] = ui_language
if requested_ui_language != ui_language:
    st.query_params["ui_language"] = ui_language

requested_workspace_key = f"{ui_language}::{requested_search_user_id}"
previous_workspace_key = st.session_state.get("_rendered_workspace_key")
if previous_workspace_key is not None and previous_workspace_key != requested_workspace_key:
    clear_language_bound_state()
    for query_key in ("book_query", "stage_view", "preview_plan", "history"):
        if query_key in st.query_params:
            del st.query_params[query_key]
st.session_state["_rendered_workspace_key"] = requested_workspace_key


settings = get_settings()
database = AtlasDatabase(settings.resolved_database_path)


def save_progress_with_stage_handoff(
    result: RecommendationResult,
    profile: UserProfile,
    language: str,
    book: BookCandidate,
    stage_number: int,
    progress_percent: int,
    status: str,
    *,
    set_current: bool,
) -> tuple[int, str, str | None]:
    """Save a book update and hand the active marker to the next stage at 100%."""
    saved_percent, saved_status = normalize_reading_state(progress_percent, status)
    before = database.load_reading_progress(profile.user_id, language)
    active_before = resolve_current_book_id(result, before)
    should_advance = saved_status == "completed" and (
        active_before == book.canonical_id or set_current
    )
    next_book_id = next_stage_book_id(result, stage_number) if should_advance else None
    database.save_reading_progress(
        profile.user_id,
        book.canonical_id,
        saved_percent,
        saved_status,
        is_current=bool(set_current and not next_book_id) or (
            saved_status == "completed" and next_book_id is None and active_before == book.canonical_id
        ),
        language=language,
    )
    if next_book_id:
        next_state = before.get(next_book_id, {})
        next_percent = int(next_state.get("progress_percent", 0))
        next_status = str(next_state.get("status", "planned"))
        database.save_reading_progress(
            profile.user_id,
            next_book_id,
            next_percent,
            next_status,
            is_current=True,
            language=language,
        )
    return saved_percent, saved_status, next_book_id


def run_mentor_turn(
    *,
    scope: str,
    message: str,
    result: RecommendationResult,
    profile: UserProfile,
    goal: LearningGoal,
    stage_number: int,
    book: BookCandidate,
    language: str,
) -> RecommendationResult:
    """Run one persistent mentor turn and apply its explicit state-changing actions."""
    history = database.load_mentor_messages(
        profile.user_id, scope, language=language, limit=16
    )
    database.save_mentor_message(
        profile.user_id, scope, "user", message, language=language
    )
    progress_state = database.load_reading_progress(profile.user_id, language).get(
        book.canonical_id, {}
    )
    mentor_preferences = database.load_mentor_settings(profile.user_id, language=language)
    mentor_preferences.setdefault("cadence", "daily")
    mentor_preferences.setdefault("tone", "supportive")
    mentor_preferences.setdefault("target_minutes", 25)
    try:
        mentor_provider = create_learning_provider(settings)
    except Exception:  # noqa: BLE001 - local mentor fallback stays available
        logging.exception("Mentor provider could not be initialized")
        mentor_provider = None
    response, used_live_model, warnings = generate_mentor_response(
        message,
        profile=profile,
        goal=goal,
        result=result,
        stage_number=stage_number,
        book=book,
        progress_percent=int(progress_state.get("progress_percent", 0)),
        history=history,
        provider=mentor_provider,
        mentor_preferences=mentor_preferences,
    )
    updated_result = result
    action_notes: list[str] = []
    progress_rejected_note = ""

    if response.progress_percent >= 0 or response.reading_status != "unchanged":
        requested_percent = (
            response.progress_percent
            if response.progress_percent >= 0
            else int(progress_state.get("progress_percent", 0))
        )
        requested_status = (
            response.reading_status
            if response.reading_status != "unchanged"
            else str(progress_state.get("status", "planned"))
        )
        current_percent = int(progress_state.get("progress_percent", 0))
        if not should_accept_progress_update(current_percent, requested_percent, message):
            progress_rejected_note = (
                f"你刚才说的 {requested_percent}% 低于已保存的 {current_percent}%，为避免误覆盖，本次没有修改；如需更正，请明确说“更正为 {requested_percent}%”。"
                if language == "zh"
                else f"The reported {requested_percent}% is below the saved {current_percent}%, so it was not changed. To correct it, say “correction: set it to {requested_percent}%.”"
            )
            action_notes.append(progress_rejected_note)
        else:
            saved_percent, _, next_book_id = save_progress_with_stage_handoff(
                updated_result,
                profile,
                language,
                book,
                stage_number,
                requested_percent,
                requested_status,
                set_current=bool(progress_state.get("is_current"))
                or resolve_current_book_id(updated_result, database.load_reading_progress(profile.user_id, language))
                == book.canonical_id,
            )
            if next_book_id:
                next_book = next(
                    item for item in updated_result.selected_books if item.canonical_id == next_book_id
                )
                action_notes.append(
                    f"已将当前阅读推进到《{next_book.title}》。"
                    if language == "zh"
                    else f"Current reading advanced to {next_book.title}."
                )
            else:
                action_notes.append(
                    f"阅读进度已更新为 {saved_percent}%。"
                    if language == "zh"
                    else f"Reading progress updated to {saved_percent}%."
                )

    if response.replace_book:
        replacement_reason = (
            response.replacement_reason
            if response.replacement_reason != "none"
            else "other"
        )
        database.save_book_feedback(
            profile.user_id,
            book.canonical_id,
            stage_number,
            replacement_reason,
            message,
            language=language,
        )
        try:
            replacement = find_stage_replacement(
                updated_result,
                goal,
                profile,
                settings,
                stage_number,
                replacement_reason,
                feedback=message,
            )
            was_current = resolve_current_book_id(
                updated_result,
                database.load_reading_progress(profile.user_id, language),
            ) == book.canonical_id
            updated_result = replacement.result
            database.save_recommendation(profile.user_id, updated_result, language)
            database.save_path(updated_result.reading_path)
            database.save_reading_progress(
                profile.user_id,
                replacement.book.canonical_id,
                0,
                "planned",
                is_current=was_current,
                language=language,
            )
            warnings.extend(replacement.warnings)
            action_notes.append(
                f"已只替换第 {stage_number} 阶段：改为《{replacement.book.title}》，其他阶段保持不变。"
                if language == "zh"
                else f"Only Stage {stage_number} was replaced with {replacement.book.title}; the other stages were preserved."
            )
        except Exception as exc:  # noqa: BLE001 - leave the existing path intact
            logging.exception("Mentor book replacement failed")
            response = response.model_copy(update={"next_step": (
                "告诉我哪些偏好可以放宽，或提供一本候选书名；确认新的检索方向后再找替代书。"
                if language == "zh" else
                "Tell me which preferences you can relax, or suggest a candidate title, so the next search has a clearer direction."
            )})
            action_notes.append(
                "暂未找到足够契合且可核验的替代书，原书未被更改。你可以补充希望的难度、语言或内容侧重。"
                if language == "zh"
                else "No sufficiently relevant verified alternative was found, so the current book was kept. Add the difficulty, language, or emphasis you want and try again."
            )
            warnings.append(type(exc).__name__)

    if response.should_replan:
        changed_hours = response.revised_hours_per_week > 0
        has_constraint = changed_hours or response.too_theoretical or bool(
            response.low_mastery_concept.strip()
        )
        if has_constraint:
            new_hours = (
                response.revised_hours_per_week if changed_hours else goal.hours_per_week
            )
            revised, revision = replan_path(
                updated_result.reading_path,
                goal,
                new_hours,
                response.too_theoretical,
                response.low_mastery_concept.strip() or None,
            )
            updated_result = updated_result.model_copy(update={"reading_path": revised})
            if changed_hours:
                goal = goal.model_copy(update={"hours_per_week": new_hours})
                st.session_state["goal"] = goal
                database.save_user(profile, goal, language)
            database.save_path(revised)
            database.save_revision(revised.path_id, revision)
            database.save_recommendation(profile.user_id, updated_result, language)
            st.session_state["revised_path"] = revised
            st.session_state["plan_revision"] = revision
            action_notes.append(
                "已按你刚才说明的限制调整整条阅读路径，并保留原学习目标。"
                if language == "zh"
                else "The full path was updated around the constraints you described while preserving the learning goal."
            )
        else:
            action_notes.append(
                "我还需要一个具体约束，例如每周可投入时间、材料太理论，或尚未掌握的概念，才能安全调整整条路径。"
                if language == "zh"
                else "I need one concrete constraint—weekly time, material that is too theoretical, or an unclear concept—before safely changing the full path."
            )

    settings_payload = database.load_mentor_settings(profile.user_id, language=language)
    settings_payload.update(
        {
            "next_step": response.next_step,
            "encouragement": response.encouragement,
            "last_check_in_at": datetime.now(UTC).isoformat(),
            "next_check_in_days": response.next_check_in_days,
        }
    )
    database.save_mentor_settings(
        profile.user_id, settings_payload, language=language
    )
    action_payload = response.model_dump(mode="json")
    action_payload.update(
        {
            "used_live_model": used_live_model,
            "applied_actions": action_notes,
            "warnings": warnings,
        }
    )
    # The model reply is already instructed to be encouraging. Keep the
    # structured encouragement for the accountability card instead of
    # duplicating it in chat. If a lower percentage was safely rejected,
    # replace any potentially contradictory model wording with the clear action.
    assistant_content = progress_rejected_note or response.reply
    if action_notes and not progress_rejected_note:
        assistant_content += "\n\n" + " ".join(action_notes)
    if warnings and not used_live_model:
        assistant_content += "\n\n" + warnings[0]
    database.save_mentor_message(
        profile.user_id,
        scope,
        "assistant",
        assistant_content,
        action_payload,
        language=language,
    )
    st.session_state["recommendation"] = updated_result
    return updated_result


with sidebar_settings:
    st.markdown(f'<div class="atlas-side-label">{tr("AI model", "模型服务")}</div>', unsafe_allow_html=True)
    if settings.llm_provider.strip().lower() == "bedrock" and not settings.demo_mode:
        st.markdown(
            provider_html(
                tr("Amazon Bedrock", "Amazon Bedrock"),
                settings.bedrock_model_id or tr("Not configured", "尚未配置"),
                live=True,
                state_label=tr("Live model", "在线模型"),
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            provider_html(
                tr("Offline demo model", "本地模拟模型"),
                tr("Runs locally", "本地 / 离线"),
                live=False,
                state_label=tr("Demo model", "模拟模式"),
            ),
            unsafe_allow_html=True,
        )
    st.markdown(f'<div class="atlas-side-label">{tr("Book data source", "书目服务")}</div>', unsafe_allow_html=True)
    st.markdown(
        provider_html(
            tr("Included book snapshots", "项目附带书目快照") if settings.demo_mode else "Google Books API",
            (
                tr("No live catalogue calls", "不调用实时书目服务") if settings.demo_mode else
                tr("API key configured", "API 密钥已配置")
                if settings.google_books_api_key
                else tr("API key not configured", "GOOGLE_BOOKS_API_KEY 尚未填写")
            ),
            live=bool(settings.google_books_api_key) and not settings.demo_mode,
            state_label=(
                tr("Demo data", "演示数据") if settings.demo_mode else
                tr("Ready", "已就绪")
                if settings.google_books_api_key
                else tr("Setup required", "需要配置")
            ),
        ),
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="atlas-side-label">{tr("Saved journey", "已保存的学习路径")}</div>', unsafe_allow_html=True)
    saved_user_id = st.text_input(
        tr("User ID", "用户 ID"),
        requested_search_user_id,
        key=f"saved_user_id_{ui_language}_{requested_search_user_id}",
    )
    if st.button(tr("Load saved journey", "加载已保存路径")):
        saved_user_id = saved_user_id.strip()
        loaded_user = database.load_user(saved_user_id, ui_language)
        loaded_result = database.load_recommendation(saved_user_id, ui_language)
        if loaded_user and loaded_result:
            loaded_profile, loaded_goal = loaded_user
            if interface_language(loaded_goal) == ui_language:
                clear_language_bound_state()
                st.session_state["profile"] = loaded_profile
                st.session_state["goal"] = loaded_goal
                st.session_state["recommendation"] = loaded_result
                st.session_state["_rendered_workspace_key"] = f"{ui_language}::{loaded_profile.user_id}"
                st.query_params["user_id"] = loaded_profile.user_id
                for query_key in (
                    "book_query", "stage_view", "preview_plan", "history",
                    "new_profile", "return_profile", "return_language",
                ):
                    if query_key in st.query_params:
                        del st.query_params[query_key]
                st.session_state["profile_switch_notice"] = tr(
                    f"Switched to learning profile: {loaded_profile.user_id}",
                    f"已切换到学习档案：{loaded_profile.user_id}",
                )
                # The sidebar was already rendered using the old URL identity.
                # Restart before rendering any more controls so every surface
                # (including history, search and goal widgets) uses the new ID.
                st.rerun()
            else:
                saved_language = "Chinese" if interface_language(loaded_goal) == "zh" else "English"
                saved_language_zh = "中文" if interface_language(loaded_goal) == "zh" else "英文"
                st.warning(tr(
                    f"This journey was created in {saved_language}. Switch the interface to {saved_language} to load it.",
                    f"这条学习路径使用{saved_language_zh}生成，请切换到对应的界面语言后再加载。",
                ))
        else:
            st.warning(tr("No saved journey exists for this user ID yet.", "未找到该用户的已保存学习路径。"))

if notice := st.session_state.pop("profile_switch_notice", None):
    st.success(notice)

if render_plan_history(database, requested_search_user_id, ui_language):
    st.markdown(mobile_navigation_html(is_zh, requested_search_user_id, preview=True), unsafe_allow_html=True)
    st.stop()
if notice := st.session_state.pop('history_switch_notice', None):
    st.success(notice)

if "recommendation" not in st.session_state:
    stored_user = database.load_user(requested_search_user_id, ui_language)
    stored_result = database.load_recommendation(requested_search_user_id, ui_language)
    if stored_user and stored_result and interface_language(stored_user[1]) == ui_language:
        st.session_state["profile"], st.session_state["goal"] = stored_user
        st.session_state["recommendation"] = stored_result
    elif stored_user and ("profile" not in st.session_state or "goal" not in st.session_state):
        st.session_state["profile"], st.session_state["goal"] = stored_user

result = st.session_state.get("recommendation")
if result:
    profile = UserProfile.model_validate(st.session_state["profile"].model_dump(mode="python"))
    goal = LearningGoal.model_validate(st.session_state["goal"].model_dump(mode="python"))
    result = RecommendationResult.model_validate(result.model_dump(mode="python"))
    if interface_language(goal) != ui_language:
        clear_language_bound_state()
        result = None
    else:
        detailed_assessments = ensure_detailed_assessments(
            result.selected_books,
            result.assessments,
            goal,
            profile,
        )
        if detailed_assessments != result.assessments:
            result = result.model_copy(update={"assessments": detailed_assessments})
            database.save_recommendation(profile.user_id, result, ui_language)
        st.session_state["profile"] = profile
        st.session_state["goal"] = goal
        st.session_state["recommendation"] = result

if result and not result.selected_books:
    st.warning(tr(
        "No sufficiently relevant verified books were found. Refine the learning topic or allow sample data, then try again.",
        "暂未找到与学习目标充分相关且经过核验的书籍。请细化学习主题，或允许使用示例数据后重试。",
    ))
    st.session_state.pop("recommendation", None)
    result = None

search_profile: UserProfile | None = None
search_goal: LearningGoal | None = None
if result:
    search_profile = profile
    search_goal = goal
elif st.session_state.get("profile") and st.session_state.get("goal"):
    search_profile = UserProfile.model_validate(st.session_state["profile"])
    search_goal = LearningGoal.model_validate(st.session_state["goal"])

search_items: list[tuple[str, str, str, str]] = []
if result:
    search_items.append((goal.topic, tr("Learning topic", "学习主题"), "#knowledge-map", goal.topic))
    for index, requirement in enumerate(result.concepts, start=1):
        area_label = resource_type_label(requirement.required_resource_type, ui_language)
        search_items.append(
            (
                requirement.concept,
                tr("Knowledge area", "知识类型"),
                f"#knowledge-area-{index}",
                f"{area_label} {requirement.importance if is_zh else requirement.importance.capitalize()}",
            )
        )
    book_by_search_id = {item.canonical_id: item for item in result.selected_books}
    for stage in result.reading_path.stages:
        if not stage.books or stage.books[0] not in book_by_search_id:
            continue
        book = book_by_search_id[stage.books[0]]
        search_items.append(
            (
                book.title,
                tr("Book", "书籍"),
                f"#book-stage-{stage.stage_number}",
                " ".join([*book.authors, reading_stage_title(stage.title, ui_language)]),
            )
        )

requested_book_query = str(st.query_params.get("book_query", "")).strip()[:160]

st.markdown(
    f'<a class="atlas-skip" href="#atlas-main">{tr("Skip to main content", "跳至主要内容")}</a>',
    unsafe_allow_html=True,
)
st.markdown(
    topbar_html(
        is_zh,
        search_items,
        initial_query=requested_book_query,
        agent_search_enabled=bool(search_profile and search_goal),
        search_user_id=requested_search_user_id,
        native_search=True,
    ),
    unsafe_allow_html=True,
)

search_ready = bool(search_profile and search_goal)
search_placeholder = (
    tr("Enter a book title or ISBN to assess fit", "输入书名或 ISBN，评估契合度")
    if search_ready
    else tr("Create a reading path to enable book assessment", "生成学习路径后即可评估书籍")
)
st.markdown(section_anchor("book-search"), unsafe_allow_html=True)
with st.container(key="atlas_global_search"):
    with st.form(f"atlas_global_search_form_{ui_language}", border=False):
        query_column, submit_column = st.columns([4, 1], gap="small", vertical_alignment="center")
        with query_column:
            submitted_book_query = st.text_input(
                search_placeholder,
                value=requested_book_query,
                placeholder=search_placeholder,
                key=f"atlas_search_input_{ui_language}_{requested_search_user_id}",
                label_visibility="collapsed",
                icon=":material/search:",
                disabled=not search_ready,
            )
        with submit_column:
            search_submitted = st.form_submit_button(
                tr("Assess", "评估"),
                type="primary",
                disabled=not search_ready,
                use_container_width=True,
            )

st.markdown(
    mobile_navigation_html(
        is_zh, requested_search_user_id,
        return_profile_id=(str(st.query_params.get("return_profile", "")).strip()[:120]
                           if st.query_params.get("new_profile") == "1" else ""),
        return_language=str(st.query_params.get("return_language", "")),
    ),
    unsafe_allow_html=True,
)

if search_submitted:
    # Submitting again is an explicit retry, not a request to reuse a failed
    # lookup (or an assessment produced by the previous identity logic).
    for search_state_key in ("book_search_key", "book_search_evaluation", "book_search_error", "book_search_not_found"):
        st.session_state.pop(search_state_key, None)
    next_book_query = submitted_book_query.strip()[:160]
    if next_book_query:
        st.query_params["book_query"] = next_book_query
        st.query_params["ui_language"] = ui_language
        if search_profile:
            st.query_params["user_id"] = search_profile.user_id
    elif "book_query" in st.query_params:
        del st.query_params["book_query"]
    st.rerun()

if search_profile and search_goal and requested_book_query:
    search_key = "|".join(
        (
            SEARCH_EVALUATION_VERSION,
            search_profile.user_id,
            ui_language,
            requested_book_query.casefold(),
            search_goal.model_dump_json(),
        )
    )
    evaluation: BookSearchEvaluation | None = None
    search_error = ""
    search_not_found = False
    if st.session_state.get("book_search_key") == search_key:
        cached_evaluation = st.session_state.get("book_search_evaluation")
        if cached_evaluation:
            evaluation = BookSearchEvaluation.model_validate(cached_evaluation)
            if not is_search_identity_match(requested_book_query, evaluation.book):
                evaluation = None
                st.session_state.pop("book_search_key", None)
        search_error = str(st.session_state.get("book_search_error") or "")
        search_not_found = bool(st.session_state.get("book_search_not_found"))
    if st.session_state.get("book_search_key") != search_key:
        with st.status(
            tr(
                f'Atlas is searching for “{requested_book_query}” and assessing its fit…',
                f'Atlas 正在检索“{requested_book_query}”并评估契合度……',
            ),
            expanded=True,
        ) as search_status:
            st.write(
                tr(
                    "1 of 3 · Searching Google Books and Open Library",
                    "第 1 步，共 3 步 · 检索 Google Books 与 Open Library",
                )
            )
            st.caption(
                tr(
                    "Search, edition checks and fit review can take a minute or more. Results will appear here when ready.",
                    "Atlas 会核对版本，再判断是否适合你的目标。首次检索可能需要一分钟以上，完成后结果会显示在这里。",
                )
            )
            try:
                evaluation = search_and_assess_book(
                    requested_book_query,
                    search_goal,
                    search_profile,
                    settings,
                    provider=create_learning_provider(settings),
                    known_candidates=result.selected_books if result else None,
                )
                st.write(
                    tr(
                        "2 of 3 · Edition and source records checked",
                        "第 2 步，共 3 步 · 已核对版本与来源记录",
                    )
                )
                st.write(
                    tr(
                        "3 of 3 · Fit assessment complete",
                        "第 3 步，共 3 步 · 契合度评估完成",
                    )
                )
                search_status.update(
                    label=tr("Book assessment complete", "书籍评估完成"),
                    state="complete",
                    expanded=False,
                )
            except LookupError as exc:
                search_error = str(exc)
                search_not_found = True
                search_status.update(
                    label=tr("No matching book found", "未找到匹配的书目"),
                    state="complete",
                    expanded=False,
                )
            except Exception as exc:  # noqa: BLE001 - surface a recoverable search state in the UI
                search_error = str(exc)
                search_status.update(
                    label=tr("Book assessment could not be completed", "暂时无法完成书籍评估"),
                    state="error",
                    expanded=False,
                )
        st.session_state["book_search_key"] = search_key
        st.session_state["book_search_evaluation"] = evaluation
        st.session_state["book_search_error"] = search_error
        st.session_state["book_search_not_found"] = search_not_found

    st.markdown(section_anchor("book-fit-results"), unsafe_allow_html=True)
    if evaluation:
        st.markdown(book_fit_result_html(evaluation, is_zh), unsafe_allow_html=True)
        if evaluation.book.isbn_13 or evaluation.book.isbn_10:
            st.caption(tr("Edition shown · ISBN ", "当前展示版本 · ISBN ") + (evaluation.book.isbn_13 or evaluation.book.isbn_10))
        if result:
            assessments_by_book = {item.canonical_id: item for item in result.assessments}
            available_stages = result.reading_path.stages
            default_stage_index = next((index for index, stage in enumerate(available_stages)
                if assessments_by_book.get(stage.books[0])
                and assessments_by_book[stage.books[0]].evaluated_role == evaluation.evaluated_role), 0)
            target_stage_number = st.selectbox(
                tr("Which stage would you like to replace?", "你想替换哪个阶段的书？"),
                options=[stage.stage_number for stage in available_stages],
                index=default_stage_index,
                format_func=lambda number: reading_stage_title(next(
                    stage.title for stage in available_stages if stage.stage_number == number), ui_language),
                key=f"manual_replacement_target_{ui_language}_{evaluation.book.canonical_id}",
            )
            target_stage = next(stage for stage in available_stages if stage.stage_number == target_stage_number)
            current_stage_book = next(
                book for book in result.selected_books if book.canonical_id == target_stage.books[0]
            )
            is_current_choice = current_stage_book.canonical_id == evaluation.book.canonical_id
            recommended_for_path = (
                evaluation.assessment.goal_relevance >= 0.3
                and evaluation.assessment.overall_rank_score >= 0.35
            )
            with st.container(border=True):
                st.markdown(f"#### {tr('Use this book in your reading path', '将这本书加入阅读路径')}")
                st.caption(tr(
                    f"Replace “{current_stage_book.title}” in Stage {target_stage_number}? Your other books and their progress will stay unchanged.",
                    f"确认后将替换第 {target_stage_number} 阶段的《{current_stage_book.title}》。其他书目及其进度保持不变。",
                ))
                target_assessment = assessments_by_book.get(current_stage_book.canonical_id)
                if target_assessment and target_assessment.evaluated_role != evaluation.evaluated_role:
                    st.info(tr(
                        "This book was assessed for a different knowledge area. You can choose it, but coverage of this stage's original goal has not been verified.",
                        "这本书更适合补充另一类知识。你仍可选择它，但它是否覆盖本阶段原定目标尚未核实。",
                    ))
                acknowledge_low_fit = True
                if not recommended_for_path:
                    st.warning(tr(
                        "This book has a low fit score. Atlas does not recommend using it as a core path book.",
                        "这本书与当前学习目标的契合度较低，Atlas 不建议将其作为核心阅读书目。",
                    ))
                    acknowledge_low_fit = st.checkbox(
                        tr(
                            "I understand the low fit and still want to replace the stage book",
                            "我了解契合度较低，仍要替换该阶段书目",
                        ),
                        key=f"replacement_override_{ui_language}_{profile.user_id}_{evaluation.book.canonical_id}",
                    )
                replace_book = st.button(
                    tr(
                        f"Replace Stage {target_stage_number} book",
                        f"替换第 {target_stage_number} 阶段书目",
                    ),
                    type="primary",
                    disabled=is_current_choice or not acknowledge_low_fit,
                    key=f"replace_stage_book_{ui_language}_{profile.user_id}_{evaluation.book.canonical_id}",
                )
                if is_current_choice:
                    st.info(tr(
                        "This book is already used in the selected stage.",
                        "这个阶段已经在使用这本书，无需重复替换。",
                    ))
                if replace_book:
                    if not acknowledge_low_fit:
                        st.error(tr(
                            "Confirm that you understand the low fit before replacing the book.",
                            "请先确认你了解契合度较低，再执行替换。",
                        ))
                    else:
                        try:
                            updated_result = replace_stage_book(
                                result,
                                evaluation.book,
                                evaluation.assessment,
                                target_stage_number,
                                available_hours=goal.total_hours,
                            )
                            prior_progress = database.load_reading_progress(
                                profile.user_id, ui_language
                            ).get(current_stage_book.canonical_id, {})
                            should_be_current = bool(prior_progress.get("is_current")) or (
                                not prior_progress and target_stage_number == 1
                            )
                            database.save_book_feedback(
                                profile.user_id,
                                current_stage_book.canonical_id,
                                target_stage_number,
                                "replaced",
                                f"Replaced with {evaluation.book.title}",
                                language=ui_language,
                            )
                            database.save_reading_progress(
                                profile.user_id,
                                evaluation.book.canonical_id,
                                0,
                                "planned",
                                is_current=should_be_current,
                                language=ui_language,
                            )
                            database.save_recommendation(
                                profile.user_id, updated_result, ui_language
                            )
                            database.save_path(updated_result.reading_path)
                            st.session_state["recommendation"] = updated_result
                            st.session_state["replacement_notice"] = tr(
                                f'“{evaluation.book.title}” replaced “{current_stage_book.title}” in Stage {target_stage_number}.',
                                f'已用《{evaluation.book.title}》替换第 {target_stage_number} 阶段的《{current_stage_book.title}》。',
                            )
                            for key in (
                                "book_search_evaluation",
                                "book_search_error",
                                "book_search_key",
                                "book_search_not_found",
                            ):
                                st.session_state.pop(key, None)
                            if "book_query" in st.query_params:
                                del st.query_params["book_query"]
                            st.rerun()
                        except ValueError as exc:
                            st.error(localize_system_message(str(exc), ui_language))
    elif search_error:
        with st.container(border=True):
            if search_not_found:
                st.info(search_error)
                st.write(tr(
                    "Try the full title, add the author, or enter the ISBN for a specific edition. A missing result does not mean the book does not exist or is unsuitable for you.",
                    "可以输入完整书名、补充作者，或用 ISBN 指定版本。没有搜到，不代表这本书不存在，也不代表它不适合你。",
                ))
            else:
                st.error(tr(
                    "The book lookup could not be completed. Your current reading path has not changed.",
                    "这次书籍检索未能完成，你当前的阅读路径没有改变。",
                ))
                with st.expander(tr("Connection details", "连接详情")):
                    st.caption(search_error)
            st.markdown(tr(
                "[Edit the title and search again](#book-search)",
                "[修改书名，重新搜索](#book-search)",
            ))
            if st.button(tr("Retry search", "重新检索"), key="book_search_retry"):
                st.session_state.pop("book_search_key", None)
                st.rerun()

st.markdown(hero_html(is_zh, has_path=bool(result)), unsafe_allow_html=True)
if settings.demo_mode:
    st.info(tr(
        "DEMO MODE · Included book snapshots and local rules, not live AI. Try the embodied-intelligence example below. Switch to live mode for other topics and AI tutoring. Cover images and source links may still need internet.",
        "演示模式 · 当前使用附带书目快照和本地规则，不是真实 AI 输出。可在下方填入具身智能示例体验流程；其他主题及 AI 答疑请使用真实模式。封面图片与来源链接仍可能需要联网。",
    ))

if result:
    progress_by_book = database.load_reading_progress(profile.user_id, ui_language)
    current_book_id = resolve_current_book_id(result, progress_by_book)
    current_book = next(
        book for book in result.selected_books if book.canonical_id == current_book_id
    )
    current_stage = next(
        stage for stage in result.reading_path.stages if current_book_id in stage.books
    )
    current_progress = int(
        progress_by_book.get(current_book_id, {}).get("progress_percent", 0)
    )
    assessment_by_id = {item.canonical_id: item for item in result.assessments}
    book_by_id = {item.canonical_id: item for item in result.selected_books}
    requested_stage_view = st.query_params.get("stage_view", current_stage.stage_number)
    viewed_stage_number = resolve_stage_view_number(
        result, requested_stage_view, current_stage.stage_number
    )
    viewed_stage = next(
        stage for stage in result.reading_path.stages
        if stage.stage_number == viewed_stage_number and stage.books
    )
    viewed_book = book_by_id[viewed_stage.books[0]]
    viewed_progress = int(
        progress_by_book.get(viewed_book.canonical_id, {}).get("progress_percent", 0)
    )
    viewed_assessment = assessment_by_id[viewed_book.canonical_id]
    persisted_loop_settings = database.load_mentor_settings(
        profile.user_id, language=ui_language
    )
    diagnostic_context = diagnostic_scope_key(goal, profile, current_book, current_stage)
    mastery_by_context = persisted_loop_settings.get("mastery_by_context", {})
    persisted_mastery_payload = (
        mastery_by_context.get(diagnostic_context, [])
        if isinstance(mastery_by_context, dict)
        else []
    )
    persisted_mastery: list[ConceptMastery] = []
    if isinstance(persisted_mastery_payload, list):
        for item in persisted_mastery_payload:
            try:
                persisted_mastery.append(ConceptMastery.model_validate(item))
            except Exception:  # noqa: BLE001 - ignore only malformed legacy snapshots
                logging.warning("Ignoring malformed mastery snapshot")
    mastery_owner = (profile.user_id, ui_language,
                     database.mentor_scope_for_path(result.reading_path), diagnostic_context)
    if st.session_state.get("mastery_context") != mastery_owner:
        st.session_state["mastery"] = persisted_mastery
        st.session_state["mastery_context"] = mastery_owner
    mastery_items = st.session_state.get("mastery", [])
    learner_percent = (
        round(
            sum(item.mastery_score for item in mastery_items)
            / len(mastery_items)
            * 100
        )
        if mastery_items
        else None
    )
    source_links: list[tuple[str, str | None]] = []
    seen_sources: set[str] = set()
    for selected_book in [viewed_book]:
        for record in selected_book.source_records:
            if record.source_name not in seen_sources:
                seen_sources.add(record.source_name)
                source_links.append((record.source_name, record.source_url))
    if len(source_links) < 4:
        source_links.append((
            "Amazon Bedrock"
            if settings.llm_provider.strip().lower() == "bedrock"
            else tr("Transparent scoring rubric", "透明评分规则"),
            None,
        ))
    replacement_notice = st.session_state.pop("replacement_notice", None)
    if replacement_notice:
        st.success(replacement_notice)
    if not result.reading_path.constraints_satisfied:
        st.warning(tr("This is a partial match, not a fully checked learning plan. Review the gaps before starting.",
                      "这份方案还没有完全满足你的要求，请先看看缺少哪些内容，再决定是否开始。"))
        with st.expander(tr("What's still missing?", "还缺少什么？"), expanded=True):
            for warning in dict.fromkeys([*result.warnings, *result.reading_path.warnings]):
                st.write(warning)
    st.markdown(
        reading_dashboard_html(
            is_zh=is_zh,
            topic=goal.topic,
            duration_weeks=goal.duration_weeks,
            stage_labels=[
                reading_stage_title(stage.title, ui_language)
                .split("：", 1)[0]
                .split(":", 1)[0]
                .strip()
                for stage in result.reading_path.stages
            ],
            book_title=viewed_book.title,
            authors=viewed_book.authors,
            reason=localize_catalog_text(viewed_assessment.recommendation_reason, ui_language),
            overview=localize_catalog_text(viewed_assessment.book_overview, ui_language),
            book=viewed_book,
            confidence=viewed_assessment.confidence,
            source_links=source_links,
            data_mode=result.data_mode,
            progress_percent=viewed_progress,
            current_stage_number=viewed_stage.stage_number,
            active_stage_number=current_stage.stage_number,
            active_progress_percent=current_progress,
            stage_progress=stage_progress_values(result, progress_by_book),
            learner_percent=learner_percent,
            user_id=profile.user_id,
            interface_language=ui_language,
        ),
        unsafe_allow_html=True,
    )
else:
    st.markdown(workspace_intro_html(is_zh), unsafe_allow_html=True)

st.markdown(section_anchor("learning-brief"), unsafe_allow_html=True)
if result:
    goal_editor = st.container(key="atlas_goal_editor")
    with goal_editor:
        st.markdown(
            learning_goal_editor_html(is_zh, topic=goal.topic),
            unsafe_allow_html=True,
        )
        form_area = st.expander(
            tr("Edit goals, time, and book preferences", "调整目标、时间与书目偏好"),
            expanded=False,
        )
else:
    is_new_profile = st.query_params.get("new_profile") == "1"
    st.markdown(
        section_header(
            "01 · DIRECTION" if not is_zh else "01 · 学习方向",
            tr("New learning profile", "新建学习档案") if is_new_profile else tr("Define your learning goals", "填写学习需求"),
            tr(
                "Start with a new topic. Your previous plans, conversations, and reading progress stay in their original profile. This profile is saved when you generate a reading path.",
                "从新的学习主题开始。原档案的方案、对话和阅读进度都会保留；填写并生成路径后，新档案才会保存。",
            ) if is_new_profile else tr(
                "Tell Atlas what you want to learn so it can create a focused reading path—not a generic book list.",
                "提供学习目标、已有基础和时间安排，Atlas 会据此生成有针对性的阅读路径。",
            ),
        ),
        unsafe_allow_html=True,
    )
    return_profile_id = str(st.query_params.get("return_profile", "")).strip()[:120]
    if is_new_profile and return_profile_id and return_profile_id != requested_search_user_id:
        st.markdown(profile_return_html(
            is_zh, return_profile_id, return_language=str(st.query_params.get("return_language", "")),
        ), unsafe_allow_html=True)
    form_area = st.container()

goal_form_keys = {
    "user_id": f"goal_user_id_{ui_language}_{requested_search_user_id}",
    "topic": f"topic_{ui_language}_{requested_search_user_id}",
    "major": f"major_{ui_language}_{requested_search_user_id}",
    "background": f"background_{ui_language}_{requested_search_user_id}",
    "purpose": f"purpose_{ui_language}_{requested_search_user_id}",
    "focus_details": f"focus_details_{ui_language}_{requested_search_user_id}",
    "duration": f"duration_{ui_language}_{requested_search_user_id}",
    "hours": f"hours_{ui_language}_{requested_search_user_id}",
    "perspectives": f"perspectives_{ui_language}_{requested_search_user_id}",
    "balance": f"balance_{ui_language}_{requested_search_user_id}",
    "book_language": f"book_language_{ui_language}_{requested_search_user_id}",
    "difficulty": f"difficulty_{ui_language}_{requested_search_user_id}",
}
fresh_goal_defaults = {
    "user_id": requested_search_user_id,
    "topic": "",
    "major": "",
    "background": "",
    "purpose": "",
    "focus_details": "",
    "duration": 6,
    "hours": 4.0,
    "perspectives": [],
    "difficulty": "beginner",
    "balance": "theory and application",
    "book_language": "zh" if is_zh else "en",
}
if settings.demo_mode and not result and st.button(
    tr("Use example learning goals", "填入演示学习需求"), key="fill_demo_goals",
):
    example_values = {
        "topic": "具身智能" if is_zh else "Embodied Intelligence",
        "major": "电子与电气工程" if is_zh else "Electrical and Electronic Engineering",
        "background": "Python\nMachine Learning\nBasic control theory",
        "purpose": "建立跨学科基础，理解认知、机器人和伦理的联系" if is_zh else "Build an interdisciplinary foundation across cognition, robotics and ethics",
        "focus_details": "",
        "perspectives": ["机器人学", "认知科学", "伦理学"] if is_zh else ["Robotics", "Cognitive Science", "Ethics"],
        "difficulty": "intermediate",
        "duration": 6,
        "hours": 4.0,
        "book_language": "zh" if is_zh else "en",
    }
    for field, value in example_values.items():
        st.session_state[goal_form_keys[field]] = value
for field, default_value in fresh_goal_defaults.items():
    st.session_state.setdefault(goal_form_keys[field], default_value)
if result:
    saved_perspectives = list(goal.required_perspectives or profile.interests)
    saved_book_languages = list(goal.book_language_preferences)
    saved_book_language_mode = (
        "bilingual" if len(saved_book_languages) > 1 else (saved_book_languages[0] if saved_book_languages else "en")
    )
    goal_form_signature = repr((
        profile.model_dump(mode="json"),
        goal.model_dump(mode="json"),
    ))
    goal_form_marker = f"_goal_form_source_{ui_language}_{requested_search_user_id}"
    if st.session_state.get(goal_form_marker) != goal_form_signature:
        st.session_state[goal_form_keys["user_id"]] = profile.user_id
        st.session_state[goal_form_keys["topic"]] = goal.topic
        st.session_state[goal_form_keys["major"]] = profile.major or ""
        st.session_state[goal_form_keys["background"]] = "\n".join(profile.background_knowledge)
        st.session_state[goal_form_keys["purpose"]] = goal.purpose
        st.session_state[goal_form_keys["focus_details"]] = goal.focus_details
        st.session_state[goal_form_keys["duration"]] = goal.duration_weeks
        st.session_state[goal_form_keys["hours"]] = goal.hours_per_week
        st.session_state[goal_form_keys["perspectives"]] = saved_perspectives
        st.session_state[goal_form_keys["balance"]] = goal.desired_balance
        st.session_state[goal_form_keys["book_language"]] = saved_book_language_mode
        st.session_state[goal_form_keys["difficulty"]] = goal.preferred_difficulty if goal.preferred_difficulty in {"beginner", "intermediate", "advanced"} else "intermediate"
        st.session_state[goal_form_marker] = goal_form_signature

with form_area:
  with st.form(f"goal_setup_{ui_language}"):
    st.caption(tr("Fields marked * are required.", "标有 * 的字段为必填项。"))
    left, right = st.columns(2)
    with left:
        st.markdown(f'<div class="atlas-form-kicker">{tr("Learning profile", "学习背景")}</div>', unsafe_allow_html=True)
        user_id = st.text_input(
            tr("Learning profile name *", "学习档案名称 *"),
            help=tr("Use the same name to return to these records. This local prototype is not an authenticated account.", "再次使用同一名称可找回记录。这是本地学习档案，不是经过身份验证的账号。"),
            key=goal_form_keys["user_id"],
        )
        topic = st.text_input(
            tr("Learning topic *", "学习主题 *"),
            placeholder=tr("For example: machine learning, climate science, design history", "例如：机器学习、气候科学、设计史"),
            key=goal_form_keys["topic"],
        )
        major = st.text_input(
            tr("Field of study or work *", "你的专业或工作领域 *"),
            key=goal_form_keys["major"],
        )
        background = st.text_area(
            tr("Existing knowledge (one per line)", "已有知识（每行一项）"),
            placeholder=tr("What do you already know? Leave blank if you are starting fresh.", "已经学过什么？零基础也没关系，可以留空。"),
            key=goal_form_keys["background"],
        )
        purpose = st.text_input(
            tr("Why are you learning this? *", "学习目的 *"),
            placeholder=tr("What would you like to understand or be able to do?", "学完后，你希望理解什么，或能做什么？"),
            key=goal_form_keys["purpose"],
        )
        focus_details = st.text_area(
            tr("Specific interests and requirements (optional)", "细分方向与特别要求（选填）"),
            placeholder=tr(
                "For example: I want to go deeper into cognitive psychology, especially attention and working memory. I'd like research-based books and experiments I can try, not self-help books.",
                "例如：我想深入学习认知心理学，重点了解注意力和工作记忆。希望读有研究依据的书，试着设计小实验，不想读心灵鸡汤类书籍。",
            ),
            max_chars=2000,
            height=125,
            key=goal_form_keys["focus_details"],
        )
        st.caption(tr(
            "Write freely: a subfield, a question to explore, or material to avoid. Atlas will use this when finding books and planning your study.",
            "不用局限于选项。感兴趣的分支、想研究的问题、不想读的内容，都可以写在这里；Atlas 会据此选书和规划。",
        ))
    with right:
        st.markdown(f'<div class="atlas-form-kicker">{tr("Time and preferences", "时间与偏好")}</div>', unsafe_allow_html=True)
        duration = st.number_input(
            tr("Duration (weeks)", "学习周期（周）"),
            min_value=1,
            max_value=24,
            key=goal_form_keys["duration"],
        )
        hours = st.number_input(
            tr("Hours per week", "每周可投入时间（小时）"),
            min_value=0.5,
            max_value=40.0,
            step=0.5,
            key=goal_form_keys["hours"],
        )
        perspective_options = (
            ["心理学", "认知心理学", "发展心理学", "社会心理学", "计算机科学", "统计学习", "科研方法", "工程实践", "社会影响", "伦理学", "设计", "机器人学", "认知科学", "神经科学"]
            if is_zh
            else ["Psychology", "Cognitive Psychology", "Developmental Psychology", "Social Psychology", "Computer Science", "Statistical Learning", "Research Methods", "Engineering Practice", "Social Impact", "Ethics", "Design", "Robotics", "Cognitive Science", "Neuroscience"]
        )
        perspectives = st.multiselect(
            tr("Other disciplines or perspectives (optional)", "还想结合哪些学科或视角？（选填）"),
            perspective_options,
            accept_new_options=True,
            placeholder=tr("Choose an option, or type your own and press Enter", "选择已有选项，或输入自定义内容后按 Enter"),
            help=tr(
                "Add any discipline or perspective you want included. Press Enter after each one.",
                "可添加任意学科或分析视角；每输入一项后按 Enter 确认。",
            ),
            key=goal_form_keys["perspectives"],
        )
        difficulty = st.selectbox(
            tr("Starting level", "这次想从什么难度开始？"),
            ["beginner", "intermediate", "advanced"],
            format_func=lambda value: {"beginner": tr("Beginner-friendly", "从入门开始"), "intermediate": tr("Build on some foundations", "有基础，继续深入"), "advanced": tr("Advanced study", "进阶研读")}[value],
            key=goal_form_keys["difficulty"],
        )
        balance = st.selectbox(
            tr("Learning emphasis", "内容侧重"),
            ["theory and application", "application first", "theory first"],
            format_func=lambda value: {
                "theory and application": tr("Balanced theory and practice", "理论与应用并重"),
                "application first": tr("Practice first", "应用优先"),
                "theory first": tr("Theory first", "理论优先"),
            }[value],
            key=goal_form_keys["balance"],
        )
        book_language_mode = st.selectbox(
            tr("Preferred book language", "书目语言偏好"),
            ["zh", "en", "bilingual"] if is_zh else ["en", "zh", "bilingual"],
            format_func=lambda value: {
                "zh": tr("Chinese preferred", "中文优先"),
                "en": tr("English preferred", "英文优先"),
                "bilingual": tr("Chinese and English equally", "中英双语"),
            }[value],
            key=goal_form_keys["book_language"],
        )
        allow_cached = st.checkbox(
            tr("Use the included demo book snapshots", "使用项目附带的演示书目快照") if settings.demo_mode else
            tr("Use clearly labeled sample data if live search is unavailable", "实时检索不足时，允许使用已标注的示例数据"),
            value=settings.demo_mode,
            disabled=settings.demo_mode,
            key=f"allow_cached_{ui_language}_{requested_search_user_id}",
        )
    submitted = st.form_submit_button(
        (
            tr("Save changes and rebuild the path", "保存更改并重新规划")
            if result
            else tr("Create a source-verified reading path", "生成学习路径")
        ),
        type="primary",
    )

form_errors: list[str] = []
if submitted:
    required_values = (
        (user_id, tr("Enter a learning profile name.", "请输入学习档案名称。")),
        (topic, tr("Enter a learning topic.", "请输入学习主题。")),
        (major, tr("Enter your field of study or work.", "请输入你的专业或领域。")),
        (purpose, tr("Explain why you want to learn this topic.", "请说明学习这个主题的目的。")),
    )
    form_errors.extend(message for value, message in required_values if not value.strip())
    if st.query_params.get("new_profile") == "1" and user_id.strip() and database.load_user(user_id.strip(), ui_language):
        form_errors.append(tr(
            "That profile name is already in use. Choose a different name to keep your existing records separate.",
            "这个档案名称已经用过了。请换一个名称，新旧学习记录就能分别保存。",
        ))

if form_errors:
    st.error(
        tr("Please fix the following before building your path:", "请先修正以下问题，再构建学习路径：")
        + "\n\n"
        + "\n".join(f"- {message}" for message in form_errors)
    )

if submitted and not form_errors:
    book_languages = ["zh", "en"] if book_language_mode == "bilingual" else [book_language_mode]
    profile = UserProfile(
        user_id=user_id,
        education_level=profile.education_level if result else "self-directed learner",
        major=major,
        background_knowledge=[line.strip() for line in background.splitlines() if line.strip()],
        interests=perspectives,
        language_preferences=["Chinese" if code == "zh" else "English" for code in book_languages],
        reading_preferences=[balance],
        completed_books=[],
        interface_language=ui_language,
    )
    goal = LearningGoal(
        topic=topic,
        purpose=purpose,
        focus_details=focus_details.strip(),
        duration_weeks=int(duration),
        hours_per_week=float(hours),
        required_perspectives=perspectives,
        preferred_difficulty=difficulty,
        desired_balance=balance,
        interface_language=ui_language,
        book_language_preferences=book_languages,
    )
    with st.status(
        tr("Atlas is building your reading path…", "Atlas 正在为你规划阅读路径……"),
        expanded=True,
    ) as path_status:
        st.write(tr("1 of 4 · Mapping three complementary knowledge areas", "第 1 步，共 4 步 · 梳理三类互补知识"))
        st.write(tr("2 of 4 · Searching recent book-source results", "第 2 步，共 4 步 · 检索近期书目来源"))
        st.caption(
            tr(
                "The first run usually takes 30–60 seconds. Keep this tab open; Atlas will save the path automatically.",
                "首次生成通常需要 30–60 秒。请保持当前页面打开，完成后 Atlas 会自动保存路径。",
            )
        )
        try:
            result = run_recommendation_graph(
                profile,
                goal,
                settings,
                allow_cached,
                provider=create_llm_provider(settings),
            )
            if not result.reading_path.stages:
                raise ValueError(tr(
                    "No sufficiently suitable books were found. Your previous plan is unchanged. You can revise your preferences or retry. ",
                    "暂时没有找到足够合适的书，原有方案不会被改动。你可以调整偏好或稍后重试。",
                ) + "\n\n" + "\n".join(result.warnings[-3:]))
            st.write(tr("3 of 4 · Checking editions, relevance, and reading-time fit", "第 3 步，共 4 步 · 核对版本、主题相关性与阅读时间"))
            st.write(tr("4 of 4 · Sequencing the strongest verified books", "第 4 步，共 4 步 · 编排通过核验的最佳书目"))
            st.session_state["recommendation"] = result
            st.session_state["profile"] = profile
            st.session_state["goal"] = goal
            st.session_state["_rendered_workspace_key"] = f"{ui_language}::{profile.user_id}"
            st.query_params["user_id"] = profile.user_id
            if "stage_view" in st.query_params:
                del st.query_params["stage_view"]
            database = AtlasDatabase(settings.resolved_database_path)
            database.save_user(profile, goal, ui_language)
            database.save_path(result.reading_path)
            database.save_recommendation(profile.user_id, result, ui_language)
            for query_key in ("new_profile", "return_profile", "return_language"):
                if query_key in st.query_params:
                    del st.query_params[query_key]
            path_status.update(
                label=(tr("Reading path ready", "阅读路径已生成") if result.reading_path.constraints_satisfied else
                       tr("Partial path saved — review the gaps", "已保存部分方案，请查看待补充内容")),
                state="complete",
                expanded=False,
            )
            st.rerun()
        except Exception as exc:
            logging.exception("Recommendation flow failed")
            path_status.update(
                label=tr("Atlas could not finish this path", "Atlas 暂时无法完成这条路径"),
                state="error",
                expanded=True,
            )
            detail = str(exc) if isinstance(exc, ValueError) else tr(
                f"The path could not be built: {type(exc).__name__}. Check network access, then submit again to retry.",
                f"无法构建路径：{type(exc).__name__}。请检查网络连接，然后再次提交即可重试。",
            )
            st.error(detail)

result = st.session_state.get("recommendation")
if result:
    # Streamlit can retain instances created from an older class definition after hot reload.
    # Revalidate their serialized payloads so newly added fields receive current defaults.
    profile = UserProfile.model_validate(st.session_state["profile"].model_dump(mode="python"))
    goal = LearningGoal.model_validate(st.session_state["goal"].model_dump(mode="python"))
    result = RecommendationResult.model_validate(result.model_dump(mode="python"))
    st.session_state["profile"] = profile
    st.session_state["goal"] = goal
    st.session_state["recommendation"] = result
    if result.scoring_version < SCORING_VERSION:
        st.warning(
            tr(
                "This saved path uses an earlier matching method. Recheck it to apply the stricter topic-relevance rules; your recorded reading progress will be kept.",
                "这条已保存路径使用的是旧版匹配规则。建议重新核验，以应用更严格的主题相关性标准；已记录的阅读进度会保留。",
            )
        )
        if st.button(
            tr("Recheck this reading path", "按新版规则重新核验"),
            type="primary",
            key=f"refresh_scoring_{ui_language}_{profile.user_id}",
        ):
            with st.status(
                tr("Atlas is rechecking every recommendation…", "Atlas 正在重新核验每一本推荐书……"),
                expanded=True,
            ) as refresh_status:
                refreshed = run_recommendation_graph(
                    profile,
                    goal,
                    settings,
                    allow_cached_fallback=True,
                    provider=create_llm_provider(settings),
                )
                refreshed_path = refreshed.reading_path.model_copy(
                    update={
                        "path_id": result.reading_path.path_id,
                        "version": result.reading_path.version + 1,
                    }
                )
                refreshed = refreshed.model_copy(update={"reading_path": refreshed_path})
                database.save_path(refreshed_path)
                database.save_recommendation(profile.user_id, refreshed, ui_language)
                st.session_state["recommendation"] = refreshed
                refresh_status.update(
                    label=tr("Path rechecked and saved", "路径已重新核验并保存"),
                    state="complete",
                    expanded=False,
                )
            st.rerun()
    mode_labels = {
        "live": tr("LIVE SOURCES", "实时来源"),
        "cached_demo": tr("VERIFIED CACHE", "已核验缓存"),
        "mixed": tr("LIVE + VERIFIED CACHE", "实时来源与已核验缓存"),
    }
    status_detail = tr(
        "Book details can be traced to the sources shown below.",
        "下方书目的基本信息均可追溯到所列来源。",
    ) if result.data_mode == "live" else tr(
        "Cached bibliographic records retain their source links and retrieval dates and are clearly separated from live results.",
        "缓存书目保留来源链接与获取日期，并与本次实时检索结果清晰区分。",
    )
    st.markdown(
        status_html(mode_labels[result.data_mode], status_detail, warning=result.data_mode != "live"),
        unsafe_allow_html=True,
    )

    with st.expander(tr("How Atlas built this path", "Atlas 如何生成这条路径"), expanded=False):
        st.markdown(execution_trace_html(result.execution_trace), unsafe_allow_html=True)

    st.markdown(
        section_anchor("knowledge-map")
        +
        section_header(
            "02 · KNOWLEDGE MAP" if not is_zh else "02 · 知识地图",
            "",
            tr(
                "Atlas identifies complementary knowledge areas, then finds suitable books for each one.",
                "Atlas 先梳理相互补充的知识类型，再据此匹配合适的书籍。",
            ),
        ),
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    for index, (col, requirement) in enumerate(
        zip(cols, result.concepts, strict=False), start=1
    ):
        with col:
            st.markdown(
                section_anchor(f"knowledge-area-{index}")
                + concept_card_html(
                    resource_type_label(requirement.required_resource_type, ui_language),
                    requirement.concept,
                    tr("Importance", "重要程度"),
                    requirement.importance if is_zh else requirement.importance.capitalize(),
                ),
                unsafe_allow_html=True,
            )

    st.markdown(
        section_anchor("reading-route")
        +
        section_header(
            "03 · READING PATH" if not is_zh else "03 · 阅读路径",
            "",
            tr(
                "Expand a stage to review its sources, recommendation rationale, limitations, and fit scores.",
                "展开各阶段，可查看书目来源、推荐理由、注意事项和各项匹配度。",
            ),
        ),
        unsafe_allow_html=True,
    )
    assessment_by_id = {item.canonical_id: item for item in result.assessments}
    book_by_id = {item.canonical_id: item for item in result.selected_books}
    route_progress_by_book = database.load_reading_progress(profile.user_id, ui_language)
    route_current_book_id = resolve_current_book_id(result, route_progress_by_book)
    for stage in result.reading_path.stages:
        book = book_by_id[stage.books[0]]
        assessment = assessment_by_id[book.canonical_id]
        stage_prefix = f"第 {stage.stage_number} 阶段" if is_zh else f"Stage {stage.stage_number}"
        st.markdown(section_anchor(f"book-stage-{stage.stage_number}"), unsafe_allow_html=True)
        with st.expander(
            f"{stage_prefix} · {book.title}",
            expanded=book.canonical_id == route_current_book_id,
        ):
            cover_column, a, b = st.columns([0.48, 1.52, 1], gap="large")
            with cover_column:
                st.markdown(book_cover_html(book, is_zh), unsafe_allow_html=True)
            with a:
                st.write(f"**{tr('Author(s)', '作者')}{label_separator}** {', '.join(book.authors) or tr('Not available', '暂无数据')}")
                st.write(f"**ISBN-13{label_separator}** {book.isbn_13 or tr('Not available', '暂无数据')}")
                overview_text = assessment.book_overview or book.description or tr(
                    "No description is available from the verified sources.",
                    "已核验来源暂未提供内容简介。",
                )
                st.write(
                    f"**{tr('About this book', '内容简介')}{label_separator}** "
                    f"{localize_catalog_text(overview_text, ui_language)}"
                )
                st.write(
                    f"**{tr('Why this book', '推荐理由')}{label_separator}** "
                    f"{localize_catalog_text(assessment.recommendation_reason, ui_language)}"
                )
                if assessment.why_now.strip() != assessment.recommendation_reason.strip():
                    st.write(
                        f"**{tr('Why this stage', '本阶段推荐理由')}{label_separator}** "
                        f"{localize_catalog_text(assessment.why_now, ui_language)}"
                    )
                st.write(f"**{tr('Learning objective', '学习目标')}{label_separator}** {stage.learning_objective}")
            with b:
                confidence_label = {"low": tr("LOW", "低"), "medium": tr("MEDIUM", "中"), "high": tr("HIGH", "高")}[assessment.confidence]
                st.metric(tr("Book record verification", "书目信息核验程度"), confidence_label)
                st.metric(tr("Estimated reading time", "预计精读时间"), f"{stage.estimated_hours:g} {tr('hours', '小时')}")
                st.write(f"**{tr('Publication year', '出版年份')}{label_separator}** {book.published_year or tr('Not available', '暂无数据')}")
                rating = tr("Not available", "暂无数据")
                if book.average_rating is not None:
                    count = book.ratings_count if book.ratings_count is not None else tr("Not available", "暂无数据")
                    if is_zh:
                        rating = f"{book.average_rating:.2f}（{count} 条评分）"
                    else:
                        rating_word = "rating" if count == 1 else "ratings"
                        rating = f"{book.average_rating:.2f} ({count} {rating_word})"
                st.write(f"**{tr('Reader ratings', '读者评分')}{label_separator}** {rating}")
            if is_zh:
                purchase_links = build_purchase_links(book.title, book.isbn_13 or book.isbn_10)
                st.markdown(
                    purchase_links_html(
                        [(link.platform, link.url) for link in purchase_links],
                        book.isbn_13 or book.isbn_10,
                    ),
                    unsafe_allow_html=True,
                )
            st.write(f"**{tr('Book sources', '书目来源')}{label_separator}**")
            for record in book.source_records:
                label = f"{record.source_name} · {tr('accessed', '获取日期')} {record.retrieved_at.date()}"
                if record.source_url:
                    st.markdown(f"- [{label}]({record.source_url})")
                else:
                    st.markdown(f"- {label}")
                st.caption(
                    f"{tr('Verified fields', '已核对字段')}{label_separator}"
                    f" {', '.join(metadata_field_label(field, ui_language) for field in record.fields_verified) or tr('Not available', '暂无数据')} · "
                    f"{tr('Metadata conflicts', '信息冲突')}{label_separator} {', '.join(record.conflicts) or tr('None found', '未发现冲突')}"
                )
            st.write(f"**{tr('Fit score breakdown', '匹配度明细')}{label_separator}**")
            st.caption(tr("These are ranking signals, not measured learning outcomes or probabilities of suitability.", "以下是选书时的参考指标，不是实测学习效果，也不代表适合你的概率。"))
            score_values = fit_score_dimensions(assessment, is_zh)
            st.markdown(score_grid_html(score_values), unsafe_allow_html=True)
            st.write(f"**{tr('Limitations', '注意事项')}{label_separator}**")
            for reservation in assessment.reservations or [tr("No significant metadata limitations found.", "未发现明显的书目信息问题。")]:
                st.write(f"- {localize_catalog_text(reservation, ui_language)}")
            if stage.selected_chapters:
                st.write(f"**{tr('Reading scope adjustment', '阅读范围调整')}{label_separator}**")
                for note in stage.selected_chapters:
                    st.write(f"- {localize_catalog_text(note, ui_language)}")

            st.divider()
            # A conversation belongs to the exact book, not the numbered stage.
            # Replacing a stage book must not surface the previous book's questions.
            book_scope = book_conversation_scope(book)
            with st.container(key=f"book_mentor_{ui_language}_{profile.user_id}_{stage.stage_number}"):
                st.markdown(f"#### {tr('Talk with Atlas about this book', '就这本书与 Atlas 沟通')}")
                st.caption(tr(
                    "This conversation belongs only to this book. Ask a question, explain what is not working, or request a verified replacement without changing the other books.",
                    "这段对话只属于当前这本书。你可以提问、说明哪里不合适，或要求 Atlas 核验并替换它；其他书不会被改动。",
                ))
                book_messages = database.load_mentor_messages(
                    profile.user_id,
                    book_scope,
                    language=ui_language,
                    limit=8,
                )
                st.markdown(
                    mentor_conversation_html(book_messages, is_zh=is_zh, compact=True),
                    unsafe_allow_html=True,
                )
                book_actions = [
                    "custom",
                    "question",
                    "replace",
                    "too_difficult",
                    "too_theoretical",
                    "already_read",
                    "progress",
                ]
                book_action_labels = {
                    "custom": tr("Write my own message", "自己说明"),
                    "question": tr("Ask about this book", "请教这本书的内容"),
                    "replace": tr("Replace only this book", "只替换这一本"),
                    "too_difficult": tr("This book is too difficult", "这本书目前太难"),
                    "too_theoretical": tr("I need something more practical", "我需要更偏实践的书"),
                    "already_read": tr("I have already read this book", "这本书我已经读过"),
                    "progress": tr("Report my progress", "汇报这本书的进度"),
                }
                with st.form(
                    f"book_mentor_form_{ui_language}_{profile.user_id}_{book.canonical_id}",
                    clear_on_submit=True,
                ):
                    st.markdown(
                        f'<span class="atlas-sr-only" data-atlas-form-target="book-stage-{stage.stage_number}"></span>',
                        unsafe_allow_html=True,
                    )
                    action_choice = st.selectbox(
                        tr("What would you like Atlas to do?", "你希望 Atlas 做什么？"),
                        book_actions,
                        format_func=lambda value, labels=book_action_labels: labels[value],
                        key=f"book_mentor_action_{ui_language}_{profile.user_id}_{book.canonical_id}",
                    )
                    book_message = st.text_area(
                        tr("Message to Atlas", "告诉 Atlas 你的具体情况"),
                        max_chars=1600,
                        placeholder=tr(
                            "For example: Chapter 3 assumes too much mathematics. Please find a gentler alternative for this stage only.",
                            "例如：第三章的数学前置要求太高，请只为当前阶段换一本更易入门的书。",
                        ),
                        key=f"book_mentor_message_{ui_language}_{profile.user_id}_{book.canonical_id}",
                    )
                    send_book_message = st.form_submit_button(
                        tr("Send to Atlas", "发送给 Atlas"),
                        type="primary",
                    )
                if send_book_message:
                    quick_prompts = {
                        "question": tr(
                            f"I have a question about {book.title}: ",
                            f"我对《{book.title}》有一个疑问：",
                        ),
                        "replace": tr(
                            f"Replace only {book.title} with a better verified book for this stage. Keep the other stages unchanged.",
                            f"请只替换《{book.title}》，为当前阶段找一本更合适且经过核验的书，其他阶段保持不变。",
                        ),
                        "too_difficult": tr(
                            f"{book.title} is too difficult right now. Replace only this book with a gentler verified alternative.",
                            f"《{book.title}》目前太难，请只替换这一本，找一本更易入门且经过核验的替代书。",
                        ),
                        "too_theoretical": tr(
                            f"{book.title} is too theoretical. Replace only this book with a more practical verified alternative.",
                            f"《{book.title}》偏理论，请只替换这一本，找一本更偏实践且经过核验的替代书。",
                        ),
                        "already_read": tr(
                            f"I have already read {book.title}. Replace only this book with a different verified resource.",
                            f"《{book.title}》我已经读过，请只替换这一本，换成另一本经过核验的书。",
                        ),
                        "progress": tr(
                            f"My progress in {book.title} is: ",
                            f"我阅读《{book.title}》的进度是：",
                        ),
                    }
                    message = book_message.strip()
                    if action_choice != "custom":
                        message = " ".join(
                            item for item in (quick_prompts[action_choice], message) if item
                        )
                    if not message:
                        st.error(tr("Write a message before sending.", "请先填写要发送的内容。"))
                    else:
                        with st.status(
                            tr("Atlas is reviewing this book and your request…", "Atlas 正在结合这本书和你的要求进行处理……"),
                            expanded=True,
                        ) as mentor_status:
                            result = run_mentor_turn(
                                scope=book_scope,
                                message=message,
                                result=result,
                                profile=profile,
                                goal=goal,
                                stage_number=stage.stage_number,
                                book=book,
                                language=ui_language,
                            )
                            mentor_status.update(
                                label=tr("Atlas responded", "Atlas 已回复"),
                                state="complete",
                                expanded=False,
                            )
                        st.rerun()

    st.caption(
        f"{tr('Estimated reading time', '预计阅读时间')}{label_separator} {result.reading_path.total_estimated_hours:g} / {goal.total_hours:g} {tr('hours', '小时')} · "
        f"{tr('Path check', '路径检查')}{label_separator} {tr('Stages and time budget checked; review the suitability notes', '阶段与时间已检查，请同时查看书目适用说明') if result.reading_path.constraints_satisfied else tr('Some requirements remain unmet — see the notes', '部分要求仍未满足，请查看说明')}"
    )
    if result.warnings:
        with st.expander(tr("Data notes and limitations", "提示与数据说明")):
            for warning in result.warnings:
                st.warning(localize_system_message(warning, ui_language))

    st.markdown(
        section_anchor("learning-loop")
        +
        section_header(
            "04 · LEARNING LOOP" if not is_zh else "04 · 学习闭环",
            "",
            tr(
                "Report progress, check your understanding, or ask a question. Atlas saves the outcome, recommends a next step, and suggests changes when needed.",
                "记录进度、解答疑问、检查理解，让下一步更清楚。",
            ),
        ),
        unsafe_allow_html=True,
    )
    loop_settings = database.load_mentor_settings(
        profile.user_id, language=ui_language
    )
    coach_context = database.path_mentor_scope(profile.user_id, language=ui_language)
    st.markdown(
        '<div class="atlas-loop-context">'
        f'<span>{tr("WORKING WITH", "当前学习")}</span>'
        f'<strong>{escape(current_book.title)}</strong>'
        f'<span>{tr("Stage", "阶段")} {current_stage.stage_number} · '
        f'{int(progress_by_book.get(current_book.canonical_id, {}).get("progress_percent", 0))}%</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    mentor_tab, journey_tab, diagnostic_tab, session_tab, adaptation_tab = st.tabs(
        [
            tr("Study coach", "学习安排"),
            tr("Report progress", "汇报进度"),
            tr("Knowledge check", "知识自测"),
            tr("Explain a passage", "原文答疑"),
            tr("Adjust plan", "调整计划"),
        ],
        key=f"learning_loop_tabs_{ui_language}_{profile.user_id}",
    )
    with mentor_tab:
        with st.container(key="atlas_mentor_workspace"):
            st.markdown(
                f'<h3 class="atlas-tool-title">{tr("Make learning work for you", "一起安排接下来的学习")}</h3>',
                unsafe_allow_html=True,
            )
            st.caption(tr(
                "Short on time, losing momentum, or connecting ideas across books? Work it through here. To discuss or replace one book, open its conversation below.",
                "时间不够、读不下去，或想把几本书的知识串起来，都可以在这里聊。只想问一本书或换书？用下面的专属对话。",
            ))
            st.markdown(
                f'[{tr(f"Open the conversation for {current_book.title}", f"前往《{current_book.title}》的专属对话")}](#book-stage-{current_stage.stage_number})'
            )
            mentor_settings = loop_settings
            next_step = str(mentor_settings.get("next_step") or tr(
                "Read a short passage, then share one idea or question that stood out.",
                "先读一小段，再记下一条收获或一个疑问。",
            ))
            cadence_values = ["daily", "three_times_weekly", "weekly"]
            cadence_labels = {
                "daily": tr("Daily", "每天"),
                "three_times_weekly": tr("Three times a week", "每周三次"),
                "weekly": tr("Weekly", "每周一次"),
            }
            saved_cadence = str(mentor_settings.get("cadence", "daily"))
            if saved_cadence not in cadence_values:
                saved_cadence = "daily"
            accountability_enabled = bool(
                mentor_settings.get("accountability_enabled", True)
            )
            companion_enabled = bool(mentor_settings.get("companion_enabled", True))
            target_minutes_saved = max(
                1, min(int(mentor_settings.get("target_minutes", 25)), 180)
            )
            cadence_days = {"daily": 1, "three_times_weekly": 2, "weekly": 7}
            last_check_in = str(mentor_settings.get("last_check_in_at", ""))
            check_in_due = accountability_enabled and not last_check_in
            if last_check_in:
                try:
                    elapsed = datetime.now(UTC) - datetime.fromisoformat(last_check_in)
                    check_in_due = (
                        accountability_enabled
                        and elapsed.total_seconds() >= cadence_days[saved_cadence] * 86400
                    )
                except ValueError:
                    check_in_due = accountability_enabled
            path_messages = database.load_mentor_messages(
                profile.user_id, "path", language=ui_language, limit=20
            )
            mentor_draft_key = f"coach_draft_{ui_language}_{profile.user_id}_{coach_context}"
            if st.session_state.pop("coach_clear_draft", False):
                st.session_state[mentor_draft_key] = ""
            with st.form(
                f"path_mentor_form_{ui_language}_{profile.user_id}_{coach_context}",
                clear_on_submit=False,
            ):
                st.markdown(
                    '<span class="atlas-sr-only" data-atlas-form-target="coach-reply" data-atlas-wait-result></span>',
                    unsafe_allow_html=True,
                )
                mentor_message = st.text_area(
                    tr("What would you like to work through?", "你想和 Atlas 讨论什么？"),
                    key=mentor_draft_key,
                    max_chars=2000,
                    placeholder=tr(
                        "For example: I only have two hours this week; help me stay on track; how do the ideas across these books connect?",
                        "例如：这周只能投入 2 小时；我最近难以坚持；这几本书的知识应该怎样串起来？",
                    ),
                )
                send_mentor_message = st.form_submit_button(
                    tr("Send to Atlas", "发送给 Atlas"), type="primary"
                )
            mentor_status_slot = st.empty()
            if st.session_state.pop("coach_reply_ready", False):
                st.markdown(interaction_result_html("coach-reply"), unsafe_allow_html=True)
            if path_messages:
                st.markdown(
                    mentor_conversation_html(path_messages[-2:], is_zh=is_zh),
                    unsafe_allow_html=True,
                )
                if len(path_messages) > 2:
                    with st.expander(tr("Earlier messages in this plan", "本方案的较早对话")):
                        st.markdown(mentor_conversation_html(path_messages[:-2], is_zh=is_zh), unsafe_allow_html=True)
            else:
                st.caption(tr(
                    f"Start a conversation about your current plan. You are reading {current_book.title}.",
                    f"从当前计划开始聊吧。你现在阅读的是《{current_book.title}》。",
                ))
            previous_path_messages = database.load_mentor_messages(
                profile.user_id, "path", language=ui_language, limit=100, archived=True,
            )
            if previous_path_messages:
                with st.expander(tr("Earlier plan conversations", "旧路径对话（仅供回顾）")):
                    st.caption(tr(
                        "These are earlier conversations and reading reports. They are not used as context for the current plan. Showing the latest 100 messages.",
                        "这里保留之前的对话和阅读汇报，不会用于当前计划的回答或下一步建议。显示最近 100 条记录。",
                    ))
                    st.markdown(
                        mentor_conversation_html(previous_path_messages, is_zh=is_zh),
                        unsafe_allow_html=True,
                    )
            if send_mentor_message:
                message = mentor_message.strip()
                if not message:
                    st.markdown(interaction_result_html("coach-reply"), unsafe_allow_html=True)
                    st.error(tr("Write a message before sending.", "请先填写要发送的内容。"))
                else:
                    with mentor_status_slot.status(
                        tr("Atlas is reviewing your path and recent progress…", "Atlas 正在结合学习路径和近期进展进行处理……"),
                        expanded=True,
                    ) as mentor_status:
                        result = run_mentor_turn(
                            scope="path",
                            message=message,
                            result=result,
                            profile=profile,
                            goal=goal,
                            stage_number=current_stage.stage_number,
                            book=current_book,
                            language=ui_language,
                        )
                        mentor_status.update(
                            label=tr("Atlas responded", "Atlas 已回复"),
                            state="complete",
                            expanded=False,
                        )
                    st.session_state["coach_reply_ready"] = True
                    st.session_state["coach_clear_draft"] = True
                    st.rerun()

            if check_in_due:
                st.info(tr(
                    f"Check-in due: how is {current_book.title} going? Report a percentage, a blocker, or what you finished.",
                    f"该做一次学习检查了：《{current_book.title}》读得怎么样？可以汇报百分比、遇到的困难或今天完成的内容。",
                ))
            st.markdown(
                accountability_card_html(
                    is_zh=is_zh,
                    next_step=next_step,
                    cadence=cadence_labels[saved_cadence],
                    target_minutes=target_minutes_saved,
                    enabled=accountability_enabled,
                    companion_enabled=companion_enabled,
                    check_in_due=check_in_due,
                ),
                unsafe_allow_html=True,
            )
            coaching_notice = st.session_state.pop("coaching_notice", None)
            if coaching_notice:
                st.success(coaching_notice)

            session_followup_key = (
                f"reading_session_followup_{ui_language}_{profile.user_id}_{coach_context}"
            )
            session_followup_choice_key = (
                f"session_followup_choice_{ui_language}_{profile.user_id}_{coach_context}"
            )
            session_followup_question_key = (
                f"session_followup_question_text_{ui_language}_{profile.user_id}_{coach_context}"
            )
            session_followup_quiz_key = (
                f"session_followup_quiz_text_{ui_language}_{profile.user_id}_{coach_context}"
            )
            pending_followup = st.session_state.get(
                session_followup_key,
                mentor_settings.get("pending_session_followup"),
            )
            if companion_enabled and isinstance(pending_followup, dict):
                completed_book = next(
                    (
                        book
                        for book in result.selected_books
                        if book.canonical_id == pending_followup.get("book_id")
                    ),
                    current_book,
                )
                completed_stage_number = int(
                    pending_followup.get("stage_number", current_stage.stage_number)
                )
                completed_stage = next(
                    (
                        stage
                        for stage in result.reading_path.stages
                        if stage.stage_number == completed_stage_number
                    ),
                    current_stage,
                )

                def clear_pending_followup() -> None:
                    # Dismissal changes only the invitation, never the saved reading report.
                    database.dismiss_reading_followup(
                        profile.user_id, language=ui_language, path=result.reading_path
                    )
                    for key in (session_followup_key, session_followup_choice_key,
                                session_followup_question_key, session_followup_quiz_key):
                        st.session_state.pop(key, None)

                @st.dialog(
                    tr("Little Atlas · Session complete", "小 Atlas · 阅读完成"),
                    width="large",
                    dismissible=True,
                    on_dismiss=clear_pending_followup,
                )
                def show_reading_session_followup() -> None:
                    followup = dict(
                        st.session_state.get(session_followup_key, pending_followup)
                    )

                    def save_pending_followup(payload: dict[str, object]) -> None:
                        persisted_settings = database.load_mentor_settings(
                            profile.user_id, language=ui_language
                        )
                        persisted_settings["pending_session_followup"] = payload
                        database.save_mentor_settings(
                            profile.user_id,
                            persisted_settings,
                            language=ui_language,
                        )
                        st.session_state[session_followup_key] = payload

                    st.markdown(
                        reading_session_completion_html(
                            is_zh=is_zh,
                            book_title=str(
                                followup.get("book_title") or completed_book.title
                            ),
                            target_minutes=int(followup.get("target_minutes", 25)),
                            actual_minutes=int(followup.get("actual_minutes", 1)),
                            progress_percent=int(followup.get("progress_percent", 0)),
                        ),
                        unsafe_allow_html=True,
                    )

                    response_kind = str(followup.get("response_kind", ""))
                    st.caption(tr("You can close this window at any time. Your reading report is already saved.",
                                  "可以随时关闭弹窗，已保存的阅读汇报不会丢失。"))
                    if response_kind == "question":
                        st.markdown(
                            mentor_conversation_html(
                                [
                                    {
                                        "role": "user",
                                        "content": str(followup.get("question", "")),
                                    },
                                    {
                                        "role": "assistant",
                                        "content": str(followup.get("response", "")),
                                    },
                                ],
                                is_zh=is_zh,
                                compact=True,
                            ),
                            unsafe_allow_html=True,
                        )
                    elif response_kind == "quiz":
                        st.markdown(
                            f"#### {tr('Little Atlas’s feedback', '小 Atlas 的反馈')}"
                        )
                        st.write(str(followup.get("response", "")))
                        if followup.get("model_answer"):
                            with st.expander(tr("See an example answer", "查看参考思路")):
                                st.write(followup["model_answer"])
                        if followup.get("next_step"):
                            st.info(tr("Try this next: ", "再想一题：") + followup["next_step"])
                        st.caption(tr("Feedback on this answer only, not a mastery percentage.", "这里只点评这次回答，不把一次自测换算成掌握百分比。"))

                    if response_kind:
                        if st.button(
                            tr("Finish this check-in", "完成本次收尾"),
                            type="primary",
                            key=f"close_completed_session_{ui_language}_{profile.user_id}",
                        ):
                            clear_pending_followup()
                            st.rerun()
                        return

                    st.markdown(
                        f"**{tr('How would you like to wrap up?', '趁记忆还新鲜，你想怎样收尾？')}**"
                    )
                    followup_choice = st.radio(
                        tr("Choose one next action", "选择一个下一步"),
                        ["question", "quiz", "done"],
                        index=None,
                        horizontal=True,
                        format_func=lambda value: {
                            "question": tr("I have a question", "我有一个疑问"),
                            "quiz": tr("Give me one quick check", "用一道题考考我"),
                            "done": tr("Just record completion", "这次很顺利，直接完成"),
                        }[value],
                        key=session_followup_choice_key,
                    )
                    if followup_choice == "question":
                        with st.form(
                            f"session_followup_question_{ui_language}_{profile.user_id}"
                        ):
                            st.markdown(
                                '<span class="atlas-sr-only" data-atlas-form-target="learning-loop"></span>',
                                unsafe_allow_html=True,
                            )
                            followup_question = st.text_area(
                                tr(
                                    "What is still unclear?",
                                    "刚才的阅读里，什么还没有弄懂？",
                                ),
                                max_chars=1200,
                                placeholder=tr(
                                    "Name the idea, passage, or example that is blocking you.",
                                    "写下让你卡住的概念、段落或例子。",
                                ),
                                key=session_followup_question_key,
                            )
                            ask_followup = st.form_submit_button(
                                tr("Ask Little Atlas", "问小 Atlas"), type="primary"
                            )
                        if ask_followup:
                            if not followup_question.strip():
                                st.error(
                                    tr(
                                        "Write your question first.",
                                        "请先写下你的具体疑问。",
                                    )
                                )
                            else:
                                with st.spinner(
                                    tr(
                                        "Little Atlas is thinking…",
                                        "小 Atlas 正在结合本书和你的目标思考……",
                                    )
                                ):
                                    run_mentor_turn(
                                        scope="path",
                                        message=followup_question.strip(),
                                        result=result,
                                        profile=profile,
                                        goal=goal,
                                        stage_number=completed_stage.stage_number,
                                        book=completed_book,
                                        language=ui_language,
                                    )
                                latest_messages = database.load_mentor_messages(
                                    profile.user_id,
                                    "path",
                                    language=ui_language,
                                    limit=2,
                                )
                                assistant_reply = next(
                                    (
                                        str(message.get("content", ""))
                                        for message in reversed(latest_messages)
                                        if message.get("role") == "assistant"
                                    ),
                                    tr(
                                        "Your question was saved. Atlas will keep it in the next step.",
                                        "问题已经保存，Atlas 会把它带入后续学习。",
                                    ),
                                )
                                followup.update(
                                    {
                                        "response_kind": "question",
                                        "question": followup_question.strip(),
                                        "response": assistant_reply,
                                    }
                                )
                                save_pending_followup(followup)
                                st.rerun()
                    elif followup_choice == "quiz":
                        stored_question = followup.get("quick_question")
                        retry_question = st.button(
                            tr("Retry question generation", "重新出题") if followup.get("question_error") else tr("Try another question", "换一道题"),
                            key=f"refresh_quick_question_{session_followup_key}",
                            help=tr("A new question replaces the current question and answer draft.", "换题后会清空这道题的回答草稿。"),
                        )
                        if retry_question or (not stored_question and not followup.get("question_error")):
                            try:
                                with st.spinner(tr("Little Atlas is preparing a question for this session…", "小 Atlas 正在结合这次阅读出题……")):
                                    question_settings = database.load_mentor_settings(profile.user_id, language=ui_language)
                                    history = question_settings.get("quick_question_history", [])
                                    if not isinstance(history, list):
                                        history = []
                                    reviewed = question_settings.get("quick_check_history", [])
                                    recent = (reviewed if isinstance(reviewed, list) else []) + history
                                    generated = generate_quick_question(
                                        goal, profile, completed_book, completed_stage,
                                        session=followup, recent_questions=recent,
                                        provider=create_learning_provider(settings) if settings.llm_provider != "mock" else None,
                                    )
                                history.append({"book_id": completed_book.canonical_id,
                                                "question": generated.prompt, "concept": generated.concept})
                                question_settings["quick_question_history"] = history[-30:]
                                database.save_mentor_settings(profile.user_id, question_settings, language=ui_language)
                                stored_question = generated.model_dump()
                                followup["quick_question"] = stored_question
                                followup.pop("question_error", None)
                                save_pending_followup(followup)
                                st.session_state.pop(session_followup_quiz_key, None)
                            except Exception:
                                logging.exception("Quick question generation failed")
                                followup["question_error"] = True
                                save_pending_followup(followup)
                        if followup.get("question_error"):
                            st.warning(tr("Could not prepare a new question. Your saved report and any existing answer are safe. Retry or close this window.",
                                          "暂时没能出好新题。阅读记录和已有回答都已保留，可以重试或关闭弹窗。"))
                            if not stored_question:
                                return
                        quick_question = DiagnosticQuestion.model_validate(stored_question)
                        st.caption(tr("Based on your reading report and this book’s learning context, not unseen chapter text.",
                                      "结合本次汇报和当前书籍的学习内容出题，不假设已读过未提供的原文。"))
                        st.info(quick_question.prompt)
                        with st.form(
                            f"session_followup_quiz_{ui_language}_{profile.user_id}"
                        ):
                            st.markdown(
                                '<span class="atlas-sr-only" data-atlas-form-target="learning-loop"></span>',
                                unsafe_allow_html=True,
                            )
                            quick_answer = st.text_area(
                                tr("Answer in your own words", "请用自己的话回答"),
                                max_chars=1600,
                                key=session_followup_quiz_key,
                            )
                            submit_quick_check = st.form_submit_button(
                                tr("Let Little Atlas check it", "交给小 Atlas 检查"),
                                type="primary",
                            )
                        if submit_quick_check:
                            if not quick_answer.strip():
                                st.error(
                                    tr(
                                        "Write an answer before checking it.",
                                        "请先写下你的回答。",
                                    )
                                )
                            else:
                                try:
                                    with st.spinner(tr("Little Atlas is checking your reasoning…", "小 Atlas 正在检查你的理解……")):
                                        quick_review = review_answers([quick_question], [quick_answer.strip()],
                                            context=learning_context(goal, profile, completed_book, completed_stage),
                                            provider=create_learning_provider(settings) if settings.llm_provider != "mock" else None)[0]
                                except Exception:
                                    logging.exception("Quick review failed")
                                    st.error(tr("Review unavailable. Your answer is still here; retry later. No score has been recorded.", "暂时无法点评，回答仍保留在这里，请稍后重试。没有记录评估分数。"))
                                    st.stop()
                                quick_feedback = quick_review.feedback
                                quick_next_step = quick_review.follow_up
                                quick_signal = review_mastery([quick_question], [quick_review])
                                quick_score = quick_signal[0].mastery_score if quick_signal else None
                                quick_settings = database.load_mentor_settings(
                                    profile.user_id, language=ui_language
                                )
                                quick_history = quick_settings.get(
                                    "quick_check_history", []
                                )
                                if not isinstance(quick_history, list):
                                    quick_history = []
                                quick_history.append(
                                    {
                                        "book_id": completed_book.canonical_id,
                                        "book_title": completed_book.title,
                                        "stage_number": completed_stage.stage_number,
                                        "concept": quick_question.concept,
                                        "question": quick_question.prompt,
                                        "answer": quick_answer.strip(),
                                        "score": quick_score,
                                        "verdict": quick_review.verdict,
                                        "completed_at": datetime.now(UTC).isoformat(),
                                    }
                                )
                                quick_settings.update(
                                    {
                                        "quick_check_history": quick_history[-20:],
                                        "last_check_in_at": datetime.now(UTC).isoformat(),
                                        "next_step": quick_next_step,
                                    }
                                )
                                database.save_mentor_settings(
                                    profile.user_id,
                                    quick_settings,
                                    language=ui_language,
                                )
                                database.save_mentor_message(
                                    profile.user_id,
                                    "path",
                                    "user",
                                    tr(
                                        f'Quick check answer for “{quick_question.concept}”: {quick_answer.strip()}',
                                        f'快速自测“{quick_question.concept}”的回答：{quick_answer.strip()}',
                                    ),
                                    language=ui_language,
                                )
                                database.save_mentor_message(
                                    profile.user_id,
                                    "path",
                                    "assistant",
                                    quick_feedback,
                                    {
                                        "type": "quick_check",
                                        "score": quick_score,
                                        "next_step": quick_next_step,
                                    },
                                    language=ui_language,
                                )
                                followup.update(
                                    {
                                        "response_kind": "quiz",
                                        "response": quick_feedback,
                                        "score": quick_score,
                                        "verdict": quick_review.verdict,
                                        "model_answer": quick_review.model_answer,
                                        "next_step": quick_next_step,
                                    }
                                )
                                save_pending_followup(followup)
                                st.rerun()
                    elif followup_choice == "done":
                        st.caption(
                            tr(
                                "Your reading report is already saved. You can return for a question or quick check at any time.",
                                "阅读汇报已经保存；之后仍可随时回来提问或自测。",
                            )
                        )
                        if st.button(
                            tr("Done", "完成"),
                            type="primary",
                            key=f"finish_without_followup_{ui_language}_{profile.user_id}",
                        ):
                            clear_pending_followup()
                            st.rerun()

                show_reading_session_followup()

            active_session_payload = mentor_settings.get("active_reading_session", {})
            active_session = (
                active_session_payload
                if isinstance(active_session_payload, dict)
                and active_session_payload.get("book_id") == current_book.canonical_id
                else {}
            )
            if companion_enabled:
                if not active_session:
                    with st.form(
                        f"start_reading_session_{ui_language}_{profile.user_id}_{current_book.canonical_id}"
                    ):
                        st.markdown(
                            '<span class="atlas-sr-only" data-atlas-form-target="learning-loop"></span>',
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f'<h4 class="atlas-session-heading">{tr("Start a focused reading session", "开始一次专注阅读")}</h4>',
                            unsafe_allow_html=True,
                        )
                        st.caption(tr(
                            f'Little Atlas will time {target_minutes_saved} {"minute" if target_minutes_saved == 1 else "minutes"}. When you finish and save the report, it will celebrate with you and offer a question or quick check.',
                            f'小 Atlas 会为你计时 {target_minutes_saved} 分钟。完成并保存汇报后，它会出现并祝贺你，再邀请你提问或做一道快速自测。',
                        ))
                        start_reading_session = st.form_submit_button(
                            tr(
                                f"Start {target_minutes_saved}-minute reading",
                                f"开始 {target_minutes_saved} 分钟阅读",
                            ),
                            type="primary",
                        )
                    if start_reading_session:
                        started_at = datetime.now(UTC).isoformat()
                        session_settings = database.load_mentor_settings(
                            profile.user_id, language=ui_language
                        )
                        session_settings["active_reading_session"] = {
                            "book_id": current_book.canonical_id,
                            "book_title": current_book.title,
                            "stage_number": current_stage.stage_number,
                            "started_at": started_at,
                            "target_minutes": target_minutes_saved,
                        }
                        session_settings["next_step"] = tr(
                            f'Read “{current_book.title}” for {target_minutes_saved} focused {"minute" if target_minutes_saved == 1 else "minutes"}, then report below.',
                            f'专注阅读《{current_book.title}》{target_minutes_saved} 分钟，然后在下方汇报。',
                        )
                        database.save_mentor_settings(
                            profile.user_id, session_settings, language=ui_language
                        )
                        st.session_state["coaching_notice"] = tr(
                            "Timer started. Little Atlas will keep your report form ready here.",
                            "计时已开始，小 Atlas 会把汇报入口一直留在这里。",
                        )
                        st.rerun()
                else:
                    active_target_minutes = max(
                        1, min(int(active_session.get("target_minutes", target_minutes_saved)), 180)
                    )
                    active_started_at = str(active_session.get("started_at", ""))
                    try:
                        active_started = datetime.fromisoformat(active_started_at)
                        if active_started.tzinfo is None:
                            active_started = active_started.replace(tzinfo=UTC)
                        elapsed_seconds = max(
                            0, int((datetime.now(UTC) - active_started).total_seconds())
                        )
                    except ValueError:
                        elapsed_seconds = 0
                    components.html(
                        reading_session_timer_html(
                            is_zh=is_zh,
                            book_title=current_book.title,
                            target_minutes=active_target_minutes,
                            elapsed_seconds=elapsed_seconds,
                        ),
                        height=112,
                        scrolling=False,
                    )
                    st.markdown(
                        f'<h4 class="atlas-session-heading">{tr("Finish and report", "完成后汇报")}</h4>',
                        unsafe_allow_html=True,
                    )
                    st.caption(tr(
                        "This form stays available while the timer runs. Report early if you finish early or get stuck.",
                        "计时期间这个表单会一直显示；提前读完或中途卡住，也可以直接汇报。",
                    ))
                    report_form_key = active_started_at.replace(":", "").replace("+", "")
                    with st.form(
                        f"reading_session_report_{ui_language}_{profile.user_id}_{report_form_key}"
                    ):
                        st.markdown(
                            '<span class="atlas-sr-only" data-atlas-form-target="learning-loop"></span>',
                            unsafe_allow_html=True,
                        )
                        report_progress = st.slider(
                            tr("Current reading progress", "当前阅读进度"),
                            0,
                            100,
                            int(current_progress),
                            5,
                            format="%d%%",
                        )
                        report_note = st.text_area(
                            tr("What did you finish or find unclear?", "这次读完了什么，哪里还不清楚？"),
                            max_chars=1200,
                            placeholder=tr(
                                "For example: I finished chapter 2 and understand the main idea, but the loss function is still unclear.",
                                "例如：读完了第 2 章，理解了主要思路，但损失函数这一段还不清楚。",
                            ),
                        )
                        report_col, stop_col = st.columns([1, 1])
                        with report_col:
                            finish_reading_session = st.form_submit_button(
                                tr(
                                    "Complete and check in with Little Atlas",
                                    "完成阅读，向小 Atlas 汇报",
                                ),
                                type="primary",
                            )
                        with stop_col:
                            stop_reading_session = st.form_submit_button(
                                tr("End without a report", "结束本次，不保存汇报")
                            )
                    if stop_reading_session:
                        session_settings = database.load_mentor_settings(
                            profile.user_id, language=ui_language
                        )
                        session_settings.pop("active_reading_session", None)
                        database.save_mentor_settings(
                            profile.user_id, session_settings, language=ui_language
                        )
                        st.session_state["coaching_notice"] = tr(
                            "The timer was stopped. Your saved reading progress was not changed.",
                            "本次计时已结束，原有阅读进度没有改变。",
                        )
                        st.rerun()
                    if finish_reading_session:
                        actual_minutes = max(1, round(elapsed_seconds / 60))
                        reading_status = "completed" if report_progress == 100 else "reading"
                        saved_percent, saved_status, next_book_id = save_progress_with_stage_handoff(
                            result,
                            profile,
                            ui_language,
                            current_book,
                            current_stage.stage_number,
                            int(report_progress),
                            reading_status,
                            set_current=True,
                        )
                        if next_book_id:
                            next_book = next(
                                book for book in result.selected_books if book.canonical_id == next_book_id
                            )
                            session_next_step = tr(
                                f'Start “{next_book.title}” and note one question from the first session.',
                                f'开始阅读《{next_book.title}》，并记录第一次阅读中遇到的一个问题。',
                            )
                        elif saved_status == "completed":
                            session_next_step = tr(
                                "Write a short reflection connecting what you learned across the path.",
                                "写一段简短总结，说明这条路径中的知识怎样相互连接。",
                            )
                        else:
                            next_target = min(100, max(saved_percent + 10, 10))
                            session_next_step = tr(
                                f'Continue “{current_book.title}” to about {next_target}% and resolve one open question.',
                                f'继续阅读《{current_book.title}》至约 {next_target}%，并解决一个尚未理解的问题。',
                            )
                        completed_at = datetime.now(UTC).isoformat()
                        session_settings = database.load_mentor_settings(
                            profile.user_id, language=ui_language
                        )
                        session_settings.pop("active_reading_session", None)
                        pending_session_followup = {
                            "book_id": current_book.canonical_id,
                            "book_title": current_book.title,
                            "stage_number": current_stage.stage_number,
                            "target_minutes": active_target_minutes,
                            "actual_minutes": actual_minutes,
                            "progress_percent": saved_percent,
                            "note": report_note.strip(),
                            "next_step": session_next_step,
                        }
                        session_settings.update(
                            {
                                "last_check_in_at": completed_at,
                                "next_step": session_next_step,
                                "pending_session_followup": pending_session_followup,
                                "last_reading_session": {
                                    "book_id": current_book.canonical_id,
                                    "book_title": current_book.title,
                                    "started_at": active_started_at,
                                    "completed_at": completed_at,
                                    "target_minutes": active_target_minutes,
                                    "actual_minutes": actual_minutes,
                                    "progress_percent": saved_percent,
                                    "note": report_note.strip(),
                                },
                            }
                        )
                        database.save_mentor_settings(
                            profile.user_id, session_settings, language=ui_language
                        )
                        report_message = tr(
                            f'I completed a {actual_minutes}-minute reading session for “{current_book.title}”. My progress is {saved_percent}%.',
                            f'我完成了《{current_book.title}》的一次 {actual_minutes} 分钟阅读，当前进度 {saved_percent}%。',
                        )
                        if report_note.strip():
                            report_message += tr(" Note: ", " 补充：") + report_note.strip()
                        database.save_mentor_message(
                            profile.user_id,
                            "path",
                            "user",
                            report_message,
                            language=ui_language,
                        )
                        database.save_mentor_message(
                            profile.user_id,
                            "path",
                            "assistant",
                            tr(
                                "Your reading time, progress and note are saved. We can work through your question or try a quick check.",
                                "阅读时间、进度和笔记都已保存。接下来可以聊聊你的疑问，或做一道小测。",
                            ),
                            {"type": "reading_session_report", "next_step": session_next_step},
                            language=ui_language,
                        )
                        st.session_state[session_followup_key] = (
                            pending_session_followup
                        )
                        st.session_state.pop(session_followup_choice_key, None)
                        st.session_state.pop(session_followup_question_key, None)
                        st.session_state.pop(session_followup_quiz_key, None)
                        st.rerun()
            with st.expander(
                tr("Study companion and check-ins", "学习伙伴与提醒"),
                expanded=False,
                key=f"companion_settings_panel_{ui_language}_{profile.user_id}",
            ):
                st.markdown(
                    f"**{tr('How it works', '它会怎样陪你学习')}**"
                )
                st.caption(tr(
                    "When a check-in is due, the Atlas companion asks for your progress the next time you open this page. After a progress update or knowledge check, it refreshes your next step. This local app cannot send notifications while it is closed.",
                    "到了检查时间，你下次打开本页时，小 Atlas 会询问进展；提交阅读进度或知识自测后，它会更新下一步。此本地应用关闭后无法发送系统通知。",
                ))
                tone_values = ["supportive", "direct", "concise"]
                tone_labels = {
                    "supportive": tr(
                        "Supportive · acknowledge progress, then suggest one small step",
                        "温和陪伴 · 先肯定进展，再给一个小步骤",
                    ),
                    "direct": tr(
                        "Direct · name the gap and give a clear target",
                        "明确督促 · 指出偏差，并给出明确目标",
                    ),
                    "concise": tr(
                        "Concise · show only status and next step",
                        "极简提醒 · 只显示状态和下一步",
                    ),
                }
                saved_tone = str(mentor_settings.get("tone", "supportive"))
                if saved_tone not in tone_values:
                    saved_tone = "supportive"

                accountability_toggle_key = (
                    f"mentor_accountability_toggle_{ui_language}_{profile.user_id}"
                )
                companion_toggle_key = (
                    f"mentor_companion_toggle_{ui_language}_{profile.user_id}"
                )
                st.session_state.setdefault(
                    accountability_toggle_key, accountability_enabled
                )
                st.session_state.setdefault(companion_toggle_key, companion_enabled)

                def persist_companion_controls() -> None:
                    updated_settings = database.load_mentor_settings(
                        profile.user_id, language=ui_language
                    )
                    updated_settings.update(
                        {
                            "accountability_enabled": bool(
                                st.session_state.get(accountability_toggle_key, True)
                            ),
                            "companion_enabled": bool(
                                st.session_state.get(companion_toggle_key, True)
                            ),
                        }
                    )
                    database.save_mentor_settings(
                        profile.user_id, updated_settings, language=ui_language
                    )
                    st.session_state["coaching_notice"] = tr(
                        "Study companion display updated.",
                        "小 Atlas 的显示设置已即时更新。",
                    )

                st.caption(tr(
                    "The two switches below take effect immediately; no save button is required.",
                    "下面两个开关会即时生效，不需要再点击保存。",
                ))
                enabled_col, companion_col = st.columns(2)
                with enabled_col:
                    mentor_accountability_enabled = st.checkbox(
                        tr("Enable progress check-ins", "开启学习检查"),
                        key=accountability_toggle_key,
                        on_change=persist_companion_controls,
                    )
                with companion_col:
                    mentor_companion_enabled = st.checkbox(
                        tr(
                            "Show Little Atlas in the learning loop",
                            "在学习闭环中显示小 Atlas",
                        ),
                        key=companion_toggle_key,
                        on_change=persist_companion_controls,
                    )

                if mentor_companion_enabled:
                    st.markdown(
                        companion_preview_html(
                            is_zh=is_zh,
                            cadence=cadence_labels[saved_cadence],
                            target_minutes=target_minutes_saved,
                            tone=saved_tone,
                        ),
                        unsafe_allow_html=True,
                    )
                else:
                    st.info(tr(
                        "Little Atlas is hidden. Progress check-ins can still remain active.",
                        "小 Atlas 当前已隐藏；你仍然可以单独保留学习检查。",
                    ))

                with st.form(f"mentor_settings_form_{ui_language}_{profile.user_id}"):
                    st.markdown(
                        '<span class="atlas-sr-only" data-atlas-form-target="learning-loop"></span>',
                        unsafe_allow_html=True,
                    )
                    cadence_col, tone_col, target_col = st.columns(3)
                    with cadence_col:
                        mentor_cadence = st.selectbox(
                            tr("Check-in rhythm", "检查频率"),
                            cadence_values,
                            index=cadence_values.index(saved_cadence),
                            format_func=lambda value: cadence_labels[value],
                        )
                    with tone_col:
                        mentor_tone = st.selectbox(
                            tr("Coaching style", "督促方式"),
                            tone_values,
                            index=tone_values.index(saved_tone),
                            format_func=lambda value: tone_labels[value],
                        )
                    with target_col:
                        target_minutes = st.number_input(
                            tr("Minutes per reading session", "每次阅读时长（分钟）"),
                            1,
                            180,
                            target_minutes_saved,
                            1,
                            help=tr("Choose 1–180 minutes. You can finish early and report the time actually spent.",
                                    "可选 1–180 分钟。提前结束也可以，汇报时会记录实际用时。"),
                        )
                    save_mentor_settings = st.form_submit_button(
                        tr(
                            "Save rhythm, tone, and session length",
                            "保存频率、提醒方式与阅读时长",
                        )
                    )
                if save_mentor_settings:
                    mentor_settings.update(
                        {
                            "accountability_enabled": mentor_accountability_enabled,
                            "companion_enabled": mentor_companion_enabled,
                            "cadence": mentor_cadence,
                            "tone": mentor_tone,
                            "target_minutes": int(target_minutes),
                        }
                    )
                    database.save_mentor_settings(
                        profile.user_id, mentor_settings, language=ui_language
                    )
                    st.session_state["coaching_notice"] = tr(
                        "Study companion settings saved.",
                        "学习伙伴设置已保存。",
                    )
                    st.rerun()

    with journey_tab:
        st.markdown(
            f'<h3 class="atlas-tool-title">{tr("Update reading progress", "更新阅读进度")}</h3>',
            unsafe_allow_html=True,
        )
        st.caption(tr(
            "Save each book separately, choose your current read, or explain why a recommendation is not working.",
            "分别保存每本书的进度、指定当前阅读，也可以说明某本推荐书为什么不适合。",
        ))
        stage_lookup = {stage.stage_number: stage for stage in result.reading_path.stages}
        journey_book_lookup = {book.canonical_id: book for book in result.selected_books}
        progress_stage_key = (
            f"progress_stage_v2_{ui_language}_{profile.user_id}_{current_stage.stage_number}"
        )
        progress_stage_context_key = (
            f"_progress_stage_context_v2_{ui_language}_{profile.user_id}"
        )
        pending_progress_stage_key = f"_pending_progress_stage_{ui_language}_{profile.user_id}"
        pending_progress_stage = st.session_state.pop(pending_progress_stage_key, None)
        if pending_progress_stage in stage_lookup:
            st.session_state[progress_stage_key] = pending_progress_stage
        stage_numbers = list(stage_lookup)
        active_stage_changed = (
            st.session_state.get(progress_stage_context_key) != current_stage.stage_number
        )
        if active_stage_changed or st.session_state.get(progress_stage_key) not in stage_lookup:
            st.session_state[progress_stage_key] = (
                current_stage.stage_number
                if current_stage.stage_number in stage_lookup
                else stage_numbers[0]
            )
        st.session_state[progress_stage_context_key] = current_stage.stage_number
        selected_stage_number = st.selectbox(
            tr("Book to update", "选择要更新的书籍"),
            stage_numbers,
            format_func=lambda number: tr(
                f"Stage {number} · {journey_book_lookup[stage_lookup[number].books[0]].title}",
                f"第 {number} 阶段 ·《{journey_book_lookup[stage_lookup[number].books[0]].title}》",
            ),
            key=progress_stage_key,
        )
        selected_progress_stage = stage_lookup[selected_stage_number]
        selected_progress_book = journey_book_lookup[selected_progress_stage.books[0]]
        selected_progress_state = progress_by_book.get(selected_progress_book.canonical_id, {})
        status_values = ["planned", "reading", "paused", "completed"]
        status_labels = {
            "planned": tr("Not started", "尚未开始"),
            "reading": tr("Reading", "正在阅读"),
            "paused": tr("Paused", "暂时搁置"),
            "completed": tr("Completed", "已读完"),
        }
        progress_notice = st.session_state.pop("progress_notice", None)
        if progress_notice:
            st.markdown(interaction_result_html("progress-saved"), unsafe_allow_html=True)
            st.success(progress_notice)
        feedback_notice = st.session_state.pop("feedback_notice", None)
        if feedback_notice:
            st.markdown(interaction_result_html("book-feedback-result"), unsafe_allow_html=True)
            if feedback_notice["changed"]:
                st.success(feedback_notice["message"])
            else:
                st.info(feedback_notice["message"])
        with st.form(f"reading_progress_form_{ui_language}_{profile.user_id}_{selected_progress_book.canonical_id}"):
            st.markdown(
                '<span class="atlas-sr-only" data-atlas-learning-loop-form data-atlas-form-target="progress-saved" data-atlas-wait-result></span>',
                unsafe_allow_html=True,
            )
            progress_column, status_column = st.columns([1.45, 1])
            with progress_column:
                progress_percent = st.slider(
                    tr("Reading progress", "阅读进度"),
                    0,
                    100,
                    int(selected_progress_state.get("progress_percent", 0)),
                    5,
                    format="%d%%",
                )
            with status_column:
                saved_status = str(selected_progress_state.get("status", "planned"))
                reading_status = st.selectbox(
                    tr("Reading status", "阅读状态"),
                    status_values,
                    index=status_values.index(saved_status) if saved_status in status_values else 0,
                    format_func=lambda value: status_labels[value],
                )
            set_current = st.checkbox(
                tr("Show this as my current book", "将这本书设为当前阅读"),
                value=bool(selected_progress_state.get("is_current"))
                or selected_progress_book.canonical_id == current_book.canonical_id,
            )
            save_progress = st.form_submit_button(
                tr("Save reading progress", "保存阅读进度"),
                type="primary",
            )
        if save_progress:
            saved_percent, saved_status, next_book_id = save_progress_with_stage_handoff(
                result,
                profile,
                ui_language,
                selected_progress_book,
                selected_stage_number,
                int(progress_percent),
                reading_status,
                set_current=set_current,
            )
            if next_book_id:
                next_book = journey_book_lookup[next_book_id]
                next_stage_number = next(
                    (
                        stage.stage_number
                        for stage in result.reading_path.stages
                        if next_book_id in stage.books
                    ),
                    selected_stage_number,
                )
                st.session_state[pending_progress_stage_key] = next_stage_number
                st.session_state["progress_notice"] = tr(
                    f'“{selected_progress_book.title}” is complete. Current reading advanced to “{next_book.title}”.',
                    f'《{selected_progress_book.title}》已完成，当前阅读已自动进入下一阶段《{next_book.title}》。',
                )
                progress_next_step = tr(
                    f'Start “{next_book.title}” and note one question from the first reading session.',
                    f'开始阅读《{next_book.title}》，并记录第一次阅读中遇到的一个问题。',
                )
            elif saved_status == "completed" and next_stage_book_id(result, selected_stage_number) is None:
                st.session_state["progress_notice"] = tr(
                    "All reading stages are complete. Your path is ready for a final reflection.",
                    "所有阅读阶段均已完成，可以开始整条路径的总结与反思。",
                )
                progress_next_step = tr(
                    "Write a short final reflection connecting the three stages.",
                    "写一段简短总结，说明三个阶段的知识怎样相互连接。",
                )
            else:
                st.session_state["progress_notice"] = tr(
                    f'Progress for “{selected_progress_book.title}” saved at {saved_percent}%.',
                    f'《{selected_progress_book.title}》的阅读进度已保存为 {saved_percent}%。',
                )
                next_target = min(100, max(saved_percent + 10, 10))
                progress_next_step = tr(
                    f'Continue “{selected_progress_book.title}” to about {next_target}% and note one unclear point.',
                    f'继续阅读《{selected_progress_book.title}》至约 {next_target}%，并记录一个尚未理解的问题。',
                )
            progress_loop_settings = database.load_mentor_settings(
                profile.user_id, language=ui_language
            )
            progress_loop_settings.update(
                {
                    "last_check_in_at": datetime.now(UTC).isoformat(),
                    "next_step": progress_next_step,
                }
            )
            database.save_mentor_settings(
                profile.user_id, progress_loop_settings, language=ui_language
            )
            st.rerun()

        st.markdown(f"#### {tr('Recommendation feedback', '推荐反馈')}")
        st.caption(tr(
            "Tell Atlas why a recommendation is not working. Your feedback is saved even if you do not replace the book yet.",
            "如果推荐不合适，可以告诉 Atlas 原因；即使暂时不换书，反馈也会保存。",
        ))
        feedback_reasons = [
            "not_relevant",
            "too_difficult",
            "too_basic",
            "too_theoretical",
            "already_read",
            "cannot_access",
            "other",
        ]
        feedback_labels = {
            "not_relevant": tr("Not relevant to my goal", "与学习目标不符"),
            "too_difficult": tr("Too difficult right now", "目前难度过高"),
            "too_basic": tr("Too basic", "内容过于基础"),
            "too_theoretical": tr("Too theoretical", "内容偏理论"),
            "already_read": tr("I have already read it", "我已经读过"),
            "cannot_access": tr("I cannot access this edition", "无法获取这个版本"),
            "other": tr("Another reason", "其他原因"),
        }
        with st.form(f"book_feedback_form_{ui_language}_{profile.user_id}_{selected_progress_book.canonical_id}"):
            st.markdown(
                '<span class="atlas-sr-only" data-atlas-learning-loop-form data-atlas-form-target="book-feedback-result" data-atlas-wait-result></span>',
                unsafe_allow_html=True,
            )
            feedback_reason = st.selectbox(
                tr("What is not working?", "这本书哪里不合适？"),
                feedback_reasons,
                format_func=lambda value: feedback_labels[value],
            )
            feedback_note = st.text_area(
                tr("Additional note (optional)", "补充说明（可选）"),
                max_chars=1000,
                placeholder=tr(
                    "For example: I need a more practical introduction with worked examples.",
                    "例如：我更需要一本包含实践案例的入门书。",
                ),
            )
            replace_from_feedback = st.checkbox(
                tr(
                    "Ask Atlas to find and replace only this book now",
                    "请 Atlas 现在核验并只替换这一本书",
                ),
                value=False,
            )
            save_feedback = st.form_submit_button(tr("Send feedback to Atlas", "把反馈交给 Atlas"))
        if save_feedback:
            database.save_book_feedback(
                profile.user_id,
                selected_progress_book.canonical_id,
                selected_stage_number,
                feedback_reason,
                feedback_note,
                language=ui_language,
            )
            if replace_from_feedback:
                feedback_message = tr(
                    f"Replace only {selected_progress_book.title}. Reason: {feedback_labels[feedback_reason]}. {feedback_note}",
                    f"请只替换《{selected_progress_book.title}》。原因：{feedback_labels[feedback_reason]}。{feedback_note}",
                )
                with st.status(
                    tr("Atlas is finding a verified alternative…", "Atlas 正在核验并筛选替代书目……"),
                    expanded=True,
                ) as feedback_status:
                    result = run_mentor_turn(
                        scope=book_conversation_scope(selected_progress_book),
                        message=feedback_message,
                        result=result,
                        profile=profile,
                        goal=goal,
                        stage_number=selected_stage_number,
                        book=selected_progress_book,
                        language=ui_language,
                    )
                    feedback_status.update(
                        label=tr("Atlas responded", "Atlas 已完成处理"),
                        state="complete",
                        expanded=False,
                    )
                replacement_stage = next(s for s in result.reading_path.stages if s.stage_number == selected_stage_number)
                did_replace = replacement_stage.books[0] != selected_progress_book.canonical_id
                replacement_title = next(b.title for b in result.selected_books if b.canonical_id == replacement_stage.books[0])
                st.session_state["feedback_notice"] = {"changed": did_replace, "message": (
                    tr(f"Stage {selected_stage_number} now uses {replacement_title}. Other books and their progress are unchanged.",
                       f"第 {selected_stage_number} 阶段已换成《{replacement_title}》，其他书籍与已记录进度保持不变。") if did_replace else
                    tr("Your feedback is saved. Atlas did not find a suitable verified replacement, so the original book is unchanged. Try specifying a title, language, or preferred approach.",
                       "反馈已保存。Atlas 暂时没有找到足够合适、可核验的替代书，因此保留了原书。你可以补充书名、语言或希望的讲解方式再试。"))}
                st.rerun()
            else:
                database.save_mentor_message(
                    profile.user_id,
                    book_conversation_scope(selected_progress_book),
                    "user",
                    tr(
                        f"Feedback: {feedback_labels[feedback_reason]}. {feedback_note}",
                        f"反馈：{feedback_labels[feedback_reason]}。{feedback_note}",
                    ),
                    {"intent": "feedback", "reason": feedback_reason},
                    language=ui_language,
                )
                st.markdown(interaction_result_html("book-feedback-result"), unsafe_allow_html=True)
                st.success(tr(
                    "Feedback saved to this book's conversation. The path has not been changed.",
                    "反馈已记入这本书的对话，当前阅读路径尚未更改。",
                ))
        st.markdown(
            f'[{tr("Search for and assess a replacement book", "搜索并评估替代书目")}](#book-search)'
        )
        st.divider()
        st.write(f"**{tr('Learning goal', '目标')}{label_separator}** {goal.topic} · {goal.duration_weeks} {tr('weeks', '周')} · {goal.hours_per_week:g} {tr('hours/week', '小时/周')}")
        for stage in result.reading_path.stages:
            st.write(
                f"**{stage.stage_number}. {reading_stage_title(stage.title, ui_language)}** — {stage.estimated_hours:g} {tr('h', '小时')}  \n"
                f"{stage.learning_objective}"
            )
        mastery_items = st.session_state.get("mastery", [])
        if mastery_items:
            st.write(f"**{tr('Current understanding', '当前知识掌握度')}**")
            for item in mastery_items:
                st.progress(item.mastery_score, text=f"{item.concept}: {item.mastery_score:.0%}")

    with diagnostic_tab:
        st.markdown(
            f'<h3 class="atlas-tool-title">{tr("Check your understanding", "检查理解情况")}</h3>',
            unsafe_allow_html=True,
        )
        st.caption(tr(
            "One multiple-choice question, one true/false question, and a short explanation. Review answers and reasoning when you're done.",
            "一道单选、一道判断，再用几句话说说你的理解。答完查看解析和改进建议。",
        ))
        question_bank = loop_settings.get("question_bank", {})
        question_record = question_bank.get(diagnostic_context, {})
        try:
            questions = [DiagnosticQuestion.model_validate(q) for q in question_record.get("questions", [])]
        except (ValueError, TypeError):
            logging.warning("Saved practice questions could not be loaded")
            questions = []
            st.warning(tr("This saved set could not be opened. Generate a new set below.", "这组旧练习暂时无法打开，请重新生成。"))
        with st.form(f"generate_check_{ui_language}_{diagnostic_context}", border=False):
            st.markdown('<span class="atlas-sr-only" data-atlas-form-target="check-questions" data-atlas-wait-result></span>', unsafe_allow_html=True)
            generate_check = st.form_submit_button(
                tr("Try a new set", "换一组练习") if questions else tr("Create 3 practice questions", "生成 3 道练习"),
                type="secondary" if questions else "primary",
            )
        if generate_check:
            try:
                with st.spinner(tr("Atlas is designing questions and checking the answer criteria…", "Atlas 正在设计题目和评阅要点……")):
                    generated = generate_questions(goal, profile, current_book, current_stage,
                        create_learning_provider(settings) if settings.llm_provider != "mock" else None,
                        recent_questions=questions)
                unchanged = same_question_set(questions, generated)
                if not unchanged:
                    questions = generated
                    new_payload = [q.model_dump() for q in questions]
                    question_record = {"questions": new_payload, "revision": datetime.now(UTC).isoformat()}
                    question_bank[diagnostic_context] = question_record
                    loop_settings["question_bank"] = question_bank
                    # Only a genuinely new set replaces the previous answers.
                    loop_settings.get("answer_reviews", {}).pop(diagnostic_context, None)
                    database.save_mentor_settings(profile.user_id, loop_settings, language=ui_language)
                st.markdown(interaction_result_html("check-questions"), unsafe_allow_html=True)
                if unchanged:
                    st.info(tr("No different set is available yet. Your questions, answers and feedback are unchanged.", "暂时没有生成不同的题目，已保留当前练习、回答和点评。"))
                else:
                    st.success(tr("Your new questions are ready below.", "新题目已准备好，请在下方作答。"))
            except Exception:
                logging.exception("Question generation failed")
                st.markdown(interaction_result_html("check-questions"), unsafe_allow_html=True)
                st.warning(tr("Question generation is unavailable. Your existing questions and answers are unchanged; try again later.", "暂时无法生成新题，原有题目和回答保持不变，请稍后重试。"))
        if questions:
            question_revision = question_record.get("revision", "starter")
            if any(q.generation_source == "local" for q in questions):
                st.caption(tr(
                    "Foundational practice · The online question designer is unavailable. These are general subject exercises, not a test of your book's exact contents.",
                    "基础练习 · 在线出题暂不可用，以下用于练习相关领域的基础思路，不代表本书或细分方向的完整测验。",
                ))
            prior_review = loop_settings.get("answer_reviews", {}).get(diagnostic_context, {})
            saved_answers = prior_review.get("answers", []) if prior_review.get("revision") == question_revision else []
            with st.form(
                f"diagnostic_form_{ui_language}_{profile.user_id}_{diagnostic_context}_{question_revision}"
            ):
                st.markdown(
                    f'<span class="atlas-sr-only" data-atlas-knowledge-check-form data-atlas-form-target="knowledge-check-results" data-atlas-wait-result>'
                    f'{tr("Knowledge check form", "知识自测表单")}</span>',
                    unsafe_allow_html=True,
                )
                answers = question_inputs(
                    questions, is_zh=is_zh, saved_answers=saved_answers,
                    key_prefix=f"diag_{ui_language}_{profile.user_id}_{diagnostic_context}_{question_revision}",
                )
                diagnose = st.form_submit_button(tr("Check answers and get feedback", "提交答案，查看点评"), type="primary")
            diagnosed_mastery = []
            if diagnose:
                if not any(a.strip() for a in answers):
                    st.warning(tr("Answer at least one question. Unanswered questions will not be assessed.", "请至少回答一道题；未作答的题目不会评估，也不会降低你的已有结果。"))
                else:
                    try:
                        with st.spinner(tr("Atlas is checking your reasoning, examples and possible misconceptions…", "Atlas 正在逐题检查推理、例子和可能的误区……")):
                            reviewed = review_answers(questions, answers,
                                context=learning_context(goal, profile, current_book, current_stage),
                                provider=create_learning_provider(settings) if settings.llm_provider != "mock" else None)
                        diagnosed_mastery = review_mastery(questions, reviewed)
                        saved_reviews = loop_settings.get("answer_reviews", {})
                        saved_reviews[diagnostic_context] = {
                            "reviews": [r.model_dump() for r in reviewed],
                            "answers": answers, "revision": question_revision,
                            "reviewed_at": datetime.now(UTC).isoformat(),
                        }
                        loop_settings["answer_reviews"] = saved_reviews
                        database.save_mentor_settings(profile.user_id, loop_settings, language=ui_language)
                        st.success(tr("Feedback saved. Your learning plan is unchanged.", "点评已保存，学习计划未改动。"))
                    except Exception:
                        logging.exception("Semantic knowledge check failed")
                        st.error(tr("Atlas could not complete the review. Your answers remain in the form; retry when the model is available. No assessment or mastery update was recorded.", "本次点评未完成，回答仍保留在输入框中，请稍后重试。没有记录评估分数，也没有更新掌握情况。"))
                st.markdown(interaction_result_html("knowledge-check-results"), unsafe_allow_html=True)
            if diagnosed_mastery:
                diagnosed_mastery = merge_mastery(st.session_state.get("mastery", []), diagnosed_mastery)
                st.session_state["mastery"] = diagnosed_mastery
                weakest = min(diagnosed_mastery, key=lambda item: item.mastery_score)
                stored_mastery_by_context = loop_settings.get("mastery_by_context", {})
                if not isinstance(stored_mastery_by_context, dict):
                    stored_mastery_by_context = {}
                stored_mastery_by_context[diagnostic_context] = [
                    item.model_dump(mode="json") for item in diagnosed_mastery
                ]
                stored_lowest_by_context = loop_settings.get("lowest_mastery_by_context", {})
                if not isinstance(stored_lowest_by_context, dict):
                    stored_lowest_by_context = {}
                stored_lowest_by_context[diagnostic_context] = weakest.concept
                loop_settings.update(
                    {
                        "mastery_by_context": stored_mastery_by_context,
                        "lowest_mastery_by_context": stored_lowest_by_context,
                        "active_mastery_context": diagnostic_context,
                        "last_diagnosis_at": datetime.now(UTC).isoformat(),
                        "last_check_in_at": datetime.now(UTC).isoformat(),
                        "next_step": tr(
                            f"Review {weakest.concept}, then answer one recall question without notes.",
                            f"先复习“{weakest.concept}”，再脱离笔记完成一道主动回忆题。",
                        ),
                    }
                )
                database.save_mentor_settings(
                    profile.user_id, loop_settings, language=ui_language
                )
                # Surface the diagnosis in the adaptation module on this rerun. A
                # stable widget key otherwise keeps its earlier empty value and
                # hides the hand-off between diagnosis and planning.
                st.session_state[f"adapt_concept_{ui_language}_{profile.user_id}"] = weakest.concept
            review_record = loop_settings.get("answer_reviews", {}).get(diagnostic_context, {})
            if questions and review_record and review_record.get("revision") == question_revision:
                st.markdown(f"**{tr('Last saved feedback', '最近保存的点评')}**")
                st.caption(tr("Feedback covers the submitted answers, not the whole book. Resubmit after editing to update it.", "这里只评估已提交的回答，不代表整本书的掌握程度。修改答案后需重新提交。"))
                saved_feedback(review_record["reviews"], is_zh=is_zh)

    with session_tab:
        st.markdown(
            f'<h3 class="atlas-tool-title">{tr("Get help with an excerpt", "请 Atlas 讲解原文")}</h3>',
            unsafe_allow_html=True,
        )
        st.caption(tr(
                "Paste a short passage and ask a specific question. Atlas separates text evidence from general explanations and offers a recall prompt.",
                "粘贴一小段原文并提出具体问题；Atlas 会区分原文依据和补充解释，再给你一道回忆练习。",
        ))
        reading_focus_concept = (
            current_stage.concepts[0] if current_stage.concepts else goal.topic
        )
        reading_support_key = f"reading_support_{ui_language}_{diagnostic_context}"
        with st.form(
            f"reading_session_form_{ui_language}_{profile.user_id}_{diagnostic_context}"
        ):
            st.markdown(
                '<span class="atlas-sr-only" data-atlas-learning-loop-form data-atlas-form-target="excerpt-result" data-atlas-wait-result></span>',
                unsafe_allow_html=True,
            )
            st.write(f"{tr('Now reading', '正在阅读')}{label_separator} **{current_book.title}**")
            chapter = st.text_input(
                tr("Current chapter or section (optional)", "当前章节（可选）"),
                key=f"reading_chapter_{ui_language}_{profile.user_id}_{diagnostic_context}",
            )
            excerpt = st.text_area(
                tr("Paste a short excerpt you are allowed to share", "粘贴一段可合法使用的原文"),
                height=130,
                max_chars=6000,
                placeholder=tr(
                    "Atlas analyzes only the text you provide and does not access the full book.",
                    "Atlas 只分析你提供的文字，不会假定能够访问整本书。",
                ),
                key=f"reading_excerpt_{ui_language}_{profile.user_id}_{diagnostic_context}",
            )
            notes = st.text_area(
                tr("Your notes", "你的笔记"),
                height=90,
                key=f"reading_notes_{ui_language}_{profile.user_id}_{diagnostic_context}",
            )
            question = st.text_input(
                tr("What would you like help with?", "你想弄清楚什么？"),
                placeholder=tr("For example: Are my notes correct? Why does this step matter?",
                               "例如：我的理解对吗？这里为什么要这样做？"),
                max_chars=1000,
                key=f"reading_question_{ui_language}_{profile.user_id}_{diagnostic_context}",
            )
            support = st.form_submit_button(tr("Get reading guidance", "生成阅读辅导"), type="primary")
        if support:
            st.session_state.pop(reading_support_key, None)
            if len(excerpt.strip()) < 10:
                st.error(tr(
                    "Paste at least 10 characters from the passage you want help with.",
                    "请粘贴至少 10 个字符的原文，再生成阅读辅导。",
                ))
            elif len(question.strip()) < 2:
                st.error(tr(
                    "Enter a question about the passage.",
                    "请输入你想针对这段原文弄清楚的问题。",
                ))
            else:
              try:
                session_input = ReadingSessionInput(
                    book_title=current_book.title,
                    chapter=chapter or None,
                    notes=notes,
                    excerpt=excerpt,
                    question=question,
                    target_concept=reading_focus_concept,
                    response_language="Chinese" if is_zh else "English",
                )
                provider = create_learning_provider(settings)
                with st.spinner(tr("Atlas is reading your passage and preparing an explanation…", "Atlas 正在阅读这段原文，并整理讲解与练习……")):
                    output = support_reading(session_input, provider=provider)
                st.session_state[reading_support_key] = output
                AtlasDatabase(settings.resolved_database_path).save_reading_session(
                    profile.user_id,
                    {
                        "input": session_input.model_dump(mode="json"),
                        "output": output.model_dump(mode="json"),
                        "llm_provider": settings.llm_provider,
                        "model_id": settings.bedrock_learning_model_id or settings.bedrock_model_id or None,
                    },
                )
                loop_settings.update(
                    {
                        "last_support_at": datetime.now(UTC).isoformat(),
                        "last_support_book": current_book.title,
                        "next_step": output.reflection_task,
                    }
                )
                database.save_mentor_settings(
                    profile.user_id, loop_settings, language=ui_language
                )
              except Exception:
                logging.exception("Reading support failed")
                st.error(
                    tr(
                        "Atlas could not complete a verified explanation. Your passage and question are still in the form; please retry. No new guidance was saved.",
                        "Atlas 暂时没能完成可靠的原文讲解。原文和问题仍保留在输入框中，请稍后重试；本次未保存新的辅导结果。",
                    )
                )
            st.markdown(interaction_result_html("excerpt-result"), unsafe_allow_html=True)
        output = st.session_state.get(reading_support_key)
        if output:
            st.success(tr(
                "This guidance is grounded in the excerpt you supplied. Atlas saved the reflection task as your next step.",
                    "讲解已完成，原文依据与补充说明可在下方查看；反思练习已记为下一步任务。",
            ))
            st.write(f"**{tr('Key explanation', '要点讲解')}{label_separator}** {output.explanation}")
            with st.expander(tr("Text evidence and connections", "查看原文依据与知识关联")):
                st.write(output.grounding)
                st.write(output.connection)
                st.write(f"**{tr('Think about this', '理解提示')}{label_separator}** {output.guiding_question}")
            st.info(f"{tr('Recall challenge', '主动回忆')}{label_separator} {output.recall_question}")
            st.write(f"**{tr('Reflection exercise', '反思练习')}{label_separator}** {output.reflection_task}")
            for limitation in output.limitations:
                st.caption(limitation)

    with adaptation_tab:
        st.markdown(
            f'<h3 class="atlas-tool-title">{tr("Adjust the learning plan", "调整学习计划")}</h3>',
            unsafe_allow_html=True,
        )
        st.caption(tr(
            "Confirm the constraints that have actually changed. Atlas creates a new active version and keeps the previous version for comparison.",
            "只填写确实发生的变化。Atlas 会生成新的当前版本，并保留旧版本供你对照。",
        ))
        lowest_mastery_by_context = loop_settings.get("lowest_mastery_by_context", {})
        suggested_low_concept = (
            str(lowest_mastery_by_context.get(diagnostic_context, ""))
            if isinstance(lowest_mastery_by_context, dict)
            else ""
        )
        adaptation_concept_key = f"adapt_concept_{ui_language}_{profile.user_id}"
        if adaptation_concept_key not in st.session_state:
            st.session_state[adaptation_concept_key] = suggested_low_concept
        with st.form(f"adaptation_form_{ui_language}_{profile.user_id}"):
            st.markdown(
                '<span class="atlas-sr-only" data-atlas-learning-loop-form data-atlas-form-target="plan-updated" data-atlas-wait-result></span>',
                unsafe_allow_html=True,
            )
            new_hours = st.number_input(
                tr("Available hours per week", "调整后每周可投入时间（小时）"),
                0.5,
                20.0,
                float(goal.hours_per_week),
                0.5,
                key=f"adapt_hours_{ui_language}_{profile.user_id}",
            )
            too_theoretical = st.checkbox(
                tr("The first book is too theoretical", "第一本书偏理论"),
                value=False,
                key=f"adapt_theory_{ui_language}_{profile.user_id}",
            )
            low_concept = st.text_input(
                tr("Concept you are still unsure about", "尚未掌握的概念"),
                key=adaptation_concept_key,
            )
            adapt = st.form_submit_button(tr("Update my plan and show what changed", "调整路径并说明原因"), type="primary")
        if adapt:
            no_confirmed_change = (
                abs(float(new_hours) - float(goal.hours_per_week)) < 0.001
                and not too_theoretical
                and not low_concept.strip()
            )
            if no_confirmed_change:
                st.markdown(interaction_result_html("plan-updated"), unsafe_allow_html=True)
                st.warning(tr(
                    "Nothing has changed yet. Update at least one constraint before creating a new plan version.",
                    "目前没有需要调整的内容。请至少修改一项条件，再生成新版本。",
                ))
            else:
                previous_path = result.reading_path.model_copy(deep=True)
                revised, revision = replan_path(
                    previous_path,
                    goal,
                    float(new_hours),
                    too_theoretical,
                    low_concept.strip() or None,
                )
                revised_result = result.model_copy(
                    update={
                        "reading_path": revised,
                        "execution_trace": [
                            *result.execution_trace,
                            f"ADAPT · activated reading path version {revised.version}",
                        ],
                    }
                )
                updated_goal = goal.model_copy(
                    update={"hours_per_week": float(new_hours)}
                )
                database.save_path(revised)
                database.save_revision(revised.path_id, revision)
                database.save_user(profile, updated_goal, ui_language)
                database.save_recommendation(
                    profile.user_id, revised_result, ui_language
                )
                loop_settings = database.load_mentor_settings(
                    profile.user_id, language=ui_language
                )
                loop_settings.update(
                    {
                        "last_adaptation_at": datetime.now(UTC).isoformat(),
                        "active_path_version": revised.version,
                        "next_step": tr(
                            f"Explain {low_concept.strip()} in one or two sentences, and share what is still unclear."
                            if low_concept.strip() else "Continue your current book within the updated weekly schedule, then report one useful idea or question.",
                            f"用一两句话说说你对“{low_concept.strip()}”的理解，不确定的地方也可以一起告诉 Atlas。"
                            if low_concept.strip() else "按新的每周时间安排继续读当前这本书，再汇报一条收获或一个疑问。",
                        ),
                    }
                )
                database.save_mentor_settings(
                    profile.user_id, loop_settings, language=ui_language
                )
                st.session_state["previous_path"] = previous_path
                st.session_state["revised_path"] = revised
                st.session_state["plan_revision"] = revision
                st.session_state["recommendation"] = revised_result
                st.session_state["goal"] = updated_goal
                st.session_state["plan_notice"] = tr(
                    f"Plan v{revised.version} is now active. Your reading progress was preserved.",
                    f"路径 v{revised.version} 已设为当前方案，原有阅读进度保持不变。",
                )
                st.rerun()
        plan_notice = st.session_state.pop("plan_notice", None)
        if plan_notice:
            st.markdown(interaction_result_html("plan-updated"), unsafe_allow_html=True)
            st.success(plan_notice)
        revised = st.session_state.get("revised_path")
        previous_path_payload = st.session_state.get("previous_path")
        revision = st.session_state.get("plan_revision")
        if revised and revision and previous_path_payload:
            previous_path = ReadingPath.model_validate(
                previous_path_payload.model_dump(mode="python")
                if isinstance(previous_path_payload, ReadingPath)
                else previous_path_payload
            )
            before, after = st.columns(2)
            with before:
                st.markdown(f"### {tr('Previous plan', '调整前')} · v{previous_path.version}")
                st.metric(tr("Total reading time", "总时长"), f"{previous_path.total_estimated_hours:g} {tr('h', '小时')}")
                for stage in previous_path.stages:
                    st.write(f"{stage.stage_number}. {reading_stage_title(stage.title, ui_language)} · {stage.estimated_hours:g} {tr('h', '小时')}")
            with after:
                st.markdown(f"### {tr('Active plan', '当前方案')} · v{revised.version}")
                st.metric(tr("Total reading time", "总时长"), f"{revised.total_estimated_hours:g} {tr('h', '小时')}")
                for stage in revised.stages:
                    st.write(f"{stage.stage_number}. {reading_stage_title(stage.title, ui_language)} · {stage.estimated_hours:g} {tr('h', '小时')}")
            st.success(revision.explanation)
            st.write(f"**{tr('Reason for change', '调整原因')}{label_separator}** {revision.trigger}")
            st.write(f"**{tr('Perspectives retained', '保留的学科视角')}{label_separator}** {', '.join(revision.preserved_goals)}")
        saved_versions = database.load_paths(result.reading_path.path_id)
        if saved_versions:
            version_labels = " → ".join(f"v{item.version}" for item in saved_versions)
            st.caption(tr(
                f"Saved plans: {version_labels}. Open Plan history to review an earlier version.",
                f"已保存方案：{version_labels}。可以在左侧“历史方案”中查看旧版本。",
            ))
    with sidebar_settings:
        technical_details = st.expander(tr("Technical run details", "技术运行详情"), expanded=False)
    with technical_details:
        st.caption(tr(
            "These audit details show how Atlas searched, checked, and selected the books in the active plan.",
            "这里保留 Atlas 检索、核验和筛选当前方案书目的技术记录，便于核查。",
        ))
        st.markdown(execution_trace_html(result.execution_trace), unsafe_allow_html=True)
else:
    st.markdown(navigation_empty_state_html(is_zh), unsafe_allow_html=True)

st.html(
    hash_navigation_html() + form_scroll_restoration_html(),
    unsafe_allow_javascript=True,
    width="stretch",
)
