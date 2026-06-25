import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  resolveApiUrl,
  ApiError,
  normalizeVideoResult,
  getVideoResult,
} from "./api";
import type { VideoResult } from "./types/video";

// ── resolveApiUrl ──────────────────────────────

describe("resolveApiUrl", () => {
  it("returns null for null input", () => {
    expect(resolveApiUrl(null)).toBeNull();
  });

  it("returns null for undefined", () => {
    expect(resolveApiUrl(undefined)).toBeNull();
  });

  it("returns null for empty string", () => {
    expect(resolveApiUrl("")).toBeNull();
  });

  it("prefixes relative API URL with BASE", () => {
    const result = resolveApiUrl("/api/v1/videos/abc/source");
    expect(result).toBe("/api/v1/videos/abc/source");
  });

  it("rejects Windows drive-letter path", () => {
    expect(resolveApiUrl("D:\\videos\\test.mp4")).toBeNull();
    expect(resolveApiUrl("C:/Users/test.mp4")).toBeNull();
  });

  it("rejects file:// scheme", () => {
    expect(resolveApiUrl("file:///etc/passwd")).toBeNull();
  });

  it("rejects data:// scheme", () => {
    expect(resolveApiUrl("data:text/plain,hello")).toBeNull();
  });

  it("allows http/https URLs unchanged", () => {
    expect(resolveApiUrl("http://example.com/video.mp4")).toBe("http://example.com/video.mp4");
    expect(resolveApiUrl("https://cdn.example.com/v.mp4")).toBe("https://cdn.example.com/v.mp4");
  });
});

// ── ApiError ──────────────────────────────────

describe("ApiError", () => {
  it("extends Error with status and detail", () => {
    const err = new ApiError("Not found", 404, "Video not found");
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe("ApiError");
    expect(err.status).toBe(404);
    expect(err.detail).toBe("Video not found");
    expect(err.message).toBe("Not found");
  });
});

// ── normalizeVideoResult ──────────────────────

describe("normalizeVideoResult", () => {
  it("normalizes a complete valid response", () => {
    const raw = {
      video_id: "abc",
      status: "success",
      duration: 88,
      source_url: "/api/v1/videos/abc/source",
      highlights: [
        {
          id: "hl_0001",
          start_time: 10,
          end_time: 30,
          duration: 20,
          score: 0.5,
          base_score: 0.5,
          selection_score: 0.5,
          overlap_penalty: 0,
          score_breakdown: { object: { raw: 0.5, weight: 0.25, weighted: 0.125 } },
          reason: ["test"],
        },
      ],
      clips: [
        {
          id: "clip_001",
          url: "/api/v1/videos/abc/clips/clip_001",
          start_time: 10,
          end_time: 30,
          duration: 20,
          highlight_id: "hl_0001",
          size_bytes: 1234,
        },
      ],
      report: { markdown_url: "/api/v1/videos/abc/reports/markdown", json_url: "/api/v1/videos/abc/reports/json" },
      error: null,
      warnings: [],
    };

    const result = normalizeVideoResult(raw);
    expect(result.video_id).toBe("abc");
    expect(result.status).toBe("success");
    expect(result.duration).toBe(88);
    expect(result.source_url).toBe("/api/v1/videos/abc/source");
    expect(result.highlights).toHaveLength(1);
    expect(result.clips).toHaveLength(1);
    expect(result.report.markdown_url).toBe("/api/v1/videos/abc/reports/markdown");
    expect(result.error).toBeNull();
    expect(result.warnings).toEqual([]);
  });

  it("handles empty highlights and clips", () => {
    const result = normalizeVideoResult({});
    expect(result.highlights).toEqual([]);
    expect(result.clips).toEqual([]);
  });

  it("handles missing score_breakdown", () => {
    const result = normalizeVideoResult({
      highlights: [{ id: "h1", start_time: 0, end_time: 1, duration: 1, score: 0.5 }],
    });
    expect(result.highlights[0].score_breakdown).toEqual({});
  });

  it("handles reason as string (old format)", () => {
    const result = normalizeVideoResult({
      highlights: [{ id: "h1", start_time: 0, end_time: 1, duration: 1, score: 0.5, reason: "old string" }],
    });
    expect(Array.isArray(result.highlights[0].reason)).toBe(true);
    expect(result.highlights[0].reason).toEqual(["old string"]);
  });

  it("handles missing selection_score", () => {
    const result = normalizeVideoResult({
      highlights: [{ id: "h1", start_time: 0, end_time: 1, duration: 1, score: 0.5 }],
    });
    expect(result.highlights[0].selection_score).toBe(0.5);
  });

  it("handles NaN safely", () => {
    const result = normalizeVideoResult({
      highlights: [{ id: "h1", start_time: NaN, end_time: 1, duration: 1, score: 0.5 }],
    });
    expect(result.highlights[0].start_time).toBe(0);
  });

  it("handles Windows paths in source_url safely", () => {
    const result = normalizeVideoResult({ source_url: "D:\\videos\\test.mp4" });
    expect(result.source_url).toBe("D:\\videos\\test.mp4");
    // resolveApiUrl will reject it later
  });

  it("ignores unknown extra fields", () => {
    const result = normalizeVideoResult({ video_id: "abc", extra: "ignored" } as any);
    expect(result.video_id).toBe("abc");
  });

  it("preserves completed_with_errors status", () => {
    const result = normalizeVideoResult({ status: "completed_with_errors", warnings: ["some warning"] });
    expect(result.status).toBe("completed_with_errors");
    expect(result.warnings).toContain("some warning");
  });

  it("handles top-level non-object gracefully", () => {
    const result = normalizeVideoResult(null);
    expect(result.video_id).toBe("");
    expect(result.highlights).toEqual([]);
  });
});

// ── getVideoResult (mocked) ────────────────────

describe("getVideoResult", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("returns normalized result for 200 response", async () => {
    const mockData = { video_id: "abc", status: "success", highlights: [], clips: [], report: {}, warnings: [] };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: () => Promise.resolve(mockData),
    });
    const result = await getVideoResult("abc");
    expect(result.video_id).toBe("abc");
    expect(result.status).toBe("success");
  });

  it("throws ApiError for 404", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: () => Promise.resolve({ detail: "Video not found" }),
    });
    await expect(getVideoResult("nonexistent")).rejects.toThrow(ApiError);
  });

  it("throws ApiError for 500", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.reject(new Error("parse failed")),
    });
    try {
      await getVideoResult("broken");
      expect.unreachable("should have thrown");
    } catch (e: any) {
      expect(e).toBeInstanceOf(ApiError);
      expect(e.status).toBe(500);
    }
  });

  it("passes AbortSignal to fetch", async () => {
    const abortController = new AbortController();
    let capturedSignal: AbortSignal | undefined;
    globalThis.fetch = vi.fn().mockImplementation((_url, opts) => {
      capturedSignal = opts?.signal;
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) });
    });
    await getVideoResult("abc", abortController.signal);
    expect(capturedSignal).toBe(abortController.signal);
  });

  it("rejects when aborted", async () => {
    const abortController = new AbortController();
    globalThis.fetch = vi.fn().mockImplementation((_url, opts) => {
      return new Promise((_, reject) => {
        opts?.signal?.addEventListener("abort", () => {
          const err = new DOMException("The operation was aborted", "AbortError");
          reject(err);
        });
        abortController.abort();
      });
    });
    await expect(getVideoResult("abc", abortController.signal)).rejects.toThrow(DOMException);
  });
});
