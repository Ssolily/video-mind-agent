import { describe, it, expect } from "vitest";
import {
  formatScore,
  getPrimaryHighlightScore,
  formatHighlightReason,
  sortHighlightsForDisplay,
  getScoreDimensions,
  sortHighlightsByScore,
} from "./highlightDisplay";
import type { HighlightResult, ScoreComponent } from "../types/video";

function makeHL(ov: Partial<HighlightResult> & { start_time: number; end_time: number }): HighlightResult {
  return {
    id: "hl_001",
    score: 0.5,
    base_score: 0.5,
    selection_score: 0.5,
    overlap_penalty: 0,
    duration: ov.end_time - ov.start_time,
    score_breakdown: {},
    reason: [],
    ...ov,
  };
}

// ---- formatScore ----

describe("formatScore", () => {
  it("formats normal value", () => {
    expect(formatScore(0.12345)).toBe("0.123");
  });
  it("default digits is 3", () => {
    expect(formatScore(0.5)).toBe("0.500");
  });
  it("custom digits", () => {
    expect(formatScore(0.5, 1)).toBe("0.5");
  });
  it("NaN shows 0.000", () => {
    expect(formatScore(NaN)).toBe("0.000");
  });
  it("Infinity shows 0.000", () => {
    expect(formatScore(Infinity)).toBe("0.000");
  });
  it("-Infinity shows 0.000", () => {
    expect(formatScore(-Infinity)).toBe("0.000");
  });
  it("digits clamped to 0-6", () => {
    expect(formatScore(0.5, -1)).toBe("1");
  });
  it("digits max 6", () => {
    expect(formatScore(0.5, 10)).toBe("0.500000");
  });
});

// ---- getPrimaryHighlightScore ----

describe("getPrimaryHighlightScore", () => {
  it("returns selection_score when finite", () => {
    expect(getPrimaryHighlightScore(makeHL({ start_time: 0, end_time: 10, selection_score: 0.8 }))).toBe(0.8);
  });
  it("selection_score=0 is valid and returns 0", () => {
    expect(getPrimaryHighlightScore(makeHL({ start_time: 0, end_time: 10, selection_score: 0, score: 0.8 }))).toBe(0);
  });
  it("selection_score=0 does NOT fallback to positive score", () => {
    const hl = makeHL({ start_time: 0, end_time: 10, selection_score: 0, score: 0.8 });
    expect(getPrimaryHighlightScore(hl)).toBe(0);
    expect(getPrimaryHighlightScore(hl)).not.toBe(0.8);
  });
  it("falls back to score when selection_score is missing", () => {
    const hl = makeHL({ start_time: 0, end_time: 10 });
    hl.selection_score = undefined as any;
    hl.score = 0.7;
    expect(getPrimaryHighlightScore(hl)).toBe(0.7);
  });
  it("returns 0 when both are invalid", () => {
    const hl = makeHL({ start_time: 0, end_time: 10 });
    hl.selection_score = undefined as any;
    hl.score = undefined as any;
    expect(getPrimaryHighlightScore(hl)).toBe(0);
  });
  it("returns 0 when selection_score is NaN and score is also invalid", () => {
    const hl = makeHL({ start_time: 0, end_time: 10, selection_score: NaN });
    hl.score = undefined as any;
    expect(getPrimaryHighlightScore(hl)).toBe(0);
  });
  it("prefers selection_score over score", () => {
    expect(
      getPrimaryHighlightScore(
        makeHL({ start_time: 0, end_time: 10, selection_score: 0.9, score: 0.5 }),
      ),
    ).toBe(0.9);
  });
  it("negative selection_score is valid", () => {
    expect(getPrimaryHighlightScore(makeHL({ start_time: 0, end_time: 10, selection_score: -0.1 }))).toBe(-0.1);
  });
});

// ---- formatHighlightReason ----

describe("formatHighlightReason", () => {
  it("joins string array with Chinese semicolons", () => {
    expect(formatHighlightReason(["a", "b"])).toBe("a\uff1bb");
  });
  it("handles single element array", () => {
    expect(formatHighlightReason(["only"])).toBe("only");
  });
  it("filters empty strings and trims whitespace", () => {
    expect(formatHighlightReason(["  a  ", "", "b"])).toBe("a\uff1bb");
  });
  it("handles old string format", () => {
    expect(formatHighlightReason("old reason")).toBe("old reason");
  });
  it("trims old string format", () => {
    expect(formatHighlightReason("  spaced  ")).toBe("spaced");
  });
  it("handles empty array", () => {
    expect(formatHighlightReason([])).toContain("\u6682\u65e0\u8bc4\u5206\u8bf4\u660e");
  });
  it("handles null", () => {
    expect(formatHighlightReason(null)).toContain("\u6682\u65e0\u8bc4\u5206\u8bf4\u660e");
  });
  it("handles undefined", () => {
    expect(formatHighlightReason(undefined)).toContain("\u6682\u65e0\u8bc4\u5206\u8bf4\u660e");
  });
  it("handles empty string", () => {
    expect(formatHighlightReason("")).toContain("\u6682\u65e0\u8bc4\u5206\u8bf4\u660e");
  });
  it("does not use pipe or English semicolon", () => {
    const result = formatHighlightReason(["a", "b"]);
    expect(result).not.toContain(" | ");
    expect(result).not.toContain("; ");
  });
});

// ---- sortHighlightsForDisplay ----

describe("sortHighlightsForDisplay", () => {
  it("sorts by start_time ascending", () => {
    const hls = [
      makeHL({ id: "late", start_time: 20, end_time: 30, selection_score: 0.9 }),
      makeHL({ id: "early", start_time: 10, end_time: 30, selection_score: 0.3 }),
    ];
    const sorted = sortHighlightsForDisplay(hls);
    expect(sorted[0].id).toBe("early");
    expect(sorted[1].id).toBe("late");
  });
  it("same start_time sorts by end_time ascending", () => {
    const hls = [
      makeHL({ id: "long", start_time: 10, end_time: 30 }),
      makeHL({ id: "short", start_time: 10, end_time: 20 }),
    ];
    const sorted = sortHighlightsForDisplay(hls);
    expect(sorted[0].id).toBe("short");
  });
  it("same time sorts by selection_score descending", () => {
    const hls = [
      makeHL({ id: "low", start_time: 10, end_time: 20, selection_score: 0.3 }),
      makeHL({ id: "high", start_time: 10, end_time: 20, selection_score: 0.9 }),
    ];
    const sorted = sortHighlightsForDisplay(hls);
    expect(sorted[0].id).toBe("high");
  });
  it("same time and score sorts by id ascending", () => {
    const hls = [
      makeHL({ id: "b", start_time: 10, end_time: 20, selection_score: 0.5 }),
      makeHL({ id: "a", start_time: 10, end_time: 20, selection_score: 0.5 }),
    ];
    const sorted = sortHighlightsForDisplay(hls);
    expect(sorted[0].id).toBe("a");
  });
  it("invalid start_time items go after valid ones", () => {
    const hls = [
      makeHL({ id: "b", start_time: Infinity, end_time: 20 }),
      makeHL({ id: "a", start_time: 10, end_time: 20 }),
    ];
    const sorted = sortHighlightsForDisplay(hls);
    expect(sorted[0].id).toBe("a");
    expect(sorted[1].id).toBe("b");
  });
  it("does not mutate original array", () => {
    const hls = [
      makeHL({ id: "a", start_time: 0, end_time: 10, selection_score: 0.3 }),
      makeHL({ id: "b", start_time: 0, end_time: 10, selection_score: 0.9 }),
    ];
    const orig = hls.map((h) => h.id).join(",");
    sortHighlightsForDisplay(hls);
    expect(hls.map((h) => h.id).join(",")).toBe(orig);
  });
  it("handles empty array", () => {
    expect(sortHighlightsForDisplay([])).toEqual([]);
  });
  it("handles null", () => {
    expect(sortHighlightsForDisplay(null as any)).toEqual([]);
  });
  it("deterministic order for same values", () => {
    const hls = [
      makeHL({ id: "x", start_time: 10, end_time: 20, selection_score: 0.5 }),
      makeHL({ id: "y", start_time: 10, end_time: 20, selection_score: 0.5 }),
    ];
    const r1 = sortHighlightsForDisplay(hls);
    const r2 = sortHighlightsForDisplay(hls);
    expect(r1[0].id).toBe(r2[0].id);
    expect(r1[1].id).toBe(r2[1].id);
  });
});

// ---- sortHighlightsByScore (deprecated) ----

describe("sortHighlightsByScore (deprecated)", () => {
  it("delegates to sortHighlightsForDisplay", () => {
    const hls = [
      makeHL({ id: "late", start_time: 20, end_time: 30, selection_score: 0.9 }),
      makeHL({ id: "early", start_time: 10, end_time: 30, selection_score: 0.3 }),
    ];
    const sorted = sortHighlightsByScore(hls);
    expect(sorted[0].id).toBe("early");
  });
});

// ---- getScoreDimensions ----

describe("getScoreDimensions", () => {
  const mockBD: Record<string, ScoreComponent> = {
    object: { raw: 0.8, weight: 0.25, weighted: 0.2 },
    scene: { raw: 0.5, weight: 0.15, weighted: 0.075 },
    quality: { raw: 0.7, weight: 0.2, weighted: 0.14 },
  };
  it("returns dimensions in stable order", () => {
    const dims = getScoreDimensions(mockBD);
    expect(dims.length).toBe(3);
    expect(dims[0].name).toBe("object");
    expect(dims[1].name).toBe("scene");
    expect(dims[2].name).toBe("quality");
  });
  it("marks quality as placeholder", () => {
    const dims = getScoreDimensions(mockBD);
    const q = dims.find((d) => d.name === "quality");
    expect(q?.isPlaceholder).toBe(true);
  });
  it("other dimensions not placeholder", () => {
    const dims = getScoreDimensions(mockBD);
    const obj = dims.find((d) => d.name === "object");
    expect(obj?.isPlaceholder).toBe(false);
  });
  it("handles null breakdown", () => {
    expect(getScoreDimensions(null)).toEqual([]);
  });
  it("handles undefined breakdown", () => {
    expect(getScoreDimensions(undefined)).toEqual([]);
  });
  it("handles empty breakdown", () => {
    expect(getScoreDimensions({})).toEqual([]);
  });
  it("handles unknown dimensions after known ones", () => {
    const bd: Record<string, ScoreComponent> = {
      ...mockBD,
      custom_dim: { raw: 0.9, weight: 0.1, weighted: 0.09 },
    };
    const dims = getScoreDimensions(bd);
    const last = dims[dims.length - 1];
    expect(last.name).toBe("custom_dim");
  });
  it("invalid components are defaulted", () => {
    const bd: Record<string, any> = {
      motion: { raw: NaN, weight: Infinity, weighted: "x" },
    };
    const dims = getScoreDimensions(bd);
    const m = dims.find((d) => d.name === "motion");
    expect(m).toBeDefined();
    expect(m!.raw).toBe(0);
  });
});
