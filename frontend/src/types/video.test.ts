import { describe, it, expect } from "vitest";
import type {
  VideoTaskStatus,
  ScoreComponent,
  HighlightScoreBreakdown,
  HighlightResult,
  ClipResult,
  ReportLinks,
  VideoResult,
} from "./video";

describe("VideoTaskStatus type shape", () => {
  it("accepts all valid status values", () => {
    const statuses: VideoTaskStatus[] = [
      "uploaded",
      "pending",
      "running",
      "success",
      "completed_with_errors",
      "failed",
    ];
    expect(statuses).toHaveLength(6);
  });
});

describe("ScoreComponent", () => {
  it("can represent a valid component", () => {
    const c: ScoreComponent = { raw: 0.5, weight: 0.25, weighted: 0.125 };
    expect(c.raw).toBe(0.5);
    expect(c.weight).toBe(0.25);
    expect(c.weighted).toBe(0.125);
  });
});

describe("HighlightScoreBreakdown", () => {
  it("accepts multiple dimensions", () => {
    const sb: HighlightScoreBreakdown = {
      object: { raw: 0.5, weight: 0.25, weighted: 0.125 },
      motion: { raw: 0.3, weight: 0.2, weighted: 0.06 },
    };
    expect(Object.keys(sb)).toHaveLength(2);
  });
});

describe("HighlightResult", () => {
  it("holds all required fields", () => {
    const h: HighlightResult = {
      id: "hl_0001",
      start_time: 10,
      end_time: 30,
      duration: 20,
      score: 0.5,
      base_score: 0.5,
      selection_score: 0.5,
      overlap_penalty: 0,
      score_breakdown: {},
      reason: ["test"],
    };
    expect(h.score).toBe(h.selection_score);
    expect(Array.isArray(h.reason)).toBe(true);
  });
});

describe("ClipResult", () => {
  it("nullable fields work", () => {
    const c: ClipResult = {
      id: "clip_001",
      url: "/api/v1/videos/abc/clips/clip_001",
      start_time: null,
      end_time: null,
      duration: null,
      highlight_id: null,
      size_bytes: null,
    };
    expect(c.start_time).toBeNull();
  });
});

describe("VideoResult", () => {
  it("holds a complete result", () => {
    const r: VideoResult = {
      video_id: "abc",
      status: "success",
      duration: 88,
      source_url: "/api/v1/videos/abc/source",
      highlights: [],
      clips: [],
      report: { markdown_url: null, json_url: null, candidates_url: null },
      error: null,
      warnings: [],
    };
    expect(r.video_id).toBe("abc");
    expect(r.highlights).toEqual([]);
  });
});
