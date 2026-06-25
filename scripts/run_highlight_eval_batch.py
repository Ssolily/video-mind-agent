"""Batch highlight evaluation across multiple videos with best_config selection and paper tables.

Reads a manifest file listing videos with their candidates/labels, runs rescore
evaluation for each video with multiple weight configs, selects the best config
via weighted scoring, and generates paper-ready result tables.
"""

import argparse, csv, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluate_highlights import (
    load_labels, load_config, rescore_candidates, evaluate_config,
    load_candidates,
)


# ── Manifest ─────────────────────────────────────────


def load_manifest(path: str) -> dict:
    """Load and return a manifest dict."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"Manifest not found: {path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    validate_manifest(data, p.parent)
    return data


def validate_manifest(manifest: dict, base_dir: Path):
    """Validate manifest structure, paths, and data."""
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be a JSON object")

    sv = manifest.get("schema_version")
    if not sv:
        raise ValueError("Manifest missing required field: schema_version")

    videos = manifest.get("videos", [])
    if not isinstance(videos, list) or not videos:
        raise ValueError("Manifest must contain at least one video entry")

    seen_ids = set()
    for v in videos:
        vid = v.get("video_id")
        if not vid:
            raise ValueError("Each video entry must have a video_id")
        if vid in seen_ids:
            raise ValueError(f"Duplicate video_id: {vid}")
        seen_ids.add(vid)

        for key in ("candidates_json", "labels_json"):
            raw = v.get(key, "")
            # Reject absolute paths
            if raw.startswith("/") or (len(raw) > 1 and raw[1] == ":"):
                raise ValueError(f"{key} for {vid} is an absolute path: {raw}")
            resolved = (base_dir / raw).resolve()
            if not resolved.is_file():
                raise FileNotFoundError(f"{key} for {vid} not found: {resolved}")

        category = v.get("category", "")
        if not category:
            raise ValueError(f"Video {vid} missing category")

        dur = v.get("duration")
        if dur is None or not isinstance(dur, (int, float)) or dur <= 0:
            raise ValueError(f"Video {vid} has invalid duration")


# ── Aggregation ──────────────────────────────────────


_METRIC_SRC = {
    "iou": "mean_iou",
}


_METRIC_FIELDS = [
    "precision_at_k", "recall_at_k", "iou", "avg_human_rating",
    "duplicate_ratio", "coverage_seconds", "avg_pred_duration", "highlight_count",
]


def aggregate_by_config(rows: list[dict]) -> list[dict]:
    """Aggregate per-video-per-config rows by config_name."""
    from collections import defaultdict
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("error"):
            continue
        groups[r["config_name"]].append(r)

    results = []
    for cfg, group in groups.items():
        entry = {"config_name": cfg, "video_count": len(group)}
        for field in _METRIC_FIELDS:
            vals = [g.get(field, 0) or 0 for g in group]
            entry[f"mean_{field}"] = round(sum(vals) / len(vals), 4) if vals else 0.0
        results.append(entry)
    return results


def aggregate_by_category(rows: list[dict]) -> list[dict]:
    """Aggregate per-video-per-config rows by category + config_name."""
    from collections import defaultdict
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("error"):
            continue
        key = (r.get("category", "unknown"), r["config_name"])
        groups[key].append(r)

    results = []
    for (cat, cfg), group in groups.items():
        entry = {"category": cat, "config_name": cfg, "video_count": len(group)}
        for field in _METRIC_FIELDS:
            vals = [g.get(field, 0) or 0 for g in group]
            entry[f"mean_{field}"] = round(sum(vals) / len(vals), 4) if vals else 0.0
        results.append(entry)
    return results


# ── Summary Markdown ─────────────────────────────────


# ── Score Weights for Best Config Selection ──────────

DEFAULT_SCORE_WEIGHTS = {
    "precision_at_k": 0.30,
    "recall_at_k": 0.20,
    "mean_iou": 0.25,
    "avg_human_rating": 0.20,
    "duplicate_ratio": 0.05,
}


def validate_score_weights(weights: dict) -> dict:
    """Validate and return score weights, normalizing to sum 1.0."""
    allowed = {"precision_at_k", "recall_at_k", "mean_iou", "avg_human_rating", "duplicate_ratio"}
    for k in weights:
        if k not in allowed:
            raise ValueError(f"Unknown score weight dimension: '{k}'. Allowed: {sorted(allowed)}")
        v = weights[k]
        if not isinstance(v, (int, float)) or v < 0 or v > 1:
            raise ValueError(f"Weight '{k}' = {v} not in [0, 1]")
    w_sum = sum(weights.values())
    if abs(w_sum - 1.0) > 0.01:
        raise ValueError(f"Score weights sum to {w_sum}, expected 1.0. Weights: {weights}")
    return weights


def parse_score_weights(expr: str) -> dict:
    """Parse 'precision_at_k=0.30,recall_at_k=0.20,...' into dict."""
    weights = {}
    for part in expr.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"Invalid score weight expression: '{part}'. Use key=value format.")
        k, v = part.split("=", 1)
        weights[k.strip()] = float(v.strip())
    return validate_score_weights(weights)


def norm_human_rating(avg_rating: float) -> float:
    """Normalize avg_human_rating from [1,5] to [0,1]."""
    return max(0.0, min(1.0, (avg_rating - 1.0) / 4.0))


def compute_weighted_score(agg_row: dict, score_weights: dict) -> float:
    """Compute composite weighted score from an aggregate row."""
    score = 0.0
    for dim, w in score_weights.items():
        if dim == "avg_human_rating":
            raw = agg_row.get("mean_avg_human_rating", 0) or 0
            val = norm_human_rating(raw)
        elif dim == "duplicate_ratio":
            val = agg_row.get("mean_duplicate_ratio", 0) or 0
            score -= w * val
            continue
        else:
            val = agg_row.get(f"mean_{dim}", 0) or 0
        score += w * val
    return round(score, 4)


def select_best_config(aggregate: list[dict], score_weights: dict) -> dict | None:
    """Select the best config from aggregated results.
    Tie-breaking: higher precision -> higher iou -> lower duplicate -> alphabetical config name."""
    if not aggregate:
        return None
    for row in aggregate:
        row["weighted_score"] = compute_weighted_score(row, score_weights)
    sorted_rows = sorted(
        aggregate,
        key=lambda r: (
            r["weighted_score"],
            r.get("mean_precision_at_k", 0),
            r.get("mean_iou", 0),
            -r.get("mean_duplicate_ratio", 0),
            r.get("config_name", ""),
        ),
        reverse=True,
    )
    for i, row in enumerate(sorted_rows):
        row["rank"] = i + 1
        row["is_best"] = i == 0
    return sorted_rows[0]


def select_best_by_category(category_rows: list[dict], score_weights: dict) -> dict | None:
    """Select best config within one category group."""
    return select_best_config(category_rows, score_weights)





def write_summary_markdown(manifest: dict, per_video: list[dict],
                           aggregate: list[dict], category: list[dict],
                           errors: list[dict], output_path: Path):
    """Write an experiment_summary.md file with best config selection and paper tables."""
    lines = []
    add = lambda s="": lines.append(s)
    add(f"# Experiment Summary: {manifest.get('name', 'unnamed')}")
    add()
    add(f"**Description**: {manifest.get('description', '')}")
    add(f"**Videos**: {len(manifest.get('videos', []))}")
    add(f"**Categories**: {', '.join(sorted(set(v.get('category', '') for v in manifest.get('videos', []))))}")
    add()
    cfg_names = sorted(set(r["config_name"] for r in per_video))
    sw = DEFAULT_SCORE_WEIGHTS.copy()
    add(f"**Configs**: {', '.join(cfg_names)}")
    add()

    # Overall metrics table
    add("## Overall Metrics by Config")
    add("| Config | Videos | P@K | R@K | mIoU | Dup% | AvgR | Cov | #HL |")
    add("|--------|--------|-----|-----|------|------|------|-----|-----|")
    for r in aggregate:
        add(f"| **{r['config_name']}** | {r['video_count']} | {r.get('mean_precision_at_k', 0):.3f} | {r.get('mean_recall_at_k', 0):.3f} | {r.get('mean_iou', 0):.3f} | {r.get('mean_duplicate_ratio', 0)*100:.1f} | {r.get('mean_avg_human_rating', 0):.2f} | {r.get('mean_coverage_seconds', 0):.1f} | {r.get('mean_highlight_count', 0):.1f} |")
    add()

    # Category breakdown
    add("## Metrics by Category")
    add("| Category | Config | Videos | P@K | R@K | mIoU | Dup% | AvgR | #HL |")
    add("|----------|--------|-------|-----|-----|------|------|------|-----|")
    for r in sorted(category, key=lambda x: (x.get("category", ""), x.get("config_name", ""))):
        add(f"| {r.get('category', '')} | {r['config_name']} | {r['video_count']} | {r.get('mean_precision_at_k', 0):.3f} | {r.get('mean_recall_at_k', 0):.3f} | {r.get('mean_iou', 0):.3f} | {r.get('mean_duplicate_ratio', 0)*100:.1f} | {r.get('mean_avg_human_rating', 0):.2f} | {r.get('mean_highlight_count', 0):.1f} |")
    add()

    # Observations
    add("## Observations")
    for r in aggregate:
        ws = r.get("weighted_score", compute_weighted_score(r, sw))
        add(f"- **{r['config_name']}**: P@K={r.get('mean_precision_at_k', 0):.3f}, R@K={r.get('mean_recall_at_k', 0):.3f}, mIoU={r.get('mean_iou', 0):.3f}, weighted={ws:.4f}")
    add()

    # Per-category observations with best config
    cat_groups: dict[str, list[dict]] = {}
    for r in category:
        cat_groups.setdefault(r["category"], []).append(r)
    for cat, rows in sorted(cat_groups.items()):
        best_cat = select_best_by_category(rows, sw)
        if best_cat:
            add(f"- **{cat}**: best config = **{best_cat['config_name']}** (weighted={best_cat['weighted_score']:.4f})")
        else:
            add(f"- **{cat}**: no results")
        for row in rows:
            rws = row.get("weighted_score", compute_weighted_score(row, sw))
            add(f"  - {row['config_name']}: P@K={row.get('mean_precision_at_k', 0):.3f}, R@K={row.get('mean_recall_at_k', 0):.3f}, mIoU={row.get('mean_iou', 0):.3f}, weighted={rws:.4f}")
    add()

    # Best config conclusion
    best_overall = select_best_config(aggregate, sw)
    if best_overall:
        contribs = []
        for dim, w in sorted(sw.items()):
            if dim == "duplicate_ratio":
                val = best_overall.get("mean_duplicate_ratio", 0) or 0
                cval = -w * val
                contribs.append((abs(cval), f"{dim}(-{val:.3f}*{w})"))
            elif dim == "avg_human_rating":
                raw = best_overall.get("mean_avg_human_rating", 0) or 0
                nv = norm_human_rating(raw)
                cval = w * nv
                contribs.append((abs(cval), f"{dim}({raw:.2f}->{nv:.3f}*{w})"))
            else:
                val = best_overall.get(f"mean_{dim}", 0) or 0
                cval = w * val
                contribs.append((abs(cval), f"{dim}({val:.3f}*{w})"))
        contribs.sort(key=lambda x: -x[0])
        top_contrib = ", ".join(c[1] for c in contribs[:3])

        add("## Best Config Selection")
        add(f"**Score weights**: {sw}")
        add(f"**Best overall config**: **{best_overall['config_name']}** (weighted = {best_overall['weighted_score']:.4f})")
        add(f"**Top contributors**: {top_contrib}")
        add()
        add("**Config Rankings**:")
        for r in sorted(aggregate, key=lambda x: x.get("rank", 999)):
            add(f"  {r['rank']}. **{r['config_name']}** - weighted={r['weighted_score']:.4f}, P@K={r.get('mean_precision_at_k', 0):.3f}, R@K={r.get('mean_recall_at_k', 0):.3f}, mIoU={r.get('mean_iou', 0):.3f}")
        add()

    # Paper tables section
    add("## Paper-Ready Tables")
    add()
    add("### Overall Metrics")
    add("| Config | Weighted | P@K | R@K | mIoU | AvgR | Dup% | Rank | Best |")
    add("|--------|----------|-----|-----|------|------|------|------|------|")
    for r in sorted(aggregate, key=lambda x: x.get("rank", 999)):
        ws = r.get("weighted_score", compute_weighted_score(r, sw))
        add(f"| {r['config_name']} | {ws:.4f} | {r.get('mean_precision_at_k', 0):.3f} | {r.get('mean_recall_at_k', 0):.3f} | {r.get('mean_iou', 0):.3f} | {r.get('mean_avg_human_rating', 0):.2f} | {r.get('mean_duplicate_ratio', 0)*100:.1f} | {r.get('rank', '-')} | {'Y' if r.get('is_best') else ''} |")
    add()
    add("### Metrics by Category")
    add("| Category | Config | Weighted | P@K | R@K | mIoU | AvgR | Dup% | Best |")
    add("|----------|--------|----------|-----|-----|------|------|------|------|")
    for r in sorted(category, key=lambda x: (x.get("category", ""), x.get("config_name", ""))):
        rws = r.get("weighted_score", compute_weighted_score(r, sw))
        add(f"| {r.get('category', '')} | {r['config_name']} | {rws:.4f} | {r.get('mean_precision_at_k', 0):.3f} | {r.get('mean_recall_at_k', 0):.3f} | {r.get('mean_iou', 0):.3f} | {r.get('mean_avg_human_rating', 0):.2f} | {r.get('mean_duplicate_ratio', 0)*100:.1f} | {'Y' if r.get('is_best') else ''} |")
    add()
    add("### Per-Video Metrics")
    add("| Video | Category | Config | Weighted | P@K | R@K | mIoU | Duration | Error |")
    add("|-------|----------|--------|----------|-----|-----|------|----------|-------|")
    for r in sorted(per_video, key=lambda x: (x.get("video_id", ""), x.get("config_name", ""))):
        add(f"| {r.get('video_id', '')} | {r.get('category', '')} | {r['config_name']} | - | {r.get('precision_at_k', 0):.3f} | {r.get('recall_at_k', 0):.3f} | {r.get('iou', 0):.3f} | {r.get('coverage_seconds', 0):.1f}s | {'!' if r.get('error') else ''} |")
    add()

    if errors:
        add("## Errors")
        add("| Video | Category | Error |")
        add("|-------|----------|-------|")
        for e in errors:
            add(f"| {e.get('video_id', '')} | {e.get('category', '')} | {e.get('error', '')} |")
        add()

    add("---")
    add("*Generated by run_highlight_eval_batch.py*")

    output_path.write_text("\n".join(lines), encoding="utf-8")



def run_batch_evaluation(
    manifest_path: str,
    config_files: list[str],
    output_dir: str,
    top_k: int = 3,
    iou_threshold: float = 0.3,
    score_weights: dict | None = None,
    paper_tables: bool = True,
    fail_fast: bool = False,
):
    """Run rescore evaluation for all videos in the manifest and write outputs."""
    manifest = load_manifest(manifest_path)
    score_weights = score_weights or DEFAULT_SCORE_WEIGHTS.copy()
    base_dir = Path(manifest_path).parent
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Save run config
    run_cfg = {
        "manifest": manifest_path,
        "configs": config_files,
        "top_k": top_k,
        "iou_threshold": iou_threshold,
        "fail_fast": fail_fast,
    }
    (out / "run_config.json").write_text(json.dumps(run_cfg, indent=2), encoding="utf-8")

    # Load configs once
    configs = [load_config(cf) for cf in config_files]

    per_video: list[dict] = []
    errors: list[dict] = []

    for v in manifest["videos"]:
        vid = v["video_id"]
        category = v.get("category", "unknown")
        candidates_path = str((base_dir / v["candidates_json"]).resolve())
        labels_path = str((base_dir / v["labels_json"]).resolve())
        duration = v.get("duration", 0.0)

        try:
            candidates_data = load_candidates(candidates_path)
            labels = load_labels(labels_path)

            for cfg in configs:
                cfg_name = cfg.get("name", "unnamed")
                weights = cfg.get("weights", {})
                dl = cfg.get("diversity_lambda", 0.15)

                predictions = rescore_candidates(
                    candidates_data["candidates"],
                    weights,
                    top_k=top_k,
                    min_score=cfg.get("min_score", 0.0),
                    min_duration=cfg.get("min_duration", 0),
                    max_duration=cfg.get("max_duration", 999),
                    diversity_lambda=dl,
                )

                metrics = evaluate_config(
                    predictions, labels, cfg, iou_th=iou_threshold, top_k=top_k
                )

                row = {
                    "video_id": vid,
                    "category": category,
                    "config_name": cfg_name,
                    "top_k": top_k,
                    "iou_threshold": iou_threshold,
                    **{k: metrics.get(_METRIC_SRC.get(k, k), 0) for k in _METRIC_FIELDS},
                    "error": "",
                }
                per_video.append(row)

        except Exception as e:
            err_msg = str(e).split("\\n")[0][:200]
            errors.append({"video_id": vid, "category": category, "error": err_msg})

            for cfg in configs:
                cfg_name = cfg.get("name", "unnamed")
                row = {
                    "video_id": vid, "category": category,
                    "config_name": cfg_name, "top_k": top_k,
                    "iou_threshold": iou_threshold,
                    **{k: 0.0 for k in _METRIC_FIELDS},
                    "error": err_msg,
                }
                per_video.append(row)

            if fail_fast:
                raise

    # Write per-video CSV
    fieldnames = ["video_id", "category", "config_name", "top_k", "iou_threshold",
                  *sorted(_METRIC_FIELDS), "error"]
    csv_path = out / "per_video_metrics.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(per_video)

    # Write errors JSON
    (out / "errors.json").write_text(json.dumps(errors, indent=2, ensure_ascii=False), encoding="utf-8")

    # Aggregate
    aggregate = aggregate_by_config(per_video)
    agg_csv_path = out / "aggregate_metrics.csv"
    agg_fields = ["config_name", "video_count"] + [f"mean_{f}" for f in _METRIC_FIELDS]
    with open(agg_csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=agg_fields)
        w.writeheader()
        w.writerows(aggregate)

    # Aggregate JSON
    (out / "aggregate_metrics.json").write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False), encoding="utf-8")

    # Category aggregation
    cat_agg = aggregate_by_category(per_video)
    cat_csv_path = out / "category_metrics.csv"
    cat_fields = ["category", "config_name", "video_count"] + [f"mean_{f}" for f in _METRIC_FIELDS]
    with open(cat_csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cat_fields)
        w.writeheader()
        w.writerows(cat_agg)

    # Summary markdown
    write_summary_markdown(manifest, per_video, aggregate, cat_agg, errors,
                           out / "experiment_summary.md")

    # Best config selection and paper tables
    best_overall = select_best_config(aggregate, score_weights)
    if best_overall:
        (out / "best_config.json").write_text(
            json.dumps({"config_name": best_overall["config_name"],
                        "weighted_score": best_overall["weighted_score"],
                        "rank": 1, "is_best": True}, indent=2), encoding="utf-8")

    if paper_tables:
        write_paper_tables(aggregate, cat_agg, per_video, score_weights, out)

    print(f"\\nBatch evaluation complete: {len(per_video)} rows, {len(errors)} errors")
    if errors:
        print(f"  Errors: {len(errors)} — see {out / 'errors.json'}")
    print(f"  Per-video:    {csv_path}")
    print(f"  Aggregate:    {agg_csv_path}")
    print(f"  Category:     {cat_csv_path}")
    print(f"  Summary:      {out / 'experiment_summary.md'}")
    if best_overall:
        bname = best_overall["config_name"]
        bscore = best_overall["weighted_score"]
        print(f"  Best config:  {bname} (weighted={bscore:.4f})")
    print(f"  Paper tables: {out / 'paper_table_overall.md'}, {out / 'paper_table_by_category.md'}, {out / 'paper_table_per_video.md'}")

    return per_video, aggregate, cat_agg, errors


# ── Main ─────────────────────────────────────────────

# ── Paper-Ready Table Generators ──────────────────────


def write_paper_tables(aggregate, category, per_video, score_weights, out):
    """Write three paper-ready markdown tables."""
    write_paper_table_overall(aggregate, score_weights, out)
    write_paper_table_by_category(category, score_weights, out)
    write_paper_table_per_video(per_video, score_weights, out)


def write_paper_table_overall(aggregate, score_weights, out):
    """Write paper_table_overall.md."""
    lines = ["# Paper Table \u2014 Overall Metrics\n"]
    lines.append("| Config | Weighted | P@K | R@K | mIoU | AvgR | Dup% | Rank | Best |")
    lines.append("|--------|----------|-----|-----|------|------|------|------|------|")
    for r in sorted(aggregate, key=lambda x: x.get("rank", 999)):
        ws = r.get("weighted_score", 0)
        lines.append(
            f"| {r['config_name']} | {ws:.4f} | {r.get('mean_precision_at_k', 0):.3f} "
            f"| {r.get('mean_recall_at_k', 0):.3f} | {r.get('mean_iou', 0):.3f} "
            f"| {r.get('mean_avg_human_rating', 0):.2f} | {r.get('mean_duplicate_ratio', 0)*100:.1f} "
            f"| {r.get('rank', '-')} | {'Y' if r.get('is_best') else ''} |"
        )
    lines.append("")
    lines.append("*Score weights: " + str(score_weights) + "*")
    (out / "paper_table_overall.md").write_text("\n".join(lines), encoding="utf-8")


def write_paper_table_by_category(category, score_weights, out):
    """Write paper_table_by_category.md with per-category best highlighted."""
    lines = ["# Paper Table \u2014 Metrics by Category\n"]
    lines.append("| Category | Config | Weighted | P@K | R@K | mIoU | AvgR | Dup% | Best |")
    lines.append("|----------|--------|----------|-----|-----|------|------|------|------|")
    cat_groups = {}
    for r in category:
        cat_groups.setdefault(r.get("category", ""), []).append(r)
    for cat in sorted(cat_groups):
        rows = cat_groups[cat]
        for r in rows:
            ws_val = 0.0
            for dk, dw in score_weights.items():
                if dk == "avg_human_rating":
                    raw = r.get("mean_avg_human_rating", 0) or 0
                    nv = max(0.0, min(1.0, (raw - 1.0) / 4.0))
                    ws_val += dw * nv
                elif dk == "duplicate_ratio":
                    ws_val -= dw * (r.get("mean_duplicate_ratio", 0) or 0)
                else:
                    ws_val += dw * (r.get("mean_" + dk, 0) or 0)
            r["weighted_score"] = round(ws_val, 4)
        sorted_rows = sorted(rows, key=lambda x: (
            x.get("weighted_score", 0),
            x.get("mean_precision_at_k", 0),
            x.get("mean_iou", 0),
        ), reverse=True)
        best_name = sorted_rows[0]["config_name"] if sorted_rows else ""
        for r in sorted(rows, key=lambda x: x.get("config_name", "")):
            ws = r.get("weighted_score", 0)
            is_best = r["config_name"] == best_name
            lines.append(
                f"| {cat} | {r['config_name']} | {ws:.4f} | {r.get('mean_precision_at_k', 0):.3f} "
                f"| {r.get('mean_recall_at_k', 0):.3f} | {r.get('mean_iou', 0):.3f} "
                f"| {r.get('mean_avg_human_rating', 0):.2f} | {r.get('mean_duplicate_ratio', 0)*100:.1f} "
                f"| {'Y' if is_best else ''} |"
            )
    lines.append("")
    lines.append("*Score weights: " + str(score_weights) + "*")
    (out / "paper_table_by_category.md").write_text("\n".join(lines), encoding="utf-8")
def write_paper_table_per_video(per_video, score_weights, out):
    """Write paper_table_per_video.md."""
    lines = ["# Paper Table \u2014 Per-Video Metrics\n"]
    lines.append("| Video | Category | Config | P@K | R@K | mIoU | Dup% | Cov(s) | Dur(s) | HL | Error |")
    lines.append("|-------|----------|--------|-----|-----|------|------|--------|--------|----|-------|")
    for r in sorted(per_video, key=lambda x: (x.get("video_id", ""), x.get("config_name", ""))):
        lines.append(
            f"| {r.get('video_id', '')} | {r.get('category', '')} | {r['config_name']} "
            f"| {r.get('precision_at_k', 0):.3f} | {r.get('recall_at_k', 0):.3f} | {r.get('iou', 0):.3f} "
            f"| {r.get('duplicate_ratio', 0)*100:.1f} | {r.get('coverage_seconds', 0):.1f} "
            f"| {r.get('avg_pred_duration', 0):.1f} | {r.get('highlight_count', 0)} "
            f"| {'!' if r.get('error') else ''} |"
        )
    (out / "paper_table_per_video.md").write_text("\n".join(lines), encoding="utf-8")




def main():
    parser = argparse.ArgumentParser(
        description="Batch highlight evaluation across multiple videos."
    )
    parser.add_argument("--manifest", required=True,
                        help="Path to manifest JSON file")
    parser.add_argument("--configs", required=True, nargs="+",
                        help="Weight config JSON files")
    parser.add_argument("--output-dir", required=True,
                        help="Output directory for results")
    parser.add_argument("--top-k", type=int, default=3,
                        help="Top-K predictions (default: 3)")
    parser.add_argument("--score-weights", type=str, default=None,
                        help=(
                            "Weight dims for best-config selection: "
                            "'precision_at_k=0.30,recall_at_k=0.20,mean_iou=0.25,"
                            "avg_human_rating=0.20,duplicate_ratio=0.05'"
                        ))
    parser.add_argument("--iou-threshold", type=float, default=0.3,
                        help="Minimum IoU for match (default: 0.3)")
    parser.add_argument("--fail-fast", action="store_true",
                        help="Exit on first error")

    args = parser.parse_args()

    run_batch_evaluation(
        manifest_path=args.manifest,
        config_files=args.configs,
        output_dir=args.output_dir,
        top_k=args.top_k,
        iou_threshold=args.iou_threshold,
        score_weights=parse_score_weights(args.score_weights) if args.score_weights else None,
        paper_tables=True,
        fail_fast=args.fail_fast,
    )


if __name__ == "__main__":
    main()
