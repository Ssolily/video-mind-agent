/// <reference types="vite/client" />

/** Unified video analysis task status matching the backend Pydantic model. */
export type VideoTaskStatus =
  | "uploaded"
  | "pending"
  | "running"
  | "success"
  | "completed_with_errors"
  | "failed";

/** A single scoring dimension in score_breakdown. */
export interface ScoreComponent {
  raw: number;
  weight: number;
  weighted: number;
}

/** score_breakdown mapping dimension names to ScoreComponent. */
export interface HighlightScoreBreakdown {
  [dimension: string]: ScoreComponent;
}

/** A recommended highlight segment from the backend Result API. */
export interface HighlightResult {
  id: string;
  start_time: number;
  end_time: number;
  duration: number;
  score: number;
  base_score: number;
  selection_score: number;
  overlap_penalty: number;
  score_breakdown: HighlightScoreBreakdown;
  reason: string[];
}

/** An exported highlight clip accessible via the media streaming API. */
export interface ClipResult {
  id: string;
  url: string;
  start_time: number | null;
  end_time: number | null;
  duration: number | null;
  highlight_id: string | null;
  size_bytes: number | null;
}

/** URLs to generated reports. */
export interface ReportLinks {
  markdown_url: string | null;
  json_url: string | null;
  candidates_url: string | null;
}

/** Unified result for a video analysis task (GET /api/v1/videos/{id}/result). */
export interface VideoResult {
  video_id: string;
  status: VideoTaskStatus;
  duration: number | null;
  source_url: string | null;
  highlights: HighlightResult[];
  clips: ClipResult[];
  report: ReportLinks;
  error: string | null;
  warnings: string[];
}
