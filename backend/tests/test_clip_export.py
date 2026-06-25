"""Tests for clip_export_service — generates short synthetic videos with FFmpeg.

No large binary files are committed.  Each test creates a small test video
(1-2 seconds, 1-2 frames) on the fly.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

from app.services.clip_export_service import export_clips, _ffprobe_duration, _ffprobe_has_video


# ── Helpers ─────────────────────────────────────


def _make_synthetic_video(path: str, duration_s: float = 2.0, has_audio: bool = False) -> str:
    """Use FFmpeg to create a short synthetic test video.

    Parameters
    ----------
    path : str
        Output path for the video.
    duration_s : float
        Duration in seconds.
    has_audio : bool
        If True, include a synthetic audio tone.

    Returns
    -------
    str
        Absolute path to the created video.
    """
    path = os.path.abspath(path)
    out_dir = os.path.dirname(path)
    os.makedirs(out_dir, exist_ok=True)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=blue:size=320x240:duration={duration_s}:rate=10",
    ]
    if has_audio:
        cmd += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={duration_s}"]
        cmd += ["-c:v", "libx264", "-c:a", "aac", "-shortest", path]
    else:
        cmd += ["-c:v", "libx264", "-an", path]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg synth failed: {result.stderr[:300]}")
    return path


# ── Fixture ──────────────────────────────────────

@pytest.fixture
def synth_video(tmp_path: Path) -> str:
    """Create a 2-second 10fps blue video (no audio)."""
    return _make_synthetic_video(str(tmp_path / "source.mp4"), duration_s=2.0, has_audio=False)


@pytest.fixture
def synth_video_with_audio(tmp_path: Path) -> str:
    """Create a 2-second 10fps blue video (with audio tone)."""
    return _make_synthetic_video(str(tmp_path / "source_audio.mp4"), duration_s=2.0, has_audio=True)


# ── Unit tests: ffprobe helpers ──────────────────

class TestFfprobeHelpers:
    def test_duration_of_synth(self, synth_video):
        dur = _ffprobe_duration(synth_video)
        assert dur > 0
        assert abs(dur - 2.0) < 0.3  # allow some encoding variance

    def test_has_video(self, synth_video):
        assert _ffprobe_has_video(synth_video) is True

    def test_has_video_nonexistent(self):
        assert _ffprobe_has_video("/nonexistent/file.mp4") is False

    def test_duration_nonexistent(self):
        assert _ffprobe_duration("/nonexistent/file.mp4") == 0.0


# ── Integration tests: export_clips ──────────────

class TestExportClips:
    def _make_highlights(self, *segments: tuple[float, float]) -> list[dict]:
        return [{"start_time": s, "end_time": e} for s, e in segments]

    def _export(self, video_path: str, highlights: list[dict], video_id: str) -> dict:
        return export_clips(video_path, highlights, video_id)

    # 1. Full video
    def test_export_full_video(self, synth_video, tmp_path):
        result = self._export(synth_video, self._make_highlights((0.0, 2.0)), "test_full")
        assert len(result["clip_paths"]) == 1
        clip = result["clip_paths"][0]
        assert os.path.isfile(clip)
        assert _ffprobe_has_video(clip)
        dur = _ffprobe_duration(clip)
        assert abs(dur - 2.0) < 0.5

    # 2. Middle segment
    def test_export_middle_segment(self, synth_video, tmp_path):
        result = self._export(synth_video, self._make_highlights((0.5, 1.5)), "test_mid")
        assert len(result["clip_paths"]) == 1
        dur = _ffprobe_duration(result["clip_paths"][0])
        assert abs(dur - 1.0) < 0.5

    # 3. From 0 seconds
    def test_export_from_zero(self, synth_video, tmp_path):
        result = self._export(synth_video, self._make_highlights((0.0, 1.0)), "test_zero")
        assert len(result["clip_paths"]) == 1
        dur = _ffprobe_duration(result["clip_paths"][0])
        assert abs(dur - 1.0) < 0.5

    # 4. No audio (synth_video has no audio)
    def test_export_no_audio(self, synth_video, tmp_path):
        result = self._export(synth_video, self._make_highlights((0.0, 1.5)), "test_no_audio")
        clip = result["clip_paths"][0]
        assert _ffprobe_has_video(clip)
        dur = _ffprobe_duration(clip)
        assert abs(dur - 1.5) < 0.5

    # 5. With audio
    def test_export_with_audio(self, synth_video_with_audio, tmp_path):
        result = self._export(synth_video_with_audio, self._make_highlights((0.0, 1.0)), "test_audio")
        clip = result["clip_paths"][0]
        assert _ffprobe_has_video(clip)
        dur = _ffprobe_duration(clip)
        assert abs(dur - 1.0) < 0.5

    # 6. Invalid time range (end <= start)
    def test_export_invalid_range(self, synth_video, tmp_path):
        result = self._export(
            synth_video,
            self._make_highlights((1.0, 0.5)),  # start > end
            "test_invalid",
        )
        # Clip should be skipped
        assert result["clip_paths"] == []

    # 7. Non-existent source
    def test_export_nonexistent_source(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            self._export("/nonexistent/video.mp4", self._make_highlights((0.0, 1.0)), "test_bad_src")

    # 8. Multiple segments
    def test_export_multiple_segments(self, synth_video, tmp_path):
        highlights = self._make_highlights((0.0, 0.5), (0.5, 1.0), (1.0, 1.5))
        result = self._export(synth_video, highlights, "test_multi")
        assert len(result["clip_paths"]) == 3
        for clip in result["clip_paths"]:
            assert _ffprobe_has_video(clip)
