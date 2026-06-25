"""Pytest configuration - ensures clean test environment.

Sets YOLO_CONFIG_DIR to a project-local cache directory so that
Ultralytics settings access does not hit PermissionError on the
real user profile directory.
"""
import os
import pytest
import pathlib

@pytest.fixture(autouse=True)
def _close_task_store_connections():
    import app.services.task_store
    app.services.task_store.close_connection()
    yield
    app.services.task_store.close_connection()


@pytest.fixture(autouse=True)
def _mock_task_queue(monkeypatch):
    """Prevent background worker threads from starting during tests."""
    import app.services.task_queue
    import app.services.task_logger
    monkeypatch.setattr(app.services.task_queue, "start_workers", lambda **kw: None)
    monkeypatch.setattr(app.services.task_queue, "stop_workers", lambda **kw: None)
    # Don't mock check_timeouts or recover_stale_tasks - reliability tests need real implementations
    # Don't mock write_task_log - logger tests need real implementation


_tmp_dir = pathlib.Path(__file__).resolve().parent / ".pytest_cache" / "ultralytics"
_tmp_dir.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(_tmp_dir))
