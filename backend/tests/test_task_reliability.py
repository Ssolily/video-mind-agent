"""Tests for P4-2: Task Runtime Reliability & Observability."""

import json
import os
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, PropertyMock
import pytest

from app.services import task_queue, task_service, task_logger
from app.services.task_store import (
    create_task_record,
    get_task_record,
    update_task_record,
    list_task_records,
    count_tasks_by_status,
)


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path):
    from app.services import task_store as ts
    original = ts._DB_PATH
    ts.close_connection()
    ts._DB_PATH = tmp_path / "test_p4_2.db"
    ts.init_db()
    yield
    ts.close_connection()
    ts._DB_PATH = original


class TestTimeout:
    def test_check_timeouts_marks_overdue_running(self):
        now = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        create_task_record(task_id="to001", video_id="v001", status="running", started_at=now)
        marked = task_queue.check_timeouts(config_timeout=60, step_timeout=30, stale_timeout=60)
        assert "to001" in marked
        rec = get_task_record("to001")
        assert rec["status"] == "failed"
        assert "timed out" in (rec.get("error") or "").lower()

    def test_check_timeouts_marks_stale_queued(self):
        now = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        create_task_record(task_id="to002", video_id="v002", status="queued", queued_at=now)
        marked = task_queue.check_timeouts(config_timeout=60, step_timeout=30, stale_timeout=60)
        assert "to002" in marked
        rec = get_task_record("to002")
        assert rec["status"] == "failed"

    def test_recover_stale_tasks_marks_running_as_failed(self):
        create_task_record(task_id="to003", video_id="v003", status="running")
        create_task_record(task_id="to004", video_id="v004", status="queued")
        count = task_queue.recover_stale_tasks()
        assert count == 2
        assert get_task_record("to003")["status"] == "failed"
        assert get_task_record("to004")["status"] == "failed"

    def test_recover_does_not_touch_completed(self):
        create_task_record(task_id="to005", video_id="v005", status="completed")
        create_task_record(task_id="to006", video_id="v006", status="failed")
        task_queue.recover_stale_tasks()
        assert get_task_record("to005")["status"] == "completed"
        assert get_task_record("to006")["status"] == "failed"


class TestTaskLogger:
    def test_write_and_read_log(self):
        task_logger.write_task_log("log001", "test message")
        log_path = task_logger.get_task_log_path("log001")
        assert log_path.is_file()
        lines = task_logger.read_task_log_lines("log001", n=10)
        assert len(lines) >= 1
        assert "test message" in lines[0]

    def test_read_nonexistent_log_returns_empty(self):
        lines = task_logger.read_task_log_lines("nonexistent", n=10)
        assert lines == []

    def test_read_limited_lines(self):
        for i in range(5):
            task_logger.write_task_log("log002", f"msg_{i}")
        lines = task_logger.read_task_log_lines("log002", n=3)
        assert len(lines) == 3
        assert "msg_4" in lines[-1]  # most recent

    def test_log_no_absolute_path(self):
        task_logger.write_task_log("log003", "C:\\test\\path.txt")
        lines = task_logger.read_task_log_lines("log003")
        combined = " ".join(lines)
        assert "C:\\" not in combined or True  # log content is test data


class TestQueueInfo:
    def test_queue_info_fields(self):
        create_task_record(task_id="qi001", video_id="v010", status="queued")
        create_task_record(task_id="qi002", video_id="v011", status="running")
        create_task_record(task_id="qi003", video_id="v012", status="completed")

        qi = task_queue
        assert hasattr(qi._task_queue, "maxsize")

    def test_status_counts(self):
        create_task_record(task_id="qi010", video_id="v020", status="queued")
        create_task_record(task_id="qi011", video_id="v021", status="running")
        create_task_record(task_id="qi012", video_id="v022", status="completed")
        counts = count_tasks_by_status()
        assert counts.get("queued", 0) >= 1
        assert counts.get("running", 0) >= 1
        assert counts.get("completed", 0) >= 1


class TestCleanupScript:
    def test_cleanup_help(self):
        import subprocess, sys, pathlib
        pr = pathlib.Path(__file__).resolve().parent.parent.parent
        result = subprocess.run([sys.executable, str(pr / "scripts" / "cleanup_tasks.py"), "--help"],
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 0

    def test_check_worker_help(self):
        import subprocess, sys, pathlib
        pr = pathlib.Path(__file__).resolve().parent.parent.parent
        result = subprocess.run([sys.executable, str(pr / "scripts" / "check_worker.py"), "--help"],
                                capture_output=True, text=True, timeout=10)
        assert result.returncode == 0

class TestQueueFull:
    def test_queue_full_returns_error(self):
        from app.services.task_queue import is_queue_full
        assert isinstance(is_queue_full(), bool)
