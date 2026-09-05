from __future__ import annotations

from src.services.recommendation import RetrievalTelemetry


def test_retrieval_telemetry_reports_usable_operation_rate() -> None:
    telemetry = RetrievalTelemetry(
        planned_operations=6,
        cache_hits=2,
        network_calls=4,
        usable_results=5,
        empty_results=0,
        failed_operations=1,
    )

    assert telemetry.success_rate == 0.8333
    assert telemetry.as_dict() == {
        "planned_operations": 6,
        "cache_hits": 2,
        "network_calls": 4,
        "usable_results": 5,
        "empty_results": 0,
        "failed_operations": 1,
        "tool_call_success_rate": 0.8333,
    }
