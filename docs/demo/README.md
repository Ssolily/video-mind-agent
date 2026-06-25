# Demo Screenshots & Screencast Guide

## Overview

This directory contains screenshot and screencast materials for the VideoMind Agent demo.

## Screenshot Checklist

| # | Screenshot | Content | Status |
|---|-----------|---------|--------|
| 1 | `01_upload.png` | Frontend page with file picker and parameters | |
| 2 | `02_progress.png` | Analysis pipeline progress with step names | |
| 3 | `03_player_timeline.png` | VideoPlayer + HighlightTimeline with markers | |
| 4 | `04_highlight_list.png` | HighlightList with score breakdown expanded | |
| 5 | `05_clip_playback.png` | Clip playing independently | |
| 6 | `06_markdown_report.png` | Markdown report rendered in browser | |
| 7 | `07_json_report.png` | JSON report in browser | |
| 8 | `08_dev_startup.png` | dev.ps1 startup console output | |

### Naming Convention

- All lowercase
- Two-digit sequence prefix
- Use underscores, not spaces
- Format: `.png`

### How to Take Screenshots

1. Launch the project: `.\dev.ps1`
2. Open `http://127.0.0.1:5173`
3. Use browser DevTools to capture at 1920×1080 (or use Snipping Tool)
4. Avoid capturing personal files, API keys, or environment variables

---

## Screencast Guide

### Recommended Flow (2-3 minutes)

1. **0:00-0:15** — Open terminal, run `.\dev.ps1`
2. **0:15-0:25** — Open browser at `http://127.0.0.1:5173`
3. **0:25-0:35** — Select a video file, click 开始分析
4. **0:35-1:00** — Wait for pipeline execution (fast‑forward if >30s)
5. **1:00-1:20** — Navigate result workspace:
   - VideoPlayer playing
   - Click Timeline → seek
   - Click HighlightList → seek
6. **1:20-1:40** — Switch to Clip mode, play exported clip
7. **1:40-1:50** — Open Markdown report
8. **1:50-2:00** — Open JSON report
9. **2:00-2:10** — Refresh page → data still there
10. **2:10-2:30** — Fade to black with project name

### Naming Convention

```
videomind_demo_YYYYMMDD.mp4
```

### Recording Tips

| Tip | Detail |
|-----|--------|
| Resolution | 1920×1080 or 2560×1440 |
| Frame rate | 30 fps |
| Audio | Optional — use if narrating with script |
| No audio | Acceptable — add subtitle overlay later |
| Tool | OBS Studio, Windows Game Bar, or browser DevTools recorder |

---

## Privacy Checklist

Before sharing screenshots or screencast, verify:

- [ ] No Windows absolute paths visible (`C:\`, `D:\`)
- [ ] No API keys or `.env` values visible
- [ ] No personal video content visible (use public or synthetic video)
- [ ] No terminal output showing environment variables
- [ ] No browser DevTools showing localStorage or cookies
- [ ] No real name or personal information in files

---

## Synthetic Test Video

To generate a quick test video:

```powershell
ffmpeg -y -f lavfi -i testsrc=size=1280x720:rate=30 `
  -f lavfi -i sine=frequency=1000:sample_rate=44100 `
  -t 30 -c:v libx264 -pix_fmt yuv420p -c:a aac `
  data/demo_e2e_test.mp4
```

> This is a synthetic test video with no real content. For a more impressive demo, use a short video clip with visible objects and speech.
