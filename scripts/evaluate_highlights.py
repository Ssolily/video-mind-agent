"""Evaluate / rescore highlight scoring against ground-truth labels.

Modes:
  existing  — evaluate already-computed highlights by sorting/selection.
  rescore   — load candidates, apply config weights, select, then evaluate.
"""

import argparse, csv, json, math, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

IOU_THRESHOLD = 0.3

# ── Constants for schema validation ────────────────────────────────────────

ALLOWED_SCORE_KEYS = {"object", "motion", "speech", "scene", "quality"}

# ── Loaders ────────────────────────────────────────────────────────────────

def load_labels(path: str) -> list[dict]:
    """Load ground-truth label file, validate fields."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    labels = data.get("labels", data)
    if isinstance(labels, dict):
        labels = [labels]
    for i, lbl in enumerate(labels):
        st = lbl.get("start_time", lbl.get("start", 0))
        et = lbl.get("end_time", lbl.get("end", 0))
        rating = lbl.get("rating", 3)
        if st < 0 or et < 0:
            raise ValueError(f"Label {i}: negative time")
        if et <= st:
            raise ValueError(f"Label {i}: end_time ({et}) <= start_time ({st})")
        if not (1 <= rating <= 5):
            raise ValueError(f"Label {i}: rating {rating} not in [1,5]")
        lbl["start_time"] = st
        lbl["end_time"] = et
        lbl["rating"] = rating
        if "id" not in lbl:
            lbl["id"] = f"gt_{i+1:03d}"
        vid_dur = data.get("duration")
        if vid_dur and et > vid_dur:
            raise ValueError(f"Label {i}: end_time {et} exceeds video duration {vid_dur}")
    return labels


def load_config(path: str) -> dict:
    """Load a weight config JSON file and validate."""
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    weights = cfg.get("weights", cfg)
    w_sum = sum(weights.get(k, 0) for k in ALLOWED_SCORE_KEYS)
    if abs(w_sum - 1.0) > 0.01:
        raise ValueError(
            f"Config '{cfg.get('name', path)}': content weights sum to {w_sum}, expected 1.0. "
            f"Weights: {weights}"
        )
    for k in ALLOWED_SCORE_KEYS:
        if k not in weights:
            weights[k] = 0.0
    cfg["weights"] = weights
    cfg.setdefault("name", Path(path).stem)
    cfg.setdefault("diversity_lambda", 0.15)
    cfg.setdefault("min_score", 0.0)
    cfg.setdefault("min_duration", 3.0)
    cfg.setdefault("max_duration", 45.0)
    cfg.setdefault("top_k", 5)
    return cfg


def load_result_highlights(path: str) -> tuple[str, float, list[dict]]:
    """Load highlights from a result JSON (or report JSON)."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    highlights = data.get("highlights", data.get("recommendations", []))
    if isinstance(highlights, dict):
        highlights = list(highlights.values())
    video_id = data.get("video_id", data.get("id", Path(path).stem))
    duration = data.get("duration", data.get("video_info", {}).get("duration", 0))
    return video_id, duration, highlights


# ── Candidates schema & loader ─────────────────────────────────────────────

def validate_candidate(c: dict, idx: int, duration: float):
    """Validate a single candidate entry."""
    st = c.get("start_time", 0)
    et = c.get("end_time", 0)
    dur = c.get("duration", et - st)
    scores = c.get("scores", {})

    if st < 0 or et < 0:
        raise ValueError(f"Candidate {idx}: negative time")
    if et <= st:
        raise ValueError(f"Candidate {idx}: end_time ({et}) <= start_time ({st})")
    if duration > 0 and et > duration:
        raise ValueError(f"Candidate {idx}: end_time {et} exceeds duration {duration}")

    for k in ALLOWED_SCORE_KEYS:
        v = scores.get(k)
        if v is None:
            raise ValueError(f"Candidate {idx}: missing score key '{k}'")
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            raise ValueError(f"Candidate {idx}: score '{k}' is NaN/Infinity")
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Candidate {idx}: score '{k}' = {v} not in [0, 1]")

    c["start_time"] = st
    c["end_time"] = et
    c["duration"] = dur


def load_candidates(path: str) -> dict:
    """Load and validate a candidates JSON file.

    Returns dict with keys: video_id, duration, candidates (list).
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "candidates" not in data:
        raise ValueError("Missing 'candidates' array in candidates JSON")
    if data.get("schema_version", 0) < 1:
        raise ValueError("schema_version must be >= 1")

    video_id = data.get("video_id", Path(path).stem)
    duration = data.get("duration", 0.0)
    candidates = data["candidates"]

    for i, c in enumerate(candidates):
        validate_candidate(c, i, duration)

    return {"video_id": video_id, "duration": duration, "candidates": candidates}


# ── Rescore logic ──────────────────────────────────────────────────────────

def rescore_candidates(candidates: list[dict], weights: dict, top_k: int,
                       min_score: float, min_duration: float, max_duration: float,
                       diversity_lambda: float) -> list[dict]:
    """Apply config weights to candidates and select top-K with diversity.

    Returns scored predictions sorted by selection_score descending.
    """
    # Compute base_score for every candidate
    scored = []
    for i, c in enumerate(candidates):
        dur = c.get("duration", c["end_time"] - c["start_time"])
        if dur < min_duration or dur > max_duration:
            continue

        s = c["scores"]
        base = sum(weights[k] * s[k] for k in ALLOWED_SCORE_KEYS)
        if base < min_score:
            continue

        # Build score_breakdown
        breakdown = {}
        for k in ALLOWED_SCORE_KEYS:
            breakdown[k] = {
                "raw": round(s[k], 4),
                "weight": weights[k],
                "weighted": round(weights[k] * s[k], 4),
            }

        scored.append({
            "id": c.get("id", f"cand_{i+1:04d}"),
            "start_time": c["start_time"],
            "end_time": c["end_time"],
            "duration": dur,
            "base_score": round(base, 4),
            "score_breakdown": breakdown,
            "_diversity_lambda": diversity_lambda,
        })

    # Greedy selection with diversity penalty
    selected = []
    remaining = sorted(scored, key=lambda x: -x["base_score"])

    for cand in remaining:
        # Compute overlap penalty against already-selected
        max_overlap = 0.0
        for sel in selected:
            s = max(cand["start_time"], sel["start_time"])
            e = min(cand["end_time"], sel["end_time"])
            inter = max(0.0, e - s)
            if inter > 0:
                union = max(cand["end_time"] - cand["start_time"],
                            sel["end_time"] - sel["start_time"], 1e-6)
                max_overlap = max(max_overlap, inter / union)

        overlap_penalty = diversity_lambda * max_overlap
        selection_score = max(0.0, min(1.0, cand["base_score"] - overlap_penalty))

        cand["overlap_penalty"] = round(overlap_penalty, 4)
        cand["selection_score"] = round(selection_score, 4)
        cand["score"] = cand["selection_score"]
        selected.append(cand)

    # Sort by selection_score descending, keep top_k
    selected.sort(key=lambda x: -x["selection_score"])
    return selected[:top_k]


# ── Metric helpers ─────────────────────────────────────────────────────────

def temporal_iou(a: dict, b: dict) -> float:
    s = max(a["start_time"], b["start_time"])
    e = min(a["end_time"], b["end_time"])
    inter = max(0.0, e - s)
    union = max(a["end_time"] - a["start_time"], b["end_time"] - b["start_time"], 1e-6)
    return inter / union


def precision_at_k(highlights: list[dict], labels: list[dict], k: int, iou_th: float) -> float:
    if not highlights or k <= 0:
        return 0.0
    hits = 0
    for h in highlights[:k]:
        for lbl in labels:
            if temporal_iou(h, lbl) >= iou_th:
                hits += 1
                break
    return hits / min(k, len(highlights))


def recall_at_k(highlights: list[dict], labels: list[dict], k: int, iou_th: float) -> float:
    if not labels or not highlights or k <= 0:
        return 0.0
    hit_labels = set()
    for h in highlights[:k]:
        for gi, lbl in enumerate(labels):
            if temporal_iou(h, lbl) >= iou_th:
                hit_labels.add(gi)
                break
    return len(hit_labels) / len(labels)


def mean_temporal_iou(highlights: list[dict], labels: list[dict]) -> float:
    if not highlights or not labels:
        return 0.0
    bests = [max((temporal_iou(h, lbl) for lbl in labels), default=0.0) for h in highlights]
    return sum(bests) / len(bests)


def avg_human_rating(highlights: list[dict], labels: list[dict], iou_th: float) -> float:
    ratings = []
    for h in highlights:
        for lbl in labels:
            if temporal_iou(h, lbl) >= iou_th:
                ratings.append(lbl.get("rating", 0))
                break
    return sum(ratings) / len(ratings) if ratings else 0.0


def duplicate_ratio(highlights: list[dict], iou_th: float = 0.5) -> float:
    if len(highlights) < 2:
        return 0.0
    pairs = 0
    dup = 0
    for i in range(len(highlights)):
        for j in range(i + 1, len(highlights)):
            pairs += 1
            if temporal_iou(highlights[i], highlights[j]) > iou_th:
                dup += 1
    return dup / pairs if pairs > 0 else 0.0


def coverage_seconds(highlights: list[dict]) -> float:
    if not highlights:
        return 0.0
    segs = sorted(((h["start_time"], h["end_time"]) for h in highlights), key=lambda x: x[0])
    merged = []
    for st, et in segs:
        if merged and st <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], et))
        else:
            merged.append((st, et))
    return sum(et - st for st, et in merged)


def avg_pred_duration(highlights: list[dict]) -> float:
    if not highlights:
        return 0.0
    return sum(h.get("duration", h["end_time"] - h["start_time"]) for h in highlights) / len(highlights)


def build_matches(highlights: list[dict], labels: list[dict], config_name: str, iou_th: float) -> list[dict]:
    matches = []
    for h in highlights:
        best_iou = 0.0
        best_lbl = None
        for lbl in labels:
            iou = temporal_iou(h, lbl)
            if iou > best_iou:
                best_iou = iou
                best_lbl = lbl
        m = {
            "prediction_id": h.get("id", "?"),
            "prediction_start": h["start_time"],
            "prediction_end": h["end_time"],
            "iou": round(best_iou, 4),
        }
        if best_lbl and best_iou >= iou_th:
            m["matched_label_id"] = best_lbl.get("id", "?")
            m["rating"] = best_lbl.get("rating", 0)
        else:
            m["matched_label_id"] = None
            m["rating"] = None
        matches.append(m)
    return matches


# ── Evaluation runner ──────────────────────────────────────────────────────

def evaluate_config(highlights: list[dict], labels: list[dict], config: dict, iou_th: float, top_k: int) -> dict:
    """Compute all metrics for one config on one set of highlights."""
    hl_sorted = sorted(
        highlights,
        key=lambda h: h.get("selection_score", h.get("score", 0)),
        reverse=True,
    )
    p = precision_at_k(hl_sorted, labels, top_k, iou_th)
    r = recall_at_k(hl_sorted, labels, top_k, iou_th)
    return {
        "config_name": config["name"],
        "top_k": top_k,
        "iou_threshold": iou_th,
        "highlight_count": len(hl_sorted),
        "precision_at_k": round(p, 4),
        "recall_at_k": round(r, 4),
        "mean_iou": round(mean_temporal_iou(hl_sorted, labels), 4),
        "avg_human_rating": round(avg_human_rating(hl_sorted, labels, iou_th), 4),
        "duplicate_ratio": round(duplicate_ratio(hl_sorted), 4),
        "coverage_seconds": round(coverage_seconds(hl_sorted), 2),
        "avg_pred_duration": round(avg_pred_duration(hl_sorted), 2),
    }


def run_evaluation(labels_file: str, config_files: list[str], result_highlights: list[dict],
                   output_dir: str, iou_th: float, top_k: int, result_video_id: str,
                   rescore_predictions: dict[str, list[dict]] | None = None) -> list[dict]:
    """Run evaluation for all configs and write output files."""
    labels = load_labels(labels_file)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    all_metrics = []
    for cf in config_files:
        cfg = load_config(cf)
        name = cfg["name"]

        # Use rescore predictions if provided, else use the provided highlights
        if rescore_predictions and name in rescore_predictions:
            hl = rescore_predictions[name]
        else:
            hl = result_highlights

        metrics = evaluate_config(hl, labels, cfg, iou_th, top_k)
        metrics["video_id"] = result_video_id
        all_metrics.append(metrics)

        # Per-config matches
        matches = build_matches(hl, labels, name, iou_th)
        (out / f"matches_{name}.json").write_text(
            json.dumps({"config_name": name, "matches": matches}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # metrics.csv
    csv_path = out / "metrics.csv"
    fieldnames = [
        "config_name", "video_id", "top_k", "iou_threshold",
        "precision_at_k", "recall_at_k", "mean_iou", "avg_human_rating",
        "duplicate_ratio", "coverage_seconds", "avg_pred_duration", "highlight_count",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_metrics)

    # metrics.json
    (out / "metrics.json").write_text(json.dumps(all_metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    # run_config.json
    run_cfg = {
        "labels_file": str(Path(labels_file).resolve()),
        "config_files": [str(Path(f).resolve()) for f in config_files],
        "iou_threshold": iou_th,
        "top_k": top_k,
        "video_id": result_video_id,
        "highlight_count": len(result_highlights),
        "rescore_predictions": list(rescore_predictions.keys()) if rescore_predictions else None,
    }
    (out / "run_config.json").write_text(json.dumps(run_cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    return all_metrics


def print_summary(metrics: list[dict]):
    header = f"{'Config':<25} {'P@K':<8} {'R@K':<8} {'mIoU':<8} {'Dup%':<8} {'AvgR':<6} {'Cov':<8} {'#HL':<5}"
    print(header)
    print("-" * len(header))
    for m in metrics:
        print(
            f"{m['config_name']:<25} "
            f"{m['precision_at_k']:<8.3f} "
            f"{m['recall_at_k']:<8.3f} "
            f"{m['mean_iou']:<8.3f} "
            f"{m['duplicate_ratio']:<8.3f} "
            f"{m['avg_human_rating']:<6.2f} "
            f"{m['coverage_seconds']:<8.1f} "
            f"{m['highlight_count']:<5}"
        )


# ── CLI ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate / rescore highlight scoring against ground-truth labels."
    )
    parser.add_argument(
        "--mode", choices=["existing", "rescore"], default="existing",
        help="Mode: existing (evaluate pre-computed highlights) or rescore (load candidates, re-score, evaluate)",
    )
    parser.add_argument(
        "--result-json", help="Path to a result JSON containing highlights (existing mode only)"
    )
    parser.add_argument(
        "--result-dir", help="Directory containing per-video report dirs (existing mode only)"
    )
    parser.add_argument(
        "--candidates-json", help="Path to candidates JSON file (rescore mode only)"
    )
    parser.add_argument("--labels", required=True, help="Path to ground-truth label JSON")
    parser.add_argument("--configs", required=True, nargs="+", help="Weight config JSON files")
    parser.add_argument("--output-dir", required=True, help="Output directory")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K predictions (default: 5)")
    parser.add_argument("--iou-threshold", type=float, default=IOU_THRESHOLD,
                        help=f"Minimum IoU for match (default: {IOU_THRESHOLD})")

    args = parser.parse_args()

    # Validate args
    if args.mode == "existing":
        if not args.result_json and not args.result_dir:
            print("ERROR: existing mode requires --result-json or --result-dir")
            sys.exit(1)
        if args.candidates_json:
            print("WARNING: --candidates-json ignored in existing mode")
    elif args.mode == "rescore":
        if not args.candidates_json:
            print("ERROR: rescore mode requires --candidates-json")
            sys.exit(1)
        if args.result_json:
            print("WARNING: --result-json ignored in rescore mode")
        if args.result_dir:
            print("WARNING: --result-dir ignored in rescore mode")

    # Load data
    if args.mode == "existing":
        if args.result_json:
            video_id, duration, highlights = load_result_highlights(args.result_json)
        else:
            result_dir = Path(args.result_dir)
            result_file = None
            for f in result_dir.rglob("final_report.json"):
                result_file = f; break
            if not result_file:
                for f in result_dir.rglob("*.json"):
                    if "report" in f.name.lower() or "result" in f.name.lower():
                        result_file = f; break
            if not result_file:
                print(f"ERROR: No result JSON found in {args.result_dir}")
                sys.exit(1)
            video_id, duration, highlights = load_result_highlights(str(result_file))

        print(f"Mode:           existing")
        print(f"Video ID:       {video_id}")
        print(f"Duration:       {duration}s")
        print(f"Highlights:     {len(highlights)}")
        print(f"Labels file:    {args.labels}")
        print(f"Configs:        {args.configs}")
        print(f"Top-K:          {args.top_k}")
        print(f"IoU threshold:  {args.iou_threshold}")
        print(f"Output dir:     {args.output_dir}")
        print()

        metrics = run_evaluation(
            labels_file=args.labels,
            config_files=args.configs,
            result_highlights=highlights,
            output_dir=args.output_dir,
            iou_th=args.iou_threshold,
            top_k=args.top_k,
            result_video_id=video_id,
        )
    else:
        # rescore mode
        cand_data = load_candidates(args.candidates_json)
        video_id = cand_data["video_id"]
        duration = cand_data["duration"]
        candidates = cand_data["candidates"]
        labels = load_labels(args.labels)

        print(f"Mode:           rescore")
        print(f"Video ID:       {video_id}")
        print(f"Duration:       {duration}s")
        print(f"Candidates:     {len(candidates)}")
        print(f"Labels file:    {args.labels}")
        print(f"Configs:        {args.configs}")
        print(f"Top-K:          {args.top_k}")
        print(f"IoU threshold:  {args.iou_threshold}")
        print(f"Output dir:     {args.output_dir}")
        print()

        out = Path(args.output_dir)
        out.mkdir(parents=True, exist_ok=True)

        # Run rescore for each config
        rescore_predictions = {}
        for cf in args.configs:
            cfg = load_config(cf)
            name = cfg["name"]
            predictions = rescore_candidates(
                candidates=candidates,
                weights=cfg["weights"],
                top_k=args.top_k,
                min_score=cfg.get("min_score", 0.0),
                min_duration=cfg.get("min_duration", 3.0),
                max_duration=cfg.get("max_duration", 45.0),
                diversity_lambda=cfg.get("diversity_lambda", 0.15),
            )
            rescore_predictions[name] = predictions

            # Save predictions_{config}.json
            (out / f"predictions_{name}.json").write_text(
                json.dumps({"config_name": name, "predictions": predictions},
                           indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        # Evaluate rescored predictions using standard metrics
        metrics = run_evaluation(
            labels_file=args.labels,
            config_files=args.configs,
            result_highlights=[],  # not used when rescore_predictions is provided
            output_dir=args.output_dir,
            iou_th=args.iou_threshold,
            top_k=args.top_k,
            result_video_id=video_id,
            rescore_predictions=rescore_predictions,
        )

    print_summary(metrics)
    csv_path = Path(args.output_dir) / "metrics.csv"
    json_path = Path(args.output_dir) / "metrics.json"
    print(f"\nResults saved to:")
    print(f"  CSV:  {csv_path}")
    print(f"  JSON: {json_path}")
    if args.mode == "rescore":
        for name in rescore_predictions:
            print(f"  Predictions ({name}): {out / f'predictions_{name}.json'}")


if __name__ == "__main__":
    main()
