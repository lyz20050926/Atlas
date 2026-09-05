from __future__ import annotations

import json

import boto3
from botocore.config import Config
from pydantic import ValidationError

from src.llm.base import LLMProvider, T


class BedrockProvider(LLMProvider):
    def __init__(
        self,
        model_id: str,
        region: str = "us-east-1",
        profile_name: str = "",
        connect_timeout_seconds: float = 5.0,
        read_timeout_seconds: float = 65.0,
        max_attempts: int = 2,
    ) -> None:
        if not model_id:
            raise ValueError("BEDROCK_MODEL_ID is required when LLM_PROVIDER=bedrock")
        self.model_id = model_id
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_read_input_tokens = 0
        self.cache_write_input_tokens = 0
        self.structured_requests = 0
        self.structured_first_attempt_successes = 0
        self.structured_validation_retries = 0
        session = boto3.Session(profile_name=profile_name or None, region_name=region)
        self.client = session.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(
                connect_timeout=connect_timeout_seconds,
                read_timeout=read_timeout_seconds,
                retries={"max_attempts": max_attempts, "mode": "standard"},
            ),
        )

    def generate_structured(self, system: str, user: str, output_model: type[T]) -> T:
        self.structured_requests = getattr(self, "structured_requests", 0) + 1
        tool_name = "submit_structured_output"
        schema = _nova_compatible_tool_schema(output_model.model_json_schema())
        tool_config = {
            "tools": [
                {
                    "toolSpec": {
                        "name": tool_name,
                        "description": "Submit the final validated response. Supply native arrays and objects as required by the schema, NEVER JSON-encoded strings.",
                        "inputSchema": {"json": schema},
                    }
                }
            ],
            "toolChoice": {"tool": {"name": tool_name}},
        }
        correction = ""
        last_error = "the model did not call the required output tool"
        for attempt in range(2):
            prompt = user
            if correction:
                prompt += (
                    "\nYour previous tool input was invalid. Correct every listed issue and call "
                    f"{tool_name} again. Validation issues: {correction}"
                )
            response = self.client.converse(
                modelId=self.model_id,
                system=[{"text": system}],
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                toolConfig=tool_config,
                inferenceConfig={"temperature": 0, "maxTokens": 3200 if output_model.__name__ in {
                    "DiagnosticDraft", "QuestionSet", "ReviewSet", "EditedReviewSet", "MentorResponse", "EditedMentorResponse", "ReadingSupportOutput", "ReadingSupportDraft", "PathSelection"
                } else 1800},
            )
            self.calls = getattr(self, "calls", 0) + 1
            usage = response.get("usage") or {}
            self.input_tokens = getattr(self, "input_tokens", 0) + int(
                usage.get("inputTokens") or 0
            )
            self.output_tokens = getattr(self, "output_tokens", 0) + int(
                usage.get("outputTokens") or 0
            )
            self.cache_read_input_tokens = getattr(self, "cache_read_input_tokens", 0) + int(
                usage.get("cacheReadInputTokens") or 0
            )
            self.cache_write_input_tokens = getattr(self, "cache_write_input_tokens", 0) + int(
                usage.get("cacheWriteInputTokens") or 0
            )
            tool_input = _find_tool_input(response, tool_name)
            if tool_input is None:
                if attempt == 0:
                    self.structured_validation_retries = getattr(
                        self, "structured_validation_retries", 0
                    ) + 1
                correction = last_error
                continue
            try:
                validated = output_model.model_validate(_decode_json_containers(tool_input, schema))
                if attempt == 0:
                    self.structured_first_attempt_successes = getattr(
                        self, "structured_first_attempt_successes", 0
                    ) + 1
                return validated
            except ValidationError as exc:
                last_error = str(exc)
                correction = last_error[:2000]
                if attempt == 0:
                    self.structured_validation_retries = getattr(
                        self, "structured_validation_retries", 0
                    ) + 1
                if attempt == 1:
                    break
        raise ValueError(f"Bedrock could not produce valid structured output after 2 attempts: {last_error}")

    def usage_summary(self) -> dict[str, int | float]:
        """Return provider telemetry without exposing prompts or credentials."""
        structured_requests = getattr(self, "structured_requests", 0)
        first_attempt_successes = getattr(self, "structured_first_attempt_successes", 0)
        first_attempt_rate = (
            round(first_attempt_successes / structured_requests, 4)
            if structured_requests
            else 0.0
        )
        return {
            "calls": getattr(self, "calls", 0),
            "input_tokens": getattr(self, "input_tokens", 0),
            "output_tokens": getattr(self, "output_tokens", 0),
            "cache_read_input_tokens": getattr(self, "cache_read_input_tokens", 0),
            "cache_write_input_tokens": getattr(self, "cache_write_input_tokens", 0),
            "structured_requests": structured_requests,
            "structured_first_attempt_successes": first_attempt_successes,
            "structured_validation_retries": getattr(
                self, "structured_validation_retries", 0
            ),
            "schema_validation_first_attempt_rate": first_attempt_rate,
        }


def _find_tool_input(response: dict, tool_name: str) -> dict | None:
    content = response.get("output", {}).get("message", {}).get("content", [])
    for block in content:
        tool_use = block.get("toolUse")
        if tool_use and tool_use.get("name") == tool_name and isinstance(tool_use.get("input"), dict):
            return tool_use["input"]
    return None


def _decode_json_containers(value, schema: dict):
    """Accept JSON-encoded containers only where the tool schema requires them.

    Some Bedrock models stringify nested arrays. Parse JSON, never eval or
    invent missing fields; Pydantic remains the final validator.
    """
    expected = schema.get("type")
    if expected in {"array", "object"} and isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return value
    if expected == "object" and isinstance(value, dict):
        properties = schema.get("properties", {})
        return {key: _decode_json_containers(item, properties.get(key, {})) for key, item in value.items()}
    if expected == "array" and isinstance(value, list):
        return [_decode_json_containers(item, schema.get("items", {})) for item in value]
    return value


def _nova_compatible_tool_schema(schema: dict, definitions: dict | None = None) -> dict:
    """Remove validation keywords unsupported by Nova v1 tool input schemas."""
    definitions = schema.get("$defs", {}) if definitions is None else definitions
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        if name not in definitions:
            raise ValueError(f"Unresolved tool schema reference: {name}")
        return _nova_compatible_tool_schema(definitions[name], definitions)
    schema_type = schema.get("type")
    cleaned: dict = {"type": schema_type} if schema_type else {}
    if "description" in schema:
        cleaned["description"] = schema["description"]
    if "enum" in schema:
        cleaned["enum"] = schema["enum"]
    if schema_type == "object":
        cleaned["properties"] = {
            name: _nova_compatible_tool_schema(value, definitions)
            for name, value in schema.get("properties", {}).items()
        }
        if schema.get("required"):
            cleaned["required"] = schema["required"]
    elif schema_type == "array":
        cleaned["items"] = _nova_compatible_tool_schema(schema.get("items", {}), definitions)
    return cleaned
