"""Small, accessible practice controls shared by the learning workspace."""
from __future__ import annotations

from html import escape

import streamlit as st

from src.models import ConceptMastery, DiagnosticQuestion


def same_question_set(previous: list[DiagnosticQuestion], generated: list[DiagnosticQuestion]) -> bool:
    """A new explanation or option order is not a new exercise."""
    def signature(question):
        def normalize(value: str) -> str:
            return " ".join(value.casefold().split())

        return (question.question_type, normalize(question.prompt),
                tuple(sorted(normalize(option) for option in question.options)),
                normalize(question.correct_answer))
    return bool(previous) and [signature(q) for q in previous] == [signature(q) for q in generated]


def question_inputs(questions: list[DiagnosticQuestion], *, key_prefix: str,
                    is_zh: bool, saved_answers: list[str] | None = None) -> list[str]:
    """Render unanswered objective questions without silently selecting an answer."""
    labels = ({"single_choice": "单项选择", "true_false": "判断题", "short_answer": "简短作答"}
              if is_zh else {"single_choice": "Single choice", "true_false": "True or false",
                             "short_answer": "Short answer"})
    saved_answers = saved_answers or []
    answers = []
    for index, question in enumerate(questions):
        if index:
            st.divider()
        st.markdown(
            f'<div class="atlas-question-meta"><span>{index + 1:02d}</span>'
            f'<strong>{labels[question.question_type]}</strong>'
            f'<span>{escape(question.concept)}</span></div>', unsafe_allow_html=True,
        )
        previous = saved_answers[index] if index < len(saved_answers) else ""
        key = f"{key_prefix}_{index}"
        if question.question_type == "short_answer":
            answer = st.text_area(question.prompt, value=previous, key=key,
                                  placeholder="说说你的判断和理由，不必写很长。" if is_zh
                                  else "Explain your reasoning in a few sentences.",
                                  max_chars=3000, height=110)
        else:
            answer = st.radio(question.prompt, question.options,
                              index=question.options.index(previous) if previous in question.options else None,
                              horizontal=question.question_type == "true_false", key=key)
        answers.append(answer or "")
    return answers


def merge_mastery(previous: list[ConceptMastery], assessed: list[ConceptMastery]) -> list[ConceptMastery]:
    """A partial submission must not discard previously assessed concepts."""
    merged = {item.concept: item for item in previous}
    merged.update({item.concept: item for item in assessed})
    return list(merged.values())


def saved_feedback(reviews: list[dict], *, is_zh: bool) -> None:
    labels = ({"sound": "理解到位", "partial": "还需补充", "misconception": "需要纠正",
               "insufficient": "暂不判断"} if is_zh else
              {"sound": "Well reasoned", "partial": "A little more to explain",
               "misconception": "An idea to revisit", "insufficient": "Not assessed"})
    for review in reviews:
        objective = review.get("assessment_method") == "objective"
        verdict = review.get("verdict", "insufficient")
        label = labels.get(verdict, labels["insufficient"])
        if objective and verdict != "insufficient":
            label = ("回答正确" if verdict == "sound" else "再核对一下") if is_zh else (
                "Correct" if verdict == "sound" else "Take another look")
        with st.container(border=True):
            st.markdown(f"**{review['question_number']} · {label}**")
            if review.get("answer_quote"):
                st.caption(("你的回答：" if is_zh else "Your answer: ") + review["answer_quote"])
            st.write(review.get("feedback", ""))
            if review.get("assessment_method") == "unavailable":
                st.caption("简答点评暂未完成。回答已保存，稍后可重新提交。" if is_zh else
                           "Short-answer review is unavailable. Your answer is saved; you can resubmit later.")
            elif review.get("model_answer") and review.get("assessment_method") != "not_answered":
                with st.expander(("答案与解析" if objective else "参考思路") if is_zh else
                                 ("Answer and explanation" if objective else "One way to reason about it")):
                    st.write(review["model_answer"])
                    if review.get("follow_up") and verdict != "insufficient":
                        st.write(("可以再想想：" if is_zh else "Think a little further: ") + review["follow_up"])
