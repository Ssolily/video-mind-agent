"""Per-task logging: each task gets its own log file."""
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from app.config import DATA_DIR

TASK_LOGS_DIR = DATA_DIR / "task_logs"


def _ensure_dir():
    TASK_LOGS_DIR.mkdir(parents=True, exist_ok=True)


def get_task_log_path(task_id):
    _ensure_dir()
    return TASK_LOGS_DIR / f"{task_id}.log"


def write_task_log(task_id, message, level="INFO"):
    path = get_task_log_path(task_id)
    ts = datetime.now(timezone.utc).isoformat()
    line = f"{ts} [{level}] {message}\n"
    with open(path, "a", encoding="utf-8") as f:
        f.write(line)


def read_task_log_lines(task_id, n=200):
    path = get_task_log_path(task_id)
    if not path.is_file():
        return []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return [l.rstrip("\n") for l in lines[-n:]]
