from __future__ import annotations

from copy import deepcopy
from math import floor

from src.language import interface_language
from src.models import LearningGoal, PlanRevision, ReadingPath


def replan_path(
    path: ReadingPath,
    goal: LearningGoal,
    new_hours_per_week: float,
    too_theoretical: bool,
    low_mastery_concept: str | None,
) -> tuple[ReadingPath, PlanRevision]:
    if new_hours_per_week <= 0:
        raise ValueError("New weekly time must be positive")
    revised = deepcopy(path)
    chinese = interface_language(goal) == "zh"
    old_order = [stage.title for stage in path.stages]
    new_budget = round(goal.duration_weeks * new_hours_per_week, 1)
    stages = list(revised.stages)
    if too_theoretical and len(stages) >= 2:
        stages[0], stages[1] = stages[1], stages[0]
        if chinese:
            stages[0].title = stages[0].title.replace("技术与应用", "应用优先")
            stages[1].title = stages[1].title.replace("概念基础", "聚焦基础")
        else:
            stages[0].title = stages[0].title.replace("Technical/Application", "Practice first")
            stages[0].title = stages[0].title.replace("Technical principles & applications", "Practice first")
            stages[1].title = stages[1].title.replace("Conceptual Foundation", "Focused foundations")
            stages[1].title = stages[1].title.replace("Foundational concepts", "Focused foundations")
    for stage_number, stage in enumerate(stages, start=1):
        stage.stage_number = stage_number
    per_stage = floor((new_budget / max(1, len(stages))) * 10) / 10
    for stage in stages:
        previous_hours = stage.estimated_hours
        stage.estimated_hours = round(min(stage.estimated_hours, per_stage), 1)
        if stage.estimated_hours < previous_hours:
            stage.selected_chapters = list(dict.fromkeys([*stage.selected_chapters,
                (f"本阶段安排 {stage.estimated_hours:g} 小时选读与练习，不代表读完整本书；请从目录中选择与阶段目标直接相关的一节。"
                 if chinese else f"Budget {stage.estimated_hours:g} hours for selected reading and practice, not the whole book; choose one section directly relevant to this stage's objective from its contents.")]))
        if too_theoretical and ("foundation" in stage.title.lower() or "基础" in stage.title):
            stage.selected_chapters = list(
                dict.fromkeys(
                    [
                        *stage.selected_chapters,
                        "仅选读核心概念章节，跳过非必要的理论综述。"
                        if chinese
                        else "Selected concept sections only; skip non-essential theoretical survey material.",
                    ]
                )
            )
    if low_mastery_concept and stages:
        target = stages[1] if len(stages) > 1 else stages[0]
        target.concepts = list(dict.fromkeys([*target.concepts, low_mastery_concept]))
        target.selected_chapters = list(
            dict.fromkeys(
                [
                    *target.selected_chapters,
                    f"为“{low_mastery_concept}”增加简短的前置讲解与主动回忆任务。"
                    if chinese
                    else f"Add a short prerequisite review and active-recall task for {low_mastery_concept}.",
                ]
            )
        )
    revised.version = path.version + 1
    revised.stages = stages
    revised.total_estimated_hours = round(sum(stage.estimated_hours for stage in stages), 1)
    revised.constraints_satisfied = path.constraints_satisfied and revised.total_estimated_hours <= new_budget
    revised.warnings = list(path.warnings)
    if revised.total_estimated_hours > new_budget:
        revised.warnings.append("调整后的路径仍超出时间预算。" if chinese else "The updated path still exceeds your available time.")
    if not path.constraints_satisfied:
        revised.warnings.append("本次只调整阅读安排，原方案中尚未满足的选书要求仍需处理。" if chinese else
                                "This changes the reading schedule only; unresolved book-selection requirements still need attention.")
    new_order = [stage.title for stage in stages]
    explanation_parts: list[str] = []
    if abs(new_hours_per_week - goal.hours_per_week) >= 0.001:
        scope_was_reduced = revised.total_estimated_hours < path.total_estimated_hours - 0.05
        explanation_parts.append(
            (
                "已按新的每周时间压缩各阶段精读范围"
                if chinese
                else "Reading scope was reduced to fit the new weekly schedule"
            )
            if scope_was_reduced
            else (
                "已更新每周时间安排；原有阅读范围仍在新预算内"
                if chinese
                else "The weekly schedule was updated; the existing reading scope already fits the new budget"
            )
        )
    if too_theoretical:
        explanation_parts.append(
            "应用型材料已提前，理论材料改为聚焦选读"
            if chinese
            else "Practice-focused material was moved earlier and theory was narrowed to selected sections"
        )
    if low_mastery_concept:
        explanation_parts.append(
            f"已为“{low_mastery_concept}”加入前置讲解与主动回忆任务"
            if chinese
            else f"A prerequisite review and active-recall task were added for {low_mastery_concept}"
        )
    explanation_parts.append(
        "原有书目与学科视角保持不变"
        if chinese
        else "The existing books and perspectives are unchanged"
    )
    explanation = ("；" if chinese else "; ").join(explanation_parts)
    explanation += "。" if chinese else "."
    revision = PlanRevision(
        previous_version=path.version,
        new_version=revised.version,
        trigger="；".join(
            item
            for item in [
                (f"每周时间改为 {new_hours_per_week:g} 小时" if chinese else f"Available time changed to {new_hours_per_week:g} hours per week"),
                ("第一份材料过于理论化" if chinese else "The first book felt too theoretical") if too_theoretical else "",
                (f"掌握度较低：{low_mastery_concept}" if chinese else f"Needs more support: {low_mastery_concept}") if low_mastery_concept else "",
            ]
            if item
        ),
        changed_constraints={"hours_per_week": new_hours_per_week, "total_hours": new_budget},
        reordered_items=[
            f"{old} -> {new}"
            for old, new in zip(old_order, new_order, strict=True)
            if old != new
        ],
        explanation=explanation,
        preserved_goals=list(goal.required_perspectives),
    )
    return revised, revision
