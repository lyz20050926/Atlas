from __future__ import annotations

from types import SimpleNamespace

import httpx

from src.diagnostic import build_diagnostic
from src.language import (
    DEFAULT_INTERFACE_LANGUAGE,
    book_language_preferences,
    interface_language,
    localize_catalog_text,
    localize_system_message,
    metadata_field_label,
    reading_stage_title,
    resource_type_label,
)
from src.models import BookAssessment, LearningGoal, ReadingSessionInput, UserProfile
from src.reading_support import support_reading
from src.services.book_matching import identity_matches
from src.services.recommendation import (
    ROLES,
    _select_complementary,
    build_queries,
    load_chinese_demo_candidates,
    load_fallback_candidates,
)
from src.tools.google_books import GoogleBooksClient
from src.tools.open_library import OpenLibraryClient


def chinese_goal() -> LearningGoal:
    return LearningGoal(
        topic="具身智能",
        purpose="建立跨学科基础",
        duration_weeks=6,
        hours_per_week=4,
        required_perspectives=["机器人学", "认知科学", "伦理学"],
        interface_language="zh",
        book_language_preferences=["zh"],
    )


def chinese_profile() -> UserProfile:
    return UserProfile(
        user_id="zh-user",
        education_level="undergraduate",
        major="电子与电气工程",
        interface_language="zh",
        language_preferences=["Chinese"],
    )


def test_chinese_mode_builds_role_specific_chinese_queries() -> None:
    queries = build_queries(chinese_goal())
    assert queries == {
        ROLES[0]: "具身认知",
        ROLES[1]: "自主移动机器人",
        ROLES[2]: "机器人伦理",
    }


def test_chinese_fallback_has_verified_chinese_book_for_each_role() -> None:
    books = load_fallback_candidates(chinese_goal())
    assert len(books) == 3
    assert {book.language for book in books} == {"zh"}
    assert all(book.isbn_13 and book.source_records for book in books)
    assert {role for book in books for role in book.search_roles} == set(ROLES)


def test_chinese_selection_prefers_and_explains_chinese_books() -> None:
    selected, assessments, warnings = _select_complementary(
        load_chinese_demo_candidates(), chinese_goal(), chinese_profile()
    )
    assert warnings == []
    assert len(selected) == 3
    assert all(book.language == "zh" for book in selected)
    assert all(item.language_fit == 1 for item in assessments)
    assert all("学习目标" in item.recommendation_reason for item in assessments)


def test_chinese_titles_do_not_collapse_during_identity_matching() -> None:
    foundation, technical, _ = load_chinese_demo_candidates()
    assert not identity_matches(foundation, technical)


def test_diagnostic_and_mock_reading_support_answer_in_chinese() -> None:
    questions = build_diagnostic(chinese_goal(), chinese_profile())
    assert "自己的话" in questions[0].prompt
    output = support_reading(
        ReadingSessionInput(
            book_title="具身心智",
            excerpt="认知并不是孤立计算，而是在身体与环境的持续互动中生成的。",
            question="这与生成认知有什么关系？",
            target_concept="生成认知",
            response_language="Chinese",
        )
    )
    assert "用户提供" in output.grounding
    assert "生成认知" in output.recall_question


def test_book_clients_send_language_controls() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"items": [], "docs": []})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    GoogleBooksClient(client=http_client).search("具身认知", language="zh")
    OpenLibraryClient(client=http_client).search("具身认知", language="zh")

    assert seen[0].url.params["langRestrict"] == "zh"
    assert seen[1].url.params["lang"] == "zh"
    assert "language:chi" in seen[1].url.params["q"]
    http_client.close()


def test_pre_language_migration_objects_get_safe_defaults() -> None:
    legacy = SimpleNamespace()
    assert DEFAULT_INTERFACE_LANGUAGE == "en"
    assert interface_language(legacy) == "en"
    assert book_language_preferences(legacy) == ["en"]

    _, assessments, _ = _select_complementary(
        load_chinese_demo_candidates(), chinese_goal(), chinese_profile()
    )
    legacy_assessment = assessments[0].model_dump()
    legacy_assessment.pop("language_fit")
    assert BookAssessment.model_validate(legacy_assessment).language_fit == 0.5


def test_selection_warnings_follow_the_interface_language() -> None:
    _, _, chinese_warnings = _select_complementary([], chinese_goal(), chinese_profile())
    assert len(chinese_warnings) == 3
    assert all("尚未找到经过核验" in warning for warning in chinese_warnings)

    english_goal = chinese_goal().model_copy(
        update={"topic": "Embodied Intelligence", "interface_language": "en"}
    )
    english_profile = chinese_profile().model_copy(update={"interface_language": "en"})
    _, _, english_warnings = _select_complementary([], english_goal, english_profile)
    assert len(english_warnings) == 3
    assert all(warning.startswith("No verified book") for warning in english_warnings)


def test_legacy_warnings_and_metadata_fields_are_localized() -> None:
    assert localize_system_message(
        "Search branch added clearly labelled cached demo evidence.", "zh"
    ) == "实时检索结果不足，已补充清晰标注的缓存示例数据。"
    assert localize_system_message(
        "Google Books failed for Conceptual Foundation (zh): HTTPStatusError", "zh"
    ) == "Google Books 检索“基础概念”（zh）时失败：HTTPStatusError"
    assert metadata_field_label("published_year", "zh") == "出版年份"
    assert metadata_field_label("published_year", "en") == "Publication year"


def test_catalog_copy_polishes_mixed_language_and_legacy_encoding() -> None:
    chinese = (
        "本书属于 Technology & Engineering，介绍先进技術?品和技术?品；"
        "全書分?從六個方面展開，本書?容全面、應用性?，適合學生?讀。"
    )
    assert localize_catalog_text(chinese, "zh") == (
        "本书属于 技术与工程，介绍先进技術產品和技术产品；"
        "全書分別從六個方面展開，本書內容全面、應用性強，適合學生閱讀。"
    )
    assert localize_catalog_text(chinese, "en") == chinese


def test_saved_resource_types_receive_natural_chinese_labels() -> None:
    assert resource_type_label("概念基础", "zh") == "基础概念"
    assert resource_type_label("Technical/Application", "zh") == "技术原理与应用"
    assert resource_type_label("批判与跨学科", "zh") == "批判思考与跨学科视角"
    assert reading_stage_title("概念基础：具身心智", "zh") == "基础概念：具身心智"


def test_internal_resource_types_receive_natural_english_labels() -> None:
    assert resource_type_label("Conceptual Foundation", "en") == "Foundational concepts"
    assert resource_type_label("Technical/Application", "en") == "Technical principles & applications"
    assert reading_stage_title("Conceptual Foundation: The Embodied Mind", "en") == "Foundational concepts: The Embodied Mind"
