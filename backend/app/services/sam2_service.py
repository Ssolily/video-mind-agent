"""SAM 2 segmentation module — completely optional.

If SAM 2 is not installed or weights are missing, all functions
return None and _available is False.  Nothing breaks.
"""

import os
import json
from pathlib import Path

import cv2
import numpy as np

from app.config import REPORTS_DIR, FRAMES_DIR

# ── Availability check ──────────────────────────────

_AVAILABLE = False
_SAM2_ERROR = ""
_PREDICTOR = None

try:
    from sam2.build_sam import build_sam2
    from sam2.sam2_image_predictor import SAM2ImagePredictor
    _SAM2_BUILD = build_sam2
    _SAM2_PREDICTOR = SAM2ImagePredictor
    _AVAILABLE = True
except ImportError as e:
    _AVAILABLE = False
    _SAM2_ERROR = f"SAM 2 package not installed: {e}"

# Default config — point to SAM 2 repo checkpoints
_SAM2_CONFIG = os.getenv(
    "SAM2_CONFIG",
    os.path.join(os.path.dirname(__file__), *[".."]*3, "sam2", "sam2", "configs", "sam2", "sam2_hiera_b+.yaml"),
)
_SAM2_CHECKPOINT = os.getenv(
    "SAM2_CHECKPOINT",
    os.path.join(os.path.dirname(__file__), *[".."]*3, "sam2", "checkpoints", "sam2_hiera_base_plus.pt"),
)


def is_available() -> tuple[bool, str]:
    """Return (available, error_message)."""
    if not _AVAILABLE:
        return False, _SAM2_ERROR
    if not os.path.isfile(_SAM2_CONFIG):
        return False, f"SAM 2 config not found: {_SAM2_CONFIG}"
    if not os.path.isfile(_SAM2_CHECKPOINT):
        return False, f"SAM 2 checkpoint not found: {_SAM2_CHECKPOINT}"
    return True, ""


def _get_predictor():
    """Lazy-init the predictor singleton."""
    global _PREDICTOR
    if _PREDICTOR is not None:
        return _PREDICTOR

    available, err = is_available()
    if not available:
        raise RuntimeError(err)

    from app.config import SAM2_DEVICE as _SAM2_DEVICE
    sam = _SAM2_BUILD(_SAM2_CONFIG, _SAM2_CHECKPOINT, device=_SAM2_DEVICE)
    _PREDICTOR = _SAM2_PREDICTOR(sam)
    return _PREDICTOR


# ── Segmentation ────────────────────────────────────


def segment_with_bbox(
    image_path: str,
    bbox: list[float],
) -> dict | None:
    """Run SAM 2 on a single image with a bbox prompt.

    Parameters
    ----------
    image_path : str
        Path to the input image.
    bbox : list[float]
        [x1, y1, x2, y2] in pixel coordinates.

    Returns
    -------
    dict with keys:
        mask_path : str   (path to saved mask PNG)
        mask : list[list] (binary mask as nested list for JSON)
        area : float      (mask pixel area)
    or None if SAM 2 is unavailable.
    """
    available, err = is_available()
    if not available:
        return None

    image_path = str(Path(image_path).resolve())
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    predictor = _get_predictor()
    predictor.set_image(image)

    masks, scores, _ = predictor.predict(box=bbox)

    if masks is None or len(masks) == 0:
        return None

    # Pick the mask with the highest IoU score
    best_idx = int(np.argmax(scores))
    mask = masks[best_idx]  # (H, W) bool
    score = float(scores[best_idx])
    area = int(np.sum(mask))

    return {
        "mask": mask.tolist(),
        "area": area,
        "score": round(score, 4),
    }


def segment_main_object(video_id: str) -> dict | None:
    """Pick the best object from detections and run SAM 2 segmentation.

    Selection priority:
      1. The person with the largest bbox area.
      2. If no person, the detection with the highest confidence.

    The mask is saved to data/reports/{video_id}/masks/.

    Returns
    -------
    dict with keys: frame_path, bbox, class_name, confidence, mask_path
    or a dict with "message" if nothing could be segmented.
    """
    available, err = is_available()
    if not available:
        return {"message": f"SAM 2 unavailable: {err}"}

    det_path = REPORTS_DIR / video_id / "detections.json"
    if not det_path.is_file():
        return {"message": "detections.json not found. Run detect-objects first."}

    detections = json.loads(det_path.read_text(encoding="utf-8"))
    if not detections:
        return {"message": "No detections found."}

    # Find the best target
    target = _pick_best_target(detections)
    if target is None:
        return {"message": "No suitable detection found for segmentation."}

    frame_id = target["frame_id"]
    bbox = target["bbox"]
    cls_name = target["class_name"]
    confidence = target["confidence"]

    # Locate the original frame
    frames_dir = FRAMES_DIR / video_id
    if not frames_dir.is_dir():
        return {"message": f"Frames directory not found: {frames_dir}"}

    frame_path = None
    for ext in (".jpg", ".jpeg", ".png"):
        p = frames_dir / f"{frame_id}{ext}"
        if p.is_file():
            frame_path = str(p)
            break
    if frame_path is None:
        return {"message": f"Frame not found on disk: {frame_id}"}

    # Run segmentation
    result = segment_with_bbox(frame_path, bbox)
    if result is None:
        return {"message": "SAM 2 returned no mask."}

    # Save mask as PNG
    mask_dir = REPORTS_DIR / video_id / "masks"
    mask_dir.mkdir(parents=True, exist_ok=True)
    mask_path = mask_dir / f"{frame_id}_mask.png"

    mask_array = np.array(result["mask"], dtype=np.uint8) * 255
    cv2.imwrite(str(mask_path), mask_array)

    # Save mask overlay for preview
    overlay = cv2.imread(frame_path)
    if overlay is not None:
        colored = np.zeros_like(overlay, dtype=np.uint8)
        colored[:, :] = (0, 255, 0)  # green overlay (BGR)
        mask_3ch = cv2.merge([mask_array, mask_array, mask_array])
        overlay = cv2.addWeighted(overlay, 0.6, cv2.bitwise_and(colored, mask_3ch), 0.4, 0)
        overlay_path = mask_dir / f"{frame_id}_overlay.jpg"
        cv2.imwrite(str(overlay_path), overlay, [cv2.IMWRITE_JPEG_QUALITY, 90])
    else:
        overlay_path = None

    return {
        "frame_path": frame_path,
        "bbox": bbox,
        "class_name": cls_name,
        "confidence": confidence,
        "mask_path": str(mask_path),
        "overlay_path": str(overlay_path) if overlay_path else None,
        "mask_area": result["area"],
        "mask_score": result["score"],
    }


# ── Selection helpers ───────────────────────────────


def _pick_best_target(detections: list[dict]) -> dict | None:
    """Select the best detection for segmentation."""
    persons: list[dict] = []
    best_conf: dict | None = None

    for entry in detections:
        frame_id = entry.get("frame_id", "")
        ts = entry.get("timestamp", 0.0)
        for d in entry.get("detections", []):
            x1, y1, x2, y2 = d["bbox"]
            area = (x2 - x1) * (y2 - y1)
            cand = {
                "frame_id": frame_id,
                "timestamp": ts,
                "bbox": d["bbox"],
                "class_name": d["class_name"],
                "confidence": d["confidence"],
                "area": area,
            }
            if d["class_name"] == "person":
                persons.append(cand)
            if best_conf is None or d["confidence"] > best_conf["confidence"]:
                best_conf = cand

    # Priority 1: largest person
    if persons:
        persons.sort(key=lambda x: -x["area"])
        return persons[0]

    # Priority 2: highest confidence
    if best_conf is not None:
        return best_conf

    return None
