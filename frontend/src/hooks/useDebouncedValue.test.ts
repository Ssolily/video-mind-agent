import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDebouncedValue } from "./useDebouncedValue";

beforeEach(() => { vi.useFakeTimers(); });
afterEach(() => { vi.useRealTimers(); });

describe("useDebouncedValue", () => {
  it("returns initial value immediately", () => {
    const { result } = renderHook(() => useDebouncedValue("hello", 250));
    expect(result.current).toBe("hello");
  });

  it("does not update before delay", () => {
    const { result, rerender } = renderHook(({ v }) => useDebouncedValue(v, 250), { initialProps: { v: "hello" } });
    rerender({ v: "world" });
    expect(result.current).toBe("hello");
  });

  it("updates after delay", () => {
    const { result, rerender } = renderHook(({ v }) => useDebouncedValue(v, 250), { initialProps: { v: "hello" } });
    rerender({ v: "world" });
    act(() => { vi.advanceTimersByTime(250); });
    expect(result.current).toBe("world");
  });

  it("resets timer on rapid changes", () => {
    const { result, rerender } = renderHook(({ v }) => useDebouncedValue(v, 250), { initialProps: { v: "a" } });
    rerender({ v: "b" });
    act(() => { vi.advanceTimersByTime(100); });
    rerender({ v: "c" });
    act(() => { vi.advanceTimersByTime(100); });
    expect(result.current).toBe("a"); // still old because timer was reset
    act(() => { vi.advanceTimersByTime(150); });
    expect(result.current).toBe("c");
  });

  it("handles empty string rapid change correctly", () => {
    const { result, rerender } = renderHook(({ v }) => useDebouncedValue(v, 200), { initialProps: { v: "test" } });
    rerender({ v: "" });
    act(() => { vi.advanceTimersByTime(200); });
    expect(result.current).toBe("");
  });
});
