from __future__ import annotations

import json
import os
from pathlib import Path

import logging

logger = logging.getLogger(__name__)

from app.config import REPORTS_DIR, FRAMES_DIR
from app.services.frame_service import load_frames


# Default model – can be overridden via env var
from app.config import YOLO_MODEL_PATH as _MODEL_PATH, YOLO_DEVICE as _YOLO_DEVICE
_CONFIDENCE_THRESHOLD = 0.25


_model = None  # lazy-loaded via _get_model()


def _get_model():
    """Lazy-load the YOLO model (loaded once and reused)."""
    from ultralytics import YOLO
    global _model
    if _model is None:
        logger.info("Initialising YOLO model device=%s path=%s", _YOLO_DEVICE, _MODEL_PATH)
        _model = YOLO(str(_MODEL_PATH))
    return _model


def detect_objects_on_frames(frames: list[dict]) -> list[dict]:
    """Run YOLO detection on a list of frames.

    Parameters
    ----------
    frames : list[dict]
        Each entry must have keys: frame_id, timestamp, path

    Returns
    -------
    list[dict]
        Each entry: {frame_id, timestamp, detections: [{class_name, confidence, bbox}]}
        bbox format: [x1, y1, x2, y2] in pixels
    """
    model = _get_model()
    results: list[dict] = []

    for frame in frames:
        frame_id = frame.get("frame_id", "")
        timestamp = frame.get("timestamp", 0.0)
        path = frame.get("path", "")

        if not path or not os.path.isfile(path):
            continue

        detections = _infer_one(model, path)
        results.append({
            "frame_id": frame_id,
            "timestamp": timestamp,
            "detections": detections,
        })

    return results


def _infer_one(model: YOLO, image_path: str) -> list[dict]:
    """Run inference on a single image and return filtered detections."""
    output = model(image_path, verbose=False, device=_YOLO_DEVICE)
    detections: list[dict] = []

    for result in output:
        if result.boxes is None:
            continue
        for box in result.boxes:
            conf = float(box.conf[0])
            if conf < _CONFIDENCE_THRESHOLD:
                continue
            cls_id = int(box.cls[0])
            class_name = result.names[cls_id]
            xyxy = [round(float(v), 4) for v in box.xyxy[0]]
            detections.append({
                "class_name": class_name,
                "confidence": round(conf, 4),
                "bbox": xyxy,
            })

    return detections


def save_detections(video_id: str, detections: list[dict]) -> str:
    """Save detection results to data/reports/{video_id}/detections.json."""
    report_dir = REPORTS_DIR / video_id
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / "detections.json"
    out_path.write_text(json.dumps(detections, indent=2), encoding="utf-8")
    return str(out_path)
