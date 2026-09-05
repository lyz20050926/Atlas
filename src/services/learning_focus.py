"""Small offline retrieval hints; the original brief remains the source of truth.

These are conservative lexical hints, not a semantic interpretation of arbitrary
requirements. The model receives the complete focus_details for selection and
teaching; catalogue APIs receive only short positive phrases, never full prose.
"""
from __future__ import annotations

import re

from src.models import LearningGoal

_NEGATIVE_CLAUSE = re.compile(
    r"不要|不需要|不推荐|不想(?:读|学习|学|研究)|不使用|不涉及|不包含|排除|不感兴趣|"
    r"\b(?:no|not|exclude|excluding|avoid|do not|don't|without)\b",
    re.I,
)
_FORMAT_OR_SCHEDULE = re.compile(
    r"(?:中文|英文|双语).*(?:优先|书|资料)|只读|每周|每天|小时|分钟|预算|"
    r"\b(?:hours?|minutes?|weeks?|budget|bilingual)\b|\b(?:in|prefer)\s+(?:Chinese|English)\b",
    re.I,
)
_ENGLISH_FILLERS = {
    "i", "want", "would", "like", "to", "learn", "study", "explore", "understand",
    "go", "deeper", "deeply", "depth", "in", "into", "the", "a", "an", "about", "on",
    "especially", "specifically", "focus", "focusing", "interested", "please", "books",
    "book", "textbooks", "textbook", "prefer", "need", "and", "with", "some",
}


def focus_search_phrases(goal: LearningGoal) -> list[str]:
    """Extract at most three short positive hints without searching exclusions."""
    phrases: list[str] = []
    for sentence in re.split(r"[。.!?！？;；\n]", goal.focus_details):
        for clause in re.split(r"[,，:：]|\b(?:especially|specifically)\b", sentence, flags=re.I):
            if _NEGATIVE_CLAUSE.search(clause) or _FORMAT_OR_SCHEDULE.search(clause):
                continue
            # After a subject has been named, prose about what kind of books to
            # read is a selection preference, not another catalogue subject.
            if phrases and re.search(r"\b(?:books?|textbooks?|reading material)\b", clause, re.I):
                continue
            clause = re.sub(
                r"^(?:我|希望|想要|想|重点|特别|主要|深入|进一步|系统|了解|理解|学习|研究|关注|是|能|能够|在|的)+",
                "", clause.strip(),
            )
            for part in re.split(r"[、]|和|与|以及", clause):
                part = part.strip()
                if re.search(r"[\u4e00-\u9fff]", part):
                    # Long explanations, scheduling and format preferences are
                    # kept for the semantic gate, not sent as subject keywords.
                    if not 2 <= len(part) <= 20 or re.search(r"每周|小时|分钟|每天|希望|书籍|的书|读物|时间|预算", part):
                        continue
                else:
                    words = [word for word in re.findall(r"[\w+#'-]+", part)
                             if word.casefold() not in _ENGLISH_FILLERS]
                    if not 1 <= len(words) <= 6:
                        continue
                    part = " ".join(words)
                if part and part.casefold() != goal.topic.strip().casefold() and part not in phrases:
                    phrases.append(part)
                if len(phrases) == 3:
                    return phrases
    return phrases


def focused_topic(goal: LearningGoal) -> str:
    """A compact catalogue topic while preserving the original display name."""
    parts = [goal.topic.strip(), *focus_search_phrases(goal)]
    result = parts[0]
    for part in parts[1:]:
        if part.casefold() in result.casefold():
            continue
        if result.casefold() in part.casefold():
            result = part
            continue
        if len(result) + len(part) + 1 > 110:
            break
        result += " " + part
    return result
