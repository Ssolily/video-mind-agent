"""Tests for VideoAnalysisState dataclass."""
from app.agent.state import VideoAnalysisState


class TestVideoAnalysisState:
    def test_create_default_state(self):
        state = VideoAnalysisState()
        assert state.video_id == ""
        assert state.video_path == ""
        assert state.user_goal == ""
        assert state.steps == []

    def test_create_with_values(self):
        state = VideoAnalysisState(
            video_id="abc123",
            video_path="/tmp/video.mp4",
            user_goal="detect objects",
        )
        assert state.video_id == "abc123"
        assert state.video_path == "/tmp/video.mp4"
        assert state.user_goal == "detect objects"

    def test_add_step_increases_length(self):
        state = VideoAnalysisState()
        state.add_step("metadata", "ok")
        assert len(state.steps) == 1
        state.add_step("detect_scenes", "ok", detail="found 3 scenes")
        assert len(state.steps) == 2

    def test_step_contains_expected_fields(self):
        state = VideoAnalysisState()
        state.add_step("metadata", "ok")
        step = state.steps[0]
        assert step["step"] == "metadata"
        assert step["status"] == "ok"
        # detail defaults to empty string
        assert "detail" in step

    def test_step_detail(self):
        state = VideoAnalysisState()
        state.add_step("extract_frames", "ok", detail="42 frames")
        step = state.steps[0]
        assert step["detail"] == "42 frames"

    def test_step_error(self):
        state = VideoAnalysisState()
        state.add_step("detect_objects", "error", detail="model not loaded")
        step = state.steps[0]
        assert step["status"] == "error"
