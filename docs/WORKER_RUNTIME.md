# Worker Runtime Guide

## Overview
The VideoMind Agent uses an in-process task queue for asynchronous video analysis.
Tasks are created via the API, enqueued, and processed by background worker threads.

## Architecture

```
Client -> FastAPI -> Task Service -> Task Queue -> Worker Thread -> Agent Pipeline
                           |
                      SQLite Persistence
```

## Task States

| State | Description |
|-------|-------------|
| pending | Created but not yet queued |
| queued | Waiting in queue for a worker |
| running | Being processed by a worker |
| completed | All steps finished successfully |
| completed_with_errors | Finished with some step errors |
| failed | Fatal error during execution |
| cancelled | Cancelled by user request |

## Starting Workers

Workers start automatically with the FastAPI application (via app lifespan).
To run a standalone worker:

```powershell
# Start 1 worker
.\scripts\worker.ps1

# Start 2 concurrent workers
.\scripts\worker.ps1 -Concurrency 2

# Stop worker
.\scripts\worker.ps1 -Stop
```

## Checking Status

```powershell
python scripts/check_worker.py
```

Or via API:
```bash
curl http://127.0.0.1:8000/api/v1/q/info
```

## API Endpoints

### List Tasks
```bash
curl http://127.0.0.1:8000/api/v1/tasks
curl http://127.0.0.1:8000/api/v1/tasks?status=failed
curl http://127.0.0.1:8000/api/v1/tasks?video_id=abc123
```

### Get Task
```bash
curl http://127.0.0.1:8000/api/v1/tasks/{task_id}
```

### Cancel Task
```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/{task_id}/cancel
```

### Retry Task
```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks/{task_id}/retry
```

## Cancellation Behavior

- **Queued tasks**: Immediately marked as cancelled (worker skips them)
- **Running tasks**: `cancellation_requested` flag is set; worker checks at step boundaries
- **Completed/failed tasks**: Cannot be cancelled (API returns 400)

## Retry Behavior

- **Failed/cancelled tasks**: Creates a new task with `parent_task_id` referencing the original
- **Running tasks**: Cannot be retried (must wait for completion or failure)
- **Completed tasks**: Cannot be retried (creates a new independent task)
- Retry count is tracked in `retry_count` field

## Persistence

Task state is persisted in SQLite (`data/app.db`), so completed tasks survive backend restarts.
Queued tasks that were in-memory during a crash will be lost.

## Configuration

Settings in `.env.example`:

```env
VIDEOMIND_QUEUE_BACKEND=inprocess
VIDEOMIND_REDIS_URL=redis://localhost:6379/0
VIDEOMIND_WORKER_CONCURRENCY=1
VIDEOMIND_TASK_TIMEOUT_SEC=3600
VIDEOMIND_MAX_QUEUE_SIZE=20
```

## Storage Directory Structure

Runtime files are organized under the `data/` directory:

| Directory | Purpose | Cleanup Policy |
|-----------|---------|----------------|
| `data/uploads/` (or `data/raw_videos/`) | Uploaded source videos | Preserved for completed tasks |
| `data/clips/` | Exported highlight clips | Deletable via `cleanup_storage.py` |
| `data/reports/` | Generated Markdown/JSON reports | Preserved for completed tasks |
| `data/task_logs/` | Per-task log files | Deletable via `--delete-logs` |
| `data/tmp/` | Temporary processing files | Cleaned up automatically |

**Important**: API responses never expose local filesystem paths. All file references use relative API URLs.

## Upload Limits

Configured via `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `VIDEOMIND_MAX_UPLOAD_MB` | 1024 | Maximum upload file size in MB |
| `VIDEOMIND_MAX_VIDEO_DURATION_SEC` | 7200 | Maximum video duration in seconds |
| `VIDEOMIND_MAX_VIDEO_WIDTH` | 3840 | Maximum video width (0 = no limit) |
| `VIDEOMIND_MAX_VIDEO_HEIGHT` | 2160 | Maximum video height (0 = no limit) |
| `VIDEOMIND_MIN_FREE_DISK_GB` | 5 | Minimum free disk space before refusing new tasks |
| `VIDEOMIND_MAX_TASK_STORAGE_MB` | 2048 | Maximum storage per task |

When limits are exceeded, the API returns a user-friendly error message. The frontend displays translated Chinese error messages for common scenarios:
- **File too large (413)**: "文件过大"
- **Queue full**: "队列已满"
- **Disk space low**: "磁盘空间不足"
- **Video too long**: "视频过长"
- **Unsupported format**: "不支持的格式"

## Disk Space Guardrail

The system actively checks free disk space before accepting new uploads or creating analysis tasks.

| Variable | Default | Description |
|----------|---------|-------------|
| `VIDEOMIND_MIN_FREE_DISK_GB` | 5 | Minimum free disk space in GB |

When free space falls below the threshold:
- **Upload** returns HTTP 507 (Insufficient Storage) with a user-friendly error
- **Agent-run** returns HTTP 507 before creating a task
- The background monitor logs a warning every interval

The check is performed via `shutil.disk_usage()` on the `DATA_DIR` path.
If the check itself fails (permission error, etc.), the request is still processed.

### Error Response Example
```json
{
  "detail": "Insufficient disk space: 3.2 GB free (minimum: 5 GB). Please clean storage and retry."
}
```

## Storage Manifest

Each task has a per-task storage manifest that tracks all generated files.

### Manifest Location
```
data/task_manifests/{task_id}.json
```

### Manifest JSON Structure
```json
{
  "task_id": "abc123",
  "video_id": "vid_001",
  "status": "completed",
  "files": [
    {
      "type": "clip|report|log|upload",
      "relative_path": "clips/vid_001/clip_001.mp4",
      "size_bytes": 1234567,
      "created_at": "2026-06-21T...",
      "exists": true
    }
  ],
  "total_size_bytes": 1234567,
  "created_at": "2026-06-21T...",
  "updated_at": "2026-06-21T..."
}
```

### Security
- Manifests never store Windows absolute paths
- All paths are relative to `DATA_DIR`
- Path traversal (`..`) is rejected

### Manifest Lifecycle
1. Created when task is created (via agent-run)
2. Upload file recorded after video upload
3. Status updated when task completes or fails
4. Scan task directory on completion to discover report/clip/log files
5. Cleanup scripts read manifests to determine file ownership

### Cleanup with Manifests
The cleanup_storage.py script uses manifests to:
- Skip files belonging to completed tasks (not deleted by default)
- Skip files belonging to running/queued tasks
- Delete only files from failed/cancelled tasks (when --delete-failed)
- Detect orphaned files (no manifest match) for cleanup (when --delete-orphaned)

## Storage Health API

Check disk usage via:

```bash
curl http://127.0.0.1:8000/api/v1/system/storage
```

Returns free/used space, per-subdirectory sizes, and warnings.

CLI equivalent:

```powershell
python scripts/check_storage.py --local
python scripts/check_storage.py --json
```

## Storage Cleanup

The `cleanup_storage.py` script manages disk space:

```powershell
# Dry run — preview what would be deleted
python scripts/cleanup_storage.py --dry-run --older-than-days 30

# Delete old task logs
python scripts/cleanup_storage.py --delete-logs --older-than-days 7

# Delete orphaned files (no matching task)
python scripts/cleanup_storage.py --delete-orphaned --dry-run

# Delete failed task files
python scripts/cleanup_storage.py --delete-failed --older-than-days 1

# Limit total storage to 10 GB
python scripts/cleanup_storage.py --max-total-gb 10 --dry-run
```

## Background Monitor

A background monitor thread runs periodically (configurable via `VIDEOMIND_MONITOR_INTERVAL_SEC`, default 30s) to:

1. **Check task timeouts** — Mark overdue running tasks as failed
2. **Update worker heartbeat** — Track worker liveness
3. **Check disk space** — Log warning when free space is low

The monitor starts automatically with the FastAPI application (via lifespan) and stops on shutdown.

Monitor status is visible via the queue info endpoint:

```bash
curl http://127.0.0.1:8000/api/v1/q/info
```

Returns `monitor_running: true/false` and current `heartbeats`.

## Worker Heartbeat

Each worker thread registers a heartbeat on startup and updates it periodically. The heartbeat records:
- worker_id
- started_at
- last_heartbeat_at
- status (idle/active)
- active_task_id
- processed_count

Stale workers (no heartbeat for 120s) are reported via `queue_info` or `check_worker.py`.

## Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues.


## Windows Notes

- Workers run on background threads by default
- The worker process script (`worker.ps1`) starts a headless Python process
- To stop: use `worker.ps1 -Stop` or `dev.ps1 -Kill`
- In-process queue does not require Redis


## Real-Time Progress (SSE)

Subscribe to real-time task progress via Server-Sent Events:

```bash
curl -N http://127.0.0.1:8000/api/v1/tasks/{task_id}/events
```

Returns `text/event-stream` with events containing:
- task_id, status, progress, current_step, message, updated_at

A `final` event is sent when the task completes, fails, or is cancelled.
If SSE is unavailable, the frontend falls back to polling.

## Task Logs

Each task has its own log file at `data/task_logs/{task_id}.log`.

View via API:
```bash
curl http://127.0.0.1:8000/api/v1/tasks/{task_id}/logs?lines=200
```

## Timeout Configuration

Set in `.env`:
```env
VIDEOMIND_TASK_TIMEOUT_SEC=3600
VIDEOMIND_STEP_TIMEOUT_SEC=900
VIDEOMIND_TASK_STALE_SEC=1800
```

Overdue running tasks are marked `failed` with timeout reason.
Stale queued tasks are also cleaned up automatically.

## Crash Recovery

On backend restart, any tasks left in `running`/`queued`/`pending` state
are marked as `failed` with "Task interrupted by backend restart".
Already completed/failed/cancelled tasks are not affected.

## Task Cleanup

Clean up old tasks:
```bash
python scripts/cleanup_tasks.py --older-than-days 7
python scripts/cleanup_tasks.py --older-than-days 30 --dry-run
python scripts/cleanup_tasks.py --older-than-days 7 --only-failed
```
