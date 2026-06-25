"""Structured task logging — writes one JSON line per event to
data/tasks/{task_id}/events.jsonl.
"""

import json
import re
import time
import traceback
from pathlib import Path
from typing import Optional

from app.config import DATA_DIR

_TASKS_LOG_DIR = DATA_DIR / "tasks"


def ensure_task_log_dir(task_id: str) -> Path:
    d = _TASKS_LOG_DIR / task_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _sanitize(msg: str, max_len: int = 300) -> str:
    """Remove absolute local paths from a message and truncate."""
    sanitized = re.sub(
        r"[A-Za-z]:\\[^\s,;)\]>]+",
        "<path>",
        msg,
    )
    sanitized = re.sub(r"/[^\s,;)\]>]+", "<path>", sanitized)
    if len(sanitized) > max_len:
        sanitized = sanitized[:max_len] + "..."
    return sanitized


def append_task_event(
    task_id: str,
    video_id: str,
    step: str,
    event: str,
    status: str,
    *,
    error: Optional[str] = None,
    duration_ms: Optional[float] = None,
    tb: Optional[str] = None,
) -> None:
    """Append a single JSON line to data/tasks/{task_id}/events.jsonl."""
    log_dir = ensure_task_log_dir(task_id)
    log_path = log_dir / "events.jsonl"

    record = {
        "task_id": task_id,
        "video_id": video_id,
        "step": step,
        "event": event,
        "status": status,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
        "duration_ms": duration_ms,
    }

    if error:
        record["error"] = _sanitize(error)
    if tb:
        record["traceback"] = tb

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def log_step_start(task_id: str, video_id: str, step: str) -> None:
    append_task_event(task_id, video_id, step, "start", "running")


def log_step_success(task_id: str, video_id: str, step: str, duration_ms: float) -> None:
    append_task_event(task_id, video_id, step, "success", "ok", duration_ms=duration_ms)


def log_step_error(
    task_id: str, video_id: str, step: str, error: str, duration_ms: float,
) -> None:
    tb = traceback.format_exc()
    append_task_event(
        task_id, video_id, step, "error", "error",
        error=_sanitize(error), duration_ms=duration_ms, tb=tb,
    )


def log_step_skipped(task_id: str, video_id: str, step: str, reason: str) -> None:
    append_task_event(task_id, video_id, step, "skipped", "skipped", error=reason)
