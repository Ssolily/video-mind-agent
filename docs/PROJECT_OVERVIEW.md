# VideoMind Agent — Project Overview

> **一句话**：上传一段视频，系统自动分析视频内容（场景、人物、物体、字幕），找出精彩片段并生成结构化报告和剪辑视频。

---

## 1. 项目定位

VideoMind Agent 是一个**视频内容理解与自动编辑系统**，后端用 FastAPI 搭建，前端用 React + TypeScript。

当前定位：**具备 Agent 架构外壳的规则驱动自动化视频分析系统**。

未来方向：升级为 LLM 驱动的多模态理解 Agent。

## 2. 当前核心能力

| 能力 | 说明 | 成熟度 |
|------|------|--------|
| 视频上传 | 支持 mp4/mov/avi，magic bytes 校验，uuid 重命名 | ✅ 可用 |
| 元信息提取 | duration、fps、width、height、frame_count | ✅ 可用 |
| 抽帧 | 按可配置 fps 抽取关键帧（OpenCV） | ✅ 可用 |
| 场景检测 | PySceneDetect 检测镜头切换点 | ✅ 可用 |
| 目标检测 | YOLO 目标检测，confidence ≥ 0.25 | ✅ 可用 |
| 目标跟踪 | 类 IoU 启发式跨帧跟踪 | ⚠️ 部分可用（无真实 ByteTrack） |
| 语音转文字 | FFmpeg 提取音频 + faster-whisper 识别 | ✅ 可用（CPU 较慢） |
| 精彩片段推荐 | 多维度评分（object/motion/speech/scene/quality） | ✅ 可用（权重未优化） |
| 剪辑导出 | FFmpeg fast copy 裁剪 + 拼接 | ✅ 可用 |
| 报告生成 | Markdown + JSON 结构化报告 | ✅ 可用 |
| 可视化检测框 | 在帧上绘制 bbox | ✅ 可用 |
| SAM2 分割 | 主目标像素级分割 | ⚠️ 可选（需自行安装权重） |
| 任务进度查询 | 后台任务轮询 + SQLite 持久化 | ✅ 可用 |
| 前端界面 | 上传 / 分析 / 查看报告 | ✅ 可用（简洁版） |

## 3. 适合谁用

| 用户类型 | 使用方式 | 价值 |
|----------|----------|------|
| **视频创作者** | 上传视频 → 系统自动找精彩片段 → 导出 clip | 节省手动浏览和剪辑时间 |
| **视频运营** | 上传视频 → 获取结构化分析报告 | 辅助内容审核和运营决策 |
| **视频分析师** | 批量分析 → 获得 scene/detection/subtitle 数据 | 免手动标注 |
| **开发者** | 研究 Agent 架构、视频处理管线编排 | 参考实现模板 |
| **数据隐私关注者** | 完全本地运行（YOLO + Whisper 均本地） | 数据不离开本地 |

## 4. 核心流程

```text
用户上传视频
    │
    ▼
storage_service 保存到 data/raw_videos/
    │ 返回 video_id
    ▼
任务创建（后台 daemon 线程）
    │
    ▼
planner 根据 user_goal 生成工具链（规则匹配）
    │ 例如 ["metadata", "extract_frames", "detect_scenes", ...]
    ▼
executor 串行执行 9 个工具：
    ├─ metadata          → data/reports/{id}/metadata.json
    ├─ extract_frames    → data/frames/{id}/frame_*.jpg
    ├─ detect_scenes     → data/reports/{id}/scenes.json
    ├─ detect_objects    → data/reports/{id}/detections.json
    ├─ track_objects     → data/reports/{id}/tracks.json + class_stats.json
    ├─ transcribe        → data/reports/{id}/subtitles.json + .srt
    ├─ recommend_highlights → data/reports/{id}/highlights.json
    ├─ export_clips      → data/clips/{id}/clip_*.mp4 + highlight.mp4
    └─ generate_report   → data/reports/{id}/final_report.json + .md
    │
    ▼
前端轮询 /api/tasks/{task_id} 获取进度
    │
    ▼
完成后 GET /api/v1/videos/{id}/report 展示结果
```

## 5. 技术栈

| 层 | 技术 |
|----|------|
| 前端框架 | React 19 + TypeScript + Vite |
| 后端框架 | Python 3.10+ + FastAPI |
| 视频处理 | OpenCV, FFmpeg, PySceneDetect |
| 目标检测 | Ultralytics YOLO (yolo11n.pt, CPU) |
| 语音识别 | faster-whisper (base model, CPU) |
| 图像分割 | SAM2（可选，需自行安装） |
| 数据存储 | 文件系统 + SQLite |
| 任务调度 | Python threading (daemon) |
| 测试 | pytest + pytest-asyncio |

## 6. 当前限制

### 架构限制
- ❌ **不是真正 LLM Agent** — 无 LLM、无推理、无 prompt
- ❌ **无动态重规划** — 线性执行，无 observe → think → re-plan 循环
- ❌ **无消息队列** — daemon thread 重启即丢失运行中任务
- ❌ **无并发控制** — MAX_CONCURRENT_TASKS 配置存在但未强校验

### 功能限制
- ❌ **用户意图理解有限** — planner 只支持 8 组关键词匹配
- ❌ **大视频性能差** — OpenCV 逐帧读取 + CPU 推理
- ❌ **跟踪算法简单** — 只做了 IoU 启发式
- ❌ **评分权重未优化** — 直觉数值，未经过数据驱动调参

### 工程限制
- ❌ **无可部署配置** — 无 Dockerfile
- ❌ **无鉴权** — API 完全开放
- ❌ **无集成测试** — 仅 66 个单元测试
- ❌ **前端 UI 简陋** — 无视频播放器、无交互式 timeline

## 7. 路线图

### 近期（Demo 可用）
1. 调整 highlight 评分权重（实际视频测试）
2. 前端加视频播放器 + timeline
3. 一键启动脚本
4. README 补充演示截图

### 中期（作品集 / 毕业设计）
1. 集成真实 LLM（OpenAI / Ollama），升级 planner
2. 端到端集成测试
3. 规则 vs LLM 对比实验
4. 大视频采样优化

### 远期（产品化）
1. Docker 部署（Dockerfile + docker-compose）
2. 用户认证 + API 鉴权
3. Celery + Redis 消息队列
4. 前端全面重构（Tailwind + 响应式 + 交互式）
5. 评分权重数据驱动优化
