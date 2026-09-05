from __future__ import annotations

import json

from src.config import Settings
from src.graph import run_recommendation_graph
from src.llm.base import LLMProvider, T
from src.models import BookCandidate, LearningGoal, UserProfile
from src.services.goal_alignment import PathSelection, RetrievalBrief
from src.services.recommendation import load_demo_candidates
from src.services.scoring import SCORING_VERSION


def profile() -> UserProfile:
    return UserProfile(
        user_id="graph-user",
        education_level="undergraduate",
        major="EEE",
        background_knowledge=["Python", "Machine Learning", "Control theory"],
        interests=["Robotics", "Cognitive Science", "Ethics"],
    )


def goal() -> LearningGoal:
    return LearningGoal(
        topic="Embodied Intelligence",
        purpose="Learn",
        duration_weeks=6,
        hours_per_week=4,
        required_perspectives=["Robotics", "Cognitive Science", "Ethics"],
        preferred_difficulty="intermediate",
        desired_balance="theory and application",
    )


class NarrativeProvider(LLMProvider):
    def generate_structured(self, system: str, user: str, output_model: type[T]) -> T:
        if output_model is RetrievalBrief:
            return output_model(foundation_query="embodied cognition", application_query="mobile robots", perspective_query="robot ethics")
        assert output_model is PathSelection
        assert "NOT a salesperson" in system
        payload = {"gaps": "", "requirements_met": True}
        for role, prefix in zip(("Conceptual Foundation", "Technical/Application", "Critical/Cross-disciplinary"),
                                ("foundation", "application", "perspective"), strict=True):
            payload[f"{prefix}_id"] = json.loads(user)["candidates_by_role"][role][0]["id"]
            payload[f"{prefix}_reason"] = f"Relevant to {role} based on the supplied description."
        return output_model.model_validate(payload)


def test_graph_retries_with_cached_evidence_and_terminates() -> None:
    calls = 0

    def empty_search(goal, settings):
        nonlocal calls
        calls += 1
        return [], ["Both live sources unavailable in test"]

    result = run_recommendation_graph(
        profile(),
        goal(),
        Settings(max_search_iterations=3),
        allow_cached_fallback=True,
        search_function=empty_search,
    )
    assert calls == 1
    assert result.data_mode == "cached_demo"
    assert len(result.reading_path.stages) == 3
    assert result.reading_path.constraints_satisfied
    assert any(step.startswith("Search pass 2") for step in result.execution_trace)
    assert result.execution_trace[-1].startswith("Checked the path")


def test_graph_uses_verified_live_candidates_without_retry() -> None:
    def fixture_search(goal, settings):
        return load_demo_candidates(), []

    result = run_recommendation_graph(
        profile(), goal(), Settings(), search_function=fixture_search
    )
    assert result.data_mode == "live"
    assert result.scoring_version == SCORING_VERSION
    assert len(result.selected_books) == 3
    assert sum(step.startswith("Search pass") for step in result.execution_trace) == 1


def test_graph_retries_when_live_results_cover_roles_but_fail_semantic_fit() -> None:
    irrelevant = [
        BookCandidate(
            canonical_id=f"generic-{index}",
            title=f"General Technology Systems {index}",
            authors=["Example Author"],
            description="A general handbook about technology systems and applications.",
            categories=["Technology"],
            language="en",
            verification_status="verified_single_source",
            search_roles=[role],
        )
        for index, role in enumerate((
            "Conceptual Foundation",
            "Technical/Application",
            "Critical/Cross-disciplinary",
        ))
    ]

    result = run_recommendation_graph(
        profile(),
        goal(),
        Settings(max_search_iterations=3),
        search_function=lambda goal, settings: (irrelevant, []),
    )

    assert result.data_mode == "mixed"
    assert len(result.selected_books) == 3
    assert all(not book.canonical_id.startswith("generic-") for book in result.selected_books)
    assert sum(step.startswith("Search pass") for step in result.execution_trace) == 2


def test_graph_checks_goal_suitability_before_writing_reasons() -> None:
    provider = NarrativeProvider()
    result = run_recommendation_graph(
        profile(),
        goal(),
        Settings(),
        search_function=lambda goal, settings: (load_demo_candidates(), []),
        provider=provider,
    )

    assert len(result.assessments) == 3
    assert all(item.book_overview and item.meets_stated_requirements for item in result.assessments)
    assert len({item.recommendation_reason for item in result.assessments}) == 3
    assert any("Amazon Bedrock" in step for step in result.execution_trace)


def test_graph_localizes_cached_fallback_trace_and_warnings_in_chinese() -> None:
    chinese_profile = profile().model_copy(
        update={"major": "电子与电气工程", "interface_language": "zh"}
    )
    chinese_goal = goal().model_copy(
        update={
            "topic": "具身智能",
            "interface_language": "zh",
            "book_language_preferences": ["zh"],
        }
    )

    result = run_recommendation_graph(
        chinese_profile,
        chinese_goal,
        Settings(max_search_iterations=3),
        search_function=lambda goal, settings: ([], []),
    )

    assert all(not step.startswith(("PLAN", "ACT", "OBSERVE", "ADAPT", "FINALIZE", "VERIFY")) for step in result.execution_trace)
    assert any("缓存示例数据" in warning for warning in result.warnings)
