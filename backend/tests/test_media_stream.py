
"""Tests for media streaming — Range parsing, source video, clip serving, path safety."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import RAW_VIDEOS_DIR, CLIPS_DIR
from app.services.media_stream_service import (
    parse_range_header,
    RangeHeader,
    resolve_video_path,
    resolve_clip_path,
    guess_video_mime,
    ALLOWED_VIDEO_EXTENSIONS,
)


# ── Helpers ─────────────────────────────────────────


def _make_small_video(path: Path, duration: float = 1.0, width: int = 160, height: int = 90) -> Path:
    """Generate a tiny synthetic video with FFmpeg.  Returns the path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration}:size={width}x{height}:rate=1",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-frames:v", str(max(1, int(duration))),
        "-an",
        str(path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=True)
    return path


def _make_clip_entry(video_id: str, clip_id: str, clips_root: Path, duration: float = 1.0) -> Path:
    """Create a clip file in the proper directory structure."""
    clip_dir = clips_root / video_id
    clip_dir.mkdir(parents=True, exist_ok=True)
    clip_name = f"{clip_id}.mp4" if not clip_id.endswith(".mp4") else clip_id
    clip_path = clip_dir / clip_name
    return _make_small_video(clip_path, duration=duration)


# ── A. Range parsing unit tests ─────────────────────


class TestParseRangeHeader:
    def test_no_range(self):
        assert parse_range_header(None, 1000) is None

    def test_range_start_end(self):
        r = parse_range_header("bytes=0-99", 1000)
        assert isinstance(r, RangeHeader)
        assert r.start == 0
        assert r.end == 99
        assert r.length == 100

    def test_range_open_end(self):
        r = parse_range_header("bytes=100-", 1000)
        assert r.start == 100
        assert r.end == 999
        assert r.length == 900

    def test_range_suffix(self):
        r = parse_range_header("bytes=-100", 1000)
        assert r.start == 900
        assert r.end == 999
        assert r.length == 100

    def test_end_beyond_file(self):
        r = parse_range_header("bytes=0-999999", 1000)
        assert r.start == 0
        assert r.end == 999
        assert r.length == 1000

    def test_start_equals_file_size(self):
        with pytest.raises(Exception) as exc:
            parse_range_header("bytes=1000-", 1000)
        assert exc.value.status_code == 416  # type: ignore

    def test_start_greater_than_file_size(self):
        with pytest.raises(Exception) as exc:
            parse_range_header("bytes=2000-3000", 1000)
        assert exc.value.status_code == 416  # type: ignore

    def test_end_less_than_start(self):
        with pytest.raises(Exception) as exc:
            parse_range_header("bytes=100-50", 1000)
        assert exc.value.status_code == 416  # type: ignore

    def test_non_numeric(self):
        with pytest.raises(Exception) as exc:
            parse_range_header("bytes=abc-def", 1000)
        assert exc.value.status_code == 400  # type: ignore

    def test_empty_range_value(self):
        with pytest.raises(Exception) as exc:
            parse_range_header("bytes=", 1000)
        assert exc.value.status_code == 400  # type: ignore

    def test_multi_range(self):
        with pytest.raises(Exception) as exc:
            parse_range_header("bytes=0-10,20-30", 1000)
        assert exc.value.status_code == 400  # type: ignore

    def test_file_size_zero(self):
        with pytest.raises(Exception) as exc:
            parse_range_header("bytes=0-10", 0)
        assert exc.value.status_code == 416  # type: ignore

    def test_content_range_header(self):
        r = RangeHeader(0, 99, 1000)
        assert r.content_range_header() == "bytes 0-99/1000"


# ── B. Source video interface tests ─────────────────


class TestSourceVideoEndpoint:
    """Uses FastAPI TestClient and a temporary directory."""

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        """Point config dirs to a tmp path and create a test video."""
        self.raw_root = tmp_path / "raw_videos"
        self.raw_root.mkdir()

        # Create a real MP4 file
        self.test_video_id = "test_vid_001"
        self.video_path = self.raw_root / f"{self.test_video_id}.mp4"
        _make_small_video(self.video_path)

        # Create another file for isolation test
        self.other_video_id = "other_vid"
        self.other_path = self.raw_root / f"{self.other_video_id}.mp4"
        _make_small_video(self.other_path, duration=0.5)

        monkeypatch.setattr("app.config.RAW_VIDEOS_DIR", self.raw_root)
        monkeypatch.setattr("app.config.RAW_VIDEOS_DIR", self.raw_root)

        from app.main import app
        self.client = TestClient(app)

    def test_full_get_returns_200(self):
        resp = self.client.get(f"/api/v1/videos/{self.test_video_id}/source")
        assert resp.status_code == 200

    def test_content_type_correct(self):
        resp = self.client.get(f"/api/v1/videos/{self.test_video_id}/source")
        assert resp.headers.get("content-type", "").startswith("video/")

    def test_content_length_correct(self):
        resp = self.client.get(f"/api/v1/videos/{self.test_video_id}/source")
        expected = self.video_path.stat().st_size
        assert int(resp.headers["content-length"]) == expected

    def test_accept_ranges_header(self):
        resp = self.client.get(f"/api/v1/videos/{self.test_video_id}/source")
        assert resp.headers.get("accept-ranges") == "bytes"

    def test_range_returns_206(self):
        resp = self.client.get(
            f"/api/v1/videos/{self.test_video_id}/source",
            headers={"Range": "bytes=0-99"},
        )
        assert resp.status_code == 206

    def test_range_body_exact_bytes(self):
        resp = self.client.get(
            f"/api/v1/videos/{self.test_video_id}/source",
            headers={"Range": "bytes=0-99"},
        )
        assert len(resp.content) == 100

    def test_range_content_range_header(self):
        resp = self.client.get(
            f"/api/v1/videos/{self.test_video_id}/source",
            headers={"Range": "bytes=0-99"},
        )
        cr = resp.headers.get("content-range")
        assert cr is not None
        assert cr.startswith("bytes 0-99/")
        file_size = self.video_path.stat().st_size
        assert cr == f"bytes 0-99/{file_size}"

    def test_range_open_ended(self):
        total = self.video_path.stat().st_size
        resp = self.client.get(
            f"/api/v1/videos/{self.test_video_id}/source",
            headers={"Range": "bytes=100-"},
        )
        assert resp.status_code == 206
        assert len(resp.content) == total - 100

    def test_range_suffix(self):
        total = self.video_path.stat().st_size
        resp = self.client.get(
            f"/api/v1/videos/{self.test_video_id}/source",
            headers={"Range": "bytes=-100"},
        )
        assert resp.status_code == 206
        assert len(resp.content) == min(100, total)

    def test_invalid_range_returns_416(self):
        total = self.video_path.stat().st_size
        resp = self.client.get(
            f"/api/v1/videos/{self.test_video_id}/source",
            headers={"Range": f"bytes={total+1000}-{total+2000}"},
        )
        assert resp.status_code == 416

    def test_unknown_video_id_returns_404(self):
        resp = self.client.get("/api/v1/videos/nonexistent_video_id/source")
        assert resp.status_code == 404

    def test_no_absolute_path_in_response(self):
        resp = self.client.get(f"/api/v1/videos/{self.test_video_id}/source")
        body_lower = resp.content.lower()
        assert b"d:\\" not in body_lower
        assert b"c:\\" not in body_lower

    def test_no_absolute_path_in_headers(self):
        resp = self.client.get(f"/api/v1/videos/{self.test_video_id}/source")
        for val in resp.headers.values():
            # Check headers don't contain drive-letter paths
            if val.startswith("D:\\\\") or val.startswith("C:\\\\"):
                pytest.fail(f"Header contains absolute path: {val}")


# ── C. Clip interface tests ─────────────────────────


class TestClipEndpoint:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        self.clips_root = tmp_path / "clips"
        self.clips_root.mkdir()

        self.video_id = "clip_vid"
        self.other_id = "other_vid"

        # Create clips for video_id
        self.clip_001_path = _make_clip_entry(self.video_id, "clip_001", self.clips_root, duration=1.0)
        self.clip_002_path = _make_clip_entry(self.video_id, "clip_002", self.clips_root, duration=0.5)

        # Create clip for another video (isolation test)
        _make_clip_entry(self.other_id, "clip_001", self.clips_root, duration=0.5)

        monkeypatch.setattr("app.config.CLIPS_DIR", self.clips_root)
        monkeypatch.setattr("app.config.CLIPS_DIR", self.clips_root)

        from app.main import app
        self.client = TestClient(app)

    def test_clip_full_get_returns_200(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/clips/clip_001")
        assert resp.status_code == 200

    def test_clip_with_ext_200(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/clips/clip_001.mp4")
        assert resp.status_code == 200

    def test_clip_range_returns_206(self):
        resp = self.client.get(
            f"/api/v1/videos/{self.video_id}/clips/clip_001",
            headers={"Range": "bytes=0-99"},
        )
        assert resp.status_code == 206
        assert len(resp.content) == 100

    def test_unknown_clip_id_returns_404(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/clips/nonexistent")
        assert resp.status_code == 404

    def test_unknown_video_id_returns_404(self):
        resp = self.client.get("/api/v1/videos/no_such_vid/clips/clip_001")
        assert resp.status_code == 404

    def test_cannot_read_other_video_clip(self):
        """clip_001 of other_vid should not be accessible under video_id."""
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/clips/clip_001")
        assert resp.status_code == 200
        # Ensure it's the right one
        data_001 = self.clip_001_path.stat().st_size
        assert len(resp.content) == data_001

    def test_path_traversal_dotdot(self):
        resp = self.client.get(
            f"/api/v1/videos/../{self.other_id}/clips/clip_001",
        )
        assert resp.status_code == 404

    def test_path_traversal_backslash(self):
        resp = self.client.get(
            f"/api/v1/videos/{self.video_id}/clips/..\\..\\etc\\passwd",
        )
        assert resp.status_code == 404

    def test_windows_absolute_path(self):
        resp = self.client.get(
            f"/api/v1/videos/{self.video_id}/clips/C:\\\\Windows\\\\win.ini",
        )
        assert resp.status_code == 404

    def test_url_encoded_traversal(self):
        resp = self.client.get(
            f"/api/v1/videos/{self.video_id}/clips/%2e%2e%2fsecret",
        )
        assert resp.status_code == 404

    def test_no_absolute_path_in_response(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/clips/clip_001")
        assert b"D:\\\\" not in resp.content
        assert b"C:\\\\" not in resp.content

    def test_content_type_correct(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/clips/clip_001")
        assert resp.headers.get("content-type", "").startswith("video/")

    def test_content_length_correct(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/clips/clip_001")
        expected = self.clip_001_path.stat().st_size
        assert int(resp.headers["content-length"]) == expected


# ── D. Resolver unit tests ──────────────────────────


class TestResolveVideoPath:
    def test_resolve_finds_mp4(self, tmp_path):
        raw = tmp_path / "raw"
        raw.mkdir()
        (raw / "abc.mp4").write_text("fake mp4")
        path = resolve_video_path("abc", raw)
        assert path.name == "abc.mp4"

    def test_resolve_not_found(self, tmp_path):
        raw = tmp_path / "raw"
        raw.mkdir()
        with pytest.raises(Exception) as exc:
            resolve_video_path("nonexistent", raw)
        assert exc.value.status_code == 404

    def test_traversal_in_id(self, tmp_path):
        raw = tmp_path / "raw"
        raw.mkdir()
        with pytest.raises(Exception) as exc:
            resolve_video_path("../evil", raw)
        assert exc.value.status_code == 404

    def test_absolute_path_in_id(self, tmp_path):
        raw = tmp_path / "raw"
        raw.mkdir()
        with pytest.raises(Exception) as exc:
            resolve_video_path("C:\\\\Windows\\\\win.ini", raw)
        assert exc.value.status_code == 404


class TestResolveClipPath:
    def test_resolve_by_short_id(self, tmp_path):
        clips = tmp_path / "clips"
        _make_clip_entry("vid1", "clip_001", clips)
        path = resolve_clip_path("vid1", "clip_001", clips)
        assert path.name == "clip_001.mp4"

    def test_resolve_by_full_name(self, tmp_path):
        clips = tmp_path / "clips"
        _make_clip_entry("vid1", "clip_001.mp4", clips)
        path = resolve_clip_path("vid1", "clip_001.mp4", clips)
        assert path.name == "clip_001.mp4"

    def test_unknown_clip(self, tmp_path):
        clips = tmp_path / "clips"
        clips.mkdir()
        with pytest.raises(Exception) as exc:
            resolve_clip_path("vid1", "nonexistent", clips)
        assert exc.value.status_code == 404

    def test_traversal_clip_id(self, tmp_path):
        clips = tmp_path / "clips"
        clips.mkdir()
        with pytest.raises(Exception) as exc:
            resolve_clip_path("vid1", "../other", clips)
        assert exc.value.status_code == 404

    def test_other_video_isolation(self, tmp_path):
        clips = tmp_path / "clips"
        _make_clip_entry("vid_a", "clip_001", clips)
        with pytest.raises(Exception) as exc:
            resolve_clip_path("vid_b", "clip_001", clips)
        assert exc.value.status_code == 404


# ── E. MIME type tests ──────────────────────────────


class TestGuessVideoMime:
    def test_mp4(self):
        assert guess_video_mime(Path("test.mp4")) == "video/mp4"

    def test_mov(self):
        assert guess_video_mime(Path("test.mov")) == "video/quicktime"

    def test_webm(self):
        assert guess_video_mime(Path("test.webm")) == "video/webm"

    def test_unknown_ext(self):
        mime = guess_video_mime(Path("test.xyz"))
        assert mime is not None and isinstance(mime, str) and len(mime) > 0


# ── F. Regression tests ─────────────────────────────


def test_existing_upload_still_works():
    """Quick check that the upload route is still importable (routed at app level)."""
    from app.api.video_api import router
    routes = [r.path for r in router.routes]
    assert "/videos/upload" in routes
    assert "/videos/{video_id}/source" in routes
    assert "/videos/{video_id}/clips/{clip_id}" in routes
