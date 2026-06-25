"""Central agent executor — runs an ordered list of tools against a VideoAnalysisState.

This is the single place where tool execution, error capture, and step
recording happen.  Both the background-task runner (task_service) and the
synchronous pipeline (pipeline_service) delegate to this function.
"""

import time
from typing import Callable, Optional

from app.agent.state import VideoAnalysisState
from app.agent.planner import build_plan, validate_plan
from app.agent.tools import TOOL_REGISTRY
from app.services.task_log_service import (
    log_step_start,
    log_step_success,
    log_step_error,
    log_step_skipped,
)


# ── Callback type ───────────────────────────────────

OnStepUpdate = Callable[
    [int, int, str, VideoAnalysisState],  # idx, total, current_tool_name, state
    None,
]


# ── Public API ──────────────────────────────────────


def execute_plan(
    video_id: str,
    video_path: str,
    user_goal: str,
    tool_names: Optional[list[str]] = None,
    kwargs: Optional[dict] = None,
    on_step_update: Optional[OnStepUpdate] = None,
    task_id: Optional[str] = None,
) -> VideoAnalysisState:
    """Execute an ordered list of tools and return the final state.

    Parameters
    ----------
    video_id : str
        Video identifier.
    video_path : str
        Absolute path to the video file on disk.
    user_goal : str
        User's intent (used for planning if *tool_names* is not given).
    tool_names : list[str] | None
        Explicit tool chain.  If *None* or empty, the planner generates one.
    kwargs : dict | None
        Extra keyword arguments forwarded to each tool (e.g. sample_fps, top_k).
    on_step_update : callable | None
        Optional callback invoked after every tool execution.
        Signature: (idx, total, current_tool_name, state).
    task_id : str | None
        Task identifier for structured logging.  Falls back to *video_id*.

    Returns
    -------
    VideoAnalysisState
        The state after all tools have been executed (or failed).
    """
    if not tool_names:
        tool_names = build_plan(user_goal)

    if kwargs is None:
        kwargs = {}

    log_id = task_id or video_id

    state = VideoAnalysisState(
        video_id=video_id,
        video_path=video_path,
        user_goal=user_goal,
    )

    # ── Validate plan before execution ──────────────
    validation = validate_plan(tool_names)
    if not validation.valid:
        for err in validation.errors:
            state.add_step("plan_validation", "error", err)
        return state

    total = len(tool_names)

    for idx, name in enumerate(tool_names):
        tool_fn = TOOL_REGISTRY.get(name)
        if tool_fn is None:
            log_step_skipped(log_id, video_id, name, "unknown tool")
            state.add_step(name, "error", f"unknown tool: {name}")
            if on_step_update:
                on_step_update(idx, total, name, state)
            continue

        log_step_start(log_id, video_id, name)
        t0 = time.perf_counter()

        try:
            state = tool_fn(state, **kwargs)
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            log_step_error(log_id, video_id, name, str(e)[:200], elapsed)
            state.add_step(name, "error", str(e)[:200])
            if on_step_update:
                on_step_update(idx, total, name, state)
            continue

        elapsed = (time.perf_counter() - t0) * 1000
        log_step_success(log_id, video_id, name, elapsed)

        if on_step_update:
            on_step_update(idx, total, name, state)

    return state
