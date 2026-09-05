from __future__ import annotations

from src.llm.bedrock_provider import BedrockProvider
from src.models import ReadingSupportOutput

VALID_OUTPUT = {
    "grounding": "User-provided excerpt",
    "explanation": "The passage treats cognition as interaction.",
    "connection": "This supports the target concept of enactivism.",
    "guiding_question": "Which sentence supplies the strongest evidence?",
    "recall_question": "Explain enactivism without looking back.",
    "reflection_task": "Write one supported claim and one uncertainty.",
    "mastery_update_suggestion": 0.05,
    "limitations": ["Only the supplied excerpt was used."],
}


class StubClient:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = responses
        self.calls: list[dict] = []

    def converse(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return self.responses.pop(0)


def tool_response(tool_input: dict) -> dict:
    return {
        "usage": {"inputTokens": 125, "outputTokens": 48},
        "output": {
            "message": {
                "content": [
                    {
                        "toolUse": {
                            "name": "submit_structured_output",
                            "toolUseId": "test-id",
                            "input": tool_input,
                        }
                    }
                ]
            }
        }
    }


def provider_with(client: StubClient) -> BedrockProvider:
    provider = BedrockProvider.__new__(BedrockProvider)
    provider.model_id = "amazon.nova-lite-v1:0"
    provider.client = client
    return provider


def test_bedrock_uses_forced_tool_output_instead_of_prompting_with_schema() -> None:
    client = StubClient([tool_response(VALID_OUTPUT)])

    result = provider_with(client).generate_structured(
        "Use only supplied evidence.", "session input", ReadingSupportOutput
    )

    assert result.grounding == "User-provided excerpt"
    call = client.calls[0]
    assert call["toolConfig"]["toolChoice"] == {
        "tool": {"name": "submit_structured_output"}
    }
    assert "Return JSON matching this schema" not in call["messages"][0]["content"][0]["text"]
    assert call["inferenceConfig"]["temperature"] == 0
    assert provider_with(StubClient([])).usage_summary() == {
        "calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_write_input_tokens": 0,
        "structured_requests": 0,
        "structured_first_attempt_successes": 0,
        "structured_validation_retries": 0,
        "schema_validation_first_attempt_rate": 0.0,
    }


def test_bedrock_collects_non_sensitive_usage_metrics() -> None:
    client = StubClient([tool_response(VALID_OUTPUT)])
    provider = provider_with(client)

    provider.generate_structured(
        "Use only supplied evidence.", "session input", ReadingSupportOutput
    )

    assert provider.usage_summary() == {
        "calls": 1,
        "input_tokens": 125,
        "output_tokens": 48,
        "cache_read_input_tokens": 0,
        "cache_write_input_tokens": 0,
        "structured_requests": 1,
        "structured_first_attempt_successes": 1,
        "structured_validation_retries": 0,
        "schema_validation_first_attempt_rate": 1.0,
    }


def test_bedrock_retries_once_after_invalid_tool_input() -> None:
    client = StubClient([tool_response({"properties": {}}), tool_response(VALID_OUTPUT)])
    provider = provider_with(client)

    result = provider.generate_structured(
        "Use only supplied evidence.", "session input", ReadingSupportOutput
    )

    assert result.explanation.startswith("The passage")
    assert len(client.calls) == 2
    retry_prompt = client.calls[1]["messages"][0]["content"][0]["text"]
    assert "previous tool input was invalid" in retry_prompt
    assert provider.usage_summary()["schema_validation_first_attempt_rate"] == 0.0
    assert provider.usage_summary()["structured_validation_retries"] == 1
