from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from src.config import get_settings
from src.llm.factory import create_llm_provider


class ConnectionCheck(BaseModel):
    status: Literal["ready"]


def main() -> None:
    settings = get_settings()
    provider = create_llm_provider(settings)
    if provider is None:
        raise RuntimeError("LLM_PROVIDER is not configured for Amazon Bedrock")
    result = provider.generate_structured(
        system="Return the required structured output exactly.",
        user="Set status to ready.",
        output_model=ConnectionCheck,
    )
    if result.status != "ready":
        raise RuntimeError("Amazon Bedrock returned an unexpected status")
    print(f"BEDROCK_OK model={settings.bedrock_model_id}")


if __name__ == "__main__":
    main()
