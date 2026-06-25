import { describe, it, expect } from "vitest";
import { normalizeHighlightRange, findActiveHighlight, highlightLeftPercent, highlightWidthPercent, playheadLeftPercent, xToTime } from "./highlightTimeline";
import type { HighlightResult } from "../types/video";

function makeHL(ov: Partial<HighlightResult> & { start_time: number; end_time: number }): HighlightResult {
  return { id: "hl_001", score: 0.5, base_score: 0.5, selection_score: 0.5, overlap_penalty: 0, duration: ov.end_time - ov.start_time, score_breakdown: {}, reason: [], ...ov };
}

describe("normalizeHighlightRange", () => {
  it("returns normalized range for valid input", () => {
    const r = normalizeHighlightRange({ start_time: 10, end_time: 30 }, 120);
    expect(r).toEqual({ startTime: 10, endTime: 30, duration: 20 });
  });
  it("clamps start_time to 0 when negative", () => {
    const r = normalizeHighlightRange({ start_time: -5, end_time: 20 }, 120);
    expect(r!.startTime).toBe(0);
  });
  it("clamps end_time to videoDuration when exceeds", () => {
    const r = normalizeHighlightRange({ start_time: 10, end_time: 200 }, 120);
    expect(r!.endTime).toBe(120);
  });
  it("returns null when end_time <= start_time", () => {
    expect(normalizeHighlightRange({ start_time: 30, end_time: 20 }, 120)).toBeNull();
    expect(normalizeHighlightRange({ start_time: 10, end_time: 10 }, 120)).toBeNull();
  });
  it("returns null when videoDuration is 0 or NaN", () => {
    expect(normalizeHighlightRange({ start_time: 0, end_time: 10 }, 0)).toBeNull();
    expect(normalizeHighlightRange({ start_time: 0, end_time: 10 }, NaN)).toBeNull();
  });
  it("returns null when start_time or end_time is Infinity", () => {
    expect(normalizeHighlightRange({ start_time: Infinity, end_time: 100 }, 120)).toBeNull();
    expect(normalizeHighlightRange({ start_time: 0, end_time: Infinity }, 120)).toBeNull();
  });
  it("returns null when start_time or end_time is NaN", () => {
    expect(normalizeHighlightRange({ start_time: NaN, end_time: 100 }, 120)).toBeNull();
    expect(normalizeHighlightRange({ start_time: 0, end_time: NaN }, 120)).toBeNull();
  });
});

describe("findActiveHighlight", () => {
  const dur = 120;
  it("returns the highlight whose interval contains currentTime", () => {
    const m = findActiveHighlight([makeHL({ id: "a", start_time: 10, end_time: 20 })], 15, dur);
    expect(m).not.toBeNull();
    expect(m!.id).toBe("a");
  });
  it("returns null when currentTime is outside all intervals", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 })];
    expect(findActiveHighlight(hls, 5, dur)).toBeNull();
    expect(findActiveHighlight(hls, 25, dur)).toBeNull();
  });
  it("returns null when currentTime equals end_time (half-open)", () => {
    expect(findActiveHighlight([makeHL({ id: "a", start_time: 10, end_time: 20 })], 20, dur)).toBeNull();
  });
  it("currentTime equal to start_time is active", () => {
    const m = findActiveHighlight([makeHL({ id: "a", start_time: 10, end_time: 20 })], 10, dur);
    expect(m!.id).toBe("a");
  });
  it("prefers selected highlight over higher score", () => {
    const m = findActiveHighlight([
      makeHL({ id: "low", start_time: 0, end_time: 100, selection_score: 0.3 }),
      makeHL({ id: "high", start_time: 0, end_time: 100, selection_score: 0.9 }),
    ], 30, dur, "low");
    expect(m!.id).toBe("low");
  });
  it("among non-selected, picks highest selection_score", () => {
    const m = findActiveHighlight([
      makeHL({ id: "low", start_time: 0, end_time: 100, selection_score: 0.3 }),
      makeHL({ id: "high", start_time: 0, end_time: 100, selection_score: 0.9 }),
    ], 30, dur);
    expect(m!.id).toBe("high");
  });
  it("among equal selection_score, picks earliest start_time", () => {
    const m = findActiveHighlight([
      makeHL({ id: "late", start_time: 30, end_time: 100, selection_score: 0.5 }),
      makeHL({ id: "early", start_time: 10, end_time: 100, selection_score: 0.5 }),
    ], 40, dur);
    expect(m!.id).toBe("early");
  });
  it("among equal start_time, picks earliest end_time", () => {
    const m = findActiveHighlight([
      makeHL({ id: "long", start_time: 10, end_time: 100, selection_score: 0.5 }),
      makeHL({ id: "short", start_time: 10, end_time: 50, selection_score: 0.5 }),
    ], 40, dur);
    expect(m!.id).toBe("short");
  });
  it("among all equal, picks id ascending", () => {
    const m = findActiveHighlight([
      makeHL({ id: "z", start_time: 10, end_time: 50, selection_score: 0.5 }),
      makeHL({ id: "a", start_time: 10, end_time: 50, selection_score: 0.5 }),
    ], 30, dur);
    expect(m!.id).toBe("a");
  });
  it("returns null for empty array", () => {
    expect(findActiveHighlight([], 30, dur)).toBeNull();
  });
  it("handles NaN currentTime", () => {
    expect(findActiveHighlight([makeHL({ id: "a", start_time: 10, end_time: 20 })], NaN, dur)).toBeNull();
  });
  it("handles invalid highlights gracefully", () => {
    const m = findActiveHighlight([
      makeHL({ id: "inv", start_time: 20, end_time: 10 }),
      makeHL({ id: "val", start_time: 10, end_time: 20 }),
    ], 15, dur);
    expect(m!.id).toBe("val");
  });
  it("NaN selection_score treated as lowest", () => {
    const m = findActiveHighlight([
      makeHL({ id: "nan", start_time: 0, end_time: 100, selection_score: NaN }),
      makeHL({ id: "good", start_time: 0, end_time: 100, selection_score: 0.5 }),
    ], 30, dur);
    expect(m!.id).toBe("good");
  });
});

describe("highlightLeftPercent", () => {
  it("returns correct percentage", () => {
    expect(highlightLeftPercent({ startTime: 30, endTime: 60, duration: 30 }, 120)).toBeCloseTo(25, 1);
  });
  it("returns 0 for start at 0", () => {
    expect(highlightLeftPercent({ startTime: 0, endTime: 60, duration: 60 }, 120)).toBe(0);
  });
});

describe("highlightWidthPercent", () => {
  it("returns correct percentage", () => {
    expect(highlightWidthPercent({ startTime: 30, endTime: 60, duration: 30 }, 120)).toBeCloseTo(25, 1);
  });
  it("large highlight does not exceed 100%", () => {
    expect(highlightWidthPercent({ startTime: 0, endTime: 200, duration: 200 }, 120)).toBe(100);
  });
});

describe("playheadLeftPercent", () => {
  it("returns 50% at midpoint", () => { expect(playheadLeftPercent(60, 120)).toBeCloseTo(50, 1); });
  it("returns 0 at start", () => { expect(playheadLeftPercent(0, 120)).toBe(0); });
  it("returns 100 at end", () => { expect(playheadLeftPercent(120, 120)).toBeCloseTo(100, 1); });
  it("clamps negative to 0", () => { expect(playheadLeftPercent(-10, 120)).toBe(0); });
});

describe("xToTime", () => {
  const rect = { left: 100, width: 800 };
  it("converts click position to time", () => { expect(xToTime(500, rect, 120)).toBeCloseTo(60, 1); });
  it("returns 0 for left edge", () => { expect(xToTime(100, rect, 120)).toBe(0); });
  it("returns duration for right edge", () => { expect(xToTime(900, rect, 120)).toBeCloseTo(120, 1); });
  it("clamps outside to [0, duration]", () => {
    expect(xToTime(50, rect, 120)).toBe(0);
    expect(xToTime(1000, rect, 120)).toBe(120);
  });
});
