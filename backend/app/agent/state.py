from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VideoAnalysisState:
    video_id: str = ""
    video_path: str = ""
    user_goal: str = ""

    metadata: Optional[dict] = None
    frames: Optional[list[dict]] = None
    scenes: Optional[list[dict]] = None
    detections: Optional[list[dict]] = None
    tracks: Optional[list[dict]] = None
    subtitles: Optional[list[dict]] = None
    highlights: Optional[list[dict]] = None
    report: Optional[dict] = None
    clips: Optional[dict] = None

    steps: list[dict] = field(default_factory=list)

    def add_step(self, name: str, status: str, detail: str = "") -> None:
        self.steps.append({"step": name, "status": status, "detail": detail})
