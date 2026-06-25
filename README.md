# VideoMind Agent

**Video content understanding and auto-editing agent** — a modular pipeline that ingests a video, extracts multi-modal understanding (frames, scenes, objects, speech, motion), scores highlight segments, exports clips, and generates structured reports.

The system uses a lightweight Agent architecture: a tool-registry pattern with a step-by-step executor, in-process task queue, and dual-mode planner (rule-based deterministic or LLM-driven via DeepSeek). A React + TypeScript frontend provides upload, live progress, timeline-based highlight review, and structured report viewing.

---

## Features

- **Multi-modal video understanding** — frame extraction (FFmpeg), scene detection (PySceneDetect), object detection (YOLOv8) and tracking (ByteTrack), speech transcription (faster-whisper), optional SAM 2 segmentation
- **Highlight scoring engine** — configurable weighted scoring across 5 dimensions (object, motion, speech, scene, quality) with diversity penalty and top-K selection
- **Auto clip export** — FFmpeg-based segment cutting from scored highlights with streaming playback
- **Dual-mode planner** — rule-based (deterministic, default) or LLM-driven (DeepSeek) tool chain orchestration
- **In-process task queue** — threaded async worker with cancel / retry / timeout / progress tracking, backed by SQLite
- **Per-task storage manifest** — tracks generated files with safe relative paths for cleanup and auditing
- **Disk space guardrail** — checks free space before upload and agent-run, returns 507 if below threshold
- **REST API** — video upload, task lifecycle management, unified result query, real-time progress (SSE), system health, storage status, task logs
- **Frontend** — drag-and-drop upload panel, live task progress, video player with highlight timeline & list, report overview, insight panels, clip playback, task history dashboard, light/dark system theme, toast notifications
- **Docker support** — CPU-mode container with healthcheck and volume mounts
- **CI / Release** — GitHub Actions, privacy scan, automated release packaging with checksum

---

## Project Structure

```
├── backend/                      # FastAPI Python backend
│   ├── requirements.txt          # Python dependencies
│   ├── pytest.ini                # Pytest configuration
│   ├── app/
│   │   ├── api/                  # API route definitions (video, task, system, health)
│   │   ├── schemas/              # Pydantic data models
│   │   ├── agent/                # Agent core
│   │   │   ├── planner.py        # Plan builder (rule + LLM)
│   │   │   ├── executor.py       # Tool chain executor
│   │   │   ├── tools.py          # Tool registry (9 tools)
│   │   │   ├── llm_client.py     # DeepSeek API client
│   │   │   ├── plan_schema.py    # Pydantic schemas
│   │   │   └── state.py          # Execution state
│   │   ├── services/             # Business logic & processing services
│   │   │   ├── frame_service.py        # FFmpeg frame extraction
│   │   │   ├── scene_service.py        # PySceneDetect scene detection
│   │   │   ├── detection_service.py    # YOLO object detection
│   │   │   ├── tracking_service.py     # ByteTrack object tracking
│   │   │   ├── subtitle_service.py     # faster-whisper ASR
│   │   │   ├── highlight_service.py    # Multi-dim highlight scoring
│   │   │   ├── clip_export_service.py  # FFmpeg clip export
│   │   │   ├── report_service.py       # Structured JSON + Markdown report
│   │   │   ├── video_metadata_service.py   # ffprobe metadata extraction
│   │   │   ├── video_result_service.py     # Unified result aggregation
│   │   │   ├── media_stream_service.py     # HTTP Range streaming
│   │   │   ├── visualization_service.py    # Detection visualization
│   │   │   ├── task_queue.py           # In-process worker queue
│   │   │   ├── task_store.py           # SQLite task persistence
│   │   │   ├── task_service.py         # Task lifecycle
│   │   │   ├── task_monitor.py         # Periodic health checks
│   │   │   ├── task_log_service.py     # Task log management
│   │   │   ├── task_logger.py          # Per-task file logging
│   │   │   ├── audio_service.py        # Audio extraction
│   │   │   ├── pipeline_service.py     # Full pipeline orchestration
│   │   │   ├── storage_service.py      # File upload, validation, disk check
│   │   │   ├── storage_manifest_service.py  # Per-task file manifest
│   │   │   └── sam2_service.py         # (Optional) SAM 2 segmentation
│   │   ├── config.py             # Centralized env-based configuration
│   │   └── main.py               # FastAPI app entry + lifespan
│   └── tests/                    # Pytest suite (20 test files)
├── frontend/                     # React + Vite + TypeScript
│   └── src/
│       ├── components/           # React components (~30 files)
│       │   ├── history/          # Task history dashboard (filters, list, item, page)
│       │   ├── report/           # Report, insight, clip, score, technical panels
│       │   └── toast/            # Toast notification provider & hook
│       ├── hooks/                # Custom hooks (device, playback, result, history, theme, debounce)
│       ├── layouts/              # DesktopLayout & MobileLayout
│       ├── styles/               # CSS tokens, theme overrides, global & print styles
│       ├── types/                # TypeScript definitions (video, playback)
│       ├── utils/                # Utility functions (time, display, timeline, history, insights)
│       └── api.ts                # Typed backend API client
├── scripts/                      # Utility & automation scripts
├── docs/                         # Documentation
│   ├── DEPLOYMENT.md             # Docker deployment guide
│   ├── HANDOFF_NOTES.md          # Project handoff documentation
│   ├── WORKER_RUNTIME.md         # Task queue, SSE, timeout, storage, monitoring
│   ├── TROUBLESHOOTING.md        # Common issues & solutions
│   ├── RELEASE_PROCESS.md        # Release workflow
│   ├── RELEASE_CHECKLIST.md      # Pre-release verification
│   └── DEMO_WALKTHROUGH.md       # Demo flow & UX guide
├── Dockerfile                    # CPU-mode Docker build
├── docker-compose.yml            # Backend container service
├── .dockerignore                 # Docker build exclusions
├── .env.example                  # Environment variable template
├── .env.docker.example           # Docker environment template
├── environment.yml               # Conda environment definition
├── dev.ps1                       # Windows one-click startup
└── README.md                     # This file
```

> **Note:** Runtime directories `data/` (videos, frames, audio, clips, reports, manifests) and `logs/` are created automatically and excluded from version control.

---

## Quick Start

### 1. Prerequisites

- Python 3.10–3.11
- FFmpeg and ffprobe in PATH
- Node.js 18+ (for frontend)

### 2. Backend

```bash
# Recommended: conda environment
conda env create -f environment.yml
conda activate agent

# Or create a virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
cd backend && pip install -r requirements.txt && cd ..

# Copy and configure environment
copy .env.example .env

# Start the backend
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend && npm install && npm run dev
```

Frontend runs at `http://localhost:5173` by default, with CORS configured for the backend.

### 4. Verify

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

### 5. One-click start (Windows)

```powershell
.\dev.ps1              # Start both backend and frontend
.\dev.ps1 -Kill        # Stop all processes
.\dev.ps1 -NoFrontend  # Backend only
.\dev.ps1 -Production  # Production mode (no reload)
```

---

## Configuration

Configuration is read from environment variables at startup. Copy `.env.example` to `.env` and adjust as needed.

### Required

| Variable | Default | Description |
|----------|---------|-------------|
| `VIDEOMIND_DATA_DIR` | `./data` | Runtime data directory |
| `VIDEOMIND_MAX_UPLOAD_MB` | `1024` | Max upload file size (MB) |

### Planner

| Variable | Default | Description |
|----------|---------|-------------|
| `VIDEOMIND_PLANNER_PROVIDER` | `rule` | Planner mode: `rule` or `llm` |
| `VIDEOMIND_MAX_VIDEO_DURATION_SEC` | `3600` | Max video duration (0 = no limit) |

### LLM (optional — only needed for LLM planner)

| Variable | Default | Description |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API key (leave empty for rule-based planner) |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | Model name |

### Device

| Variable | Default | Description |
|----------|---------|-------------|
| `VIDEOMIND_DEVICE` | `auto` | Device: `auto` → CUDA if available, else CPU |
| `VIDEOMIND_YOLO_DEVICE` | — | Per-model override |
| `VIDEOMIND_WHISPER_DEVICE` | — | Per-model override |

### Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `VIDEOMIND_MIN_FREE_DISK_GB` | `5` | Minimum free disk before rejecting uploads & agent-runs |
| `VIDEOMIND_MAX_TASK_STORAGE_MB` | `2048` | Max storage per task |
| `VIDEOMIND_MONITOR_INTERVAL_SEC` | `30` | Periodic monitor interval |

### Task Queue

| Variable | Default | Description |
|----------|---------|-------------|
| `VIDEOMIND_WORKER_CONCURRENCY` | `1` | Concurrent task workers |
| `VIDEOMIND_MAX_QUEUE_SIZE` | `20` | Max queued tasks |
| `VIDEOMIND_TASK_TIMEOUT_SEC` | `3600` | Per-task timeout |
| `VIDEOMIND_STEP_TIMEOUT_SEC` | `900` | Per-step timeout |

### Highlight Scoring (optional tuning)

See `.env.example` for all `VIDEOMIND_HIGHLIGHT_W_*` weights, diversity lambda, duration constraints, and minimum score.

---

## API Overview

All routes are prefixed with `/api/v1` unless noted otherwise.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/videos/upload` | Upload video (validates extension, magic bytes, disk space) |
| `GET` | `/videos/{id}/source` | Stream source video (HTTP Range support) |
| `GET` | `/videos/{id}/clips/{clip_id}` | Stream exported clip (Range support) |
| `GET` | `/videos/{id}/result` | Unified result — highlights, clips, report URLs, status |
| `GET` | `/videos/{id}/reports/markdown` | Markdown report content |
| `GET` | `/videos/{id}/reports/json` | JSON report content (sanitized) |
| `GET` | `/videos/{id}/reports/candidates` | Raw highlight candidates |
| `POST` | `/videos/{id}/agent-run` | Start analysis task |
| `POST` | `/videos/{id}/visualize-detections` | Generate detection visualization |
| `POST` | `/videos/{id}/extract-frames` | Direct API — extract frames |
| `POST` | `/videos/{id}/detect-scenes` | Direct API — detect scenes |
| `POST` | `/videos/{id}/detect-objects` | Direct API — YOLO detection |
| `POST` | `/videos/{id}/track-objects` | Direct API — ByteTrack tracking |
| `POST` | `/videos/{id}/transcribe` | Direct API — speech transcription |
| `GET` | `/tasks/{id}` (also at `/api/tasks/{id}`) | Poll task status |
| `GET` | `/tasks/{id}/events` | SSE task progress stream |
| `GET` | `/tasks/{id}/logs` | Recent task log lines |
| `POST` | `/tasks/{id}/cancel` | Cancel a running/queued task |
| `POST` | `/tasks/{id}/retry` | Retry a failed task |
| `GET` | `/tasks` | List tasks (filters: status, video_id, limit, offset) |
| `GET` | `/system/storage` | Storage health — disk space, per-category sizes |
| `GET` | `/q/info` | Queue status, worker heartbeats, stale tasks |

> **agent-run query parameters:** `user_goal`, `sample_fps`, `top_k`, `planner_provider`

---

## Testing

### Backend tests

```bash
cd backend && pytest -ra -q
```

### Frontend tests

```bash
cd frontend
npm run typecheck      # TypeScript type check
npm run test:run       # Vitest test suite
npm run build          # Production build
```

### Full regression

```powershell
# Windows
.\scripts\check_all.ps1       # Full regression suite

# Manual full check
python -m compileall backend/app scripts                    # Python compilation check
cd backend && pytest -ra -q                                 # Backend tests
cd frontend && npm run typecheck && npm run test:run && npm run build  # Frontend
```

### Privacy scan

```bash
python scripts/check_privacy.py             # Default scan (0 errors expected)
python scripts/check_privacy.py --strict    # Stricter mode (warnings → failures)
```

---

## Pipeline Overview

When a video is uploaded and an analysis task is created, the Agent executes these steps in order:

```
1. metadata          → ffprobe: duration, fps, resolution, frame count
2. extract_frames    → FFmpeg: sample frames at configurable fps
3. detect_scenes     → PySceneDetect: shot boundary detection
4. detect_objects    → YOLO: object detection per frame (80 COCO classes)
5. track_objects     → ByteTrack: cross-frame object tracking
6. transcribe        → faster-whisper: speech-to-text + timestamps
7. recommend_highlights → Multi-dimensional scoring + Top-K selection
8. export_clips      → FFmpeg: cut segments from original video
9. generate_report   → Structured JSON + Markdown report
```

Step 7 (highlight scoring) uses a configurable weighted formula:

```
base_score = w_object · object_score
           + w_motion · motion_score
           + w_speech · speech_score
           + w_scene  · scene_score
           + w_quality · quality_score

selection_score = base_score - diversity_lambda · overlap_penalty
```

All weights and the diversity lambda are configurable via environment variables (`VIDEOMIND_HIGHLIGHT_W_*`).

---

## Agent Architecture

The Agent uses a lightweight in-process design (no external frameworks like LangChain or CrewAI):

1. **Planner** — Given a user goal, generates an ordered tool list. Default is rule-based (deterministic full pipeline). If `DEEPSEEK_API_KEY` is set and `VIDEOMIND_PLANNER_PROVIDER=llm`, uses DeepSeek to dynamically select tools.
2. **Executor** — Iterates through the tool list, calling each tool in sequence. Tracks step status (ok/error/skipped). Calls `on_step_update` callback for progress reporting. Continues on individual step failures.
3. **Tool Registry** — `TOOL_REGISTRY` dict in `tools.py` maps tool names to callable functions. All tools follow the same signature: `fn(video_id, video_path, state, **kwargs)`.
4. **Task Queue** — Python `threading` + `queue.Queue`. Workers pick tasks from the queue, execute the pipeline, update SQLite state, and support cancellation via a `cancellation_requested` flag.

### Agent tool chain (9 tools)

| # | Tool | Service | Description |
|---|------|---------|-------------|
| 1 | `metadata` | `video_metadata_service` | ffprobe: duration, fps, resolution, frame count |
| 2 | `extract_frames` | `frame_service` | FFmpeg frame sampling at configurable FPS |
| 3 | `detect_scenes` | `scene_service` | PySceneDetect content-aware scene boundaries |
| 4 | `detect_objects` | `detection_service` | YOLO inference on sampled frames (80 COCO classes) |
| 5 | `track_objects` | `tracking_service` | ByteTrack: cross-frame object IDs and trajectories |
| 6 | `transcribe` | `subtitle_service` | faster-whisper: speech-to-text with word timestamps |
| 7 | `recommend_highlights` | `highlight_service` | 5-dimension scoring + diversity penalty + top-K |
| 8 | `export_clips` | `clip_export_service` | FFmpeg: cut segments from source, save to `data/clips/` |
| 9 | `generate_report` | `report_service` | Structured JSON report + Markdown summary |

### Storage manifest integration

After task creation, `storage_manifest_service.create_manifest()` generates `data/task_manifests/{task_id}.json`. Generated files are recorded as relative paths (never absolute) via `add_file()`. Status is updated throughout the pipeline. The manifest powers `scripts/cleanup_storage.py` for reliable, manifest-aware cleanup.

### Disk space guardrail

`storage_service.check_disk_space()` compares free disk space against `VIDEOMIND_MIN_FREE_DISK_GB` before video upload (returns HTTP 507) and before agent-run creation (returns HTTP 507). Low-disk requests do not create any task record. Error messages are user-friendly and do not expose local absolute paths.

---

## Deployment

See the [Deployment Guide](docs/DEPLOYMENT.md) for Docker setup, environment configuration, and troubleshooting.

- Docker backend container with CPU defaults
- No GPU or API Key required for basic operation
- Data persisted in `data/` and `logs/` volumes

```bash
# Start
docker compose up -d

# Check health
curl http://127.0.0.1:8000/health

# View logs
docker compose logs -f backend

# Stop
docker compose down
```

---

## Release

See [Release Process](docs/RELEASE_PROCESS.md) for full instructions.

```bash
# Privacy check (must pass before release)
python scripts/check_privacy.py

# Create release package (dry-run)
python scripts/make_release.py --dry-run

# Create release package with zip
python scripts/make_release.py --zip --check-privacy
```

---

## Documentation

| Document (in `docs/`) | Description |
|--------------------------|-------------|
| [Deployment Guide](docs/DEPLOYMENT.md) | Local & Docker deployment |
| [Worker Runtime Guide](docs/WORKER_RUNTIME.md) | Task queue, SSE, timeout, storage, monitoring |
| [Troubleshooting Guide](docs/TROUBLESHOOTING.md) | Common issues & solutions |
| [Demo Walkthrough](docs/DEMO_WALKTHROUGH.md) | Demo flow & UX guide |
| [Handoff Notes](docs/HANDOFF_NOTES.md) | Project overview and developer onboarding |
| [Technical Architecture](docs/TECHNICAL_ARCHITECTURE.md) | Architecture overview and design decisions |
| [Release Checklist](docs/RELEASE_CHECKLIST.md) | Pre-release verification |
| [Release Process](docs/RELEASE_PROCESS.md) | Step-by-step release workflow |

---

## Known Limitations

- **Long video processing** — processing time scales linearly with video length; no adaptive/scene-aware frame sampling (uses fixed FPS)
- **YOLO double inference** — `detect_objects` and `track_objects` run separate YOLO passes instead of sharing detection results (tracking already contains detections)
- **Linear clip export** — clips are cut independently; no multi-track editing, transitions, or compositing
- **No multi-turn feedback** — pipeline is single-pass; no interactive refinement loop for highlight selection
- **Single-user, in-process queue** — task queue uses Python threads and SQLite; not a distributed system (no Redis/Celery). Sufficient for local desktop use
- **GPU optional** — all models (YOLO, Whisper, SAM 2) run on CPU by default; GPU auto-detected when available
- **Model auto-download** — YOLO weights download on first use (Internet required)
- **Windows-focused** — `dev.ps1` and helper scripts tested primarily on Windows; Docker and manual CLI commands work cross-platform

---

## License

This project is provided for educational and research purposes.

---

*VideoMind Agent — video content understanding and auto-editing agent.*
