# Handoff Notes — VideoMind Agent

## 1. Project Status

| Area | Status |
|------|--------|
| Backend tests | 380 passed, 0 failed |
| Frontend tests | 275 passed, 0 failed |
| Frontend typecheck | 0 errors |
| Frontend build | Success |
| Demo walkthrough | Verified |

## 2. Completed Modules

| Module | Description |
|--------|-------------|
| Video Upload | Accept .mp4/.mov/.webm/.avi/.m4v, up to 500MB |
| Video Metadata | Duration, FPS, resolution, frame count via ffprobe |
| Frame Extraction | Configurable FPS, OpenCV-based |
| Scene Detection | PySceneDetect ContentDetector |
| Object Detection | YOLO (ultralytics), configurable model |
| Object Tracking | ByteTrack-based |
| Speech-to-Text | faster-whisper |
| Highlight Scoring | 5-dimension weighted scoring |
| Clip Export | FFmpeg-based, no re-encode |
| Report Generation | Markdown + JSON |
| Media Streaming | HTTP Range 206 support for source and clips |
| Unified Result API | `/api/v1/videos/{id}/result` |
| Video Player | Native HTML5 player with interval controls |
| Highlight Timeline | Visual timeline with overlap priorities |
| Highlight List | Score listing with breakdown |
| ResultWorkspace | Orchestrates player + timeline + list |
| Windows Startup | `dev.ps1` with port check, PID management |
| Highlight Evaluation | CLI scripts for batch experiment and paper tables |
| Privacy Check | Script to detect local paths and sensitive data |

## 3. Core Directory Structure

```
backend/
  app/
    main.py              # FastAPI entry point
    config.py            # Configuration (env vars)
    api/
      video_api.py       # All API routes
    services/
      storage_service.py        # File storage paths
      video_metadata_service.py # ffprobe wrapper
      media_stream_service.py   # HTTP Range streaming
      video_result_service.py   # Result API aggregation
      highlight_service.py      # Highlight scoring algorithm
      clip_export_service.py    # FFmpeg clip export
      report_service.py         # Report generation
      task_service.py           # Task state management
    agent/
      planner.py          # LLM-first, rule-fallback planner
      llm_client.py       # DeepSeek API client
      executor.py         # Plan executor
      tools.py            # Tool definitions (YOLO, Whisper, etc.)
    models/
      task.py             # Task/result data models
    schemas/
      video_schemas.py    # Pydantic response models
  tests/                  # 380 tests
frontend/
  src/
    App.tsx               # Main app state + dispatch
    api.ts                # API client + types
    components/
      VideoPlayer.tsx
      HighlightTimeline.tsx
      HighlightList.tsx
      ScoreBreakdown.tsx
      ResultWorkspace.tsx
    layouts/
      DesktopLayout.tsx
      MobileLayout.tsx
    hooks/
      useClipPlayer.ts
      useVideoPlayer.ts
    types/
      video.ts
data/                     # Runtime data (gitignored)
  raw_videos/
  clips/
  reports/
docs/
  demo/                   # Demo materials
  portfolio/              # Graduation/portfolio docs
  HANDOFF_NOTES.md         # This file
  ROADMAP_FINAL.md         # Project roadmap
scripts/                  # Utility scripts
```

## 4. Backend Service Dependencies

```
upload → storage_service
agent-run → task_service → planner → executor → (tools)
  metadata      → video_metadata_service
  extract_frames  → OpenCV
  detect_scenes   → PySceneDetect
  detect_objects  → YOLO (ultralytics)
  track_objects   → ByteTrack
  transcribe      → faster-whisper
  recommend_highlights → highlight_service
  export_clips    → clip_export_service
  generate_report → report_service
result API       → video_result_service + media_stream_service
```

## 5. Frontend Data Flow

```
App.tsx (state machine: idle → uploading → analyzing → done → error)
  └─ DesktopLayout.tsx / MobileLayout.tsx
       ├─ Upload form + Video metadata
       ├─ Progress bar + Executions steps
       └─ ResultWorkspace.tsx (shown when done)
            ├─ VideoPlayer.tsx (source / clip modes)
            ├─ HighlightTimeline.tsx
            ├─ HighlightList.tsx + ScoreBreakdown.tsx
            └─ Report section (Markdown + JSON links)
```

## 6. Key Scripts

| Script | Purpose |
|--------|---------|
| `dev.ps1` | Windows one-click startup |
| `scripts/check_all.ps1` | Full regression check |
| `scripts/verify_mvp_delivery.py` | Delivery acceptance verification |
| `scripts/check_experiment_privacy.py` | Privacy leak detection |
| `scripts/evaluate_highlights.py` | Single-video highlight evaluation |
| `scripts/run_highlight_eval_batch.py` | Batch highlight evaluation |
| `scripts/create_label_template.py` | Label template generation |

## 7. Common Commands

```powershell
# Start
.\dev.ps1

# Stop
.\dev.ps1 -Kill

# Backend only
.\dev.ps1 -NoFrontend

# Run backend tests
cd backend
python -m pytest -ra -q

# Run frontend tests
cd frontend
npm run typecheck && npm run test:run && npm run build

# Full regression
.\scripts\check_all.ps1

# Verify delivery
python scripts/verify_mvp_delivery.py --video-id <id>

# Privacy check
python scripts/check_experiment_privacy.py --root . --include-json --include-md
```

## 8. Known Limitations

- Windows-specific — no Linux/Mac startup script
- No user authentication — single-user system
- No async task queue — long videos block the process
- No Docker deployment
- Clip export requires FFmpeg
- GPU acceleration is optional and auto-detected
- Frontend is desktop-first, mobile layout is minimal
- No i18n — UI is Chinese/English mixed
- No WebSocket — task polling uses HTTP interval

## 9. Suggested Next Steps

1. Real video experiments (8-12 videos, 7 categories)
2. Docker deployment (CPU-only first, GPU optional)
3. WebSocket or SSE for real-time task progress
4. i18n (English-only mode)
5. User authentication for multi-user scenarios
6. Async task queue (Celery + Redis) for production

## 10. Modules NOT to Change Lightly

- **Highlight scoring** (`highlight_service.py`) — affects all result quality
- **Clip export** (`clip_export_service.py`) — tightly coupled with FFmpeg
- **Media streaming** (`media_stream_service.py`) — Range 206 is browser-essential
- **Result API** (`video_result_service.py`) — frontend contract
- **Planner** (`planner.py` + `llm_client.py`) — affects all analysis flow
- **Frontend API types** (`api.ts`, `types/video.ts`) — shared with backend contract
