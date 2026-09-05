from __future__ import annotations

from typing import TypedDict

from src.models import (
    BookAssessment,
    BookCandidate,
    ConceptMastery,
    ConceptRequirement,
    LearningGoal,
    PlanRevision,
    ReadingPath,
    UserProfile,
)


class AgentState(TypedDict):
    user_profile: UserProfile
    learning_goal: LearningGoal
    concept_requirements: list[ConceptRequirement]
    search_queries: list[str]
    raw_candidates: list[BookCandidate]
    verified_candidates: list[BookCandidate]
    selected_books: list[BookCandidate]
    assessments: list[BookAssessment]
    reading_path: ReadingPath | None
    concept_mastery: list[ConceptMastery]
    user_feedback: list[dict]
    plan_revisions: list[PlanRevision]
    search_iteration: int
    max_search_iterations: int
    errors: list[str]
    warnings: list[str]
    data_mode: str
    execution_trace: list[str]
