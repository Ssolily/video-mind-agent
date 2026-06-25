"""Tests for task_store.py — SQLite persistence of task records."""

import pytest

from app.services import task_store


# ── Fixtures ────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path):
    """Redirect the store to a temp database so tests don't touch the real one."""
    original_path = task_store._DB_PATH
    task_store.close_connection()
    task_store._DB_PATH = tmp_path / "test_app.db"
    task_store.init_db()
    yield
    task_store.close_connection()
    task_store._DB_PATH = original_path


# ── Tests ───────────────────────────────────────────


class TestTaskStore:
    def test_create_and_read(self):
        task_store.create_task_record(
            task_id="t001",
            video_id="vid001",
            status="pending",
        )
        record = task_store.get_task_record("t001")
        assert record is not None
        assert record["task_id"] == "t001"
        assert record["video_id"] == "vid001"
        assert record["status"] == "pending"
        assert record["current_step"] == ""
        assert record["progress"] == 0.0

    def test_create_with_result(self):
        result = {"plan": ["metadata", "frames"], "steps": []}
        task_store.create_task_record(
            task_id="t002",
            video_id="vid002",
            status="running",
            current_step="metadata",
            progress=0.5,
            result=result,
        )
        record = task_store.get_task_record("t002")
        assert record is not None
        assert record["status"] == "running"
        assert record["current_step"] == "metadata"
        assert record["progress"] == 0.5
        assert record["result"] == result

    def test_update_status(self):
        task_store.create_task_record(task_id="t003", video_id="vid003")
        task_store.update_task_record("t003", status="running", current_step="metadata")
        record = task_store.get_task_record("t003")
        assert record["status"] == "running"
        assert record["current_step"] == "metadata"

    def test_update_progress(self):
        task_store.create_task_record(task_id="t004", video_id="vid004")
        task_store.update_task_record("t004", progress=0.75)
        record = task_store.get_task_record("t004")
        assert record["progress"] == 0.75

    def test_update_result(self):
        task_store.create_task_record(task_id="t005", video_id="vid005")
        r = {"steps": [{"name": "metadata", "status": "ok"}]}
        task_store.update_task_record("t005", result=r)
        record = task_store.get_task_record("t005")
        assert record["result"] == r

    def test_get_nonexistent_returns_none(self):
        record = task_store.get_task_record("does_not_exist")
        assert record is None

    def test_multiple_tasks(self):
        task_store.create_task_record(task_id="t006", video_id="vid006")
        task_store.create_task_record(task_id="t007", video_id="vid007")
        r1 = task_store.get_task_record("t006")
        r2 = task_store.get_task_record("t007")
        assert r1 is not None and r1["video_id"] == "vid006"
        assert r2 is not None and r2["video_id"] == "vid007"

    def test_updated_at_changes_on_update(self):
        task_store.create_task_record(task_id="t008", video_id="vid008")
        r1 = task_store.get_task_record("t008")
        t1 = r1["updated_at"]
        task_store.update_task_record("t008", progress=1.0)
        r2 = task_store.get_task_record("t008")
        t2 = r2["updated_at"]
        assert t2 >= t1

    def test_result_json_roundtrip(self):
        complex_result = {
            "steps": [
                {"name": "metadata", "status": "ok"},
                {"name": "frames", "status": "ok", "count": 120},
            ],
            "nested": {"a": [1, 2, 3]},
        }
        task_store.create_task_record(
            task_id="t009",
            video_id="vid009",
            result=complex_result,
        )
        record = task_store.get_task_record("t009")
        assert record["result"] == complex_result
