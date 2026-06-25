import os
import json
from pathlib import Path

import cv2

from app.config import FRAMES_DIR, REPORTS_DIR


# Color palette for different classes (BGR for OpenCV)
_COLORS = [
    (0, 255, 255),    # neon cyan
    (60, 60, 255),    # neon red
    (0, 255, 0),      # neon green
    (0, 130, 255),    # orange
    (255, 0, 255),    # magenta
    (0, 165, 255),    # orange
    (255, 255, 0),    # blue
    (255, 0, 128),    # pink
    (255, 255, 128),  # light blue
    (180, 255, 128),  # light green
]
_color_index: dict[str, tuple[int, int, int]] = {}


def _get_color(class_name: str) -> tuple[int, int, int]:
    if class_name not in _color_index:
        _color_index[class_name] = _COLORS[len(_color_index) % len(_COLORS)]
    return _color_index[class_name]


def visualize_detections(video_id: str, max_frames: int = 500) -> list[str]:
    """Draw detection bboxes on extracted frames.

    Reads frames from data/frames/{video_id}/ and detections from
    data/reports/{video_id}/detections.json.  Writes annotated images
    to data/reports/{video_id}/vis_frames/.

    Returns list of relative paths to the annotated images.
    """
    det_path = REPORTS_DIR / video_id / "detections.json"
    if not det_path.is_file():
        raise FileNotFoundError(f"detections.json not found for {video_id}")

    detections = json.loads(det_path.read_text(encoding="utf-8"))
    if not detections:
        return []

    out_dir = REPORTS_DIR / video_id / "vis_frames"
    out_dir.mkdir(parents=True, exist_ok=True)

    vis_paths: list[str] = []

    for entry in detections[:max_frames]:
        frame_id = entry.get("frame_id", "")
        ts = entry.get("timestamp", 0.0)
        dets = entry.get("detections", [])

        # Locate the original frame
        frame_path = _find_frame(video_id, frame_id)
        if frame_path is None:
            continue

        img = cv2.imread(str(frame_path))
        if img is None:
            continue

        h, w = img.shape[:2]

        for d in dets:
            cls_name = d["class_name"]
            conf = d["confidence"]
            x1, y1, x2, y2 = d["bbox"]
            # Clamp to image bounds
            x1, y1 = int(max(0, x1)), int(max(0, y1))
            x2, y2 = int(min(w, x2)), int(min(h, y2))

            color = _get_color(cls_name)

            # Draw bbox
            cv2.rectangle(img, (x1, y1), (x2, y2), color, 4)

            # Label background
            label = f"{cls_name} {conf:.2f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
            cv2.rectangle(img, (x1, y1 - th - 8), (x1 + tw + 8, y1), color, -1)

            # Label text (white)
            cv2.putText(img, label, (x1 + 4, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

        out_name = f"{frame_id}_vis.jpg"
        out_path = out_dir / out_name
        cv2.imwrite(str(out_path), img, [cv2.IMWRITE_JPEG_QUALITY, 90])
        vis_paths.append(str(out_path))

    return vis_paths


def _find_frame(video_id: str, frame_id: str) -> Path | None:
    """Look for the original frame image in data/frames/{video_id}/."""
    frames_dir = FRAMES_DIR / video_id
    if not frames_dir.is_dir():
        return None

    # Try exact filename first
    for ext in (".jpg", ".jpeg", ".png"):
        p = frames_dir / f"{frame_id}{ext}"
        if p.is_file():
            return p

    # Try partial match
    for p in sorted(frames_dir.iterdir()):
        if p.stem == frame_id and p.suffix.lower() in (".jpg", ".jpeg", ".png"):
            return p

    return None
