"""Tests for task queue and task service."""
import json
import time
import pytest
from unittest.mock import patch, MagicMock

from app.services import task_queue, task_service
from app.services.task_store import (
    create_task_record,
    get_task_record,
    update_task_record,
    list_task_records,
    count_tasks_by_status,
    mark_cancellation_requested,
)


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path):
    """Redirect task_store to a temp database."""
    from app.services import task_store as ts
    ts.close_connection()
    ts._DB_PATH = tmp_path / "test_queue.db"
    ts.init_db()
    yield
    ts.close_connection()
    ts._DB_PATH = None


class TestQueueCore:
    def test_enqueue_and_queue_size(self):
        create_task_record(task_id="tq001", video_id="v001", status="queued")
        task_queue.enqueue("tq001", "v001", "test", 2.0, 5)
        assert task_queue.get_queue_size() >= 0

    def test_queue_maxsize(self):
        assert task_queue._task_queue.maxsize == 20

    def test_active_task_none_initially(self):
        assert task_queue.get_active_task() is None

    def test_is_queue_full_returns_false_initially(self):
        assert task_queue.is_queue_full() is False


class TestTaskService:
    def test_create_task_returns_id(self):
        tid = task_service.create_task("v001", "test", 2.0, 5)
        assert tid is not None
        assert len(tid) > 0

    def test_create_task_creates_queued_record(self):
        tid = task_service.create_task("v002", "test", 2.0, 5)
        rec = get_task_record(tid)
        assert rec is not None
        assert rec["status"] == "queued"

    def test_get_task_returns_record(self):
        tid = task_service.create_task("v003", "test", 2.0, 5)
        rec = task_service.get_task(tid)
        assert rec is not None
        assert rec["task_id"] == tid

    def test_get_task_nonexistent_returns_none(self):
        rec = task_service.get_task("does_not_exist")
        assert rec is None

    def test_list_tasks_empty(self):
        tasks = task_service.list_tasks()
        assert isinstance(tasks, list)

    def test_list_tasks_with_video_id(self):
        task_service.create_task("v004", "test")
        tasks = task_service.list_tasks(video_id="v004")
        assert len(tasks) >= 1

    def test_cancel_queued_task(self):
        tid = task_service.create_task("v005", "test")
        ok = task_service.cancel_task(tid)
        assert ok is True
        rec = get_task_record(tid)
        assert rec["status"] == "cancelled"

    def test_cancel_already_completed_returns_false(self):
        create_task_record(task_id="tc001", video_id="v006", status="completed")
        ok = task_service.cancel_task("tc001")
        assert ok is False

    def test_cancel_running_sets_cancellation_requested(self):
        create_task_record(task_id="tc002", video_id="v007", status="running")
        with patch("app.services.task_service.mark_cancellation_requested") as mock:
            task_service.cancel_task("tc002")
            mock.assert_called_once()

    def test_retry_failed_task_creates_new(self):
        create_task_record(task_id="tr001", video_id="v008", user_goal="test", status="failed")
        new_id = task_service.retry_task("tr001")
        assert new_id is not None
        assert new_id != "tr001"
        rec = get_task_record(new_id)
        assert rec["status"] == "queued"
        assert rec["parent_task_id"] == "tr001"
        assert rec["retry_count"] == 1

    def test_retry_nonexistent_returns_none(self):
        new_id = task_service.retry_task("does_not_exist")
        assert new_id is None


class TestTaskStore:
    def test_create_record_with_user_goal(self):
        create_task_record(task_id="ts001", video_id="v010", user_goal="detect objects")
        rec = get_task_record("ts001")
        assert rec["user_goal"] == "detect objects"

    def test_create_record_with_timestamps(self):
        now = "2026-01-01T00:00:00"
        create_task_record(task_id="ts002", video_id="v011", queued_at=now, started_at=now, finished_at=now)
        rec = get_task_record("ts002")
        assert rec["queued_at"] == now
        assert rec["started_at"] == now
        assert rec["finished_at"] == now

    def test_create_record_with_cancellation_requested(self):
        create_task_record(task_id="ts003", video_id="v012", cancellation_requested=True)
        rec = get_task_record("ts003")
        assert rec["cancellation_requested"] == 1

    def test_mark_cancellation_requested(self):
        create_task_record(task_id="ts004", video_id="v013")
        mark_cancellation_requested("ts004")
        rec = get_task_record("ts004")
        assert rec["cancellation_requested"] == 1

    def test_list_task_records_with_status_filter(self):
        create_task_record(task_id="ts005", video_id="v014", status="running")
        tasks = list_task_records(status_filter="running")
        assert any(t["task_id"] == "ts005" for t in tasks)

    def test_count_tasks_by_status(self):
        create_task_record(task_id="ts006", video_id="v015", status="queued")
        create_task_record(task_id="ts007", video_id="v016", status="completed")
        counts = count_tasks_by_status()
        assert isinstance(counts, dict)
        assert "queued" in counts
        assert "completed" in counts

    def test_update_worker_id(self):
        create_task_record(task_id="ts008", video_id="v017")
        update_task_record("ts008", worker_id="worker-1", started_at="2026-01-01T00:00:00")
        rec = get_task_record("ts008")
        assert rec["worker_id"] == "worker-1"
        assert rec["started_at"] is not None

    def test_update_cancellation_requested(self):
        create_task_record(task_id="ts009", video_id="v018")
        update_task_record("ts009", cancellation_requested=1)
        rec = get_task_record("ts009")
        assert rec["cancellation_requested"] == 1

    def test_retry_count_persisted(self):
        create_task_record(task_id="ts010", video_id="v019", retry_count=3)
        rec = get_task_record("ts010")
        assert rec["retry_count"] == 3

    def test_parent_task_id_persisted(self):
        create_task_record(task_id="ts011", video_id="v020", parent_task_id="ts010")
        rec = get_task_record("ts011")
        assert rec["parent_task_id"] == "ts010"
