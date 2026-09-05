from __future__ import annotations

import json
import time
from datetime import UTC, datetime

from src.config import PROJECT_ROOT, Settings
from src.graph import run_recommendation_graph
from src.models import BookCandidate, LearningGoal, UserProfile
from src.replanning import replan_path
from src.services.recommendation import load_demo_candidates


def fixture_search(goal, settings):
    topic = goal.topic.casefold()
    if "embodied" in topic or "具身" in topic:
        return load_demo_candidates(), []
    payload = json.loads(
        (PROJECT_ROOT / "data" / "fixtures" / "evaluation_books.json").read_text(
            encoding="utf-8"
        )
    )
    books = [BookCandidate.model_validate(item) for item in payload["books"]]
    if "ethic" in topic or "伦理" in topic:
        selected_ids = {"9780262534635", "9780195374049", "9780190652951"}
    else:
        selected_ids = {"9780262201629", "9780262195027", "9780262526005"}
    return [book for book in books if book.canonical_id in selected_ids], []


def rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def release_gate_passes(cases: list[dict]) -> bool:
    """A completed command is not enough: every fixed case must pass its checks."""
    return bool(cases) and all(
        all(case.get(key) is True for key in (
            "hard_constraints", "replan", "loop_terminated", "task_completed_end_to_end",
        ))
        for case in cases
    )


def main() -> None:
    cases = json.loads((PROJECT_ROOT / "data" / "evaluation_cases.json").read_text(encoding="utf-8"))
    totals = {
        "books": 0,
        "verified_books": 0,
        "source_attributed_books": 0,
        "hard_constraints_passed": 0,
        "structured_outputs_passed": 0,
        "replans_passed": 0,
        "loops_terminated": 0,
        "loop_cap_hits": 0,
        "search_iterations": 0,
        "search_tool_operations": 0,
        "search_tool_successes": 0,
        "tasks_completed": 0,
        "semantically_relevant_books": 0,
        "fit_score_sum": 0.0,
    }
    case_results = []
    started = time.perf_counter()
    for case in cases:
        profile = UserProfile(
            user_id=case["id"],
            education_level="undergraduate",
            major=case["major"],
            background_knowledge=case["background"],
            interests=case["perspectives"],
        )
        goal = LearningGoal(
            topic=case["topic"],
            purpose="Develop an interdisciplinary foundation",
            duration_weeks=case["weeks"],
            hours_per_week=case["hours"],
            required_perspectives=case["perspectives"],
            preferred_difficulty="intermediate",
            desired_balance="theory and application",
        )
        result = run_recommendation_graph(
            profile,
            goal,
            Settings(_env_file=None, app_mode="evaluation", llm_provider="mock", max_search_iterations=3),
            search_function=fixture_search,
        )
        revised, revision = replan_path(
            result.reading_path,
            goal,
            max(0.5, goal.hours_per_week / 2),
            True,
            "enactivism",
        )
        books = result.selected_books
        verified = sum(
            bool(book.source_records) and bool(book.isbn_10 or book.isbn_13) for book in books
        )
        attributed = sum(
            all(record.source_name and record.source_url for record in book.source_records) for book in books
        )
        hard_pass = result.reading_path.constraints_satisfied and len(result.reading_path.stages) == 3
        replan_pass = (
            revised.constraints_satisfied
            and revised.total_estimated_hours <= goal.duration_weeks * max(0.5, goal.hours_per_week / 2)
            and set(revision.preserved_goals) == set(goal.required_perspectives)
        )
        search_iterations = sum(
            step.startswith("Search pass") or step.startswith("检索 ·")
            for step in result.execution_trace
        )
        loop_pass = search_iterations <= 3
        task_complete = (
            hard_pass
            and len(books) == 3
            and verified == len(books)
            and all(
                assessment.goal_relevance >= 0.3
                for assessment in result.assessments
            )
        )
        totals["books"] += len(books)
        totals["verified_books"] += verified
        totals["source_attributed_books"] += attributed
        totals["hard_constraints_passed"] += int(hard_pass)
        totals["structured_outputs_passed"] += 1
        totals["replans_passed"] += int(replan_pass)
        totals["loops_terminated"] += int(loop_pass)
        totals["loop_cap_hits"] += int(search_iterations >= 3)
        totals["search_iterations"] += search_iterations
        totals["search_tool_operations"] += 1
        totals["search_tool_successes"] += int(bool(books))
        totals["tasks_completed"] += int(task_complete)
        totals["semantically_relevant_books"] += sum(
            assessment.goal_relevance >= 0.3 for assessment in result.assessments
        )
        totals["fit_score_sum"] += sum(
            assessment.overall_rank_score for assessment in result.assessments
        )
        case_results.append(
            {
                "id": case["id"],
                "books": [book.title for book in books],
                "roles": [assessment.evaluated_role for assessment in result.assessments],
                "fit_scores": [assessment.overall_rank_score for assessment in result.assessments],
                "hard_constraints": hard_pass,
                "replan": replan_pass,
                "loop_terminated": loop_pass,
                "search_iterations": search_iterations,
                "task_completed_end_to_end": task_complete,
            }
        )
    elapsed = time.perf_counter() - started
    count = len(cases)
    output = {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "cached Open Library snapshot; deterministic pipeline; no live API or LLM calls",
        "case_count": count,
        "metrics": {
            "book_identity_verification_rate": rate(totals["verified_books"], totals["books"]),
            "hard_constraint_satisfaction_rate": rate(totals["hard_constraints_passed"], count),
            "structured_output_pass_rate": rate(totals["structured_outputs_passed"], count),
            "replanning_success_rate": rate(totals["replans_passed"], count),
            "source_attribution_correctness_proxy": rate(
                totals["source_attributed_books"], totals["books"]
            ),
            "loop_termination_within_cap": rate(totals["loops_terminated"], count),
            "semantic_relevance_gate_pass_rate": rate(
                totals["semantically_relevant_books"], totals["books"]
            ),
            "average_transparent_fit_score": round(
                totals["fit_score_sum"] / max(1, totals["books"]), 4
            ),
            "average_latency_seconds": round(elapsed / count, 4),
            "model_calls_per_task": 0,
            "estimated_model_cost_usd_per_task": 0.0,
        },
        "topic4_digital_agent_metrics": {
            "schema_validation_first_attempt_rate": rate(
                totals["structured_outputs_passed"], count
            ),
            "tool_call_success_rate": rate(
                totals["search_tool_successes"], totals["search_tool_operations"]
            ),
            "task_completion_rate": rate(totals["tasks_completed"], count),
            "token_cost_per_run": {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_input_tokens": 0,
                "cache_write_input_tokens": 0,
                "estimated_usd": 0.0,
                "scope": "deterministic run; no model calls",
            },
            "loop_discipline": {
                "average_search_iterations": round(
                    totals["search_iterations"] / max(1, count), 4
                ),
                "iteration_cap": 3,
                "cap_hit_rate": rate(totals["loop_cap_hits"], count),
            },
            "answer_fidelity_proxy": rate(
                totals["semantically_relevant_books"], totals["books"]
            ),
        },
        "limitations": [
            "This run validates deterministic orchestration against fixed Google Books and Open Library snapshots covering three distinct learning topics.",
            "It does not measure live API availability, semantic recommendation quality or Bedrock cost.",
            "The semantic relevance metric is a transparent rule-based gate, not a substitute for blind human review.",
            "The deterministic schema and tool-call rates measure typed local output and a fixture-backed search adapter, not Bedrock first-attempt validity or live catalogue availability.",
            "Use a separate live run and human review to substantiate model-quality claims; these are not measured by this deterministic check.",
        ],
        "cases": case_results,
        "release_gate_passed": release_gate_passes(case_results),
    }
    target = PROJECT_ROOT / "evaluation_results" / "latest.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(output["metrics"], indent=2))
    print(f"saved={target}")
    raise SystemExit(0 if output["release_gate_passed"] else 1)


if __name__ == "__main__":
    main()
