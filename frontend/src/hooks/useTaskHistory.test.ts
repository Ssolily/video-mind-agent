import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTaskHistory } from "./useTaskHistory";
import { STORAGE_KEY } from "../utils/taskHistory";

beforeEach(() => {
  localStorage.clear();
});

describe("useTaskHistory", () => {
  it("returns empty tasks initially", () => {
    const { result } = renderHook(() => useTaskHistory());
    expect(result.current.tasks).toEqual([]);
  });

  it("adds entry via addEntry", () => {
    const { result } = renderHook(() => useTaskHistory());
    act(() => {
      result.current.addEntry({
        videoId: "v1",
        filename: "test.mp4",
        status: "completed",
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    });
    expect(result.current.tasks).toHaveLength(1);
    expect(result.current.tasks[0].videoId).toBe("v1");
  });

  it("persists entry to localStorage", () => {
    const { result } = renderHook(() => useTaskHistory());
    act(() => {
      result.current.addEntry({
        videoId: "v1",
        filename: "test.mp4",
        status: "completed",
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    });
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    expect(stored).toHaveLength(1);
    expect(stored[0].videoId).toBe("v1");
  });

  it("loads existing tasks from localStorage on mount", () => {
    const entry = {
      videoId: "v1",
      filename: "test.mp4",
      status: "completed",
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify([entry]));
    const { result } = renderHook(() => useTaskHistory());
    expect(result.current.tasks).toHaveLength(1);
  });

  it("removes entry via removeEntry", () => {
    const { result } = renderHook(() => useTaskHistory());
    act(() => {
      result.current.addEntry({
        videoId: "v1",
        filename: "test.mp4",
        status: "completed",
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
      result.current.addEntry({
        videoId: "v2",
        filename: "test2.mp4",
        status: "failed",
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    });
    expect(result.current.tasks).toHaveLength(2);
    act(() => {
      result.current.removeEntry("v1");
    });
    expect(result.current.tasks).toHaveLength(1);
    expect(result.current.tasks[0].videoId).toBe("v2");
  });

  it("merges entry deduplicated by videoId", () => {
    const { result } = renderHook(() => useTaskHistory());
    act(() => {
      result.current.addEntry({
        videoId: "v1",
        filename: "test.mp4",
        status: "running",
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    });
    act(() => {
      result.current.addEntry({
        videoId: "v1",
        filename: "test.mp4",
        status: "completed",
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        highlightCount: 5,
      });
    });
    expect(result.current.tasks).toHaveLength(1);
    expect(result.current.tasks[0].status).toBe("completed");
    expect(result.current.tasks[0].highlightCount).toBe(5);
  });
});
