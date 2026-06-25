"""Tests for TOOL_REGISTRY — validates all registered tools exist and are callable."""
from app.agent.tools import TOOL_REGISTRY


class TestToolRegistry:
    """Verify TOOL_REGISTRY is a dict with all expected tool entries."""

    EXPECTED_KEYS = [
        "metadata",
        "extract_frames",
        "detect_scenes",
        "detect_objects",
        "track_objects",
        "transcribe",
        "recommend_highlights",
        "export_clips",
        "generate_report",
    ]

    def test_registry_is_dict(self):
        assert isinstance(TOOL_REGISTRY, dict)

    def test_all_expected_keys_present(self):
        for key in self.EXPECTED_KEYS:
            assert key in TOOL_REGISTRY, f"Missing key: {key}"

    def test_no_unexpected_keys(self):
        # Only the expected tools should be registered
        assert set(TOOL_REGISTRY.keys()) == set(self.EXPECTED_KEYS)

    def test_all_values_are_callable(self):
        for key, val in TOOL_REGISTRY.items():
            assert callable(val), f"Tool '{key}' is not callable, got {type(val)}"

    def test_registry_size(self):
        assert len(TOOL_REGISTRY) == 9
