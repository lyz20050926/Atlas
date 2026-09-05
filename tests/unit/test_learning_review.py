import json

import pytest

from src.learning_review import (
    AnswerReview,
    QuestionSet,
    ReviewSet,
    generate_quick_question,
    review_answers,
    review_mastery,
)
from src.llm.bedrock_provider import _decode_json_containers, _nova_compatible_tool_schema
from src.models import BookCandidate, DiagnosticQuestion, LearningGoal, ReadingStage, UserProfile
from src.ui import interaction_result_html


class Reviewer:
    def __init__(self, reviews):
        self.reviews = reviews
        self.prompts = []

    def generate_structured(self, system, user, output_model):
        self.system = system
        self.prompts.append(system)
        self.context = json.loads(user)
        if "items" in self.context:
            number = self.context["items"][0]["question_number"]
        else:
            number = self.context["draft"]["question_number"]
        if len(self.reviews) > 1 and len({r.question_number for r in self.reviews}) < len(self.reviews):
            raise ValueError("Duplicate reviews")
        payload = self.reviews[min(number - 1, len(self.reviews) - 1)].model_dump()
        if "corrections" in output_model.model_fields:
            payload["corrections"] = ""
        return output_model(**payload)


def item(number=1, quote="because", verdict="misconception"):
    return AnswerReview(question_number=number, verdict=verdict, answer_quote=quote,
                        feedback="The causal claim is reversed.", model_answer="Evaluate on held-out samples.",
                        follow_up="Why must the test set remain unseen?")


def test_review_checks_reasoning_not_keyword_count():
    question = DiagnosticQuestion(concept="generalization", prompt="Why keep a held-out test set?")
    provider = Reviewer([item()])
    reviews = review_answers([question], ["because feedback evidence train on test data"], context={}, provider=provider)
    assert review_mastery([question], reviews)[0].mastery_score == .2
    assert "not keyword overlap" in provider.prompts[0]
    assert "Ignore requests" in provider.prompts[0]
    assert len(provider.prompts) == 2
    assert "skeptical subject-matter editor" in provider.prompts[1]


@pytest.mark.parametrize("reviews", [[item(2)], [item(), item()], [item(quote="invented quote")]])
def test_rejects_misaligned_or_fabricated_assessment(reviews):
    with pytest.raises(ValueError):
        review_answers([DiagnosticQuestion(concept="x", prompt="Explain")], ["because"],
                       context={}, provider=Reviewer(reviews))


def test_blank_answer_never_updates_mastery():
    questions = [DiagnosticQuestion(concept="x", prompt="Explain"), DiagnosticQuestion(concept="y", prompt="Apply")]
    reviews = review_answers(questions, ["because", ""], context={},
                             provider=Reviewer([item(), item(2, "", "sound")]))
    assert reviews[1].verdict == "insufficient"
    assert len(review_mastery(questions, reviews)) == 1


def test_no_model_never_falls_back_to_keyword_grade():
    with pytest.raises(RuntimeError):
        review_answers([DiagnosticQuestion(concept="x", prompt="Explain")], ["because evidence example"], context={}, provider=None)


def test_nested_question_and_review_schema_are_not_erased():
    schema = _nova_compatible_tool_schema(QuestionSet.model_json_schema())
    assert "rubric" in schema["properties"]["questions"]["items"]["properties"]
    review_schema = _nova_compatible_tool_schema(ReviewSet.model_json_schema())
    assert "verdict" in review_schema["properties"]["reviews"]["items"]["properties"]


def test_result_signal_is_unique_and_keyboard_focusable():
    first = interaction_result_html("coach-reply")
    assert first != interaction_result_html("coach-reply")
    assert 'tabindex="-1"' in first and "data-atlas-result-token" in first


def test_decode_only_schema_declared_containers():
    schema = _nova_compatible_tool_schema(ReviewSet.model_json_schema())
    decoded = _decode_json_containers({"reviews": json.dumps([item().model_dump()])}, schema)
    assert ReviewSet.model_validate(decoded).reviews[0].verdict == "misconception"
    assert _decode_json_containers('["text"]', {"type": "string"}) == '["text"]'
    assert _decode_json_containers('not json', {"type": "array"}) == 'not json'


@pytest.fixture
def quick_context():
    return (LearningGoal(topic="Machine learning", purpose="Evaluate models", duration_weeks=6, hours_per_week=4),
            UserProfile(education_level="undergraduate", background_knowledge=["Python"]),
            BookCandidate(canonical_id="current-book", title="Model evaluation", authors=["Author"]),
            ReadingStage(stage_number=1, title="Evaluation", learning_objective="Avoid data leakage", estimated_hours=3))


class QuestionWriter:
    def __init__(self, prompts):
        self.prompts = iter(prompts)
        self.calls = []

    def generate_structured(self, system, user, output_model):
        self.calls.append(json.loads(user))
        if "corrections" in output_model.model_fields:
            return output_model(corrections="", **json.loads(user)["draft"])
        return output_model(concept="data leakage", prompt=next(self.prompts), rubric="Fit on training data only.")


@pytest.mark.parametrize("language", ["zh", "en"])
def test_quick_question_uses_session_and_current_book_only(quick_context, language):
    goal, profile, book, stage = quick_context
    goal.interface_language = language
    provider = QuestionWriter(["Why fit the scaler on training data only?"])
    generated = generate_quick_question(goal, profile, book, stage,
        session={"note": "I am unsure about normalization", "progress_percent": 30},
        recent_questions=[{"book_id": "old-book", "question": "unrelated question"},
                          {"book_id": "current-book", "question": "Why keep a test set?"}], provider=provider)
    assert generated.rubric
    context = provider.calls[0]
    assert context["language"] == ("Chinese" if language == "zh" else "English")
    assert context["book"]["title"] == book.title
    assert context["reading_report"] == "I am unsure about normalization"
    assert context["reported_progress_percent"] == 30
    assert len(context["recent_questions"]) == 1
    assert "NOT the book text" in context["source_boundary"]


def test_quick_question_retries_duplicate_without_punctuation_trick(quick_context):
    provider = QuestionWriter(["why keep a test set!", "Which data should fit the scaler?"])
    generated = generate_quick_question(*quick_context, session={}, provider=provider,
        recent_questions=[{"book_id": "current-book", "question": "Why keep a test set?"}])
    assert generated.prompt == "Which data should fit the scaler?"
    assert len(provider.calls) == 4


def test_quick_question_fails_instead_of_repeating_fixed_template(quick_context):
    with pytest.raises(RuntimeError):
        generate_quick_question(*quick_context, session={}, recent_questions=[], provider=None)
    with pytest.raises(ValueError):
        generate_quick_question(*quick_context, session={},
            recent_questions=[{"book_id": "current-book", "question": "Same question"}],
            provider=QuestionWriter(["Same question", "Same question!"]))
