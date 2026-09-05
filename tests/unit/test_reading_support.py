from __future__ import annotations

import pytest

from src.models import ReadingSessionInput
from src.reading_support import support_reading


def test_reading_support_declares_grounding_and_limitations() -> None:
    session = ReadingSessionInput(
        book_title="Embodied Cognition",
        chapter="Introduction",
        notes="I think cognition depends on interaction.",
        excerpt="The agent brings forth a meaningful world through recurrent sensorimotor interaction.",
        question="How does this relate to enactivism?",
        target_concept="enactivism",
    )
    output = support_reading(session)
    assert "User-provided" in output.grounding
    assert "enactivism" in output.recall_question
    assert any("full copyrighted book" in item for item in output.limitations)


@pytest.mark.parametrize("quote", ["fabricated source", ""])
def test_live_support_rejects_fabricated_evidence(quote):
    class Provider:
        def generate_structured(self, **kwargs):
            return kwargs["output_model"](grounding=quote, explanation="An explanation", connection="A connection",
                guiding_question="Why?", recall_question="What follows?", reflection_task="Explain it.",
                limitations_note="Only the supplied excerpt.")

    session = ReadingSessionInput(book_title="Test", excerpt="Actual supplied text.",
                                 question="What does it mean?", notes="", target_concept="Test")
    with pytest.raises(ValueError, match="faithfully"):
        support_reading(session, Provider())


def test_receiving_an_explanation_is_not_mastery_evidence():
    class Provider:
        def generate_structured(self, **kwargs):
            return kwargs["output_model"](grounding="Actual supplied text.", explanation="An explanation",
                connection="A connection", guiding_question="Why?", recall_question="What follows?",
                reflection_task="Explain it.", limitations_note="Only the supplied excerpt.")

    session = ReadingSessionInput(book_title="Test", excerpt="Actual supplied text.",
                                 question="What does it mean?", notes="", target_concept="Test")
    assert support_reading(session, Provider()).mastery_update_suggestion == 0
