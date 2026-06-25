"""Media streaming service — Range parsing, safe path resolution, and HTTP media response.

Provides middleware-level helpers for serving source videos and exported clips
over HTTP with proper Range (206 Partial Content) support.
"""

import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import Request, HTTPException
from fastapi.responses import StreamingResponse, Response


# ── Allowed video extensions ────────────────────────

ALLOWED_VIDEO_EXTENSIONS: set[str] = {
    ".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v",
}

MIME_OVERRIDES: dict[str, str] = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
    ".avi": "video/x-msvideo",
    ".m4v": "video/mp4",
}


# ── Content-Type ────────────────────────────────────


def guess_video_mime(path: Path) -> str:
    """Return the Content-Type for a video file, preferring explicit overrides."""
    ext = path.suffix.lower()
    if ext in MIME_OVERRIDES:
        return MIME_OVERRIDES[ext]
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


# ── Safe path resolution (source video) ────────────


def resolve_video_path(video_id: str, raw_videos_dir: Path) -> Path:
    """Resolve a source video by video_id, trying allowed extensions.

    Returns a resolved, verified path or raises HTTPException(404).
    """
    _reject_path_traversal(video_id)

    for ext in sorted(ALLOWED_VIDEO_EXTENSIONS, reverse=True):
        candidate = (raw_videos_dir / f"{video_id}{ext}").resolve()
        try:
            _check_safe_file(candidate, raw_videos_dir)
            return candidate
        except HTTPException:
            continue
    raise HTTPException(status_code=404, detail="Video not found")


def resolve_clip_path(video_id: str, clip_id: str, clips_dir: Path) -> Path:
    """Resolve a clip by video_id + clip_id.

    clip_id can be a short ID (e.g. "clip_001") or a full filename ("clip_001.mp4").
    Returns a resolved, verified path or raises HTTPException(404).
    """
    _reject_path_traversal(video_id)
    _reject_path_traversal(clip_id)

    video_clip_dir = clips_dir / video_id
    resolved_video_clip_dir = video_clip_dir.resolve()

    # Determine filename
    clip_filename = clip_id if clip_id.endswith(".mp4") else f"{clip_id}.mp4"
    candidate = (video_clip_dir / clip_filename).resolve()

    # Must be inside the video_id-specific clip dir
    if not candidate.is_relative_to(resolved_video_clip_dir):
        raise HTTPException(status_code=404, detail="Clip not found")
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Clip not found")
    return candidate


# ── Path security helpers ───────────────────────────


def _reject_path_traversal(name: str) -> None:
    """Reject path-traversal patterns in logical identifiers."""
    if not name:
        raise HTTPException(status_code=404, detail="Not found")
    for pat in ("..", "/", "\\", ":", "%"):
        if pat in name:
            raise HTTPException(status_code=404, detail="Not found")


def _check_safe_file(resolved: Path, allowed_root: Path) -> None:
    """Verify *resolved* is a regular file within *allowed_root*."""
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Not found")
    if not resolved.is_relative_to(allowed_root.resolve()):
        raise HTTPException(status_code=404, detail="Not found")


# ── Range parsing ───────────────────────────────────


class RangeHeader:
    """Parsed HTTP Range header for a single ``bytes`` range."""

    def __init__(self, start: int, end: int, file_size: int) -> None:
        self.start = start
        self.end = end
        self.file_size = file_size

    @property
    def length(self) -> int:
        return self.end - self.start + 1

    def content_range_header(self) -> str:
        return f"bytes {self.start}-{self.end}/{self.file_size}"


def parse_range_header(range_header: Optional[str], file_size: int) -> Optional[RangeHeader]:
    """Parse a single ``bytes`` Range header.

    Returns *None* when the header is absent.
    Raises ``HTTPException(416)`` if the range is not satisfiable.
    Raises ``HTTPException(400)`` for multi-range requests.

    Supported forms: ``bytes=0-99``, ``bytes=100-``, ``bytes=-100``.
    """
    if range_header is None:
        return None

    if file_size == 0:
        raise HTTPException(status_code=416, detail="Range Not Satisfiable")

    if "," in range_header:
        raise HTTPException(
            status_code=400,
            detail="Multi-range requests are not supported",
        )

    if not range_header.startswith("bytes="):
        raise HTTPException(status_code=400, detail="Invalid Range header")

    range_value = range_header[6:].strip()
    if not range_value:
        raise HTTPException(status_code=400, detail="Empty Range value")

    try:
        if range_value.startswith("-"):
            suffix_length = int(range_value[1:])
            if suffix_length <= 0:
                raise HTTPException(status_code=416, detail="Range Not Satisfiable")
            start = max(0, file_size - suffix_length)
            end = file_size - 1
        elif "-" in range_value:
            parts = range_value.split("-", 1)
            start_str, end_str = parts[0], parts[1]
            start = int(start_str) if start_str else 0
            if end_str:
                end = int(end_str)
                if end < start:
                    raise HTTPException(status_code=416, detail="Range Not Satisfiable")
            else:
                end = file_size - 1
        else:
            raise HTTPException(status_code=400, detail="Invalid Range format")

        start = max(0, start)
        end = min(end, file_size - 1)

        if start >= file_size:
            raise HTTPException(
                status_code=416,
                detail="Range Not Satisfiable",
                headers={"Content-Range": f"bytes */{file_size}"},
            )
        if end < 0 or start > end:
            raise HTTPException(status_code=416, detail="Range Not Satisfiable")

        return RangeHeader(start=start, end=end, file_size=file_size)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Range header")


# ── Streaming response builder ─────────────────────


def build_media_response(path: Path, request: Request, content_type: str) -> Response:
    """Build a 200 or 206 StreamingResponse for a media file.

    Never loads the entire file into memory; uses 64 KB chunk streaming.
    """
    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    parsed = parse_range_header(range_header, file_size)

    if parsed is None:
        return _stream_full(path, content_type, file_size)
    else:
        return _stream_partial(path, content_type, parsed)


def _stream_full(path: Path, content_type: str, file_size: int) -> Response:
    """200 OK — stream entire file."""

    async def _iterfile():
        with open(path, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        _iterfile(),
        status_code=200,
        media_type=content_type,
        headers={
            "Content-Length": str(file_size),
            "Accept-Ranges": "bytes",
        },
    )


def _stream_partial(path: Path, content_type: str, r: RangeHeader) -> Response:
    """206 Partial Content — stream a byte range."""

    async def _iterrange():
        with open(path, "rb") as f:
            f.seek(r.start)
            remaining = r.length
            while remaining > 0:
                chunk_size = min(remaining, 65536)
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
                remaining -= len(chunk)

    return StreamingResponse(
        _iterrange(),
        status_code=206,
        media_type=content_type,
        headers={
            "Content-Length": str(r.length),
            "Content-Range": r.content_range_header(),
            "Accept-Ranges": "bytes",
        },
    )
