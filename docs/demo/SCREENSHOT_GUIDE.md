# Screenshot Guide — VideoMind Agent

This guide lists screenshots needed for README, portfolio, or graduation materials.

## Screenshot List

### 1. Project Homepage
- **What**: The main page showing the upload form and VideoMind Agent header
- **Why**: First impression — shows UI style and purpose
- **Avoid**: Local file paths in the input, personal files
- **Caption**: "VideoMind Agent — 视频内容理解与自动剪辑 Web 界面"

### 2. Video Upload & Task Running
- **What**: After clicking "开始分析" — showing progress bar, current step, video metadata card
- **Why**: Demonstrates the upload → analyze flow
- **Avoid**: Exposing the local file path of the uploaded video
- **Caption**: "视频上传后自动执行多模态分析 Pipeline"

### 3. Execution Steps
- **What**: The execution result panel with all 9 steps and their status (green checkmarks)
- **Why**: Shows the full pipeline — metadata, frames, scenes, objects, track, transcribe, highlights, clips, report
- **Avoid**: None specific
- **Caption**: "9 步分析任务执行结果"

### 4. VideoPlayer with Timeline
- **What**: The ResultWorkspace showing VideoPlayer with highlight bars on the timeline
- **Why**: Core feature — demonstrates integrated playback and highlight visualization
- **Avoid**: Personal content visible in the video itself
- **Caption**: "视频播放器与 Highlight 时间轴"

### 5. Highlight Timeline Interaction
- **What**: After clicking a highlight bar — video jumps to that time, highlight is active, score shown
- **Why**: Shows interactivity between timeline and playback
- **Caption**: "点击时间轴精彩片段自动跳转播放"

### 6. Highlight List with Scores
- **What**: The HighlightList panel showing multiple highlights with scores, reasons, and score breakdown
- **Why**: Shows scoring transparency — base_score, selection_score, per-dimension breakdown
- **Caption**: "精彩片段列表与多维评分详情"

### 7. Score Breakdown
- **What**: Expanded score breakdown for one highlight — object/motion/speech/scene/quality with raw/weight/weighted
- **Why**: Technical detail — shows the 5-dimension scoring system
- **Caption**: "五维度评分分解 (Object / Motion / Speech / Scene / Quality)"

### 8. Clip Playback Mode
- **What**: VideoPlayer in clip mode with "正在播放: Clip" indicator
- **Why**: Shows clip export and playback capability
- **Caption**: "导出 Clip 独立播放"

### 9. Analysis Report
- **What**: The Markdown report section rendered below the player
- **Why**: Shows structured report generation
- **Avoid**: Long content that makes the screenshot busy
- **Caption**: "结构化分析报告 (Markdown / JSON)"

### 10. Demo Complete Overview
- **What**: A full-page screenshot showing the entire ResultWorkspace (player + timeline + highlights + clips + report)
- **Why**: Summary screenshot for portfolio or README
- **Caption**: "VideoMind Agent 完整分析结果展示"

## Recommended Screenshot Order for README

1. Homepage (1)
2. Pipeline steps (3)
3. Player + Timeline (4)
4. Highlight list with scores (6)
5. Clip playback (8)
6. Report (9)

## Screenshot Order for Portfolio/Thesis

1. Homepage (1)
2. Pipeline steps (3)
3. Player + Timeline (4)
4. Timeline interaction (5)
5. Score breakdown (7)
6. Highlight list (6)
7. Clip playback (8)
8. Report (9)
9. Full overview (10)

## Tips

- Use a clean demo video (no copyrighted or private content)
- Set browser zoom to 100% for consistent screenshots
- Use browser dev tools to hide any console errors or warnings
- Crop screenshots to show only the relevant area
- Use consistent image width across screenshots
- Save as PNG or WebP for quality
- File naming suggestion: `screenshot_01_homepage.png`, `screenshot_02_pipeline.png`, etc.

## What NOT to Show in Screenshots

- ❌ Windows local absolute paths (`D:\...`, `C:\...`)
- ❌ API Keys or environment variables
- ❌ Personal or copyrighted video content
- ❌ Browser console errors
- ❌ Terminal windows with command history
- ❌ File explorer showing project directory structure with full paths
