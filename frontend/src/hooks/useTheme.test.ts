// ── Tests for useTheme hook ────────────────────────

import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useTheme } from "./useTheme";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
  // Mock matchMedia for light mode default
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  });
});

describe("useTheme", () => {
  it("defaults to system mode", () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.mode).toBe("system");
  });

  it("resolved theme is light by default (mocked system light)", () => {
    const { result } = renderHook(() => useTheme());
    expect(result.current.resolved).toBe("light");
  });

  it("setMode switches to dark", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setMode("dark"));
    expect(result.current.mode).toBe("dark");
    expect(result.current.resolved).toBe("dark");
  });

  it("setMode persists to localStorage", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setMode("dark"));
    expect(localStorage.getItem("videomind-theme")).toBe("dark");
  });

  it("toggle switches between light and dark", () => {
    const { result } = renderHook(() => useTheme());
    // Default is system, but resolved is light
    act(() => result.current.setMode("light"));
    expect(result.current.mode).toBe("light");

    act(() => result.current.toggle());
    expect(result.current.mode).toBe("dark");
    expect(result.current.resolved).toBe("dark");

    act(() => result.current.toggle());
    expect(result.current.resolved).toBe("light");
  });

  it("reads stored mode from localStorage", () => {
    localStorage.setItem("videomind-theme", "dark");
    const { result } = renderHook(() => useTheme());
    expect(result.current.mode).toBe("dark");
    expect(result.current.resolved).toBe("dark");
  });

  it("applies data-theme attribute on documentElement", () => {
    const { result } = renderHook(() => useTheme());
    act(() => result.current.setMode("dark"));
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark");
  });
});
