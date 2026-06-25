"""Tests for batch highlight evaluation (manifest loading, aggregation, batch run)."""

import json, sys, tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))


def _make_candidates(video_id: str, duration: float = 30.0, count: int = 3):
    return {
        "schema_version": 1,
        "video_id": video_id,
        "duration": duration,
        "generated_at": "2026-06-20T12:00:00Z",
        "candidates": [
            {
                "id": f"cand_{i+1:04d}",
                "start_time": float(i * 10), "end_time": float(i * 10 + 8), "duration": 8.0,
                "scores": {"object": 0.5, "motion": 0.4, "speech": 0.3, "scene": 0.2, "quality": 0.7},
            }
            for i in range(count)
        ],
    }


def _make_labels(video_id: str, count: int = 2):
    return {
        "video_id": video_id, "duration": 30.0,
        "labels": [
            {"id": f"gt_{i+1:03d}", "start_time": float(i * 5), "end_time": float(i * 5 + 4),
             "rating": 5, "category": "test"}
            for i in range(count)
        ],
    }


def _make_config(name: str = "test_cfg", weights: dict = None):
    if weights is None:
        weights = {"object": 0.25, "motion": 0.25, "speech": 0.25, "scene": 0.25, "quality": 0.0}
    return {"name": name, "weights": weights}


@pytest.fixture
def batch_env(tmp_path):
    """Set up a temp directory tree with manifest, candidates, labels, configs."""
    # Create dirs
    cans_dir = tmp_path / "candidates"
    labs_dir = tmp_path / "labels"
    cfgs_dir = tmp_path / "configs"
    out_dir = tmp_path / "results"
    for d in (cans_dir, labs_dir, cfgs_dir, out_dir):
        d.mkdir()

    # Write candidates
    cand1 = _make_candidates("vid_a", 30.0, 3)
    (cans_dir / "vid_a_candidates.json").write_text(json.dumps(cand1), encoding="utf-8")
    cand2 = _make_candidates("vid_b", 40.0, 4)
    (cans_dir / "vid_b_candidates.json").write_text(json.dumps(cand2), encoding="utf-8")

    # Write labels
    (labs_dir / "vid_a_labels.json").write_text(json.dumps(_make_labels("vid_a")), encoding="utf-8")
    (labs_dir / "vid_b_labels.json").write_text(json.dumps(_make_labels("vid_b")), encoding="utf-8")

    # Write config
    cfg = _make_config("baseline", {"object": 0.25, "motion": 0.25, "speech": 0.25, "scene": 0.25, "quality": 0.0})
    (cfgs_dir / "baseline.json").write_text(json.dumps(cfg), encoding="utf-8")

    # Write manifest
    manifest = {
        "schema_version": 1,
        "name": "test_batch",
        "videos": [
            {"video_id": "vid_a", "category": "lecture", "duration": 30.0,
             "candidates_json": "candidates/vid_a_candidates.json",
             "labels_json": "labels/vid_a_labels.json"},
            {"video_id": "vid_b", "category": "sports", "duration": 40.0,
             "candidates_json": "candidates/vid_b_candidates.json",
             "labels_json": "labels/vid_b_labels.json"},
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    return {
        "tmp": tmp_path,
        "manifest": manifest_path,
        "configs": [str(cfgs_dir / "baseline.json")],
        "output": out_dir,
    }


# ── Manifest tests ───────────────────────────────────


class TestManifest:
    def test_load_manifest(self, batch_env):
        from run_highlight_eval_batch import load_manifest
        m = load_manifest(str(batch_env["manifest"]))
        assert m["schema_version"] == 1
        assert len(m["videos"]) == 2

    def test_missing_schema_version(self, tmp_path):
        from run_highlight_eval_batch import validate_manifest
        with pytest.raises(ValueError, match="schema_version"):
            validate_manifest({"videos": [{"video_id": "v1", "category": "x", "duration": 10.0,
                                           "candidates_json": "nonexist.json", "labels_json": "nonexist.json"}]}, tmp_path)

    def test_duplicate_video_id(self, tmp_path):
        from run_highlight_eval_batch import validate_manifest
        (tmp_path / "nope.json").write_text("{}", encoding="utf-8")
        (tmp_path / "labels.json").write_text("{}", encoding="utf-8")
        m = {"schema_version": 1, "videos": [
            {"video_id": "v1", "category": "x", "duration": 10.0,
             "candidates_json": "nope.json", "labels_json": "labels.json"},
            {"video_id": "v1", "category": "x", "duration": 10.0,
             "candidates_json": "nope.json", "labels_json": "labels.json"},
        ]}
        with pytest.raises(ValueError, match="Duplicate"):
            validate_manifest(m, tmp_path)

    def test_absolute_path_rejected(self, tmp_path):
        from run_highlight_eval_batch import validate_manifest
        m = {"schema_version": 1, "videos": [
            {"video_id": "v1", "category": "x", "duration": 10.0,
             "candidates_json": "C:/bad/path.json", "labels_json": "labels.json"}
        ]}
        with pytest.raises(ValueError, match="absolute path"):
            validate_manifest(m, tmp_path)

    def test_file_not_found(self, tmp_path):
        from run_highlight_eval_batch import validate_manifest
        m = {"schema_version": 1, "videos": [
            {"video_id": "v1", "category": "x", "duration": 10.0,
             "candidates_json": "nonexist.json", "labels_json": "labels.json"}
        ]}
        # Create labels file but not candidates
        (tmp_path / "labels.json").write_text("{}", encoding="utf-8")
        with pytest.raises(FileNotFoundError):
            validate_manifest(m, tmp_path)


# ── Aggregation tests ────────────────────────────────


class TestAggregation:
    def test_aggregate_by_config(self):
        from run_highlight_eval_batch import aggregate_by_config
        rows = [
            {"config_name": "baseline", "precision_at_k": 0.8, "recall_at_k": 0.6,
             "mean_iou": 0.5, "avg_human_rating": 4.0, "duplicate_ratio": 0.1,
             "coverage_seconds": 20.0, "avg_pred_duration": 10.0, "highlight_count": 3},
            {"config_name": "baseline", "precision_at_k": 1.0, "recall_at_k": 0.8,
             "mean_iou": 0.7, "avg_human_rating": 4.5, "duplicate_ratio": 0.0,
             "coverage_seconds": 30.0, "avg_pred_duration": 12.0, "highlight_count": 4},
            {"config_name": "speech", "precision_at_k": 0.5, "recall_at_k": 0.4,
             "mean_iou": 0.3, "avg_human_rating": 3.0, "duplicate_ratio": 0.2,
             "coverage_seconds": 15.0, "avg_pred_duration": 8.0, "highlight_count": 2},
        ]
        result = aggregate_by_config(rows)
        assert len(result) == 2
        baseline = [r for r in result if r["config_name"] == "baseline"][0]
        assert baseline["video_count"] == 2
        assert baseline["mean_precision_at_k"] == 0.9  # (0.8 + 1.0) / 2

    def test_aggregate_by_category(self):
        from run_highlight_eval_batch import aggregate_by_category
        rows = [
            {"config_name": "baseline", "category": "lecture", "precision_at_k": 0.8,
             "recall_at_k": 0.6, "mean_iou": 0.5, "avg_human_rating": 4.0,
             "duplicate_ratio": 0.1, "coverage_seconds": 20.0, "avg_pred_duration": 10.0,
             "highlight_count": 3},
            {"config_name": "baseline", "category": "sports", "precision_at_k": 1.0,
             "recall_at_k": 0.8, "mean_iou": 0.7, "avg_human_rating": 4.5,
             "duplicate_ratio": 0.0, "coverage_seconds": 30.0, "avg_pred_duration": 12.0,
             "highlight_count": 4},
        ]
        result = aggregate_by_category(rows)
        assert len(result) == 2
        lect = [r for r in result if r["category"] == "lecture"][0]
        assert lect["mean_precision_at_k"] == 0.8

    def test_aggregate_skips_errors(self):
        from run_highlight_eval_batch import aggregate_by_config
        rows = [
            {"config_name": "baseline", "precision_at_k": 1.0, "recall_at_k": 0.8,
             "mean_iou": 0.7, "avg_human_rating": 4.5, "duplicate_ratio": 0.0,
             "coverage_seconds": 30.0, "avg_pred_duration": 12.0, "highlight_count": 4,
             "error": ""},
            {"config_name": "baseline", "precision_at_k": 0.0, "recall_at_k": 0.0,
             "mean_iou": 0.0, "avg_human_rating": 0.0, "duplicate_ratio": 0.0,
             "coverage_seconds": 0.0, "avg_pred_duration": 0.0, "highlight_count": 0,
             "error": "something failed"},
        ]
        result = aggregate_by_config(rows)
        assert len(result) == 1
        assert result[0]["video_count"] == 1


# ── Batch run tests ──────────────────────────────────


class TestBatchRun:
    def test_batch_outputs_exist(self, batch_env):
        from run_highlight_eval_batch import run_batch_evaluation
        pv, agg, cat, errs = run_batch_evaluation(
            manifest_path=str(batch_env["manifest"]),
            config_files=batch_env["configs"],
            output_dir=str(batch_env["output"]),
            top_k=3, iou_threshold=0.3,
        )
        out = batch_env["output"]
        assert (out / "per_video_metrics.csv").exists()
        assert (out / "aggregate_metrics.csv").exists()
        assert (out / "aggregate_metrics.json").exists()
        assert (out / "category_metrics.csv").exists()
        assert (out / "experiment_summary.md").exists()
        assert (out / "run_config.json").exists()
        assert (out / "errors.json").exists()
        assert len(pv) == 2  # 2 videos * 1 config

    def test_batch_per_video_columns(self, batch_env):
        from run_highlight_eval_batch import run_batch_evaluation
        pv, _, _, _ = run_batch_evaluation(
            manifest_path=str(batch_env["manifest"]),
            config_files=batch_env["configs"],
            output_dir=str(batch_env["output"]),
            top_k=3, iou_threshold=0.3,
        )
        row = pv[0]
        assert "video_id" in row
        assert "category" in row
        assert "config_name" in row
        assert "precision_at_k" in row
        assert "recall_at_k" in row
        assert "iou" in row

    def test_batch_aggregate_json(self, batch_env):
        from run_highlight_eval_batch import run_batch_evaluation
        _, agg, _, _ = run_batch_evaluation(
            manifest_path=str(batch_env["manifest"]),
            config_files=batch_env["configs"],
            output_dir=str(batch_env["output"]),
            top_k=3, iou_threshold=0.3,
        )
        assert len(agg) > 0
        assert agg[0]["video_count"] == 2
        assert "mean_precision_at_k" in agg[0]

    def test_batch_category_aggregation(self, batch_env):
        from run_highlight_eval_batch import run_batch_evaluation
        _, _, cat, _ = run_batch_evaluation(
            manifest_path=str(batch_env["manifest"]),
            config_files=batch_env["configs"],
            output_dir=str(batch_env["output"]),
            top_k=3, iou_threshold=0.3,
        )
        assert len(cat) == 2  # 2 categories
        cats = {c["category"] for c in cat}
        assert "lecture" in cats
        assert "sports" in cats

    def test_batch_summary_markdown_contains_tables(self, batch_env):
        from run_highlight_eval_batch import run_batch_evaluation
        run_batch_evaluation(
            manifest_path=str(batch_env["manifest"]),
            config_files=batch_env["configs"],
            output_dir=str(batch_env["output"]),
            top_k=3, iou_threshold=0.3,
        )
        md = (batch_env["output"] / "experiment_summary.md").read_text(encoding="utf-8")
        assert "## Overall Metrics by Config" in md
        assert "baseline" in md

    def test_batch_no_nan_in_outputs(self, batch_env):
        import math
        from run_highlight_eval_batch import run_batch_evaluation
        run_batch_evaluation(
            manifest_path=str(batch_env["manifest"]),
            config_files=batch_env["configs"],
            output_dir=str(batch_env["output"]),
            top_k=3, iou_threshold=0.3,
        )
        text = (batch_env["output"] / "aggregate_metrics.json").read_text(encoding="utf-8")
        assert "NaN" not in text
        assert "Infinity" not in text

    def test_fail_fast_not_set_still_continues(self, batch_env):
        # Break one candidate file
        cans_dir = batch_env["tmp"] / "candidates"
        (cans_dir / "vid_a_candidates.json").write_text("not json", encoding="utf-8")
        from run_highlight_eval_batch import run_batch_evaluation
        pv, _, _, errs = run_batch_evaluation(
            manifest_path=str(batch_env["manifest"]),
            config_files=batch_env["configs"],
            output_dir=str(batch_env["output"]),
            top_k=3, iou_threshold=0.3, fail_fast=False,
        )
        assert len(errs) > 0  # vid_a failed
        # vid_b should still have results
        vid_b_rows = [r for r in pv if r["video_id"] == "vid_b" and not r["error"]]
        assert len(vid_b_rows) > 0

    def test_fail_fast_stops(self, batch_env):
        cans_dir = batch_env["tmp"] / "candidates"
        (cans_dir / "vid_a_candidates.json").write_text("not json", encoding="utf-8")
        from run_highlight_eval_batch import run_batch_evaluation
        with pytest.raises(Exception):
            run_batch_evaluation(
                manifest_path=str(batch_env["manifest"]),
                config_files=batch_env["configs"],
                output_dir=str(batch_env["output"]),
                top_k=3, iou_threshold=0.3, fail_fast=True,
            )

    def test_summary_md_errors_section(self, batch_env):
        cans_dir = batch_env["tmp"] / "candidates"
        (cans_dir / "vid_a_candidates.json").write_text("not json", encoding="utf-8")
        from run_highlight_eval_batch import run_batch_evaluation
        run_batch_evaluation(
            manifest_path=str(batch_env["manifest"]),
            config_files=batch_env["configs"],
            output_dir=str(batch_env["output"]),
            top_k=3, iou_threshold=0.3, fail_fast=False,
        )
        md = (batch_env["output"] / "experiment_summary.md").read_text(encoding="utf-8")
        assert "## Errors" in md

# ── Score Weights Tests ──────────────────────────────


class TestScoreWeights:
    """Validate score weights parsing, normalization, and best config selection."""

    def test_default_weights_valid(self):
        from run_highlight_eval_batch import DEFAULT_SCORE_WEIGHTS, validate_score_weights
        result = validate_score_weights(DEFAULT_SCORE_WEIGHTS.copy())
        assert abs(sum(result.values()) - 1.0) < 0.01

    def test_parse_cli_success(self):
        from run_highlight_eval_batch import parse_score_weights
        w = parse_score_weights("precision_at_k=0.5,recall_at_k=0.5")
        assert w["precision_at_k"] == 0.5
        assert w["recall_at_k"] == 0.5
        assert abs(sum(w.values()) - 1.0) < 0.01

    def test_parse_cli_error(self):
        from run_highlight_eval_batch import parse_score_weights
        import pytest
        with pytest.raises(ValueError, match="Invalid"):
            parse_score_weights("bad_format")
        with pytest.raises(ValueError, match="Unknown"):
            parse_score_weights("invalid_dim=1.0")
        with pytest.raises(ValueError, match="sum to"):
            parse_score_weights("precision_at_k=0.3")

    def test_norm_human_rating(self):
        from run_highlight_eval_batch import norm_human_rating
        assert norm_human_rating(1.0) == 0.0
        assert norm_human_rating(5.0) == 1.0
        assert norm_human_rating(3.0) == 0.5
        assert norm_human_rating(4.5) == 0.875

    def test_compute_weighted_score(self):
        from run_highlight_eval_batch import compute_weighted_score
        sw = {"precision_at_k": 0.5, "recall_at_k": 0.5}
        row = {"mean_precision_at_k": 0.8, "mean_recall_at_k": 0.6}
        score = compute_weighted_score(row, sw)
        assert score == 0.7

    def test_compute_weighted_score_with_human_rating(self):
        from run_highlight_eval_batch import compute_weighted_score
        sw = {"avg_human_rating": 1.0}
        row = {"mean_avg_human_rating": 4.0}
        assert compute_weighted_score(row, sw) == (4.0 - 1.0) / 4.0

    def test_compute_weighted_score_with_duplicate(self):
        from run_highlight_eval_batch import compute_weighted_score
        sw = {"precision_at_k": 0.8, "duplicate_ratio": 0.2}
        row = {"mean_precision_at_k": 0.9, "mean_duplicate_ratio": 0.25}
        assert compute_weighted_score(row, sw) == 0.9 * 0.8 - 0.25 * 0.2

    def test_best_config_selection(self):
        from run_highlight_eval_batch import select_best_config
        sw = {"precision_at_k": 1.0}
        aggs = [
            {"config_name": "cfg_a", "mean_precision_at_k": 0.8, "mean_recall_at_k": 0.7,
             "mean_iou": 0.6, "mean_avg_human_rating": 4.0, "mean_duplicate_ratio": 0.1},
            {"config_name": "cfg_b", "mean_precision_at_k": 0.9, "mean_recall_at_k": 0.8,
             "mean_iou": 0.7, "mean_avg_human_rating": 4.5, "mean_duplicate_ratio": 0.05},
        ]
        best = select_best_config(aggs, sw)
        assert best["config_name"] == "cfg_b"
        assert best["rank"] == 1
        assert best["is_best"] is True
        assert aggs[1]["rank"] == 1
        assert aggs[1]["is_best"] is True

    def test_tie_breaking(self):
        from run_highlight_eval_batch import select_best_config
        sw = {"precision_at_k": 1.0}
        aggs = [
            {"config_name": "cfg_b", "mean_precision_at_k": 0.8, "mean_recall_at_k": 0.7,
             "mean_iou": 0.7, "mean_avg_human_rating": 4.0, "mean_duplicate_ratio": 0.1},
            {"config_name": "cfg_a", "mean_precision_at_k": 0.8, "mean_recall_at_k": 0.7,
             "mean_iou": 0.6, "mean_avg_human_rating": 4.0, "mean_duplicate_ratio": 0.1},
        ]
        best = select_best_config(aggs, sw)
        assert best["config_name"] == "cfg_b"

    def test_empty_aggregate(self):
        from run_highlight_eval_batch import select_best_config
        sw = {"precision_at_k": 1.0}
        assert select_best_config([], sw) is None


# ── Paper Table Tests ────────────────────────────────


class TestPaperTables:
    def test_paper_table_overall_contains_columns(self, tmp_path):
        from run_highlight_eval_batch import write_paper_table_overall
        agg = [
            {"config_name": "baseline", "mean_precision_at_k": 0.8, "mean_recall_at_k": 0.7,
             "mean_iou": 0.6, "mean_avg_human_rating": 4.0, "mean_duplicate_ratio": 0.1,
             "rank": 1, "is_best": True},
        ]
        sw = {"precision_at_k": 1.0}
        write_paper_table_overall(agg, sw, tmp_path)
        md = (tmp_path / "paper_table_overall.md").read_text(encoding="utf-8")
        assert "baseline" in md

    def test_paper_table_by_category(self, tmp_path):
        from run_highlight_eval_batch import write_paper_table_by_category
        cat = [
            {"category": "lecture", "config_name": "baseline", "mean_precision_at_k": 0.8,
             "mean_recall_at_k": 0.7, "mean_iou": 0.6, "mean_avg_human_rating": 4.0,
             "mean_duplicate_ratio": 0.1},
        ]
        sw = {"precision_at_k": 1.0}
        write_paper_table_by_category(cat, sw, tmp_path)
        md = (tmp_path / "paper_table_by_category.md").read_text(encoding="utf-8")
        assert "lecture" in md

    def test_paper_table_per_video(self, tmp_path):
        from run_highlight_eval_batch import write_paper_table_per_video
        pv = [
            {"video_id": "vid_a", "category": "lecture", "config_name": "baseline",
             "precision_at_k": 0.8, "recall_at_k": 0.7, "iou": 0.6, "duplicate_ratio": 0.1,
             "coverage_seconds": 50.0, "avg_pred_duration": 12.5, "highlight_count": 4,
             "error": ""},
        ]
        sw = {}
        write_paper_table_per_video(pv, sw, tmp_path)
        md = (tmp_path / "paper_table_per_video.md").read_text(encoding="utf-8")
        assert "vid_a" in md

    def test_aggregate_contains_weighted_score(self, batch_env):
        from run_highlight_eval_batch import run_batch_evaluation
        _, agg, _, _ = run_batch_evaluation(
            manifest_path=str(batch_env["manifest"]),
            config_files=batch_env["configs"],
            output_dir=str(batch_env["output"]),
            top_k=3, iou_threshold=0.3,
        )
        assert "weighted_score" in agg[0]
        assert "rank" in agg[0]
        assert "is_best" in agg[0]

    def test_category_contains_weighted_score(self, batch_env):
        from run_highlight_eval_batch import run_batch_evaluation
        _, _, cat, _ = run_batch_evaluation(
            manifest_path=str(batch_env["manifest"]),
            config_files=batch_env["configs"],
            output_dir=str(batch_env["output"]),
            top_k=3, iou_threshold=0.3,
        )
        assert "weighted_score" in cat[0]

    def test_best_config_json_written(self, batch_env):
        from run_highlight_eval_batch import run_batch_evaluation
        run_batch_evaluation(
            manifest_path=str(batch_env["manifest"]),
            config_files=batch_env["configs"],
            output_dir=str(batch_env["output"]),
            top_k=3, iou_threshold=0.3,
        )
        bc = batch_env["output"] / "best_config.json"
        assert bc.exists()
        import json
        data = json.loads(bc.read_text(encoding="utf-8"))
        assert "config_name" in data
        assert "weighted_score" in data
        assert data["is_best"] is True

    def test_paper_table_files_written(self, batch_env):
        from run_highlight_eval_batch import run_batch_evaluation
        run_batch_evaluation(
            manifest_path=str(batch_env["manifest"]),
            config_files=batch_env["configs"],
            output_dir=str(batch_env["output"]),
            top_k=3, iou_threshold=0.3,
        )
        assert (batch_env["output"] / "paper_table_overall.md").exists()
        assert (batch_env["output"] / "paper_table_by_category.md").exists()
        assert (batch_env["output"] / "paper_table_per_video.md").exists()

    def test_summary_contains_best_config(self, batch_env):
        from run_highlight_eval_batch import run_batch_evaluation
        run_batch_evaluation(
            manifest_path=str(batch_env["manifest"]),
            config_files=batch_env["configs"],
            output_dir=str(batch_env["output"]),
            top_k=3, iou_threshold=0.3,
        )
        md = (batch_env["output"] / "experiment_summary.md").read_text(encoding="utf-8")
        assert "Best Config Selection" in md
        assert "Config Rankings" in md
        assert "Paper-Ready Tables" in md
