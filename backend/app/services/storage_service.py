import json
import uuid
from pathlib import Path

from fastapi import UploadFile, HTTPException

from app.config import RAW_VIDEOS_DIR, DATA_DIR, MAX_UPLOAD_BYTES
from app.services.video_metadata_service import get_video_metadata

def check_disk_space() -> None:
    """Check if free disk space is above MIN_FREE_DISK_GB threshold.
    Raises HTTPException 507 if insufficient."""
    import shutil
    from app.config import DATA_DIR, MIN_FREE_DISK_GB
    try:
        usage = shutil.disk_usage(str(DATA_DIR))
        free_gb = usage.free / (1024 ** 3)
        if free_gb < MIN_FREE_DISK_GB:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=507,
                detail=f"Insufficient disk space: {free_gb:.1f} GB free (minimum: {MIN_FREE_DISK_GB} GB). Please clean storage and retry.",
            )
    except HTTPException:
        raise
    except Exception:
        pass  # If we cannot check, allow the request


ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi"}

# ISO BMFF (MP4/MOV) magic: bytes 4-7 == b"ftyp"
# AVI magic: bytes 0-3 == b"RIFF" and bytes 8-11 == b"AVI "
_MAGIC_CHECKS: list[tuple[bytes, str]] = [
    (b"ftyp", ".mp4"),   # MP4/MOV — check offset 4 after reading 12 bytes
]

_AVI_MAGIC_HEAD = b"RIFF"
_AVI_MAGIC_TAIL = b"AVI "

_MIN_HEADER_SIZE = 12  # bytes needed for magic check

_REGISTRY_PATH = DATA_DIR / "video_registry.json"


# ── Registry helpers (JSON-backed) ───────────────────


def _load_registry() -> dict:
    if _REGISTRY_PATH.is_file():
        return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    return {}


def _save_registry(registry: dict) -> None:
    _REGISTRY_PATH.write_text(json.dumps(registry, indent=2), encoding="utf-8")


def register_video(video_id: str, raw_path: str, filename: str) -> None:
    registry = _load_registry()
    registry[video_id] = {"raw_path": raw_path, "filename": filename}
    _save_registry(registry)


def get_video_path(video_id: str) -> str | None:
    registry = _load_registry()
    entry = registry.get(video_id)
    return entry["raw_path"] if entry else None


# ── Magic bytes check ────────────────────────────────


def _detect_extension_from_header(header: bytes) -> str | None:
    """Inspect the first bytes of a file and return a safe extension if it looks
    like a valid MP4, MOV, or AVI."""

    if len(header) < _MIN_HEADER_SIZE:
        return None

    # AVI: starts with "RIFF" ... "AVI "
    if header[:4] == _AVI_MAGIC_HEAD and header[8:12] == _AVI_MAGIC_TAIL:
        return ".avi"

    # MP4 / MOV: bytes 4-7 are "ftyp"
    if header[4:8] == _MAGIC_CHECKS[0][0]:
        return ".mp4"  # safe default for both mp4 and mov

    return None


# ── Validation ──────────────────────────────────────


def _validate_filename(filename: str | None) -> str:
    """Validate and sanitise the uploaded filename.

    Returns the original filename for display purposes.  Raises HTTPException
    if the extension is not allowed.
    """
    safe_name = Path((filename or "video.mp4").strip()).name  # strip path
    ext = Path(safe_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type {ext!r}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )
    return safe_name


async def _check_magic_bytes(file: UploadFile) -> str:
    """Read the file header and verify magic bytes.  Returns the detected extension."""
    header = await file.read(_MIN_HEADER_SIZE)
    await file.seek(0)  # rewind so the main read loop gets the full stream

    detected = _detect_extension_from_header(header)
    if detected is None:
        raise HTTPException(
            status_code=400,
            detail="File header does not match a supported video format (MP4, MOV, AVI).",
        )
    return detected


# ── Upload ──────────────────────────────────────────


async def save_uploaded_video(file: UploadFile) -> dict:
    # Check disk space before saving
    check_disk_space()
    """Save an uploaded video to disk, read metadata, and return combined result.

    Returns
    -------
    dict with keys: video_id, filename, raw_path, status, metadata
    """
    # 1. Validate extension from original filename
    safe_original_name = _validate_filename(file.filename)

    # 2. Magic bytes check — also determines the safe extension for storage
    safe_ext = await _check_magic_bytes(file)

    # 3. Generate storage identity
    video_id = uuid.uuid4().hex[:12]
    dest_name = f"{video_id}{safe_ext}"
    dest_path = RAW_VIDEOS_DIR / dest_name

    try:
        RAW_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
        bytes_written = 0
        with open(dest_path, "wb") as dst:
            while True:
                chunk = await file.read(64 * 1024)  # 64 KB chunks
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_BYTES:
                    dst.close()
                    dest_path.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Max {MAX_UPLOAD_BYTES // (1024*1024)} MB.",
                    )
                dst.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {exc}") from exc

    # Register in the video registry (store original filename for display)
    register_video(video_id, str(dest_path), safe_original_name)

    # Record upload in storage manifest
    try:
        from app.services.storage_manifest_service import add_file
        add_file(video_id, "upload", dest_path)
    except Exception:
        pass

    # Read video metadata
    try:
        video_meta = get_video_metadata(str(dest_path))
    except Exception:
        video_meta = None

    return {
        "video_id": video_id,
        "filename": safe_original_name,
        "raw_path": str(dest_path),
        "status": "uploaded",
        "metadata": video_meta,
    }
