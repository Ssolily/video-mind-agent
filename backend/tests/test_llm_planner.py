"""Tests for LLM planner integration — call_llm_planner and build_plan LLM path."""

import json
from unittest.mock import patch, MagicMock

from app.agent.planner import build_plan
from app.agent.llm_client import call_llm_planner, _build_payload


# ── Helper: create a context-manager-compatible mock response ──


def _mock_response(content: str):
    """Return a MagicMock that supports ``with resp:`` context manager."""
    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = mock_resp
    payload = {"choices": [{"message": {"content": content}}]}
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    return mock_resp


class TestCallLlmPlanner:
    """Tests for the DeepSeek API client."""

    def test_build_payload_contains_goal(self):
        payload = _build_payload("分析视频场景")
        assert payload["model"] == "deepseek-v4-flash"
        assert payload["temperature"] == 0.1
        assert "分析视频场景" in payload["messages"][1]["content"]

    def test_call_llm_returns_none_on_empty_key(self):
        with patch("app.agent.llm_client.DEEPSEEK_API_KEY", ""):
            result = call_llm_planner("metadata")
            assert result is None

    def test_call_llm_returns_none_on_invalid_key(self):
        with patch("app.agent.llm_client.DEEPSEEK_API_KEY", "invalid"):
            result = call_llm_planner("test")
            assert result is None

    def test_call_llm_parses_json_array(self):
        resp = _mock_response('["metadata", "detect_scenes"]')
        with patch("app.agent.llm_client.DEEPSEEK_API_KEY", "sk-valid-key"):
            with patch("urllib.request.urlopen", return_value=resp):
                result = call_llm_planner("detect scenes")
                assert result == ["metadata", "detect_scenes"]

    def test_call_llm_strips_markdown_fences(self):
        content = "```json\n[\"metadata\"]\n```"
        resp = _mock_response(content)
        with patch("app.agent.llm_client.DEEPSEEK_API_KEY", "sk-valid-key"):
            with patch("urllib.request.urlopen", return_value=resp):
                result = call_llm_planner("metadata")
                assert result == ["metadata"]

    def test_call_llm_returns_none_on_invalid_json(self):
        resp = _mock_response("not json")
        with patch("app.agent.llm_client.DEEPSEEK_API_KEY", "sk-valid-key"):
            with patch("urllib.request.urlopen", return_value=resp):
                result = call_llm_planner("metadata")
                assert result is None

    def test_call_llm_returns_none_on_network_error(self):
        with patch("app.agent.llm_client.DEEPSEEK_API_KEY", "sk-valid-key"):
            with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
                result = call_llm_planner("metadata")
                assert result is None


class TestBuildPlanLlmPath:
    """Tests that build_plan uses LLM result when available."""

    # Patch at the source module (llm_client), not planner
    PATCH_TARGET = "app.agent.llm_client.call_llm_planner"

    def test_build_plan_uses_llm_result(self):
        with patch(self.PATCH_TARGET, return_value=["metadata"]):
            result = build_plan("随意输入，LLM 决定只做 metadata")
            assert result == ["metadata"]

    def test_build_plan_uses_llm_complex_plan(self):
        plan = ["metadata", "extract_frames", "detect_objects", "track_objects"]
        with patch(self.PATCH_TARGET, return_value=plan):
            result = build_plan("detect and track objects")
            assert result == plan

    def test_build_plan_fallback_on_none(self):
        with patch(self.PATCH_TARGET, return_value=None):
            result = build_plan("report")
            assert "generate_report" in result

    def test_build_plan_fallback_on_invalid_tool(self):
        with patch(self.PATCH_TARGET, return_value=["metadata", "do_nothing"]):
            result = build_plan("test")
            assert "generate_report" in result

    def test_build_plan_fallback_on_invalid_dependency(self):
        with patch(self.PATCH_TARGET,
                   return_value=["detect_objects", "extract_frames"]):
            result = build_plan("test")
            assert "generate_report" in result
