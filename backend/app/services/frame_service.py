import json
import os
from pathlib import Path

import cv2


def extract_frames(
    video_path: str,
    output_dir: str,
    sample_fps: float = 2.0,
) -> list[dict]:
    """Extract frames from a video at a given sampling rate.

    Parameters
    ----------
    video_path : str
        Path to the source video file.
    output_dir : str
        Directory where frames will be saved.
    sample_fps : float, optional
        Number of frames to extract per second of video (default 2).

    Returns
    -------
    list[dict]
        Each entry: {frame_id, timestamp, path}
    """
    video_path = str(Path(video_path).resolve())
    output_dir = str(Path(output_dir).resolve())

    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    original_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Interval: extract 1 frame every N original frames
    interval = max(1, int(original_fps / sample_fps)) if original_fps > 0 else 1

    frames: list[dict] = []
    frame_index = 0
    read_count = 0

    while True:
        ret, img = cap.read()
        if not ret:
            break

        if read_count % interval == 0:
            frame_index += 1
            timestamp = round(read_count / original_fps, 3) if original_fps > 0 else 0.0
            frame_name = f"frame_{frame_index:06d}.jpg"
            frame_path = os.path.join(output_dir, frame_name)

            cv2.imwrite(frame_path, img, [cv2.IMWRITE_JPEG_QUALITY, 85])

            frames.append({
                "frame_id": frame_name.replace(".jpg", ""),
                "timestamp": timestamp,
                "path": frame_path,
            })

        read_count += 1

    cap.release()

    # Save an index for later use by other services
    _save_frames_index(output_dir, frames)

    return frames


def _save_frames_index(output_dir: str, frames: list[dict]) -> None:
    """Write _frames_index.json so detection etc. can reload metadata."""
    index_path = os.path.join(output_dir, "_frames_index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(frames, f, indent=2)


def load_frames(video_id: str, frames_dir: str) -> list[dict]:
    """Load frames list from disk (read _frames_index.json or scan directory).

    Returns frames sorted by timestamp.
    """
    frames_dir = str(Path(frames_dir).resolve())
    index_path = os.path.join(frames_dir, "_frames_index.json")

    if os.path.isfile(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # Fallback: scan directory
    frames: list[dict] = []
    for fname in sorted(os.listdir(frames_dir)):
        if not fname.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        frame_id = Path(fname).stem
        frames.append({
            "frame_id": frame_id,
            "timestamp": 0.0,
            "path": os.path.join(frames_dir, fname),
        })
    return frames
