from __future__ import annotations

import argparse
import json
import time
from datetime import UTC, datetime

from src.config import PROJECT_ROOT, Settings
from src.graph import run_recommendation_graph
from src.llm.bedrock_provider import BedrockProvider
from src.llm.factory import create_llm_provider
from src.models import LearningGoal, UserProfile
from src.services.recommendation import search_live_candidates_with_telemetry

CASES = (
    {
        "id": "live-en-embodied",
        "language": "en",
        "topic": "Embodied Intelligence",
        "purpose": "Build a trustworthy interdisciplinary foundation",
        "major": "Electrical and Electronic Engineering",
        "background": ["Python", "Machine Learning", "Control theory"],
        "perspectives": ["Robotics", "Cognitive Science", "Ethics"],
    },
    {
        "id": "live-zh-embodied",
        "language": "zh",
        "topic": "具身智能",
        "purpose": "建立可信的跨学科知识基础",
        "major": "电子与电气工程",
        "background": ["Python", "机器学习", "控制理论"],
        "perspectives": ["机器人学", "认知科学", "伦理学"],
    },
)


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a small, billable live-source and Bedrock acceptance test."
    )
    parser.add_argument(
        "--confirm-live-cost",
        action="store_true",
        help="Required acknowledgement that Bedrock calls may incur a small AWS charge.",
    )
    args = parser.parse_args()
    if not args.confirm_live_cost:
        raise SystemExit(
            "Refusing live model calls without --confirm-live-cost. "
            "Use scripts/run_evaluation.py for the free deterministic suite."
        )

    settings = Settings()
    provider = create_llm_provider(settings)
    if not isinstance(provider, BedrockProvider):
        raise SystemExit("Set LLM_PROVIDER=bedrock and BEDROCK_MODEL_ID before this live run.")

    results = []
    run_started = time.perf_counter()
    for case in CASES:
        language = case["language"]
        profile = UserProfile(
            user_id=case["id"],
            education_level="undergraduate",
            major=case["major"],
            background_knowledge=case["background"],
            interests=case["perspectives"],
            interface_language=language,
            language_preferences=["Chinese" if language == "zh" else "English"],
        )
        goal = LearningGoal(
            topic=case["topic"],
            purpose=case["purpose"],
            duration_weeks=6,
            hours_per_week=4,
            required_perspectives=case["perspectives"],
            preferred_difficulty="intermediate",
            desired_balance="theory and application",
            interface_language=language,
            book_language_preferences=[language],
        )
        retrieval_telemetry: dict[str, int | float] = {}

        def measured_search(
            search_goal,
            search_settings,
            telemetry_target=retrieval_telemetry,
        ):
            books, warnings, telemetry = search_live_candidates_with_telemetry(
                search_goal, search_settings
            )
            telemetry_target.update(telemetry.as_dict())
            return books, warnings

        started = time.perf_counter()
        result = run_recommendation_graph(
            profile,
            goal,
            settings,
            allow_cached_fallback=True,
            search_function=measured_search,
            provider=provider,
        )
        search_iterations = sum(
            step.startswith("Search pass") or step.startswith("检索 ·")
            for step in result.execution_trace
        )
        task_completed = (
            result.reading_path.constraints_satisfied
            and len(result.reading_path.stages) == 3
            and len(result.selected_books) == 3
            and all(
                assessment.goal_relevance >= 0.3
                for assessment in result.assessments
            )
        )
        results.append(
            {
                "id": case["id"],
                "language": language,
                "latency_seconds": round(time.perf_counter() - started, 3),
                "data_mode": result.data_mode,
                "constraints_satisfied": result.reading_path.constraints_satisfied,
                "task_completed_end_to_end": task_completed,
                "search_iterations": search_iterations,
                "retrieval_telemetry": retrieval_telemetry,
                "books": [
                    {
                        "title": book.title,
                        "role": assessment.evaluated_role,
                        "goal_relevance": assessment.goal_relevance,
                        "fit_score": assessment.overall_rank_score,
                        "verified_sources": sorted(
                            {record.source_name for record in book.source_records}
                        ),
                    }
                    for book, assessment in zip(
                        result.selected_books, result.assessments, strict=True
                    )
                ],
                "warnings": result.warnings,
            }
        )

    usage = provider.usage_summary()
    case_count = len(results)
    planned_tool_operations = sum(
        int(item["retrieval_telemetry"].get("planned_operations", 0))
        for item in results
    )
    usable_tool_results = sum(
        int(item["retrieval_telemetry"].get("usable_results", 0))
        for item in results
    )
    selected_book_count = sum(len(item["books"]) for item in results)
    relevant_book_count = sum(
        book["goal_relevance"] >= 0.3
        for item in results
        for book in item["books"]
    )
    total_metered_tokens = sum(
        int(usage.get(key, 0))
        for key in (
            "input_tokens",
            "output_tokens",
            "cache_read_input_tokens",
            "cache_write_input_tokens",
        )
    )
    output = {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "billable source-tool and Amazon Bedrock smoke test; catalogue operations may use the labelled 24-hour cache",
        "model_id": settings.bedrock_model_id,
        "case_count": case_count,
        "elapsed_seconds": round(time.perf_counter() - run_started, 3),
        "bedrock_usage": usage,
        "all_constraints_satisfied": all(
            item["constraints_satisfied"] for item in results
        ),
        "all_selected_books_pass_relevance_gate": all(
            book["goal_relevance"] >= 0.3
            for item in results
            for book in item["books"]
        ),
        "topic4_digital_agent_metrics": {
            "schema_validation_first_attempt_rate": usage[
                "schema_validation_first_attempt_rate"
            ],
            "tool_call_success_rate": rate(
                usable_tool_results, planned_tool_operations
            ),
            "task_completion_rate": rate(
                sum(item["task_completed_end_to_end"] for item in results),
                case_count,
            ),
            "token_cost_per_run": {
                "average_metered_tokens": round(
                    total_metered_tokens / max(1, case_count), 2
                ),
                "estimated_usd": None,
                "note": "Apply the current account/model pricing or AWS billing export; no stale price is hard-coded.",
            },
            "loop_discipline": {
                "average_search_iterations": round(
                    sum(item["search_iterations"] for item in results)
                    / max(1, case_count),
                    4,
                ),
                "iteration_cap": settings.max_search_iterations,
                "cap_hit_rate": rate(
                    sum(
                        item["search_iterations"] >= settings.max_search_iterations
                        for item in results
                    ),
                    case_count,
                ),
            },
            "answer_fidelity_proxy": rate(
                relevant_book_count, selected_book_count
            ),
            "answer_fidelity_human_review_status": "pending",
        },
        "cases": results,
        "limitations": [
            "This is a two-case integration smoke test, not a statistically powered quality study.",
            "Token usage is reported directly from Bedrock; cost is not estimated because prices can change.",
            "Tool-call success counts planned catalogue operations that returned at least one usable record; cache hits and network calls are reported separately.",
            "Blind human ratings are still needed for a defensible semantic-quality claim.",
        ],
    }
    target = PROJECT_ROOT / "evaluation_results" / "live_latest.json"
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: output[key] for key in (
        "model_id",
        "case_count",
        "elapsed_seconds",
        "bedrock_usage",
        "all_constraints_satisfied",
        "all_selected_books_pass_relevance_gate",
    )}, indent=2, ensure_ascii=False))
    print(f"saved={target}")


if __name__ == "__main__":
    main()
