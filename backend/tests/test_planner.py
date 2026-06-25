"""Tests for the rule-based planner (build_plan and _rule_based_plan).

``call_llm_planner`` is patched to return None so all tests exercise the
rule-based fallback path.
"""

from unittest.mock import patch

from app.agent.planner import build_plan, _rule_based_plan


# ── Patch target (call_llm_planner lives in llm_client, not planner) ──

_PATCH_TARGET = "app.agent.llm_client.call_llm_planner"


def _build_plan(user_goal: str):
    """Call build_plan with LLM patched to None (forces rule fallback)."""
    with patch(_PATCH_TARGET, return_value=None):
        return build_plan(user_goal)


class TestBuildPlan:
    """Verifies that build_plan falls back to rule-based when LLM is unavailable."""

    def test_empty_goal_returns_full_pipeline(self):
        tools = _build_plan("")
        assert len(tools) > 0
        assert "metadata" in tools

    def test_metadata_goal(self):
        tools = _build_plan("metadata")
        assert "metadata" in tools

    def test_metadata_chinese_goal(self):
        tools = _build_plan("基本信息")
        assert "metadata" in tools

    def test_report_goal_contains_generate_report(self):
        tools = _build_plan("报告")
        assert "generate_report" in tools

    def test_report_chinese_goal(self):
        tools = _build_plan("摘要")
        assert "generate_report" in tools

    def test_scene_goal(self):
        tools = _build_plan("场景")
        assert "detect_scenes" in tools

    def test_subtitle_goal_contains_transcribe(self):
        tools = _build_plan("字幕")
        assert "transcribe" in tools

    def test_object_detection_goal(self):
        tools = _build_plan("检测物体")
        assert "detect_objects" in tools
        assert "track_objects" in tools

    def test_highlight_goal(self):
        tools = _build_plan("推荐精彩片段")
        assert "recommend_highlights" in tools

    def test_unknown_goal_falls_back_to_full_pipeline(self):
        tools = _build_plan("some random gibberish that matches nothing")
        assert len(tools) >= 8
        assert "metadata" in tools
        assert "generate_report" in tools


class TestRuleBasedPlan:
    """Direct tests for the rule-based fallback (same as old build_plan)."""

    def test_empty_goal_returns_full_pipeline(self):
        tools = _rule_based_plan("")
        assert len(tools) > 0
        assert "metadata" in tools

    def test_metadata_goal(self):
        tools = _rule_based_plan("metadata")
        assert "metadata" in tools

    def test_metadata_chinese_goal(self):
        tools = _rule_based_plan("基本信息")
        assert "metadata" in tools

    def test_report_goal_contains_generate_report(self):
        tools = _rule_based_plan("报告")
        assert "generate_report" in tools

    def test_report_chinese_goal(self):
        tools = _rule_based_plan("摘要")
        assert "generate_report" in tools

    def test_scene_goal(self):
        tools = _rule_based_plan("场景")
        assert "detect_scenes" in tools

    def test_subtitle_goal_contains_transcribe(self):
        tools = _rule_based_plan("字幕")
        assert "transcribe" in tools

    def test_object_detection_goal(self):
        tools = _rule_based_plan("检测物体")
        assert "detect_objects" in tools
        assert "track_objects" in tools

    def test_highlight_goal(self):
        tools = _rule_based_plan("推荐精彩片段")
        assert "recommend_highlights" in tools

    def test_unknown_goal_falls_back_to_full_pipeline(self):
        tools = _rule_based_plan("some random gibberish that matches nothing")
        assert len(tools) >= 8
        assert "metadata" in tools
        assert "generate_report" in tools
