# VideoMind Agent — 最终路线图

## 已完成

### P0 — 系统稳定性与基础架构
- ✅ FastAPI 后端 + SQLite + 路由结构
- ✅ React + Vite 前端基础
- ✅ 视频上传、元数据提取、帧提取、场景检测
- ✅ YOLO 目标检测、Whisper 字幕生成
- ✅ Stream 输出与任务状态管理
- ✅ Windows 路径兼容性
- ✅ 测试环境 Ultralytics 隔离

### P1 — Demo 可展示
- ✅ 统一 Result API
- ✅ 媒体接口（HTTP Range 206 支持）
- ✅ 结构化的 Highlight / Clip API
- ✅ 响应安全（清理本地绝对路径）
- ✅ 原生 VideoPlayer 组件（区间播放、进度跳转）
- ✅ HighlightTimeline（重叠片段优先级、播放头同步）
- ✅ HighlightList + ScoreBreakdown（评分展示）
- ✅ ResultWorkspace（统一连接 Result API + 播放器 + Timeline）
- ✅ 浏览器验收（Edge, Range 206, 真实视频播放）
- ✅ Windows 一键启动脚本 dev.ps1
- ✅ 部署文档（.env.example, .gitignore, README）

### P2 — Highlight 实验工具链
- ✅ `evaluate_highlights.py` — 单视频评估 CLI
- ✅ rescore 模式 — 对已有 candidates 重新评分
- ✅ candidates 导出 + `/reports/candidates` API
- ✅ `run_highlight_eval_batch.py` — 多视频批量评估
- ✅ weighted best_config 选择 + paper-ready 表格
- ✅ `create_label_template.py` — 标注模板生成
- ✅ `check_experiment_privacy.py` — 隐私检查
- ✅ 42 个数据集相关测试
- ✅ P2_EXPERIMENT_WORKFLOW.md — 实验工作流文档
- ✅ EXPERIMENT_CHAPTER_DRAFT.md — 毕业设计/作品集实验草稿

## 下一阶段建议

### 第一优先级 — 真实实验

| 任务 | 预期产出 | 预计工作量 |
|------|----------|-----------|
| 收集 8–12 个真实视频 | 覆盖 7+ 类别 | 1–2 周 |
| 人工标注 | 每视频 5–15 个标签 | 1–2 周 |
| 运行 batch 实验 | best_config, paper tables | 1 天 |
| 撰写实验结论 | 论文图表、结果分析 | 3–5 天 |

### 第二优先级 — 实验深化

| 任务 | 预期产出 | 说明 |
|------|----------|------|
| 自动权重搜索 | 网格 / 贝叶斯搜索脚本 | 减少手动试错 |
| 多标注者一致性 | Cohen‘s Kappa 计算 | 提高标注可信度 |
| Bootstrap / Paired test | p-value，置信区间 | 统计显著性 |
| Baseline 对比 | 随机选择 / 均匀采样 | 证明算法有效 |

### 第三优先级 — 规划器对比

| 任务 | 预期产出 | 说明 |
|------|----------|------|
| Planner Provider 抽象 | 统一接口 | 解耦 rule 和 LLM |
| LLM 对比实验 | DeepSeek vs. rule-based | 评估规划质量 |
| 扩展数据集 | LLM 输出的评估集 | 需要人工评判 |

### 第四优先级 — 产品化

| 任务 | 预期产出 | 说明 |
|------|----------|------|
| Docker 化部署 | docker-compose.yml | GPU 支持需要额外配置 |
| Celery / Redis 队列 | 异步分析任务 | 解决大视频超时 |
| 用户认证 | 简单的 token 鉴权 | 多用户隔离 |
| 前端国际化 | i18n | 非必需 |

## 不推荐马上做

- ❌ 用户认证系统 — 当前单人使用场景不需要
- ❌ Docker GPU 部署 — 环境依赖复杂，建议等稳定性更高
- ❌ 大规模前端重构 — 当前播放器 + Timeline 已可使用
- ❌ 移动端适配 — 非毕业设计重点

## 推荐优先级

```
1. 真实实验（论文核心）
   ↓
2. 实验深化（论文质量）
   ↓
3. Planner 对比（如有余力）
   ↓
4. 产品化（非必要）
```

## 各阶段预期产出

| 阶段 | 产出 |
|------|------|
| P0 稳定性 | 可靠的基础系统 |
| P1 Demo | 可展示 Web 应用 |
| P2 实验工具链 | 可复现的实验框架 |
| P2-real-data | 真实实验结论 + 论文图表 |
| P2-statistics | 统计显著性证据 |
| P2-LLM-planner | Planner 性能对比 |
| P3 产品化 | Docker + Queue + Auth |

---

*本文档为项目路线图的最终版本，反映截至 P2 实验工具链完成时的状态。*
