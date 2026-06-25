"""Per-task storage manifest: tracks generated files with relative paths.

Manifest files are stored under ``data/task_manifests/{task_id}.json``.
All paths are relative to DATA_DIR. Never stores Windows absolute paths.
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import DATA_DIR

MANIFESTS_DIR = DATA_DIR / "task_manifests"


def _ensure_dir() -> None:
    MANIFESTS_DIR.mkdir(parents=True, exist_ok=True)


def _manifest_path(task_id: str) -> Path:
    return MANIFESTS_DIR / f"{task_id}.json"


def _safe_relative_path(path: str | Path) -> str:
    """Convert a path to a relative path under DATA_DIR, or return as-is if already relative."""
    p = Path(path)
    try:
        rel = p.relative_to(DATA_DIR)
        return rel.as_posix()
    except ValueError:
        # Outside DATA_DIR
        sp = str(p)
        # Normalize backslashes to forward slashes
        sp = sp.replace("\\", "/")
        # If it has a drive letter pattern like C:, it is absolute
        import re
        if re.match(r"^[A-Za-z]:", sp):
            raise ValueError(f"Absolute path not allowed in manifest: {sp}")
        # Strip leading / or ./
        return sp.lstrip("/").lstrip("./")


def _validate_path(relative_path: str) -> str:
    """Validate a relative path string, reject path traversal."""
    p = Path(relative_path)
    if ".." in p.parts:
        raise ValueError(f"Path traversal detected: {relative_path}")
    return relative_path


def create_manifest(task_id: str, video_id: str, status: str = "pending") -> dict:
    """Create a new storage manifest for a task."""
    _ensure_dir()
    now = datetime.now(timezone.utc).isoformat()
    manifest = {
        "task_id": task_id,
        "video_id": video_id,
        "status": status,
        "files": [],
        "total_size_bytes": 0,
        "created_at": now,
        "updated_at": now,
    }
    _manifest_path(task_id).write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return manifest


def load_manifest(task_id: str) -> Optional[dict]:
    """Load a manifest for a task. Returns None if not found."""
    p = _manifest_path(task_id)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_manifest(manifest: dict) -> None:
    """Persist a manifest dict to disk."""
    _ensure_dir()
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    task_id = manifest.get("task_id", "")
    if not task_id:
        raise ValueError("manifest missing task_id")
    _manifest_path(task_id).write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")


def add_file(task_id: str, file_type: str, file_path: str | Path, size_bytes: Optional[int] = None) -> dict:
    """Record a generated file in the manifest."""
    manifest = load_manifest(task_id) or create_manifest(task_id, video_id="")
    rel = _safe_relative_path(file_path)
    _validate_path(rel)
    if size_bytes is None:
        p = Path(file_path)
        size_bytes = p.stat().st_size if p.is_file() else 0
    now = datetime.now(timezone.utc).isoformat()
    file_entry = {
        "type": file_type,
        "relative_path": rel,
        "size_bytes": size_bytes,
        "created_at": now,
        "exists": True,
    }
    manifest["files"].append(file_entry)
    manifest["total_size_bytes"] = sum(f.get("size_bytes", 0) for f in manifest["files"] if f.get("exists"))
    save_manifest(manifest)
    return manifest


def update_status(task_id: str, status: str) -> Optional[dict]:
    """Update the task status in the manifest."""
    manifest = load_manifest(task_id)
    if manifest is None:
        return None
    manifest["status"] = status
    save_manifest(manifest)
    return manifest


def list_manifests() -> list[dict]:
    """Return all manifests, newest first."""
    _ensure_dir()
    result = []
    for p in sorted(MANIFESTS_DIR.glob("*.json"), reverse=True):
        try:
            result.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return result


def refresh_file_status(task_id: str) -> Optional[dict]:
    """Update exists and size_bytes for all files in the manifest."""
    manifest = load_manifest(task_id)
    if manifest is None:
        return None
    total = 0
    for entry in manifest.get("files", []):
        rel = entry.get("relative_path", "")
        full = DATA_DIR / rel
        exists = full.is_file()
        entry["exists"] = exists
        if exists:
            try:
                entry["size_bytes"] = full.stat().st_size
            except OSError:
                pass
        else:
            entry["size_bytes"] = 0
        if exists:
            total += entry.get("size_bytes", 0)
    manifest["total_size_bytes"] = total
    save_manifest(manifest)
    return manifest


def compute_total_size(task_id: str) -> int:
    """Return total size in bytes for existing files."""
    manifest = refresh_file_status(task_id)
    if manifest is None:
        return 0
    return manifest.get("total_size_bytes", 0)


def scan_task_directory(task_id: str, video_id: str) -> dict:
    """Scan the data directory for files belonging to a task and update the manifest."""
    manifest = load_manifest(task_id)
    if manifest is None:
        manifest = create_manifest(task_id, video_id, status="unknown")
    # Scan clips
    clips_dir = DATA_DIR / "clips" / video_id
    if clips_dir.is_dir():
        for f in clips_dir.iterdir():
            if f.is_file():
                rel = _safe_relative_path(f)
                if not any(e.get("relative_path") == rel for e in manifest["files"]):
                    manifest["files"].append({
                        "type": "clip",
                        "relative_path": rel,
                        "size_bytes": f.stat().st_size,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "exists": True,
                    })
    # Scan reports
    reports_dir = DATA_DIR / "reports" / video_id
    if reports_dir.is_dir():
        for f in reports_dir.iterdir():
            if f.is_file():
                rel = _safe_relative_path(f)
                if not any(e.get("relative_path") == rel for e in manifest["files"]):
                    manifest["files"].append({
                        "type": "report",
                        "relative_path": rel,
                        "size_bytes": f.stat().st_size,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "exists": True,
                    })
    # Scan task log
    log_path = DATA_DIR / "task_logs" / f"{task_id}.log"
    if log_path.is_file():
        rel = _safe_relative_path(log_path)
        if not any(e.get("relative_path") == rel for e in manifest["files"]):
            manifest["files"].append({
                "type": "log",
                "relative_path": rel,
                "size_bytes": log_path.stat().st_size,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "exists": True,
            })
    manifest["total_size_bytes"] = sum(f.get("size_bytes", 0) for f in manifest["files"] if f.get("exists"))
    save_manifest(manifest)
    return manifest


def get_active_manifest_ids() -> set[str]:
    """Return set of task_ids from manifests with active (non-terminal) status."""
    active = set()
    for m in list_manifests():
        status = m.get("status", "")
        task_id = m.get("task_id", "")
        if status in ("pending", "queued", "running", "unknown"):
            active.add(task_id)
            active.add(m.get("video_id", ""))
    return active
