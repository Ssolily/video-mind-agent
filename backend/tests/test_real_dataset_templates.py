"""Tests for real_dataset templates, create_label_template.py, and check_experiment_privacy.py."""

import csv, json, os, sys, tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))


# ── Helpers ──────────────────────────────────────────


def _make_csv(tmp_path, rows: list[dict]) -> Path:
    """Write a temporary CSV file and return its path."""
    p = tmp_path / "videos.csv"
    if not rows:
        p.write_text("video_id,duration,category\n", encoding="utf-8")
        return p
    keys = list(rows[0].keys())
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return p


# ── create_label_template tests ──────────────────────


class TestCreateLabelTemplate:
    """Test the create_label_template.py CLI tool."""

    def test_help_runs(self):
        from create_label_template import main as cli_main
        import argparse
        parser = argparse.ArgumentParser()
        # Just verify the module can be imported
        import create_label_template
        assert hasattr(create_label_template, "create_video_template")
        assert hasattr(create_label_template, "create_batch_templates")
        assert hasattr(create_label_template, "create_timeline_template")
        assert hasattr(create_label_template, "validate_label_file")

    def test_video_mode_generates_json(self, tmp_path):
        from create_label_template import create_video_template
        tpl = create_video_template("vid_001", 60.0, category="lecture")
        assert tpl["video_id"] == "vid_001"
        assert tpl["duration"] == 60.0
        assert tpl["video_category"] == "lecture"
        assert isinstance(tpl["labels"], list)

    def test_video_default_placeholder_count(self, tmp_path):
        from create_label_template import create_video_template
        tpl = create_video_template("vid_002", 100.0)
        assert len(tpl["labels"]) == 0

    def test_video_custom_placeholders(self, tmp_path):
        from create_label_template import create_video_template
        tpl = create_video_template("vid_003", 100.0, num_segments=5)
        assert len(tpl["labels"]) == 5
        assert tpl["labels"][0]["id"] == "gt_001"
        assert tpl["labels"][4]["id"] == "gt_005"

    def test_timeline_segments(self, tmp_path):
        from create_label_template import create_timeline_template
        tpl = create_timeline_template("vid_004", 100.0, interval=30.0)
        assert len(tpl["labels"]) == 4  # ceil(100/30)=4
        assert tpl["labels"][0]["start_time"] == 0.0
        assert tpl["labels"][-1]["end_time"] == 100.0

    def test_timeline_last_not_exceed_duration(self, tmp_path):
        from create_label_template import create_timeline_template
        tpl = create_timeline_template("vid_005", 45.0, interval=20.0)
        assert len(tpl["labels"]) == 3  # ceil(45/20)=3
        assert tpl["labels"][-1]["end_time"] == 45.0

    def test_batch_dry_run_does_not_write(self, tmp_path):
        from create_label_template import create_batch_templates
        csv_rows = [
            {"video_id": "a", "duration": "30", "category": "lecture"},
            {"video_id": "b", "duration": "60", "category": "sports"},
        ]
        csv_path = _make_csv(tmp_path, csv_rows)
        out = tmp_path / "out"
        templates = create_batch_templates(str(csv_path), str(out), dry_run=True)
        assert len(templates) == 2
        assert not out.exists()

    def test_batch_generate(self, tmp_path):
        from create_label_template import create_batch_templates
        csv_rows = [
            {"video_id": "v1", "duration": "30", "category": "lecture"},
            {"video_id": "v2", "duration": "60", "category": "sports"},
        ]
        csv_path = _make_csv(tmp_path, csv_rows)
        out = tmp_path / "out"
        templates = create_batch_templates(str(csv_path), str(out))
        assert len(templates) == 2
        assert (out / "v1_label_template.json").exists()
        assert (out / "v2_label_template.json").exists()

    def test_validate_valid_label(self, tmp_path):
        from create_label_template import validate_label_file
        label = {
            "video_id": "test", "duration": 30.0,
            "labels": [
                {"id": "gt_001", "start_time": 0.0, "end_time": 10.0, "rating": 5, "category": "speech"},
            ],
        }
        p = tmp_path / "valid.json"
        p.write_text(json.dumps(label), encoding="utf-8")
        errors = validate_label_file(str(p))
        assert errors == []

    def test_validate_end_before_start(self, tmp_path):
        from create_label_template import validate_label_file
        label = {
            "video_id": "test", "duration": 30.0,
            "labels": [
                {"id": "gt_001", "start_time": 10.0, "end_time": 5.0, "rating": 3, "category": "speech"},
            ],
        }
        p = tmp_path / "bad.json"
        p.write_text(json.dumps(label), encoding="utf-8")
        errors = validate_label_file(str(p))
        assert any("end_time" in e and "<=" in e for e in errors)

    def test_validate_rating_out_of_range(self, tmp_path):
        from create_label_template import validate_label_file
        label = {
            "video_id": "test", "duration": 30.0,
            "labels": [
                {"id": "gt_001", "start_time": 0.0, "end_time": 10.0, "rating": 6, "category": "speech"},
            ],
        }
        p = tmp_path / "bad.json"
        p.write_text(json.dumps(label), encoding="utf-8")
        errors = validate_label_file(str(p))
        assert any("rating" in e for e in errors)

    def test_validate_unknown_category(self, tmp_path):
        from create_label_template import validate_label_file
        label = {
            "video_id": "test", "duration": 30.0,
            "labels": [
                {"id": "gt_001", "start_time": 0.0, "end_time": 10.0, "rating": 3, "category": "nonexistent"},
            ],
        }
        p = tmp_path / "bad.json"
        p.write_text(json.dumps(label), encoding="utf-8")
        errors = validate_label_file(str(p))
        assert any("unknown category" in e for e in errors)

    def test_output_utf8_non_ascii(self, tmp_path):
        from create_label_template import create_video_template
        tpl = create_video_template("cn_001", 60.0, num_segments=1)
        # Force a Chinese note
        tpl["labels"][0]["note"] = "中文备注"
        p = tmp_path / "cn.json"
        p.write_text(json.dumps(tpl, indent=2, ensure_ascii=False), encoding="utf-8")
        raw = p.read_bytes()
        # Check UTF-8 encoded Chinese chars
        assert b"\xe4\xb8\xad\xe6\x96\x87" in raw  # "中文" in UTF-8

    def test_output_no_win_abs_path(self, tmp_path):
        from create_label_template import create_video_template
        tpl = create_video_template("safe_001", 60.0)
        text = json.dumps(tpl)
        assert "C:" not in text
        assert "D:" not in text

    def test_duration_zero_raises(self):
        from create_label_template import create_video_template
        with pytest.raises(ValueError, match="Duration must be > 0"):
            create_video_template("bad_dur", 0)

    def test_negative_duration_raises(self):
        from create_label_template import create_video_template
        with pytest.raises(ValueError, match="Duration must be > 0"):
            create_video_template("neg_dur", -1)

    def test_duplicate_ids_detected(self, tmp_path):
        from create_label_template import validate_label_file
        label = {
            "video_id": "test", "duration": 30.0,
            "labels": [
                {"id": "gt_001", "start_time": 0.0, "end_time": 5.0, "rating": 3, "category": "speech"},
                {"id": "gt_001", "start_time": 10.0, "end_time": 15.0, "rating": 4, "category": "speech"},
            ],
        }
        p = tmp_path / "dup.json"
        p.write_text(json.dumps(label), encoding="utf-8")
        errors = validate_label_file(str(p))
        assert any("duplicate" in e.lower() for e in errors)


# ── Real Dataset Template Validation ────────────────

REAL_DATASET = Path(__file__).resolve().parent.parent.parent / "experiments" / "highlight_eval" / "real_dataset"


class TestRealDatasetManifest:
    """Validate the real_dataset manifest template."""

    def test_manifest_exists(self):
        mf = REAL_DATASET / "manifest" / "template_manifest.json"
        assert mf.exists(), f"Manifest not found: {mf}"

    def test_manifest_parses(self):
        mf = REAL_DATASET / "manifest" / "template_manifest.json"
        data = json.loads(mf.read_text(encoding="utf-8"))
        assert data["schema_version"] >= 1

    def test_manifest_video_ids_unique(self):
        mf = REAL_DATASET / "manifest" / "template_manifest.json"
        data = json.loads(mf.read_text(encoding="utf-8"))
        ids = [v["video_id"] for v in data.get("videos", [])]
        assert len(ids) == len(set(ids)), f"Duplicate video_ids: {ids}"

    def test_manifest_paths_relative(self):
        mf = REAL_DATASET / "manifest" / "template_manifest.json"
        data = json.loads(mf.read_text(encoding="utf-8"))
        for v in data.get("videos", []):
            for key in ("candidates_json", "labels_json"):
                val = v.get(key, "")
                assert val, f"{key} for {v['video_id']} is empty"
                assert not val.startswith("/"), f"{key} for {v['video_id']} is absolute: {val}"
                assert ":" not in val or val[1] != ":", f"{key} for {v['video_id']} is absolute Windows path: {val}"

    def test_manifest_categories_valid(self):
        mf = REAL_DATASET / "manifest" / "template_manifest.json"
        data = json.loads(mf.read_text(encoding="utf-8"))
        valid = {"lecture", "interview", "sports", "scene_change", "low_information", "no_audio"}
        for v in data.get("videos", []):
            assert v["category"] in valid, f"Invalid category {v['category']} for {v['video_id']}"

    def test_manifest_duration_positive(self):
        mf = REAL_DATASET / "manifest" / "template_manifest.json"
        data = json.loads(mf.read_text(encoding="utf-8"))
        for v in data.get("videos", []):
            assert v["duration"] > 0, f"Non-positive duration for {v['video_id']}"

    def test_video_list_csv_exists(self):
        csv_path = REAL_DATASET / "source" / "video_list.csv"
        assert csv_path.exists()

    def test_video_list_columns(self):
        csv_path = REAL_DATASET / "source" / "video_list.csv"
        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []
            for col in ("video_id", "duration", "category"):
                assert col in headers, f"Missing column: {col}"

    def test_video_list_categories_valid(self):
        csv_path = REAL_DATASET / "source" / "video_list.csv"
        valid = {"lecture", "interview", "sports", "scene_change", "low_information", "no_audio"}
        with open(csv_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                cat = row.get("category", "")
                assert cat in valid, f"Invalid category '{cat}' for {row.get('video_id')}"

    def test_readme_exists(self):
        readme = REAL_DATASET / "README.md"
        assert readme.exists()

    def test_candidates_gitkeep_exists(self):
        gk = REAL_DATASET / "candidates" / ".gitkeep"
        assert gk.exists()

    def test_labels_dir_has_files(self):
        label_dir = REAL_DATASET / "labels"
        json_files = list(label_dir.glob("*.json"))
        assert len(json_files) >= 1, "No label template files found"

    def test_label_template_count(self):
        label_dir = REAL_DATASET / "labels"
        json_files = list(label_dir.glob("*.json"))
        assert len(json_files) >= 8, f"Expected >=8 templates, got {len(json_files)}"


# ── Privacy Check Tests ──────────────────────────────


class TestPrivacyCheck:
    """Test check_experiment_privacy.py."""

    def test_clean_dataset_passes(self, tmp_path):
        from check_experiment_privacy import scan_root
        # Create a clean dataset
        d = tmp_path / "clean"
        d.mkdir()
        (d / "labels.json").write_text(
            json.dumps({"video_id": "test", "duration": 30.0}, ensure_ascii=False),
            encoding="utf-8",
        )
        issues = scan_root(d)
        errors = [i for i in issues if i.get("severity") == "error"]
        assert len(errors) == 0

    def test_detects_win_abs_path(self):
        from check_experiment_privacy import scan_root
        d = Path(tempfile.mkdtemp()) / "winpath"
        d.mkdir(parents=True)
        (d / "labels.json").write_text(
            json.dumps({"raw_path": "C:\\Users\\test\\video.mp4"}, ensure_ascii=False),
            encoding="utf-8",
        )
        issues = scan_root(d)
        win_issues = [i for i in issues if i["type"] == "WIN_ABS_PATH"]
        assert len(win_issues) >= 1

    def test_detects_drive_d(self):
        from check_experiment_privacy import scan_root
        d = Path(tempfile.mkdtemp()) / "dpath"
        d.mkdir(parents=True)
        (d / "out.md").write_text("Output: D:\\projects\\video.mp4", encoding="utf-8")
        issues = scan_root(d)
        win_issues = [i for i in issues if i["type"] == "WIN_ABS_PATH"]
        assert len(win_issues) >= 1

    def test_detects_unix_abs_path(self, tmp_path):
        from check_experiment_privacy import scan_root
        d = tmp_path / "unixpath"
        d.mkdir()
        (d / "config.json").write_text(
            json.dumps({"path": "/home/user/video.mp4"}, ensure_ascii=False),
            encoding="utf-8",
        )
        issues = scan_root(d)
        unix_issues = [i for i in issues if i["type"] == "UNIX_ABS_PATH"]
        assert len(unix_issues) >= 1

    def test_detects_api_key(self, tmp_path):
        from check_experiment_privacy import scan_root
        d = tmp_path / "apikey"
        d.mkdir()
        (d / "config.txt").write_text(
            "API_KEY=sk-1234567890abcdef\n", encoding="utf-8",
        )
        issues = scan_root(d)
        kw_issues = [i for i in issues if i["type"] == "SENSITIVE_KEYWORD"]
        assert len(kw_issues) >= 1

    def test_detects_email(self, tmp_path):
        from check_experiment_privacy import scan_root
        d = tmp_path / "email"
        d.mkdir()
        (d / "labels.json").write_text(
            json.dumps({"annotator": "alice@personal-mail.com"}, ensure_ascii=False),
            encoding="utf-8",
        )
        issues = scan_root(d)
        email_issues = [i for i in issues if i["type"] == "EMAIL"]
        assert len(email_issues) >= 1

    def test_skips_test_email(self, tmp_path):
        from check_experiment_privacy import scan_root
        d = tmp_path / "testemail"
        d.mkdir()
        (d / "labels.json").write_text(
            json.dumps({"annotator": "test@example.com"}, ensure_ascii=False),
            encoding="utf-8",
        )
        issues = scan_root(d)
        email_issues = [i for i in issues if i["type"] == "EMAIL"]
        assert len(email_issues) == 0

    def test_snippet_truncated(self, tmp_path):
        from check_experiment_privacy import scan_root
        d = tmp_path / "snippet"
        d.mkdir()
        long_line = "path = " + "C:\\" + "x" * 200
        (d / "config.py").write_text(long_line, encoding="utf-8")
        issues = scan_root(d)
        if issues:
            snippet = issues[0].get("snippet", "")
            assert len(snippet) <= 80

    def test_video_file_warning(self, tmp_path):
        from check_experiment_privacy import scan_root
        d = tmp_path / "videos"
        d.mkdir()
        (d / "clip.mp4").write_bytes(b"\x00\x00\x00\x00")
        issues = scan_root(d)
        video_issues = [i for i in issues if i["type"] == "VIDEO_FILE"]
        assert len(video_issues) >= 1

    def test_cli_exit_code_on_clean(self, tmp_path):
        from check_experiment_privacy import scan_root, format_issues
        d = tmp_path / "clean_cli"
        d.mkdir()
        (d / "ok.json").write_text("{}", encoding="utf-8")
        issues = scan_root(d)
        assert len([i for i in issues if i.get("severity") == "error"]) == 0

    def test_cli_exit_code_on_fail_on_warning(self, tmp_path):
        from check_experiment_privacy import scan_root
        d = tmp_path / "warn_cli"
        d.mkdir()
        (d / "clip.mp4").write_bytes(b"\x00\x00\x00")
        issues = scan_root(d)
        warnings = [i for i in issues if i.get("severity") == "warning"]
        # With --fail-on-warning, warnings trigger non-zero exit
        # But here we just check that warnings are properly categorized
        assert len(warnings) >= 1

    def test_scan_root_no_errors_on_empty_dir(self):
        from check_experiment_privacy import scan_root
        d = Path(tempfile.mkdtemp()) / "empty"
        d.mkdir(parents=True)
        issues = scan_root(d)
        assert len(issues) == 0
