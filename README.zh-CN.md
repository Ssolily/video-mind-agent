# VideoMind Agent

**视频内容理解与自动剪辑 Agent** — 一个模块化管线，用于接收视频、提取多模态理解（帧、场景、物体、语音、运动）、对高光片段评分、导出剪辑片段并生成结构化报告。

系统采用轻量级 Agent 架构：工具注册模式 + 逐步执行器 + 进程内任务队列 + 双模式规划器（基于规则的确定性模式或通过 DeepSeek 驱动的 LLM 模式）。React + TypeScript 前端提供上传、实时进度、基于时间轴的高光片段浏览和结构化报告查看。

---

## 功能特性

- **多模态视频理解** — 帧提取（FFmpeg）、场景检测（PySceneDetect）、物体检测（YOLOv8）与跟踪（ByteTrack）、语音转录（faster-whisper）、可选 SAM 2 分割
- **高光评分引擎** — 可配置的加权评分（5 个维度：物体、运动、语音、场景、质量），含多样性惩罚和 Top-K 选择
- **自动剪辑导出** — 基于 FFmpeg 从评分高光片段切割视频，支持流式播放
- **双模式规划器** — 基于规则的确定性模式（默认）或基于 DeepSeek 的 LLM 驱动模式
- **进程内任务队列** — 线程异步 Worker，支持取消/重试/超时/进度跟踪，使用 SQLite 存储
- **每任务存储清单** — 使用安全相对路径跟踪生成的文件，用于清理和审计
- **磁盘空间守卫** — 在上传和分析前检查可用空间，低于阈值时返回 507
- **REST API** — 视频上传、任务生命周期管理、统一结果查询、实时进度（SSE）、系统健康、存储状态、任务日志
- **前端界面** — 拖拽上传面板、实时任务进度、视频播放器（含高光时间轴与列表）、报告概览、洞察面板、剪辑播放、任务历史看板、亮/暗系统主题、Toast 通知
- **Docker 支持** — CPU 模式容器，含健康检查和卷挂载
- **CI / 发布** — GitHub Actions、隐私扫描、自动化发布打包（含校验和）

---

## 项目结构

```
├── backend/                      # FastAPI Python 后端
│   ├── requirements.txt          # Python 依赖
│   ├── pytest.ini                # Pytest 配置
│   ├── app/
│   │   ├── api/                  # API 路由定义（视频、任务、系统、健康）
│   │   ├── schemas/              # Pydantic 数据模型
│   │   ├── agent/                # Agent 核心
│   │   │   ├── planner.py        # 计划生成器（规则 + LLM）
│   │   │   ├── executor.py       # 工具链执行器
│   │   │   ├── tools.py          # 工具注册表（9 个工具）
│   │   │   ├── llm_client.py     # DeepSeek API 客户端
│   │   │   ├── plan_schema.py    # Pydantic 模式定义
│   │   │   └── state.py          # 执行状态管理
│   │   ├── services/             # 业务逻辑与处理服务
│   │   │   ├── frame_service.py        # FFmpeg 帧提取
│   │   │   ├── scene_service.py        # PySceneDetect 场景检测
│   │   │   ├── detection_service.py    # YOLO 物体检测
│   │   │   ├── tracking_service.py     # ByteTrack 物体跟踪
│   │   │   ├── subtitle_service.py     # faster-whisper 语音识别
│   │   │   ├── highlight_service.py    # 多维度高光评分
│   │   │   ├── clip_export_service.py  # FFmpeg 剪辑导出
│   │   │   ├── report_service.py       # 结构化 JSON + Markdown 报告
│   │   │   ├── video_metadata_service.py   # ffprobe 元数据提取
│   │   │   ├── video_result_service.py     # 统一结果聚合
│   │   │   ├── media_stream_service.py     # HTTP Range 流式传输
│   │   │   ├── visualization_service.py    # 检测结果可视化
│   │   │   ├── task_queue.py           # 进程内工作队列
│   │   │   ├── task_store.py           # SQLite 任务持久化
│   │   │   ├── task_service.py         # 任务生命周期管理
│   │   │   ├── task_monitor.py         # 定时健康检查
│   │   │   ├── task_log_service.py     # 任务日志管理
│   │   │   ├── task_logger.py          # 按任务文件日志
│   │   │   ├── audio_service.py        # 音频提取
│   │   │   ├── pipeline_service.py     # 完整管线编排
│   │   │   ├── storage_service.py      # 文件上传、校验、磁盘检查
│   │   │   ├── storage_manifest_service.py  # 每任务文件清单
│   │   │   └── sam2_service.py         # （可选）SAM 2 分割
│   │   ├── config.py             # 基于环境变量的集中配置
│   │   └── main.py               # FastAPI 应用入口 + 生命周期管理
│   └── tests/                    # Pytest 测试套件（20 个测试文件）
├── frontend/                     # React + Vite + TypeScript
│   └── src/
│       ├── components/           # React 组件（约 30 个文件）
│       │   ├── history/          # 任务历史看板（筛选、列表、条目、页面）
│       │   ├── report/           # 报告、洞察、剪辑、评分、技术面板
│       │   └── toast/            # Toast 通知提供者与 Hook
│       ├── hooks/                # 自定义 Hook（设备、播放、结果、历史、主题、防抖）
│       ├── layouts/              # 桌面布局与移动布局
│       ├── styles/               # CSS 设计变量、主题覆盖、全局与打印样式
│       ├── types/                # TypeScript 类型定义（视频、播放）
│       ├── utils/                # 工具函数（时间、显示、时间轴、历史、洞察）
│       └── api.ts                # 类型化后端 API 客户端
├── scripts/                      # 工具与自动化脚本
├── docs/                         # 文档
│   ├── DEPLOYMENT.md             # Docker 部署指南
│   ├── HANDOFF_NOTES.md          # 项目交接文档
│   ├── WORKER_RUNTIME.md         # 任务队列、SSE、超时、存储、监控
│   ├── TROUBLESHOOTING.md        # 常见问题与解决
│   ├── RELEASE_PROCESS.md        # 发布流程
│   ├── RELEASE_CHECKLIST.md      # 发布前检查清单
│   └── DEMO_WALKTHROUGH.md       # 演示流程与 UX 指南
├── Dockerfile                    # CPU 模式 Docker 构建
├── docker-compose.yml            # 后端容器服务
├── .dockerignore                 # Docker 构建排除规则
├── .env.example                  # 环境变量模板
├── .env.docker.example           # Docker 环境变量模板
├── environment.yml               # Conda 环境定义
├── dev.ps1                       # Windows 一键启动脚本
├── README.md                     # 本文件（英文）
└── README.zh-CN.md               # 中文版 README
```

> **注意：** 运行时目录 `data/`（视频、帧、音频、剪辑、报告、清单）和 `logs/` 会自动创建，并被版本控制排除。

---

## 快速开始

### 1. 前置条件

- Python 3.10–3.11
- FFmpeg 和 ffprobe 已加入 PATH
- Node.js 18+（用于前端）

### 2. 启动后端

```bash
# 推荐：使用 conda 环境
conda env create -f environment.yml
conda activate agent

# 或创建虚拟环境
python -m venv .venv
.venv\Scripts\activate

# 安装依赖
cd backend && pip install -r requirements.txt && cd ..

# 复制并配置环境变量
copy .env.example .env

# 启动后端
uvicorn app.main:app --reload --port 8000
```

### 3. 启动前端

```bash
cd frontend && npm install && npm run dev
```

前端默认运行在 `http://localhost:5173`，已配置 CORS 连接到后端。

### 4. 验证

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok"}
```

### 5. 一键启动（Windows）

```powershell
.\dev.ps1              # 同时启动后端和前端
.\dev.ps1 -Kill        # 停止所有进程
.\dev.ps1 -NoFrontend  # 仅启动后端
.\dev.ps1 -Production  # 生产模式（无热重载）
```

---

## 配置说明

系统在启动时从环境变量读取配置。将 `.env.example` 复制为 `.env` 后按需调整。

### 必需配置

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `VIDEOMIND_DATA_DIR` | `./data` | 运行时数据目录 |
| `VIDEOMIND_MAX_UPLOAD_MB` | `1024` | 最大上传文件大小（MB） |

### 规划器

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `VIDEOMIND_PLANNER_PROVIDER` | `rule` | 规划器模式：`rule` 或 `llm` |
| `VIDEOMIND_MAX_VIDEO_DURATION_SEC` | `3600` | 最大视频时长（0 = 不限制） |

### LLM（可选 — 仅 LLM 规划器需要）

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `DEEPSEEK_API_KEY` | — | DeepSeek API 密钥（留空使用规则规划器） |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 模型名称 |

### 设备

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `VIDEOMIND_DEVICE` | `auto` | 设备：`auto` → 优先 CUDA，否则 CPU |
| `VIDEOMIND_YOLO_DEVICE` | — | 逐模型覆盖 |
| `VIDEOMIND_WHISPER_DEVICE` | — | 逐模型覆盖 |

### 存储

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `VIDEOMIND_MIN_FREE_DISK_GB` | `5` | 拒绝上传和分析前的最小剩余磁盘空间（GB） |
| `VIDEOMIND_MAX_TASK_STORAGE_MB` | `2048` | 每任务最大存储（MB） |
| `VIDEOMIND_MONITOR_INTERVAL_SEC` | `30` | 监控检查间隔（秒） |

### 任务队列

| 变量 | 默认值 | 说明 |
|----------|---------|-------------|
| `VIDEOMIND_WORKER_CONCURRENCY` | `1` | 并发任务 Worker 数 |
| `VIDEOMIND_MAX_QUEUE_SIZE` | `20` | 最大排队任务数 |
| `VIDEOMIND_TASK_TIMEOUT_SEC` | `3600` | 每任务超时时间（秒） |
| `VIDEOMIND_STEP_TIMEOUT_SEC` | `900` | 每步骤超时时间（秒） |

### 高光评分（可选调优）

参见 `.env.example` 中所有 `VIDEOMIND_HIGHLIGHT_W_*` 权重、多样性惩罚系数、时长约束和最低评分。

---

## API 概览

所有路由以 `/api/v1` 为前缀（除非另有说明）。

| 方法 | 路径 | 说明 |
|--------|------|-------------|
| `GET` | `/health` | 健康检查 |
| `POST` | `/videos/upload` | 上传视频（校验扩展名、魔数、磁盘空间） |
| `GET` | `/videos/{id}/source` | 流式播放源视频（支持 HTTP Range） |
| `GET` | `/videos/{id}/clips/{clip_id}` | 流式播放导出剪辑（支持 Range） |
| `GET` | `/videos/{id}/result` | 统一结果 — 高光、剪辑、报告 URL、状态 |
| `GET` | `/videos/{id}/reports/markdown` | Markdown 报告内容 |
| `GET` | `/videos/{id}/reports/json` | JSON 报告内容（已清理） |
| `GET` | `/videos/{id}/reports/candidates` | 原始高光候选数据 |
| `POST` | `/videos/{id}/agent-run` | 开始分析任务 |
| `POST` | `/videos/{id}/visualize-detections` | 生成检测可视化 |
| `POST` | `/videos/{id}/extract-frames` | 直接 API — 提取帧 |
| `POST` | `/videos/{id}/detect-scenes` | 直接 API — 检测场景 |
| `POST` | `/videos/{id}/detect-objects` | 直接 API — YOLO 检测 |
| `POST` | `/videos/{id}/track-objects` | 直接 API — ByteTrack 跟踪 |
| `POST` | `/videos/{id}/transcribe` | 直接 API — 语音转录 |
| `GET` | `/tasks/{id}`（也支持 `/api/tasks/{id}`） | 轮询任务状态 |
| `GET` | `/tasks/{id}/events` | SSE 任务进度流 |
| `GET` | `/tasks/{id}/logs` | 最近任务日志行 |
| `POST` | `/tasks/{id}/cancel` | 取消运行中/排队中的任务 |
| `POST` | `/tasks/{id}/retry` | 重试失败的任务 |
| `GET` | `/tasks` | 列出任务（筛选：status、video_id、limit、offset） |
| `GET` | `/system/storage` | 存储健康 — 磁盘空间、各类别大小 |
| `GET` | `/q/info` | 队列状态、Worker 心跳、过期任务 |

> **agent-run 查询参数：** `user_goal`、`sample_fps`、`top_k`、`planner_provider`

---

## 测试

### 后端测试

```bash
cd backend && pytest -ra -q
```

### 前端测试

```bash
cd frontend
npm run typecheck      # TypeScript 类型检查
npm run test:run       # Vitest 测试套件
npm run build          # 生产构建
```

### 完整回归测试

```powershell
# Windows
.\scripts\check_all.ps1       # 完整回归套件

# 手动完整检查
python -m compileall backend/app scripts                    # Python 编译检查
cd backend && pytest -ra -q                                 # 后端测试
cd frontend && npm run typecheck && npm run test:run && npm run build  # 前端
```

### 隐私扫描

```bash
python scripts/check_privacy.py             # 默认扫描（期望 0 错误）
python scripts/check_privacy.py --strict    # 严格模式（警告视为失败）
```

---

## 管线概览

上传视频并创建分析任务后，Agent 按顺序执行以下步骤：

```
1. metadata          → ffprobe：时长、帧率、分辨率、帧数
2. extract_frames    → FFmpeg：按可配置帧率采样帧
3. detect_scenes     → PySceneDetect：镜头边界检测
4. detect_objects    → YOLO：每帧物体检测（80 个 COCO 类别）
5. track_objects     → ByteTrack：跨帧物体跟踪
6. transcribe        → faster-whisper：语音转文字 + 时间戳
7. recommend_highlights → 多维度评分 + Top-K 选择
8. export_clips      → FFmpeg：从原始视频切割片段
9. generate_report   → 结构化 JSON + Markdown 报告
```

第 7 步（高光评分）使用可配置的加权公式：

```
base_score = w_object · object_score
           + w_motion · motion_score
           + w_speech · speech_score
           + w_scene  · scene_score
           + w_quality · quality_score

selection_score = base_score - diversity_lambda · overlap_penalty
```

所有权重和多样性惩罚系数均可通过环境变量（`VIDEOMIND_HIGHLIGHT_W_*`）配置。

---

## Agent 架构

Agent 采用轻量级进程内设计（不使用 LangChain 或 CrewAI 等外部框架）：

1. **规划器（Planner）** — 根据用户目标生成有序工具列表。默认为基于规则的确定性全管线模式。如果设置了 `DEEPSEEK_API_KEY` 且 `VIDEOMIND_PLANNER_PROVIDER=llm`，则使用 DeepSeek 动态选择工具。
2. **执行器（Executor）** — 遍历工具列表，依次调用每个工具。跟踪步骤状态（ok/error/skipped）。通过 `on_step_update` 回调报告进度。单步骤失败时继续执行。
3. **工具注册表（Tool Registry）** — `tools.py` 中的 `TOOL_REGISTRY` 字典将工具名称映射到可调用函数。所有工具遵循相同的签名：`fn(video_id, video_path, state, **kwargs)`。
4. **任务队列（Task Queue）** — Python `threading` + `queue.Queue`。Worker 从队列中取出任务，执行管线，更新 SQLite 状态，通过 `cancellation_requested` 标志支持取消。

### Agent 工具链（9 个工具）

| # | 工具 | 服务 | 说明 |
|---|------|---------|-------------|
| 1 | `metadata` | `video_metadata_service` | ffprobe：时长、帧率、分辨率、帧数 |
| 2 | `extract_frames` | `frame_service` | FFmpeg 按可配置帧率采样 |
| 3 | `detect_scenes` | `scene_service` | PySceneDetect 内容感知场景边界 |
| 4 | `detect_objects` | `detection_service` | YOLO 推理采样帧（80 COCO 类别） |
| 5 | `track_objects` | `tracking_service` | ByteTrack：跨帧物体 ID 和轨迹 |
| 6 | `transcribe` | `subtitle_service` | faster-whisper：语音转文字 + 时间戳 |
| 7 | `recommend_highlights` | `highlight_service` | 5 维度评分 + 多样性惩罚 + Top-K |
| 8 | `export_clips` | `clip_export_service` | FFmpeg：从源视频切割片段，保存至 `data/clips/` |
| 9 | `generate_report` | `report_service` | 结构化 JSON 报告 + Markdown 摘要 |

### 存储清单集成

任务创建后，`storage_manifest_service.create_manifest()` 生成 `data/task_manifests/{task_id}.json`。通过 `add_file()` 以相对路径（绝不使用绝对路径）记录生成的文件。状态在整个管线中持续更新。该清单为 `scripts/cleanup_storage.py` 提供可靠的、基于清单的清理能力。

### 磁盘空间守卫

`storage_service.check_disk_space()` 在视频上传前（返回 HTTP 507）和分析任务创建前（返回 HTTP 507）将可用磁盘空间与 `VIDEOMIND_MIN_FREE_DISK_GB` 进行比较。磁盘空间不足的请求不会创建任何任务记录。错误信息对用户友好，不暴露本地绝对路径。

---

## 部署

参见 [部署指南](docs/DEPLOYMENT.md) 了解 Docker 搭建、环境配置和故障排除。

- CPU 默认的 Docker 后端容器
- 基本运行不需要 GPU 或 API 密钥
- 数据持久化在 `data/` 和 `logs/` 卷中

```bash
# 启动
docker compose up -d

# 检查健康
curl http://127.0.0.1:8000/health

# 查看日志
docker compose logs -f backend

# 停止
docker compose down
```

---

## 发布

参见 [发布流程](docs/RELEASE_PROCESS.md) 获取完整说明。

```bash
# 隐私扫描（发布前必须通过）
python scripts/check_privacy.py

# 创建发布包（试运行）
python scripts/make_release.py --dry-run

# 创建发布包（含 zip）
python scripts/make_release.py --zip --check-privacy
```

---

## 文档

| 文档（位于 `docs/`） | 说明 |
|--------------------------|-------------|
| [部署指南](docs/DEPLOYMENT.md) | 本地与 Docker 部署 |
| [Worker 运行时指南](docs/WORKER_RUNTIME.md) | 任务队列、SSE、超时、存储、监控 |
| [故障排除指南](docs/TROUBLESHOOTING.md) | 常见问题与解决方案 |
| [演示流程](docs/DEMO_WALKTHROUGH.md) | 演示流程与 UX 指南 |
| [项目交接文档](docs/HANDOFF_NOTES.md) | 项目概览与开发者入职 |
| [技术架构](docs/TECHNICAL_ARCHITECTURE.md) | 架构概览与设计决策 |
| [发布检查清单](docs/RELEASE_CHECKLIST.md) | 发布前验证 |
| [发布流程](docs/RELEASE_PROCESS.md) | 逐步发布工作流 |

---

## 已知限制

- **长视频处理** — 处理时间随视频长度线性增长；无自适应/场景感知帧采样（使用固定帧率）
- **YOLO 双重推理** — `detect_objects` 和 `track_objects` 分别执行独立的 YOLO 推理，未共享检测结果（tracking 已包含检测结果）
- **线性剪辑导出** — 剪辑独立切割，不支持多轨编辑、转场或合成
- **无多轮反馈** — 管线为单次执行，无高光选择交互式优化循环
- **单用户进程内队列** — 任务队列使用 Python 线程和 SQLite，非分布式系统（无 Redis/Celery），满足本地桌面使用
- **GPU 可选** — 所有模型（YOLO、Whisper、SAM 2）默认在 CPU 上运行；GPU 可用时自动检测
- **模型自动下载** — YOLO 权重在首次使用时下载（需要互联网）
- **Windows 优先** — `dev.ps1` 和辅助脚本主要在 Windows 上测试；Docker 和手动 CLI 命令可跨平台使用

---

## 许可证

本项目仅供教育和研究目的使用。

---

*VideoMind Agent — 视频内容理解与自动剪辑 Agent。*
