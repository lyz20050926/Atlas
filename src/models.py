from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, HttpUrl, model_validator

Confidence = Literal["low", "medium", "high"]


class UserProfile(BaseModel):
    user_id: str = Field(default_factory=lambda: str(uuid4()))
    education_level: str
    major: str | None = None
    background_knowledge: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    language_preferences: list[str] = Field(default_factory=lambda: ["English"])
    reading_preferences: list[str] = Field(default_factory=list)
    completed_books: list[str] = Field(default_factory=list)
    interface_language: Literal["en", "zh"] = "en"


class LearningGoal(BaseModel):
    topic: str = Field(min_length=2)
    purpose: str = Field(min_length=2)
    focus_details: str = Field(default="", max_length=2000)
    duration_weeks: int = Field(gt=0, le=52)
    hours_per_week: float = Field(gt=0, le=80)
    required_perspectives: list[str] = Field(default_factory=list)
    preferred_difficulty: str = "intermediate"
    desired_balance: str = "theory and application"
    interface_language: Literal["en", "zh"] = "en"
    book_language_preferences: list[Literal["en", "zh"]] = Field(default_factory=lambda: ["en"])
    catalog_queries: dict[str, str] = Field(default_factory=dict)

    @property
    def total_hours(self) -> float:
        return round(self.duration_weeks * self.hours_per_week, 1)


class ConceptRequirement(BaseModel):
    concept: str
    importance: str
    prerequisites: list[str] = Field(default_factory=list)
    current_mastery: float = Field(default=0.0, ge=0, le=1)
    required_resource_type: str


class EvidenceRecord(BaseModel):
    source_name: str
    source_url: HttpUrl | None = None
    source_book_id: str | None = None
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    fields_verified: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


class BookCandidate(BaseModel):
    canonical_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    isbn_10: str | None = None
    isbn_13: str | None = None
    published_year: int | None = None
    description: str | None = None
    language: str | None = None
    page_count: int | None = None
    categories: list[str] = Field(default_factory=list)
    average_rating: float | None = None
    ratings_count: int | None = None
    cover_url: HttpUrl | None = None
    source_records: list[EvidenceRecord] = Field(default_factory=list)
    verification_status: str = "unverified"
    search_roles: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_identity(self) -> BookCandidate:
        if not self.title.strip() or (not self.authors and not self.isbn_10 and not self.isbn_13):
            raise ValueError("A candidate needs a title plus an author or ISBN")
        return self


class BookAssessment(BaseModel):
    meets_stated_requirements: bool | None = None
    canonical_id: str
    goal_relevance: float = Field(ge=0, le=1)
    prerequisite_fit: float = Field(ge=0, le=1)
    evidence_strength: float = Field(ge=0, le=1)
    perspective_value: float = Field(ge=0, le=1)
    time_feasibility: float = Field(ge=0, le=1)
    language_fit: float = Field(default=0.5, ge=0, le=1)
    overall_rank_score: float = Field(ge=0, le=1)
    book_overview: str = ""
    recommendation_reason: str
    why_now: str
    reservations: list[str] = Field(default_factory=list)
    confidence: Confidence
    evaluated_role: str = ""


class RecommendationNarrativeBatch(BaseModel):
    """Flat schema so Bedrock/Nova tool calling can enrich all three books in one request."""

    stage_1_overview: str = Field(min_length=30)
    stage_1_reason: str = Field(min_length=30)
    stage_1_why_now: str = Field(min_length=20)
    stage_1_reservations: list[str] = Field(default_factory=list)
    stage_2_overview: str = Field(min_length=30)
    stage_2_reason: str = Field(min_length=30)
    stage_2_why_now: str = Field(min_length=20)
    stage_2_reservations: list[str] = Field(default_factory=list)
    stage_3_overview: str = Field(min_length=30)
    stage_3_reason: str = Field(min_length=30)
    stage_3_why_now: str = Field(min_length=20)
    stage_3_reservations: list[str] = Field(default_factory=list)


class BookSemanticFit(BaseModel):
    goal_relevance: float = Field(ge=0, le=1)
    prerequisite_fit: float = Field(ge=0, le=1)
    perspective_value: float = Field(ge=0, le=1)
    recommended_role: Literal[
        "Conceptual Foundation",
        "Technical/Application",
        "Critical/Cross-disciplinary",
    ]
    recommendation_reason: str = Field(min_length=10)
    why_now: str = Field(min_length=10)
    reservations: list[str] = Field(default_factory=list)


class BookSearchEvaluation(BaseModel):
    query: str
    book: BookCandidate
    assessment: BookAssessment
    evaluated_role: str
    title_match_score: float = Field(ge=0, le=1)
    alternatives: list[BookCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    execution_trace: list[str] = Field(default_factory=list)
    used_live_model: bool = False


class ReadingStage(BaseModel):
    stage_number: int = Field(gt=0)
    title: str
    learning_objective: str
    concepts: list[str] = Field(default_factory=list)
    books: list[str] = Field(default_factory=list)
    selected_chapters: list[str] = Field(default_factory=list)
    estimated_hours: float = Field(ge=0)
    guiding_questions: list[str] = Field(default_factory=list)


class ReadingPath(BaseModel):
    path_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    version: int = Field(default=1, gt=0)
    total_weeks: int = Field(gt=0)
    total_estimated_hours: float = Field(ge=0)
    stages: list[ReadingStage]
    constraints_satisfied: bool
    warnings: list[str] = Field(default_factory=list)


class ConceptMastery(BaseModel):
    concept: str
    mastery_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PlanRevision(BaseModel):
    previous_version: int
    new_version: int
    trigger: str
    changed_constraints: dict[str, Any] = Field(default_factory=dict)
    removed_items: list[str] = Field(default_factory=list)
    added_items: list[str] = Field(default_factory=list)
    reordered_items: list[str] = Field(default_factory=list)
    explanation: str
    preserved_goals: list[str] = Field(default_factory=list)


class RecommendationResult(BaseModel):
    scoring_version: int = Field(default=1, ge=1)
    data_mode: Literal["live", "cached_demo", "mixed"]
    concepts: list[ConceptRequirement]
    candidates: list[BookCandidate]
    selected_books: list[BookCandidate]
    assessments: list[BookAssessment]
    reading_path: ReadingPath
    warnings: list[str] = Field(default_factory=list)
    execution_trace: list[str] = Field(default_factory=list)


class DiagnosticQuestion(BaseModel):
    concept: str
    prompt: str
    expected_signals: list[str] = Field(default_factory=list)
    rubric: str = ""
    question_type: Literal["short_answer", "single_choice", "true_false"] = "short_answer"
    options: list[str] = Field(default_factory=list)
    correct_answer: str = ""
    explanation: str = ""
    generation_source: Literal["model", "local"] = "model"

    @model_validator(mode="after")
    def validate_answer_contract(self) -> DiagnosticQuestion:
        """Keep old short-answer records readable; objective keys must be exact."""
        self.options = [option.strip() for option in self.options]
        self.correct_answer = self.correct_answer.strip()
        self.explanation = self.explanation.strip()
        if self.question_type == "short_answer":
            if self.options or self.correct_answer:
                raise ValueError("Short-answer questions cannot carry objective answer keys")
            return self
        expected_count = 4 if self.question_type == "single_choice" else 2
        if len(self.options) != expected_count or any(not option for option in self.options):
            raise ValueError(f"This question requires {expected_count} nonempty options")
        if len({option.casefold() for option in self.options}) != len(self.options):
            raise ValueError("Answer options must be distinct")
        if self.question_type == "true_false" and self.options not in (["正确", "错误"], ["True", "False"]):
            raise ValueError("True/false options must use the supported localized labels")
        if self.correct_answer not in self.options:
            raise ValueError("The answer key must match one exact option")
        if not self.explanation:
            raise ValueError("Objective questions require a rationale")
        return self


class ReadingSessionInput(BaseModel):
    book_title: str
    chapter: str | None = None
    notes: str = ""
    excerpt: str = Field(min_length=10, max_length=6000)
    question: str = Field(min_length=2, max_length=1000)
    target_concept: str
    response_language: Literal["English", "Chinese"] = "English"


class ReadingSupportOutput(BaseModel):
    grounding: str
    explanation: str
    connection: str
    guiding_question: str
    recall_question: str
    reflection_task: str
    mastery_update_suggestion: float = Field(ge=-0.2, le=0.2)
    limitations: list[str] = Field(default_factory=list)


class MentorResponse(BaseModel):
    """A flat, Bedrock-compatible action envelope for the learning mentor."""

    reply: str = Field(min_length=2)
    intent: Literal[
        "question",
        "progress_update",
        "replace_book",
        "replan",
        "motivation",
        "check_in",
        "general",
    ]
    progress_percent: int = Field(ge=-1, le=100)
    reading_status: Literal["unchanged", "planned", "reading", "paused", "completed"]
    replace_book: bool
    replacement_reason: Literal[
        "none",
        "not_relevant",
        "too_difficult",
        "too_basic",
        "too_theoretical",
        "already_read",
        "cannot_access",
        "other",
    ]
    replacement_query: str
    should_replan: bool
    revised_hours_per_week: float = Field(ge=0, le=80)
    too_theoretical: bool
    low_mastery_concept: str
    next_step: str
    encouragement: str
    next_check_in_days: int = Field(ge=1, le=14)
