"""Tests for Result API, report endpoints, and absolute path cleanup."""

import json
import os
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# ── FFmpeg helper ───────────────────────────────────


def _make_small_video(path: Path, duration: float = 1.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", f"testsrc=duration={duration}:size=160x90:rate=1",
         "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         "-frames:v", str(max(1, int(duration))), "-an", str(path)],
        capture_output=True, text=True, timeout=30, check=True,
    )


def _write_report_json(video_id: str, reports_root: Path, data: dict):
    d = reports_root / video_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "final_report.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _write_report_md(video_id: str, reports_root: Path, text: str):
    d = reports_root / video_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "final_report.md").write_text(text, encoding="utf-8")


def _write_highlights(video_id: str, reports_root: Path, highlights: list):
    d = reports_root / video_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "highlights.json").write_text(json.dumps(highlights, ensure_ascii=False), encoding="utf-8")


def _write_metadata(video_id: str, reports_root: Path, meta: dict):
    d = reports_root / video_id
    d.mkdir(parents=True, exist_ok=True)
    (d / "metadata.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


# ── A. Result API basic tests ────────────────────────


class TestResultApiBasic:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        from app.config import RAW_VIDEOS_DIR, CLIPS_DIR, REPORTS_DIR, DATA_DIR
        self.raw_root = tmp_path / "raw_videos"
        self.raw_root.mkdir()
        self.clips_root = tmp_path / "clips"
        self.clips_root.mkdir()
        self.reports_root = tmp_path / "reports"
        self.reports_root.mkdir()
        self.data_root = tmp_path / "data"
        self.data_root.mkdir()

        monkeypatch.setattr("app.config.RAW_VIDEOS_DIR", self.raw_root)
        monkeypatch.setattr("app.config.CLIPS_DIR", self.clips_root)
        monkeypatch.setattr("app.config.REPORTS_DIR", self.reports_root)
        monkeypatch.setattr("app.config.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.storage_service.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.storage_service._REGISTRY_PATH", self.data_root / "video_registry.json")
        monkeypatch.setattr("app.services.video_result_service.RAW_VIDEOS_DIR", self.raw_root)
        monkeypatch.setattr("app.services.video_result_service.CLIPS_DIR", self.clips_root)
        monkeypatch.setattr("app.services.video_result_service.REPORTS_DIR", self.reports_root)
        monkeypatch.setattr("app.services.video_result_service.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.task_store._DB_PATH", self.data_root / "app.db")
        from app.services import task_store; task_store.close_connection(); task_store.init_db()

        # Create a test video
        self.video_id = "result_test_vid"
        self.video_path = self.raw_root / f"{self.video_id}.mp4"
        _make_small_video(self.video_path)

        # Register in video_registry
        reg_path = self.data_root / "video_registry.json"
        reg_path.write_text(json.dumps({self.video_id: {"raw_path": str(self.video_path), "filename": "test.mp4"}}))

        # Metadata
        _write_metadata(self.video_id, self.reports_root, {"duration": 1.0, "fps": 1, "width": 160, "height": 90, "frame_count": 1})

        from app.main import app
        self.client = TestClient(app)

    def test_unknown_video_returns_404(self):
        resp = self.client.get("/api/v1/videos/nonexistent/result")
        assert resp.status_code == 404

    def test_uploaded_video_returns_200(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        assert resp.status_code == 200

    def test_uploaded_status(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        data = resp.json()
        assert data["status"] == "uploaded"

    def test_source_url_correct(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        data = resp.json()
        assert data["source_url"] == f"/api/v1/videos/{self.video_id}/source"

    def test_duration_correct(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        data = resp.json()
        assert data["duration"] == 1.0

    def test_highlights_empty_when_no_task(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        data = resp.json()
        assert data["highlights"] == []

    def test_clips_empty_when_no_export(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        data = resp.json()
        assert data["clips"] == []

    def test_report_urls_null_when_no_report(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        data = resp.json()
        assert data["report"]["markdown_url"] is None
        assert data["report"]["json_url"] is None

    def test_no_absolute_paths(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        body = json.dumps(resp.json())
        assert "D:\\\\" not in body
        assert "C:\\\\" not in body
        assert "raw_path" not in body
        assert "clip_paths" not in body
        assert "highlight_path" not in body
        assert "json_path" not in body
        assert "md_path" not in body

    def test_response_json_serializable(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        # Already deserialized — ensure no errors
        assert resp.json() is not None


# ── B. Success result tests ─────────────────────────


class TestResultApiSuccess:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        from app.config import RAW_VIDEOS_DIR, CLIPS_DIR, REPORTS_DIR, DATA_DIR
        self.raw_root = tmp_path / "raw_videos"
        self.raw_root.mkdir()
        self.clips_root = tmp_path / "clips"
        self.clips_root.mkdir()
        self.reports_root = tmp_path / "reports"
        self.reports_root.mkdir()
        self.data_root = tmp_path / "data"
        self.data_root.mkdir()

        monkeypatch.setattr("app.config.RAW_VIDEOS_DIR", self.raw_root)
        monkeypatch.setattr("app.config.CLIPS_DIR", self.clips_root)
        monkeypatch.setattr("app.config.REPORTS_DIR", self.reports_root)
        monkeypatch.setattr("app.config.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.storage_service.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.storage_service._REGISTRY_PATH", self.data_root / "video_registry.json")
        monkeypatch.setattr("app.services.video_result_service.RAW_VIDEOS_DIR", self.raw_root)
        monkeypatch.setattr("app.services.video_result_service.CLIPS_DIR", self.clips_root)
        monkeypatch.setattr("app.services.video_result_service.REPORTS_DIR", self.reports_root)
        monkeypatch.setattr("app.services.video_result_service.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.task_store._DB_PATH", self.data_root / "app.db")
        from app.services import task_store; task_store.close_connection(); task_store.init_db()

        self.video_id = "success_vid"
        self.video_path = self.raw_root / f"{self.video_id}.mp4"
        _make_small_video(self.video_path)
        _write_metadata(self.video_id, self.reports_root, {"duration": 2.0})

        reg_path = self.data_root / "video_registry.json"
        reg_path.write_text(json.dumps({self.video_id: {"raw_path": str(self.video_path), "filename": "test.mp4"}}))

        # Write highlights
        _write_highlights(self.video_id, self.reports_root, [
            {
                "id": "hl_0001",
                "start_time": 0.0, "end_time": 1.0, "duration": 1.0,
                "score": 0.5, "base_score": 0.5, "selection_score": 0.5,
                "overlap_penalty": 0.0,
                "score_breakdown": {
                    "object": {"raw": 0.5, "weight": 0.25, "weighted": 0.125},
                },
                "reason": ["目标丰富(0.50)"],
            }
        ])

        # Write reports
        _write_report_md(self.video_id, self.reports_root, "# Markdown Report")
        _write_report_json(self.video_id, self.reports_root, {"video_id": self.video_id})

        # Create clips
        clip_dir = self.clips_root / self.video_id
        clip_dir.mkdir(parents=True, exist_ok=True)
        _make_small_video(clip_dir / "clip_001.mp4", duration=0.5)

        # Clear any lingering tasks from previous tests
        
        # Write task state to SQLite
        from app.services.task_store import create_task_record, update_task_record
        task_id = f"task_success_{id(self)}"
        create_task_record(task_id=task_id, video_id=self.video_id, status="success")
        update_task_record(task_id, status="success", progress=1.0, current_step="done")



        from app.main import app
        self.client = TestClient(app)

    def test_success_returns_full_result(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

    def test_highlight_fields_complete(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        data = resp.json()
        hl = data["highlights"][0]
        assert hl["id"] == "hl_0001"
        assert hl["score"] == 0.5
        assert hl["base_score"] == 0.5
        assert hl["selection_score"] == 0.5
        assert hl["overlap_penalty"] == 0.0

    def test_score_equals_selection_score(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        hl = resp.json()["highlights"][0]
        assert hl["score"] == hl["selection_score"]

    def test_reason_is_list(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        hl = resp.json()["highlights"][0]
        assert isinstance(hl["reason"], list)
        assert len(hl["reason"]) > 0

    def test_score_breakdown_has_raw_weight_weighted(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        sb = resp.json()["highlights"][0]["score_breakdown"]
        obj = sb["object"]
        assert "raw" in obj
        assert "weight" in obj
        assert "weighted" in obj
        assert obj["raw"] == 0.5

    def test_clip_url_points_to_media_route(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        clip = resp.json()["clips"][0]
        assert clip["url"].startswith("/api/v1/videos/")

    def test_clip_id_stable(self):
        resp1 = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        resp2 = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        assert resp1.json()["clips"] == resp2.json()["clips"]

    def test_report_urls_correct(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        rpt = resp.json()["report"]
        assert rpt["markdown_url"] == f"/api/v1/videos/{self.video_id}/reports/markdown"
        assert rpt["json_url"] == f"/api/v1/videos/{self.video_id}/reports/json"

    def test_no_absolute_paths(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        body = json.dumps(resp.json())
        assert "raw_path" not in body
        assert "clip_paths" not in body
        assert "highlight_path" not in body
        assert "json_path" not in body
        assert "md_path" not in body


# ── C. Status tests ─────────────────────────────────


class TestResultApiStatus:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        from app.config import RAW_VIDEOS_DIR, CLIPS_DIR, REPORTS_DIR, DATA_DIR
        self.raw_root = tmp_path / "raw_videos"
        self.raw_root.mkdir()
        self.reports_root = tmp_path / "reports"
        self.reports_root.mkdir()
        self.data_root = tmp_path / "data"
        self.data_root.mkdir()
        self.clips_root = tmp_path / "clips"
        self.clips_root.mkdir()

        monkeypatch.setattr("app.config.RAW_VIDEOS_DIR", self.raw_root)
        monkeypatch.setattr("app.config.CLIPS_DIR", self.clips_root)
        monkeypatch.setattr("app.config.REPORTS_DIR", self.reports_root)
        monkeypatch.setattr("app.config.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.storage_service.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.storage_service._REGISTRY_PATH", self.data_root / "video_registry.json")
        monkeypatch.setattr("app.services.video_result_service.RAW_VIDEOS_DIR", self.raw_root)
        monkeypatch.setattr("app.services.video_result_service.CLIPS_DIR", self.clips_root)
        monkeypatch.setattr("app.services.video_result_service.REPORTS_DIR", self.reports_root)
        monkeypatch.setattr("app.services.video_result_service.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.task_store._DB_PATH", self.data_root / "app.db")
        from app.services import task_store; task_store.close_connection(); task_store.init_db()

        self.video_id = "status_vid"
        self.video_path = self.raw_root / f"{self.video_id}.mp4"
        _make_small_video(self.video_path)
        _write_metadata(self.video_id, self.reports_root, {"duration": 1.0})

        reg_path = self.data_root / "video_registry.json"
        reg_path.write_text(json.dumps({self.video_id: {"raw_path": str(self.video_path), "filename": "test.mp4"}}))

        from app.main import app
                # Clear lingering tasks
        
        self.client = TestClient(app)

    def _inject_task(self, status):
        import uuid
        from app.services.task_store import create_task_record, update_task_record
        task_id = "task_" + uuid.uuid4().hex[:8]
        error = "部分步骤失败: clip export failed" if status == "failed" else None
        create_task_record(task_id=task_id, video_id=self.video_id, status=status)
        update_task_record(task_id, status=status, error=error)

    def test_pending_returns_200(self):
        self._inject_task("pending")
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        assert resp.status_code == 200

    def test_running_returns_200(self):
        self._inject_task("running")
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        assert resp.status_code == 200

    def test_success_returns_200(self):
        self._inject_task("success")
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        assert resp.status_code == 200

    def test_completed_with_errors_returns_200(self):
        self._inject_task("completed_with_errors")
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        assert resp.status_code == 200

    def test_completed_with_errors_has_warnings(self):
        self._inject_task("completed_with_errors")
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        data = resp.json()
        assert len(data["warnings"]) > 0

    def test_failed_returns_200(self):
        self._inject_task("failed")
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        assert resp.status_code == 200

    def test_failed_error_no_traceback(self):
        self._inject_task("failed")
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        data = resp.json()
        err = data.get("error", "")
        assert "Traceback" not in (err or "")
        assert "D:\\\\" not in (err or "")


# ── D. Historical data compatibility ────────────────


class TestHistoricalCompatibility:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        from app.config import RAW_VIDEOS_DIR, CLIPS_DIR, REPORTS_DIR, DATA_DIR
        self.raw_root = tmp_path / "raw_videos"
        self.raw_root.mkdir()
        self.clips_root = tmp_path / "clips"
        self.clips_root.mkdir()
        self.reports_root = tmp_path / "reports"
        self.reports_root.mkdir()
        self.data_root = tmp_path / "data"
        self.data_root.mkdir()

        monkeypatch.setattr("app.config.RAW_VIDEOS_DIR", self.raw_root)
        monkeypatch.setattr("app.config.CLIPS_DIR", self.clips_root)
        monkeypatch.setattr("app.config.REPORTS_DIR", self.reports_root)
        monkeypatch.setattr("app.config.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.storage_service.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.storage_service._REGISTRY_PATH", self.data_root / "video_registry.json")
        monkeypatch.setattr("app.services.video_result_service.RAW_VIDEOS_DIR", self.raw_root)
        monkeypatch.setattr("app.services.video_result_service.CLIPS_DIR", self.clips_root)
        monkeypatch.setattr("app.services.video_result_service.REPORTS_DIR", self.reports_root)
        monkeypatch.setattr("app.services.video_result_service.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.task_store._DB_PATH", self.data_root / "app.db")
        from app.services import task_store; task_store.close_connection(); task_store.init_db()

        self.video_id = "hist_vid"
        self.video_path = self.raw_root / f"{self.video_id}.mp4"
        _make_small_video(self.video_path)
        _write_metadata(self.video_id, self.reports_root, {"duration": 1.0})

        reg_path = self.data_root / "video_registry.json"
        reg_path.write_text(json.dumps({self.video_id: {"raw_path": str(self.video_path), "filename": "test.mp4"}}))

        from app.main import app
        self.client = TestClient(app)

    def _set_highlights(self, hl):
        _write_highlights(self.video_id, self.reports_root, hl)

    def test_missing_selection_score(self):
        self._set_highlights([{"id": "h1", "start_time": 0, "end_time": 1, "duration": 1, "score": 0.5}])
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        hl = resp.json()["highlights"][0]
        assert hl["score"] == 0.5

    def test_missing_score_uses_selection_score(self):
        self._set_highlights([{"id": "h1", "start_time": 0, "end_time": 1, "duration": 1, "selection_score": 0.7}])
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        hl = resp.json()["highlights"][0]
        assert hl["score"] == 0.7

    def test_missing_base_score(self):
        self._set_highlights([{"id": "h1", "start_time": 0, "end_time": 1, "duration": 1, "score": 0.5}])
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        hl = resp.json()["highlights"][0]
        assert hl["base_score"] == 0.5

    def test_missing_overlap_penalty(self):
        self._set_highlights([{"id": "h1", "start_time": 0, "end_time": 1, "duration": 1, "score": 0.5}])
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        assert resp.json()["highlights"][0]["overlap_penalty"] == 0.0

    def test_missing_score_breakdown(self):
        self._set_highlights([{"id": "h1", "start_time": 0, "end_time": 1, "duration": 1, "score": 0.5}])
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        assert resp.json()["highlights"][0]["score_breakdown"] == {}

    def test_missing_reason(self):
        self._set_highlights([{"id": "h1", "start_time": 0, "end_time": 1, "duration": 1, "score": 0.5}])
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        assert resp.json()["highlights"][0]["reason"] == []

    def test_reason_as_old_string(self):
        self._set_highlights([{"id": "h1", "start_time": 0, "end_time": 1, "duration": 1, "score": 0.5, "reason": "old string"}])
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        assert isinstance(resp.json()["highlights"][0]["reason"], list)
        assert "old string" in resp.json()["highlights"][0]["reason"]

    def test_missing_highlight_id(self):
        self._set_highlights([{"start_time": 0, "end_time": 1, "duration": 1, "score": 0.5}])
        hl = self.client.get(f"/api/v1/videos/{self.video_id}/result").json()["highlights"][0]
        assert hl["id"].startswith("hl_")

    def test_unknown_fields_ignored(self):
        self._set_highlights([{"id": "h1", "start_time": 0, "end_time": 1, "duration": 1, "score": 0.5, "extra_field": "ignored"}])
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        assert resp.status_code == 200


# ── E. Report endpoints ─────────────────────────────


class TestReportEndpoints:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        from app.config import REPORTS_DIR
        self.reports_root = tmp_path / "reports"
        self.reports_root.mkdir()

        monkeypatch.setattr("app.config.REPORTS_DIR", self.reports_root)

        self.video_id = "report_vid"
        _write_report_md(self.video_id, self.reports_root, "# 测试报告\n\n中文字符正常")
        _write_report_json(self.video_id, self.reports_root, {"video_id": self.video_id, "score": 0.5})

        from app.main import app
        self.client = TestClient(app)

    def test_markdown_returns_200(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/reports/markdown")
        assert resp.status_code == 200

    def test_markdown_utf8(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/reports/markdown")
        assert "中文字符正常" in resp.text

    def test_markdown_content_type(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/reports/markdown")
        ct = resp.headers.get("content-type", "")
        assert "text/markdown" in ct
        assert "utf-8" in ct.lower()

    def test_markdown_not_found(self):
        resp = self.client.get("/api/v1/videos/nonexistent/reports/markdown")
        assert resp.status_code == 404

    def test_json_returns_200(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/reports/json")
        assert resp.status_code == 200

    def test_json_content_type(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/reports/json")
        assert "application/json" in resp.headers.get("content-type", "")

    def test_json_not_found(self):
        resp = self.client.get("/api/v1/videos/nonexistent/reports/json")
        assert resp.status_code == 404

    def test_no_absolute_paths(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/reports/markdown")
        assert "D:\\\\" not in resp.text

        resp2 = self.client.get(f"/api/v1/videos/{self.video_id}/reports/json")
        body = json.dumps(resp2.json())
        assert "D:\\\\" not in body


# ── F. Old API path cleanup tests ───────────────────


class TestOldApiCleanup:
    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        from app.config import RAW_VIDEOS_DIR, CLIPS_DIR, REPORTS_DIR, DATA_DIR
        self.raw_root = tmp_path / "raw_videos"
        self.raw_root.mkdir()
        self.clips_root = tmp_path / "clips"
        self.clips_root.mkdir()
        self.reports_root = tmp_path / "reports"
        self.reports_root.mkdir()
        self.data_root = tmp_path / "data"
        self.data_root.mkdir()

        monkeypatch.setattr("app.config.RAW_VIDEOS_DIR", self.raw_root)
        monkeypatch.setattr("app.config.CLIPS_DIR", self.clips_root)
        monkeypatch.setattr("app.config.REPORTS_DIR", self.reports_root)
        monkeypatch.setattr("app.config.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.storage_service.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.storage_service._REGISTRY_PATH", self.data_root / "video_registry.json")
        monkeypatch.setattr("app.config.RAW_VIDEOS_DIR", self.raw_root)
        monkeypatch.setattr("app.config.CLIPS_DIR", self.clips_root)
        monkeypatch.setattr("app.config.REPORTS_DIR", self.reports_root)
        monkeypatch.setattr("app.config.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.storage_service.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.storage_service._REGISTRY_PATH", self.data_root / "video_registry.json")

        self.video_id = "cleanup_vid"
        self.video_path = self.raw_root / f"{self.video_id}.mp4"
        _make_small_video(self.video_path)

        reg_path = self.data_root / "video_registry.json"
        reg_path.write_text(json.dumps({self.video_id: {"raw_path": str(self.video_path), "filename": "test.mp4"}}))

        from app.main import app
        self.client = TestClient(app)

    @pytest.mark.asyncio
    async def test_upload_no_raw_path(self):
        # Use TestClient's upload mechanism
        with open(self.video_path, "rb") as f:
            resp = self.client.post("/api/v1/videos/upload", files={"file": ("test.mp4", f, "video/mp4")})
        data = resp.json()
        assert "raw_path" not in data, f"raw_path found: {data.get('raw_path')}"
        assert "source_url" in data
        assert data["source_url"].startswith("/api/v1/videos/")

    def test_report_no_json_path_or_md_path(self):
        _write_report_md(self.video_id, self.reports_root, "# Report")
        _write_report_json(self.video_id, self.reports_root, {"key": "val"})
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/report")
        data = resp.json()
        assert "json_path" not in data
        assert "md_path" not in data
        assert "markdown_url" in data
        assert "json_url" in data
        assert "markdown" in data




class TestCandidatesEndpoint:

    @pytest.fixture(autouse=True)
    def _setup(self, tmp_path, monkeypatch):
        from app.config import RAW_VIDEOS_DIR, CLIPS_DIR, REPORTS_DIR, DATA_DIR
        self.raw_root = tmp_path / "raw_videos"
        self.raw_root.mkdir()
        self.clips_root = tmp_path / "clips"
        self.clips_root.mkdir()
        self.reports_root = tmp_path / "reports"
        self.reports_root.mkdir()
        self.data_root = tmp_path / "data"
        self.data_root.mkdir()

        monkeypatch.setattr("app.config.RAW_VIDEOS_DIR", self.raw_root)
        monkeypatch.setattr("app.config.CLIPS_DIR", self.clips_root)
        monkeypatch.setattr("app.config.REPORTS_DIR", self.reports_root)
        monkeypatch.setattr("app.config.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.storage_service.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.storage_service._REGISTRY_PATH", self.data_root / "video_registry.json")
        monkeypatch.setattr("app.services.video_result_service.RAW_VIDEOS_DIR", self.raw_root)
        monkeypatch.setattr("app.services.video_result_service.CLIPS_DIR", self.clips_root)
        monkeypatch.setattr("app.services.video_result_service.REPORTS_DIR", self.reports_root)
        monkeypatch.setattr("app.services.video_result_service.DATA_DIR", self.data_root)
        monkeypatch.setattr("app.services.task_store._DB_PATH", self.data_root / "app.db")
        from app.services import task_store; task_store.close_connection(); task_store.init_db()

        self.video_id = "cand_test_vid"
        self.video_path = self.raw_root / f"{self.video_id}.mp4"
        _make_small_video(self.video_path)
        reg_path = self.data_root / "video_registry.json"
        reg_path.write_text(json.dumps({self.video_id: {"raw_path": str(self.video_path), "filename": "test.mp4"}}))

        from app.main import app
        self.client = TestClient(app)

    def _write_candidates(self, video_id, data):
        d = self.reports_root / video_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "highlight_candidates.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def test_candidates_endpoint_returns_json(self):
        self._write_candidates(self.video_id, {
            "schema_version": 1, "video_id": self.video_id, "duration": 30.0,
            "generated_at": "2026-06-20T12:00:00Z", "candidates": [],
        })
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/reports/candidates")
        assert resp.status_code == 200
        assert "application/json" in resp.headers.get("content-type", "")

    def test_candidates_endpoint_not_found(self):
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/reports/candidates")
        assert resp.status_code == 404

    def test_candidates_endpoint_unknown_video(self):
        resp = self.client.get("/api/v1/videos/does_not_exist/reports/candidates")
        assert resp.status_code == 404

    def test_candidates_no_absolute_path(self):
        self._write_candidates(self.video_id, {
            "schema_version": 1, "video_id": self.video_id, "duration": 30.0,
            "generated_at": "2026-06-20T12:00:00Z", "candidates": [],
        })
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/reports/candidates")
        body = resp.text
        assert "D:\\\\" not in body
        assert "C:\\\\" not in body

    def test_result_includes_candidates_url_when_exists(self):
        self._write_candidates(self.video_id, {
            "schema_version": 1, "video_id": self.video_id, "duration": 30.0,
            "generated_at": "2026-06-20T12:00:00Z", "candidates": [],
        })
        _write_report_json(self.video_id, self.reports_root, {"video_id": self.video_id})
        _write_report_md(self.video_id, self.reports_root, "# test")
        _write_metadata(self.video_id, self.reports_root, {"duration": 1.0})
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        data = resp.json()
        assert data["report"]["candidates_url"] == f"/api/v1/videos/{self.video_id}/reports/candidates"

    def test_result_candidates_url_null_when_not_exists(self):
        _write_report_json(self.video_id, self.reports_root, {"video_id": self.video_id})
        _write_report_md(self.video_id, self.reports_root, "# test")
        _write_metadata(self.video_id, self.reports_root, {"duration": 1.0})
        resp = self.client.get(f"/api/v1/videos/{self.video_id}/result")
        data = resp.json()
        assert data["report"]["candidates_url"] is None

    def test_path_traversal_blocked(self):
        self._write_candidates(self.video_id, {
            "schema_version": 1, "video_id": self.video_id, "candidates": [],
        })
        resp = self.client.get("/api/v1/videos/../../reports/candidates")
        assert resp.status_code in (404, 422)
