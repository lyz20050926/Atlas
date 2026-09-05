from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.models import LearningGoal


def test_learning_goal_computes_budget() -> None:
    goal = LearningGoal(
        topic="Embodied Intelligence",
        purpose="Learn",
        duration_weeks=6,
        hours_per_week=4,
        required_perspectives=["Robotics"],
        preferred_difficulty="intermediate",
        desired_balance="balanced",
    )
    assert goal.total_hours == 24


def test_learning_goal_rejects_zero_time() -> None:
    with pytest.raises(ValidationError):
        LearningGoal(
            topic="Embodied Intelligence",
            purpose="Learn",
            duration_weeks=6,
            hours_per_week=0,
            required_perspectives=[],
            preferred_difficulty="intermediate",
            desired_balance="balanced",
        )

