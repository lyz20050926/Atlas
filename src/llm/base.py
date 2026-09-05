from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    @abstractmethod
    def generate_structured(self, system: str, user: str, output_model: type[T]) -> T:
        """Return validated structured output or raise an actionable error."""

