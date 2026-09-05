from __future__ import annotations

import re
from typing import Any

DEFAULT_INTERFACE_LANGUAGE = "en"
SUPPORTED_INTERFACE_LANGUAGES = ("en", "zh")

_SYSTEM_MESSAGES = {
    # Legacy English messages remain readable for journeys saved before this copy update.
    "Search branch added clearly labelled cached demo evidence.": "实时检索结果不足，已补充清晰标注的缓存示例数据。",
    "Final verifier: the reading path does not contain all three roles.": "最终检查未通过：学习路径尚未覆盖三类知识内容。",
    "Final verifier: one or more hard constraints are not satisfied.": "最终检查未通过：部分必要条件尚未满足。",
    "The path is incomplete because one or more evidence roles lacked candidates.": "学习路径不完整：部分知识类型尚未找到合适的候选书目。",
    "Estimated reading exceeds the declared time budget.": "预计阅读时间超出了设定的时间预算。",
    "Live sources returned too few candidates; clearly labelled cached demo data was added.": "实时来源返回的候选书目不足，已补充清晰标注的缓存示例数据。",
    "Sample data was added because live search returned too few verified books.": "实时检索结果不足，已补充清晰标注的缓存示例数据。",
    "Final check: the reading path does not cover all three knowledge areas.": "最终检查未通过：学习路径尚未覆盖三类知识内容。",
    "Final check: one or more required constraints are not satisfied.": "最终检查未通过：部分必要条件尚未满足。",
    "The reading path is incomplete because one or more knowledge areas have no verified books.": "学习路径不完整：部分知识类型尚未找到合适的候选书目。",
    "The estimated reading time exceeds your available time.": "预计阅读时间超出了设定的时间预算。",
    "Live sources returned too few verified books, so clearly labeled sample data was added.": "实时来源返回的候选书目不足，已补充清晰标注的缓存示例数据。",
}
_ROLE_NAMES_ZH = {
    "Conceptual Foundation": "基础概念",
    "Technical/Application": "技术原理与应用",
    "Critical/Cross-disciplinary": "批判思考与跨学科视角",
    # Preserve natural display labels for journeys saved before this copy update.
    "概念基础": "基础概念",
    "技术与应用": "技术原理与应用",
    "批判与跨学科": "批判思考与跨学科视角",
    "Foundational concepts": "基础概念",
    "Technical principles & applications": "技术原理与应用",
    "Critical & interdisciplinary perspectives": "批判思考与跨学科视角",
}
_ROLE_NAMES_EN = {
    "Conceptual Foundation": "Foundational concepts",
    "Technical/Application": "Technical principles & applications",
    "Critical/Cross-disciplinary": "Critical & interdisciplinary perspectives",
}
_METADATA_FIELDS = {
    "title": ("Title", "书名"),
    "authors": ("Authors", "作者"),
    "isbn_10": ("ISBN-10", "ISBN-10"),
    "isbn_13": ("ISBN-13", "ISBN-13"),
    "published_year": ("Publication year", "出版年份"),
    "description": ("Description", "简介"),
    "language": ("Language", "语言"),
    "page_count": ("Page count", "页数"),
    "categories": ("Categories", "分类"),
    "average_rating": ("Average rating", "平均评分"),
    "ratings_count": ("Ratings count", "评分人数"),
}


def interface_language(value: Any) -> str:
    """Read language from new or pre-migration session objects."""
    language = getattr(value, "interface_language", DEFAULT_INTERFACE_LANGUAGE)
    return language if language in SUPPORTED_INTERFACE_LANGUAGES else DEFAULT_INTERFACE_LANGUAGE


def book_language_preferences(value: Any) -> list[str]:
    """Return normalized preferences for goals saved before language support."""
    languages = getattr(value, "book_language_preferences", None) or ["en"]
    normalized = [language for language in languages if language in {"en", "zh"}]
    return list(dict.fromkeys(normalized)) or ["en"]


def localize_system_message(message: str, language: str) -> str:
    """Translate current and legacy system warnings without altering source or book names."""
    if language == "zh":
        if message in _SYSTEM_MESSAGES:
            return _SYSTEM_MESSAGES[message]
        role_match = re.fullmatch(r"No verified candidate filled the (.+) role\.", message)
        if role_match:
            role = _ROLE_NAMES_ZH.get(role_match.group(1), role_match.group(1))
            return f"“{role}”尚未找到经过核验的候选书目。"
        book_match = re.fullmatch(r"No verified book was found for (.+)\.", message)
        if book_match:
            role = _ROLE_NAMES_ZH.get(book_match.group(1), book_match.group(1))
            return f"“{role}”尚未找到经过核验的候选书目。"
        search_match = re.fullmatch(r"(.+) failed for (.+) \((.+)\): (.+)", message)
        if search_match:
            source, role, book_language, error = search_match.groups()
            return f"{source} 检索“{_ROLE_NAMES_ZH.get(role, role)}”（{book_language}）时失败：{error}"
        current_search_match = re.fullmatch(r"(.+) search failed for (.+) \((.+)\): (.+)", message)
        if current_search_match:
            source, role, book_language, error = current_search_match.groups()
            return f"{source} 检索“{_ROLE_NAMES_ZH.get(role, role)}”（{book_language}）时失败：{error}"
        return message

    reverse_messages = {chinese: english for english, chinese in _SYSTEM_MESSAGES.items()}
    return reverse_messages.get(message, message)


def localize_catalog_text(message: str, language: str) -> str:
    """Polish known catalogue labels and legacy encoding artefacts for display."""
    if language != "zh" or not message:
        return message
    replacements = {
        "Technology & Engineering": "技术与工程",
        "技術?品": "技術產品",
        "技术?品": "技术产品",
        "分?從": "分別從",
        "本書?容": "本書內容",
        "應用性?": "應用性強",
        "學生?讀": "學生閱讀",
    }
    localized = message
    for source, target in replacements.items():
        localized = localized.replace(source, target)
    return localized


def metadata_field_label(field: str, language: str) -> str:
    labels = _METADATA_FIELDS.get(field)
    if labels:
        return labels[1] if language == "zh" else labels[0]
    return field.replace("_", " ").title() if language == "en" else field


def resource_type_label(value: str, language: str) -> str:
    """Return user-facing knowledge-type labels, including for saved legacy journeys."""
    return _ROLE_NAMES_ZH.get(value, value) if language == "zh" else _ROLE_NAMES_EN.get(value, value)


def reading_stage_title(value: str, language: str) -> str:
    """Refresh saved stage-title prefixes without altering the book title."""
    labels = _ROLE_NAMES_ZH if language == "zh" else _ROLE_NAMES_EN
    separators = ("：", ":")
    for old_label, new_label in labels.items():
        for separator in separators:
            if value.startswith(f"{old_label}{separator}"):
                suffix = value.split(separator, 1)[1]
                return f"{new_label}{separator}{suffix}"
    return value
