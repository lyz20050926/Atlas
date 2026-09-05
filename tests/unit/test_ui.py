from __future__ import annotations

import re

from src.models import (
    BookAssessment,
    BookCandidate,
    BookSearchEvaluation,
    EvidenceRecord,
    ReadingPath,
    ReadingStage,
)
from src.ui import (
    accountability_card_html,
    activity_history_html,
    atlas_theme_css,
    book_cover_html,
    book_fit_result_html,
    brand_html,
    companion_preview_html,
    concept_card_html,
    fit_score_dimensions,
    form_scroll_restoration_html,
    hash_navigation_html,
    hero_html,
    learning_goal_editor_html,
    mobile_navigation_html,
    navigation_empty_state_html,
    reading_dashboard_html,
    reading_session_completion_html,
    reading_session_timer_html,
    section_anchor,
    section_header,
    sidebar_navigation_html,
    topbar_html,
    workspace_intro_html,
)


def visible_text(html: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def test_compact_section_header_omits_redundant_visual_heading() -> None:
    html = section_header("02 · 知识地图", "", "Atlas 会据此匹配合适的书籍。")
    css = atlas_theme_css()

    assert 'class="atlas-section-head compact"' in html
    assert "<h2>" not in html
    assert "02 · 知识地图" in html
    assert "Atlas 会据此匹配合适的书籍。" in html
    assert ".atlas-section-head.compact .atlas-section-index" in css
    assert "font-size: clamp(.94rem, .9rem + .15vw, 1.02rem)" in css
    assert "color: var(--atlas-accent-deep)" in css


def test_concept_card_omits_redundant_ordinal_number() -> None:
    html = concept_card_html("基础概念", "核心概念与基本术语", "重要程度", "核心")
    css = atlas_theme_css()

    assert "atlas-card-number" not in html
    assert ">01<" not in html
    assert "基础概念" in html
    assert "核心概念与基本术语" in html
    assert "min-height: 132px" in css


def test_learning_goal_editor_makes_replanning_visible_and_safe() -> None:
    zh_html = learning_goal_editor_html(True, topic="机器学习")
    en_html = learning_goal_editor_html(False, topic="Machine Learning")
    css = atlas_theme_css()

    assert "当前学习目标" in zh_html
    assert "正在学习：机器学习" in zh_html
    assert "保留已有进度" in zh_html
    assert "已有基础" in zh_html
    assert "CURRENT LEARNING GOAL" in en_html
    assert "Learning now: Machine Learning" in en_html
    assert "Progress stays saved" in en_html
    assert ".st-key-atlas_goal_editor" in css
    assert ".atlas-goal-entry-badge" in css


def test_brand_uses_nexmind_agentic_intelligence_lockup() -> None:
    html = brand_html()

    assert "NexMind — Agentic Intelligence" in html
    assert html.count('src="app/static/nexmind-logo.png"') == 2
    assert "atlas-brand-wordmark" in html
    assert "NexMind Atlas" not in html


def test_reading_dashboard_matches_workspace_structure_and_escapes_content() -> None:
    html = reading_dashboard_html(
        is_zh=True,
        topic="具身智能<script>alert(1)</script>",
        duration_weeks=6,
        stage_labels=["基础概念", "技术原理与应用", "批判思考与跨学科视角"],
        book_title="具身心智：认知科学和人类经验",
        authors=["作者甲"],
        reason="建立有证据支持的概念基础。",
        confidence="high",
        source_links=[("Google Books", "https://books.google.com/example")],
        data_mode="live",
    )

    assert '<main class="journey-page"' in html
    assert 'id="reading-journey" aria-labelledby="reading-journey-title"' in html
    assert '<div class="journey-page-title" id="reading-journey-title" role="heading" aria-level="1">阅读旅程</div>' in html
    assert 'class="journey-primary-grid"' in html
    assert 'class="journey-panel journey-sources"' in html
    assert 'class="journey-panel journey-agent"' not in html
    assert 'id="journey-foundation"' not in html
    assert 'id="agent-progress"' not in html
    assert 'aria-label="具身心智：认知科学和人类经验"' in html
    assert '>具身心智</h2>' in html
    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "可信路径基础" not in html
    assert "进行中" not in html
    assert "待更新" not in html
    assert 'aria-valuenow="80"' not in html
    assert 'class="journey-agent-state done"' not in html
    assert 'class="journey-mentor-link" href="#book-stage-1"' in html
    assert "和 Atlas 聊这本书" in html
    assert "学习状态" in html
    assert "核验书目信息" not in html
    assert "学习者模型" not in html


def test_atlas_introduction_is_bilingual_and_points_to_real_workspaces() -> None:
    chinese = hero_html(True, has_path=True)
    english = hero_html(False, has_path=False)

    assert "找到适合你的书" in chinese
    assert "把疑问变成理解" in chinese
    assert "学习目标和已有基础" in chinese
    assert "核对书籍、安排阅读顺序" in chinese
    assert "小练习和进度反馈" in chinese
    assert "调整后续计划" in chinese
    assert "atlas-hero-zh" in chinese
    assert 'id="atlas-introduction-title" role="heading" aria-level="1"' in chinese
    assert 'aria-labelledby="atlas-introduction-title"' in chinese
    assert "\n" not in chinese  # Markdown must not split the SVG into blocks.
    assert "你的智能阅读伙伴" in chinese
    assert "想系统学点什么" not in chinese
    assert "先找到适合你的书" not in chinese
    assert "再陪你一步步读懂" not in chinese
    assert "NEXMIND" not in chinese
    assert "ATLAS · AGENTIC READING COMPANION" not in chinese
    assert "暂停动态" in chinese
    assert 'class="atlas-data-rain"' not in chinese
    assert "atlas-data-stream" not in chinese
    assert 'role="switch"' in chinese
    assert "atlas-hero-visual" in chinese
    assert "atlas-book-scene" in chinese
    assert "atlas-book-pages" in chinese
    assert "atlas-book-network" in chinese
    assert "atlas-book-cover" in chinese
    assert "atlas-book-page-edges" in chinese
    assert "atlas-book-leaf" in chinese
    assert "__NODES__" not in chinese and "__EDGES__" not in chinese
    assert "和 Atlas 聊聊" in chinese
    assert "继续我的阅读" in chinese
    assert "第 2 周" not in chinese
    assert 'href="#reading-journey"' in chinese
    assert 'href="#learning-loop"' in chinese
    assert "From the right book" in english
    assert "to real understanding" in english
    assert "with sources checked and a clear reading order" in english
    assert "test your understanding" in english
    assert "Curious about something new?" not in english
    assert "I’ll find the right books." not in english
    assert "Then we’ll make sense of them." not in english
    assert "NEXMIND" not in english
    assert "ATLAS · AGENTIC READING COMPANION" in english
    assert "Week 2" not in english
    assert "Pause motion" in english
    assert "Ask NexMind" not in english
    assert 'href="#learning-brief"' in english
    assert 'href="#learning-loop"' not in english
    assert english.count("atlas-hero-action primary") == 1
    assert "你好" not in english


def test_hero_book_animation_is_controllable_and_motion_safe() -> None:
    css = atlas_theme_css()

    assert "@keyframes atlas-data-fall" not in css
    assert ".atlas-motion-toggle:checked ~ .atlas-book-scene *" in css
    assert ".atlas-motion-toggle:checked ~ .atlas-book-scene .atlas-book-pages" in css
    assert "@keyframes atlas-book-float" in css
    assert ".atlas-motion-toggle:checked ~ .atlas-book-scene .atlas-book-leaf" in css
    assert "@keyframes atlas-leaf-breathe" in css
    assert "@keyframes atlas-data-flow" in css
    assert "@keyframes atlas-orbit-drift" in css
    assert "@keyframes atlas-signal-breathe" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert ".atlas-signal-card" not in css
    assert ".atlas-hero-orbit" not in css
    assert ".atlas-hero *, .atlas-hero *::before, .atlas-hero *::after { animation: none !important; }" in css
    assert "@container atlas-intro (max-width: 660px)" in css
    assert "min-width: 460px" not in css
    assert ".atlas-book-page { fill:" not in css


def test_activity_history_exposes_saved_versions_without_changing_progress() -> None:
    def path(version: int, title: str) -> ReadingPath:
        return ReadingPath(
            path_id="path-1",
            user_id="learner",
            version=version,
            total_weeks=6,
            total_estimated_hours=3.5,
            stages=[
                ReadingStage(
                    stage_number=1,
                    title=title,
                    learning_objective="建立基础",
                    books=[f"book-{version}"],
                    estimated_hours=3.5,
                )
            ],
            constraints_satisfied=True,
        )

    html = activity_history_html(
        [path(2, "旧方案<script>"), path(3, "当前方案")],
        active_version=3,
        verified_book_count=3,
        data_mode="live",
        is_zh=True,
    )

    assert "你的旧方案仍然保留" in html
    assert "v2" in html and "v3" in html
    assert "当前方案" in html and "历史版本" in html
    assert "不会覆盖先前方案或已经记录的阅读进度" in html
    assert "实时来源" in html
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_reading_dashboard_keeps_full_english_title() -> None:
    book = BookCandidate(
        canonical_id="cover-test",
        title="The Embodied Mind",
        authors=["Francisco Varela"],
        cover_url="https://books.google.com/real-cover.jpg",
    )
    html = reading_dashboard_html(
        is_zh=False,
        topic="Embodied intelligence",
        duration_weeks=6,
        stage_labels=["Foundations", "Robot learning", "Ethics & society"],
        book_title="The Embodied Mind",
        authors=["Francisco Varela"],
        reason="Builds the conceptual foundation.",
        confidence="medium",
        source_links=[],
        data_mode="mixed",
        overview="A verified introduction to embodied cognition and lived experience.",
        book=book,
    )

    assert ">The Embodied Mind</h2>" in html
    assert 'aria-label="Reading Journey"' in html
    assert "Trusted path foundation" not in html
    assert "Complete · Live and sample sources" not in html
    assert "Agent run complete" not in html
    assert "Learner model" not in html
    assert "In progress" not in html
    assert "Pending" not in html
    assert "About this book" in html
    assert "https://books.google.com/real-cover.jpg" in html
    assert 'class="journey-cover-image google-cover"' in html
    assert 'alt="Cover of The Embodied Mind"' in html
    assert 'width="464" height="696"' in html


def test_reading_dashboard_uses_saved_progress_and_current_stage() -> None:
    html = reading_dashboard_html(
        is_zh=False,
        topic="Robotics",
        duration_weeks=6,
        stage_labels=["Foundations", "Systems", "Reflection"],
        book_title="Robot Learning",
        authors=["Example Author"],
        reason="A concise rationale.",
        confidence="high",
        source_links=[],
        data_mode="live",
        progress_percent=45,
        current_stage_number=2,
        stage_progress=[100, 45, 0],
    )

    assert 'aria-label="Reading progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow="45"' in html
    assert '<strong>45%</strong>' in html
    assert html.count('class="journey-stage active selected"') == 1
    assert 'aria-label="Foundations" aria-valuemin="0" aria-valuemax="100" aria-valuenow="100"' in html


def test_long_dashboard_narratives_end_cleanly_and_offer_full_text() -> None:
    overview = (
        "第一句完整说明本书讨论的主要主题与研究范围。"
        "第二句继续补充非常详细的版本信息、阅读建议、章节结构、适用对象和相关背景，"
        "让首页摘要明显超过卡片适合直接展示的长度。第三句继续提供补充信息。"
    )
    reason = (
        "这本书适合作为当前阶段的概念入口。"
        "它还提供了更详细的推荐依据，并结合学习目标、已有基础和后续阶段解释其位置。"
        "第三句提供更多解释，以确保推荐理由需要通过展开控件查看。第四句继续补充。"
    )

    html = reading_dashboard_html(
        is_zh=True,
        topic="具身智能",
        duration_weeks=6,
        stage_labels=["基础概念", "技术原理与应用", "批判思考与跨学科视角"],
        book_title="具身认知论",
        authors=["徐献军"],
        reason=reason,
        confidence="medium",
        source_links=[],
        data_mode="live",
        overview=overview,
    )

    assert html.count('class="journey-narrative-disclosure"') == 2
    assert "展开完整简介" in html
    assert "展开完整推荐理由" in html
    assert "收起" in html
    assert overview in html
    assert reason in html
    assert "…" not in html
    assert "..." not in html


def test_short_dashboard_narratives_do_not_add_disclosure() -> None:
    html = reading_dashboard_html(
        is_zh=False,
        topic="Robotics",
        duration_weeks=4,
        stage_labels=["Concepts", "Systems", "Reflection"],
        book_title="Robot Learning",
        authors=["Example Author"],
        reason="A concise and complete rationale.",
        confidence="high",
        source_links=[],
        data_mode="live",
        overview="A concise and complete overview.",
    )

    assert "journey-narrative-disclosure" not in html
    assert html.count('class="journey-narrative-copy"') == 2


def test_reading_dashboard_does_not_persist_completed_generation_steps() -> None:
    html = reading_dashboard_html(
        is_zh=True,
        topic="具身智能",
        duration_weeks=6,
        stage_labels=["基础概念", "技术原理与应用", "批判思考与跨学科视角"],
        book_title="具身心智",
        authors=["作者甲"],
        reason="建立概念基础。",
        confidence="medium",
        source_links=[],
        data_mode="cached_demo",
    )

    assert "已完成 · 缓存示例" not in html
    assert "进行中" not in html
    assert 'class="journey-agent-state done"' not in html
    assert 'class="journey-model-value">0%</span>' in html


def test_reading_dashboard_stage_navigation_separates_view_from_active_progress() -> None:
    html = reading_dashboard_html(
        is_zh=True,
        topic="具身智能",
        duration_weeks=6,
        stage_labels=["基础概念", "技术原理与应用", "批判思考与跨学科视角"],
        book_title="具身认知论",
        authors=["徐献军"],
        reason="回顾概念基础。",
        confidence="medium",
        source_links=[],
        data_mode="live",
        progress_percent=100,
        current_stage_number=1,
        active_stage_number=2,
        active_progress_percent=35,
        stage_progress=[100, 35, 0],
        user_id="demo learner",
        interface_language="zh",
    )

    assert "阶段回顾" in html
    assert "主线学习仍在第 2 阶段" in html
    assert "查看、复习或预览不会改变已保存的进度" in html
    assert "stage_view=1" in html
    assert "user_id=demo+learner" in html
    assert 'class="journey-stage selected complete"' in html
    assert 'class="journey-stage active"' in html
    assert "返回当前阶段" in html


def test_accountability_card_explains_companion_state_and_local_limit() -> None:
    active = accountability_card_html(
        is_zh=True,
        next_step="阅读 25 分钟",
        cadence="每天",
        target_minutes=25,
        enabled=True,
        companion_enabled=True,
        check_in_due=True,
    )
    inactive = accountability_card_html(
        is_zh=False,
        next_step="Read for 25 minutes",
        cadence="Daily",
        target_minutes=25,
        enabled=False,
        companion_enabled=False,
        check_in_due=False,
    )

    assert "小 Atlas 在等你汇报" in active
    assert "不会在后台" in active
    assert 'class="atlas-accountability-card is-due"' in active
    assert "Progress check-ins are off" in inactive
    assert 'class="atlas-accountability-card is-off"' in inactive


def test_reading_session_timer_is_scoped_and_bilingual() -> None:
    chinese = reading_session_timer_html(
        is_zh=True,
        book_title="迁移学习",
        target_minutes=25,
        elapsed_seconds=60,
    )
    english = reading_session_timer_html(
        is_zh=False,
        book_title="Transfer Learning",
        target_minutes=30,
        elapsed_seconds=120,
    )

    assert "小 Atlas 正在为你计时" in chinese
    assert "正在阅读《迁移学习》" in chinese
    assert "const total = 1500" in chinese
    assert "const startedElapsed = 60" in chinese
    assert "Little Atlas is timing this session" in english
    assert "Reading Transfer Learning" in english
    assert "const total = 1800" in english


def test_reading_session_completion_celebrates_and_offers_reflection() -> None:
    chinese = reading_session_completion_html(
        is_zh=True,
        book_title="迁移学习",
        target_minutes=25,
        actual_minutes=25,
        progress_percent=35,
    )
    english = reading_session_completion_html(
        is_zh=False,
        book_title="Transfer Learning",
        target_minutes=30,
        actual_minutes=12,
        progress_percent=20,
    )

    assert "做得很好，这一段读完了" in chinese
    assert "提出一个疑问" in chinese
    assert "阅读进度 35%" in chinese
    assert "Little Atlas recorded" in english
    assert "ask one question" in english
    assert 'aria-live="polite"' in chinese
    assert 'class="atlas-session-complete-mark"' in chinese


def test_companion_preview_makes_tone_and_mascot_visible() -> None:
    preview = companion_preview_html(
        is_zh=True,
        cadence="每天",
        target_minutes=25,
        tone="supportive",
    )

    assert "小 Atlas 已显示" in preview
    assert "今天能读一点就是进展" in preview
    assert "提醒节奏：每天" in preview
    assert 'class="atlas-companion-preview-mark"' in preview


def test_english_navigation_and_empty_workspace_have_no_chinese_visible_labels() -> None:
    html = "".join(
        (
            sidebar_navigation_html(False, "demo-user"),
            topbar_html(False),
            hero_html(False),
            workspace_intro_html(False),
        )
    )
    text = visible_text(html)

    assert "Reading Journey" in text
    assert "Current profile" in text
    assert "From the right book" in text
    assert "Create your reading journey" not in text
    assert re.search(r"[\u4e00-\u9fff]", text) is None


def test_chinese_navigation_and_empty_workspace_translate_visible_labels() -> None:
    html = "".join(
        (
            sidebar_navigation_html(True, "demo-user"),
            topbar_html(True),
            hero_html(True),
            workspace_intro_html(True),
        )
    )
    text = visible_text(html)

    assert "阅读旅程" in text
    assert "当前用户" in text
    assert "找到适合你的书" in text
    assert "开始规划你的阅读路径" not in text
    assert "Reading Journey" not in text
    assert "Current profile" not in text
    assert "Weekly reading" not in text


def test_topbar_search_exposes_safe_index_and_accessible_controls() -> None:
    html = topbar_html(
        False,
        [
            (
                'Robot Ethics <script>alert("x")</script>',
                "Book",
                "#book-stage-3",
                "Patrick Lin",
            )
        ],
    )

    assert 'role="combobox"' in html
    assert 'type="text"' in html
    assert 'inputmode="search"' in html
    assert 'aria-controls="atlas-search-results"' in html
    assert 'role="listbox"' in html
    assert 'data-atlas-search-input' in html
    assert '#book-stage-3' in html
    assert '<script>alert("x")</script>' not in html
    assert '&lt;script&gt;' in html
    assert '&lt;/script&gt;' in html


def test_topbar_search_exposes_agent_action_and_initial_query_safely() -> None:
    html = topbar_html(
        False,
        [],
        initial_query='The <script>Mind</script>',
        agent_search_enabled=True,
        search_user_id='demo-eee<script>alert("x")</script>',
    )

    assert 'data-agent-enabled="true"' in html
    assert 'data-agent-label="Search online and assess"' in html
    assert 'value="The &lt;script&gt;Mind&lt;/script&gt;"' in html
    assert 'id="agent-search"' in html
    assert 'data-search-user-id="demo-eee&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;"' in html


def test_chinese_topbar_can_offer_agent_search_without_local_path_items() -> None:
    html = topbar_html(True, [], agent_search_enabled=True)

    assert 'data-language="zh"' in html
    assert 'data-agent-enabled="true"' in html
    assert 'data-agent-label="联网搜索并评估"' in html
    assert 'placeholder="输入书名或 ISBN，评估契合度"' in html


def test_topbar_supports_native_streamlit_search_slot() -> None:
    html = topbar_html(True, native_search=True)

    assert 'class="atlas-native-search-slot"' in html
    assert 'data-atlas-search-input' not in html
    assert 'role="combobox"' not in html


def test_native_search_uses_one_unclipped_focus_ring() -> None:
    css = atlas_theme_css()

    assert '.st-key-atlas_global_search [data-testid="stTextInputRootElement"]:focus-within' in css
    assert '.st-key-atlas_global_search input:focus' in css
    assert 'outline: 0 !important;' in css


def test_native_search_submit_is_visible_and_touch_sized() -> None:
    css = atlas_theme_css()
    submit_rule = css.split('.st-key-atlas_global_search [data-testid="stFormSubmitButton"] {')[1].split('}')[0]
    assert 'clip' not in submit_rule
    assert 'width: 100%' in submit_rule
    assert '[data-testid="stFormSubmitButton"] button { min-height: 44px' in css


def test_hash_navigation_binds_search_and_keyboard_controls() -> None:
    script = hash_navigation_html()

    assert "atlasSearchBound" in script
    assert "renderSearchResults" in script
    assert "ArrowDown" in script
    assert "ArrowUp" in script
    assert "Escape" in script
    assert "scrollToTarget(item.href" in script
    assert "launchAgentSearch" in script
    assert "book_query" in script
    assert "ui_language" in script
    assert "history.replaceState" in script
    assert "searchUserId" in script
    assert "url.searchParams.set('user_id'" in script
    assert "__nexmindAtlasSearchDraft" not in script
    assert "rememberSearchDraft" not in script
    assert "restoreDraftAfterInputReplacement" not in script
    assert "scheduleSearchDraftRestore" not in script
    assert "setAttribute('value', draft)" not in script
    assert "launchAgentSearch(event.currentTarget.value)" in script
    assert "addEventListener('input'" not in script
    assert "MutationObserver" in script
    assert "searchItemsRaw" in script
    assert "nextItemsRaw !== searchItemsRaw" in script
    assert "atlasLanguageBound" in script
    assert "host.location.assign(link.href)" in script


def test_topbar_search_leaves_native_chinese_ime_editing_untouched() -> None:
    script = hash_navigation_html()

    assert "event.isComposing" in script
    assert "event.keyCode === 229" in script
    assert "addEventListener('compositionstart'" not in script
    assert "addEventListener('compositionend'" not in script
    assert "addEventListener('input'" not in script


def test_book_fit_result_renders_overall_and_dimension_scores() -> None:
    book = BookCandidate(
        canonical_id="9780000000001",
        title="The Embodied Mind",
        authors=["Francisco Varela"],
        isbn_13="9780000000001",
        language="en",
        page_count=300,
        cover_url="https://books.google.com/the-embodied-mind.jpg",
        source_records=[
            EvidenceRecord(
                source_name="Google Books",
                source_url="https://books.google.com/example",
                fields_verified=["title", "isbn_13"],
            )
        ],
        verification_status="verified_single_source",
    )
    assessment = BookAssessment(
        canonical_id=book.canonical_id,
        goal_relevance=0.9,
        prerequisite_fit=0.8,
        evidence_strength=0.7,
        perspective_value=0.9,
        time_feasibility=0.6,
        language_fit=1.0,
        overall_rank_score=0.82,
        recommendation_reason="This book closely supports the current learning goal.",
        why_now="It provides a useful conceptual foundation.",
        confidence="medium",
    )
    evaluation = BookSearchEvaluation(
        query="The Embodied Mind",
        book=book,
        assessment=assessment,
        evaluated_role="Conceptual Foundation",
        title_match_score=0.98,
        execution_trace=["SEARCH · checked two sources"],
        used_live_model=True,
    )

    html = book_fit_result_html(evaluation, False)

    assert "Atlas book assessment" in html
    assert 'data-score="82%"' in html
    assert "Goal relevance" in html
    assert "Bibliographic verification" in html
    assert "Foundational concepts" in html
    assert "Google Books" in html
    assert "atlas-cover-card--fit" in html
    assert "https://books.google.com/the-embodied-mind.jpg" in html
    assert 'width="328" height="492"' in html


def test_fit_score_dimensions_use_one_canonical_bilingual_order() -> None:
    assessment = BookAssessment(
        canonical_id="score-label-test",
        goal_relevance=0.1,
        prerequisite_fit=0.2,
        evidence_strength=0.3,
        perspective_value=0.4,
        time_feasibility=0.5,
        language_fit=0.6,
        overall_rank_score=0.3,
        recommendation_reason="A sufficiently detailed recommendation reason.",
        why_now="A sufficiently detailed explanation for this stage.",
        confidence="medium",
    )

    assert fit_score_dimensions(assessment, True) == (
        ("目标相关性", 0.1),
        ("学习基础匹配度", 0.2),
        ("书目信息核验充分度", 0.3),
        ("视角补充价值", 0.4),
        ("阅读时间可行性", 0.5),
        ("语言偏好匹配度", 0.6),
    )
    assert fit_score_dimensions(assessment, False) == (
        ("Goal relevance", 0.1),
        ("Prior-knowledge fit", 0.2),
        ("Bibliographic verification", 0.3),
        ("Perspective value", 0.4),
        ("Time feasibility", 0.5),
        ("Language fit", 0.6),
    )


def test_book_cover_does_not_invent_a_google_cover_from_a_volume_id() -> None:
    book = BookCandidate(
        canonical_id="google:volume-123",
        title="Visual Thinking",
        authors=["Example Author"],
        isbn_13="9780000000123",
        source_records=[
            EvidenceRecord(
                source_name="Google Books",
                source_book_id="volume-123",
            )
        ],
    )

    html = book_cover_html(book, False)

    assert "atlas-cover-card--detail" in html
    assert "books.google.com/books/content?" not in html
    assert "covers.openlibrary.org" not in html
    assert "volume-123" not in html
    assert 'aria-label="Cover of Visual Thinking"' in html
    assert "atlas-cover-image--detail" not in html
    assert "Visual Thinking" in html


def test_cover_images_upscale_proportionally_without_cropping() -> None:
    css = atlas_theme_css()

    assert css.count("object-fit: contain !important;") >= 2
    assert ".atlas-cover-card--detail .atlas-cover-image" not in css
    assert ".journey-cover-image.google-cover" not in css


def test_low_relevance_book_is_explicitly_not_recommended() -> None:
    book = BookCandidate(
        canonical_id="9780000000099",
        title="Unrelated Biography",
        authors=["Example Author"],
        language="en",
        source_records=[],
    )
    assessment = BookAssessment(
        canonical_id=book.canonical_id,
        goal_relevance=0.08,
        prerequisite_fit=0.55,
        evidence_strength=0.7,
        perspective_value=0.12,
        time_feasibility=1.0,
        language_fit=1.0,
        overall_rank_score=0.16,
        recommendation_reason="This biography is not relevant to the current learning goal.",
        why_now="It should not be forced into the path.",
        confidence="medium",
    )
    evaluation = BookSearchEvaluation(
        query="biography",
        book=book,
        assessment=assessment,
        evaluated_role="Critical/Cross-disciplinary",
        title_match_score=0.9,
        execution_trace=["CONCLUDE · not recommended"],
    )

    html = book_fit_result_html(evaluation, False)

    assert "Not recommended for this learning path" in html
    assert "Best role in this path" not in html


def test_sidebar_navigation_targets_exist_in_ready_and_empty_views() -> None:
    navigation = sidebar_navigation_html(False, "demo-user")
    targets = set(re.findall(r'href="#([^"]+)"', navigation))
    ready_html = "".join(
        (
            section_anchor("learning-brief"),
            section_anchor("knowledge-map"),
            section_anchor("reading-route"),
            section_anchor("learning-loop"),
            '<div id="reading-journey"></div>',
            '<div id="journey-sources"></div>',
            '<div id="agent-progress"></div>',
        )
    )
    empty_html = "".join(
        (
            workspace_intro_html(False),
            section_anchor("learning-brief"),
            navigation_empty_state_html(False),
        )
    )

    assert targets
    assert all(f'id="{target}"' in ready_html for target in targets)
    assert all(f'id="{target}"' in empty_html for target in targets)


def test_hash_navigation_scrolls_streamlit_container_and_syncs_active_link() -> None:
    script = hash_navigation_html()

    assert "scrollIntoView" in script
    assert "hashchange" in script
    assert "aria-current" in script
    assert "matchingLinks.find" in script
    assert "hasAttribute('aria-current')" in script
    assert "prefers-reduced-motion" in script
    assert "if (!hash)" in script


def test_knowledge_check_restores_scroll_position_after_form_rerun() -> None:
    script = form_scroll_restoration_html()

    assert "data-atlas-knowledge-check-form" in script
    assert "data-atlas-learning-loop-form" in script
    assert "nexmind:form-scroll" in script
    assert "knowledge-check-results" in script
    assert "sessionStorage" in script
    assert "preventScroll: true" in script
    assert "data-atlas-form-target" in script
    assert "targetId" in script
    assert "isKnowledgeCheck ? 'knowledge-check-results' : 'learning-loop'" in script
    assert "formViewportTop" in script
    assert "restoredForm.getBoundingClientRect().top" in script
    assert "360000" in script  # Allow both model passes and bounded retries.
    assert "form.appendChild(status)" in script  # Feedback must not stretch the submit button.
    assert "__nexmindAtlasPendingForm" in script
    assert "MutationObserver(scheduleRestore)" in script
    assert "learningToolsUrl.hash" not in script
    assert "HashChangeEvent" not in script
    assert "}, 180);" in script


def test_sidebar_only_advertises_distinct_available_destinations() -> None:
    english = visible_text(sidebar_navigation_html(False, "demo-user"))
    chinese = visible_text(sidebar_navigation_html(True, "demo-user"))

    assert "Recommendations" in english
    assert "Learning Tools" in english
    assert "Plan history" in english
    assert all(label not in english for label in ("Library", "Collections", "Notes", "Highlights"))
    assert "推荐书目" in chinese
    assert "学习工具" in chinese
    assert "历史方案" in chinese


def test_mobile_navigation_exposes_all_destinations_and_scoped_language_links() -> None:
    html = mobile_navigation_html(True, "team member")

    assert 'class="atlas-mobile-nav"' in html
    assert "阅读旅程" in html
    assert "推荐书目" in html
    assert "历史方案" in html
    assert "ui_language=en&amp;set_language=en&amp;user_id=team+member" in html
    assert "ui_language=zh&amp;set_language=zh&amp;user_id=team+member" in html
    assert 'aria-current="true">中文</a>' in html
    assert "新建学习档案" in html
    assert html.count('target="_self"') == 10
    assert 'history=1' in html


def test_history_navigation_is_scoped_and_preview_can_return_to_active_page() -> None:
    html = sidebar_navigation_html(True, 'person & test', preview=True)
    assert 'ui_language=zh&amp;user_id=person+%26+test&amp;history=1' in html
    assert 'user_id=person+%26+test#reading-journey' in html
    assert '#agent-progress' not in html


def test_topbar_uses_current_profile_without_fake_controls() -> None:
    html = topbar_html(False, native_search=True, search_user_id="demo-eee")

    assert 'aria-label="Current profile: demo-eee"' in html
    assert ">DE</span>" in html
    assert "Notifications" not in html
