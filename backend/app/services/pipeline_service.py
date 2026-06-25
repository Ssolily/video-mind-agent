import json
from pathlib import Path

from app.config import REPORTS_DIR
from app.services.storage_service import get_video_path
from app.agent.executor import execute_plan


def analyze_video(
    video_id: str,
    sample_fps: float = 2.0,
    top_k: int = 5,
    enable_subtitle: bool = True,
    export_clips_enabled: bool = True,
) -> dict:
    """Run the full analysis pipeline sequentially.

    Delegates actual tool execution to *executor.execute_plan*.  This wrapper
    handles skip logic (subtitle, clip export) and generates a summary report.

    Returns a dict with keys: status, video_id, steps, summary, report_path.
    """
    raw_path = get_video_path(video_id)
    if not raw_path:
        return {
            "status": "error",
            "video_id": video_id,
            "error": "Video not found in registry.",
        }

    # ── Build tool list with skip logic ──────────────
    tool_names: list[str] = [
        "metadata",
        "extract_frames",
        "detect_scenes",
    ]

    # detect_objects and track_objects depend on frames having been extracted
    tool_names.extend(["detect_objects", "track_objects"])

    if enable_subtitle:
        tool_names.append("transcribe")

    tool_names.append("recommend_highlights")

    if export_clips_enabled:
        tool_names.append("export_clips")

    tool_names.append("generate_report")

    # ── Execute ──────────────────────────────────────
    kwargs = {"sample_fps": sample_fps, "top_k": top_k}
    state = execute_plan(
        video_id=video_id,
        video_path=raw_path,
        user_goal="report",  # triggers full-pipeline plan in planner
        tool_names=tool_names,
        kwargs=kwargs,
        on_step_update=None,
    )

    # ── Build pipeline report ────────────────────────
    report_path = _build_pipeline_report(video_id, state.steps)
    summary = {
        "total_steps": len(state.steps),
        "ok": sum(1 for s in state.steps if s["status"] == "ok"),
        "errors": sum(1 for s in state.steps if s["status"] == "error"),
        "skipped": sum(1 for s in state.steps if s["status"] == "skipped"),
    }

    return {
        "status": "completed",
        "video_id": video_id,
        "steps": state.steps,
        "summary": summary,
        "report_path": report_path,
    }


# ── Helpers ─────────────────────────────────────────


def _build_pipeline_report(video_id: str, steps: list[dict]) -> str:
    """Collate a summary pipeline report JSON."""
    report: dict = {
        "video_id": video_id,
        "pipeline_steps": steps,
        "summary": {
            "total_steps": len(steps),
            "ok": sum(1 for s in steps if s["status"] == "ok"),
            "errors": sum(1 for s in steps if s["status"] == "error"),
            "skipped": sum(1 for s in steps if s["status"] == "skipped"),
        },
    }
    report_dir = REPORTS_DIR / video_id
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / "pipeline_report.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(out_path)
