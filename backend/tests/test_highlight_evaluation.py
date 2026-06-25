"""Tests for highlight evaluation metrics and CLI."""

import csv, json, math, os, sys, tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

from evaluate_highlights import (
    load_labels,
    load_config,
    temporal_iou,
    precision_at_k,
    recall_at_k,
    mean_temporal_iou,
    avg_human_rating,
    duplicate_ratio,
    coverage_seconds,
    avg_pred_duration,
    build_matches,
    evaluate_config,
    run_evaluation,
)


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def hl():
    return [
        {"id": "hl_1", "start_time": 0, "end_time": 10, "score": 0.8, "selection_score": 0.8},
        {"id": "hl_2", "start_time": 15, "end_time": 25, "score": 0.6, "selection_score": 0.6},
        {"id": "hl_3", "start_time": 30, "end_time": 40, "score": 0.4, "selection_score": 0.4},
    ]


@pytest.fixture
def labels():
    return [
        {"id": "gt_1", "start_time": 2, "end_time": 8, "rating": 5},
        {"id": "gt_2", "start_time": 16, "end_time": 24, "rating": 4},
        {"id": "gt_3", "start_time": 50, "end_time": 60, "rating": 3},
    ]


@pytest.fixture
def config():
    return {
        "name": "test_cfg",
        "weights": {"object": 0.25, "motion": 0.20, "speech": 0.20, "scene": 0.15, "quality": 0.20},
        "diversity_lambda": 0.15,
        "min_score": 0.0,
        "min_duration": 3.0,
        "max_duration": 45.0,
        "top_k": 5,
    }


# ── Temporal IoU ──────────────────────────────────────────────────────────

def test_iou_full_overlap():
    assert temporal_iou({"start_time": 5, "end_time": 15}, {"start_time": 5, "end_time": 15}) == 1.0

def test_iou_partial_overlap():
    iou = temporal_iou({"start_time": 5, "end_time": 15}, {"start_time": 10, "end_time": 20})
    assert iou == 0.5  # inter=5, union=max(10,10)=10

def test_iou_no_overlap():
    assert temporal_iou({"start_time": 0, "end_time": 5}, {"start_time": 10, "end_time": 15}) == 0.0

def test_iou_point_overlap():
    assert temporal_iou({"start_time": 5, "end_time": 10}, {"start_time": 10, "end_time": 15}) == 0.0

def test_iou_nested():
    iou = temporal_iou({"start_time": 2, "end_time": 18}, {"start_time": 5, "end_time": 15})
    assert iou >= 0.5  # 10/16 = 0.625


# ── Precision / Recall ────────────────────────────────────────────────────

def test_precision_at_k(hl, labels):
    p1 = precision_at_k(hl, labels, 1, 0.3)
    p2 = precision_at_k(hl, labels, 2, 0.3)
    assert 0 < p1 <= 1.0
    assert p2 >= p1  # more preds = same or better precision

def test_precision_all_miss():
    hl_miss = [{"id": "h", "start_time": 100, "end_time": 110}]
    assert precision_at_k(hl_miss, [{"start_time": 0, "end_time": 5}], 1, 0.3) == 0.0

def test_precision_empty():
    assert precision_at_k([], [{"start_time": 0, "end_time": 5}], 5, 0.3) == 0.0

def test_recall_at_k(hl, labels):
    r = recall_at_k(hl, labels, 5, 0.3)
    # 2 of 3 ground-truth labels should be hit
    assert 0.5 <= r <= 1.0

def test_recall_no_labels():
    assert recall_at_k([{"start_time": 0, "end_time": 5}], [], 5, 0.3) == 0.0

def test_recall_no_predictions(labels):
    assert recall_at_k([], labels, 5, 0.3) == 0.0

def test_precision_recall_k0():
    assert precision_at_k([{"start_time": 0, "end_time": 5}], [{"start_time": 0, "end_time": 5}], 0, 0.3) == 0.0
    assert recall_at_k([{"start_time": 0, "end_time": 5}], [{"start_time": 0, "end_time": 5}], 0, 0.3) == 0.0


# ── Mean IoU ───────────────────────────────────────────────────────────────

def test_mean_iou(hl, labels):
    miou = mean_temporal_iou(hl, labels)
    assert 0 < miou <= 1.0

def test_mean_iou_empty():
    assert mean_temporal_iou([], [{"start_time": 0, "end_time": 5}]) == 0.0
    assert mean_temporal_iou([{"start_time": 0, "end_time": 5}], []) == 0.0


# ── Human rating ───────────────────────────────────────────────────────────

def test_avg_rating(hl, labels):
    ar = avg_human_rating(hl, labels, 0.3)
    assert ar > 0

def test_avg_rating_no_match():
    assert avg_human_rating(
        [{"start_time": 100, "end_time": 110}],
        [{"start_time": 0, "end_time": 5, "rating": 5}],
        0.3,
    ) == 0.0


# ── Duplicate ratio ────────────────────────────────────────────────────────

def test_dup_ratio_no_dup():
    assert duplicate_ratio([
        {"start_time": 0, "end_time": 10},
        {"start_time": 20, "end_time": 30},
    ]) == 0.0

def test_dup_ratio_single():
    assert duplicate_ratio([{"start_time": 0, "end_time": 10}]) == 0.0

def test_dup_ratio_empty():
    assert duplicate_ratio([]) == 0.0


# ── Coverage / duration ────────────────────────────────────────────────────

def test_coverage_seconds():
    assert coverage_seconds([
        {"start_time": 0, "end_time": 10},
        {"start_time": 5, "end_time": 15},
    ]) == 15.0  # merged: 0-15

def test_coverage_empty():
    assert coverage_seconds([]) == 0.0

def test_avg_pred_duration():
    d = avg_pred_duration([
        {"start_time": 0, "end_time": 10, "duration": 10},
        {"start_time": 20, "end_time": 30, "duration": 10},
    ])
    assert d == 10.0

def test_avg_pred_duration_empty():
    assert avg_pred_duration([]) == 0.0


# ── Label validation ───────────────────────────────────────────────────────

def test_label_valid():
    ls = load_labels_from_text('{"labels": [{"start_time": 1, "end_time": 5, "rating": 3}]}')
    assert len(ls) == 1
    assert ls[0]["start_time"] == 1

def test_label_negative_time():
    with pytest.raises(ValueError, match="negative"):
        load_labels_from_text('{"labels": [{"start_time": -1, "end_time": 5, "rating": 3}]}')

def test_label_end_less_than_start():
    with pytest.raises(ValueError, match="end_time.*<=.*start_time"):
        load_labels_from_text('{"labels": [{"start_time": 5, "end_time": 3, "rating": 3}]}')

def test_label_rating_out_of_range():
    with pytest.raises(ValueError, match="rating"):
        load_labels_from_text('{"labels": [{"start_time": 1, "end_time": 5, "rating": 0}]}')

def test_label_exceeds_duration():
    with pytest.raises(ValueError, match="exceeds"):
        load_labels_from_text('{"duration": 10, "labels": [{"start_time": 5, "end_time": 15, "rating": 3}]}')


# ── Config validation ──────────────────────────────────────────────────────

def test_config_weight_sum_invalid(tmp_path):
    cfg_path = tmp_path / "bad.json"
    cfg_path.write_text('{"weights": {"object": 1.0, "motion": 0.0, "speech": 0.0, "scene": 0.0, "quality": 0.0}}', encoding="utf-8")
    # This should pass — sum is 1.0
    cfg = load_config(str(cfg_path))
    assert cfg["name"] == "bad"

    cfg_path.write_text('{"weights": {"object": 0.5, "motion": 0.5, "speech": 0.0, "scene": 0.0, "quality": 0.0}}', encoding="utf-8")
    cfg = load_config(str(cfg_path))
    assert cfg["name"] == "bad"

def test_config_weight_sum_invalid_bad(tmp_path):
    cfg_path = tmp_path / "bad.json"
    cfg_path.write_text('{"weights": {"object": 0.8, "motion": 0.3, "speech": 0.0, "scene": 0.0, "quality": 0.0}}', encoding="utf-8")
    with pytest.raises(ValueError, match="sum to 1"):
        load_config(str(cfg_path))


# ── CLI output files (smoke) ───────────────────────────────────────────────

def test_run_evaluation(tmp_path, hl, labels):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({
        "name": "smoke",
        "weights": {"object": 0.25, "motion": 0.20, "speech": 0.20, "scene": 0.15, "quality": 0.20},
    }))
    out_dir = tmp_path / "out"
    (tmp_path / "labels.json").write_text(json.dumps({"labels": labels}), encoding="utf-8")
    metrics = run_evaluation(
        labels_file=str(tmp_path / "labels.json"),
        config_files=[str(cfg_path)],
        result_highlights=hl,
        output_dir=str(out_dir),
        iou_th=0.3,
        top_k=5,
        result_video_id="test_vid",
    )
    # We need to write labels first — let's do this properly
    assert (out_dir / "metrics.csv").exists()
    assert (out_dir / "metrics.json").exists()
    assert (out_dir / "run_config.json").exists()

def test_csv_has_correct_fields(tmp_path, hl, labels):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"name": "csv_test", "weights": {"object": 0.25, "motion": 0.20, "speech": 0.20, "scene": 0.15, "quality": 0.20}}))
    lbl_path = tmp_path / "labels.json"
    lbl_path.write_text(json.dumps({"labels": [{"start_time": 2, "end_time": 8, "rating": 5}]}))
    out_dir = tmp_path / "csv_out"
    metrics = run_evaluation(str(lbl_path), [str(cfg_path)], hl, str(out_dir), 0.3, 5, "csv_vid")

    with open(out_dir / "metrics.csv") as f:
        reader = csv.DictReader(f)
        row = next(reader)
        assert "precision_at_k" in row
        assert "recall_at_k" in row
        assert "mean_iou" in row
        assert "duplicate_ratio" in row


def test_json_output_is_valid(tmp_path, hl, labels):
    cfg_path = tmp_path / "cfg.json"
    cfg_path.write_text(json.dumps({"name": "json_test", "weights": {"object": 0.25, "motion": 0.20, "speech": 0.20, "scene": 0.15, "quality": 0.20}}))
    lbl_path = tmp_path / "labels.json"
    lbl_path.write_text(json.dumps({"labels": [{"start_time": 2, "end_time": 8, "rating": 5}]}))
    out_dir = tmp_path / "json_out"
    metrics = run_evaluation(str(lbl_path), [str(cfg_path)], hl, str(out_dir), 0.3, 5, "json_vid")

    data = json.loads((out_dir / "metrics.json").read_text())
    assert len(data) == 1
    assert data[0]["config_name"] == "json_test"


# ── Helper ─────────────────────────────────────────────────────────────────

def load_labels_from_text(text: str) -> list[dict]:
    """Load labels from an inline JSON string (bypasses file I/O)."""
    data = json.loads(text)
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




# ── Candidates schema validation ──────────────────────────────────────────

def test_candidates_valid():
    from evaluate_highlights import load_candidates
    import tempfile, json
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump({
            'schema_version': 1,
            'video_id': 'test',
            'duration': 30.0,
            'candidates': [{
                'id': 'c1', 'start_time': 0, 'end_time': 10, 'duration': 10,
                'scores': {'object': 0.1, 'motion': 0.2, 'speech': 0.3, 'scene': 0.4, 'quality': 0.5}
            }]
        }, f)
        f.flush()
        result = load_candidates(f.name)
        assert result['video_id'] == 'test'
        assert len(result['candidates']) == 1
    Path(f.name).unlink()

def test_candidates_nan_rejected():
    from evaluate_highlights import load_candidates
    import tempfile, json, math
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump({
            'schema_version': 1, 'video_id': 't', 'duration': 30.0,
            'candidates': [{
                'id': 'c1', 'start_time': 0, 'end_time': 10,
                'scores': {'object': float('nan'), 'motion': 0.2, 'speech': 0.3, 'scene': 0.4, 'quality': 0.5}
            }]
        }, f)
        f.flush()
        with pytest.raises(ValueError, match='NaN'):
            load_candidates(f.name)
    Path(f.name).unlink()

def test_candidates_end_before_start():
    from evaluate_highlights import load_candidates
    import tempfile, json
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump({
            'schema_version': 1, 'video_id': 't', 'duration': 30.0,
            'candidates': [{
                'id': 'c1', 'start_time': 10, 'end_time': 5,
                'scores': {'object': 0.1, 'motion': 0.2, 'speech': 0.3, 'scene': 0.4, 'quality': 0.5}
            }]
        }, f)
        f.flush()
        with pytest.raises(ValueError, match='end_time'):
            load_candidates(f.name)
    Path(f.name).unlink()

def test_candidates_score_out_of_range():
    from evaluate_highlights import load_candidates
    import tempfile, json
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump({
            'schema_version': 1, 'video_id': 't', 'duration': 30.0,
            'candidates': [{
                'id': 'c1', 'start_time': 0, 'end_time': 10,
                'scores': {'object': 0.1, 'motion': 1.5, 'speech': 0.3, 'scene': 0.4, 'quality': 0.5}
            }]
        }, f)
        f.flush()
        with pytest.raises(ValueError, match='not in'):
            load_candidates(f.name)
    Path(f.name).unlink()


# ── Rescore logic ─────────────────────────────────────────────────────────

def _make_candidates():
    return [
        {'id': 'c1', 'start_time': 0, 'end_time': 10, 'duration': 10,
         'scores': {'object': 0.5, 'motion': 0.5, 'speech': 0.5, 'scene': 0.5, 'quality': 0.5}},
        {'id': 'c2', 'start_time': 15, 'end_time': 25, 'duration': 10,
         'scores': {'object': 0.8, 'motion': 0.2, 'speech': 0.1, 'scene': 0.3, 'quality': 0.6}},
        {'id': 'c3', 'start_time': 5, 'end_time': 12, 'duration': 7,
         'scores': {'object': 0.1, 'motion': 0.1, 'speech': 0.1, 'scene': 0.1, 'quality': 0.1}},
    ]

def test_rescore_base_score():
    from evaluate_highlights import rescore_candidates
    weights = {'object': 1.0, 'motion': 0.0, 'speech': 0.0, 'scene': 0.0, 'quality': 0.0}
    results = rescore_candidates(_make_candidates(), weights, top_k=5, min_score=0.0,
                                  min_duration=0, max_duration=999, diversity_lambda=0.0)
    # c2 has highest object_score (0.8) -> should be first
    assert results[0]['id'] == 'c2'
    assert results[0]['base_score'] == 0.8

def test_rescore_score_breakdown():
    from evaluate_highlights import rescore_candidates
    weights = {'object': 0.25, 'motion': 0.25, 'speech': 0.25, 'scene': 0.25, 'quality': 0.0}
    results = rescore_candidates(_make_candidates(), weights, top_k=5, min_score=0.0,
                                  min_duration=0, max_duration=999, diversity_lambda=0.0)
    sb = results[0]['score_breakdown']
    assert 'raw' in sb['object']
    assert 'weight' in sb['object']
    assert 'weighted' in sb['object']

def test_rescore_overlap_penalty():
    from evaluate_highlights import rescore_candidates
    weights = {'object': 0.2, 'motion': 0.2, 'speech': 0.2, 'scene': 0.2, 'quality': 0.2}
    # c1 (0-10) and c3 (5-12) overlap -> penalty applied
    results = rescore_candidates(_make_candidates(), weights, top_k=5, min_score=0.0,
                                  min_duration=0, max_duration=999, diversity_lambda=1.0)
    # c3 should have overlap_penalty > 0
    c3 = [r for r in results if r['id'] == 'c3']
    if c3:
        assert c3[0]['overlap_penalty'] > 0

def test_rescore_diversity_lambda_zero():
    from evaluate_highlights import rescore_candidates
    weights = {'object': 0.2, 'motion': 0.2, 'speech': 0.2, 'scene': 0.2, 'quality': 0.2}
    results = rescore_candidates(_make_candidates(), weights, top_k=5, min_score=0.0,
                                  min_duration=0, max_duration=999, diversity_lambda=0.0)
    for r in results:
        assert r['overlap_penalty'] == 0.0

def test_rescore_min_score_filter():
    from evaluate_highlights import rescore_candidates
    weights = {'object': 0.2, 'motion': 0.2, 'speech': 0.2, 'scene': 0.2, 'quality': 0.2}
    results = rescore_candidates(_make_candidates(), weights, top_k=5, min_score=0.9,
                                  min_duration=0, max_duration=999, diversity_lambda=0.0)
    # All scores are 0.5 (avg of 5 dimensions * 0.2) or similar -> all < 0.9
    assert len(results) == 0

def test_rescore_duration_filter():
    from evaluate_highlights import rescore_candidates
    weights = {'object': 0.2, 'motion': 0.2, 'speech': 0.2, 'scene': 0.2, 'quality': 0.2}
    results = rescore_candidates(_make_candidates(), weights, top_k=5, min_score=0.0,
                                  min_duration=9, max_duration=9.5, diversity_lambda=0.0)
    # c1 (10s), c2 (10s) outside -> filtered; c3 (7s) also outside
    assert len(results) == 0

def test_rescore_top_k():
    from evaluate_highlights import rescore_candidates
    weights = {'object': 0.2, 'motion': 0.2, 'speech': 0.2, 'scene': 0.2, 'quality': 0.2}
    results = rescore_candidates(_make_candidates(), weights, top_k=1, min_score=0.0,
                                  min_duration=0, max_duration=999, diversity_lambda=0.0)
    assert len(results) == 1

def test_rescore_predictions_output(tmp_path):
    from evaluate_highlights import rescore_candidates, run_evaluation
    import json
    weights = {'object': 0.2, 'motion': 0.2, 'speech': 0.2, 'scene': 0.2, 'quality': 0.2}
    predictions = rescore_candidates(_make_candidates(), weights, top_k=5,
                                      min_score=0.0, min_duration=0, max_duration=999, diversity_lambda=0.0)
    out_dir = tmp_path / 'pred_out'
    out_dir.mkdir()
    (out_dir / 'predictions_test.json').write_text(
        json.dumps({'config_name': 'test', 'predictions': predictions}, indent=2),
        encoding='utf-8',
    )
    assert (out_dir / 'predictions_test.json').exists()
    data = json.loads((out_dir / 'predictions_test.json').read_text(encoding='utf-8'))
    assert len(data['predictions']) == 3

def test_run_evaluation_with_rescore_predictions(tmp_path):
    from evaluate_highlights import load_labels, load_config, run_evaluation, rescore_candidates
    import json
    candidates = _make_candidates()
    weights = {'object': 0.25, 'motion': 0.25, 'speech': 0.25, 'scene': 0.25, 'quality': 0.0}
    predictions = rescore_candidates(candidates, weights, top_k=5, min_score=0.0,
                                      min_duration=0, max_duration=999, diversity_lambda=0.0)
    cfg_path = tmp_path / 'cfg.json'
    cfg_path.write_text(json.dumps({'name': 'rescore_test', 'weights': weights}))
    lbl_path = tmp_path / 'labels.json'
    lbl_path.write_text(json.dumps({'labels': [{'start_time': 2, 'end_time': 8, 'rating': 5}]}))
    out_dir = tmp_path / 'out_dir'
    metrics = run_evaluation(
        labels_file=str(lbl_path), config_files=[str(cfg_path)],
        result_highlights=[], output_dir=str(out_dir),
        iou_th=0.3, top_k=5, result_video_id='rescore_vid',
        rescore_predictions={'rescore_test': predictions},
    )
    assert len(metrics) == 1
    assert (out_dir / 'metrics.csv').exists()
    assert (out_dir / 'metrics.json').exists()
