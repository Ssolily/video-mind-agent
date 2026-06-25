import json
import os
from pathlib import Path


from app.config import REPORTS_DIR


# ── Model — reused from detection_service (singleton) ──
from app.services.detection_service import _get_model


# ── Statistics ──────────────────────────────────────


def compute_class_statistics(detections_data: list[dict]) -> list[dict]:
    """Aggregate per-class statistics across all frames.

    Returns
    -------
    list[dict]
        Each entry: {class_name, total_occurrences, frame_count, avg_confidence}
    """
    stats: dict[str, dict] = {}

    for entry in detections_data:
        for det in entry.get("detections", []):
            cls = det["class_name"]
            if cls not in stats:
                stats[cls] = {
                    "class_name": cls,
                    "total_occurrences": 0,
                    "frames": set(),
                    "confidences": [],
                }
            stats[cls]["total_occurrences"] += 1
            stats[cls]["frames"].add(entry.get("frame_id", ""))
            stats[cls]["confidences"].append(det["confidence"])

    result = []
    for cls, s in sorted(stats.items()):
        result.append({
            "class_name": cls,
            "total_occurrences": s["total_occurrences"],
            "frame_count": len(s["frames"]),
            "avg_confidence": round(
                sum(s["confidences"]) / len(s["confidences"]), 4
            ),
        })
    return result


# ── ByteTrack via YOLO ──────────────────────────────


def track_objects(frames_data: list[dict]) -> list[dict]:
    """Track objects across frames using Ultralytics YOLO track (ByteTrack).

    Parameters
    ----------
    frames_data : list[dict]
        Sorted by timestamp ascending. Each entry: {frame_id, timestamp, path}

    Returns
    -------
    list[dict]
        Each track: {track_id, class_name, start_time, end_time, duration, boxes[]}
    """
    model = _get_model()

    # Collect valid frame paths and corresponding frame metadata
    valid_frames = [f for f in frames_data if os.path.isfile(f.get("path", ""))]
    if not valid_frames:
        return []

    frame_paths = [f["path"] for f in valid_frames]

    # Run YOLO track on all frames sequentially
    from app.config import YOLO_DEVICE as _YOLO_DEVICE
    results = model.track(
        frame_paths, persist=True, verbose=False, device=_YOLO_DEVICE, stream=True
    )

    # YOLO track_id -> our track dict
    tracks_map: dict[int, dict] = {}
    # Counter for fallback tracks (when track ID is not available)
    fallback_counter = [0]

    for result, frame_data in zip(results, valid_frames):
        ts = frame_data["timestamp"]
        frame_id = frame_data["frame_id"]

        if result.boxes is None or len(result.boxes) == 0:
            continue

        ids_tensor = result.boxes.id
        cls_tensor = result.boxes.cls
        conf_tensor = result.boxes.conf
        xyxy_tensor = result.boxes.xyxy

        for i in range(len(result.boxes)):
            cls_id = int(cls_tensor[i])
            class_name = result.names[cls_id]
            conf = round(float(conf_tensor[i]), 4)
            bbox = [round(float(v), 4) for v in xyxy_tensor[i].tolist()]

            # Determine track identifier
            yolo_track_id = (
                int(ids_tensor[i]) if ids_tensor is not None else None
            )

            if yolo_track_id is not None:
                # ByteTrack assigned a stable ID
                _append_to_track(tracks_map, yolo_track_id, class_name, ts, bbox, conf)
            else:
                # Fallback: treat each detection as a single-frame track
                fallback_counter[0] += 1
                _append_to_track(
                    tracks_map,
                    -(fallback_counter[0]),  # negative = synthetic fallback id
                    class_name,
                    ts,
                    bbox,
                    conf,
                )

    # Build final output sorted by start time
    tracks = list(tracks_map.values())
    tracks.sort(key=lambda t: t["start_time"])

    # Assign human-readable track_ids
    for i, t in enumerate(tracks, start=1):
        t["track_id"] = f"track_{i:04d}"

    return tracks


def _append_to_track(
    tracks_map: dict,
    track_key: int,
    class_name: str,
    timestamp: float,
    bbox: list[float],
    confidence: float,
) -> None:
    """Add a detection to an existing track or create a new one."""
    if track_key not in tracks_map:
        tracks_map[track_key] = {
            "track_id": "",  # will be assigned at the end
            "class_name": class_name,
            "start_time": timestamp,
            "end_time": timestamp,
            "duration": 0.0,
            "boxes": [],
        }

    track = tracks_map[track_key]
    track["end_time"] = timestamp
    track["duration"] = round(timestamp - track["start_time"], 3)
    track["boxes"].append({
        "timestamp": timestamp,
        "bbox": bbox,
        "confidence": confidence,
    })


# ── Save / Load ─────────────────────────────────────


def save_tracking_report(
    video_id: str,
    statistics: list[dict],
    tracks: list[dict],
) -> dict:
    """Save stats and tracks to reports/{video_id}/ and return paths."""
    report_dir = REPORTS_DIR / video_id
    report_dir.mkdir(parents=True, exist_ok=True)

    stats_path = report_dir / "class_stats.json"
    stats_path.write_text(json.dumps(statistics, indent=2), encoding="utf-8")

    tracks_path = report_dir / "tracks.json"
    tracks_path.write_text(json.dumps(tracks, indent=2), encoding="utf-8")

    return {
        "stats_path": str(stats_path),
        "tracks_path": str(tracks_path),
    }

