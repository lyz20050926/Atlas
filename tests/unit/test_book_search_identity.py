"""Search identity must be established before learning-goal fit is assessed."""

from __future__ import annotations

import httpx
import pytest

from src import book_search
from src.config import Settings
from src.llm.base import LLMProvider, T
from src.models import BookCandidate, EvidenceRecord, LearningGoal, UserProfile


@pytest.fixture
def learning_goal() -> LearningGoal:
    return LearningGoal(
        topic="机器学习",
        purpose="用 Python 进行机器学习研究",
        duration_weeks=6,
        hours_per_week=4,
        required_perspectives=["计算机科学"],
    )


@pytest.fixture
def learner() -> UserProfile:
    return UserProfile(
        user_id="search-identity-regression",
        education_level="undergraduate",
        major="计算机科学",
        background_knowledge=["Python"],
    )


def book(title: str, identifier: str, *, isbn: str | None = None) -> BookCandidate:
    return BookCandidate(
        canonical_id=identifier,
        title=title,
        authors=["Test Author"],
        isbn_13=isbn,
        description="Test catalogue metadata, not the full text.",
        language="zh",
        page_count=240,
        categories=[],
        source_records=[
            EvidenceRecord(
                source_name="Google Books",
                source_url=f"https://books.google.com/books?id={identifier}",
                fields_verified=["title", "authors"],
            )
        ],
        verification_status="verified_single_source",
    )


class RecordingProvider(LLMProvider):
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_structured(self, system: str, user: str, output_model: type[T]) -> T:
        self.calls.append(user)
        return output_model.model_validate(
            {
                "goal_relevance": 0.1,
                "prerequisite_fit": 0.4,
                "perspective_value": 0.1,
                "recommended_role": "Conceptual Foundation",
                "recommendation_reason": "This work does not match the current research goal.",
                "why_now": "Keep this book outside the current learning path.",
                "reservations": ["Only catalogue metadata is available."],
            }
        )


class SearchClient:
    def __init__(self, results: list[BookCandidate], *, fail: bool = False) -> None:
        self.results = results
        self.fail = fail
        self.queries: list[str] = []
        self.request_options: list[dict[str, object]] = []

    def search(self, query: str, **kwargs: object) -> list[BookCandidate]:
        self.queries.append(query)
        self.request_options.append(kwargs)
        if self.fail:
            raise httpx.ConnectError("Test catalogue is unavailable")
        return self.results


@pytest.mark.parametrize("query", ["斗罗大陆", "这本书完全不存在ABCDEFG", "", "   ", "《》？！…"])
def test_unmatched_query_never_assesses_an_unrelated_book(
    query: str, learning_goal: LearningGoal, learner: UserProfile
) -> None:
    provider = RecordingProvider()
    with pytest.raises(LookupError):
        book_search.evaluate_book_candidates(
            query,
            [book("金融大数据研究与应用", "finance")],
            learning_goal,
            learner,
            provider,
        )
    assert provider.calls == []


@pytest.mark.parametrize("query", ["", " ", "《》？！…", "斗罗大陆"])
def test_identity_rejects_empty_or_unrelated_query(query: str) -> None:
    assert not book_search.is_search_identity_match(query, book("金融大数据研究与应用", "finance"))


@pytest.mark.parametrize("query", ["斗罗大陆", "《斗罗大陆》", "  斗罗大陆  "])
def test_exact_title_accepts_display_punctuation(query: str) -> None:
    assert book_search.is_search_identity_match(query, book("斗罗大陆", "novel"))


def test_english_title_accepts_punctuation_and_case() -> None:
    assert book_search.is_search_identity_match(
        "Hands On Machine Learning", book("Hands-On Machine Learning", "ml")
    )


def test_english_whole_word_fragment_remains_searchable() -> None:
    assert book_search.is_search_identity_match("musk", book("Elon Musk", "biography"))


def test_short_english_word_does_not_match_inside_another_word() -> None:
    assert not book_search.is_search_identity_match("Art", book("Artificial Intelligence", "ai"))


@pytest.mark.parametrize("query", ["9781449369415", "978-1-4493-6941-5", "978 1 4493 6941 5"])
def test_formatted_isbn_matches_the_record_identifier(query: str) -> None:
    assert book_search.is_search_identity_match(
        query, book("An Exact ISBN Match", "isbn-record", isbn="9781449369415")
    )


def test_wrong_isbn_cannot_be_rescued_by_a_similar_identifier() -> None:
    assert not book_search.is_search_identity_match(
        "9781449369416", book("An Exact ISBN Match", "isbn-record", isbn="9781449369415")
    )


def test_numeric_query_requires_isbn_evidence_not_a_title_match(
    learning_goal: LearningGoal, learner: UserProfile
) -> None:
    provider = RecordingProvider()
    misleading = book("9781449369416", "wrong-isbn", isbn="9781449369415")
    with pytest.raises(LookupError):
        book_search.evaluate_book_candidates("9781449369416", [misleading], learning_goal, learner, provider)
    assert provider.calls == []


def test_unavailable_catalogues_do_not_fall_back_to_an_unrelated_path_book(
    learning_goal: LearningGoal, learner: UserProfile
) -> None:
    provider = RecordingProvider()
    with pytest.raises(LookupError):
        book_search.search_and_assess_book(
            "斗罗大陆",
            learning_goal,
            learner,
            Settings(),
            provider=provider,
            google_client=SearchClient([], fail=True),
            open_library_client=SearchClient([], fail=True),
            known_candidates=[book("金融大数据研究与应用", "finance")],
        )
    assert provider.calls == []


def test_unavailable_catalogues_can_use_an_exact_previously_verified_record(
    learning_goal: LearningGoal, learner: UserProfile
) -> None:
    exact = book("斗罗大陆", "novel")
    result = book_search.search_and_assess_book(
        "斗罗大陆",
        learning_goal,
        learner,
        Settings(),
        google_client=SearchClient([], fail=True),
        open_library_client=SearchClient([], fail=True),
        known_candidates=[book("金融大数据研究与应用", "finance"), exact],
    )
    assert result.book.canonical_id == exact.canonical_id
    assert result.warnings
    assert result.alternatives == []


def test_novel_identity_is_not_overridden_by_the_machine_learning_goal(
    learning_goal: LearningGoal, learner: UserProfile
) -> None:
    novel = book("斗罗大陆", "novel").model_copy(
        update={"authors": ["唐家三少"], "categories": ["Fantasy fiction"], "description": "A fantasy novel."}
    )
    research = book("金融大数据研究与应用", "finance").model_copy(
        update={"description": "机器学习 Python 计算机科学 研究", "categories": ["机器学习"]}
    )
    provider = RecordingProvider()
    result = book_search.search_and_assess_book(
        "斗罗大陆",
        learning_goal,
        learner,
        Settings(),
        provider=provider,
        google_client=SearchClient([novel, research]),
        open_library_client=SearchClient([]),
        known_candidates=[research],
    )
    assert result.book.canonical_id == novel.canonical_id
    assert len(provider.calls) == 1
    assert result.assessment.goal_relevance < 0.3
    assert result.alternatives == []


def test_alternative_choices_also_require_search_identity(
    learning_goal: LearningGoal, learner: UserProfile
) -> None:
    result = book_search.evaluate_book_candidates(
        "Art",
        [book("Artificial Intelligence", "ai"), book("Art", "art"), book("Financial Data", "finance")],
        learning_goal,
        learner,
    )
    assert result.book.canonical_id == "art"
    assert result.alternatives == []


@pytest.mark.parametrize(
    ("query", "expected_google_query"),
    [
        ("斗罗大陆", 'intitle:"斗罗大陆"'),
        ("978-1-4493-6941-5", "isbn:9781449369415"),
        ("ISBN-13: 9781449369415", "isbn:9781449369415"),
    ],
)
def test_google_uses_a_title_or_isbn_query_before_keyword_search(
    query: str, expected_google_query: str, learning_goal: LearningGoal, learner: UserProfile
) -> None:
    exact = book("斗罗大陆", "novel", isbn="9781449369415")
    google = SearchClient([exact])
    open_library = SearchClient([])
    result = book_search.search_and_assess_book(
        query,
        learning_goal,
        learner,
        Settings(),
        google_client=google,
        open_library_client=open_library,
    )
    assert google.queries == [expected_google_query]
    assert open_library.queries == [query]
    assert result.book.canonical_id == exact.canonical_id


def test_direct_chinese_title_search_does_not_inherit_english_path_filter(
    learning_goal: LearningGoal, learner: UserProfile
) -> None:
    english_goal = learning_goal.model_copy(
        update={"book_language_preferences": ["en"], "interface_language": "en"}
    )
    google = SearchClient([book("斗罗大陆", "novel")])
    open_library = SearchClient([])
    result = book_search.search_and_assess_book(
        "斗罗大陆",
        english_goal,
        learner,
        Settings(),
        google_client=google,
        open_library_client=open_library,
    )
    assert result.book.language == "zh"
    assert all(options.get("language") is None for options in google.request_options)
    assert all(options.get("language") is None for options in open_library.request_options)


def test_unmatched_google_title_query_can_retry_plain_query_for_the_exact_book(
    learning_goal: LearningGoal, learner: UserProfile
) -> None:
    exact = book("斗罗大陆", "novel")

    class QuerySpecificClient(SearchClient):
        def search(self, query: str, **kwargs: object) -> list[BookCandidate]:
            self.queries.append(query)
            self.request_options.append(kwargs)
            if query.startswith("intitle:"):
                return [book("金融大数据研究与应用", "finance")]
            return [exact]

    google = QuerySpecificClient([])
    result = book_search.search_and_assess_book(
        "斗罗大陆",
        learning_goal,
        learner,
        Settings(),
        google_client=google,
        open_library_client=SearchClient([]),
    )
    assert google.queries == ['intitle:"斗罗大陆"', "斗罗大陆"]
    assert result.book.canonical_id == exact.canonical_id
    assert result.alternatives == []


def test_low_semantic_fit_preserves_the_models_negative_explanation(
    learning_goal: LearningGoal, learner: UserProfile
) -> None:
    provider = RecordingProvider()
    result = book_search.evaluate_book_candidates(
        "斗罗大陆",
        [book("斗罗大陆", "novel")],
        learning_goal,
        learner,
        provider=provider,
    )
    assert result.used_live_model is True
    assert result.assessment.goal_relevance == 0.1
    assert result.assessment.recommendation_reason == "This work does not match the current research goal."
    assert result.assessment.why_now == "Keep this book outside the current learning path."


def test_single_partial_title_is_identified_as_a_possible_adaptation(
    learning_goal: LearningGoal, learner: UserProfile
) -> None:
    result = book_search.evaluate_book_candidates(
        "斗罗大陆", [book("斗罗大陆人物绘本", "picture-book")], learning_goal, learner
    )
    assert any("斗罗大陆人物绘本" in warning and "ISBN" in warning for warning in result.warnings)
