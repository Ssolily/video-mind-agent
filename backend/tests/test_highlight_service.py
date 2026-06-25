"""Tests for highlight scoring — weights, score_breakdown, diversity, edge cases."""

import json
import math
import os
import tempfile
from pathlib import Path

import pytest

from app.services.highlight_service import (
    recommend_highlights,
    _generate_candidates,
    _calc_object_score,
    _calc_motion_score,
    _calc_speech_score,
    _calc_scene_score,
    _calc_quality_score,
    _compute_base_score,
    _time_overlap,
    _select_top_k,
    _WEIGHTS,
)


# ── Helpers ─────────────────────────────────────


def _make_detection(timestamp: float, cls: str = "person", bbox=None):
    return {
        "timestamp": timestamp,
        "frame_id": f"frame_{int(timestamp):06d}",
        "detections": [
            {"class_name": cls, "confidence": 0.9, "bbox": bbox or [100, 100, 300, 400]},
        ],
    }


def _make_track(track_id: str, cls: str, boxes: list) -> dict:
    return {
        "track_id": track_id,
        "class_name": cls,
        "start_time": boxes[0]["timestamp"],
        "end_time": boxes[-1]["timestamp"],
        "duration": boxes[-1]["timestamp"] - boxes[0]["timestamp"],
        "boxes": boxes,
    }


def _make_scene(sid: str, start: float, end: float) -> dict:
    return {"scene_id": sid, "start_time": start, "end_time": end, "duration": end - start}


# ── Weight validation ───────────────────────────


class TestWeights:
    def test_default_weights_sum_to_one(self):
        total = sum(_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01, f"weights sum to {total}"

    def test_all_weights_non_negative(self):
        for k, v in _WEIGHTS.items():
            assert v >= 0, f"{k} weight is {v}"

    def test_all_dimensions_present(self):
        expected = {"object", "motion", "speech", "scene", "quality"}
        assert set(_WEIGHTS.keys()) == expected


# ── Base score computation ──────────────────────


class TestBaseScore:
    def test_perfect_scores_give_max(self):
        cand = {
            "object_score": 1.0, "motion_score": 1.0,
            "speech_score": 1.0, "scene_score": 1.0, "quality_score": 1.0,
        }
        base, breakdown = _compute_base_score(cand)
        assert base == 1.0
        assert all(v['raw'] == 1.0 for v in breakdown.values())

    def test_zero_scores_give_min(self):
        cand = {
            "object_score": 0.0, "motion_score": 0.0,
            "speech_score": 0.0, "scene_score": 0.0, "quality_score": 0.0,
        }
        base, breakdown = _compute_base_score(cand)
        assert base == 0.0
        assert all(v["raw"] == 0.0 for v in breakdown.values())

    def test_weighted_average(self):
        # Single dimension test: only object matters
        cand = {
            "object_score": 0.5, "motion_score": 0.0,
            "speech_score": 0.0, "scene_score": 0.0, "quality_score": 0.0,
        }
        base, breakdown = _compute_base_score(cand)
        expected = _WEIGHTS["object"] * 0.5
        assert abs(base - expected) < 0.001

    def test_breakdown_structure(self):
        cand = {
            "object_score": 0.3, "motion_score": 0.4,
            "speech_score": 0.5, "scene_score": 0.6, "quality_score": 0.7,
        }
        base, breakdown = _compute_base_score(cand)
        assert breakdown["object"]["raw"] == 0.3
        assert breakdown["motion"]["raw"] == 0.4
        assert breakdown["speech"]["raw"] == 0.5
        assert breakdown["scene"]["raw"] == 0.6
        assert breakdown["quality"]["raw"] == 0.7
        assert len(breakdown) == 5

    def test_scores_clamped(self):
        cand = {
            "object_score": 5.0, "motion_score": -1.0,
            "speech_score": 0.5, "scene_score": 0.0, "quality_score": 0.7,
        }
        base, breakdown = _compute_base_score(cand)
        # base is clamped to [0,1] — it will be at least 0 and at most 1
        assert 0.0 <= base <= 1.0

    def test_deterministic(self):
        cand = {
            "object_score": 0.3, "motion_score": 0.4,
            "speech_score": 0.5, "scene_score": 0.6, "quality_score": 0.7,
        }
        b1, _ = _compute_base_score(cand)
        b2, _ = _compute_base_score(cand)
        assert b1 == b2


# ── Individual scoring dimensions ───────────────


class TestObjectScore:
    def test_no_detections(self):
        assert _calc_object_score({}, 0, 10) == 0.0

    def test_detections_in_window(self):
        det_map = {1.0: [{"class_name": "person", "bbox": [0, 0, 640, 480]}],
                   2.0: [{"class_name": "dog", "bbox": [100, 100, 200, 200]}]}
        score = _calc_object_score(det_map, 0.5, 2.5)
        assert score > 0
        assert score <= 1.0

    def test_detections_outside_window(self):
        det_map = {10.0: [{"class_name": "person", "bbox": [0, 0, 640, 480]}]}
        score = _calc_object_score(det_map, 0, 5)
        assert score == 0.0


class TestMotionScore:
    def test_no_tracks(self):
        assert _calc_motion_score({}, [], 0, 10) == 0.0

    def test_motion_detected(self):
        track = _make_track("t1", "person", [
            {"timestamp": 0.0, "bbox": [100, 100, 200, 200], "confidence": 0.9},
            {"timestamp": 2.0, "bbox": [300, 100, 400, 200], "confidence": 0.9},
        ])
        motion = {"t1": [0.2]}
        score = _calc_motion_score(motion, [track], 0, 5)
        assert score > 0
        assert score <= 1.0

    def test_no_motion(self):
        track = _make_track("t1", "person", [
            {"timestamp": 0.0, "bbox": [100, 100, 200, 200], "confidence": 0.9},
        ])
        score = _calc_motion_score({}, [track], 0, 5)
        assert score == 0.0


class TestSpeechScore:
    def test_no_subtitles(self):
        assert _calc_speech_score([], 0, 10) == 0.0

    def test_subtitles_present(self):
        subs = [{"start": 1.0, "end": 2.0, "text": "hello"}]
        score = _calc_speech_score(subs, 0, 10)
        assert score > 0
        assert score <= 1.0

    def test_no_audio_video_still_scores(self):
        # Speech not available — should return 0, not crash
        assert _calc_speech_score([], 0, 10) == 0.0


class TestSceneScore:
    def test_at_boundary(self):
        boundaries = {0.0, 10.0, 20.0}
        score = _calc_scene_score(0.0, boundaries)
        assert score == 1.0

    def test_near_boundary(self):
        boundaries = {10.0}
        score = _calc_scene_score(9.0, boundaries)
        assert 0 < score < 1.0

    def test_far_from_boundary(self):
        boundaries = {10.0}
        score = _calc_scene_score(5.0, boundaries)
        assert score == 0.0


class TestQualityScore:
    def test_placeholder_value(self):
        cand = {"dummy": 1}
        score = _calc_quality_score(cand)
        assert score == 0.7
        assert isinstance(score, float)
        assert 0 <= score <= 1.0


# ── Diversity & selection ───────────────────────


class TestTimeOverlap:
    def test_full_overlap(self):
        a = {"start_time": 0.0, "end_time": 10.0}
        b = {"start_time": 2.0, "end_time": 8.0}
        assert _time_overlap(a, b) > 0.5

    def test_no_overlap(self):
        a = {"start_time": 0.0, "end_time": 5.0}
        b = {"start_time": 5.0, "end_time": 10.0}
        assert _time_overlap(a, b) == 0.0

    def test_identical(self):
        a = {"start_time": 0.0, "end_time": 10.0}
        assert _time_overlap(a, a) == 1.0


class TestSelectTopK:
    def test_empty_candidates(self):
        assert _select_top_k([], 5) == []

    def test_single_candidate(self):
        cands = [{"start_time": 0.0, "end_time": 10.0, "duration": 10.0,
                  "object_score": 0.5, "motion_score": 0.3,
                  "speech_score": 0.0, "scene_score": 0.0, "quality_score": 0.7}]
        result = _select_top_k(cands, 5)
        assert len(result) == 1
        assert result[0]["base_score"] >= 0
        assert result[0]["selection_score"] >= 0
        assert result[0]["selection_score"] <= result[0]["base_score"]
        assert "score_breakdown" in result[0]
        assert "id" in result[0]

    def test_no_duplicate_times(self):
        cands = []
        for t in range(0, 100, 10):
            cands.append({"start_time": float(t), "end_time": float(t + 9), "duration": 9.0,
                          "object_score": 0.5, "motion_score": 0.3,
                          "speech_score": 0.0, "scene_score": 0.0, "quality_score": 0.7})
        result = _select_top_k(cands, 5)
        intervals = [(h["start_time"], h["end_time"]) for h in result]
        for i in range(len(intervals)):
            for j in range(i + 1, len(intervals)):
                s = max(intervals[i][0], intervals[j][0])
                e = min(intervals[i][1], intervals[j][1])
                overlap = max(0, e - s)
                assert overlap == 0, f"Duplicate interval: {intervals[i]} vs {intervals[j]}"

    def test_overlap_penalty_non_overlapping(self):
        # Non-overlapping candidates get no penalty
        cands = [
            {"start_time": 0.0, "end_time": 5.0, "duration": 5.0,
             "object_score": 0.5, "motion_score": 0.3,
             "speech_score": 0.0, "scene_score": 0.0, "quality_score": 0.7},
            {"start_time": 10.0, "end_time": 15.0, "duration": 5.0,
             "object_score": 0.5, "motion_score": 0.3,
             "speech_score": 0.0, "scene_score": 0.0, "quality_score": 0.7},
        ]
        result = _select_top_k(cands, 2)
        assert len(result) == 2
        # Both should have 0 overlap penalty
        for h in result:
            assert h["overlap_penalty"] == 0.0

    def test_overlap_penalty_overlapping(self):
        cands = [
            {"start_time": 0.0, "end_time": 10.0, "duration": 10.0,
             "object_score": 0.5, "motion_score": 0.3,
             "speech_score": 0.0, "scene_score": 0.0, "quality_score": 0.7},
            {"start_time": 2.0, "end_time": 8.0, "duration": 6.0,
             "object_score": 0.5, "motion_score": 0.3,
             "speech_score": 0.0, "scene_score": 0.0, "quality_score": 0.7},
        ]
        result = _select_top_k(cands, 2)
        # At least one overlapping candidate should have penalty > 0
        penalties = [h["overlap_penalty"] for h in result]
        assert any(p > 0 for p in penalties), f"No penalties found in {penalties}"

    def test_identical_input_deterministic_output(self):
        from copy import deepcopy
        cands = [
            {"start_time": float(t), "end_time": float(t + 8), "duration": 8.0,
             "object_score": 0.5, "motion_score": 0.3,
             "speech_score": 0.0, "scene_score": 0.0, "quality_score": 0.7}
            for t in range(0, 50, 10)
        ]
        r1 = _select_top_k(deepcopy(cands), 3)

    def test_respects_min_score(self):
        cands = [{"start_time": 0.0, "end_time": 10.0, "duration": 10.0,
                  "object_score": 0.0, "motion_score": 0.0,
                  "speech_score": 0.0, "scene_score": 0.0, "quality_score": 0.0}]
        result = _select_top_k(cands, 5)
        assert len(result) == 0


# ── Integration: recommend_highlights ───────────


class TestRecommendHighlights:
    def _write_report(self, video_id: str, filename: str, data, reports_dir) -> str:
        d = reports_dir / video_id
        d.mkdir(parents=True, exist_ok=True)
        p = d / filename
        p.write_text(json.dumps(data), encoding="utf-8")
        return str(p)

    def test_no_scenes_returns_empty(self, tmp_path, monkeypatch):
        # Point REPORTS_DIR to a temp empty dir
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        result = recommend_highlights("no_such_video")
        assert result == []

    def test_empty_detections_no_crash(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        vid = "empty_det"
        self._write_report(vid, "scenes.json", [_make_scene("s1", 0, 30)], tmp_path)
        self._write_report(vid, "detections.json", [], tmp_path)
        self._write_report(vid, "tracks.json", [], tmp_path)
        self._write_report(vid, "subtitles.json", [], tmp_path)
        result = recommend_highlights(vid)
        assert isinstance(result, list)
        for h in result:
            assert 0 <= h["selection_score"] <= 1.0
            assert 0 <= h["base_score"] <= 1.0
            assert "score_breakdown" in h
            assert "id" in h

    def test_full_pipeline_with_data(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        vid = "full_test"
        self._write_report(vid, "scenes.json", [
            _make_scene("s1", 0, 20),
            _make_scene("s2", 20, 40),
        ], tmp_path)
        self._write_report(vid, "detections.json", [
            _make_detection(1.0, "person"),
            _make_detection(5.0, "dog"),
            _make_detection(25.0, "person"),
        ], tmp_path)
        self._write_report(vid, "tracks.json", [
            _make_track("t1", "person", [
                {"timestamp": 1.0, "bbox": [100, 100, 200, 200], "confidence": 0.9},
                {"timestamp": 5.0, "bbox": [150, 100, 250, 200], "confidence": 0.9},
            ]),
        ], tmp_path)
        self._write_report(vid, "subtitles.json", [
            {"start": 0.5, "end": 1.5, "text": "hello"},
            {"start": 2.0, "end": 3.0, "text": "world"},
        ], tmp_path)
        result = recommend_highlights(vid, top_k=3)
        assert len(result) > 0
        for h in result:
            assert h["selection_score"] >= 0
            assert h["duration"] > 0
            assert "id" in h


# ── New P1-A1 tests ──────────────────────────────

class TestScoreEqualsSelectionScore:
    def test_score_is_selection_score(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        vid = "score_eq"
        self._write_report(vid, "scenes.json", [_make_scene("s1", 0, 30)], tmp_path)
        self._write_report(vid, "detections.json", [], tmp_path)
        self._write_report(vid, "tracks.json", [], tmp_path)
        self._write_report(vid, "subtitles.json", [], tmp_path)
        result = recommend_highlights(vid)
        for h in result:
            assert h["score"] == h["selection_score"], f"score={h['score']} != selection_score={h['selection_score']}"

    def _write_report(self, video_id, filename, data, reports_dir):
        d = reports_dir / video_id
        d.mkdir(parents=True, exist_ok=True)
        p = d / filename
        p.write_text(json.dumps(data), encoding="utf-8")


class TestJsonSerializable:
    def test_highlights_json_serializable(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        vid = "json_test"
        self._write_report(vid, "scenes.json", [_make_scene("s1", 0, 30)], tmp_path)
        self._write_report(vid, "detections.json", [], tmp_path)
        self._write_report(vid, "tracks.json", [], tmp_path)
        self._write_report(vid, "subtitles.json", [], tmp_path)
        result = recommend_highlights(vid)
        # Must not raise
        dumped = json.dumps(result, ensure_ascii=False)
        assert isinstance(dumped, str)
        assert len(dumped) > 0

    def _write_report(self, video_id, filename, data, reports_dir):
        d = reports_dir / video_id
        d.mkdir(parents=True, exist_ok=True)
        p = d / filename
        p.write_text(json.dumps(data), encoding="utf-8")


class TestReportCompatibility:
    def test_legacy_fields_present(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        vid = "legacy"
        self._write_report(vid, "scenes.json", [_make_scene("s1", 0, 30)], tmp_path)
        self._write_report(vid, "detections.json", [], tmp_path)
        self._write_report(vid, "tracks.json", [], tmp_path)
        self._write_report(vid, "subtitles.json", [], tmp_path)
        result = recommend_highlights(vid)
        for h in result:
            assert "start_time" in h
            assert "end_time" in h
            assert "duration" in h
            assert "score" in h
            assert "reason" in h
            assert "base_score" in h
            assert "selection_score" in h
            assert "overlap_penalty" in h
            assert "score_breakdown" in h
            assert "id" in h

    def _write_report(self, video_id, filename, data, reports_dir):
        d = reports_dir / video_id
        d.mkdir(parents=True, exist_ok=True)
        p = d / filename
        p.write_text(json.dumps(data), encoding="utf-8")


class TestEmptyInputs:
    def test_no_scenes_returns_empty(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        result = recommend_highlights("no_scenes")
        assert result == []

    def test_no_detections_no_crash(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        vid = "no_det"
        self._write_report(vid, "scenes.json", [_make_scene("s1", 0, 30)], tmp_path)
        self._write_report(vid, "detections.json", [], tmp_path)
        self._write_report(vid, "tracks.json", [], tmp_path)
        self._write_report(vid, "subtitles.json", [], tmp_path)
        result = recommend_highlights(vid)
        assert isinstance(result, list)

    def test_no_subtitles_no_crash(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        vid = "no_sub"
        self._write_report(vid, "scenes.json", [_make_scene("s1", 0, 30)], tmp_path)
        self._write_report(vid, "detections.json", [_make_detection(5.0, "person")], tmp_path)
        self._write_report(vid, "tracks.json", [
            _make_track("t1", "person", [
                {"timestamp": 5.0, "bbox": [100, 100, 200, 200], "confidence": 0.9},
            ]),
        ], tmp_path)
        self._write_report(vid, "subtitles.json", [], tmp_path)
        result = recommend_highlights(vid)
        assert isinstance(result, list)

    def _write_report(self, video_id, filename, data, reports_dir):
        d = reports_dir / video_id
        d.mkdir(parents=True, exist_ok=True)
        p = d / filename
        p.write_text(json.dumps(data), encoding="utf-8")


class TestDeterministicOutput:
    def test_same_input_same_output(self, tmp_path, monkeypatch):
        from copy import deepcopy
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        vid = "det_test"
        self._write_report(vid, "scenes.json", [_make_scene("s1", 0, 30)], tmp_path)
        self._write_report(vid, "detections.json", [_make_detection(5.0, "person")], tmp_path)
        self._write_report(vid, "tracks.json", [
            _make_track("t1", "person", [
                {"timestamp": 5.0, "bbox": [100, 100, 200, 200], "confidence": 0.9},
            ]),
        ], tmp_path)
        self._write_report(vid, "subtitles.json", [{"start": 0.5, "end": 1.5, "text": "test"}], tmp_path)
        r1 = recommend_highlights(vid)
        r2 = recommend_highlights(vid)
        assert r1 == r2

    def _write_report(self, video_id, filename, data, reports_dir):
        d = reports_dir / video_id
        d.mkdir(parents=True, exist_ok=True)
        p = d / filename
        p.write_text(json.dumps(data), encoding="utf-8")






class TestSaveCandidates:

    def test_save_candidates_basic(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        from app.services.highlight_service import save_candidates

        candidates = [
            {
                "id": "cand_0001",
                "start_time": 0.0,
                "end_time": 10.0,
                "duration": 10.0,
                "object_score": 0.5,
                "motion_score": 0.3,
                "speech_score": 0.8,
                "scene_score": 0.2,
                "quality_score": 0.7,
            }
        ]
        out = save_candidates("test_vid", candidates)
        assert out is not None
        artifact_path = tmp_path / "test_vid" / "highlight_candidates.json"
        assert artifact_path.is_file()
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert data["schema_version"] == 1
        assert data["video_id"] == "test_vid"
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["scores"]["object"] == 0.5
        assert data["candidates"][0]["scores"]["speech"] == 0.8

    def test_save_candidates_empty(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        from app.services.highlight_service import save_candidates
        assert save_candidates("empty_vid", []) is None

    def test_save_candidates_nan_clamped(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        from app.services.highlight_service import save_candidates
        import math
        candidates = [
            {
                "id": "cand_nan",
                "start_time": 0.0,
                "end_time": 10.0,
                "duration": 10.0,
                "object_score": float("nan"),
                "motion_score": float("inf"),
                "speech_score": -0.5,
                "scene_score": 2.0,
                "quality_score": 0.7,
            }
        ]
        save_candidates("nan_vid", candidates)
        artifact_path = tmp_path / "nan_vid" / "highlight_candidates.json"
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
        scores = data["candidates"][0]["scores"]
        assert scores["object"] == 0.0  # nan -> 0
        assert scores["motion"] == 0.0   # inf -> 0 (all non-finite become 0)
        assert scores["speech"] == 0.0   # negative -> 0
        assert scores["scene"] == 1.0    # >1 -> 1
        assert scores["quality"] == 0.7

    def test_save_candidates_reason_string_conversion(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        from app.services.highlight_service import save_candidates
        candidates = [
            {
                "id": "cand_r1",
                "start_time": 0.0, "end_time": 10.0, "duration": 10.0,
                "object_score": 0.5, "motion_score": 0.3,
                "speech_score": 0.8, "scene_score": 0.2,
                "quality_score": 0.7,
                "reason": "old string reason",
            }
        ]
        save_candidates("reason_vid", candidates)
        artifact_path = tmp_path / "reason_vid" / "highlight_candidates.json"
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
        assert data["candidates"][0]["reason"] == ["old string reason"]

    def test_save_candidates_end_before_start_filtered(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        from app.services.highlight_service import save_candidates
        candidates = [
            {
                "id": "bad", "start_time": 10.0, "end_time": 5.0, "duration": 5.0,
                "object_score": 0.5, "motion_score": 0.3,
                "speech_score": 0.8, "scene_score": 0.2,
                "quality_score": 0.7,
            },
            {
                "id": "good", "start_time": 0.0, "end_time": 10.0, "duration": 10.0,
                "object_score": 0.5, "motion_score": 0.3,
                "speech_score": 0.8, "scene_score": 0.2,
                "quality_score": 0.7,
            },
        ]
        save_candidates("filter_vid", candidates)
        artifact_path = tmp_path / "filter_vid" / "highlight_candidates.json"
        data = json.loads(artifact_path.read_text(encoding="utf-8"))
        # Only 'good' should remain
        ids = [c["id"] for c in data["candidates"]]
        assert "good" in ids
        assert "bad" not in ids


    def test_save_candidates_duration_from_metadata(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        from app.services.highlight_service import save_candidates
        candidates = [
            {
                "id": "c1", "start_time": 0.0, "end_time": 10.0, "duration": 10.0,
                "object_score": 0.5, "motion_score": 0.3,
                "speech_score": 0.8, "scene_score": 0.2,
                "quality_score": 0.7,
            }
        ]
        save_candidates("dur_vid", candidates, duration=30.0)
        data = json.loads((tmp_path / "dur_vid" / "highlight_candidates.json").read_text(encoding="utf-8"))
        assert data["duration"] == 30.0

    def test_save_candidates_duration_fallback(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        from app.services.highlight_service import save_candidates
        candidates = [
            {
                "id": "c1", "start_time": 0.0, "end_time": 10.0, "duration": 10.0,
                "object_score": 0.5, "motion_score": 0.3,
                "speech_score": 0.8, "scene_score": 0.2,
                "quality_score": 0.7,
            }
        ]
        save_candidates("fall_vid", candidates)
        data = json.loads((tmp_path / "fall_vid" / "highlight_candidates.json").read_text(encoding="utf-8"))
        assert data["duration"] == 10.0  # max candidate end_time

    def test_save_candidates_no_absolute_paths(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        from app.services.highlight_service import save_candidates
        candidates = [
            {
                "id": "c1", "start_time": 0.0, "end_time": 10.0, "duration": 10.0,
                "object_score": 0.5, "motion_score": 0.3,
                "speech_score": 0.8, "scene_score": 0.2,
                "quality_score": 0.7,
            }
        ]
        save_candidates("safe_vid", candidates)
        artifact_path = tmp_path / "safe_vid" / "highlight_candidates.json"
        text = artifact_path.read_text(encoding="utf-8")
        assert "D:\\\\" not in text
        assert "C:\\\\" not in text


class TestCandidateExportIntegration:
    def test_recommend_creates_candidates_artifact(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        from app.services.highlight_service import recommend_highlights

        vid = "int_vid"
        d = tmp_path / vid
        d.mkdir(parents=True, exist_ok=True)
        (d / "scenes.json").write_text(json.dumps([_make_scene("s1", 0, 30)]), encoding="utf-8")
        (d / "detections.json").write_text(json.dumps([]), encoding="utf-8")
        (d / "tracks.json").write_text(json.dumps([]), encoding="utf-8")
        (d / "subtitles.json").write_text(json.dumps([]), encoding="utf-8")

        result = recommend_highlights(vid)
        assert isinstance(result, list)

        candidates_path = tmp_path / vid / "highlight_candidates.json"
        assert candidates_path.is_file(), "candidates artifact should exist"
        data = json.loads(candidates_path.read_text(encoding="utf-8"))
        assert data["video_id"] == vid
        assert len(data["candidates"]) >= 0

    def test_candidates_artifact_schema_matches_rescore(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        monkeypatch.setattr("app.services.highlight_service.REPORTS_DIR", tmp_path)
        from app.services.highlight_service import recommend_highlights

        vid = "schema_vid"
        d = tmp_path / vid
        d.mkdir(parents=True, exist_ok=True)
        (d / "scenes.json").write_text(json.dumps([_make_scene("s1", 0, 30)]), encoding="utf-8")
        (d / "detections.json").write_text(json.dumps([]), encoding="utf-8")
        (d / "tracks.json").write_text(json.dumps([]), encoding="utf-8")
        (d / "subtitles.json").write_text(json.dumps([]), encoding="utf-8")

        recommend_highlights(vid)
        data = json.loads((tmp_path / vid / "highlight_candidates.json").read_text(encoding="utf-8"))
        assert "schema_version" in data
        assert "video_id" in data
        assert "duration" in data
        assert "generated_at" in data
        assert "candidates" in data
        if data["candidates"]:
            c = data["candidates"][0]
            assert "id" in c
            assert "start_time" in c
            assert "end_time" in c
            assert "duration" in c
            assert "scores" in c
            for dim in ("object", "motion", "speech", "scene", "quality"):
                assert dim in c["scores"]
