# Capability Matrix — Functional Coverage

> 所有结论基于当前代码分析，未臆测、未夸大。

## 说明

- ✅ **已实现**：代码完整实现，可独立调用
- ⚠️ **部分实现**：有基础实现但存在已知缺口
- ❌ **未实现**：代码无相关内容，仅计划或提及
- 所有能力均可在 CPU 上运行（不需要 GPU）

---

## 1. 基础能力

| 能力 | 状态 | 代码位置 | 用户价值 | 备注 |
|------|------|----------|----------|------|
| 视频上传 | ✅ 已实现 | `storage_service.py:save_uploaded_video()` | 上传视频文件 | 支持 mp4/mov/avi，magic bytes 验证 |
| 文件安全处理 | ✅ 已实现 | `storage_service.py:_validate_filename(), _check_magic_bytes()` | 防止恶意文件 | uuid 重命名、路径穿越防护 |
| 视频注册表 | ✅ 已实现 | `storage_service.py:register_video(), get_video_path()` | video_id 到文件路径映射 | 持久化到 video_registry.json |
| 配置管理 | ✅ 已实现 | `config.py` | 集中管理目录/限制/并发参数 | 支持环境变量覆盖 |
| 健康检查 | ✅ 已实现 | `main.py:health()` | API 可用性验证 | 返回 `{"status":"ok"}` |
| 错误处理 | ⚠️ 部分实现 | 各 API 端点 | 返回清晰错误信息 | 有 404/400 异常；无全局异常处理器 |
| 日志 | ✅ 已实现 | `task_log_service.py` | 记录任务执行事件 | JSONL 格式，含 timestamp 和 duration_ms |

## 2. 视频分析能力

| 能力 | 状态 | 代码位置 | 用户价值 | 备注 |
|------|------|----------|----------|------|
| 元信息提取 | ✅ 已实现 | `video_metadata_service.py:get_video_metadata()` | 获取视频基本信息 | ffprobe 优先，OpenCV fallback |
| 抽帧 | ✅ 已实现 | `frame_service.py:extract_frames()` | 提取关键帧 | OpenCV，可配置 sample_fps |
| 场景检测 | ✅ 已实现 | `scene_service.py:detect_scenes()` | 检测镜头切换点 | PySceneDetect ContentDetector |
| 目标检测 | ✅ 已实现 | `detection_service.py:detect_objects_on_frames()` | 识别画面中的物体 | YOLO，confidence ≥ 0.25 |
| 目标跟踪 | ⚠️ 部分实现 | `tracking_service.py:track_objects()` | 跨帧跟踪同一目标 | 仅有 IoU 启发式，无真实 ByteTrack/DeepSORT |
| 类别统计 | ✅ 已实现 | `tracking_service.py:compute_class_statistics()` | 每类目标出现统计 | occurrence count / frame count / avg confidence |
| 语音转文字 | ✅ 已实现 | `audio_service.py:extract_audio()` + `subtitle_service.py:transcribe_audio()` | 识别视频语音 | faster-whisper base model |
| 字幕生成 | ✅ 已实现 | `subtitle_service.py:save_subtitles()` | 输出 SRT 字幕 | 同时输出 JSON 和 SRT |
| 无音频处理 | ✅ 已实现 | `subtitle_service.py:has_audio_stream()` | 无音频视频不报错 | 返回空字幕列表 |
| SAM2 分割 | ⚠️ 部分实现 | `sam2_service.py:segment_main_object()` | 主目标像素级分割 | 可选功能，需要自行安装权重和库 |

## 3. 编辑与导出能力

| 能力 | 状态 | 代码位置 | 用户价值 | 备注 |
|------|------|----------|----------|------|
| 精彩片段推荐 | ✅ 已实现 | `highlight_service.py:recommend_highlights()` | 自动找出视频精彩部分 | 6 维度评分（权重未优化） |
| 候选片段生成 | ✅ 已实现 | `highlight_service.py:_generate_candidates()` | 场景切分成 10-20s 候选 | 滑动窗口策略 |
| 多样性选择 | ✅ 已实现 | `highlight_service.py:_select_top_k()` | 避免推荐重复片段 | 时间重叠惩罚 |
| 剪辑导出 | ✅ 已实现 | `clip_export_service.py:export_clips()` | 导出精彩片段视频 | FFmpeg fast copy |
| 片段拼接 | ✅ 已实现 | `clip_export_service.py:_concat_clips()` | 拼接成 highlight.mp4 | 需 ≥ 2 个 clip |

## 4. 报告与可视化能力

| 能力 | 状态 | 代码位置 | 用户价值 | 备注 |
|------|------|----------|----------|------|
| JSON 报告 | ✅ 已实现 | `report_service.py:generate_report()` | 结构化分析数据 | 含 metadata/scenes/stats/subtitles/highlights |
| Markdown 报告 | ✅ 已实现 | `report_service.py:_render_markdown()` | 人类可读的报告 | 6 个章节：基本信息/场景/检测/字幕/highlight/clip |
| 检测可视化 | ✅ 已实现 | `visualization_service.py:visualize_detections()` | 在帧上画 bbox | OpenCV 绘制 |
| 报告 API | ✅ 已实现 | `video_api.py:get_report_endpoint()` | 前端获取报告 | 同时返回 markdown 文本 |
| LLM 摘要 | ❌ 未实现 | 无 | AI 写报告摘要 | 需要 LLM 集成 |

## 5. Agent 基础能力

| 能力 | 状态 | 代码位置 | 用户价值 | 备注 |
|------|------|----------|----------|------|
| 任务创建 | ✅ 已实现 | `task_service.py:create_task()` | 异步后台分析 | 立即返回 task_id |
| 任务进度 | ✅ 已实现 | `task_service.py:on_step_update()` | 实时查看进度 | progress 0.0~1.0 |
| 任务持久化 | ✅ 已实现 | `task_store.py` | 重启后仍可查 | SQLite + 内存双缓存 |
| 规则 Planner | ✅ 已实现 | `planner.py:build_plan()` | 根据用户目标选工具 | 8 组关键词匹配 |
| 计划验证 | ✅ 已实现 | `planner.py:validate_plan()` | 避免非法工具链 | 工具存在性 + 依赖顺序 + 无重复 |
| 工具注册表 | ✅ 已实现 | `tools.py:TOOL_REGISTRY` | 统一管理和发现工具 | 9 个工具注册 |
| 状态传递 | ✅ 已实现 | `state.py:VideoAnalysisState` | 工具间共享数据 | dataclass，步骤记录 |
| 事件日志 | ✅ 已实现 | `task_log_service.py:append_task_event()` | 每步执行记录 | JSONL 格式 |
| LLM Planner | ❌ 未实现 | `planner.py` 注释 | 语义理解用户目标 | 已预留接口（StepPlan/ToolCall schema） |
| LLM Function Calling | ❌ 未实现 | 无 | 动态决策工具调用 | 无 LLM 调用代码 |
| Reflection/Self-correction | ❌ 未实现 | 无 | 错误后重试或调整 | 线性执行无反馈循环 |
| Human-in-the-loop | ❌ 未实现 | 无 | 用户干预中间结果 | 全自动无确认步骤 |

## 6. 前端能力

| 能力 | 状态 | 代码位置 | 用户价值 | 备注 |
|------|------|----------|----------|------|
| 文件上传 | ✅ 已实现 | `App.tsx` + `api.ts` | 选择视频文件上传 | FormData 提交 |
| 分析目标输入 | ✅ 已实现 | `App.tsx` | 输入分析意图 | 传参给 agent-run API |
| 任务轮询 | ✅ 已实现 | `App.tsx:startPoll()` | 实时查看进度 | 每 2s 轮询 |
| 报告展示 | ✅ 已实现 | `DesktopLayout.tsx`, `MobileLayout.tsx` | 展示分析结果 | Markdown 渲染 + clip 链接 |
| 检测可视化 | ✅ 已实现 | `App.tsx:handleVisualize()` | 展示检测框图片 | 展示前 20 张 |
| 响应式布局 | ✅ 已实现 | `useDevice.ts`, `DesktopLayout.tsx`, `MobileLayout.tsx` | 桌面和移动端 | 768px 断点 |
| 视频播放器 | ❌ 未实现 | 无 | 在网页中播放视频 | 当前只展示文件路径 |
| Timeline 交互 | ❌ 未实现 | 无 | 交互式浏览分析结果 | 无场景/帧时间轴 |
| 历史记录 | ❌ 未实现 | 无 | 查看以前的分析 | 无历史列表页面 |

## 7. 工程与测试

| 能力 | 状态 | 代码位置 | 备注 |
|------|------|----------|------|
| state 测试 | ✅ 已实现 | `tests/test_state.py` | VideoAnalysisState 创建和操作 |
| planner 测试 | ✅ 已实现 | `tests/test_planner.py` | build_plan 关键字匹配 |
| validation 测试 | ✅ 已实现 | `tests/test_plan_validation.py` | 非法工具/依赖/重复校验 |
| tools registry 测试 | ✅ 已实现 | `tests/test_tools_registry.py` | 9 个工具都在且可调用 |
| task store 测试 | ✅ 已实现 | `tests/test_task_store.py` | SQLite CRUD |
| task log 测试 | ✅ 已实现 | `tests/test_task_log_service.py` | JSONL 事件格式 |
| storage security 测试 | ✅ 已实现 | `tests/test_storage_security.py` | 非法扩展名/超大文件/路径穿越 |
| 集成/端到端测试 | ❌ 未实现 | 无 | 无 upload → analyze → report 全流程测试 |
| 性能测试 | ❌ 未实现 | 无 | 无大视频/高并发测试 |
| Lint / Type check | ❌ 未实现 | 无 | 无 ruff/mypy 配置 |
| CI/CD | ❌ 未实现 | 无 | 无 GitHub Actions 等 |

## 8. 部署与安全

| 能力 | 状态 | 代码位置 | 备注 |
|------|------|----------|------|
| 环境变量配置 | ✅ 已实现 | `config.py` + `.env.example` | VIDEOMIND_* 系列 |
| Magic bytes 校验 | ✅ 已实现 | `storage_service.py:_check_magic_bytes()` | MP4/MOV/AVI 文件头 |
| 文件名安全 | ✅ 已实现 | `storage_service.py:_validate_filename()` | 路径穿越防护 + 扩展名白名单 |
| 大小限制 | ✅ 已实现 | `storage_service.py:save_uploaded_video()` | 流式检查 MAX_UPLOAD_BYTES |
| 分辨率限制 | ⚠️ 部分实现 | `config.py:MAX_VIDEO_WIDTH/HEIGHT` | 配置存在但上传时未强制校验 |
| 鉴权 | ❌ 未实现 | 无 | API 完全开放 |
| 速率限制 | ❌ 未实现 | 无 | 无上传/请求频率限制 |
| Docker | ❌ 未实现 | 无 | 无可部署容器配置 |
| HTTPS | ❌ 未实现 | 无 | HTTP only |
