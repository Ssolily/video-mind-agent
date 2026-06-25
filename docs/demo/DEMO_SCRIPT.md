# Demo Script — VideoMind Agent

## 1. Demo Goal

Showcase the complete VideoMind Agent workflow: upload → analysis → highlights → clip playback → report.

## 2. Prerequisites

- [ ] Conda env `agent` exists (`conda env list`)
- [ ] Frontend deps installed (`cd frontend && npm install`)
- [ ] `.env` configured (copy `.env.example` if needed)
- [ ] FFmpeg available (`ffmpeg -version`)
- [ ] A short test video ready (`.mp4`, 30-120 seconds, < 50 MB)

## 3. Start the Project

```powershell
cd D:\Agent\video-mind-agent
.\dev.ps1
```

Expected:
- Two new PowerShell windows: "VideoMind Backend" and "VideoMind Frontend"
- Backend health check passes within 20 seconds
- Terminal shows: `Backend healthy`, access URLs

If not using `dev.ps1`:
```powershell
# Terminal 1 — Backend
conda activate agent
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

## 4. Open the Application

1. Open browser to `http://127.0.0.1:5173`
2. You should see the "VideoMind Agent" header with upload form

## 5. Upload a Video

1. Click file input, select your test video (`.mp4`, `.mov`, or `.avi`)
2. Set **抽帧 FPS** to `1` (default)
3. Set **推荐数** to `5`
4. Leave **分析目标** as "分析视频" (or type "检测物体、字幕、生成报告")
5. Click **开始分析**

Expected:
- Button changes to "上传中..." then "分析中..."
- Progress bar appears with current step name
- Video metadata card appears (duration, resolution, FPS)

## 6. Wait for Task Completion

- Pipeline runs 9 steps: metadata → extract_frames → detect_scenes → detect_objects → track_objects → transcribe → recommend_highlights → export_clips → generate_report
- Each step appears in the execution result panel
- Expected duration: ~30-180s depending on video length and hardware

**If it takes too long:**
- Use a shorter video (15-30 seconds)
- Check `logs/backend.log` for errors
- Try a video with simpler content

## 7. View Analysis Results

After completion ("done" state), the **ResultWorkspace** loads with:

- **VideoPlayer** displaying the original video
- **HighlightTimeline** showing scored segments
- **HighlightList** with scores and reasons
- **ScoreBreakdown** per dimension
- **Report** section with Markdown and JSON links

## 8. Play Original Video

1. Click the **播放** button or click on the timeline
2. Video plays in the VideoPlayer
3. Seekbar and timeline are synchronized

## 9. Click Highlight Timeline

1. Click a highlight bar in the timeline
2. Video jumps to that highlight's start_time
3. HighlightList highlights the active item
4. Score breakdown shows for the selected highlight

**If timeline doesn't respond:** Check browser console for errors. Ensure Result API returned highlights with valid start/end times.

## 10. Play Exported Clip

1. Click a clip entry in the Clip list
2. VideoPlayer switches to clip mode (status indicator shows "Clip" vs "Source")
3. Clip plays with correct boundaries
4. Click "返回原视频" to switch back

**If clip doesn't play:**
- Check `backend.log` for clip export errors
- Verify clip file exists in `data/clips/`
- Ensure export-clips step completed successfully

## 11. View Report

Scroll to the **分析报告** section:
- Click "JSON 报告" to view structured data
- Click "Markdown 报告" to view formatted report
- Both open in new tabs

## 12. Common Demo Failure Scenarios

| Problem | Likely Cause | Recovery |
|---------|-------------|----------|
| Backend won't start | Port 8000 in use | `.\dev.ps1 -Kill` or `.\dev.ps1 -Port 9000` |
| Frontend won't start | npm not installed | Run `cd frontend && npm install` |
| Upload fails | File too large or unsupported format | Use .mp4 < 500MB |
| Pipeline stuck | Missing frames or detection error | Check `logs/backend.log` |
| Player shows nothing | Media file path issue | Check Result API source_url |
| Black video in player | Missing video codec | Use H.264 encoded .mp4 |
| No highlights | Recommend_highlights step failed | Check execution result panel |
| No clips | Export_clips step failed | Check clip_count in Result API |

**Fallback statement for demo:**
> "The pipeline completed most steps. The highlight and clip export modules depend on video content complexity and FFmpeg availability. For best results, use a video with clear scene changes, people, or speech."
