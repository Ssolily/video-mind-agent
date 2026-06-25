import { describe, it, expect } from "vitest";
import { findClipForHighlight, findHighlightForClip, DEFAULT_CLIP_MATCH_TOLERANCE } from "./clipMatching";
import type { HighlightResult, ClipResult } from "../types/video";

function hl(id: string, start_time: number, end_time: number): HighlightResult {
  return {
    id, start_time, end_time,
    duration: end_time - start_time,
    score: 0.5, base_score: 0.5, selection_score: 0.5,
    overlap_penalty: 0,
    score_breakdown: {},
    reason: [],
  };
}

function clip(id: string, highlight_id: string | null, start_time: number | null, end_time: number | null): ClipResult {
  return {
    id,
    url: "/api/v1/videos/test/clips/" + id,
    start_time, end_time,
    duration: start_time != null && end_time != null ? end_time - start_time : null,
    highlight_id,
    size_bytes: 1000,
  };
}

describe("findClipForHighlight", () => {
  it("matches by explicit highlight_id", () => {
    const h = hl("hl_001", 10, 30);
    const clips = [clip("c001", "hl_001", 10, 30), clip("c002", "hl_002", 40, 60)];
    const result = findClipForHighlight(h, clips);
    expect(result).not.toBeNull();
    expect(result!.id).toBe("c001");
  });

  it("matches by time when no explicit id", () => {
    const h = hl("hl_001", 10, 30);
    const clips = [clip("c001", null, 10, 30)];
    const result = findClipForHighlight(h, clips);
    expect(result).not.toBeNull();
    expect(result!.id).toBe("c001");
  });

  it("returns null when clips is empty", () => {
    const h = hl("hl_001", 10, 30);
    expect(findClipForHighlight(h, [])).toBeNull();
  });

  it("returns null when no match", () => {
    const h = hl("hl_001", 10, 30);
    const clips = [clip("c001", null, 50, 70)];
    expect(findClipForHighlight(h, clips)).toBeNull();
  });

  it("does not use index fallback", () => {
    const h = hl("hl_001", 10, 30);
    const clips = [clip("c001", null, 50, 70), clip("c002", null, 80, 100)];
    expect(findClipForHighlight(h, clips)).toBeNull();
  });

  it("selects best time match among multiple candidates", () => {
    const h = hl("hl_001", 10, 30);
    const clips = [
      clip("c01", null, 10, 30.05),
      clip("c02", null, 10, 30.15),
      clip("c03", null, 9.9, 30),
    ];
    const result = findClipForHighlight(h, clips);
    expect(result).not.toBeNull();
    expect(result!.id).toBe("c01");
  });

  it("default tolerance is 0.1", () => {
    expect(DEFAULT_CLIP_MATCH_TOLERANCE).toBe(0.1);
  });
});

describe("findHighlightForClip", () => {
  it("matches by explicit highlight_id", () => {
    const c = clip("c001", "hl_001", 10, 30);
    const highlights = [hl("hl_001", 10, 30), hl("hl_002", 40, 60)];
    const result = findHighlightForClip(c, highlights);
    expect(result).not.toBeNull();
    expect(result!.id).toBe("hl_001");
  });

  it("matches by time when no explicit id", () => {
    const c = clip("c001", null, 10, 30);
    const highlights = [hl("hl_001", 10, 30)];
    const result = findHighlightForClip(c, highlights);
    expect(result).not.toBeNull();
    expect(result!.id).toBe("hl_001");
  });

  it("does not use index fallback", () => {
    const c = clip("c001", null, 50, 70);
    const highlights = [hl("hl_001", 10, 30)];
    expect(findHighlightForClip(c, highlights)).toBeNull();
  });

  it("returns null when no match", () => {
    const c = clip("c001", "hl_999", null, null);
    const highlights = [hl("hl_001", 10, 30)];
    expect(findHighlightForClip(c, highlights)).toBeNull();
  });
});
