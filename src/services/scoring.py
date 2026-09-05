from __future__ import annotations

import re
from html import unescape

from src.language import book_language_preferences, interface_language
from src.models import BookAssessment, BookCandidate, LearningGoal, UserProfile
from src.services.book_matching import normalize_text
from src.services.learning_focus import focus_search_phrases
from src.services.time_estimation import estimate_focused_hours

WEIGHTS = {
    "goal_relevance": 0.30,
    "prerequisite_fit": 0.20,
    "evidence_strength": 0.20,
    "perspective_value": 0.10,
    "time_feasibility": 0.10,
    "language_fit": 0.10,
}

SCORING_VERSION = 6


ROLE_CONTEXT = {
    "Conceptual Foundation": (
        "foundation foundations concept concepts theory theories cognition cognitive "
        "introduction fundamentals beginner guide textbook overview vocabulary "
        # Conceptual grounding is not synonymous with a technical introduction:
        # philosophy and theoretical frameworks also establish a field's core ideas.
        # These remain secondary role signals; the independent topic gate still applies.
        "conceptual theoretical framework frameworks philosophy philosophical "
        "基础 概念 理论 认知 导论 原理 入门 教程 术语 哲学 思想 框架"
    ),
    "Technical/Application": (
        "technical technology application applications engineering robotics robot control "
        "system systems implementation method methods model models algorithm algorithms "
        "practice practical case cases 技术 应用 工程 机器人 控制 系统 实现 方法 模型 算法 实践 案例"
    ),
    "Critical/Cross-disciplinary": (
        "critical interdisciplinary ethics ethical society social human policy responsibility "
        "evaluation limitation limitations risk risks uncertainty bias impact "
        "批判 跨学科 伦理 社会 人文 政策 责任 评估 局限 风险 不确定性 偏差 影响"
    ),
}


# Broad catalogue words can describe almost any technical book. They must not be
# allowed to stand in for a genuine match with the learner's topic or requested
# perspectives (for example, “smart technology” is not evidence of embodied AI).
GENERIC_ANCHOR_TOKENS = {
    "application",
    "applications",
    "basic",
    "concept",
    "foundation",
    "intelligence",
    "intelligent",
    "introduction",
    "learning",
    "principle",
    "science",
    "study",
    "system",
    "systems",
    "technology",
    "基础",
    "学习",
    "应用",
    "智能",
    "概念",
    "研究",
    "科技",
    "科学",
    "系统",
    "技术",
    "理论",
}


# A small, explicit synonym map is safer than treating the catalogue search
# label as proof of relevance.  It covers the product's demonstrated domains
# while the normal topic phrase/word matching handles arbitrary goals.
TOPIC_BRIDGES = {
    "embodied": {
        "cognition",
        "cognitive",
        "ethics",
        "robot",
        "robotics",
        "具身",
        "具身心智",
        "具身认知",
        "机器人",
        "認知",
        "认知",
        "倫理",
        "伦理",
    },
    "machine learning": {
        "algorithm",
        "deep learning",
        "model",
        "neural network",
        "statistical learning",
        "机器学习",
        "模型",
        "深度学习",
        "神经网络",
        "算法",
        "統計學習",
        "统计学习",
    },
    "time series": {
        "forecast",
        "forecasting",
        "time series",
        "时序",
        "時間序列",
        "时间序列",
        "预测",
        "預測",
    },
}

CATALOGUE_INTEGRITY_RED_FLAGS = (
    "anti-aging",
    "cure-all",
    "healthspan maximization",
    "miracle",
    "perpetual motion",
    "systemic rejuvenation",
    "延寿",
    "年轻化",
    "年輕化",
    "永动飞轮",
    "永動飛輪",
    "根本使命",
    "最大化",
    "自愈",
)


def aggregate_fit_score(scores: dict[str, float]) -> float:
    """Combine dimensions while preventing metadata quality from masking topic mismatch."""
    weighted_score = sum(scores[key] * weight for key, weight in WEIGHTS.items())
    relevance_gate = 0.25 + 0.75 * scores["goal_relevance"]
    return min(1.0, weighted_score * relevance_gate)


def _tokens(values: list[str]) -> set[str]:
    normalized = normalize_text(" ".join(values))
    tokens = set(normalized.split())
    for chunk in normalized.split():
        if any("\u4e00" <= char <= "\u9fff" for char in chunk):
            tokens.update(chunk[index : index + 2] for index in range(max(0, len(chunk) - 1)))
        elif len(chunk) > 4 and chunk.endswith("ies"):
            tokens.add(f"{chunk[:-3]}y")
        elif len(chunk) > 4 and chunk.endswith("s") and not chunk.endswith("ss"):
            tokens.add(chunk[:-1])
        if len(chunk) > 7 and chunk.endswith("ics"):
            tokens.add(chunk[:-3])
    return {token for token in tokens if token}


def _contains_cjk(value: str) -> bool:
    return any("\u4e00" <= character <= "\u9fff" for character in value)


def _semantic_anchors(values: list[str]) -> set[str]:
    """Return topic-bearing words/phrases, avoiding noisy two-character CJK hits."""
    anchors: set[str] = set()
    for value in values:
        normalized = normalize_text(value)
        for chunk in normalized.split():
            if _contains_cjk(chunk):
                cjk = "".join(character for character in chunk if "\u4e00" <= character <= "\u9fff")
                if len(cjk) <= 3:
                    anchors.add(cjk)
                else:
                    # Three- and four-character fragments preserve phrases such
                    # as “时间序列” while rejecting a coincidental “时间” match.
                    for size in (3, 4):
                        anchors.update(
                            cjk[index : index + size]
                            for index in range(max(0, len(cjk) - size + 1))
                        )
            else:
                anchors.update(
                    token
                    for token in _tokens([chunk])
                    if len(token) >= 3 and token not in GENERIC_ANCHOR_TOKENS
                )
    return {anchor for anchor in anchors if anchor}


def _topic_bridge_anchors(topic: str) -> set[str]:
    normalized = normalize_text(topic)
    anchors: set[str] = set()
    if "具身" in topic or "embodied" in normalized:
        anchors.update(TOPIC_BRIDGES["embodied"])
    if "机器学习" in topic or "機器學習" in topic or "machine learning" in normalized:
        anchors.update(TOPIC_BRIDGES["machine learning"])
    if "时间序列" in topic or "時間序列" in topic or "time series" in normalized:
        anchors.update(TOPIC_BRIDGES["time series"])
    return _semantic_anchors(list(anchors))


def _language_code(value: str | None) -> str | None:
    normalized = (value or "").lower().replace("_", "-")
    if normalized.startswith("zh") or normalized in {"chi", "zho"}:
        return "zh"
    if normalized.startswith("en") or normalized == "eng":
        return "en"
    return None


def _clean_description(value: str | None) -> str:
    text = unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return " ".join(text.split()).strip()


def _clip(value: str, limit: int = 620) -> str:
    if len(value) <= limit:
        return value
    clipped = value[:limit].rsplit(" ", 1)[0].rstrip("，,；;：:")
    return f"{clipped}…"


def _book_overview(book: BookCandidate, chinese: bool) -> str:
    description = _clean_description(book.description)
    authors = "、".join(book.authors) if chinese else ", ".join(book.authors)
    categories = "、".join(book.categories[:4]) if chinese else ", ".join(book.categories[:4])
    facts: list[str] = []
    if chinese:
        if authors and book.published_year:
            facts.append(f"本书由{authors}撰写，当前核验版本出版于{book.published_year}年。")
        elif authors:
            facts.append(f"本书由{authors}撰写。")
        elif book.published_year:
            facts.append(f"当前核验版本出版于{book.published_year}年。")
        if categories:
            facts.append(f"书目信息将其归入{categories}等主题。")
        if book.page_count:
            facts.append(f"当前版本约{book.page_count}页，适合按学习阶段安排精读范围。")
        lead = description.rstrip("。！？.!?") + "。" if description else f"《{book.title}》围绕现有书目信息所列主题展开。"
    else:
        if authors and book.published_year:
            facts.append(f"Written by {authors}, the verified edition was published in {book.published_year}.")
        elif authors:
            facts.append(f"The book is written by {authors}.")
        elif book.published_year:
            facts.append(f"The verified edition was published in {book.published_year}.")
        if categories:
            facts.append(f"Its catalogued subjects include {categories}.")
        if book.page_count:
            facts.append(f"At approximately {book.page_count} pages, it can be scoped across a focused reading stage.")
        lead = description.rstrip(".!?") + "." if description else f"{book.title} addresses the subjects identified in its verified bibliographic record."
    return _clip(" ".join([lead, *facts]))


def _recommendation_narrative(
    book: BookCandidate,
    goal: LearningGoal,
    profile: UserProfile,
    intended_role: str,
    chinese: bool,
) -> tuple[str, str]:
    subjects = ("、".join(book.categories[:3]) if chinese else ", ".join(book.categories[:3])) or book.title
    background = ("、".join(profile.background_knowledge[:3]) if chinese else ", ".join(profile.background_knowledge[:3]))
    major = profile.major or ("当前专业背景" if chinese else "the learner's current field")
    if chinese:
        narratives = {
            "Conceptual Foundation": (
                f"《{book.title}》聚焦{subjects}，适合作为学习目标“{goal.topic}”的概念入口。"
                f"它能先统一核心术语与理论框架，帮助你判断后续技术材料建立在哪些认知假设之上。"
                + (f"结合你已有的{background}基础，这一阶段的重点是补齐跨学科概念，而不是重复工具训练。" if background else "这一阶段先搭建共同语言，能降低后续跨学科阅读的理解成本。"),
                "将它放在第一阶段，是为了先建立可复用的概念坐标，再进入技术机制和伦理讨论。阅读时应重点记录核心术语、主要理论主张及其证据边界。",
            ),
            "Technical/Application": (
                f"《{book.title}》把{subjects}落实到具体技术系统与应用问题，可承接第一阶段形成的概念框架。"
                f"对于{major}背景的学习者，它能把已有知识与感知、决策、控制或系统实现之间的联系讲清楚。"
                f"它既补足学习目标“{goal.topic}”的技术维度，也直接服务于你的学习目的——{goal.purpose}。",
                "第二阶段需要把抽象概念转化为可分析的技术过程。建议结合案例、系统结构和关键算法阅读，并把实现条件与局限同步记入笔记。",
            ),
            "Critical/Cross-disciplinary": (
                f"《{book.title}》从{subjects}切入，为学习目标“{goal.topic}”补充技术之外的人文、认知与社会判断。"
                "它的价值不在于重复前两阶段的原理，而在于检验技术目标背后的责任分配、价值假设和现实影响。"
                "作为收束读物，它能帮助你形成既理解系统能力、又能识别边界与风险的完整观点。",
                "放在第三阶段，可以用前面形成的概念和技术理解来审视真实争议。阅读时应比较不同立场，区分事实判断、价值判断与政策选择。",
            ),
        }
        return narratives.get(
            intended_role,
            (
                f"《{book.title}》覆盖{subjects}，能够补充“{goal.topic}”学习路径中尚未充分展开的知识。",
                "当前阶段阅读这本书，有助于衔接前后内容并形成更完整的知识结构。",
            ),
        )
    narratives = {
        "Conceptual Foundation": (
            f"{book.title} concentrates on {subjects}, making it a strong conceptual entry point for the {goal.topic} pathway. "
            "It establishes shared terminology and theoretical frames before the learner encounters more technical claims. "
            + (f"Given prior experience with {background}, this stage fills interdisciplinary conceptual gaps rather than repeating tool training." if background else "This shared vocabulary reduces the cognitive load of the later interdisciplinary stages."),
            "It comes first so the learner can build a reusable conceptual map before moving into mechanisms and ethical questions. Read for definitions, central claims, and the limits of the evidence behind them.",
        ),
        "Technical/Application": (
            f"{book.title} connects {subjects} to concrete systems and applications, extending the conceptual frame established in stage one. "
            f"For a learner from {major}, it can make the links between prior knowledge and system implementation more explicit. "
            f"That connection directly supports the stated purpose: {goal.purpose}.",
            "Stage two turns abstract concepts into technical processes that can be inspected and compared. Focus on system architecture, methods, examples, operating assumptions, and implementation limits.",
        ),
        "Critical/Cross-disciplinary": (
            f"{book.title} approaches {goal.topic} through {subjects}, adding human, cognitive, and social judgment beyond technical performance. "
            "Its role is to test the responsibility, value assumptions, and real-world effects behind the systems covered earlier. "
            "As a concluding resource, it supports a view that recognizes both technical capability and its boundaries.",
            "Placed in stage three, it lets the learner use the earlier conceptual and technical foundation to examine genuine disputes. Compare positions carefully and separate empirical claims, value judgments, and policy choices.",
        ),
    }
    return narratives.get(
        intended_role,
        (
            f"{book.title} covers {subjects} and fills a knowledge gap in the {goal.topic} pathway.",
            "Reading it at this point connects the surrounding stages and strengthens the overall knowledge structure.",
        ),
    )


def _unrelated_narrative(
    book: BookCandidate,
    goal: LearningGoal,
    chinese: bool,
) -> tuple[str, str]:
    searchable_genre = " ".join([book.title, book.description or "", *book.categories]).lower()
    biography_terms = (
        "biography",
        "autobiography",
        "memoir",
        "entrepreneur",
        "传记",
        "自传",
        "回忆录",
        "企业家",
    )
    is_biographical = any(term in searchable_genre for term in biography_terms)
    if chinese:
        subject = "人物传记或商业叙事" if is_biographical else "与当前目标不同的主题"
        return (
            f"现有书目信息显示《{book.title}》主要属于{subject}。外部来源能够核实作者、版本和出版信息，"
            f"但没有证据表明本书会系统讲解学习目标“{goal.topic}”所需的核心概念、技术机制或批判性议题。"
            "因此，不建议把它纳入当前学习路径的核心书目；若你对其主题本身感兴趣，可以仅作为背景延伸阅读。",
            "这本书与当前三个学习阶段都缺少足够的直接关联，不应为了填补某个知识类型而强行加入路径。",
        )
    subject = "a biography or business narrative" if is_biographical else "a different subject area"
    return (
        f"The available catalogue evidence identifies {book.title} primarily as {subject}. Its authorship, "
        f"edition, and publication details can be verified, but the metadata does not show sustained coverage "
        f"of the core concepts, technical mechanisms, or critical questions required for {goal.topic}. "
        "It should not be included as a core resource in this learning path; at most, it may serve as optional background reading.",
        "The book lacks enough direct relevance to any of the three learning stages and should not be forced into a knowledge role.",
    )


def assess_book(
    book: BookCandidate,
    goal: LearningGoal,
    profile: UserProfile,
    intended_role: str,
) -> BookAssessment:
    book_fields = [book.title, book.description or "", *book.categories]
    from src.services.goal_alignment import exclusion_conflict
    excluded = exclusion_conflict(book, goal)
    haystack = _tokens(book_fields)
    book_anchors = _semantic_anchors(book_fields)
    topic_anchors = _semantic_anchors([goal.topic]) | _topic_bridge_anchors(goal.topic)
    focus_anchors = _semantic_anchors(focus_search_phrases(goal)) - _semantic_anchors([goal.topic])
    focus_matches = focus_anchors & book_anchors
    # A book can cover a specific subfield without repeating the broad field in
    # its title. Conversely, matching "psychology" is not proof of memory coverage.
    topic_anchors |= focus_anchors
    core_matches = book_anchors & topic_anchors
    topic_overlap = min(1.0, len(core_matches) / max(1, min(2, len(topic_anchors))))
    perspective_tokens = _tokens(goal.required_perspectives)
    perspective_overlap = len(haystack & perspective_tokens) / max(
        1, min(4, len(perspective_tokens))
    )
    role_tokens = _tokens([ROLE_CONTEXT.get(intended_role, intended_role)])
    role_overlap = len(haystack & role_tokens) / max(1, min(4, len(role_tokens)))
    retrieval_context = 0.04 if intended_role in book.search_roles else 0.0
    goal_relevance = min(
        1.0,
        0.08
        + 0.62 * topic_overlap
        + 0.18 * perspective_overlap
        + 0.32 * role_overlap
        + retrieval_context,
    )
    if topic_anchors and not core_matches:
        # Role labels, user-requested perspectives and generic vocabulary are
        # useful secondary signals, but they cannot make an off-topic book look
        # relevant. In particular, a search API returning a result for a query
        # does not prove that the result actually covers the topic.
        goal_relevance = min(goal_relevance, 0.24)
    focus_unverified = bool(focus_anchors and not focus_matches)
    if focus_unverified:
        goal_relevance = min(goal_relevance, 0.52)
    elif focus_matches:
        goal_relevance = min(1.0, goal_relevance + 0.12)

    background = _tokens(profile.background_knowledge)
    prerequisite_fit = 0.55 + min(0.35, len(haystack & background) * 0.08)
    if goal.preferred_difficulty.lower() in {"beginner", "introductory"}:
        prerequisite_fit += 0.05 if "introduction" in haystack else 0
    prerequisite_fit = min(1.0, prerequisite_fit)

    sources = len({record.source_name for record in book.source_records})
    evidence_strength = min(1.0, 0.45 + 0.25 * sources + (0.1 if book.isbn_13 else 0))
    integrity_text = " ".join(book_fields).casefold()
    integrity_flags = {
        flag for flag in CATALOGUE_INTEGRITY_RED_FLAGS if flag in integrity_text
    }
    if len(integrity_flags) >= 2:
        # Search catalogues can contain self-authored metadata that repeats the
        # learner's buzzwords while making unsupported medical or promotional
        # claims. It must not outrank established learning material merely on
        # lexical overlap.
        goal_relevance = min(goal_relevance, 0.28)
        evidence_strength = min(evidence_strength, 0.35)
    perspective_value = min(0.9, 0.12 + 0.78 * role_overlap)
    if intended_role in book.search_roles:
        perspective_value = min(0.9, perspective_value + 0.08)
    stage_budget = goal.total_hours / 3
    estimated = estimate_focused_hours(book)
    time_feasibility = min(1.0, stage_budget / max(estimated, 0.1))
    candidate_language = _language_code(book.language)
    preferred_languages = set(book_language_preferences(goal))
    language_fit = (
        1.0
        if candidate_language in preferred_languages
        else 0.45
        if candidate_language is None
        else 0.1
    )
    scores = {
        "goal_relevance": goal_relevance,
        "prerequisite_fit": prerequisite_fit,
        "evidence_strength": evidence_strength,
        "perspective_value": perspective_value,
        "time_feasibility": time_feasibility,
        "language_fit": language_fit,
    }
    if excluded:
        goal_relevance = scores["goal_relevance"] = 0.0
    overall = aggregate_fit_score(scores)
    reservations: list[str] = []
    chinese = interface_language(profile) == "zh"
    if focus_unverified:
        reservations.append(
            "书目信息尚不能确认它是否覆盖你特别提出的细分方向；不能仅凭大类主题相同就认为满足需求。"
            if chinese else
            "The available metadata does not yet confirm coverage of your specific interests; a broad topic match is not enough."
        )
    if excluded:
        reservations.append(f"与你明确排除的内容冲突：{excluded}。" if chinese else f"Conflicts with your explicit exclusion: {excluded}.")
    if sources < 2:
        reservations.append(
            "目前只有一个外部来源可用于核对书目信息。"
            if chinese
            else "This book's details are verified by only one external source."
        )
    if book.average_rating is None or book.ratings_count is None:
        reservations.append(
            "现有来源未提供读者评分。"
            if chinese
            else "No reader ratings were available from the retrieved sources."
        )
    if book.page_count is None:
        reservations.append(
            "未获取到页数，阅读时间按保守值估算。"
            if chinese
            else "Page count is unavailable; time estimate uses a conservative default."
        )
    if len(integrity_flags) >= 2:
        reservations.append(
            "书目简介含有多项宣传性或未经支持的效果表述，不适合作为当前路径的核心教材。"
            if chinese
            else "The catalogue description contains multiple promotional or unsupported outcome claims, so this is not suitable as a core path resource."
        )
    confidence = "high" if sources >= 2 and book.isbn_13 else "medium" if sources else "low"
    if goal_relevance < 0.3:
        recommendation_reason, why_now = _unrelated_narrative(book, goal, chinese)
    else:
        recommendation_reason, why_now = _recommendation_narrative(
            book, goal, profile, intended_role, chinese
        )
    return BookAssessment(
        meets_stated_requirements=False if focus_unverified else None,
        canonical_id=book.canonical_id,
        goal_relevance=round(goal_relevance, 3),
        prerequisite_fit=round(prerequisite_fit, 3),
        evidence_strength=round(evidence_strength, 3),
        perspective_value=round(perspective_value, 3),
        time_feasibility=round(time_feasibility, 3),
        language_fit=round(language_fit, 3),
        overall_rank_score=round(overall, 3),
        book_overview=_book_overview(book, chinese),
        recommendation_reason=recommendation_reason,
        why_now=why_now,
        reservations=reservations,
        confidence=confidence,
        evaluated_role=intended_role,
    )
