# Real Dataset: Highlight Evaluation

## 用途

此目录用于管理真实视频的 Highlight 评估实验数据。与 xperiments/highlight_eval/examples/ 中的合成数据不同，此目录的数据来自真实 Pipeline 输出和人工标注。

## 目录结构

`
real_dataset/
  source/              # 视频来源信息
    video_list.csv     # 视频清单模板（含 video_id、时长、类别）
  manifest/
    template_manifest.json  # 批量评估 manifest 模板
  labels/              # 人工标注文件（运行 create_label_template.py 生成）
  candidates/          # Pipeline 导出的 candidates（运行 Pipeline 后放入）
  templates/           # 由 create_label_template.py 生成的标签模板
  .gitkeep             # 占位文件
`

## 推荐的 10 视频实验集

| 类别 | 数量 | 时长 | 说明 |
|------|------|------|------|
| lecture / talking head | 2 | ~15-20 min | 单人演讲，语音密集 |
| interview / podcast | 2 | ~10-15 min | 多人对话 |
| sports / game | 2 | ~8-10 min | 快速运动，场景切换 |
| scene_change | 1 | ~5 min | 频繁场景切换 |
| low_information | 1 | ~10 min | 静态画面，信息量低 |
| no_audio | 1 | ~5 min | 无语音轨道 |
| long_video | 1 (可选) | ~30+ min | 测试长视频扩展性 |

## 使用步骤

### 1. 生成标签模板

单视频模式：

`powershell
python scripts/create_label_template.py --mode video --video-id my_video_01 --duration 900 --category lecture --output-dir experiments/highlight_eval/real_dataset/templates
`

时间线模式（等间隔分段）：

`powershell
python scripts/create_label_template.py --mode timeline --video-id my_video_01 --duration 900 --interval 30 --category lecture --output-dir experiments/highlight_eval/real_dataset/templates
`

批量模式（从 CSV 读取）：

`powershell
python scripts/create_label_template.py --mode batch --csv experiments/highlight_eval/real_dataset/source/video_list.csv --output-dir experiments/highlight_eval/real_dataset/templates
`

### 2. 手工标注

编辑生成的 *_label_template.json 文件：

- 为每个精彩片段填写 start_time、nd_time
- 设置 
ating (1-5)
- 填写 category (speech / visual / action / scene / mixed / other)
- 可添加备注到 
ote 字段
- 设置 nnotator 标注者名称

### 3. 验证标注文件

`powershell
python scripts/create_label_template.py --mode validate --label-file experiments/highlight_eval/real_dataset/labels/my_video_01_label.json
`

### 4. 运行 Pipeline 导出 Candidates

启动 dev.ps1 → 上传视频 → 获取 video_id → 下载 candidates：

`powershell
Invoke-WebRequest -Uri http://127.0.0.1:8000/api/v1/videos/<video_id>/reports/candidates -OutFile experiments/highlight_eval/real_dataset/candidates/<video_id>_candidates.json
`

### 5. 运行批量评估

更新 manifest/template_manifest.json 中的 paths 后：

`powershell
python scripts/run_highlight_eval_batch.py --manifest experiments/highlight_eval/real_dataset/manifest/template_manifest.json --configs experiments/highlight_eval/configs/baseline.json experiments/highlight_eval/configs/speech_heavy.json experiments/highlight_eval/configs/visual_heavy.json --output-dir experiments/highlight_eval/results/real_batch_run --top-k 3
`


## 隐私检查

提交代码前运行隐私检查，确保不包含本地路径或敏感信息：

```powershell
python scripts/check_experiment_privacy.py --root experiments/highlight_eval/real_dataset
```

支持参数：

| 参数 | 说明 |
|------|------|
| `--root` | 要扫描的根目录 |
| `--fail-on-warning` | warning 时也返回非零退出码 |
| `--verbose` | 详细输出，显示扫描的每个文件 |

检查规则：

1. Windows 盘符绝对路径（例如 C: 或 D: 开头的反斜杠路径）
2. Unix 绝对路径（例如 macOS/Linux 标准用户目录路径）
3. 敏感关键词（`API_KEY`、`SECRET`、`TOKEN`、`PASSWORD`）
4. 邮箱地址
5. 视频二进制文件（`.mp4`、`.mov` 等）

### 提交前 Checklist

- [ ] 运行隐私检查并通过
- [ ] label JSON 中不包含 C: 或 D: 开头的本地路径
- [ ] annotator 字段使用化名，不要使用真实邮箱
- [ ] 不提交 `.mp4`、`.mov` 等视频文件
- [ ] `.gitkeep` 以外的空目录正确忽略
- [ ] manifest 中 `candidates_json` 和 `labels_json` 使用相对路径

更多详情请参阅 [P2_EXPERIMENT_WORKFLOW.md](../P2_EXPERIMENT_WORKFLOW.md)。
