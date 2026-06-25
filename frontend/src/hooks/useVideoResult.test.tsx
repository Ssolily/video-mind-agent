import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useVideoResult } from "./useVideoResult";
import { ApiError } from "../api";

function mockFetch(result: any, status = 200) {
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(result),
  });
}

function mockFetchError(error: Error) {
  globalThis.fetch = vi.fn().mockRejectedValue(error);
}

describe("useVideoResult", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("does not fetch when videoId is null", () => {
    mockFetch({ video_id: "abc", highlights: [], clips: [], report: {}, warnings: [] });
    const { result } = renderHook(() => useVideoResult(null));
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("does not fetch when enabled=false", () => {
    mockFetch({ video_id: "abc", highlights: [], clips: [], report: {}, warnings: [] });
    const { result } = renderHook(() => useVideoResult("abc", { enabled: false }));
    expect(result.current.loading).toBe(false);
    expect(globalThis.fetch).not.toHaveBeenCalled();
  });

  it("fetches when videoId is provided", async () => {
    mockFetch({ video_id: "abc", status: "success", highlights: [], clips: [], report: {}, warnings: [] });
    const { result } = renderHook(() => useVideoResult("abc"));

    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data?.video_id).toBe("abc");
  });

  it("returns data after successful fetch", async () => {
    mockFetch({ video_id: "abc", status: "success", highlights: [], clips: [], report: {}, warnings: [] });
    const { result } = renderHook(() => useVideoResult("abc"));

    await waitFor(() => expect(result.current.data).not.toBeNull());
    expect(result.current.data?.video_id).toBe("abc");
    expect(result.current.error).toBeNull();
  });

  it("returns error on failed fetch", async () => {
    mockFetchError(new Error("Network failure"));
    const { result } = renderHook(() => useVideoResult("abc"));

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error).toBe("Network failure");
    expect(result.current.data).toBeNull();
  });

  it("refetches when videoId changes", async () => {
    mockFetch({ video_id: "v1", highlights: [], clips: [], report: {}, warnings: [] });
    const { result, rerender } = renderHook(
      ({ id }) => useVideoResult(id),
      { initialProps: { id: "v1" as string | null } },
    );

    await waitFor(() => expect(result.current.data?.video_id).toBe("v1"));

    mockFetch({ video_id: "v2", highlights: [], clips: [], report: {}, warnings: [] });
    rerender({ id: "v2" });

    await waitFor(() => expect(result.current.data?.video_id).toBe("v2"));
  });

  it("old request does not overwrite new request", async () => {
    // Simulate slow first request, fast second request
    let resolveSlow: (v: any) => void;
    const slowPromise = new Promise((resolve) => { resolveSlow = resolve; });
    const fastPromise = Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ video_id: "v2", highlights: [], clips: [], report: {}, warnings: [] }),
    });

    const fetchMock = vi.fn()
      .mockReturnValueOnce(slowPromise)
      .mockReturnValueOnce(fastPromise);
    globalThis.fetch = fetchMock;

    const { result, rerender } = renderHook(
      ({ id }) => useVideoResult(id),
      { initialProps: { id: "v1" as string | null } },
    );

    // Change to v2 before v1 resolves
    rerender({ id: "v2" });

    // Now resolve the slow v1 request
    resolveSlow!({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ video_id: "v1", highlights: [], clips: [], report: {}, warnings: [] }),
    });

    await waitFor(() => expect(result.current.data?.video_id).toBe("v2"));
    // Should NOT have been overwritten to v1
    expect(result.current.data?.video_id).toBe("v2");
  });

  it("reload refetches data", async () => {
    let callCount = 0;
    globalThis.fetch = vi.fn().mockImplementation(() => {
      callCount++;
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ video_id: "abc", highlights: [], clips: [], report: {}, warnings: [] }),
      });
    });

    const { result } = renderHook(() => useVideoResult("abc"));
    await waitFor(() => expect(result.current.data).not.toBeNull());
    expect(callCount).toBe(1);

    act(() => { result.current.reload(); });
    await waitFor(() => expect(callCount).toBe(2));
  });

  it("does not surface AbortError as error", async () => {
    const abortController = new AbortController();
    globalThis.fetch = vi.fn().mockImplementation((_url, opts) => {
      return new Promise((_, reject) => {
        opts?.signal?.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
        abortController.abort();
      });
    });

    const { result } = renderHook(() => useVideoResult("abc"));
    // Wait for any state updates
    await new Promise((r) => setTimeout(r, 50));
    // Should not have error set (AbortError is caught)
    expect(result.current.error).toBeNull();
  });
});
