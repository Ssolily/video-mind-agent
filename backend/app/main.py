import os

# Resolve OpenMP conflict (multiple libiomp5md.dll)
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.video_api import router as video_router

app = FastAPI(title=settings.app_name, debug=settings.debug)

# Start / stop background queue workers on app lifespan
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app):
    from app.services import task_queue
    task_queue.recover_stale_tasks()
    task_queue.start_workers(num_workers=1)
    from app.services import task_monitor
    from app.config import MONITOR_INTERVAL_SEC
    task_monitor.start_monitor(interval_sec=MONITOR_INTERVAL_SEC)
    yield
    task_queue.check_timeouts()
    from app.services import task_monitor
    task_monitor.stop_monitor()
    task_queue.stop_workers(timeout=10.0)

app.router.lifespan_context = lifespan

# Serve report static files (vis images, etc.)
from app.config import REPORTS_DIR
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static/reports", StaticFiles(directory=str(REPORTS_DIR)), name="reports")

# CORS (allow frontend dev server)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(video_router, prefix="/api/v1")

from app.services.task_service import get_task, list_tasks, cancel_task, retry_task


@app.get("/api/v1/tasks")
async def list_tasks_route(
    status: str | None = None,
    video_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    return list_tasks(status=status, video_id=video_id, limit=limit, offset=offset)


@app.get("/api/v1/tasks/{task_id}")
async def get_task_route(task_id: str):
    from fastapi import HTTPException
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return task


@app.get("/api/tasks/{task_id}")
async def get_task_legacy(task_id: str):
    from fastapi import HTTPException
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return task


@app.post("/api/v1/tasks/{task_id}/cancel")
async def cancel_task_route(task_id: str):
    ok = cancel_task(task_id)
    if not ok:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Task not found or already finished")
    return {"task_id": task_id, "status": "cancelled"}


@app.post("/api/v1/tasks/{task_id}/retry")
async def retry_task_route(task_id: str):
    new_id = retry_task(task_id)
    if new_id is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Original task not found")
    return {"task_id": task_id, "new_task_id": new_id, "status": "retry_created"}


@app.get("/api/v1/tasks/{task_id}/events")
async def task_events(task_id: str, request: Request):
    """SSE endpoint for real-time task progress."""
    from fastapi import HTTPException
    from fastapi.responses import StreamingResponse
    import asyncio
    import json

    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    async def event_generator():
        last_status = None
        last_progress = -1
        while True:
            current = get_task(task_id)
            if current is None:
                yield f"data: {json.dumps({'type': 'error', 'task_id': task_id, 'message': 'Task deleted'})}\n\n"
                break
            status = current.get("status")
            progress = current.get("progress", 0)
            if status != last_status or abs((progress or 0) - last_progress) > 0.01:
                event = {
                    "task_id": task_id,
                    "status": status,
                    "progress": progress,
                    "current_step": current.get("current_step", ""),
                    "message": current.get("error") or current.get("current_step", ""),
                    "updated_at": current.get("updated_at", ""),
                }
                yield f"data: {json.dumps(event)}\n\n"
                last_status = status
                last_progress = progress
                if status in ("completed", "completed_with_errors", "failed", "cancelled"):
                    yield f"data: {json.dumps({'type': 'final', 'task_id': task_id})}\n\n"
                    break
            await asyncio.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/v1/tasks/{task_id}/logs")
async def task_logs(task_id: str, lines: int = 200):
    from app.services.task_logger import read_task_log_lines
    log_lines = read_task_log_lines(task_id, n=lines)
    return {"task_id": task_id, "lines": log_lines, "count": len(log_lines)}


# Health


@app.get("/api/v1/system/storage")
async def system_storage():
    """Return storage health info for the data directory."""
    import shutil
    from app.config import DATA_DIR, MIN_FREE_DISK_GB
    from pathlib import Path

    usage = shutil.disk_usage(str(DATA_DIR))
    free_gb = round(usage.free / (1024**3), 2)
    used_gb = round(usage.used / (1024**3), 2)

    def _dir_size_gb(subdir: str) -> float:
        d = DATA_DIR / subdir
        if not d.is_dir():
            return 0.0
        total = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        return round(total / (1024**3), 4)

    sizes = {
        "uploads_gb": _dir_size_gb("raw_videos"),
        "clips_gb": _dir_size_gb("clips"),
        "reports_gb": _dir_size_gb("reports"),
        "task_logs_gb": _dir_size_gb("task_logs"),
    }

    warnings_list = []
    if free_gb < MIN_FREE_DISK_GB:
        warnings_list.append(f"Low disk space: {free_gb} GB free (min: {MIN_FREE_DISK_GB} GB)")
    total_task_gb = sizes["clips_gb"] + sizes["reports_gb"]

    return {
        "data_dir": str(DATA_DIR),
        "free_gb": free_gb,
        "used_gb": used_gb,
        "min_free_disk_gb": MIN_FREE_DISK_GB,
        **sizes,
        "warnings": warnings_list,
    }

@app.get("/api/v1/q/info")
async def queue_info():
    from app.services import task_queue
    from app.services.task_store import count_tasks_by_status, list_task_records
    from datetime import datetime, timezone
    from app.config import TASK_TIMEOUT_SEC, STEP_TIMEOUT_SEC, TASK_STALE_SEC, MAX_QUEUE_SIZE, WORKER_CONCURRENCY

    now = datetime.now(timezone.utc)
    stale_running = []
    for t in list_task_records(status_filter="running"):
        s = t.get("started_at")
        if s:
            try:
                elapsed = (now - datetime.fromisoformat(s)).total_seconds()
                if elapsed > TASK_TIMEOUT_SEC:
                    stale_running.append({"task_id": t["task_id"], "elapsed_sec": round(elapsed, 1)})
            except (ValueError, TypeError):
                pass

    oldest_age = None
    for t in list_task_records(status_filter="queued"):
        q = t.get("queued_at") or t.get("created_at")
        if q:
            try:
                age = (now - datetime.fromisoformat(q)).total_seconds()
                if oldest_age is None or age > oldest_age:
                    oldest_age = round(age, 1)
            except (ValueError, TypeError):
                pass

    from app.services.task_monitor import is_monitor_running

    return {
        "q_size": task_queue.get_queue_size(),
        "max_queue_size": MAX_QUEUE_SIZE,
        "active_workers": len(task_queue._workers) if hasattr(task_queue, "_workers") else 0,
        "worker_concurrency": WORKER_CONCURRENCY,
        "active_task": task_queue.get_active_task(),
        "status_counts": count_tasks_by_status(),
        "oldest_queued_task_age_sec": oldest_age,
        "stale_running_tasks": stale_running,
        "timeout_config": {"task_timeout_sec": TASK_TIMEOUT_SEC, "step_timeout_sec": STEP_TIMEOUT_SEC, "stale_sec": TASK_STALE_SEC},
        "heartbeats": task_queue.get_heartbeats(),
        "monitor_running": is_monitor_running(),
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
