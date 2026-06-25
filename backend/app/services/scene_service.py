import json
import os
from pathlib import Path

from scenedetect import open_video, SceneManager, ContentDetector

from app.config import REPORTS_DIR


def detect_scenes(video_path: str) -> list[dict]:
    """Detect scene boundaries using PySceneDetect (ContentDetector).

    Returns a list of scenes sorted by start time.
    Each scene: {scene_id, start_time, end_time, duration}
    """
    video_path = str(Path(video_path).resolve())
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    try:
        video = open_video(video_path)
        sm = SceneManager()
        sm.add_detector(ContentDetector())
        sm.detect_scenes(video)
        scene_list = sm.get_scene_list()
    except Exception:
        scene_list = None

    scenes = _build_scenes(scene_list, video_path)
    return scenes


def _build_scenes(
    raw_scenes: list | None,
    video_path: str,
) -> list[dict]:
    """Convert raw scene list (or None) into a list of scene dicts."""
    result: list[dict] = []

    if raw_scenes:
        for i, (start_tc, end_tc) in enumerate(raw_scenes, start=1):
            start = start_tc.seconds
            end = end_tc.seconds
            result.append({
                "scene_id": f"scene_{i:04d}",
                "start_time": round(start, 3),
                "end_time": round(end, 3),
                "duration": round(end - start, 3),
            })
    else:
        # Fallback: treat the whole video as one scene
        try:
            import cv2
            cap = cv2.VideoCapture(video_path)
            duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS) if cap.get(cv2.CAP_PROP_FPS) > 0 else 0
            cap.release()
        except Exception:
            duration = 0.0

        result.append({
            "scene_id": "scene_0001",
            "start_time": 0.0,
            "end_time": round(duration, 3),
            "duration": round(duration, 3),
        })

    return result


def save_scenes(video_id: str, scenes: list[dict]) -> str:
    """Save scene list to data/reports/{video_id}/scenes.json and return the path."""
    report_dir = REPORTS_DIR / video_id
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / "scenes.json"
    out_path.write_text(json.dumps(scenes, indent=2), encoding="utf-8")
    return str(out_path)
