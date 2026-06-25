"""Tests for task_log_service — validates JSONL event output."""
import json

import pytest

from app.services.task_log_service import append_task_event, _sanitize, _TASKS_LOG_DIR


class TestSanitize:
    def test_sanitize_windows_path(self):
        result = _sanitize(r"File not found at D:\Agent\video.mp4")
        assert "<path>" in result
        assert "<path>" in result

    def test_sanitize_truncates_long(self):
        long_msg = "x" * 500
        result = _sanitize(long_msg, max_len=50)
        assert len(result) <= 53  # 50 + "..."

    def test_sanitize_short_message_unchanged(self):
        msg = "normal error message"
        assert _sanitize(msg) == msg


class TestAppendTaskEvent:
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        self._task_id = "_test_task_log"
        self._log_dir = _TASKS_LOG_DIR / self._task_id
        # Clean before
        if self._log_dir.is_dir():
            for f in self._log_dir.iterdir():
                f.unlink()
            self._log_dir.rmdir()
        yield
        # Clean after
        if self._log_dir.is_dir():
            for f in self._log_dir.iterdir():
                f.unlink()
            self._log_dir.rmdir()

    def _log_path(self):
        return _TASKS_LOG_DIR / self._task_id / "events.jsonl"

    def test_log_file_created(self):
        append_task_event(self._task_id, "vid001", "metadata", "start", "running")
        assert self._log_path().is_file()

    def test_log_content_is_valid_json(self):
        append_task_event(self._task_id, "vid001", "metadata", "start", "running")
        append_task_event(self._task_id, "vid001", "metadata", "success", "ok",
                          duration_ms=123.4)
        lines = self._log_path().read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        for line in lines:
            obj = json.loads(line)
            assert obj["task_id"] == self._task_id
            assert obj["video_id"] == "vid001"
            assert "timestamp" in obj

    def test_log_start_event_fields(self):
        append_task_event(self._task_id, "vid001", "detect_scenes", "start", "running")
        obj = json.loads(self._log_path().read_text(encoding="utf-8"))
        assert obj["step"] == "detect_scenes"
        assert obj["event"] == "start"
        assert obj["status"] == "running"
        assert obj["duration_ms"] is None

    def test_log_success_event_fields(self):
        append_task_event(self._task_id, "vid001", "metadata", "success", "ok",
                          duration_ms=456.7)
        obj = json.loads(self._log_path().read_text(encoding="utf-8"))
        assert obj["event"] == "success"
        assert obj["duration_ms"] == 456.7

    def test_log_error_event_with_traceback(self):
        append_task_event(self._task_id, "vid001", "detect_objects", "error", "error",
                          error="model failed", duration_ms=50.0, tb="Traceback...\n...")
        obj = json.loads(self._log_path().read_text(encoding="utf-8"))
        assert obj["event"] == "error"
        assert "traceback" in obj
        assert obj["traceback"] == "Traceback...\n..."

    def test_log_skipped_event(self):
        append_task_event(self._task_id, "vid001", "transcribe", "skipped", "skipped",
                          error="no audio")
        obj = json.loads(self._log_path().read_text(encoding="utf-8"))
        assert obj["event"] == "skipped"
        assert obj["error"] == "no audio"

    def test_multiple_events_appended(self):
        for i in range(3):
            append_task_event(self._task_id, "vid001", f"step_{i}", "start", "running")
        lines = self._log_path().read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3

