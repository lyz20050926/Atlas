from __future__ import annotations

import sys
import time

import boto3
from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError, ProfileNotFound

from src.config import get_settings


def _candidate_models(bedrock) -> list[tuple[str, str, str]]:
    candidates: list[tuple[str, str, str]] = []
    response = bedrock.list_foundation_models()
    for model in response.get("modelSummaries", []):
        name = model.get("modelName", "")
        model_id = model.get("modelId", "")
        lowered = f"{name} {model_id}".lower()
        if any(token in lowered for token in ("haiku", "nova micro", "nova lite")):
            inference = ",".join(model.get("inferenceTypesSupported", []))
            candidates.append((name, model_id, inference or "Not available"))
    try:
        paginator = bedrock.get_paginator("list_inference_profiles")
        for page in paginator.paginate():
            for profile in page.get("inferenceProfileSummaries", []):
                name = profile.get("inferenceProfileName", "")
                profile_id = profile.get("inferenceProfileId", "")
                lowered = f"{name} {profile_id}".lower()
                if any(token in lowered for token in ("haiku", "nova micro", "nova lite")):
                    candidates.append((name, profile_id, "INFERENCE_PROFILE"))
    except (BotoCoreError, ClientError):
        pass
    return list(dict.fromkeys(candidates))


def main() -> int:
    settings = get_settings()
    region = settings.aws_region or "us-east-1"
    try:
        session = boto3.Session(
            profile_name=settings.aws_profile or None,
            region_name=region,
        )
        identity = session.client("sts", region_name=region).get_caller_identity()
        print("AWS identity: OK")
        print(f"account={identity.get('Account')}")
        print(f"arn={identity.get('Arn')}")
        print(f"region={region}")
        bedrock = session.client("bedrock", region_name=region)
        candidates = _candidate_models(bedrock)
        print("\nLow-cost Bedrock candidates visible to this account:")
        for name, model_id, inference in candidates:
            print(f"- {name}\n  id={model_id}\n  inference={inference}")
        if not settings.bedrock_model_id:
            print("\nBEDROCK_MODEL_ID is empty. Choose an allowed ID above, add it to .env, then rerun.")
            return 2
        runtime = session.client("bedrock-runtime", region_name=region)
        started = time.perf_counter()
        response = runtime.converse(
            modelId=settings.bedrock_model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": "Reply with exactly: ready"}],
                }
            ],
            inferenceConfig={"temperature": 0, "maxTokens": 16},
        )
        elapsed = time.perf_counter() - started
        text = response["output"]["message"]["content"][0]["text"].strip()
        usage = response.get("usage", {})
        print("\nBedrock Converse: OK")
        print(f"model={settings.bedrock_model_id}")
        print(f"response={text!r}")
        print(f"latency_seconds={elapsed:.3f}")
        print(
            "tokens="
            f"input:{usage.get('inputTokens', 'Not available')} "
            f"output:{usage.get('outputTokens', 'Not available')} "
            f"total:{usage.get('totalTokens', 'Not available')}"
        )
        return 0
    except NoCredentialsError:
        print("AWS credentials are missing. Paste the three temporary export lines from Access keys.")
    except ProfileNotFound as exc:
        print(f"AWS profile not found: {exc}")
    except ClientError as exc:
        error = exc.response.get("Error", {})
        print(f"AWS error: {error.get('Code', 'ClientError')} — {error.get('Message', str(exc))}")
    except BotoCoreError as exc:
        print(f"AWS SDK error: {exc}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

