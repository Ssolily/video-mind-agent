import json
from pathlib import Path

import os
import logging

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

from app.config import REPORTS_DIR


# Default model size – can be overridden via env var
_MODEL_SIZE = "base"  # tiny / base / small / medium / large-v3
_HF_ENDPOINT = "https://hf-mirror.com"
_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        from app.config import WHISPER_DEVICE, WHISPER_COMPUTE_TYPE
        os.environ.setdefault("HF_ENDPOINT", _HF_ENDPOINT)
        logger.info("Initialising Whisper model device=%s compute_type=%s size=%s", WHISPER_DEVICE, WHISPER_COMPUTE_TYPE, _MODEL_SIZE)
        _model = WhisperModel(_MODEL_SIZE, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
    return _model


def transcribe_audio(audio_path: str) -> list[dict]:
    """Transcribe a WAV file and return segments.

    Each segment: {start, end, text}
    start/end in seconds.
    """
    audio_path = str(Path(audio_path).resolve())
    model = _get_model()

    segments, info = model.transcribe(audio_path, beam_size=5, language=None)

    result: list[dict] = []
    for seg in segments:
        result.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
        })

    return result


def save_subtitles(video_id: str, segments: list[dict]) -> dict:
    """Save subtitles as JSON and SRT, return paths."""
    report_dir = REPORTS_DIR / video_id
    report_dir.mkdir(parents=True, exist_ok=True)

    # JSON
    json_path = report_dir / "subtitles.json"
    json_path.write_text(json.dumps(segments, indent=2, ensure_ascii=False), encoding="utf-8")

    # SRT
    srt_path = report_dir / "subtitles.srt"
    srt_lines: list[str] = []
    for i, seg in enumerate(segments, start=1):
        srt_lines.append(str(i))
        srt_lines.append(f"{_fmt_srt(seg['start'])} --> {_fmt_srt(seg['end'])}")
        srt_lines.append(seg["text"])
        srt_lines.append("")
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

    return {
        "json_path": str(json_path),
        "srt_path": str(srt_path),
    }


def _fmt_srt(seconds: float) -> str:
    """Format seconds as SRT timestamp: HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def has_audio_stream(video_path: str) -> bool:
    """Quick check whether a video file has an audio track."""
    import subprocess
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0",
         video_path],
        capture_output=True, text=True, timeout=30,
    )
    return bool(probe.stdout.strip())
