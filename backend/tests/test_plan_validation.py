"""Tests for plan validation (validate_plan) and executor plan rejection."""

from app.agent.planner import validate_plan
from app.agent.tools import TOOL_REGISTRY


class TestValidatePlan:
    """validate_plan — tool existence and dependency ordering."""

    def test_valid_full_pipeline(self):
        tools = [
            "metadata", "extract_frames", "detect_scenes",
            "detect_objects", "track_objects", "transcribe",
            "recommend_highlights", "export_clips", "generate_report",
        ]
        result = validate_plan(tools)
        assert result.valid is True
        assert result.errors == []

    def test_valid_minimal_plan(self):
        result = validate_plan(["metadata"])
        assert result.valid is True

    def test_unknown_tool_rejected(self):
        result = validate_plan(["metadata", "do_nothing"])
        assert result.valid is False
        assert any("do_nothing" in e for e in result.errors)

    def test_all_unknown_tools_rejected(self):
        result = validate_plan(["foo", "bar"])
        assert result.valid is False
        assert any("foo" in e for e in result.errors)
        assert any("bar" in e for e in result.errors)

    def test_duplicate_tool_rejected(self):
        tools = ["metadata", "extract_frames", "metadata"]
        result = validate_plan(tools)
        assert result.valid is False
        assert any("more than once" in e for e in result.errors)

    def test_dependency_order_violated(self):
        # detect_objects depends on extract_frames, put it before
        tools = ["metadata", "detect_objects", "extract_frames"]
        result = validate_plan(tools)
        assert result.valid is False
        assert any("must appear before" in e for e in result.errors)

    def test_missing_dependency_rejected(self):
        # recommend_highlights depends on detect_scenes which is absent
        tools = ["metadata", "extract_frames", "detect_objects",
                 "track_objects", "recommend_highlights"]
        result = validate_plan(tools)
        assert result.valid is False
        assert any("not in the plan" in e for e in result.errors)

    def test_empty_plan_valid(self):
        result = validate_plan([])
        assert result.valid is True

    def test_known_tool_names_all_valid(self):
        known = list(TOOL_REGISTRY.keys())
        result = validate_plan(known)
        # This might fail due to deps — just check no unknown-tool errors
        for e in result.errors:
            assert "not in TOOL_REGISTRY" not in e, f"unexpected: {e}"

    def test_generate_report_needs_highlights(self):
        # generate_report depends on recommend_highlights
        tools = ["metadata", "extract_frames", "detect_scenes",
                 "detect_objects", "track_objects", "transcribe",
                 "generate_report"]
        result = validate_plan(tools)
        assert result.valid is False
        assert any("recommend_highlights" in e for e in result.errors)
