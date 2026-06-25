"""Video result aggregation service.

Builds a ``VideoResultResponse`` from on-disk reports, metadata, highlights,
clips, and task state.  Handles backward compatibility for historical data
and ensures no local filesystem paths are exposed in API responses.
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, Optional

from app.config import (
    RAW_VIDEOS_DIR,
    CLIPS_DIR,
    REPORTS_DIR,
    DATA_DIR,
)
from app.services.media_stream_service import resolve_video_path
from app.schemas.models import (
    VideoResultResponse,
    HighlightResultResponse,
    ClipResultResponse,
    ReportLinksResponse,
    ScoreComponentResponse,
)

logger = logging.getLogger(__name__)

# ── URL helpers ─────────────────────────────────────


def _source_url(video_id: str) -> str:
    return f"/api/v1/videos/{video_id}/source"


def _clip_url(video_id: str, clip_id: str) -> str:
    return f"/api/v1/videos/{video_id}/clips/{clip_id}"


def _report_md_url(video_id: str) -> str:
    return f"/api/v1/videos/{video_id}/reports/markdown"


def _report_json_url(video_id: str) -> str:
    return f"/api/v1/videos/{video_id}/reports/json"


def _report_candidates_url(video_id: str) -> str:
    return f"/api/v1/videos/{video_id}/reports/candidates"


# ── Sanitize error messages ─────────────────────────


def sanitize_error(msg: Optional[str]) -> Optional[str]:
    """Clean an error string so it never contains paths, tracebacks, or keys."""
    if not msg:
        return msg
    # Remove common path patterns
    import re
    cleaned = re.sub(r"[A-Za-z]:\\[^\s,;)\]]+", "[path]", msg)
    cleaned = re.sub(r"/[^\s,;)\]]+", "[path]", cleaned)
    # Truncate long messages
    if len(cleaned) > 500:
        cleaned = cleaned[:500] + "..."
    return cleaned


# ── Load data ───────────────────────────────────────


def _load_json(video_id: str, filename: str) -> Any:
    p = REPORTS_DIR / video_id / filename
    if p.is_file():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load %s for %s: %s", filename, video_id, e)
            return None
    return None


def _video_exists(video_id: str) -> bool:
    """Check if a video has been uploaded (by checking registry or raw dir)."""
    registry_path = DATA_DIR / "video_registry.json"
    if registry_path.is_file():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            if video_id in registry:
                return True
        except Exception:
            pass
    # Fallback: check raw dir
    try:
        resolve_video_path(video_id, RAW_VIDEOS_DIR)
        return True
    except Exception:
        return False


def _get_video_duration(video_id: str) -> Optional[float]:
    """Get video duration from metadata.json, or fallback to ffprobe."""
    meta = _load_json(video_id, "metadata.json")
    if meta and isinstance(meta, dict):
        dur = meta.get("duration") or meta.get("Duration")
        if dur:
            return float(dur)
    # Fallback: check from upload metadata
    registry_path = DATA_DIR / "video_registry.json"
    if registry_path.is_file():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            entry = registry.get(video_id, {})
            raw_path = entry.get("raw_path", "")
            if raw_path:
                from app.services.video_metadata_service import get_video_metadata
                meta = get_video_metadata(raw_path)
                if meta:
                    return float(meta.get("duration", 0))
        except Exception:
            pass
    return None


# ── Highlight normalization ─────────────────────────


def _normalize_highlight(raw: dict, idx: int) -> HighlightResultResponse:
    """Convert a raw highlight dict to a normalized response model.

    Handles historical data that may be missing new fields.
    """
    score = raw.get("score") or raw.get("selection_score") or 0.0
    selection_score = raw.get("selection_score") or raw.get("score") or 0.0
    base_score = raw.get("base_score") or selection_score

    # Handle NaN / Inf
    score = _safe_float(score)
    selection_score = _safe_float(selection_score)
    base_score = _safe_float(base_score)
    overlap_penalty = _safe_float(raw.get("overlap_penalty", 0.0))

    # Build score_breakdown
    sb_raw = raw.get("score_breakdown", {})
    score_breakdown: dict[str, ScoreComponentResponse] = {}
    if sb_raw and isinstance(sb_raw, dict):
        for dim, val in sb_raw.items():
            if isinstance(val, dict):
                score_breakdown[dim] = ScoreComponentResponse(
                    raw=_safe_float(val.get("raw", 0.0)),
                    weight=_safe_float(val.get("weight", 0.0)),
                    weighted=_safe_float(val.get("weighted", 0.0)),
                )
            elif isinstance(val, (int, float)):
                # Historical flat format
                score_breakdown[dim] = ScoreComponentResponse(raw=float(val))

    # reason
    reason = raw.get("reason", [])
    if isinstance(reason, str):
        reason = [reason]

    highlight_id = raw.get("id", "")
    if not highlight_id:
        highlight_id = f"hl_{idx + 1:04d}"

    return HighlightResultResponse(
        id=highlight_id,
        start_time=_safe_float(raw.get("start_time", 0.0)),
        end_time=_safe_float(raw.get("end_time", 0.0)),
        duration=_safe_float(raw.get("duration", 0.0)),
        score=selection_score,
        base_score=base_score,
        selection_score=selection_score,
        overlap_penalty=overlap_penalty,
        score_breakdown=score_breakdown,
        reason=reason if isinstance(reason, list) else [],
    )


def _safe_float(v: Any) -> float:
    """Convert to float, replacing NaN/Inf with 0.0."""
    try:
        f = float(v)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return f
    except (TypeError, ValueError):
        return 0.0


# ── Clip indexing ───────────────────────────────────


def _list_clip_files(video_id: str) -> list[dict]:
    """List clip files for a video_id and return structured info.

    Returns list of dicts with keys: id, filename, path, size_bytes.
    """
    clip_dir = CLIPS_DIR / video_id
    if not clip_dir.is_dir():
        return []

    clips: list[dict] = []
    for f in sorted(clip_dir.iterdir()):
        if f.suffix.lower() == ".mp4" and f.name.startswith("clip_"):
            clips.append({
                "id": f.stem,
                "filename": f.name,
                "path": str(f),
                "size_bytes": f.stat().st_size if f.is_file() else 0,
            })
    return clips


def _match_clips_to_highlights(
    clips: list[dict],
    highlights: list[HighlightResultResponse],
) -> list[ClipResultResponse]:
    """Match clip files to highlights by sequential position.

    clip_001 → first highlight, clip_002 → second highlight, etc.
    If counts differ, unmatched items get highlight_id=None.
    """
    result: list[ClipResultResponse] = []
    for i, clip in enumerate(clips):
        hl = highlights[i] if i < len(highlights) else None
        result.append(ClipResultResponse(
            id=clip["id"],
            url=_clip_url(highlights[0].id.split("_")[0] if highlights else "unknown", clip["id"]) if False else _clip_url(
                # We need video_id — we'll set it at a higher level
                "placeholder",
                clip["id"],
            ),
            start_time=hl.start_time if hl else None,
            end_time=hl.end_time if hl else None,
            duration=hl.duration if hl else None,
            highlight_id=hl.id if hl else None,
            size_bytes=clip["size_bytes"],
        ))
    return result


# ── Task state ──────────────────────────────────────


def _get_task_state(video_id: str) -> Optional[dict]:
    """Load the latest task state for a video_id from the task store."""
    try:
        from app.services.task_store import list_task_records
        tasks = list_task_records(video_id=video_id, limit=1)
        if tasks:
            return tasks[0]
        return None
    except Exception:
        return None


def get_mem_task_by_video(video_id: str) -> Optional[dict]:
    """Search for a task matching the video_id. Delegates to _get_task_state."""
    return _get_task_state(video_id)


# ── Main aggregation ────────────────────────────────


def get_video_result(video_id: str) -> VideoResultResponse:
    """Build a unified result for a video.

    Returns a ``VideoResultResponse`` with all available data.
    Never returns ``None`` or raises ``HTTPException`` — the caller
    (route handler) decides what to return for non-existent videos.
    """
    if not video_id or not _video_exists(video_id):
        # Signal to the route to return 404
        return VideoResultResponse(video_id=video_id, status="not_found")

    duration = _get_video_duration(video_id)
    source_url_val = _source_url(video_id)

    # Load highlights
    raw_highlights = _load_json(video_id, "highlights.json") or []
    highlights = [
        _normalize_highlight(h, i) for i, h in enumerate(raw_highlights)
    ]

    # Load clips
    raw_clips = _list_clip_files(video_id)
    clips = _match_clips_to_highlights(raw_clips, highlights)
    # Fix placeholder video_id in clip URLs
    for clip in clips:
        clip.url = _clip_url(video_id, clip.id)

    # Check report existence
    md_exists = (REPORTS_DIR / video_id / "final_report.md").is_file()
    json_exists = (REPORTS_DIR / video_id / "final_report.json").is_file()
    candidates_exists = (REPORTS_DIR / video_id / "highlight_candidates.json").is_file()

    report = ReportLinksResponse(
        markdown_url=_report_md_url(video_id) if md_exists else None,
        json_url=_report_json_url(video_id) if json_exists else None,
        candidates_url=_report_candidates_url(video_id) if candidates_exists else None,
    )

    # Determine status from task state
    status = "uploaded"
    error: Optional[str] = None
    warnings: list[str] = []

    task = _get_task_state(video_id)
    if task:
        task_status = task.get("status", "")
        if task_status in ("pending", "queued", "running", "success", "completed", "completed_with_errors", "failed", "cancelled"):
            status = task_status
        if task_status == "failed":
            error = sanitize_error(task.get("error"))
        elif task_status == "completed_with_errors":
            error = sanitize_error(task.get("error"))
            warnings.append("部分分析步骤执行失败")

    return VideoResultResponse(
        video_id=video_id,
        status=status,
        duration=duration,
        source_url=source_url_val,
        highlights=highlights,
        clips=clips,
        report=report,
        error=error,
        warnings=warnings,
    )
