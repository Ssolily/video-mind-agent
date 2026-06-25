"""Clean up storage: old logs, failed task files, orphaned files."""
import argparse
import json
import shutil
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path


def _get_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _format_size(b: int) -> str:
    return f"{b / (1024**3):.2f} GB" if b > 1024**3 else f"{b / (1024**2):.2f} MB" if b > 1024**2 else f"{b / 1024:.1f} KB"


def _get_data_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "data"


def _active_task_ids() -> set[str]:
    """Get active task IDs from manifests, fallback to task_store."""
    try:
        from app.services.storage_manifest_service import get_active_manifest_ids
        active = get_active_manifest_ids()
        if active:
            return active
    except Exception:
        pass
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
    try:
        from app.services.task_store import list_task_records
        active = set()
        for s in ("running", "queued", "pending"):
            for t in list_task_records(status_filter=s):
                active.add(t["video_id"])
                active.add(t["task_id"])
        return active
    except Exception:
        return set()


def main():
    parser = argparse.ArgumentParser(description="Clean up storage")
    parser.add_argument("--dry-run", action="store_true", help="Preview without deleting")
    parser.add_argument("--older-than-days", type=float, default=30, help="Delete files older than N days")
    parser.add_argument("--delete-failed", action="store_true", help="Delete failed task clips/reports")
    parser.add_argument("--delete-orphaned", action="store_true", help="Delete files with no matching task")
    parser.add_argument("--delete-logs", action="store_true", help="Delete old task log files")
    parser.add_argument("--max-total-gb", type=float, default=0, help="Max total storage before cleanup")
    args = parser.parse_args()

    data_dir = _get_data_dir()
    now = time.time()
    cutoff_sec = args.older_than_days * 86400
    active_ids = _active_task_ids() if (args.delete_orphaned or args.max_total_gb) else set()
    total_freed = 0
    file_count = 0

    cli = "DRY RUN" if args.dry_run else "CLEANUP"
    print(f"=== {cli} ===")
    print(f"  Data dir: {data_dir}")
    print(f"  Older than: {args.older_than_days} day(s)")

    if args.max_total_gb > 0:
        total_size = _get_size(data_dir)
        total_gb = total_size / (1024**3)
        print(f"  Current total: {total_gb:.2f} GB (limit: {args.max_total_gb} GB)")

    # Task logs
    if args.delete_logs:
        log_dir = data_dir / "task_logs"
        if log_dir.is_dir():
            for f in log_dir.iterdir():
                if f.is_file() and now - f.stat().st_mtime > cutoff_sec:
                    sz = f.stat().st_size
                    total_freed += sz
                    file_count += 1
                    if not args.dry_run:
                        f.unlink()
                    print(f"  {'[DRY]' if args.dry_run else ''} Remove log: {f.name} ({_format_size(sz)})")

    # Load manifests for manifest-based cleanup
    manifest_files = 0
    orphaned_files = 0
    skipped_completed = 0
    skipped_active = 0

    def _load_manifests() -> dict:
        """Load all manifests keyed by task_id."""
        m_dir = data_dir / "task_manifests"
        result = {}
        if m_dir.is_dir():
            for p in m_dir.glob("*.json"):
                try:
                    m = json.loads(p.read_text(encoding="utf-8"))
                    result[m["task_id"]] = m
                except (json.JSONDecodeError, OSError, KeyError):
                    pass
        return result

    manifests = _load_manifests()
    manifest_files = len(manifests)

    # Failed task clips
    if args.delete_failed:
        clips_dir = data_dir / "clips"
        if clips_dir.is_dir():
            for vdir in clips_dir.iterdir():
                if vdir.is_dir():
                    for f in vdir.iterdir():
                        if f.is_file() and now - f.stat().st_mtime > cutoff_sec:
                            vid = vdir.name
                            # Check manifest
                            skip = False
                            for mid, m in manifests.items():
                                if m.get("video_id") == vid:
                                    if m.get("status") in ("completed", "completed_with_errors"):
                                        skipped_completed += 1
                                        skip = True
                                    elif m.get("status") in ("running", "queued", "pending"):
                                        skipped_active += 1
                                        skip = True
                                    break
                            if skip:
                                continue
                            if vid in active_ids:
                                skipped_active += 1
                                continue
                            sz = f.stat().st_size
                            total_freed += sz
                            file_count += 1
                            if not args.dry_run:
                                f.unlink()
                            print(f"  {'[DRY]' if args.dry_run else ''} Remove clip: {vdir.name}/{f.name} ({_format_size(sz)})")
                        else:
                            orphaned_files += 1

    # Orphaned files (no matching task or manifest)
    if args.delete_orphaned:
        # Collect all known video_ids from manifests
        manifest_video_ids = set()
        for m in manifests.values():
            manifest_video_ids.add(m.get("video_id", ""))
            manifest_video_ids.add(m.get("task_id", ""))
        for sub in ["reports", "raw_videos"]:
            subdir = data_dir / sub
            if subdir.is_dir():
                for item in subdir.iterdir():
                    if item.is_dir():
                        # Check manifests first
                        if item.name in manifest_video_ids:
                            skipped_completed += 1
                            continue
                        if item.name in active_ids:
                            skipped_active += 1
                            continue
                        sz = _get_size(item)
                        if sz == 0:
                            continue
                        total_freed += sz
                        file_count += 1
                        orphaned_files += 1
                        if not args.dry_run:
                            shutil.rmtree(item, ignore_errors=True)
                        print(f"  {'[DRY]' if args.dry_run else ''} Remove orphan: {sub}/{item.name} ({_format_size(sz)})")

    if file_count == 0:
        print("  Nothing to clean up.")
    else:
        print(f"\nSummary:")
        print(f"  Scanned: {file_count + skipped_completed + skipped_active} files")
        print(f"  Manifest entries: {manifest_files}")
        print(f"  Orphaned files: {orphaned_files}")
        print(f"  Deleted: {file_count} file(s)")
        print(f"  Freed: {_format_size(total_freed)}")
        print(f"  Skipped (completed): {skipped_completed}")
        print(f"  Skipped (active): {skipped_active}")
        print(f"  Errors: 0")


if __name__ == "__main__":
    main()
