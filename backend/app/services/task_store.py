"""SQLite-backed task store for persisting task state across restarts.

Uses ``check_same_thread=False`` and WAL mode so the background thread and
API handler can both access the same database without conflicts.
"""

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import DATA_DIR


# ── Database path ───────────────────────────────────

_DB_PATH = DATA_DIR / "app.db"
_local = threading.local()


def _get_connection() -> sqlite3.Connection:
    """Return a thread-local connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(
            str(_DB_PATH),
            check_same_thread=False,
        )
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA busy_timeout=5000")
    return _local.conn


@contextmanager
def _get_db():
    """Context manager that yields a connection and commits on success."""
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


# ── Schema ──────────────────────────────────────────

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    task_id                 TEXT PRIMARY KEY,
    video_id                TEXT NOT NULL,
    user_goal               TEXT NOT NULL DEFAULT '',
    status                  TEXT NOT NULL DEFAULT 'pending',
    current_step            TEXT NOT NULL DEFAULT '',
    progress                REAL NOT NULL DEFAULT 0.0,
    error                   TEXT,
    result                  TEXT,
    created_at              TEXT NOT NULL,
    updated_at              TEXT NOT NULL,
    queued_at               TEXT,
    started_at              TEXT,
    finished_at             TEXT,
    worker_id               TEXT,
    cancellation_requested  INTEGER NOT NULL DEFAULT 0,
    retry_count             INTEGER NOT NULL DEFAULT 0,
    parent_task_id          TEXT
);
"""


def close_connection() -> None:
    """Explicitly close the thread-local SQLite connection.
    
    Must be called before changing _DB_PATH in tests to prevent
    Windows file handle locks from blocking tmp_path cleanup.
    """
    if hasattr(_local, "conn") and _local.conn is not None:
        try:
            _local.conn.close()
        except Exception:
            pass
        _local.conn = None


def init_db() -> None:
    """Ensure the database and tasks table exist.

    Safe to call multiple times — will not re-create the table.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _get_db() as db:
        db.execute(_CREATE_TABLE_SQL)
        # Migrate: add columns that may be missing from older schemas
        for col, col_type in [("user_goal", "TEXT"), ("queued_at", "TEXT"), ("started_at", "TEXT"), ("finished_at", "TEXT"), ("worker_id", "TEXT"), ("cancellation_requested", "INTEGER DEFAULT 0"), ("retry_count", "INTEGER DEFAULT 0"), ("parent_task_id", "TEXT")]:
            try:
                db.execute(f"ALTER TABLE tasks ADD COLUMN {col} {col_type}")
            except Exception:
                pass  # Column already exists
        # Clear any global references that might hold stale data
        pass


# ── CRUD ────────────────────────────────────────────

def create_task_record(
    task_id: str,
    video_id: str,
    user_goal: str = "",
    status: str = "pending",
    current_step: str = "",
    progress: float = 0.0,
    error: Optional[str] = None,
    result: Optional[dict] = None,
    queued_at: Optional[str] = None,
    started_at: Optional[str] = None,
    finished_at: Optional[str] = None,
    worker_id: Optional[str] = None,
    cancellation_requested: bool = False,
    retry_count: int = 0,
    parent_task_id: Optional[str] = None,
) -> None:
    """Insert a new task record."""
    now = datetime.now(timezone.utc).isoformat()
    with _get_db() as db:
        db.execute(
            """INSERT INTO tasks (task_id, video_id, user_goal, status, current_step, progress,
                                  error, result, created_at, updated_at,
                                  queued_at, started_at, finished_at, worker_id,
                                  cancellation_requested, retry_count, parent_task_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task_id,
                video_id,
                user_goal,
                status,
                current_step,
                progress,
                error,
                json.dumps(result) if result is not None else None,
                now,
                now,
                queued_at,
                started_at,
                finished_at,
                worker_id,
                1 if cancellation_requested else 0,
                retry_count,
                parent_task_id,
            ),
        )


def update_task_record(task_id: str, **kw) -> None:
    """Update one or more fields of an existing task record.

    Accepts any of: status, current_step, progress, error, result.
    """
    allowed = {"status", "current_step", "progress", "error", "result", "queued_at", "started_at", "finished_at", "worker_id", "cancellation_requested", "retry_count"}
    updates = {k: v for k, v in kw.items() if k in allowed}
    if not updates:
        return

    now = datetime.now(timezone.utc).isoformat()
    updates["updated_at"] = now

    if "result" in updates and updates["result"] is not None:
        updates["result"] = json.dumps(updates["result"])

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [task_id]

    with _get_db() as db:
        db.execute(
            f"UPDATE tasks SET {set_clause} WHERE task_id = ?",
            values,
        )


def get_task_record(task_id: str) -> Optional[dict]:
    """Return a task dict, or *None* if not found."""
    with _get_db() as db:
        row = db.execute(
            "SELECT * FROM tasks WHERE task_id = ?", (task_id,),
        ).fetchone()

    if row is None:
        return None

    d = dict(row)
    if d.get("result"):
        try:
            d["result"] = json.loads(d["result"])
        except (json.JSONDecodeError, TypeError):
            pass
    return d


# ── List / Cancel / Search ──────────────────────────


def list_task_records(
    status_filter: str | None = None,
    video_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Return a list of task records, newest first."""
    conditions: list[str] = []
    params: list = []
    if status_filter:
        conditions.append("status = ?")
        params.append(status_filter)
    if video_id:
        conditions.append("video_id = ?")
        params.append(video_id)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"SELECT * FROM tasks {where} ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    with _get_db() as db:
        rows = db.execute(sql, params).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        if d.get("result"):
            try:
                d["result"] = json.loads(d["result"])
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(d)
    return result


def count_tasks_by_status() -> dict[str, int]:
    """Return a dict mapping status -> count for all tasks."""
    with _get_db() as db:
        rows = db.execute(
            "SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status"
        ).fetchall()
    return {row["status"]: row["cnt"] for row in rows}


# ── Bootstrap ───────────────────────────────────────

init_db()

def mark_cancellation_requested(task_id: str) -> None:
    """Set the cancellation_requested flag on a task."""
    update_task_record(task_id, cancellation_requested=1)


