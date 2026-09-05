from __future__ import annotations

import json

from src.config import PROJECT_ROOT, Settings
from src.graph import run_recommendation_graph
from src.models import LearningGoal, UserProfile


def main() -> None:
    profiles = json.loads((PROJECT_ROOT / "data" / "demo_profiles.json").read_text(encoding="utf-8"))
    demo = profiles[0]
    result = run_recommendation_graph(
        UserProfile.model_validate(demo["profile"]),
        LearningGoal.model_validate(demo["goal"]),
        Settings(_env_file=None, app_mode="demo", llm_provider="mock"),
        allow_cached_fallback=True,
    )
    print(f"data_mode={result.data_mode}")
    for stage, book, assessment in zip(
        result.reading_path.stages,
        result.selected_books,
        result.assessments,
        strict=True,
    ):
        sources = ", ".join(record.source_name for record in book.source_records)
        print(
            f"stage={stage.stage_number} title={book.title!r} isbn={book.isbn_13 or book.isbn_10 or 'Not available'} "
            f"confidence={assessment.confidence} sources={sources} hours={stage.estimated_hours}"
        )
    print(
        f"total_hours={result.reading_path.total_estimated_hours} "
        f"constraints_satisfied={result.reading_path.constraints_satisfied}"
    )
    for warning in result.warnings:
        print(f"warning={warning}")


if __name__ == "__main__":
    main()
