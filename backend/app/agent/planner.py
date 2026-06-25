"""Rule-based planner – maps user goals to ordered tool lists.

Also provides ``validate_plan`` which checks tool existence, ordering
dependencies, and rejects unknown tools.

When the LLM planner is enabled, ``build_plan`` delegates to DeepSeek.
"""

from app.agent.tools import TOOL_REGISTRY
from app.agent.plan_schema import StepPlan, ToolCall, PlanValidationResult


# ── Tool dependency graph ───────────────────────────
# A tool can run only after all of its dependencies have completed.

_TOOL_DEPENDENCIES: dict[str, list[str]] = {
    "metadata": [],
    "extract_frames": [],
    "detect_scenes": [],
    "detect_objects": ["extract_frames"],
    "track_objects": ["detect_objects"],
    "transcribe": [],
    "recommend_highlights": ["detect_scenes", "detect_objects", "track_objects"],
    "export_clips": ["recommend_highlights"],
    "generate_report": ["metadata", "detect_scenes", "detect_objects",
                         "track_objects", "recommend_highlights"],
}


# ── Goal → tool patterns ───────────────────────────

_GOAL_MAP: list[tuple[list[str], list[str]]] = [
    # (keywords, required_tool_chain)
    (["metadata", "信息", "基本信息"], ["metadata"]),
    (["scene", "镜头", "场景"], ["metadata", "detect_scenes"]),
    (["frame", "帧", "抽帧"], ["metadata", "extract_frames"]),
    (["object", "检测", "目标", "yolo"], ["metadata", "extract_frames", "detect_objects", "track_objects"]),
    (["subtitle", "字幕", "transcribe", "语音", "识别"], ["metadata", "transcribe"]),
    (["highlight", "精彩", "片段", "推荐"], [
        "metadata", "extract_frames", "detect_scenes",
        "detect_objects", "track_objects", "recommend_highlights",
    ]),
    (["clip", "export", "导出", "剪辑"], [
        "metadata", "extract_frames", "detect_scenes",
        "detect_objects", "track_objects",
        "recommend_highlights", "export_clips",
    ]),
    (["report", "报告", "摘要", "总结"], [
        "metadata", "extract_frames", "detect_scenes",
        "detect_objects", "track_objects", "transcribe",
        "recommend_highlights", "export_clips", "generate_report",
    ]),
]


# ── Core plan builder ───────────────────────────────


def build_plan(user_goal: str, planner_provider: str = "") -> list[str]:
    """Return an ordered list of tool names based on the user's goal.

    Parameters
    ----------
    planner_provider : str
        "llm" — try DeepSeek first, fallback to rule.
        "rule" — skip LLM, use keyword matching.
        "" — use env var ``VIDEOMIND_PLANNER_PROVIDER`` (default "rule").
    """
    from app.config import PLANNER_PROVIDER as _CFG
    provider = (planner_provider or _CFG).lower()

    # 1. Try LLM planner if configured
    if provider == "llm":
        from app.config import DEEPSEEK_API_KEY
        if DEEPSEEK_API_KEY:
            try:
                from app.agent.llm_client import call_llm_planner
                llm_tools = call_llm_planner(user_goal)
                if llm_tools is not None:
                    validation = validate_plan(llm_tools)
                    if validation.valid:
                        return llm_tools
            except Exception:
                pass

    # 2. Fallback: rule-based keyword matching
    return _rule_based_plan(user_goal)


def _rule_based_plan(user_goal: str) -> list[str]:
    """Original keyword-matching planner."""
    goal_lower = user_goal.lower()
    matched_tools: list[str] = []
    matched_any = False

    for keywords, tools in _GOAL_MAP:
        if any(kw in goal_lower for kw in keywords):
            if len(tools) > len(matched_tools):
                matched_tools = tools
                matched_any = True

    if not matched_any:
        matched_tools = [
            "metadata", "extract_frames", "detect_scenes",
            "detect_objects", "track_objects", "transcribe",
            "recommend_highlights", "export_clips", "generate_report",
        ]

    return matched_tools


# ── Plan validation ─────────────────────────────────


def validate_plan(tool_names: list[str]) -> PlanValidationResult:
    """Validate an ordered list of tool names.

    Checks
    ------
    1. Every name exists in :data:`TOOL_REGISTRY`.
    2. If a tool has declared dependencies, every dependency appears **before**
       it in the list.
    3. No duplicate tool names (each tool should run at most once).

    Returns
    -------
    PlanValidationResult
        ``valid=True`` if all checks pass, together with an error list
        otherwise.
    """
    errors_list: list[str] = []

    known = set(TOOL_REGISTRY.keys())
    seen: set[str] = set()

    for idx, name in enumerate(tool_names):
        if name not in known:
            errors_list.append(
                f"tool #{idx}: \"{name}\" is not in TOOL_REGISTRY "
                f"(known: {sorted(known)})"
            )
            seen.add(name)
            continue

        if name in seen:
            errors_list.append(
                f"tool #{idx}: \"{name}\" appears more than once"
            )

        seen.add(name)

    valid_names = [n for n in tool_names if n in known]
    name_pos = {n: i for i, n in enumerate(valid_names)}

    for name in valid_names:
        pos = name_pos[name]
        for dep in _TOOL_DEPENDENCIES.get(name, []):
            if dep not in name_pos:
                errors_list.append(
                    f"\"{name}\" depends on \"{dep}\" but \"{dep}\" is not in the plan"
                )
            elif name_pos[dep] >= pos:
                errors_list.append(
                    f"\"{dep}\" must appear before \"{name}\" "
                    f"(dep order violated)"
                )

    return PlanValidationResult(
        valid=len(errors_list) == 0,
        errors=errors_list,
    )