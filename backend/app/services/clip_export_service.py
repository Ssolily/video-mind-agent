"""FFmpeg-based clip exporting with re-encoding and ffprobe validation."""

import logging
import os
import subprocess
from pathlib import Path

from app.config import CLIPS_DIR

logger = logging.getLogger(__name__)


def _ffprobe_duration(path: str) -> float:
    """Return the duration (seconds) of a media file via ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    try:
        return float(result.stdout.strip())
    except (ValueError, TypeError):
        return 0.0


def _ffprobe_has_video(path: str) -> bool:
    """Return True if the file has at least one video stream."""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-select_streams", "v:0",
        "-show_entries", "stream=index",
        "-of", "csv=p=0",
        path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return bool(result.stdout.strip())


def export_clips(
    video_path: str,
    highlights: list[dict],
    video_id: str,
) -> dict:
    """Cut highlight clips from the original video using FFmpeg (re-encode)."""
    video_path = str(Path(video_path).resolve())
    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    out_dir = CLIPS_DIR / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    clip_paths: list[str] = []
    concat_lines: list[str] = []

    for i, h in enumerate(highlights, start=1):
        start = h["start_time"]
        end = h["end_time"]
        clip_name = f"clip_{i:03d}.mp4"
        clip_path = str(out_dir / clip_name)

        if end <= start:
            logger.warning("Skipping clip %s: end_time (%.3f) <= start_time (%.3f)", clip_name, end, start)
            continue

        # Re-encode with libx264 + aac (reliable across all inputs)
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-i", video_path,
            "-to", str(end - start),
            "-map", "0:v:0",
            "-map", "0:a:0?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            clip_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

        # Save FFmpeg logs for debugging
        log_path = out_dir / f"{clip_name}.fflog"
        log_path.write_text(
            f"RETURN CODE: {result.returncode}\n"
            f"STDERR:\n{result.stderr[:2000]}\n",
            encoding="utf-8",
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg failed for clip {clip_name} ({start}s-{end}s): {result.stderr[:300]}"
            )

        # --- ffprobe validation ---
        if not _ffprobe_has_video(clip_path):
            try:
                os.remove(clip_path)
            except OSError:
                pass
            raise RuntimeError(f"Clip {clip_name} has no video stream after FFmpeg export. stderr: {result.stderr[:500]}")

        actual_dur = _ffprobe_duration(clip_path)
        target_dur = end - start
        if actual_dur <= 0:
            try:
                os.remove(clip_path)
            except OSError:
                pass
            raise RuntimeError(f"Clip {clip_name} has zero duration ({actual_dur}s). stderr: {result.stderr[:500]}")

        if abs(actual_dur - target_dur) > 0.5:
            logger.warning("Clip %s duration mismatch: target=%.3fs actual=%.3fs", clip_name, target_dur, actual_dur)

        clip_paths.append(clip_path)
        concat_lines.append(f"file '{clip_path.replace(os.sep, '/')}'")

    # Concatenate all clips into one highlight reel
    highlight_path: str | None = None
    if len(clip_paths) >= 2:
        concat_file = out_dir / "_concat.txt"
        concat_file.write_text("\n".join(concat_lines), encoding="utf-8")
        highlight_path = str(out_dir / "highlight.mp4")
        result = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file), "-c", "copy", highlight_path],
            capture_output=True, text=True, timeout=600,
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg concat failed: {result.stderr[:300]}")
        concat_file.unlink(missing_ok=True)

    return {"clip_paths": clip_paths, "highlight_path": highlight_path}
