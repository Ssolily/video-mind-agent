"""Highlight recommendation engine.

Scoring formula (configurable via env vars):

  base_score = w_object * object_score
             + w_motion * motion_score
             + w_speech * speech_score
             + w_scene  * scene_score
             + w_quality * quality_score

  selection_score = base_score - diversity_lambda * overlap_penalty

All scores are clamped to [0, 1].
Five content weights must sum to 1.0 (validated at config import).
"""

import json
import math
from pathlib import Path

from app.config import (
    REPORTS_DIR,
    HIGHLIGHT_W_OBJECT,
    HIGHLIGHT_W_MOTION,
    HIGHLIGHT_W_SPEECH,
    HIGHLIGHT_W_SCENE,
    HIGHLIGHT_W_QUALITY,
    HIGHLIGHT_DIVERSITY_LAMBDA,
    HIGHLIGHT_MIN_SCORE,
    HIGHLIGHT_MIN_DURATION,
    HIGHLIGHT_MAX_DURATION,
)


# ── Content weights (from config) ──────────────────

_WEIGHTS = {
    "object": HIGHLIGHT_W_OBJECT,
    "motion": HIGHLIGHT_W_MOTION,
    "speech": HIGHLIGHT_W_SPEECH,
    "scene": HIGHLIGHT_W_SCENE,
    "quality": HIGHLIGHT_W_QUALITY,
}

SPLIT_MIN_DURATION = 10.0
SPLIT_MAX_DURATION = HIGHLIGHT_MAX_DURATION
SPLIT_STRIDE = 10.0
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720


# ── Public entry ───────────────────────────────────


def recommend_highlights(
    video_id: str,
    top_k: int = 5,
) -> list[dict]:
    """Load reports, generate candidates, score and rank them.

    Returns a list of dicts. Each dict has both the new structured fields
    (``base_score``, ``selection_score``, ``score_breakdown``, etc.) **and**
    the legacy ``score`` / ``reason`` fields for backward compatibility.
    """
    scenes = _load_json(video_id, "scenes.json")
    detections = _load_json(video_id, "detections.json")
    tracks = _load_json(video_id, "tracks.json")
    subtitles = _load_json(video_id, "subtitles.json")

    if not scenes:
        return []

    candidates = _generate_candidates(scenes)
    track_motion = _compute_track_motion(tracks)
    det_map = _build_detection_map(detections)
    sub_map = _build_subtitle_map(subtitles)
    scene_boundaries = {s["start_time"] for s in scenes}

    # Score each candidate
    for cand in candidates:
        cs, ce = cand["start_time"], cand["end_time"]
        cand["object_score"] = _calc_object_score(det_map, cs, ce)
        cand["motion_score"] = _calc_motion_score(track_motion, tracks, cs, ce)
        cand["speech_score"] = _calc_speech_score(sub_map, cs, ce)
        cand["scene_score"] = _calc_scene_score(cs, scene_boundaries)
        cand["quality_score"] = _calc_quality_score(cand)

    # Export raw candidates as JSON artifact for rescore evaluation
    meta = _load_json(video_id, "metadata.json") or {}
    meta_dur = None
    if isinstance(meta, dict):
        meta_dur = meta.get("duration") or meta.get("Duration") or None
    save_candidates(video_id, candidates, duration=meta_dur)

    highlights = _select_top_k(candidates, top_k)
    return highlights


# ── Load helpers ────────────────────────────────────


def _load_json(video_id: str, filename: str) -> list:
    p = REPORTS_DIR / video_id / filename
    if not p.is_file():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


# ── Candidate generation ────────────────────────────


_CAND_ID = [0]


def _next_cand_id() -> str:
    _CAND_ID[0] += 1
    return f"cand_{_CAND_ID[0]:04d}"


def _generate_candidates(scenes: list[dict]) -> list[dict]:
    """Split scenes into candidate segments."""
    candidates: list[dict] = []
    for scene in scenes:
        start = scene["start_time"]
        end = scene["end_time"]
        dur = end - start

        if dur < HIGHLIGHT_MIN_DURATION:
            continue
        if dur <= SPLIT_MAX_DURATION:
            candidates.append({
                "id": _next_cand_id(),
                "start_time": round(start, 3),
                "end_time": round(end, 3),
                "duration": round(dur, 3),
                "source_scene": scene["scene_id"],
            })
        else:
            t = start
            while t + SPLIT_MIN_DURATION <= end:
                c_end = min(t + SPLIT_MAX_DURATION, end)
                c_dur = c_end - t
                if c_dur >= SPLIT_MIN_DURATION:
                    candidates.append({
                        "id": _next_cand_id(),
                        "start_time": round(t, 3),
                        "end_time": round(c_end, 3),
                        "duration": round(c_dur, 3),
                        "source_scene": scene["scene_id"],
                    })
                t += SPLIT_STRIDE
                if t + SPLIT_MIN_DURATION > end and end - t >= SPLIT_MIN_DURATION / 2:
                    candidates.append({
                        "id": _next_cand_id(),
                        "start_time": round(t, 3),
                        "end_time": round(end, 3),
                        "duration": round(end - t, 3),
                        "source_scene": scene["scene_id"],
                    })
                    break
    return candidates


# ── Detection map ───────────────────────────────────


def _build_detection_map(detections: list[dict]) -> dict:
    m: dict[float, list[dict]] = {}
    for entry in detections:
        m[entry["timestamp"]] = entry.get("detections", [])
    return m


# ── Object score ────────────────────────────────────


def _calc_object_score(
    det_map: dict[float, list[dict]],
    start: float,
    end: float,
) -> float:
    """Object density + person presence + subject area, clamped to [0,1]."""
    total_objects = 0
    person_count = 0
    areas: list[float] = []
    frame_count = 0

    for ts in sorted(det_map):
        if not (start <= ts <= end):
            continue
        frame_count += 1
        dets = det_map[ts]
        total_objects += len(dets)
        for d in dets:
            if d["class_name"] == "person":
                person_count += 1
            x1, y1, x2, y2 = d["bbox"]
            areas.append((x2 - x1) * (y2 - y1))

    if frame_count == 0:
        return 0.0

    density = min(total_objects / frame_count / 5.0, 1.0)
    person_ratio = min(person_count / max(total_objects, 1), 1.0)
    avg_area = (sum(areas) / max(len(areas), 1)) / (FRAME_WIDTH * FRAME_HEIGHT)
    avg_area = min(avg_area * 4, 1.0)

    score = 0.4 * density + 0.3 * person_ratio + 0.3 * avg_area
    return round(min(score, 1.0), 4)


# ── Motion score ────────────────────────────────────


def _compute_track_motion(tracks: list[dict]) -> dict:
    motion: dict[str, list[float]] = {}
    for track in tracks:
        boxes = track.get("boxes", [])
        displ: list[float] = []
        for i in range(1, len(boxes)):
            b0 = boxes[i - 1].get("bbox", [0, 0, 0, 0])
            b1 = boxes[i].get("bbox", [0, 0, 0, 0])
            cx0 = (b0[0] + b0[2]) / 2
            cy0 = (b0[1] + b0[3]) / 2
            cx1 = (b1[0] + b1[2]) / 2
            cy1 = (b1[1] + b1[3]) / 2
            d = math.sqrt((cx1 - cx0) ** 2 + (cy1 - cy0) ** 2)
            displ.append(d / (FRAME_WIDTH + FRAME_HEIGHT) * 2)
        if displ:
            motion[track.get("track_id", "")] = displ
    return motion


def _calc_motion_score(
    track_motion: dict[str, list[float]],
    tracks: list[dict],
    start: float,
    end: float,
) -> float:
    """Average track center displacement in the time window, clamped to [0,1]."""
    all_displ: list[float] = []
    for track in tracks:
        boxes = track.get("boxes", [])
        relevant = [b for b in boxes if start <= b.get("timestamp", 0) <= end]
        if len(relevant) < 2:
            continue
        for i in range(1, len(relevant)):
            b0 = relevant[i - 1].get("bbox", [0, 0, 0, 0])
            b1 = relevant[i].get("bbox", [0, 0, 0, 0])
            cx0 = (b0[0] + b0[2]) / 2
            cy0 = (b0[1] + b0[3]) / 2
            cx1 = (b1[0] + b1[2]) / 2
            cy1 = (b1[1] + b1[3]) / 2
            d = math.sqrt((cx1 - cx0) ** 2 + (cy1 - cy0) ** 2)
            all_displ.append(d / (FRAME_WIDTH + FRAME_HEIGHT) * 2)

    if not all_displ:
        return 0.0
    avg_m = sum(all_displ) / len(all_displ)
    return round(min(avg_m * 3, 1.0), 4)


# ── Speech score ────────────────────────────────────


def _build_subtitle_map(subtitles: list[dict]) -> list[dict]:
    return subtitles


def _calc_speech_score(subtitles: list[dict], start: float, end: float) -> float:
    """Speech density: subtitle segments per second, clamped to [0,1]."""
    count = sum(1 for s in subtitles if s["start"] < end and s["end"] > start)
    dur = max(end - start, 1.0)
    density = count / dur
    return round(min(density * 0.5, 1.0), 4)


# ── Scene score ─────────────────────────────────────


def _calc_scene_score(start: float, scene_boundaries: set[float]) -> float:
    """Higher when near a scene boundary (within 2s window)."""
    for bound in scene_boundaries:
        if abs(start - bound) <= 2.0:
            return round(1.0 - abs(start - bound) / 2.0, 4)
    return 0.0


# ── Quality score ───────────────────────────────────


def _calc_quality_score(candidate: dict) -> float:
    """Placeholder quality score.

    Currently returns a fixed value since no true quality metric (e.g.
    sharpness, exposure, stabilization) has been implemented yet.
    When HIGHLIGHT_W_QUALITY is zero, this value does not affect rankings.
    """
    return 0.7


# ── Scoring ─────────────────────────────────────────


def _compute_base_score(c: dict) -> tuple[float, dict]:
    """Compute base_score as weighted sum of 5 dimensions.

    Returns
    -------
    (base_score, score_breakdown)
        base_score in [0, 1].
        score_breakdown maps each dimension to {"raw": float, "weight": float, "weighted": float}.
    """
    raw = {
        "object": round(c.get("object_score", 0.0), 4),
        "motion": round(c.get("motion_score", 0.0), 4),
        "speech": round(c.get("speech_score", 0.0), 4),
        "scene": round(c.get("scene_score", 0.0), 4),
        "quality": round(c.get("quality_score", 0.0), 4),
    }
    breakdown = {}
    weighted_sum = 0.0
    for dim in ("object", "motion", "speech", "scene", "quality"):
        w = _WEIGHTS[dim]
        weighted = raw[dim] * w
        breakdown[dim] = {"raw": raw[dim], "weight": w, "weighted": round(weighted, 4)}
        weighted_sum += weighted
    base = round(min(max(weighted_sum, 0.0), 1.0), 4)
    return base, breakdown


# ── Diversity & Selection ───────────────────────────


def _time_overlap(a: dict, b: dict) -> float:
    """Time IoU of two candidate segments."""
    s = max(a["start_time"], b["start_time"])
    e = min(a["end_time"], b["end_time"])
    inter = max(0.0, e - s)
    union = max(a["end_time"] - a["start_time"], b["end_time"] - b["start_time"], 0.001)
    return inter / union


_LABEL_MAP = {
    "object": "目标丰富",
    "motion": "运动剧烈",
    "speech": "有字幕/语音",
    "scene": "场景切换点",
    "quality": "画面质量",
}

def _build_reason(breakdown: dict) -> list[str]:
    """Generate a Chinese reason list from score_breakdown.

    Picks the top 1-2 dimensions by weighted contribution.
    Returns a list for backward compatibility with report_service.
    """
    dims = []
    for dim, info in breakdown.items():
        dims.append((info["weighted"], dim, info["raw"]))
    dims.sort(key=lambda x: -x[0])
    parts = []
    for _, dim, raw_val in dims[:2]:
        label = _LABEL_MAP.get(dim, dim)
        parts.append(f"{label}({raw_val:.2f})")
    return parts if parts else ["综合评分"]


def _select_top_k(candidates: list[dict], k: int) -> list[dict]:
    """Greedy top-k selection with diversity penalty.

    Formula for each candidate:

        selection_score = base_score - diversity_lambda * overlap_penalty

    where overlap_penalty is the maximum time-IoU against already-selected clips.
    """
    if not candidates:
        return []

    for c in candidates:
        base, breakdown = _compute_base_score(c)
        c["_base_score"] = base
        c["_breakdown"] = breakdown

    selected: list[dict] = []

    for _ in range(min(k, len(candidates))):
        best_idx = -1
        best_score = -float("inf")
        best_overlap = 0.0
        best_base = 0.0
        best_breakdown: dict[str, float] = {}

        for i, c in enumerate(candidates):
            if c.get("_selected"):
                continue

            overlap_penalty = 0.0
            for s in selected:
                overlap = _time_overlap(c, s)
                overlap_penalty = max(overlap_penalty, overlap)

            selection = c["_base_score"] - HIGHLIGHT_DIVERSITY_LAMBDA * overlap_penalty
            selection = max(selection, 0.0)

            # Tiebreaker: prefer earlier start_time for determinism
            if selection > best_score or (abs(selection - best_score) < 1e-10 and (best_idx == -1 or c["start_time"] < candidates[best_idx]["start_time"])):
                best_score = selection
                best_idx = i
                best_overlap = overlap_penalty
                best_base = c["_base_score"]
                best_breakdown = c["_breakdown"]

        if best_idx == -1:
            break

        c = candidates[best_idx]
        c["_selected"] = True

        if best_base <= HIGHLIGHT_MIN_SCORE:
            continue

        result = {
            "id": f"hl_{len(selected) + 1:04d}",
            "start_time": c["start_time"],
            "end_time": c["end_time"],
            "duration": c["duration"],
            "base_score": round(best_base, 4),
            "selection_score": round(best_score, 4),
            "overlap_penalty": round(best_overlap, 4),
            "score_breakdown": best_breakdown,
            "score": round(best_score, 4),
            "reason": _build_reason(best_breakdown),
        }
        selected.append(result)

    return selected


# ── Save ────────────────────────────────────────────


def save_candidates(video_id: str, candidates: list[dict], duration: float | None = None) -> str | None:
    """Export raw candidate segments (before diversity selection) to JSON artifact.

    Each candidate must have: id, start_time, end_time, duration,
    object_score, motion_score, speech_score, scene_score, quality_score.

    Returns the output path string, or None if there are no candidates.
    """
    if not candidates:
        return None

    import datetime

    report_dir = REPORTS_DIR / video_id
    report_dir.mkdir(parents=True, exist_ok=True)

    export_candidates = []
    for c in candidates:
        scores = {}
        for dim in ('object', 'motion', 'speech', 'scene', 'quality'):
            raw = c.get(f'{dim}_score', 0.0)
            if not isinstance(raw, (int, float)) or math.isnan(raw) or math.isinf(raw):
                raw = 0.0
            raw = max(0.0, min(1.0, float(raw)))
            scores[dim] = raw

        reason_raw = c.get('reason', [])
        if isinstance(reason_raw, str):
            reason = [reason_raw]
        elif isinstance(reason_raw, list):
            reason = [str(r) for r in reason_raw]
        else:
            reason = []

        export_candidates.append({
            'id': str(c.get('id', 'cand_unknown')),
            'start_time': float(c.get('start_time', 0.0)),
            'end_time': float(c.get('end_time', 0.0)),
            'duration': float(c.get('duration', 0.0)),
            'scores': scores,
            'reason': reason,
            'metadata': {
                'source': 'highlight_service',
            },
        })

    valid = []
    for ec in export_candidates:
        if ec['end_time'] <= ec['start_time']:
            continue
        valid.append(ec)

    artifact = {
        'schema_version': 1,
        'video_id': video_id,
        'duration': duration if duration is not None else max((c['end_time'] for c in valid), default=0.0),
        'generated_at': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'candidates': valid,
    }

    out_path = report_dir / 'highlight_candidates.json'
    out_path.write_text(json.dumps(artifact, indent=2, ensure_ascii=False), encoding='utf-8')
    return str(out_path)


def save_highlights(video_id: str, highlights: list[dict]) -> str:
    report_dir = REPORTS_DIR / video_id
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / "highlights.json"
    out_path.write_text(json.dumps(highlights, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(out_path)


