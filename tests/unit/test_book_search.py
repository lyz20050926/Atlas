from __future__ import annotations

from src.book_search import evaluate_book_candidates, search_and_assess_book
from src.config import Settings
from src.llm.base import LLMProvider, T
from src.models import BookCandidate, BookSemanticFit, EvidenceRecord, LearningGoal, UserProfile


def goal() -> LearningGoal:
    return LearningGoal(
        topic="Embodied Intelligence",
        purpose="Build a rigorous interdisciplinary foundation",
        duration_weeks=6,
        hours_per_week=4,
        required_perspectives=["Robotics", "Cognitive Science", "Ethics"],
    )


def profile() -> UserProfile:
    return UserProfile(
        user_id="search-test",
        education_level="undergraduate",
        major="EEE",
        background_knowledge=["Python", "Machine Learning"],
        interests=["Robotics"],
    )


def candidate(title: str, canonical_id: str) -> BookCandidate:
    return BookCandidate(
        canonical_id=canonical_id,
        title=title,
        authors=["Example Author"],
        isbn_13=canonical_id,
        description=f"A verified introduction to {title}.",
        language="en",
        page_count=240,
        categories=["Cognitive science", "Robotics"],
        source_records=[
            EvidenceRecord(
                source_name="Google Books",
                source_url="https://books.google.com/example",
                fields_verified=["title", "authors", "isbn_13"],
            )
        ],
        verification_status="verified_single_source",
    )


class SemanticProvider(LLMProvider):
    def generate_structured(self, system: str, user: str, output_model: type[T]) -> T:
        assert "rigorous" in system
        assert "Embodied Intelligence" in user
        return output_model.model_validate(
            BookSemanticFit(
                goal_relevance=0.92,
                prerequisite_fit=0.81,
                perspective_value=0.88,
                recommended_role="Conceptual Foundation",
                recommendation_reason="This book directly supports the learner's conceptual foundation.",
                why_now="It establishes terminology before technical and ethical reading.",
                reservations=["Confirm the table of contents for this edition."],
            )
        )


def test_evaluation_selects_title_match_and_combines_semantic_fit() -> None:
    exact = candidate("Embodied Cognition", "9780000000001")
    distractor = candidate("Robot Ethics", "9780000000002")

    result = evaluate_book_candidates(
        "Embodied Cognition",
        [distractor, exact],
        goal(),
        profile(),
        provider=SemanticProvider(),
    )

    assert result.book.title == "Embodied Cognition"
    assert result.title_match_score > 0.9
    assert result.used_live_model is True
    assert result.assessment.goal_relevance == 0.92
    assert 0 <= result.assessment.overall_rank_score <= 1
    assert result.evaluated_role == "Conceptual Foundation"
    assert len(result.execution_trace) == 4


def test_evaluation_has_transparent_fallback_without_model() -> None:
    result = evaluate_book_candidates(
        "Embodied Cognition",
        [candidate("Embodied Cognition", "9780000000001")],
        goal(),
        profile(),
        provider=None,
    )

    assert result.used_live_model is False
    assert result.assessment.recommendation_reason
    assert 0 <= result.assessment.overall_rank_score <= 1


def test_unrelated_biography_is_not_forced_into_learning_path() -> None:
    biography = BookCandidate(
        canonical_id="9780000000099",
        title="Elon Musk",
        authors=["Example Biographer"],
        isbn_13="9780000000099",
        description=(
            "A biography of an entrepreneur covering his companies, personal life, "
            "business ambitions, and public image."
        ),
        language="en",
        page_count=320,
        categories=["Biography & Autobiography", "Business"],
        source_records=[
            EvidenceRecord(
                source_name="Google Books",
                source_url="https://books.google.com/example-biography",
                fields_verified=["title", "authors", "isbn_13"],
            )
        ],
        verification_status="verified_single_source",
    )

    result = evaluate_book_candidates("musk", [biography], goal(), profile(), provider=None)

    assert result.assessment.goal_relevance < 0.3
    assert result.assessment.overall_rank_score < 0.35
    assert "should not be included" in result.assessment.recommendation_reason
    assert "not recommended" in result.execution_trace[-1]


def test_biography_guard_rejects_overconfident_semantic_score() -> None:
    biography = candidate("Elon Musk: A Biography", "9780000000100").model_copy(
        update={
            "description": "A biography of an entrepreneur and his business ventures.",
            "categories": ["Biography & Autobiography", "Business"],
        }
    )

    result = evaluate_book_candidates(
        "Elon Musk",
        [biography],
        goal(),
        profile(),
        provider=SemanticProvider(),
    )

    assert result.used_live_model is True
    assert result.assessment.goal_relevance <= 0.2
    assert result.assessment.overall_rank_score < 0.35
    assert "should not be included" in result.assessment.recommendation_reason


def test_evaluation_rejects_empty_search_results() -> None:
    try:
        evaluate_book_candidates("Missing Book", [], goal(), profile())
    except LookupError as exc:
        assert "No verifiable" in str(exc)
    else:
        raise AssertionError("Expected LookupError")


def test_explicit_exclusion_is_explained_as_preference_conflict_not_wrong_subject() -> None:
    requested = goal().model_copy(update={"topic": "Machine learning", "purpose": "Use Python. No MATLAB."})
    book = candidate("MATLAB Machine Learning", "9780000000202")
    result = evaluate_book_candidates(book.title, [book], requested, profile(), provider=SemanticProvider())
    assert result.assessment.goal_relevance == 0
    assert "explicit exclusion" in result.assessment.recommendation_reason


class SearchClient:
    def __init__(self, results: list[BookCandidate]) -> None:
        self.results = results

    def search(self, *args: object, **kwargs: object) -> list[BookCandidate]:
        return self.results


def test_direct_search_prefers_an_exact_verified_book_from_the_active_path() -> None:
    current = candidate("Autonomous Mobile Robots", "9780000000200")
    loose_api_match = candidate("Mobile Robot Control", "9780000000201")

    result = search_and_assess_book(
        "Autonomous Mobile Robots",
        goal(),
        profile(),
        Settings(),
        google_client=SearchClient([loose_api_match]),
        open_library_client=SearchClient([]),
        known_candidates=[current],
    )

    assert result.book.canonical_id == current.canonical_id
    assert result.title_match_score > 0.9
