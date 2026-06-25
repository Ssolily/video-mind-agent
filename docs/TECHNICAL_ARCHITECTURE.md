# Technical Architecture

## 1. 项目结构

```text
video-mind-agent/
├── AGENTS.md                          # 项目指令（开发规则）
├── .env.example                       # 环境变量示例
├── README.md                          # 项目说明
├── docs/                              # 文档目录
│   ├── PROJECT_OVERVIEW.md
│   ├── CAPABILITY_MATRIX.md
│   ├── AGENT_ANALYSIS.md
│   ├── USER_SCENARIOS.md
│   └── TECHNICAL_ARCHITECTURE.md
├── scripts/                           # 工具脚本
│   └── check_video_metadata.py
├── backend/                           # 后端（主项目）
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI 入口
│   │   ├── config.py                  # 全局配置
│   │   ├── api/
│   │   │   └── video_api.py           # 所有 API 路由
│   │   ├── agent/                     # Agent 编排层
│   │   │   ├── state.py               # VideoAnalysisState
│   │   │   ├── planner.py             # 规则规划 + 计划验证
│   │   │   ├── executor.py            # 执行器
│   │   │   ├── tools.py               # 工具封装 + TOOL_REGISTRY
│   │   │   └── plan_schema.py         # Pydantic 模型
│   │   └── services/                  # 业务逻辑层
│   │       ├── storage_service.py     # 文件上传与注册
│   │       ├── video_metadata_service.py
│   │       ├── frame_service.py
│   │       ├── scene_service.py
│   │       ├── detection_service.py
│   │       ├── tracking_service.py
│   │       ├── audio_service.py
│   │       ├── subtitle_service.py
│   │       ├── highlight_service.py
│   │       ├── clip_export_service.py
│   │       ├── report_service.py
│   │       ├── visualization_service.py
│   │       ├── sam2_service.py
│   │       ├── task_service.py        # 后台任务管理
│   │       ├── task_store.py          # SQLite 持久化
│   │       └── task_log_service.py    # 事件日志
│   └── tests/                         # 测试
│       ├── test_state.py
│       ├── test_planner.py
│       ├── test_plan_validation.py
│       ├── test_tools_registry.py
│       ├── test_task_store.py
│       ├── test_task_log_service.py
│       └── test_storage_security.py
├── frontend/                          # 前端
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       ├── App.tsx                    # 主状态管理
│       ├── api.ts                     # API 客户端
│       ├── hooks/useDevice.ts         # 设备检测 hook
│       └── layouts/
│           ├── DesktopLayout.tsx
│           └── MobileLayout.tsx
└── data/                              # 运行时数据（不提交）
    ├── raw_videos/
    ├── frames/
    ├── reports/
    ├── audio/
    ├── clips/
    ├── tasks/
    └── app.db
```

## 2. 后端架构

```text
┌──────────────────────────────────────────────────────────────┐
│                        FastAPI Server                         │
│                         main.py                               │
│                                                              │
│  CORS Middleware                                              │
│  Static File Mount (/static/reports)                          │
│  Router: /api/v1/videos/*  (video_api.py)                    │
│  Router: /api/tasks/{id}    (main.py inline)                  │
│  Route: /health             (main.py inline)                  │
└───────────────────────┬──────────────────────────────────────┘
                        │ HTTP Request / Response
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                      API Layer (video_api.py)                 │
│                                                              │
│  职责：参数提取、校验、错误响应、调用 service                 │
│                                                              │
│  路由列表：                                                   │
│  GET    /videos                  → list_videos() (占位)      │
│  POST   /videos/upload          → upload_video()             │
│  POST   /videos/{id}/extract-frames                          │
│  POST   /videos/{id}/detect-scenes                           │
│  POST   /videos/{id}/detect-objects                          │
│  POST   /videos/{id}/track-objects                           │
│  POST   /videos/{id}/transcribe                               │
│  POST   /videos/{id}/recommend-highlights                    │
│  POST   /videos/{id}/export-clips                            │
│  POST   /videos/{id}/agent-run                               │
│  POST   /videos/{id}/analyze                                 │
│  POST   /videos/{id}/visualize-detections                    │
│  POST   /videos/{id}/segment-main-object                     │
│  GET    /videos/{id}/report                                  │
│  GET    /tasks/{id}              → 任务状态查询              │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                      Agent Layer (app/agent/)                 │
│                                                              │
│  task_service.py (后台任务调度)                                │
│  └─ create_task() → 创建任务 → 启动 daemon 线程              │
│  └─ get_task()    → 查询任务（内存 + SQLite）                 │
│  └─ _run_agent()  → 后台执行循环                              │
│                                                              │
│  planner.py (规划 + 验证)                                     │
│  └─ build_plan(user_goal) → 规则匹配 → 工具名称列表           │
│  └─ validate_plan(tool_names) → PlanValidationResult         │
│                                                              │
│  executor.py (执行)                                           │
│  └─ execute_plan() → 验证 → 遍历工具 → 记录日志 → 返回 state  │
│                                                              │
│  tools.py (工具注册表)                                        │
│  └─ TOOL_REGISTRY = {                                         │
│        "metadata": metadata_tool,                              │
│        "extract_frames": extract_frames_tool,                  │
│        "detect_scenes": detect_scenes_tool,                    │
│        "detect_objects": detect_objects_tool,                  │
│        "track_objects": track_objects_tool,                    │
│        "transcribe": transcribe_tool,                          │
│        "recommend_highlights": recommend_highlights_tool,       │
│        "export_clips": export_clips_tool,                      │
│        "generate_report": generate_report_tool,                │
│      }                                                         │
│                                                              │
│  state.py (上下文状态)                                         │
│  └─ VideoAnalysisState dataclass                              │
│                                                              │
│  plan_schema.py (规划模型)                                     │
│  └─ StepPlan, ToolCall, PlanValidationResult                  │
│                                                              │
│  task_store.py (SQLite 持久化)                                 │
│  └─ create_task_record / update_task_record / get_task_record  │
│                                                              │
│  task_log_service.py (事件日志)                                │
│  └─ append_task_event → data/tasks/{id}/events.jsonl          │
└───────────────────────┬──────────────────────────────────────┘
                        │ 工具调用
                        ▼
┌──────────────────────────────────────────────────────────────┐
│                      Service Layer (app/services/)            │
│                                                              │
│  每个 service 独立负责一项视频处理任务                         │
│  工具函数在 tools.py 中封装后调用                              │
│                                                              │
│  service                   输入             输出              │
│  ─────────────────────────────────────────────────────────   │
│  video_metadata_service   video_path      dict (duration...)  │
│  frame_service            video_path, dir  list[frame_dict]   │
│  scene_service            video_path       list[scene_dict]   │
│  detection_service        frames[]         list[detection]    │
│  tracking_service         frames[]         list[tracks]       │
│  audio_service            video_path       str (wav_path)     │
│  subtitle_service         audio_path       list[segment]      │
│  highlight_service        video_id         list[highlight]    │
│  clip_export_service      video_path, hl   dict (paths)       │
│  report_service           video_id         dict (json/md)     │
│  visualization_service    video_id         list[str] (paths)  │
│  sam2_service             video_id         dict (mask/overlay)│
│  storage_service          UploadFile       dict (result)      │
└──────────────────────────────────────────────────────────────┘
```

## 3. 前端架构

```text
┌──────────────────────────────────────────────────────────────┐
│                  React Application (Vite)                     │
│                                                              │
│  main.tsx → 渲染 <App />                                      │
│                                                              │
│  App.tsx (主状态管理)                                          │
│  ├─ state: file, goal, sampleFps, topK                       │
│  ├─ state: pageState (idle|uploading|analyzing|done|error)   │
│  ├─ state: uploadResult, task, report, visResult             │
│  ├─ 函数: handleStart() → 上传 → agent-run → 轮询 → 完成     │
│  ├─ 函数: handleVisualize() → 可视化检测框                    │
│  ├─ 函数: startPoll() → 每 2s 轮询任务状态                   │
│  └─ 根据 useDevice() 选择 DesktopLayout / MobileLayout        │
│                                                              │
│  api.ts (HTTP 客户端)                                         │
│  ├─ uploadVideo(file) → POST /api/v1/videos/upload           │
│  ├─ startAgentRun(...) → POST /.../agent-run                  │
│  ├─ pollTask(taskId)  → GET /api/tasks/{taskId}              │
│  ├─ getReport(videoId) → GET /.../report                     │
│  └─ visualizeDetections(...) → POST /.../visualize-detections │
│                                                              │
│  hooks/useDevice.ts                                           │
│  └─ 检测屏幕宽度 < 768px → isMobile: boolean                 │
│                                                              │
│  layouts/DesktopLayout.tsx (桌面端)                           │
│  ├─ 左侧边栏：上传 / 参数设置 / 操作按钮                      │
│  ├─ 右侧主区域：任务进度 / 报告展示 / 可视化                   │
│  └─ 功能完整的操作体验                                         │
│                                                              │
│  layouts/MobileLayout.tsx (移动端)                            │
│  ├─ 垂直布局：上传区 → 分析中 → 结果区                        │
│  ├─ 简化 UI，适合小屏幕                                       │
│  └─ 关键操作和信息完整展示                                     │
└──────────────────────────────────────────────────────────────┘
```

## 4. 数据流

```text
用户选择文件
    │
    ▼
┌──────────────────┐
│  frontend/App.tsx │── FormData ──→ POST /api/v1/videos/upload
└──────────────────┘                     │
                                         ▼
                               storage_service.save_uploaded_video()
                                    ├─ magic bytes 校验
                                    ├─ uuid 重命名
                                    └─ 保存到 data/raw_videos/{uuid}.mp4
                                         │
                                         ▼
                               返回 video_id + filename + raw_path
                                         │
                                         ▼
┌──────────────────┐
│  App.tsx 收到     │── POST /api/v1/videos/{id}/agent-run?user_goal=...
│  video_id         │
└──────────────────┘       │
                           ▼
                  task_service.create_task()
                      ├─ 生成 task_id
                      ├─ 写入内存缓存 + SQLite
                      └─ 启动 daemon 线程
                           │
                           ▼
                  task_service._run_agent()
                      ├─ planner.build_plan(user_goal)
                      │   └─ 规则匹配 → 工具名称列表
                      ├─ executor.execute_plan()
                      │   ├─ validate_plan() 验证
                      │   └─ 遍历每个工具：
                      │       ├─ TOOL_REGISTRY[name](state)
                      │       ├─ 工具内部调用对应 service
                      │       │   ├─ 读取视频文件
                      │       │   ├─ 处理（OpenCV/YOLO/Whisper/FFmpeg）
                      │       │   └─ 写入 data/ 目录
                      │       ├─ task_log_service 记录事件
                      │       └─ on_step_update 更新进度
                      └─ 返回最终 state
                           │
                           ▼
┌──────────────────┐
│  前端轮询          │── GET /api/tasks/{task_id} (每 2s)
│  App.tsx          │
│  startPoll()      │  ← 返回 status / progress / current_step
└──────────────────┘
                           │
                    status = "success"
                           │
                           ▼
┌──────────────────┐
│  App.tsx          │── GET /api/v1/videos/{id}/report
└──────────────────┘   ← 返回 markdown 文本
                           │
                           ▼
                  桌面/移动端 Layout 展示报告
```

## 5. API 流程详解

### 上传流程

```text
POST /api/v1/videos/upload
    │
    ├─ 1. storage_service._validate_filename(file.filename)
    │      └─ Path().name 剥离路径 → 检查扩展名(.mp4/.mov/.avi)
    │
    ├─ 2. storage_service._check_magic_bytes(file)
    │      └─ 读取前 12 bytes → 检查 MP4(ftyp) 或 AVI(RIFF+AVI )
    │
    ├─ 3. 生成 video_id = uuid.uuid4().hex[:12]
    │      dest_name = f"{video_id}.{detected_ext}"
    │
    ├─ 4. 流式写入 data/raw_videos/{dest_name}
    │      └─ 每 chunk 检查累计大小是否超过 MAX_UPLOAD_BYTES
    │           ├─ 超过 → 删除文件 → 抛出 HTTPException(413)
    │           └─ 未超过 → 继续写入
    │
    ├─ 5. register_video(video_id, raw_path, filename)
    │      └─ 写入 data/video_registry.json
    │
    ├─ 6. get_video_metadata(raw_path)
    │      ├─ ffprobe 优先 → 解析 duration/fps/width/height
    │      └─ OpenCV fallback
    │
    └─ 7. 返回 { video_id, filename, raw_path, status, metadata }
```

### Agent 任务流程

```text
POST /api/v1/videos/{video_id}/agent-run?user_goal=...&sample_fps=2&top_k=5
    │
    ├─ 1. task_service.create_task(video_id, user_goal, ...)
    │      ├─ 生成 task_id (uuid.hex[:12])
    │      ├─ 创建内存 task entry
    │      ├─ task_store.create_task_record(...) → SQLite
    │      └─ 启动 daemon 线程 → _run_agent()
    │
    ├─ 2. 立即返回 { task_id, status: "pending" }
    │
    └─ 3. (后台线程) _run_agent()
           ├─ get_video_path(video_id) → 检查视频是否存在
           ├─ build_plan(user_goal) → 工具名称列表
           ├─ 更新 task 状态为 "running" + 设置初始 result(含 plan)
           ├─ execute_plan(...)
           │   ├─ validate_plan(tool_names)
           │   └─ for each tool:
           │       ├─ log_step_start(task_id, video_id, name)
           │       ├─ try: state = tool_fn(state, **kwargs)
           │       ├─ log_step_success/error
           │       └─ on_step_update(idx, total, name, state)
           │           └─ 更新 task 的 current_step 和 progress
           └─ 更新 task 为 "success" / "completed_with_errors"
```

## 6. 任务执行模型

```text
┌────────────────────────────────────────────────────────┐
│                   任务生命周期                          │
│                                                        │
│  pending → running → success (或 completed_with_errors) │
│             ↓                                          │
│          (各工具串行执行)                                │
│                                                        │
│  进度更新：                                             │
│  0%     →  pending                                      │
│  0%     →  running (plan 已生成)                        │
│  11%    →  metadata (1/9)                               │
│  22%    →  extract_frames (2/9)                         │
│  ...                                                     │
│  100%   →  success / completed_with_errors              │
└────────────────────────────────────────────────────────┘
```

- **并发模型**：每个 task 一个 daemon thread
- **持久化**：每步执行更新内存缓存 + SQLite
- **事件日志**：每步写入 JSONL（含 duration_ms 和 traceback）
- **重启恢复**：重启后内存缓存为空 → 自动从 SQLite 读取

## 7. 产物存储结构

```text
data/
├── raw_videos/
│   └── {video_id}.mp4            # 原始上传文件（uuid 重命名）
├── frames/
│   └── {video_id}/
│       ├── frame_000001.jpg       # sample_fps=2 → 每秒 2 帧
│       ├── frame_000002.jpg
│       └── ...
├── reports/
│   └── {video_id}/
│       ├── metadata.json          # 元信息
│       ├── scenes.json            # 场景检测
│       ├── detections.json        # 目标检测
│       ├── tracks.json            # 跟踪结果
│       ├── class_stats.json       # 类别统计
│       ├── subtitles.json         # 字幕（JSON 格式）
│       ├── subtitles.srt          # 字幕（SRT 格式）
│       ├── highlights.json        # 精彩片段
│       ├── final_report.json      # 最终报告（JSON）
│       ├── final_report.md        # 最终报告（Markdown）
│       ├── pipeline_report.json   # Pipeline 状态
│       ├── pipeline_report.md     # Pipeline 报告
│       ├── vis_frames/            # 可视化帧
│       └── masks/                 # SAM2 分割结果
├── audio/
│   └── {video_id}.wav            # 提取的音频（16kHz 单声道）
├── clips/
│   └── {video_id}/
│       ├── clip_001.mp4           # 精彩片段
│       ├── clip_002.mp4
│       └── highlight.mp4          # 拼接总文件
├── tasks/
│   └── {task_id}/
│       └── events.jsonl           # 任务事件日志
├── video_registry.json            # video_id → 文件路径映射
└── app.db                         # SQLite 任务持久化
```

## 8. 配置体系（`config.py`）

```python
# 所有配置通过环境变量 VIDEOMIND_* 覆盖
DATA_DIR          # → 运行时数据根目录（默认 data/）
MODEL_DIR         # → 模型文件目录（默认项目根目录）
YOLO_MODEL_PATH   # → YOLO 模型路径（默认 yolo11n.pt）
MAX_UPLOAD_MB     # → 上传文件大小限制（默认 500MB）
MAX_VIDEO_DURATION_SEC  # → 视频时长限制（默认 3600s）
MAX_VIDEO_WIDTH   # → 视频宽度限制（默认 0 = 无限制）
MAX_VIDEO_HEIGHT  # → 视频高度限制
MAX_VIDEO_FPS     # → 视频 FPS 限制
MAX_CONCURRENT_TASKS  # → 最大并发任务数（默认 4）
settings.database_url  # → SQLite 路径
settings.debug         # → 调试模式
settings.host / port   # → 服务器地址
```

## 9. 关键设计决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 任务运行 | threading daemon | 轻量、零依赖，无需 Redis/Celery |
| 数据传递 | 文件系统 | 简单可靠，重启不丢失中间产物 |
| 任务持久化 | SQLite | 轻量、零配置，重启后进程恢复 |
| 视频注册表 | JSON 文件 | 简单，单文件，适合小规模 |
| 前端状态管理 | React useState | 简单，无 flux/redux 开销 |
| 前端构建 | Vite | 快速开发体验 |
| YOLO 推理 | CPU only | 无需 GPU，降低使用门槛 |
| 字幕模型 | faster-whisper | 速度快于原版 whisper |
