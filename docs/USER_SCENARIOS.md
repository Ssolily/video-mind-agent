# User Scenarios — 使用场景

> 以下场景均基于当前代码的真实能力，未夸大。

---

## 场景一：上传视频并自动分析

### 用户
vlog 创作者，刚拍完一段 30 分钟的旅行视频

### 输入
- 视频文件（mp4, 30 分钟, 4K）
- 分析目标：「分析视频」

### 系统行为
1. 上传视频到 `data/raw_videos/`
2. 创建后台任务，调用 `build_plan("分析视频")`
3. 由于「分析视频」没有匹配任何关键词，调用全 pipeline（9 个工具）
4. 9 步串行执行，每步更新进度

### 输出
- API 返回 `task_id` + `status: "pending"`
- 前端每 2 秒轮询，显示当前步骤和进度百分比
- 完成后展示 6 个章节的报告：
  1. 视频基本信息（duration / resolution / fps）
  2. 场景时间轴（场景列表及起止时间）
  3. 目标检测统计（person / car / chair 等出现次数）
  4. 字幕摘要（语音识别结果）
  5. 精彩片段推荐（top 5 片段，含评分和理由）
  6. 导出剪辑（clip 文件列表 + highlight.mp4）

### 限制
- 全 pipeline 在 CPU 上运行，30 分钟 4K 视频可能需要 30-60 分钟
- 前端轮询 2 秒间隔，任务完成前不能关闭页面
- 不支持中途取消

---

## 场景二：快速获取视频精彩片段

### 用户
短视频运营，需要从长视频中提取精彩片段

### 输入
- 一段 60 分钟的比赛视频
- 分析目标：「推荐精彩片段」
- 参数：`top_k=10`

### 系统行为
1. planner 匹配到 `"精彩"` 关键词，生成工具链：metadata → extract_frames → detect_scenes → detect_objects → track_objects → recommend_highlights
2. 场景检测区分不同镜头
3. 目标检测识别运动员和球
4. 多维度评分（object_score + motion_score + scene_score + quality_score）
5. 多样性选择确保不推荐重复片段
6. 导出 clip_001.mp4 ... clip_010.mp4 + highlight.mp4

### 输出
- 10 个片段时间范围（如 `00:00-00:20`, `05:30-05:50`）
- 每个片段的评分和理由（如 `object_score=0.47, motion_score=0.55`）
- 10 个独立的 clip 文件 + 一个拼接的 highlight.mp4

### 限制
- 评分权重是直觉设定的（object=0.25, motion=0.20, speech=0.20, scene=0.15, quality=0.10, diversity=0.10）
- 可能和用户主观判断不一致
- 不支持用户自定义评分规则
- 只推荐连续时间片段，不支持多片段组合

---

## 场景三：给视频生成字幕

### 用户
教育视频制作者，需要为线上课程视频生成字幕

### 输入
- 一段含中文语音的教学视频（45 分钟）
- 分析目标：「生成字幕」

### 系统行为
1. planner 匹配 `"字幕"` 关键词，工具链：metadata → transcribe
2. FFmpeg 提取 16kHz 单声道 WAV 到 `data/audio/{id}.wav`
3. faster-whisper base model 进行语音识别
4. 输出 `subtitles.json`（含 start/end/text）+ `subtitles.srt`（标准字幕格式）

### 输出
```json
{
  "segment_count": 65,
  "segments": [
    {"start": 0.0, "end": 2.0, "text": "大家好，今天我们来学习..."},
    ...
  ],
  "report_paths": {
    "json_path": "data/reports/{id}/subtitles.json",
    "srt_path": "data/reports/{id}/subtitles.srt"
  }
}
```

### 限制
- CPU 上较慢：45 分钟音频约 20-30 分钟处理（base 模型）
- 默认 base 模型，大模型（large-v3）精度更高但更慢
- 无说话人区分（diarization）
- 无中文标点优化（whisper 中文标点准确度有限）

---

## 场景四：视频内容分析报告

### 用户
视频分析师，需要为多个视频生成统一格式的分析报告

### 输入
- 视频文件
- 分析目标：「生成报告」

### 系统行为
1. 全 pipeline 执行（所有 9 个工具）
2. `report_service.py` 读取所有中间产物
3. 渲染 `final_report.json`（结构化数据）和 `final_report.md`（人类可读）

### 输出
Markdown 报告，含 6 个章节：

```markdown
## 1. Video Information
- Duration: 01:28
- Resolution: 3840 x 2160
- FPS: 30.303
- Frame count: 2672

## 2. Scene Timeline
Detected 12 scenes

## 3. Object Detection Summary
| Class | Occurrences | Frames | Avg Confidence |
|-------|-------------|--------|----------------|
| person | 184 | 160 | 0.854 |
| chair | 45 | 40 | 0.723 |

## 4. Subtitle Summary
Segments: 65, Total words: ~480

## 5. Highlight Recommendations
Top 5 highlights with scores and reasoning

## 6. Exported Clips
5 individual clips + highlight.mp4
```

### 限制
- 报告是规则模板生成，无 LLM 摘要
- 不支持跨视频对比分析
- 无图表可视化
- 无 PDF/Word 导出

---

## 场景五：目标检测与统计

### 用户
安防监控人员，需要了解某段监控视频中人的出现情况

### 输入
- 监控视频
- 分析目标：「检测物体」

### 系统行为
1. planner 匹配 `"检测"` 和 `"目标"`，生成：metadata → extract_frames → detect_objects → track_objects
2. YOLO 对每帧做目标检测（person / car / etc.）
3. IoU 启发式跟踪，统计每类目标
4. 输出 detections.json + tracks.json + class_stats.json

### 输出
```json
{
  "class_summary": {"person": 158, "car": 23, "bicycle": 5},
  "statistics": [
    {"class_name": "person", "total_occurrences": 158,
     "frame_count": 140, "avg_confidence": 0.854}
  ],
  "tracks": [
    {"track_id": 1, "class_name": "person",
     "start_time": 0.0, "end_time": 45.2,
     "boxes": [...]},
    ...
  ]
}
```

### 限制
- 跟踪算法是简单 IoU 启发式，不是真实 ByteTrack
- 人物密集场景跟踪效果不佳
- 无人物重识别（ReID）
- 无跨场景跟踪

---

## 场景六：可视化检测结果

### 用户
数据标注团队质检员，需要检查 YOLO 检测效果

### 输入
- 已经分析过目标检测的视频
- 点击「生成可视化」

### 系统行为
1. 读取 detections.json
2. 在原始抽帧图上绘制 bbox、class_name、confidence
3. 输出到 `data/reports/{id}/vis_frames/`
4. 前端展示前 20 张

### 输出
20 张带标注框的关键帧图片（在浏览器中显示）

### 限制
- 只显示前 20 张（max_frames 参数可调但前端限制展示）
- 标注风格固定（颜色、粗细、字号不可配置）

---

## 场景七：精彩片段自动剪辑

### 用户
活动记录者，需要从 2 小时活动中快速提取精华片段

### 输入
- 活动视频（2 小时）
- 分析目标：「剪辑」

### 系统行为
1. planner 匹配 `"剪辑"`，工具链含 export_clips
2. 分析完成后调用 clip_export_service
3. FFmpeg fast copy（不重新编码）快速裁剪
4. 多个 clip 拼接为 highlight.mp4

### 输出
```
data/clips/{id}/
  ├─ clip_001.mp4     (00:00-00:20)
  ├─ clip_002.mp4     (05:30-05:50)
  ├─ clip_003.mp4     ...
  ├─ clip_004.mp4
  ├─ clip_005.mp4
  └─ highlight.mp4   (拼接后的总文件)
```

### 限制
- 不支持自定义起止时间
- 不支持添加转场效果
- 不支持叠加字幕或水印
- 不支持输出不同分辨率（固定原分辨率）

---

## 场景八：API 集成到自己的工作流

### 用户
开发者，需要在自有系统中集成视频分析功能

### 输入
HTTP 请求（Python/curl/Postman 等）

### 系统行为
- 16 个标准化 REST API 端点
- `POST /upload` → 获取 `video_id`
- `POST /{id}/agent-run?user_goal=...` → 获取 `task_id`
- `GET /tasks/{task_id}` → 轮询进度
- `GET /{id}/report` → 获取完整报告

### 输出
标准 JSON 响应，适合程序化处理

### 限制
- 无 API 鉴权（完全开放）
- 无速率限制
- 无 SDK/Client library
- 无 WebSocket 实时推送（只能轮询）
- 无 OpenAPI/Swagger 文档优化
