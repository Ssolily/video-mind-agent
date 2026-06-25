import subprocess
from pathlib import Path

from app.config import AUDIO_DIR


def _last_stderr_lines(stderr: str, n: int) -> str:
    """Skip FFmpeg banner and return last meaningful error lines."""
    lines = stderr.strip().split("\n")
    # Skip banner lines (start with "ffmpeg version" or "  built with" or "  configuration")
    meaningful = [l for l in lines if not l.startswith(("ffmpeg version", "  built with", "  configuration", "  lib"))]
    if not meaningful:
        meaningful = lines
    return "\n".join(meaningful[-10:])[-n:]


def extract_audio(video_path: str, video_id: str) -> str | None:
    """Extract audio from video to data/audio/{video_id}.wav using FFmpeg.

    Returns the path to the extracted WAV file, or None if the video
    has no audio track.
    """
    video_path = str(Path(video_path).resolve())
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    out_path = str(AUDIO_DIR / f"{video_id}.wav")

    # Probe audio streams first
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0",
         video_path],
        capture_output=True, text=True, timeout=30,
    )
    if not probe.stdout.strip():
        return None  # no audio stream

    # Extract as 16kHz mono WAV
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", video_path,
         "-vn",                # no video
         "-acodec", "pcm_s16le",
         "-ar", "16000",       # 16 kHz (standard for Whisper)
         "-ac", "1",           # mono
         out_path],
        capture_output=True, text=True, timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg audio extraction failed: {_last_stderr_lines(result.stderr, 400)}")

    return out_path
