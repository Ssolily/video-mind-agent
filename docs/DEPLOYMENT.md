# Deployment Guide

## Overview

VideoMind Agent supports two deployment modes:

1. **Local (Windows)** — direct Python + Node.js runtime (recommended for development)
2. **Docker** — containerized backend (recommended for deployment and evaluation)

## Local Windows Deployment

### Prerequisites

- Windows 10/11 with PowerShell 7+
- Conda (Miniconda or Anaconda) Python 3.10
- Node.js 18+ and npm
- FFmpeg (must be available in PATH)

### Quick Start

```powershell
# One-command start (backend + frontend)
.\dev.ps1

# Backend only
.\dev.ps1 -NoFrontend

# Use specific port
.\dev.ps1 -Port 9000

# Production mode (build frontend + preview)
.\dev.ps1 -Production

# Stop processes
.\dev.ps1 -Kill
```

### Manual Start

```powershell
# Backend
conda activate agent
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (separate terminal)
cd frontend
npm run dev
```

### Verification

- Backend health: http://127.0.0.1:8000/health
- Frontend: http://127.0.0.1:5173

## Docker Deployment

### Prerequisites

- Docker Desktop for Windows 4.x+
- WSL2 backend enabled (Docker Desktop settings)
- At least 4 GB RAM allocated to Docker
- At least 10 GB free disk space

### Quick Start

```powershell
# Step 1: Start backend
.\scripts\docker_up.ps1

# Step 2: Check status
.\scripts\docker_check.ps1

# Step 3: View logs
.\scripts\docker_logs.ps1

# Step 4: Stop
.\scripts\docker_down.ps1
```

### Manual Docker Commands

```powershell
# Build and start
docker compose up -d --build

# Check status
docker compose ps

# View logs
docker compose logs -f backend

# Health check
curl http://127.0.0.1:8000/health

# Stop
docker compose down
```

### Configuration

Copy the environment template and edit:

```powershell
Copy-Item .env.docker.example .env.docker
notepad .env.docker
```

Key settings:

| Variable | Default | Description |
|----------|---------|-------------|
| VIDEOMIND_DEVICE | cpu | Device mode: cpu, cuda, or auto |
| VIDEOMIND_PLANNER_PROVIDER | rule | Planner: rule or deepseek |
| DEEPSEEK_API_KEY | (empty) | API key for DeepSeek LLM planner |
| VIDEOMIND_MAX_UPLOAD_MB | 1024 | Max upload file size in MB |
| VIDEOMIND_MIN_FREE_DISK_GB | 5 | Min free disk space before rejecting tasks |

### Volumes

| Host Path | Container Path | Purpose |
|-----------|---------------|---------|
| ./data | /app/data | Video files, clips, reports, database |
| ./logs | /app/logs | Backend logs |

### Health Check

The backend exposes a health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:
```json
{"status": "ok"}
```

### Frontend Access

The Docker image currently packages only the backend.
To use the frontend, run it locally:

```powershell
cd frontend
npm run dev
```

Then configure `VITE_API_BASE_URL` in `frontend/.env`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

The frontend will be available at http://127.0.0.1:5173.

### GPU Docker (Optional)

To enable GPU acceleration:

1. Install [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html)
2. Uncomment the `deploy` section in `docker-compose.yml`
3. Set `VIDEOMIND_DEVICE=cuda` in `.env.docker`

Note: GPU Docker is not required for basic functionality.
The CPU mode works for small to medium videos (up to ~10 minutes).

### Architecture Notes

- **Task Queue**: In-process (no Redis/Celery required)
- **Database**: SQLite (no external database required)
- **Planner**: Rule-based by default (no API key required)
- **GPU**: Optional, CPU-only works for demo purposes

## Troubleshooting

### Docker not available

```powershell
# Install Docker Desktop for Windows
# https://docs.docker.com/desktop/setup/install/windows-install/
```

### Port 8000 already in use

```powershell
# Find the process
netstat -ano | findstr :8000
# Stop it
taskkill /PID <PID> /F
```

### .env.docker missing

The `docker_up.ps1` script creates `.env.docker` automatically from `.env.docker.example`.
If you prefer manual setup:

```powershell
Copy-Item .env.docker.example .env.docker
```

### Health check failing

```powershell
# Check if container is running
docker compose ps

# View recent logs
docker compose logs --tail 50 backend

# Common causes:
# - Still building on first run (wait 2-3 minutes)
# - Port conflict (8000 already in use)
# - Missing dependencies (check logs for ImportError)
```

### FFmpeg errors inside Docker

FFmpeg is pre-installed in the Docker image. If you see FFmpeg-related errors:

```powershell
# Check ffmpeg inside container
docker compose exec backend ffmpeg -version
```

### Disk space errors

```powershell
# Check host disk usage
python scripts/check_storage.py --local

# Clean up old data
python scripts/cleanup_storage.py --delete-logs --delete-failed --older-than-days 7 --dry-run
# Remove --dry-run to actually delete
```

### Permissions issues (Linux/Mac)

If you encounter permission errors on data/logs directories:

```bash
sudo chown -R 1000:1000 data logs
```

## Upgrade Notes

- Docker images are built locally (no registry). Rebuild with `docker compose build --no-cache` after pulling new code.
- The SQLite database persists in the `data/` volume. To reset, delete `data/app.db`.
- The `data/` and `logs/` directories are shared between host and container.
