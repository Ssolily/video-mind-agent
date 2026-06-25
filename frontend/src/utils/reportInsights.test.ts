// ── Tests for reportInsights ───────────────────────

import { describe, it, expect } from "vitest";
import {
  computeMetrics,
  computeScoreDistribution,
  computeDominantDimension,
  generateInsightDescription,
  generateHLExplanation,
  safeScore,
} from "./reportInsights";
import type { HighlightResult } from "../types/video";

function makeHL(overrides: Partial<HighlightResult> = {}): HighlightResult {
  return {
    id: "hl-1",
    start_time: 10,
    end_time: 25,
    duration: 15,
    score: 0.7,
    base_score: 0.65,
    selection_score: 0.7,
    overlap_penalty: 0,
    score_breakdown: {},
    reason: [],
    ...overrides,
  };
}

describe("safeScore", () => {
  it("clamps to 0-1", () => {
    expect(safeScore(1.5)).toBe(1);
    expect(safeScore(-0.5)).toBe(0);
    expect(safeScore(0.5)).toBe(0.5);
  });
  it("handles NaN and Infinity", () => {
    expect(safeScore(NaN)).toBe(0);
    expect(safeScore(Infinity)).toBe(0);
    expect(safeScore(null)).toBe(0);
    expect(safeScore(undefined)).toBe(0);
  });
});

describe("computeMetrics", () => {
  it("returns zero metrics for empty highlights", () => {
    const m = computeMetrics([], 0, 120);
    expect(m.highlightCount).toBe(0);
    expect(m.averageScore).toBe(0);
    expect(m.coveragePercent).toBe(0);
  });

  it("computes average score correctly", () => {
    const hls = [
      makeHL({ id: "a", start_time: 0, end_time: 10, score: 0.8, selection_score: 0.8 }),
      makeHL({ id: "b", start_time: 20, end_time: 30, score: 0.6, selection_score: 0.6 }),
    ];
    const m = computeMetrics(hls, 1, 120);
    expect(m.averageScore).toBe(0.7);
  });

  it("computes coverage correctly (non-overlapping)", () => {
    const hls = [
      makeHL({ id: "a", start_time: 0, end_time: 10, duration: 10 }),
      makeHL({ id: "b", start_time: 20, end_time: 30, duration: 10 }),
    ];
    const m = computeMetrics(hls, 0, 120);
    expect(m.coverageSeconds).toBe(20);
    expect(m.coveragePercent).toBeCloseTo(16.7, 0);
  });

  it("merges overlapping coverage", () => {
    const hls = [
      makeHL({ id: "a", start_time: 0, end_time: 20, duration: 20 }),
      makeHL({ id: "b", start_time: 15, end_time: 30, duration: 15 }),
    ];
    const m = computeMetrics(hls, 0, 120);
    expect(m.coverageSeconds).toBe(30); // 0-30 merged
  });

  it("finds top 3 highlights", () => {
    const hls = [
      makeHL({ id: "a", start_time: 0, end_time: 10, score: 0.5, selection_score: 0.5 }),
      makeHL({ id: "b", start_time: 10, end_time: 20, score: 0.9, selection_score: 0.9 }),
      makeHL({ id: "c", start_time: 20, end_time: 30, score: 0.7, selection_score: 0.7 }),
      makeHL({ id: "d", start_time: 30, end_time: 40, score: 0.6, selection_score: 0.6 }),
    ];
    const m = computeMetrics(hls, 0, 120);
    expect(m.topHighlights).toHaveLength(3);
    expect(m.topHighlights[0].id).toBe("b");
  });

  it("highlights invalid time ranges are excluded", () => {
    const hls = [
      makeHL({ id: "a", start_time: 0, end_time: 10 }),
      makeHL({ id: "b", start_time: 30, end_time: 20 }), // invalid
      makeHL({ id: "c", start_time: NaN, end_time: 40 }), // invalid
    ];
    const m = computeMetrics(hls as any, 0, 120);
    expect(m.highlightCount).toBe(1);
  });
});

describe("computeScoreDistribution", () => {
  it("returns empty buckets for no highlights", () => {
    const b = computeScoreDistribution([]);
    expect(b).toHaveLength(5);
    expect(b.every((x) => x.count === 0)).toBe(true);
  });

  it("buckets scores correctly", () => {
    const hls = [
      makeHL({ id: "a", score: 0.1 }),
      makeHL({ id: "b", score: 0.3 }),
      makeHL({ id: "c", score: 0.5 }),
      makeHL({ id: "d", score: 0.7 }),
      makeHL({ id: "e", score: 0.9 }),
    ];
    const b = computeScoreDistribution(hls);
    expect(b[0].count).toBe(1); // 0.0-0.2
    expect(b[1].count).toBe(1); // 0.2-0.4
    expect(b[2].count).toBe(1); // 0.4-0.6
    expect(b[3].count).toBe(1); // 0.6-0.8
    expect(b[4].count).toBe(1); // 0.8-1.0
  });
});

describe("computeDominantDimension", () => {
  it("returns null when no breakdown", () => {
    expect(computeDominantDimension([])).toBeNull();
    expect(computeDominantDimension([makeHL()])).toBeNull();
  });

  it("finds dominant dimension", () => {
    const hls = [
      makeHL({
        score_breakdown: {
          speech: { raw: 0.2, weight: 1, weighted: 0.2 },
          motion: { raw: 0.9, weight: 1, weighted: 0.9 },
        },
      }),
    ];
    const d = computeDominantDimension(hls);
    expect(d).not.toBeNull();
    expect(d!.name).toBe("motion");
  });
});

describe("generateInsightDescription", () => {
  const baseMetrics = {
    totalDuration: 120,
    highlightCount: 5,
    clipCount: 2,
    averageScore: 0.7,
    maxScore: 0.9,
    minScore: 0.3,
    coverageSeconds: 40,
    coveragePercent: 33.3,
    topHighlights: [],
    clipsHighlightCount: 2,
  };

  it("returns empty message when no highlights", () => {
    const msg = generateInsightDescription({ ...baseMetrics, highlightCount: 0, averageScore: 0 }, null);
    expect(msg).toContain("未检测到");
  });

  it("includes dimension info when dominant dim present", () => {
    const msg = generateInsightDescription(baseMetrics, { name: "speech", averageScore: 0.8, displayName: "语音内容" });
    expect(msg).toContain("语音内容");
  });

  it("returns generic description when no dominant dim", () => {
    const msg = generateInsightDescription(baseMetrics, null);
    expect(msg).toContain("精彩片段");
  });
});

describe("generateHLExplanation", () => {
  it("returns score-based explanation with reason", () => {
    const hl = makeHL({ score: 0.8, base_score: 0.7, selection_score: 0.8, reason: ["场景变化多"] });
    const exp = generateHLExplanation(hl);
    expect(exp).toContain("基础分较高");
    expect(exp).toContain("场景变化多");
  });

  it("includes top dimensions", () => {
    const hl = makeHL({
      score: 0.8,
      score_breakdown: { speech: { raw: 0.9, weight: 1, weighted: 0.9 }, motion: { raw: 0.3, weight: 1, weighted: 0.3 } },
    });
    const exp = generateHLExplanation(hl);
    expect(exp).toContain("语音内容");
  });

  it("handles missing reason and breakdown", () => {
    const hl = makeHL({ score: 0.5, base_score: 0.5, selection_score: 0.5, reason: [], score_breakdown: {} });
    const exp = generateHLExplanation(hl);
    expect(exp).toContain("基础分中等");
  });
});
