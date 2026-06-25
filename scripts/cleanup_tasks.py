"""Clean up old/failed tasks from the database.

Usage:
    python scripts/cleanup_tasks.py --older-than-days 7
    python scripts/cleanup_tasks.py --older-than-days 30 --dry-run
    python scripts/cleanup_tasks.py --older-than-days 7 --only-failed
    python scripts/cleanup_tasks.py --older-than-days 7 --status failed,cancelled
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))


def main():
    from app.services import task_store
    parser = argparse.ArgumentParser(description="Clean up old tasks from the database")
    parser.add_argument("--older-than-days", type=float, default=7.0, help="Delete tasks older than N days")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be deleted without deleting")
    parser.add_argument("--only-failed", action="store_true", help="Only delete failed/cancelled tasks")
    parser.add_argument("--status", default=None, help="Comma-separated statuses to delete (e.g. failed,cancelled)")
    args = parser.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.older_than_days)
    cutoff_str = cutoff.isoformat()

    allowed_statuses = None
    if args.status:
        allowed_statuses = set(s.strip() for s in args.status.split(","))
    elif args.only_failed:
        allowed_statuses = {"failed", "cancelled"}

    all_tasks = task_store.list_task_records()
    to_delete = []

    for t in all_tasks:
        created = t.get("created_at")
        if not created:
            continue
        try:
            created_dt = datetime.fromisoformat(created)
        except (ValueError, TypeError):
            continue
        if created_dt >= cutoff:
            continue
        status = t.get("status", "")
        if allowed_statuses and status not in allowed_statuses:
            continue
        to_delete.append(t["task_id"])

    if args.dry_run:
        print(f"[DRY RUN] Would delete {len(to_delete)} task(s) older than {args.older_than_days} day(s)")
        for tid in to_delete:
            r = task_store.get_task_record(tid)
            status = r.get("status", "?") if r else "?"
            print(f"  {tid} (status={status})")
        return

    # Delete by setting status to deleted (soft delete to preserve history)
    for tid in to_delete:
        task_store.update_task_record(tid, status="deleted", progress=0.0, current_step="")
    
    print(f"Cleaned up {len(to_delete)} task(s) older than {args.older_than_days} day(s)")
    if to_delete:
        print("Deleted:", ", ".join(to_delete[:10]))
        if len(to_delete) > 10:
            print(f"  ... and {len(to_delete) - 10} more")


if __name__ == "__main__":
    main()
