# Demo Checklist — VideoMind Agent

Use this checklist before, during, and after a demo to ensure everything is ready.

## Before Demo

### Environment
- [ ] Conda installed: `conda --version`
- [ ] Agent env exists: `conda env list | findstr agent`
- [ ] Node.js installed: `node --version`
- [ ] npm installed: `npm --version`
- [ ] FFmpeg installed: `ffmpeg -version`
- [ ] ffprobe installed: `ffprobe -version`

### Configuration
- [ ] `.env` exists (or copied from `.env.example`)
- [ ] No real API keys exposed in docs or terminal
- [ ] Frontend dependencies: `cd frontend && npm install`
- [ ] Backend compile check: `python -m compileall backend/app`

### Project State
- [ ] Backend tests pass: `cd backend && pytest -ra -q`
- [ ] Frontend typecheck: `cd frontend && npm run typecheck`
- [ ] Frontend build: `cd frontend && npm run build`

### Test Video
- [ ] Video file ready (`.mp4`, H.264, < 100 MB, 30-120 seconds)
- [ ] Video path contains no special characters or spaces (optional but recommended)

## During Demo — Startup

- [ ] Run `.\dev.ps1` or manual start
- [ ] Backend window opens without errors
- [ ] Frontend window opens without errors
- [ ] Backend healthy: `curl http://127.0.0.1:8000/health` or check health output
- [ ] Frontend loads at `http://127.0.0.1:5173`

## During Demo — Upload & Analysis

- [ ] File input accepts video
- [ ] Upload completes (get video_id)
- [ ] Task starts (status changes to "analyzing")
- [ ] Progress bar advances
- [ ] Steps appear in execution result panel
- [ ] Task completes (status changes to "done")
- [ ] ResultWorkspace renders

## During Demo — Playback

- [ ] VideoPlayer shows video
- [ ] Play/pause works
- [ ] Timeline shows highlights
- [ ] Click highlight → video jumps to time
- [ ] Clip playback works
- [ ] Source/Clip toggle works
- [ ] Seekbar responds

## During Demo — Report

- [ ] Markdown report renders
- [ ] JSON report link opens
- [ ] Markdown report link opens
- [ ] No data leaks visible in report

## After Demo

- [ ] Run `.\dev.ps1 -Kill` to stop services
- [ ] Close browser tabs
- [ ] Clear terminal output if credentials were visible (they shouldn't be)
- [ ] Check logs: `logs/backend.log` and `logs/frontend.log` for any issues to fix

## Privacy Check (Optional but Recommended)

```powershell
python scripts/check_experiment_privacy.py --root docs --include-md
python scripts/check_experiment_privacy.py --root . --include-md --include-json
```

Ensure no Windows absolute paths, API keys, or email addresses are exposed.
