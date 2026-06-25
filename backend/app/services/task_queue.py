"""In-process task queue for VideoMind Agent.

Provides a thread-safe queue for video analysis tasks with:
- Configurable concurrency (default 1 worker)
- Cancellation support via cancellation_requested flag
- Retry support (creates new task, preserves history)
- Queue status monitoring
- Graceful shutdown
"""

import logging
import queue
import threading
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_task_queue: queue.Queue = queue.Queue(maxsize=20)
_workers: list[threading.Thread] = []
_running = threading.Event()
_running.set()
_worker_id_counter = 0
_worker_id_lock = threading.Lock()
_active_task: Optional[dict] = None
_active_task_lock = threading.Lock()


def _next_worker_id() -> str:
    global _worker_id_counter
    with _worker_id_lock:
        _worker_id_counter += 1
        return f"worker-{_worker_id_counter}"


def enqueue(task_id: str, video_id: str, user_goal: str, sample_fps: float, top_k: int, planner_provider: str = "") -> None:
    _task_queue.put_nowait({
        "task_id": task_id, "video_id": video_id, "user_goal": user_goal,
        "sample_fps": sample_fps, "top_k": top_k,
        "planner_provider": planner_provider,
        "enqueued_at": datetime.now(timezone.utc).isoformat(),
    })


def start_workers(num_workers: int = 1) -> None:
    _running.set()
    for _ in range(num_workers):
        t = threading.Thread(target=_worker_loop, daemon=True)
        t.start()
        _workers.append(t)
    logger.info("Started %d task worker(s)", num_workers)


def stop_workers(timeout: float = 5.0) -> None:
    _running.clear()
    for t in _workers:
        t.join(timeout=timeout)
    _workers.clear()
    logger.info("All workers stopped")


def get_queue_size() -> int:
    return _task_queue.qsize()


def get_active_task() -> Optional[dict]:
    with _active_task_lock:
        return _active_task


def is_queue_full() -> bool:
    return _task_queue.full()


def _worker_loop() -> None:
    worker_id = _next_worker_id()
    _heartbeats[worker_id] = {"worker_id": worker_id, "started_at": datetime.now(timezone.utc).isoformat(), "last_heartbeat_at": datetime.now(timezone.utc).isoformat(), "status": "idle", "active_task_id": None, "processed_count": 0}
    logger.info("Worker %s started", worker_id)
    while _running.is_set():
        try:
            try:
                item = _task_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            task_id = item["task_id"]
            video_id = item["video_id"]
            user_goal = item["user_goal"]
            sample_fps = item["sample_fps"]
            top_k = item["top_k"]
            planner_provider = item.get("planner_provider", "")
            if _is_cancelled(task_id):
                _set_status(task_id, "cancelled")
                _update_manifest_status(task_id, "cancelled")
                record_task_completed(worker_id)
                _task_queue.task_done()
                continue
            now = datetime.now(timezone.utc).isoformat()
            _set_running(task_id, worker_id, now)
            with _active_task_lock:
                _active_task = {"task_id": task_id, "worker_id": worker_id, "started_at": now}
                with _heartbeat_lock:
                    if worker_id in _heartbeats:
                        _heartbeats[worker_id]["status"] = "active"
                        _heartbeats[worker_id]["active_task_id"] = task_id
                        _heartbeats[worker_id]["last_heartbeat_at"] = datetime.now(timezone.utc).isoformat()
            try:
                _execute_task(task_id, video_id, user_goal, sample_fps, top_k, planner_provider)
            except Exception as exc:
                logger.error("Worker %s: task %s failed: %s", worker_id, task_id, exc)
                if not _was_cancelled(task_id):
                    _set_status(task_id, "failed", error=str(exc))
                _update_manifest_status(task_id, "failed")
            finally:
                with _active_task_lock:
                    _active_task = None
                    record_task_completed(worker_id)
            _task_queue.task_done()
        except Exception:
            logger.exception("Worker %s: unexpected error", worker_id)
    logger.info("Worker %s stopped", worker_id)


def _update_manifest_status(task_id: str, status: str) -> None:
    try:
        from app.services.storage_manifest_service import update_status, scan_task_directory, load_manifest
        # Try scanning for task files first
        m = load_manifest(task_id)
        if m:
            scan_task_directory(task_id, m.get("video_id", ""))
        update_status(task_id, status)
    except Exception:
        pass


def _execute_task(task_id, video_id, user_goal, sample_fps, top_k, planner_provider=""):
    from app.services.storage_service import get_video_path
    from app.agent.planner import build_plan
    from app.agent.executor import execute_plan
    raw_path = get_video_path(video_id)
    if not raw_path:
        _set_status(task_id, "failed", error="Video not found")
        _update_manifest_status(task_id, "failed")
        return
    kwargs = {"sample_fps": sample_fps, "top_k": top_k}
    plan = build_plan(user_goal)
    if _is_cancelled(task_id):
        _set_status(task_id, "cancelled")
        return
    _update_progress(task_id, 0.0, "", {"video_id": video_id, "user_goal": user_goal, "plan": plan, "steps": []})

    def on_step_update(idx, total, current_step, state):
        if _is_cancelled(task_id):
            return
        progress = round((idx + 1) / total, 4)
        _update_progress(task_id, progress, current_step, {"video_id": video_id, "user_goal": user_goal, "plan": plan, "steps": state.steps})

    state = execute_plan(video_id=video_id, video_path=raw_path, user_goal=user_goal, tool_names=None, kwargs=kwargs, on_step_update=on_step_update, task_id=task_id)
    if _is_cancelled(task_id):
        _set_status(task_id, "cancelled")
        return
    final_status = "completed" if not any(s["status"] == "error" for s in state.steps) else "completed_with_errors"
    _update_manifest_status(task_id, final_status)
    now = datetime.now(timezone.utc).isoformat()
    _mark_finished(task_id, final_status, now, {"video_id": video_id, "user_goal": user_goal, "plan": plan, "steps": state.steps})


def _is_cancelled(task_id):
    from app.services.task_store import get_task_record
    r = get_task_record(task_id)
    if r is None:
        return False
    return r.get("status") == "cancelled" or bool(r.get("cancellation_requested"))


def _was_cancelled(task_id):
    from app.services.task_store import get_task_record
    r = get_task_record(task_id)
    if r is None:
        return False
    return r.get("status") == "cancelled"


def _set_status(task_id, status, error=None):
    from app.services.task_store import update_task_record
    kw = {"status": status}
    if error:
        kw["error"] = error
    update_task_record(task_id, **kw)


def _set_running(task_id, worker_id, started_at):
    from app.services.task_store import update_task_record
    update_task_record(task_id, status="running", worker_id=worker_id, started_at=started_at)


def _mark_finished(task_id, status, finished_at, result):
    from app.services.task_store import update_task_record
    update_task_record(task_id, status=status, progress=1.0, current_step="done", result=result, finished_at=finished_at)


def _update_progress(task_id, progress, current_step, result):
    from app.services.task_store import update_task_record
    update_task_record(task_id, progress=progress, current_step=current_step, result=result)
# ── Timeout support ──────────────────────────────────

def check_timeouts(config_timeout=3600, step_timeout=900, stale_timeout=1800):
    from app.services.task_store import get_task_record, update_task_record, list_task_records
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    marked = []

    running = list_task_records(status_filter="running")
    for task in running:
        tid = task["task_id"]
        started_at = task.get("started_at")
        if not started_at:
            continue
        try:
            started = datetime.fromisoformat(started_at)
            elapsed = (now - started).total_seconds()
        except (ValueError, TypeError):
            continue
        if elapsed > config_timeout:
            update_task_record(tid, status="failed", error=f"Task timed out after {elapsed:.0f}s (limit: {config_timeout}s)")
            from app.services.task_logger import write_task_log
            write_task_log(tid, f"Timed out after {elapsed:.0f}s", "ERROR")
            marked.append(tid)

    queued = list_task_records(status_filter="queued")
    for task in queued:
        tid = task["task_id"]
        queued_at = task.get("queued_at") or task.get("created_at")
        if not queued_at:
            continue
        try:
            qd = datetime.fromisoformat(queued_at)
            elapsed = (now - qd).total_seconds()
        except (ValueError, TypeError):
            continue
        if elapsed > stale_timeout:
            update_task_record(tid, status="failed", error=f"Task queued too long ({elapsed:.0f}s), marked stale")
            marked.append(tid)

    return marked


def recover_stale_tasks():
    from app.services.task_store import list_task_records, update_task_record
    count = 0
    for status in ("running", "queued", "pending"):
        tasks = list_task_records(status_filter=status)
        for t in tasks:
            update_task_record(t["task_id"], status="failed", error="Task interrupted by backend restart")
            count += 1
    if count:
        import logging
        logging.getLogger(__name__).info("Recovered %d stale task(s) on startup", count)
    return count


# ── Worker heartbeat ──────────────────────────────────

_heartbeats: dict[str, dict] = {}
_heartbeat_lock = threading.Lock()
_worker_processed: dict[str, int] = {}


def record_task_completed(worker_id: str) -> None:
    with _heartbeat_lock:
        _worker_processed[worker_id] = _worker_processed.get(worker_id, 0) + 1


def update_heartbeat() -> None:
    with _active_task_lock:
        at = _active_task
    worker_id = at.get("worker_id") if at else None
    now = datetime.now(timezone.utc).isoformat()
    with _heartbeat_lock:
        for wid in list(_heartbeats.keys()):
            if wid == worker_id:
                _heartbeats[wid]["last_heartbeat_at"] = now
                _heartbeats[wid]["status"] = "active"
                _heartbeats[wid]["active_task_id"] = at["task_id"] if at else None
            else:
                if _heartbeats[wid]["status"] != "idle":
                    _heartbeats[wid]["status"] = "idle"
                    _heartbeats[wid]["active_task_id"] = None


def get_heartbeats() -> dict:
    with _heartbeat_lock:
        return dict(_heartbeats)


def get_stale_workers(threshold_sec: int = 120) -> list[str]:
    stale = []
    with _heartbeat_lock:
        now = datetime.now(timezone.utc)
        for wid, hb in _heartbeats.items():
            lh = hb.get("last_heartbeat_at")
            if lh:
                try:
                    elapsed = (now - datetime.fromisoformat(lh)).total_seconds()
                    if elapsed > threshold_sec:
                        stale.append(wid)
                except (ValueError, TypeError):
                    stale.append(wid)
    return stale
