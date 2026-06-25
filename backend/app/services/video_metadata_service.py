import subprocess
import json
import os
from pathlib import Path

import cv2


def get_video_metadata(video_path: str) -> dict:
    """Read video metadata using ffprobe, falling back to OpenCV.

    Returns
    -------
    dict with keys: duration, fps, width, height, frame_count
    """
    path = str(Path(video_path).resolve())
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Video not found: {path}")

    meta = _with_ffprobe(path)
    if meta is not None:
        return meta

    meta = _with_opencv(path)
    if meta is not None:
        return meta

    raise RuntimeError(f"Unable to read metadata from: {path}")


# ── ffprobe (preferred) ──────────────────────────────


def _with_ffprobe(path: str) -> dict | None:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None

        data = json.loads(result.stdout)
        video_stream = _find_video_stream(data.get("streams", []))

        if video_stream is None:
            return None

        duration = _safe_float(data.get("format", {}).get("duration", 0))
        width = int(video_stream.get("width", 0))
        height = int(video_stream.get("height", 0))
        fps_str = video_stream.get("r_frame_rate", "0/1")
        fps = _parse_fraction(fps_str)
        frame_count_str = video_stream.get("nb_frames")
        frame_count = int(frame_count_str) if frame_count_str else _estimate_frame_count(duration, fps)

        return {
            "duration": round(duration, 3),
            "fps": round(fps, 3),
            "width": width,
            "height": height,
            "frame_count": frame_count,
        }
    except Exception:
        return None


# ── OpenCV fallback ──────────────────────────────────


def _with_opencv(path: str) -> dict | None:
    try:
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return None

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps if fps > 0 else 0

        cap.release()

        return {
            "duration": round(duration, 3),
            "fps": round(fps, 3),
            "width": width,
            "height": height,
            "frame_count": frame_count,
        }
    except Exception:
        return None


# ── Helpers ──────────────────────────────────────────


def _find_video_stream(streams: list) -> dict | None:
    for s in streams:
        if s.get("codec_type") == "video":
            return s
    return None


def _parse_fraction(frac: str) -> float:
    try:
        parts = frac.split("/")
        if len(parts) == 2:
            num, den = float(parts[0]), float(parts[1])
            return num / den if den != 0 else 0.0
        return float(parts[0])
    except (ValueError, IndexError):
        return 0.0


def _safe_float(val) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def _estimate_frame_count(duration: float, fps: float) -> int:
    return int(duration * fps) if fps > 0 else 0
