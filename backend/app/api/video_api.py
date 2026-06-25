import json
import os
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Request
from fastapi.responses import Response

from app.config import FRAMES_DIR, REPORTS_DIR
from app.services.storage_service import save_uploaded_video, get_video_path
from app.services.frame_service import extract_frames, load_frames
from app.services.scene_service import detect_scenes, save_scenes
from app.services.detection_service import detect_objects_on_frames, save_detections
from app.services.tracking_service import (
    compute_class_statistics,
    track_objects,
    save_tracking_report,
)

router = APIRouter(prefix="/videos", tags=["videos"])


@router.get("")
async def list_videos():
    """Placeholder - list uploaded videos."""
    return {"videos": []}


@router.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    """Upload a single video file. Accepts mp4, mov, avi."""
    result = await save_uploaded_video(file)
    # Replace raw_path with safe source_url
    video_id = result.get("video_id", "")
    result["source_url"] = f"/api/v1/videos/{video_id}/source"
    result.pop("raw_path", None)
    return result


@router.post("/{video_id}/extract-frames")
async def extract_frames_endpoint(
    video_id: str,
    sample_fps: float = Query(2.0, description="Frames per second to extract"),
):
    """Extract frames from an uploaded video."""
    raw_path = get_video_path(video_id)
    if not raw_path:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    output_dir = FRAMES_DIR / video_id
    frames = extract_frames(raw_path, str(output_dir), sample_fps=sample_fps)

    return {"video_id": video_id, "frame_count": len(frames), "frames": frames}


@router.post("/{video_id}/detect-scenes")
async def detect_scenes_endpoint(video_id: str):
    """Detect scene boundaries using PySceneDetect."""
    raw_path = get_video_path(video_id)
    if not raw_path:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    scenes = detect_scenes(raw_path)
    report_path = save_scenes(video_id, scenes)

    return {
        "video_id": video_id,
        "scene_count": len(scenes),
        "scenes": scenes,
        "report_path": report_path,
    }


@router.post("/{video_id}/detect-objects")
async def detect_objects_endpoint(video_id: str):
    """Run YOLO object detection on previously extracted frames."""
    raw_path = get_video_path(video_id)
    if not raw_path:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    frames_dir = FRAMES_DIR / video_id
    if not frames_dir.is_dir():
        raise HTTPException(
            status_code=400,
            detail="No frames found. Call /extract-frames first.",
        )

    frames = load_frames(video_id, str(frames_dir))
    if not frames:
        raise HTTPException(
            status_code=400,
            detail="Frame directory is empty. Call /extract-frames first.",
        )

    detections = detect_objects_on_frames(frames)
    report_path = save_detections(video_id, detections)

    class_counts: dict[str, int] = {}
    for entry in detections:
        for d in entry.get("detections", []):
            cls = d["class_name"]
            class_counts[cls] = class_counts.get(cls, 0) + 1

    return {
        "video_id": video_id,
        "frames_processed": len(detections),
        "total_detections": sum(len(d["detections"]) for d in detections),
        "class_summary": class_counts,
        "report_path": report_path,
    }


@router.post("/{video_id}/track-objects")
async def track_objects_endpoint(video_id: str):
    """Run ByteTrack tracking across frames and compute class statistics."""
    raw_path = get_video_path(video_id)
    if not raw_path:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    # Frames are required for YOLO track
    frames_dir = FRAMES_DIR / video_id
    if not frames_dir.is_dir():
        raise HTTPException(
            status_code=400,
            detail="No frames found. Call /extract-frames first.",
        )

    frames = load_frames(video_id, str(frames_dir))
    if not frames:
        raise HTTPException(
            status_code=400,
            detail="Frame directory is empty. Call /extract-frames first.",
        )

    # Run ByteTrack via YOLO
    tracks = track_objects(frames)

    # Statistics still sourced from detections.json (if available)
    detections_path = REPORTS_DIR / video_id / "detections.json"
    if detections_path.is_file():
        detections_data = json.loads(detections_path.read_text(encoding="utf-8"))
        statistics = compute_class_statistics(detections_data) if detections_data else []
    else:
        statistics = []

    report_paths = save_tracking_report(video_id, statistics, tracks)

    return {
        "video_id": video_id,
        "track_count": len(tracks),
        "statistics": statistics,
        "report_paths": report_paths,
    }

@router.post("/{video_id}/recommend-highlights")
async def recommend_highlights_endpoint(
    video_id: str,
    top_k: int = Query(5, ge=1, le=20, description="Number of highlights to recommend"),
):
    """Analyze scenes, detections, tracks, and subtitles to recommend highlight clips."""
    from app.services.storage_service import get_video_path
    from app.services.highlight_service import recommend_highlights, save_highlights

    raw_path = get_video_path(video_id)
    if not raw_path:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    highlights = recommend_highlights(video_id, top_k=top_k)
    report_path = save_highlights(video_id, highlights)

    return {
        "video_id": video_id,
        "highlight_count": len(highlights),
        "highlights": highlights,
        "report_path": report_path,
    }



@router.post("/{video_id}/export-clips")
async def export_clips_endpoint(video_id: str):
    """Cut highlight clips from the original video using FFmpeg."""
    from app.services.storage_service import get_video_path
    from app.services.clip_export_service import export_clips

    raw_path = get_video_path(video_id)
    if not raw_path:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    highlights_path = REPORTS_DIR / video_id / "highlights.json"
    if not highlights_path.is_file():
        raise HTTPException(
            status_code=400,
            detail="No highlights found. Call /recommend-highlights first.",
        )

    highlights = json.loads(highlights_path.read_text(encoding="utf-8"))
    if not highlights:
        raise HTTPException(
            status_code=400,
            detail="Highlights list is empty.",
        )

    export_result = export_clips(raw_path, highlights, video_id)

    clips_out = []
    for i, h in enumerate(highlights, start=1):
        clip_id = f"clip_{i:03d}"
        clips_out.append({
            "id": clip_id,
            "url": f"/api/v1/videos/{video_id}/clips/{clip_id}",
            "start_time": h.get("start_time"),
            "end_time": h.get("end_time"),
            "duration": h.get("duration"),
            "highlight_id": h.get("id", f"hl_{i:04d}"),
        })

    highlight_url = None
    if export_result.get("highlight_path"):
        hl_path = export_result["highlight_path"]
        if hl_path and Path(hl_path).is_file():
            highlight_url = f"/api/v1/videos/{video_id}/clips/highlight"

    return {
        "video_id": video_id,
        "clip_count": len(export_result.get("clip_paths", [])),
        "clips": clips_out,
        "highlight_url": highlight_url,
    }



@router.post("/{video_id}/analyze")
async def analyze_endpoint(
    video_id: str,
    sample_fps: float = Query(2.0, description="Frames per second to extract"),
    top_k: int = Query(5, ge=1, le=20, description="Number of highlights"),
    planner_provider: str = Query("", description="Planner mode: llm or rule (default from env)"),
    enable_subtitle: bool = Query(True, description="Enable speech-to-text"),
    export_clips: bool = Query(True, description="Export highlight clips"),
):
    """Run the full video analysis pipeline."""
    from app.services.pipeline_service import analyze_video

    result = analyze_video(
        video_id,
        sample_fps=sample_fps,
        top_k=top_k,
        enable_subtitle=enable_subtitle,
        export_clips_enabled=export_clips,
    )

    if result["status"] == "error":
        raise HTTPException(status_code=404, detail=result.get("error", "Unknown error"))

    return result



@router.get("/{video_id}/report")
async def get_report(video_id: str):
    """Generate and return the report content."""
    from app.services.report_service import generate_report

    raw_path = get_video_path(video_id)
    if not raw_path:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    result = generate_report(video_id)

    # Also return the markdown text so the frontend doesn't need a second request
    md_text = ""
    md_path = result.get("md_path", "")
    if md_path:
        try:
            md_text = Path(md_path).read_text(encoding="utf-8")
        except Exception:
            pass

    return {
        "markdown": md_text,
        "markdown_url": f"/api/v1/videos/{video_id}/reports/markdown",
        "json_url": f"/api/v1/videos/{video_id}/reports/json",
    }



@router.post("/{video_id}/agent-run")
async def agent_run(
    video_id: str,
    user_goal: str = Query(..., description="User's intent"),
    sample_fps: float = Query(2.0, description="Frames per second"),
    top_k: int = Query(5, ge=1, le=20, description="Number of highlights"),
    planner_provider: str = Query("", description="Planner mode: llm or rule (default from env)"),
):
    """Start a background agent task. Returns task_id immediately."""
    from app.services.task_service import create_task
    from app.services.storage_service import get_video_path

    raw_path = get_video_path(video_id)
    if not raw_path:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    # Check disk space before creating task
    from app.services.storage_service import check_disk_space
    check_disk_space()

    task_id = create_task(video_id=video_id, user_goal=user_goal, sample_fps=sample_fps, top_k=top_k)

    # Create storage manifest for this task
    try:
        from app.services.storage_manifest_service import create_manifest, add_file
        create_manifest(task_id, video_id, status="queued")
        # Record upload file if it exists
        from app.services.storage_service import get_video_path
        raw_path = get_video_path(video_id)
        if raw_path:
            add_file(task_id, "upload", raw_path)
    except Exception:
        pass

    return {"task_id": task_id, "status": "queued"}





@router.post("/{video_id}/visualize-detections")
async def visualize_detections_endpoint(video_id: str, max_frames: int = Query(500, description="Max frames to annotate")):
    """Draw detection bboxes on extracted frames."""
    from app.services.visualization_service import visualize_detections

    raw_path = get_video_path(video_id)
    if not raw_path:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    frames_dir = FRAMES_DIR / video_id
    if not frames_dir.is_dir():
        raise HTTPException(status_code=400, detail="No frames found. Call /extract-frames first.")

    vis_paths = visualize_detections(video_id, max_frames=max_frames)

    # Convert local paths to URLs for frontend access
    base_url = "/static/reports"
    vis_urls = []
    for p in vis_paths:
        rel = p.split("\\reports\\", 1)[-1] if "\\reports\\" in p else p.split("/reports/", 1)[-1]
        vis_urls.append(f"{base_url}/{rel.replace(os.sep, '/')}")

    return {
        "video_id": video_id,
        "frame_count": len(vis_urls),
        "image_urls": vis_urls,
    }



@router.post("/{video_id}/segment-main-object")
async def segment_main_object_endpoint(video_id: str):
    """Segment the main object using SAM 2 with bbox prompt.

    Selects the best detection (largest person or highest confidence)
    and runs SAM 2 to produce a pixel-level mask.
    """
    from app.services.sam2_service import segment_main_object, is_available

    raw_path = get_video_path(video_id)
    if not raw_path:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    avail, err = is_available()
    if not avail:
        return {"message": f"SAM 2 is not available: {err}", "hint": "Install SAM 2 and download checkpoints to enable this feature."}

    result = segment_main_object(video_id)

    # Convert local mask path to URL if present
    if result and "mask_path" in result and result["mask_path"]:
        rel = result["mask_path"].split("\\reports\\", 1)[-1] if "\\reports\\" in result["mask_path"] else result["mask_path"].split("/reports/", 1)[-1]
        result["mask_url"] = f"/static/reports/{rel.replace(os.sep, '/')}"
    if result and "overlay_path" in result and result.get("overlay_path"):
        rel = result["overlay_path"].split("\\reports\\", 1)[-1]
        result["overlay_url"] = f"/static/reports/{rel.replace(os.sep, '/')}"

    return result


@router.post("/{video_id}/transcribe")
async def transcribe_endpoint(video_id: str):
    """Extract audio and transcribe speech to subtitles."""
    raw_path = get_video_path(video_id)
    if not raw_path:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    from app.services.audio_service import extract_audio
    from app.services.subtitle_service import transcribe_audio, save_subtitles, has_audio_stream

    # Quick check for audio stream
    if not has_audio_stream(raw_path):
        return {
            "video_id": video_id,
            "segments": [],
            "message": "No audio stream found.",
            "report_paths": save_subtitles(video_id, []),
        }

    # Extract audio
    audio_path = extract_audio(raw_path, video_id)
    if audio_path is None:
        return {
            "video_id": video_id,
            "segments": [],
            "message": "Audio extraction returned no output.",
            "report_paths": save_subtitles(video_id, []),
        }

    # Transcribe
    segments = transcribe_audio(audio_path)
    report_paths = save_subtitles(video_id, segments)

    return {
        "video_id": video_id,
        "segment_count": len(segments),
        "segments": segments[:5],  # preview
        "report_paths": report_paths,
    }


# ── Media streaming endpoints (P1-A3) ────────────


@router.get("/{video_id}/source")
async def stream_source_video(video_id: str, request: Request):
    """Stream the original uploaded video with HTTP Range support.

    Supports browser seeking and partial content via the Range header.
    Returns 200 for full requests, 206 for valid Range requests,
    and 416 for unsatisfiable ranges.
    """
    from app.config import RAW_VIDEOS_DIR
    from app.services.media_stream_service import resolve_video_path, guess_video_mime, build_media_response

    path = resolve_video_path(video_id, RAW_VIDEOS_DIR)
    content_type = guess_video_mime(path)
    return build_media_response(path, request, content_type)


@router.get("/{video_id}/clips/{clip_id}")
async def stream_clip(video_id: str, clip_id: str, request: Request):
    """Stream an exported highlight clip with HTTP Range support.

    clip_id can be a short ID (e.g. ``clip_001``) or a full filename.
    """
    from app.config import CLIPS_DIR
    from app.services.media_stream_service import resolve_clip_path, guess_video_mime, build_media_response

    path = resolve_clip_path(video_id, clip_id, CLIPS_DIR)
    content_type = guess_video_mime(path)
    return build_media_response(path, request, content_type)



# ── Unified Result API (P1-A3) ─────────────────


@router.get("/{video_id}/result")
async def get_video_result(video_id: str):
    """Unified result for a video — highlights, clips, report URLs, status.

    Never returns local filesystem paths.
    Status can be: uploaded, pending, running, success, failed, completed_with_errors, not_found.
    """
    from app.services.video_result_service import get_video_result

    result = get_video_result(video_id)
    if result.status == "not_found":
        raise HTTPException(status_code=404, detail="Video not found")
    return result


# ── Report content endpoints ────────────────────


@router.get("/{video_id}/reports/markdown")
async def get_report_markdown(video_id: str):
    """Return the Markdown report content as text/markdown."""
    from app.config import REPORTS_DIR

    md_path = REPORTS_DIR / video_id / "final_report.md"
    if not md_path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    return Response(
        content=md_path.read_text(encoding="utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Type": "text/markdown; charset=utf-8"},
    )


@router.get("/{video_id}/reports/json")
async def get_report_json(video_id: str):
    """Return the JSON report content as application/json."""
    from app.config import REPORTS_DIR
    from fastapi.responses import JSONResponse

    json_path = REPORTS_DIR / video_id / "final_report.json"
    if not json_path.is_file():
        raise HTTPException(status_code=404, detail="Report not found")
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger = logging.getLogger(__name__)
        logger.warning("Corrupted report JSON for %s: %s", video_id, e)
        raise HTTPException(status_code=500, detail="Report file is corrupted")

    # Sanitize: ensure no NaN/Inf
    return JSONResponse(content=_sanitize_json(data))


@router.get("/{video_id}/reports/candidates")
async def get_report_candidates(video_id: str):
    """Return the highlight candidates JSON artifact.

    Contains raw candidate segments with pre-selection scores,
    suitable for offline rescore evaluation.
    """
    from app.config import REPORTS_DIR
    from fastapi.responses import JSONResponse

    candidates_path = REPORTS_DIR / video_id / "highlight_candidates.json"
    if not candidates_path.is_file():
        raise HTTPException(status_code=404, detail="Candidates not found")
    try:
        data = json.loads(candidates_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger = logging.getLogger(__name__)
        logger.warning("Corrupted candidates JSON for %s: %s", video_id, e)
        raise HTTPException(status_code=500, detail="Candidates file is corrupted")

    # Sanitize: ensure no NaN/Inf
    return JSONResponse(content=_sanitize_json(data))


def _sanitize_json(obj):
    """Replace NaN/Inf with null recursively."""
    import math
    if isinstance(obj, dict):
        return {k: _sanitize_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_json(v) for v in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    return obj
