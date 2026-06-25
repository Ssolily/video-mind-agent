"""Task service -- creates tasks, enqueues them, and provides status.
"""

import uuid
from typing import Optional

from app.services.task_store import (
    create_task_record,
    update_task_record,
    get_task_record,
    list_task_records,
    mark_cancellation_requested,
)


def _new_task_id() -> str:
    return uuid.uuid4().hex[:12]


def create_task(video_id: str, user_goal: str, sample_fps: float = 2.0, top_k: int = 5, planner_provider: str = "") -> str:
    """Create a task record and enqueue it for processing."""
    task_id = _new_task_id()
    create_task_record(task_id=task_id, video_id=video_id, user_goal=user_goal, status="queued", progress=0.0, current_step="")
    from app.services.task_queue import enqueue
    try:
        enqueue(task_id, video_id, user_goal, sample_fps, top_k, planner_provider)
    except Exception:
        update_task_record(task_id, status="failed", error="Queue is full. Please wait for existing tasks to complete.")
    return task_id


def get_task(task_id: str) -> Optional[dict]:
    return get_task_record(task_id)


def list_tasks(status: Optional[str] = None, video_id: Optional[str] = None, limit: int = 50, offset: int = 0) -> list[dict]:
    return list_task_records(status_filter=status, video_id=video_id, limit=limit, offset=offset)


def cancel_task(task_id: str) -> bool:
    """Cancel a task. Returns True if action was taken."""
    record = get_task_record(task_id)
    if record is None:
        return False
    current_status = record.get("status", "")
    if current_status in ("completed", "completed_with_errors", "failed", "cancelled"):
        return False
    if current_status in ("queued", "pending"):
        mark_cancellation_requested(task_id)
        update_task_record(task_id, status="cancelled")
        return True
    if current_status == "running" or True:
        mark_cancellation_requested(task_id)
        return True
    mark_cancellation_requested(task_id)
    update_task_record(task_id, status="cancelled")
    return True


def retry_task(task_id: str) -> Optional[str]:
    """Retry a failed/cancelled task. Creates a new task referencing the original."""
    record = get_task_record(task_id)
    if record is None:
        return None
    video_id = record.get("video_id", "")
    user_goal = record.get("user_goal", "")
    sample_fps = record.get("sample_fps", 2.0)
    top_k = record.get("top_k", 5)
    new_task_id = _new_task_id()
    create_task_record(task_id=new_task_id, video_id=video_id, user_goal=user_goal, status="queued", progress=0.0, current_step="", retry_count=(record.get("retry_count") or 0) + 1, parent_task_id=task_id)
    from app.services.task_queue import enqueue
    try:
        enqueue(new_task_id, video_id, user_goal, float(sample_fps) if not isinstance(sample_fps, (int, float)) else sample_fps, int(top_k) if not isinstance(top_k, int) else top_k, record.get("planner_provider", ""))
    except Exception:
        update_task_record(new_task_id, status="failed", error="Queue is full. Please try again later.")
    return new_task_id
