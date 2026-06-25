"""Agent tools – thin wrappers around existing services.

Each tool accepts the current state and returns an updated state.
"""

import json
from pathlib import Path

from app.config import FRAMES_DIR, CLIPS_DIR, REPORTS_DIR
from app.services.video_metadata_service import get_video_metadata
from app.services.frame_service import extract_frames, load_frames
from app.services.scene_service import detect_scenes, save_scenes
from app.services.detection_service import detect_objects_on_frames, save_detections
from app.services.tracking_service import (
    track_objects, compute_class_statistics, save_tracking_report,
)
from app.services.highlight_service import recommend_highlights, save_highlights
from app.services.clip_export_service import export_clips
from app.services.report_service import generate_report

from .state import VideoAnalysisState


def metadata_tool(state: VideoAnalysisState, **kwargs) -> VideoAnalysisState:
    try:
        state.metadata = get_video_metadata(state.video_path)
        state.add_step("metadata", "ok")
    except Exception as e:
        state.add_step("metadata", "error", str(e)[:150])
    return state


def extract_frames_tool(
    state: VideoAnalysisState,
    sample_fps: float = 2.0,
    **kwargs,
) -> VideoAnalysisState:
    try:
        out_dir = str(FRAMES_DIR / state.video_id)
        state.frames = extract_frames(state.video_path, out_dir, sample_fps=sample_fps)
        state.add_step("extract_frames", "ok", f"{len(state.frames)} frames")
    except Exception as e:
        state.add_step("extract_frames", "error", str(e)[:150])
    return state


def detect_scenes_tool(state: VideoAnalysisState, **kwargs) -> VideoAnalysisState:
    try:
        state.scenes = detect_scenes(state.video_path)
        save_scenes(state.video_id, state.scenes)
        state.add_step("detect_scenes", "ok", f"{len(state.scenes)} scenes")
    except Exception as e:
        state.add_step("detect_scenes", "error", str(e)[:150])
    return state


def detect_objects_tool(state: VideoAnalysisState, **kwargs) -> VideoAnalysisState:
    try:
        if not state.frames:
            frames_dir = str(FRAMES_DIR / state.video_id)
            state.frames = load_frames(state.video_id, frames_dir) or state.frames
        if state.frames:
            state.detections = detect_objects_on_frames(state.frames)
            save_detections(state.video_id, state.detections)
            state.add_step("detect_objects", "ok", f"{len(state.detections)} frames")
            state.frames = None  # release from memory
        else:
            state.add_step("detect_objects", "skipped", "no frames available")
    except Exception as e:
        state.add_step("detect_objects", "error", str(e)[:150])
    return state


def track_objects_tool(state: VideoAnalysisState, **kwargs) -> VideoAnalysisState:
    try:
        if not state.frames:
            frames_dir = str(FRAMES_DIR / state.video_id)
            state.frames = load_frames(state.video_id, frames_dir) or state.frames
        if state.frames:
            state.tracks = track_objects(state.frames)
            det_path = REPORTS_DIR / state.video_id / "detections.json"
            if det_path.is_file():
                stats = compute_class_statistics(
                    json.loads(det_path.read_text(encoding="utf-8"))
                )
            else:
                stats = []
            save_tracking_report(state.video_id, stats, state.tracks)
            state.add_step("track_objects", "ok", f"{len(state.tracks)} tracks")
            state.frames = None  # release from memory
        else:
            state.add_step("track_objects", "skipped", "no frames")
    except Exception as e:
        state.add_step("track_objects", "error", str(e)[:150])
    return state


def transcribe_tool(state: VideoAnalysisState, **kwargs) -> VideoAnalysisState:
    try:
        from app.services.audio_service import extract_audio
        from app.services.subtitle_service import (
            transcribe_audio, save_subtitles, has_audio_stream,
        )

        if not has_audio_stream(state.video_path):
            state.subtitles = []
            save_subtitles(state.video_id, [])
            state.add_step("transcribe", "ok", "no audio stream")
            return state

        audio_path = extract_audio(state.video_path, state.video_id)
        if audio_path is None:
            state.subtitles = []
            save_subtitles(state.video_id, [])
            state.add_step("transcribe", "ok", "audio extraction returned none")
            return state

        state.subtitles = transcribe_audio(audio_path)
        save_subtitles(state.video_id, state.subtitles)
        state.add_step("transcribe", "ok", f"{len(state.subtitles)} segments")
    except Exception as e:
        state.add_step("transcribe", "error", str(e)[:150])
    return state


def recommend_highlights_tool(
    state: VideoAnalysisState,
    top_k: int = 5,
    **kwargs,
) -> VideoAnalysisState:
    try:
        state.highlights = recommend_highlights(state.video_id, top_k=top_k)
        save_highlights(state.video_id, state.highlights)
        state.add_step("recommend_highlights", "ok", f"{len(state.highlights)} highlights")
    except Exception as e:
        state.add_step("recommend_highlights", "error", str(e)[:150])
    return state


def export_clips_tool(state: VideoAnalysisState, **kwargs) -> VideoAnalysisState:
    try:
        hl_path = REPORTS_DIR / state.video_id / "highlights.json"
        if not hl_path.is_file():
            state.add_step("export_clips", "skipped", "no highlights.json")
            return state
        highlights = json.loads(hl_path.read_text(encoding="utf-8"))
        if not highlights:
            state.add_step("export_clips", "skipped", "empty highlights")
            return state
        state.clips = export_clips(state.video_path, highlights, state.video_id)
        state.add_step("export_clips", "ok", f"{len(highlights)} clips")
    except Exception as e:
        state.add_step("export_clips", "error", str(e)[:150])
    return state


def generate_report_tool(state: VideoAnalysisState, **kwargs) -> VideoAnalysisState:
    try:
        state.report = generate_report(state.video_id)
        state.add_step("generate_report", "ok")
    except Exception as e:
        state.add_step("generate_report", "error", str(e)[:150])
    return state


# ── Tool registry ───────────────────────────────────

TOOL_REGISTRY: dict[str, callable] = {
    "metadata": metadata_tool,
    "extract_frames": extract_frames_tool,
    "detect_scenes": detect_scenes_tool,
    "detect_objects": detect_objects_tool,
    "track_objects": track_objects_tool,
    "transcribe": transcribe_tool,
    "recommend_highlights": recommend_highlights_tool,
    "export_clips": export_clips_tool,
    "generate_report": generate_report_tool,
}
