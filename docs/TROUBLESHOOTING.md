# Troubleshooting Guide

## Common Issues

### 1. Conda environment "agent" not found

```powershell
conda env list
```

If "agent" is not listed, create it:

```powershell
conda create -n agent python=3.10
conda activate agent
pip install -r backend/requirements.txt
```

### 2. Port 8000 or 5173 already in use

Check what is using the port:

```powershell
netstat -ano | findstr :8000
netstat -ano | findstr :5173
```

Then either:
- Kill the process using `taskkill /PID <pid> /F`
- Use a different port: `.\dev.ps1 -Port 9000`

### 3. PowerShell execution policy blocks the script

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Or run with bypass:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\dev.ps1
```

### 4. npm dependencies missing

```powershell
cd frontend
npm install
```

### 5. Backend health check times out

Check if backend started successfully:

```powershell
Get-Content logs/backend.log -Tail 20
```

Common causes:
- Conda environment not activated properly
- Port conflict
- Missing Python dependencies (run `pip install -r backend/requirements.txt`)
- GPU device initialization failure — set `VIDEOMIND_DEVICE=cpu` in `.env`

### 6. Log files growing too large

Clean up old task logs:

```powershell
python scripts/cleanup_storage.py --delete-logs --older-than-days 7
python scripts/cleanup_tasks.py --older-than-days 30 --only-failed
```

### 7. GPU not available, using CPU fallback

Set in `.env`:

```env
VIDEOMIND_DEVICE=cpu
VIDEOMIND_YOLO_DEVICE=cpu
VIDEOMIND_WHISPER_DEVICE=cpu
VIDEOMIND_SAM2_DEVICE=cpu
```

### 8. Upload fails with "File too large"

The default limit is 1024 MB. Increase in `.env`:

```env
VIDEOMIND_MAX_UPLOAD_MB=2048
```

### 9. Queue full error

The default max queue size is 20. Wait for existing tasks to complete, or increase:

```env
VIDEOMIND_MAX_QUEUE_SIZE=40
```

### 10. Disk space warning

Check storage health:

```powershell
python scripts/check_storage.py --local
```

Clean up old files:

```powershell
python scripts/cleanup_storage.py --delete-logs --delete-failed --delete-orphaned --older-than-days 7 --dry-run
# Remove --dry-run to actually delete
```

### 11. Task stuck in "running" state after backend restart

The monitor automatically marks stale running tasks as "failed" on restart.
If not, run:

```powershell
curl -X POST http://127.0.0.1:8000/api/v1/tasks/{task_id}/cancel
```

### 12. Frontend shows "Failed to fetch"

This usually means the backend is not running. Start it:

```powershell
.\dev.ps1 -NoFrontend
```

Or manually:

```powershell
conda activate agent
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 13. Worker heartbeat shows stale workers

If a worker crashes without clean shutdown, its heartbeat remains. The monitor will detect this after `VIDEOMIND_MONITOR_INTERVAL_SEC` seconds and log a warning. Restart the backend to clear stale heartbeats.

### 14. cleanup_storage.py --dry-run shows files, but actual cleanup doesn\'t help

Run with multiple flags:

```powershell
python scripts/cleanup_storage.py --delete-logs --delete-failed --delete-orphaned --max-total-gb 10
```

## Log Locations

| Log | Path |
|-----|------|
| Backend stdout/stderr | `logs/backend.log` |
| Frontend stdout/stderr | `logs/frontend.log` |
| Dev script checks | `logs/dev_startup.log` |
| Per-task logs | `data/task_logs/{task_id}.log` |

## Configuration Reference

See `.env.example` for all configurable options.
