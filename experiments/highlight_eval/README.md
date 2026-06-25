# Highlight Evaluation Experiments


> ▶ **Recommended workflow**: See [P2_EXPERIMENT_WORKFLOW.md](./P2_EXPERIMENT_WORKFLOW.md) for a complete step-by-step guide (in Chinese) covering data preparation, annotation, pipeline export, evaluation, and paper table generation.

## Purpose

Evaluate and compare different highlight scoring weight configurations against human-annotated ground-truth labels.

Supports:
- Loading existing pipeline results (`existing` mode)
- Comparing multiple weight configs side by side
- Computing Precision@K, Recall@K, temporal IoU, duplicate ratio, and more
- Outputting CSV and JSON for analysis and paper/portfolio inclusion

## Dataset Recommendations

For meaningful evaluation, prepare at least 8-10 test videos:

| Type | Count | Description |
|------|-------|-------------|
| Lecture / talking head | 2 | Person speaking, limited scene changes |
| Interview / podcast | 2 | Multi-person dialogue, few cuts |
| Game / sports | 2 | Fast motion, scene transitions |
| Clear scene changes | 2 | Obvious cuts between locations |
| Low information | 1 | Static camera, minimal activity |
| No audio | 1 | No speech track |
| Long video (30min+) | 1-2 | Tests scaling and longer highlights |

## Annotation Guidelines

Each label file follows this format:

```json
{
  "video_id": "example_001",
  "video_path": "path/to/video.mp4",
  "duration": 30.0,
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

### Rules

- `start_time` and `end_time` in seconds
- `rating` 1-5 (5 = most highlight-worthy)
- `category`: `speech`, `visual`, `action`, `scene`, `mixed`, `other`
- Timestamps must not be negative
- `end_time` must be > `start_time`
- Labels cannot exceed video duration

## Weight Configurations

| Config | Object | Motion | Speech | Scene | Quality | Best For |
|--------|--------|--------|--------|-------|---------|----------|
| baseline | 0.25 | 0.20 | 0.20 | 0.15 | 0.20 | General purpose |
| speech_heavy | 0.10 | 0.10 | 0.55 | 0.10 | 0.15 | Lectures, podcasts, interviews |
| visual_heavy | 0.35 | 0.35 | 0.05 | 0.15 | 0.10 | Sports, games, surveillance |

Config files are in `configs/`.

## Running Evaluation

### Single result file

```powershell
python scripts/evaluate_highlights.py ^
  --result-json experiments/highlight_eval/example_result.json ^
  --labels experiments/highlight_eval/labels/example_label.json ^
  --configs experiments/highlight_eval/configs/baseline.json ^
  --output-dir experiments/highlight_eval/results/run_001
```

### Multiple configs

```powershell
python scripts/evaluate_highlights.py ^
  --result-json experiments/highlight_eval/example_result.json ^
  --labels experiments/highlight_eval/labels/example_label.json ^
  --configs experiments/highlight_eval/configs/baseline.json ^
            experiments/highlight_eval/configs/speech_heavy.json ^
            experiments/highlight_eval/configs/visual_heavy.json ^
  --output-dir experiments/highlight_eval/results/run_001
```

### Custom parameters

```powershell
python scripts/evaluate_highlights.py ^
  --result-json path/to/result.json ^
  --labels path/to/labels.json ^
  --configs path/to/config.json ^
  --output-dir experiments/highlight_eval/results/custom_run ^
  --top-k 10 ^
  --iou-threshold 0.5
```

## Output Metrics

| Metric | Description |
|--------|-------------|
| Precision@K | Fraction of top-K predictions matching any ground-truth label |
| Recall@K | Fraction of ground-truth labels hit by top-K predictions |
| mean IoU | Average best temporal IoU for each prediction |
| avg_human_rating | Average rating of matched labels |
| duplicate_ratio | Fraction of prediction pairs with IoU > 0.5 |
| coverage_seconds | Total unique seconds covered by predictions |
| avg_pred_duration | Mean duration of predictions |
| highlight_count | Number of predictions |

## Output Files

| File | Contents |
|------|----------|
| `metrics.csv` | Tabular metrics for all configs |
| `metrics.json` | Same data in JSON format |
| `matches_{config}.json` | Per-prediction match details |
| `run_config.json` | Parameters used for this evaluation |

## Current Limitations

1. **existing mode only**: The tool evaluates the already-computed highlights from the pipeline by sorting and selecting by score. It does NOT re-run the full highlight service offline to re-score all candidates with different weights.
2. **No multi-annotator agreement**: Labels from a single annotator may have bias.
3. **Synthetic test video**: The example data uses a synthetic video — real content may produce different results.

## Future Plans

- `rescore` mode: fully re-run scoring with different weights
- Best config selection via weighted scoring
- Paper-ready table generation (overall, by category, per-video)
- Multi-annotator agreement (Krippendorff's alpha)
- Per-category breakdown of metrics



## Best Config Selection (Weighted Scoring)

The batch evaluation system automatically selects the best configuration using a **weighted composite score**.

### Score Weights

Default weights:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| precision_at_k | 0.30 | Hit rate of top-K predictions |
| recall_at_k | 0.20 | Coverage of ground-truth labels |
| mean_iou | 0.25 | Temporal boundary accuracy |
| avg_human_rating | 0.20 | Average human rating of matched labels (normalized [1,5] -> [0,1]) |
| duplicate_ratio | 0.05 (subtractive) | Penalty for redundant predictions |

Custom weights: `--score-weights "precision_at_k=0.50,recall_at_k=0.25,mean_iou=0.25"`

### Outputs

| File | Description |
|------|-------------|
| `aggregate_metrics.json` | Includes `weighted_score`, `rank`, `is_best` |
| `category_metrics.csv` | Per-category metrics with `weighted_score` |
| `best_config.json` | The best config name and weighted score |
| `experiment_summary.md` | Best Config Selection, Config Rankings, and Paper-Ready Tables |
| `paper_table_overall.md` | Paper-ready overall comparison table |
| `paper_table_by_category.md` | Paper-ready per-category comparison table |
| `paper_table_per_video.md` | Paper-ready per-video metrics table |

### Tie-breaking

When weighted scores are tied, the order is determined by: higher precision -> higher IoU -> lower duplicate ratio -> alphabetical config name.

### CLI Examples

```powershell
# Default weights (--top-k 3)
python scripts/run_highlight_eval_batch.py ^
  --manifest experiments/highlight_eval/manifests/example_manifest.json ^
  --configs experiments/highlight_eval/configs/baseline.json ^
            experiments/highlight_eval/configs/speech_heavy.json ^
            experiments/highlight_eval/configs/visual_heavy.json ^
  --output-dir experiments/highlight_eval/results/batch_run ^
  --top-k 3

# Custom weights
python scripts/run_highlight_eval_batch.py ^
  --manifest experiments/highlight_eval/manifests/example_manifest.json ^
  --configs experiments/highlight_eval/configs/baseline.json ^
            experiments/highlight_eval/configs/speech_heavy.json ^
  --output-dir experiments/highlight_eval/results/custom_weights ^
  --top-k 3 ^
  --score-weights "precision_at_k=0.50,recall_at_k=0.25,mean_iou=0.25"
```
## Rescore Mode

In addition to evaluating existing results, the tool supports **rescore mode** which fully re-runs the highlight scoring with different weight configurations.

### Overview

Instead of loading already-computed highlights and just sorting/re-evaluating them, rescore mode:

1. Loads raw **candidate segments** from a JSON file.
2. Applies user-specified scoring weights to each candidate.
3. Performs greedy diversity-aware selection.
4. Computes evaluation metrics against ground-truth labels.

This allows you to experiment with different weight configurations without re-running the entire video pipeline.

### Candidates JSON Schema

`json
{
  "schema_version": 1,
  "video_id": "example_001",
  "duration": 30.0,
  "generated_at": "2026-06-20T12:00:00Z",
  "candidates": [
    {
      "id": "cand_0001",
      "start_time": 2.0,
      "end_time": 16.0,
      "duration": 14.0,
      "scores": {
        "object": 0.10,
        "motion": 0.20,
        "speech": 0.80,
        "scene": 0.50,
        "quality": 0.70
      },
      "metadata": {"source": "highlight_service", "window_index": 0}
    }
  ]
}
`

Supported score dimensions: object, motion, speech, scene, quality.

### Rescore Formula

`
base_score = sum(weight_k * score_k)  for k in {object, motion, speech, scene, quality}
selection_score = clamp(base_score - diversity_lambda * max_overlap_iou, 0, 1)
`

- **Greedy selection**: candidates are sorted by ase_score descending, then each candidate's overlap penalty is computed against already-selected segments.
- **Overlap penalty**: uses max IoU between the candidate and any already-selected segment.
- **Diversity lambda**: controls how strongly overlapping segments are penalized (default 0.15).

### Running Rescore Mode

`powershell
python scripts/evaluate_highlights.py ^
  --mode rescore ^
  --candidates-json experiments/highlight_eval/example_candidates.json ^
  --labels experiments/highlight_eval/labels/example_label.json ^
  --configs experiments/highlight_eval/configs/baseline.json ^
            experiments/highlight_eval/configs/speech_heavy.json ^
            experiments/highlight_eval/configs/visual_heavy.json ^
  --output-dir experiments/highlight_eval/results/rescore_run
`

### Custom parameters

`powershell
python scripts/evaluate_highlights.py ^
  --mode rescore ^
  --candidates-json experiments/highlight_eval/example_candidates.json ^
  --labels experiments/highlight_eval/labels/example_label.json ^
  --configs experiments/highlight_eval/configs/baseline.json ^
  --output-dir experiments/highlight_eval/results/custom_rescore ^
  --top-k 10 ^
  --iou-threshold 0.5 ^
  --diversity-lambda 0.3
`

### Mode Comparison

| Aspect | Existing Mode | Rescore Mode |
|--------|---------------|--------------|
| Input | Pre-computed highlight JSON | Raw candidate segments JSON |
| Scoring | Uses existing scores | Applies config weights to raw scores |
| Selection | Top-K by existing score | Greedy diversity-aware selection |
| Overlap penalty | Not computed | Computed via IoU |
| Use case | Evaluate pipeline output | Experiment with weight configs |

### Rescore Outputs

Same metrics as existing mode plus:
- predictions_{config}.json — detailed per-prediction output with score breakdown
- Overlap penalty included in per-prediction output

## Real Pipeline Integration

Starting from P2 Step 3, the video analysis pipeline automatically exports a candidates JSON artifact alongside the highlights.

### Accessing Candidates via API

After a video analysis completes, the candidates artifact is available at:

`
GET /api/v1/videos/{video_id}/reports/candidates
`

Example:

`powershell
Invoke-WebRequest 
  http://127.0.0.1:8000/api/v1/videos/<video_id>/reports/candidates 
  -OutFile experiments/highlight_eval/results/<video_id>_candidates.json
`

The same URL is also included in the unified Result API under 
eport.candidates_url.

### Running Rescore with Real Pipeline Outputs

`powershell
python scripts/evaluate_highlights.py 
  --mode rescore 
  --candidates-json experiments/highlight_eval/results/<video_id>_candidates.json 
  --labels experiments/highlight_eval/labels/<video_id>.json 
  --configs experiments/highlight_eval/configs/baseline.json experiments/highlight_eval/configs/speech_heavy.json experiments/highlight_eval/configs/visual_heavy.json 
  --output-dir experiments/highlight_eval/results/<video_id>_rescore
`

### Candidates Artifact Location

The artifact is saved to:
`
data/reports/<video_id>/highlight_candidates.json
`

This file uses the same schema as xample_candidates.json and is directly compatible with --mode rescore --candidates-json.

### Note on Candidate Completeness

The exported candidates are the full set of scored candidates generated by _generate_candidates() before diversity selection. This includes all sliding window segments from detected scenes, each with their full score breakdown (object, motion, speech, scene, quality). This is the true candidate pool for rescore experiments.

## Batch Evaluation (Multi-Video)

Run highlight evaluation across multiple videos with a single command.

### Manifest Format

Create a JSON manifest listing your videos:

`json
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
      "labels_json": "experiments/highlight_eval/examples/lecture_label.json",
      "notes": "speech-heavy"
    }
  ]
}
`

### Running a Batch

`powershell
python scripts/run_highlight_eval_batch.py 
  --manifest experiments/highlight_eval/manifests/example_manifest.json 
  --configs experiments/highlight_eval/configs/baseline.json experiments/highlight_eval/configs/speech_heavy.json experiments/highlight_eval/configs/visual_heavy.json 
  --output-dir experiments/highlight_eval/results/batch_run 
  --top-k 3 
  --iou-threshold 0.3
`

### Output Files

| File | Description |
|------|-------------|
| per_video_metrics.csv | Per-video, per-config metrics |
| ggregate_metrics.csv | Averaged metrics by config |
| ggregate_metrics.json | Same in JSON format |
| category_metrics.csv | Metrics grouped by video category |
| xperiment_summary.md | Formatted markdown summary |
| rrors.json | Per-video errors (if any) |
| 
un_config.json | Parameters used for this run |

### Output Columns

**per_video_metrics.csv**: ideo_id, category, config_name, 	op_k, iou_threshold, precision_at_k, 
ecall_at_k, mean_iou, vg_human_rating, duplicate_ratio, coverage_seconds, vg_pred_duration, highlight_count, rror

**aggregate_metrics.csv**: Same metrics with mean_ prefix, averaged across videos.

**category_metrics.csv**: Same metrics broken down by category + config.

### Recommended Evaluation Dataset (8-12 videos)

| Type | Count | Configs to Compare |
|------|-------|--------------------|
| lecture / talking head | 2 | speech_heavy vs baseline |
| interview / podcast | 2 | baseline vs speech_heavy |
| sports / game | 2 | visual_heavy vs baseline |
| scene change | 2 | visual_heavy vs baseline |
| low information | 1 | baseline (all configs similar) |
| no audio | 1 | baseline (speech weight wasted) |
| long video (30min+) | 1-2 | All configs |

### Interpreting Results

- Higher **P@K / R@K** = better alignment with human annotations
- Higher **mIoU** = better temporal boundary accuracy
- Higher **duplicate_ratio** = more redundancy, less diversity
- Compare config means to identify which weight set best matches human judgment per category

### Paper / Portfolio Table Template

| Category | Config | P@K | R@K | mIoU | Dup% |
|----------|--------|-----|-----|------|------|
| All | baseline | — | — | — | — |
| All | speech_heavy | — | — | — | — |
| All | visual_heavy | — | — | — | — |
| Lecture (2) | baseline | — | — | — | — |
| Lecture (2) | speech_heavy | — | — | — | — |
| Sports (2) | baseline | — | — | — | — |
| Sports (2) | visual_heavy | — | — | — | — |
