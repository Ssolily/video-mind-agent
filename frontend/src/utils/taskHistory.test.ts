import { describe, it, expect, beforeEach } from "vitest";
import { deserializeTaskHistory, mergeTaskHistory, filterTaskHistory, removeFromHistory, buildEntryFromResult, STORAGE_KEY, MAX_ENTRIES } from "./taskHistory";
import type { FilterOptions } from "./taskHistory";

const makeEntry = (overrides: Record<string, any> = {}) => ({
  videoId: "v1", taskId: "t1", filename: "test.mp4", status: "completed",
  createdAt: "2025-01-01T00:00:00.000Z", updatedAt: "2025-01-01T00:00:00.000Z",
  duration: 120, highlightCount: 5, clipCount: 2, averageScore: 0.75,
  ...overrides,
});

beforeEach(() => localStorage.clear());

describe("deserializeTaskHistory", () => {
  it("returns empty array for null", () => { expect(deserializeTaskHistory(null)).toEqual([]); });
  it("returns empty array for invalid JSON", () => { expect(deserializeTaskHistory("invalid")).toEqual([]); });
  it("returns empty array for non-array", () => { expect(deserializeTaskHistory("{}")).toEqual([]); });
  it("parses valid array", () => {
    const data = JSON.stringify([makeEntry()]);
    expect(deserializeTaskHistory(data)).toHaveLength(1);
  });
});

describe("mergeTaskHistory", () => {
  it("adds new entry", () => {
    const result = mergeTaskHistory([], makeEntry());
    expect(result).toHaveLength(1);
  });
  it("deduplicates by videoId", () => {
    const existing = [makeEntry()];
    const result = mergeTaskHistory(existing, makeEntry({ status: "running" }));
    expect(result).toHaveLength(1);
    expect(result[0].status).toBe("running");
  });
  it("limits to MAX_ENTRIES", () => {
    const entries = Array.from({ length: MAX_ENTRIES + 5 }, (_, i) => makeEntry({ videoId: "v" + i, taskId: "t" + i }));
    const result = mergeTaskHistory(entries, makeEntry({ videoId: "new", taskId: "new" }));
    expect(result.length).toBeLessThanOrEqual(MAX_ENTRIES);
  });
});

describe("filterTaskHistory", () => {
  const tasks = [
    makeEntry({ videoId: "v1", filename: "lecture.mp4", status: "completed", highlightCount: 8, averageScore: 0.8, duration: 600, createdAt: "2025-01-01" }),
    makeEntry({ videoId: "v2", filename: "sports.mp4", status: "failed", highlightCount: 3, averageScore: 0.4, duration: 120, createdAt: "2025-01-02" }),
    makeEntry({ videoId: "v3", filename: "movie.mp4", status: "running", highlightCount: 5, averageScore: 0.6, duration: 300, createdAt: "2025-01-03" }),
  ];
  const baseFilter: FilterOptions = { status: "all", search: "", sort: "newest" };

  it("returns all when status=all", () => {
    expect(filterTaskHistory(tasks, baseFilter)).toHaveLength(3);
  });
  it("filters by status", () => {
    expect(filterTaskHistory(tasks, { ...baseFilter, status: "completed" })).toHaveLength(1);
  });
  it("searches case-insensitive", () => {
    expect(filterTaskHistory(tasks, { ...baseFilter, search: "LECTURE" })).toHaveLength(1);
  });
  it("searches by videoId", () => {
    expect(filterTaskHistory(tasks, { ...baseFilter, search: "v2" })).toHaveLength(1);
  });
  it("sorts by newest", () => {
    const r = filterTaskHistory(tasks, baseFilter);
    expect(r[0].videoId).toBe("v3");
  });
  it("sorts by oldest", () => {
    const r = filterTaskHistory(tasks, { ...baseFilter, sort: "oldest" });
    expect(r[0].videoId).toBe("v1");
  });
  it("sorts by highest_score", () => {
    const r = filterTaskHistory(tasks, { ...baseFilter, sort: "highest_score" });
    expect(r[0].videoId).toBe("v1");
  });
  it("sorts by most_highlights", () => {
    const r = filterTaskHistory(tasks, { ...baseFilter, sort: "most_highlights" });
    expect(r[0].videoId).toBe("v1");
  });
  it("sorts by longest_duration", () => {
    const r = filterTaskHistory(tasks, { ...baseFilter, sort: "longest_duration" });
    expect(r[0].videoId).toBe("v1");
  });
  it("missing fields do not crash", () => {
    const bad = makeEntry({ videoId: "bad", averageScore: undefined, duration: undefined, highlightCount: undefined });
    expect(() => filterTaskHistory([bad], baseFilter)).not.toThrow();
  });
});

describe("removeFromHistory", () => {
  it("removes matching videoId", () => {
    const result = removeFromHistory([makeEntry({ videoId: "v1" }), makeEntry({ videoId: "v2" })], "v1");
    expect(result).toHaveLength(1);
  });
});

describe("buildEntryFromResult", () => {
  it("computes averageScore", () => {
    const e = buildEntryFromResult({ video_id: "v1", status: "completed", highlights: [{ score: 0.8 }, { score: 0.6 }], clips: [] }, "test.mp4");
    expect(e.averageScore).toBe(0.7);
  });
  it("missing highlights do not crash", () => {
    const e = buildEntryFromResult({ video_id: "v1", status: "completed" } as any, "test.mp4");
    expect(e.highlightCount).toBe(0);
  });
});
