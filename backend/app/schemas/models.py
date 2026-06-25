"""Pydantic response models for the Result API.

All models are designed to:
- Never expose local filesystem paths in API responses
- Be fully JSON-serializable (no NaN, Infinity, or datetime objects)
- Support backward-compatible field population from historical data
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ScoreComponentResponse(BaseModel):
    """A single scoring dimension's breakdown."""

    raw: float = 0.0
    weight: float = 0.0
    weighted: float = 0.0


class HighlightResultResponse(BaseModel):
    """A recommended highlight segment."""

    id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration: float = 0.0
    score: float = 0.0
    base_score: float = 0.0
    selection_score: float = 0.0
    overlap_penalty: float = 0.0
    score_breakdown: dict[str, ScoreComponentResponse] = Field(default_factory=dict)
    reason: list[str] = Field(default_factory=list)


class ClipResultResponse(BaseModel):
    """A single exported highlight clip."""

    id: str = ""
    url: str = ""
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    highlight_id: Optional[str] = None
    size_bytes: Optional[int] = None


class ReportLinksResponse(BaseModel):
    """URLs to the generated reports and artifacts."""

    markdown_url: Optional[str] = None
    json_url: Optional[str] = None
    candidates_url: Optional[str] = None


class VideoResultResponse(BaseModel):
    """Unified result for a video analysis task.

    Used by ``GET /api/v1/videos/{video_id}/result``.
    """

    video_id: str = ""
    status: str = "uploaded"
    duration: Optional[float] = None
    source_url: Optional[str] = None

    highlights: list[HighlightResultResponse] = Field(default_factory=list)
    clips: list[ClipResultResponse] = Field(default_factory=list)

    report: ReportLinksResponse = Field(default_factory=ReportLinksResponse)

    error: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
