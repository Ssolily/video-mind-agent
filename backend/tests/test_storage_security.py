"""Tests for storage security — filename validation, magic bytes, upload limits."""
import io
from pathlib import Path

import pytest
from fastapi import UploadFile

from app.services.storage_service import (
    _validate_filename,
    _detect_extension_from_header,
    _check_magic_bytes,
    save_uploaded_video,
)
from app.config import MAX_UPLOAD_BYTES, RAW_VIDEOS_DIR as _RAW_VIDEOS_DIR


# ── Fake video headers ──────────────────────────────

# Minimal valid MP4 header: 4-byte size + "ftyp" + 4-byte brand + 4-byte version
_MP4_HEADER = (
    b"\x00\x00\x00\x10"   # box size = 16
    b"ftyp"
    b"mp42"
    b"\x00\x00\x00\x00"   # minor version
)

# Minimal AVI header: "RIFF" + 4-byte size + "AVI "
_AVI_HEADER = b"RIFF" + b"\x00\x00\x00\x00" + b"AVI " + b"LIST"

_UNKNOWN_HEADER = b"\x00\x01\x02\x03\x04\x05\x06\x07" + b"\x08\x09\x0a\x0b"


# ── TestValidateFilename ────────────────────────────


class TestValidateFilename:
    def test_allowed_extensions(self):
        for ext in [".mp4", ".MOV", ".avi"]:
            name = f"video{ext}"
            result = _validate_filename(name)
            assert result == name

    def test_path_traversal_stripped(self):
        result = _validate_filename("../../etc/passwd.mp4")
        assert "passwd.mp4" == result
        assert "../" not in result

    def test_disallowed_extension_rejected(self):
        with pytest.raises(Exception):
            _validate_filename("virus.exe")

    def test_none_filename_defaults(self):
        result = _validate_filename(None)
        assert result == "video.mp4"

    def test_empty_extension_rejected(self):
        with pytest.raises(Exception):
            _validate_filename("no_extension")


# ── TestDetectExtensionFromHeader ───────────────────


class TestDetectExtensionFromHeader:
    def test_mp4_header(self):
        assert _detect_extension_from_header(_MP4_HEADER) == ".mp4"

    def test_avi_header(self):
        assert _detect_extension_from_header(_AVI_HEADER) == ".avi"

    def test_unknown_header(self):
        assert _detect_extension_from_header(_UNKNOWN_HEADER) is None

    def test_too_short(self):
        assert _detect_extension_from_header(b"too") is None


# ── TestCheckMagicBytes ─────────────────────────────


class TestCheckMagicBytes:
    async def test_mp4_accepted(self):
        f = UploadFile(filename="test.mp4", file=io.BytesIO(_MP4_HEADER))
        ext = await _check_magic_bytes(f)
        assert ext == ".mp4"

    async def test_avi_accepted(self):
        f = UploadFile(filename="test.avi", file=io.BytesIO(_AVI_HEADER))
        ext = await _check_magic_bytes(f)
        assert ext == ".avi"

    async def test_unknown_rejected(self):
        f = UploadFile(filename="test.mp4", file=io.BytesIO(_UNKNOWN_HEADER))
        with pytest.raises(Exception, match="does not match"):
            await _check_magic_bytes(f)


# ── TestSaveUploadedVideo ───────────────────────────


class TestSaveUploadedVideo:
    @pytest.fixture(autouse=True)
    def _patch_raw_dir(self, tmp_path):
        import app.services.storage_service as svc
        self._orig = svc.RAW_VIDEOS_DIR
        svc.RAW_VIDEOS_DIR = tmp_path / "raw_videos"
        svc.RAW_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        yield
        svc.RAW_VIDEOS_DIR = self._orig

    async def test_upload_saves_to_disk(self):
        content = _MP4_HEADER + b"\x00" * 1000
        f = UploadFile(filename="my_video.MP4", file=io.BytesIO(content))
        result = await save_uploaded_video(f)

        assert result["status"] == "uploaded"
        assert result["filename"] == "my_video.MP4"
        assert result["video_id"]
        assert Path(result["raw_path"]).exists()
        saved = Path(result["raw_path"]).name
        assert saved.startswith(result["video_id"])

    async def test_oversized_file_rejected(self):
        header = _MP4_HEADER
        big = b"x" * (MAX_UPLOAD_BYTES + 1)
        f = UploadFile(filename="big.mp4", file=io.BytesIO(header + big))
        with pytest.raises(Exception, match="too large"):
            await save_uploaded_video(f)

    async def test_wrong_magic_rejected(self):
        f = UploadFile(filename="fake.mp4", file=io.BytesIO(_UNKNOWN_HEADER))
        with pytest.raises(Exception, match="does not match"):
            await save_uploaded_video(f)

    async def test_path_traversal_filename_stored_safely(self):
        content = _MP4_HEADER + b"\x00" * 100
        f = UploadFile(filename="../../evil.mp4", file=io.BytesIO(content))
        result = await save_uploaded_video(f)

        # Filename is sanitised — path components stripped
        assert result["filename"] == "evil.mp4"
        # Saved path is inside raw_videos, not traversed
        saved = Path(result["raw_path"])
        import app.services.storage_service as svc
        assert saved.is_relative_to(svc.RAW_VIDEOS_DIR)
