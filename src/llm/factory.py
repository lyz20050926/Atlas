from __future__ import annotations

from src.config import Settings, get_settings
from src.llm.base import LLMProvider
from src.llm.bedrock_provider import BedrockProvider


def create_learning_provider(settings: Settings | None = None) -> LLMProvider | None:
    """Optional dedicated teaching model; catalog/recommendation routing is unchanged."""
    resolved = settings or get_settings()
    if resolved.bedrock_learning_model_id:
        resolved = resolved.model_copy(update={"bedrock_model_id": resolved.bedrock_learning_model_id})
    return create_llm_provider(resolved)


def create_llm_provider(settings: Settings | None = None) -> LLMProvider | None:
    """Build the configured provider; ``None`` selects deterministic mock behavior."""
    resolved = settings or get_settings()
    if resolved.demo_mode:
        return None
    provider_name = resolved.llm_provider.strip().lower()
    if provider_name == "mock":
        return None
    if provider_name == "bedrock":
        return BedrockProvider(
            model_id=resolved.bedrock_model_id,
            region=resolved.aws_region,
            profile_name=resolved.aws_profile,
            connect_timeout_seconds=resolved.bedrock_connect_timeout_seconds,
            read_timeout_seconds=resolved.bedrock_read_timeout_seconds,
            max_attempts=resolved.bedrock_max_attempts,
        )
    raise ValueError(f"Unsupported LLM_PROVIDER: {resolved.llm_provider!r}")
