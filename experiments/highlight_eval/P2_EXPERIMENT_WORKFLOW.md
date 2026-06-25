# P2 实验工作流

## 1. 实验目标

比较不同 Highlight 评分权重配置在不同视频类别下的效果，通过定量指标选择最佳权重。

支持：
- 从 Pipeline 导出候选片段（candidates），用不同权重重评分
- 对已有结果重新评估（existing 模式）
- 批量评估多视频、多配置
- 加权综合评分选择最佳配置
- 生成论文级对比表格

## 2. 工具链

| 工具 | 用途 |
|------|------|
| `scripts/evaluate_highlights.py` | 单视频评估（existing / rescore 模式） |
| `scripts/run_highlight_eval_batch.py` | 多视频批量评估 + 最佳配置选择 + 论文表格 |
| `experiments/highlight_eval/configs/*.json` | 权重配置（baseline / speech_heavy / visual_heavy） |
| `experiments/highlight_eval/manifests/*.json` | 批量评估的 manifest |
| `experiments/highlight_eval/examples/*.json` | 示例候选和标注数据 |

## 3. 数据准备

建议视频类别和数量：

| 类别 | 建议数量 | 说明 |
|------|----------|------|
| lecture / talking head | 2 | 单人或多人演讲，语音密集 |
| interview / podcast | 2 | 多人对话，场景变化少 |
| sports / game | 2 | 快速运动，频繁场景切换 |
| scene change | 2 | 明显场景切换 |
| low information | 1 | 静态画面，信息量低 |
| no audio | 1 | 无语音轨道 |
| long video (30min+) | 1-2 | 测试长视频扩展性 |

**不提交大型视频文件**：视频保留在本地 `data/raw_videos/` 目录，不进入 Git 仓库。

## 4. 人工标注流程

创建 label JSON 文件：

```json
{
  "video_id": "my_video_001",
  "video_path": "data/raw_videos/my_video.mp4",
  "duration": 120.0,
  "labels": [
    {
      "id": "gt_001",
      "start_time": 10.0,
      "end_time": 25.0,
      "rating": 5,
      "category": "speech",
      "note": "关键信息密集"
    }
  ]
}
```

标注规则：
- `start_time` / `end_time`：秒级时间戳
- `rating`：1（最不重要）到 5（最重要）
- `category`：`speech`, `visual`, `action`, `scene`, `mixed`, `other`
- `end_time` > `start_time`，不超过视频总时长
- 建议多标注者进行一致性检验

## 5. 运行 Pipeline 导出 Candidates

前置条件：
- 启动 dev.ps1（或手动启动 backend）
- 上传视频，完成分析

获取 candidates：

```powershell
# 假设 video_id = "abc123"
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/v1/videos/abc123/reports/candidates `
  -OutFile experiments/highlight_eval/results/abc123_candidates.json
```

candidates JSON 示例：

```json
{
  "schema_version": 1,
  "video_id": "abc123",
  "duration": 120.0,
  "candidates": [
    {
      "id": "cand_0001",
      "start_time": 0.0,
      "end_time": 20.0,
      "duration": 20.0,
      "scores": {
        "object": 0.1, "motion": 0.05, "speech": 0.9,
        "scene": 0.2, "quality": 0.7
      }
    }
  ]
}
```

## 6. 单视频 Rescore

使用不同权重配置对同一个视频进行重新评分和评估：

```powershell
python scripts/evaluate_highlights.py --mode rescore `
  --candidates-json experiments/highlight_eval/results/abc123_candidates.json `
  --labels experiments/highlight_eval/labels/abc123_labels.json `
  --configs experiments/highlight_eval/configs/baseline.json `
            experiments/highlight_eval/configs/speech_heavy.json `
            experiments/highlight_eval/configs/visual_heavy.json `
  --output-dir experiments/highlight_eval/results/abc123_rescore `
  --top-k 3 `
  --iou-threshold 0.3
```

输出：
- `metrics.csv` / `metrics.json`：各配置的指标
- `predictions_{config}.json`：各配置的预测细节
- `matches_{config}.json`：预测与标签的匹配详情

## 7. 多视频批量评估

### 创建 Manifest

编辑 `manifests/my_dataset.json`：

```json
{
  "schema_version": 1,
  "name": "my_eval_dataset",
  "description": "8 videos for highlight evaluation",
  "videos": [
    {
      "video_id": "lecture_001",
      "category": "lecture",
      "duration": 120.0,
      "candidates_json": "experiments/highlight_eval/examples/lecture_candidates.json",
      "labels_json": "experiments/highlight_eval/examples/lecture_label.json"
    }
  ]
}
```

注意：`candidates_json` 和 `labels_json` 使用相对路径（相对于 manifest 文件所在目录）。

### 运行 Batch

```powershell
python scripts/run_highlight_eval_batch.py `
  --manifest experiments/highlight_eval/manifests/my_dataset.json `
  --configs experiments/highlight_eval/configs/baseline.json `
            experiments/highlight_eval/configs/speech_heavy.json `
            experiments/highlight_eval/configs/visual_heavy.json `
  --output-dir experiments/highlight_eval/results/batch_run `
  --top-k 3 `
  --iou-threshold 0.3
```

### 自定义评分权重

使用 `--score-weights` 指定加权指标：

```powershell
python scripts/run_highlight_eval_batch.py ... `
  --score-weights "precision_at_k=0.50,recall_at_k=0.25,mean_iou=0.25"
```

默认权重：

| 指标 | 权重 | 方向 |
|------|------|------|
| precision_at_k | 0.30 | 越高越好 |
| recall_at_k | 0.20 | 越高越好 |
| mean_iou | 0.25 | 越高越好 |
| avg_human_rating | 0.20 | 越高越好（[1,5] 归一化到 [0,1]） |
| duplicate_ratio | 0.05（扣分制） | 越低越好 |

## 8. 输出解释

| 文件 | 说明 |
|------|------|
| `per_video_metrics.csv` | 每个视频 × 每个配置的详细指标 |
| `aggregate_metrics.csv` / `.json` | 所有视频平均指标，含 weighted_score、rank、is_best |
| `category_metrics.csv` | 按类别分组的指标 |
| `best_config.json` | 最佳配置名称和加权得分 |
| `experiment_summary.md` | 汇总报告，含最佳配置选择和论文表格 |
| `paper_table_overall.md` | 论文级总体对比表 |
| `paper_table_by_category.md` | 论文级分类别对比表 |
| `paper_table_per_video.md` | 论文级每视频对比表 |
| `errors.json` | 每个视频的错误信息（如有） |
| `run_config.json` | 本次运行的参数 |

### 指标定义

| 指标 | 全称 | 定义 |
|------|------|------|
| Precision@K | 精确率 | Top-K 预测中与任一标注片段 IoU ≥ threshold 的比例 |
| Recall@K | 召回率 | 被 Top-K 预测覆盖的标注片段比例 |
| mean IoU | 平均 IoU | 每个预测的最佳时间交并比平均值 |
| avg_human_rating | 平均人工评分 | 匹配到的标注评分的平均值 |
| duplicate_ratio | 重复比例 | 预测对中 IoU > 0.5 的比例 |
| coverage_seconds | 覆盖时长 | 预测覆盖的唯一时长 |
| avg_pred_duration | 预测平均时长 | 所有预测的平均时长 |

## 9. 论文表格

包含三个论文级表格：

**Overall Metrics（总体对比）**：展示各配置在所有视频上的平均指标，含加权得分和排名。

**Metrics by Category（分类别对比）**：展示各配置在每个视频类别上的表现，自动标注类内最佳。

**Per-Video Metrics（每视频对比）**：展示每个视频在每个配置下的详细指标。

可直接将 Markdown 表格复制到论文中。

## 10. 推荐实验设置

| 参数 | 默认值 | 备注 |
|------|--------|------|
| `--top-k` | 3 | 覆盖多数标注场景。5 用于评估覆盖更多候选时的表现 |
| `--iou-threshold` | 0.3 | 标准时间定位匹配阈值 |
| `--score-weights` | 默认 | 按论文需要调整 precision / recall / iou 权重 |

## 11. 当前限制

1. **示例数据不代表真实结论**：`examples/` 中的候选和标注为合成数据，仅供功能验证。
2. **需要真实视频和人工标注**：当前实验结果不构成学术结论。
3. **无统计显著性检验**：暂未实现 bootstrap、paired t-test 等。
4. **单标注者**：标注者偏差可能影响结果。
5. **rescore 模式不调用完整 Pipeline**：只对已有候选重新评分，不重新运行检测、语音识别等。

## 12. 下一步计划

1. 对 8-12 个真实视频进行人工标注
2. 使用真实 Pipeline 导出 candidates
3. 运行批量评估，比较 baseline / speech_heavy / visual_heavy
4. 多标注者一致性检验（Krippendorff's alpha）
5. 统计显著性检验（bootstrap 或 paired test）
6. 自动权重搜索和调优


## 隐私检查

在提交实验文件前，始终运行隐私检查：

```powershell
python scripts/check_experiment_privacy.py --root experiments/highlight_eval/real_dataset
python scripts/check_experiment_privacy.py --root experiments/highlight_eval/labels
```

### 提交规则

1. **可以提交**：脱敏后的 label JSON、candidates JSON、manifest JSON、指标 CSV。
2. **不可以提交**：原始视频文件（`.mp4`、`.mov` 等）、包含本地绝对路径（`C:\`、`D:\`）的文件、包含 API Key / 邮箱的文件。
3. **标注者字段**：使用化名，不要使用真实邮箱。
4. **paths**：manifest 中 candidates_json/labels_json 始终使用相对路径。

更多详情请参阅 [real_dataset/README.md](./real_dataset/README.md)。
