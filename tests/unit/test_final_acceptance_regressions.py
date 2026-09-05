import json

import pytest

from src.learning_review import LocalizedQuestionText, _localize_question_set, _needs_chinese_prose
from src.mentor import _fallback_response
from src.models import BookCandidate, DiagnosticQuestion, LearningGoal, UserProfile
from src.services.goal_alignment import PathSelection, SelectionConstraintAudit, review_selection


@pytest.fixture
def goal():
    return LearningGoal(topic="具身智能", purpose="建立跨学科基础", duration_weeks=6, hours_per_week=4,
                        interface_language="zh", required_perspectives=["机器人学", "认知科学", "伦理学"])


@pytest.mark.parametrize("message,expected", [
    ("I have only two hours this week and have read 30%.", 30),
    ("I've been busy but have already completed 45%.", 45),
    ("I have read 30%.", 30),
    ("我已经读到30%。", 30),
    ("I have two hours and have not read 30%.", -1),
    ("I have two hours and hope to read 30%.", -1),
    ("I have a model and have measured 90% accuracy.", -1),
    ("I have two hours and my friend has read 30%.", -1),
    ("Does 100% training accuracy imply generalization?", -1),
])
def test_compound_reading_reports_do_not_confuse_subject_metrics_or_intentions(goal, message, expected):
    book = BookCandidate(canonical_id="qa", title="Reading", authors=["Author"])
    assert _fallback_response(message, goal, book).progress_percent == expected


@pytest.mark.parametrize("text,bad", [
    ("Embodied cognition depends on bodily interaction with the environment.", True),
    ("选对了。Embodied cognition depends on bodily interaction with the environment.", True),
    ("可以使用 Python、scikit-learn 或 MATLAB 实现这个简单实验。", False),
    ("感知是主动探索的过程，而非仅被动接收信息。", False),
    ("PID", False),
])
def test_chinese_prose_guard_allows_technical_terms(text, bad):
    assert _needs_chinese_prose(text) is bad


class Translator:
    def __init__(self, broken=False):
        self.broken = broken
        self.calls = 0

    def generate_structured(self, system, user, output_model):
        assert output_model is LocalizedQuestionText
        self.calls += 1
        texts = json.loads(user)["texts"]
        return output_model(texts=texts if self.broken else ["身体与环境共同参与认知。" for _ in texts])


def test_language_repair_keeps_choice_position_and_answer_contract(goal):
    question = DiagnosticQuestion(concept="具身认知", prompt="哪项符合具身认知？", question_type="single_choice",
        options=["只有符号", "Bodies interact with the environment", "只有中央处理器", "与环境无关"],
        correct_answer="Bodies interact with the environment", explanation="Bodies interact with the environment to shape cognition.")
    translator = Translator()
    repaired = _localize_question_set([question], goal, translator)[0]
    assert repaired.correct_answer == repaired.options[1]
    assert repaired.explanation == "身体与环境共同参与认知。"
    assert question.options[1] == "Bodies interact with the environment"  # originals are not mutated
    assert translator.calls == 1
    with pytest.raises(ValueError, match="language repair failed"):
        _localize_question_set([question], goal, Translator(broken=True))


class ConstraintReviewer:
    def __init__(self, blockers=(), fail=False):
        self.blockers = list(blockers)
        self.fail = fail

    def generate_structured(self, system, user, output_model):
        if output_model is PathSelection:
            return output_model(requirements_met=False, foundation_id="a", foundation_reason="基础",
                application_id="b", application_reason="实践", perspective_id="c", perspective_reason="伦理",
                gaps="还需要深入神经生物学。")
        assert output_model is SelectionConstraintAudit
        if self.fail:
            raise RuntimeError("unavailable")
        return output_model(blocking_requirements=self.blockers, optional_suggestions="可进一步了解神经生物学。")


def pools():
    return {role: [{"id": key, "title": role, "description": role}] for role, key in
            zip(("Conceptual Foundation", "Technical/Application", "Critical/Cross-disciplinary"), "abc", strict=True)}


def test_optional_neuroscience_does_not_fail_general_foundation(goal):
    selection = review_selection(pools(), goal, UserProfile(education_level="undergraduate"), ConstraintReviewer())
    assert selection.requirements_met
    assert "可选拓展" in selection.gaps


def test_explicit_depth_requirement_remains_blocking(goal):
    goal.focus_details = "必须深入学习神经生物学机制"
    provider = ConstraintReviewer([{"source_field": "focus_details", "source_quote": "神经生物学机制",
                                   "reason": "书目信息尚不能支持你要求的神经生物学深度。"}])
    selection = review_selection(pools(), goal, UserProfile(education_level="undergraduate"), provider)
    assert not selection.requirements_met


@pytest.mark.parametrize("provider", [ConstraintReviewer(fail=True), ConstraintReviewer([
    {"source_field": "purpose", "source_quote": "用户没说过的话", "reason": "未经证实"}])])
def test_unavailable_or_invented_requirement_audit_does_not_approve(goal, provider):
    assert not review_selection(pools(), goal, UserProfile(education_level="undergraduate"), provider).requirements_met
