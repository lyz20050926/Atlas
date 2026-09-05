from __future__ import annotations

from src.llm.base import LLMProvider, T


class MockProvider(LLMProvider):
    """Explicit test/UI provider. It never pretends to be a live model."""

    def generate_structured(self, system: str, user: str, output_model: type[T]) -> T:
        raise RuntimeError(
            "MockProvider has no generic fabricated response. Supply deterministic fixtures in tests."
        )

