from __future__ import annotations

import pytest

from src.config import Settings
from src.llm import factory


def test_factory_returns_none_for_mock_mode() -> None:
    assert factory.create_llm_provider(Settings(llm_provider="mock")) is None


def test_factory_builds_bedrock_from_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str | float | int] = {}

    class StubProvider:
        def __init__(
            self,
            model_id: str,
            region: str,
            profile_name: str,
            connect_timeout_seconds: float,
            read_timeout_seconds: float,
            max_attempts: int,
        ) -> None:
            captured.update(
                model_id=model_id,
                region=region,
                profile_name=profile_name,
                connect_timeout_seconds=connect_timeout_seconds,
                read_timeout_seconds=read_timeout_seconds,
                max_attempts=max_attempts,
            )

    monkeypatch.setattr(factory, "BedrockProvider", StubProvider)
    provider = factory.create_llm_provider(
        Settings(
            llm_provider="bedrock",
            bedrock_model_id="amazon.nova-lite-v1:0",
            aws_region="us-east-1",
            aws_profile="hackathon",
        )
    )

    assert isinstance(provider, StubProvider)
    assert captured == {
        "model_id": "amazon.nova-lite-v1:0",
        "region": "us-east-1",
        "profile_name": "hackathon",
        "connect_timeout_seconds": 5.0,
        "read_timeout_seconds": 65.0,
        "max_attempts": 2,
    }


def test_factory_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unsupported LLM_PROVIDER"):
        factory.create_llm_provider(Settings(llm_provider="other"))
