from __future__ import annotations

from collections.abc import Callable

from langgraph.graph import END, START, StateGraph

from src.config import Settings
from src.language import interface_language
from src.llm.base import LLMProvider
from src.models import BookCandidate, LearningGoal, RecommendationResult, UserProfile
from src.services.book_matching import merge_candidates, normalize_text
from src.services.goal_alignment import plan_catalog_queries
from src.services.recommendation import (
    _build_path,
    _select_complementary,
    build_concept_requirements,
    enrich_recommendation_narratives,
    load_fallback_candidates,
    search_live_candidates,
)
from src.services.scoring import SCORING_VERSION
from src.state import AgentState

SearchFunction = Callable[[LearningGoal, Settings], tuple[list[BookCandidate], list[str]]]


def build_recommendation_graph(
    settings: Settings,
    allow_cached_fallback: bool = True,
    search_function: SearchFunction = search_live_candidates,
    provider: LLMProvider | None = None,
):
    # A submission demo must not silently reach a real model or catalogue,
    # even if credentials are already present in the caller's environment.
    if settings.demo_mode:
        provider = None

    def concept_planner_node(state: AgentState) -> dict:
        goal = state["learning_goal"]
        warnings = list(state["warnings"])
        if provider is not None:
            try:
                goal = goal.model_copy(update={"catalog_queries": plan_catalog_queries(goal, state["user_profile"], provider)})
            except Exception:
                warnings.append("需求检索规划暂时不可用，将使用主题检索并逐项检查匹配度。" if interface_language(goal) == "zh" else
                                "Search planning is unavailable; topic search will be followed by a suitability check.")
        concepts = build_concept_requirements(state["learning_goal"], state["user_profile"])
        trace = "规划 · 已确定三类知识内容" if interface_language(state["learning_goal"]) == "zh" else "Identified three complementary knowledge areas"
        return {
            "learning_goal": goal,
            "warnings": warnings,
            "concept_requirements": concepts,
            "execution_trace": [*state["execution_trace"], trace],
        }

    def candidate_search_node(state: AgentState) -> dict:
        iteration = state["search_iteration"] + 1
        warnings = list(state["warnings"])
        data_mode = state["data_mode"]
        if settings.demo_mode:
            candidates = load_fallback_candidates(state["learning_goal"])
            data_mode = "cached_demo"
            warnings.append(
                "演示模式：只使用随项目附带的具身智能示例书目，未进行实时检索或模型调用。其他主题可能无法生成完整路径。"
                if interface_language(state["learning_goal"]) == "zh" else
                "Demo mode uses the included embodied-intelligence book snapshots, without live search or model calls. Other topics may not produce a complete path."
            )
        elif iteration == 1:
            found, search_warnings = search_function(state["learning_goal"], settings)
            warnings.extend(search_warnings)
            candidates = merge_candidates([*state["raw_candidates"], *found])
            data_mode = "live"
            goal_text = normalize_text(state["learning_goal"].topic)
            if (
                found
                and allow_cached_fallback
                and interface_language(state["learning_goal"]) == "zh"
                and ("具身" in state["learning_goal"].topic or "embodied" in goal_text)
            ):
                candidates = merge_candidates(
                    [*candidates, *load_fallback_candidates(state["learning_goal"])]
                )
                data_mode = "mixed"
                warnings.append(
                    "为提高中文推荐质量，Atlas 已将实时结果与经过核验的缓存书目共同比较。"
                )
        elif allow_cached_fallback:
            cached = load_fallback_candidates(state["learning_goal"])
            had_live = bool(state["raw_candidates"])
            candidates = merge_candidates([*state["raw_candidates"], *cached])
            data_mode = "mixed" if had_live else "cached_demo"
            warnings.append(
                "实时检索结果不足，已补充清晰标注的缓存示例数据。"
                if interface_language(state["learning_goal"]) == "zh"
                else "Sample data was added because live search returned too few verified books."
            )
        else:
            candidates = state["raw_candidates"]
        trace = (
            f"检索 · 第 {iteration} 轮找到 {len(candidates)} 本候选书目"
            if interface_language(state["learning_goal"]) == "zh"
            else f"Search pass {iteration} found {len(candidates)} unique book candidates"
        )
        return {
            "raw_candidates": candidates,
            "search_iteration": iteration,
            "warnings": list(dict.fromkeys(warnings)),
            "data_mode": data_mode,
            "execution_trace": [
                *state["execution_trace"],
                trace,
            ],
        }

    def identity_validator_node(state: AgentState) -> dict:
        verified = [
            candidate
            for candidate in merge_candidates(state["raw_candidates"])
            if candidate.verification_status.startswith("verified")
            and (candidate.isbn_10 or candidate.isbn_13 or candidate.source_records)
        ]
        trace = (
            f"核验 · 已核对 {len(verified)} 本候选书目的基本信息"
            if interface_language(state["learning_goal"]) == "zh"
            else f"Verified {len(verified)} book records"
        )
        return {
            "verified_candidates": verified,
            "execution_trace": [
                *state["execution_trace"],
                trace,
            ],
        }

    def route_after_validation(state: AgentState) -> str:
        selected, _, _ = _select_complementary(
            state["verified_candidates"],
            state["learning_goal"],
            state["user_profile"],
        )
        # Three role labels are not enough: every candidate must also clear the
        # same semantic-fit gate used by the final ranking step.
        enough = len(selected) == 3
        if settings.demo_mode or enough or state["search_iteration"] >= state["max_search_iterations"]:
            return "rank"
        return "search"

    def rank_node(state: AgentState) -> dict:
        selected, assessments, warnings = _select_complementary(
            state["verified_candidates"], state["learning_goal"], state["user_profile"], provider
        )
        # The suitability gate already supplies grounded reasons. Do not ask a
        # separate sales-style narrator to rationalise or overstate that decision.
        narrative_warnings = []
        used_live_model = provider is not None and bool(selected)
        if provider is None:
            assessments, narrative_warnings, _ = enrich_recommendation_narratives(
                selected, assessments, state["learning_goal"], state["user_profile"], None)
        warnings.extend(narrative_warnings)
        trace = (
            f"筛选 · 根据匹配度选出 {len(selected)} 本互补书目"
            + ("，并由 Amazon Bedrock 生成差异化推荐说明" if used_live_model else "")
            if interface_language(state["learning_goal"]) == "zh"
            else f"Selected {len(selected)} complementary recommendations using transparent fit scores"
            + (" and expanded each rationale with Amazon Bedrock" if used_live_model else "")
        )
        return {
            "selected_books": selected,
            "assessments": assessments,
            "warnings": list(dict.fromkeys([*state["warnings"], *warnings])),
            "execution_trace": [
                *state["execution_trace"],
                trace,
            ],
        }

    def path_builder_node(state: AgentState) -> dict:
        path = _build_path(
            state["selected_books"],
            state["assessments"],
            state["concept_requirements"],
            state["learning_goal"],
            state["user_profile"],
        )
        trace = (
            f"完成 · 已生成总计 {path.total_estimated_hours:g} 小时的阅读路径"
            if interface_language(state["learning_goal"]) == "zh"
            else f"Created a {path.total_estimated_hours:g}-hour reading path"
        )
        return {
            "reading_path": path,
            "execution_trace": [
                *state["execution_trace"],
                trace,
            ],
        }

    def verifier_node(state: AgentState) -> dict:
        path = state["reading_path"]
        warnings = list(state["warnings"])
        errors = list(state["errors"])
        chinese = interface_language(state["learning_goal"]) == "zh"
        if path is None or len(path.stages) != 3:
            errors.append(
                "最终检查未通过：学习路径尚未覆盖三类知识内容。"
                if chinese
                else "Final check: the reading path does not cover all three knowledge areas."
            )
        if path and not path.constraints_satisfied:
            warnings.append(
                "最终检查未通过：部分必要条件尚未满足。"
                if chinese
                else "Final check: one or more required constraints are not satisfied."
            )
        trace = "检查 · 已核对路径结构与时间预算" if chinese else "Checked the path structure and time budget"
        return {
            "errors": list(dict.fromkeys(errors)),
            "warnings": list(dict.fromkeys(warnings)),
            "execution_trace": [*state["execution_trace"], trace],
        }

    builder = StateGraph(AgentState)
    builder.add_node("concept_planner", concept_planner_node)
    builder.add_node("candidate_search", candidate_search_node)
    builder.add_node("identity_validator", identity_validator_node)
    builder.add_node("rank_and_diversify", rank_node)
    builder.add_node("path_builder", path_builder_node)
    builder.add_node("verifier", verifier_node)
    builder.add_edge(START, "concept_planner")
    builder.add_edge("concept_planner", "candidate_search")
    builder.add_edge("candidate_search", "identity_validator")
    builder.add_conditional_edges(
        "identity_validator",
        route_after_validation,
        {"search": "candidate_search", "rank": "rank_and_diversify"},
    )
    builder.add_edge("rank_and_diversify", "path_builder")
    builder.add_edge("path_builder", "verifier")
    builder.add_edge("verifier", END)
    return builder.compile()


def run_recommendation_graph(
    profile: UserProfile,
    goal: LearningGoal,
    settings: Settings,
    allow_cached_fallback: bool = True,
    search_function: SearchFunction = search_live_candidates,
    provider: LLMProvider | None = None,
) -> RecommendationResult:
    initial: AgentState = {
        "user_profile": profile,
        "learning_goal": goal,
        "concept_requirements": [],
        "search_queries": [],
        "raw_candidates": [],
        "verified_candidates": [],
        "selected_books": [],
        "assessments": [],
        "reading_path": None,
        "concept_mastery": [],
        "user_feedback": [],
        "plan_revisions": [],
        "search_iteration": 0,
        "max_search_iterations": settings.max_search_iterations,
        "errors": [],
        "warnings": [],
        "data_mode": "live",
        "execution_trace": [],
    }
    final = build_recommendation_graph(
        settings,
        allow_cached_fallback=allow_cached_fallback,
        search_function=search_function,
        provider=provider,
    ).invoke(initial, config={"recursion_limit": 20})
    if final["reading_path"] is None:
        raise RuntimeError("Recommendation graph ended without a reading path")
    return RecommendationResult(
        scoring_version=SCORING_VERSION,
        data_mode=final["data_mode"],
        concepts=final["concept_requirements"],
        candidates=final["verified_candidates"],
        selected_books=final["selected_books"],
        assessments=final["assessments"],
        reading_path=final["reading_path"],
        warnings=[*final["warnings"], *final["errors"]],
        execution_trace=final["execution_trace"],
    )
