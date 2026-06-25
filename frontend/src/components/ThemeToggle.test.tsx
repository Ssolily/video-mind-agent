import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ThemeToggle from "./ThemeToggle";

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
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

describe("ThemeToggle", () => {
  it("renders with system label by default", () => {
    render(<ThemeToggle />);
    expect(screen.getByText("跟随系统")).toBeTruthy();
  });

  it("cycles to light on first click from system", () => {
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button"));
    expect(screen.getByText("亮色")).toBeTruthy();
  });

  it("cycles to dark on second click", () => {
    render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button")); // system → light
    fireEvent.click(screen.getByRole("button")); // light → dark
    expect(screen.getByText("暗色")).toBeTruthy();
  });

  it("applies aria-label", () => {
    render(<ThemeToggle />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-label");
  });
});
