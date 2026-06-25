// ── Tests for ErrorState ──────────────────────────

import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ErrorState from "./ErrorState";

describe("ErrorState", () => {
  it("renders error message", () => {
    render(<ErrorState message="Test error" />);
    expect(screen.getByText("操作失败")).toBeTruthy();
  });

  it("renders custom title", () => {
    render(<ErrorState title="自定义错误" message="出错了" />);
    expect(screen.getByText("自定义错误")).toBeTruthy();
  });

  it("renders retry button", () => {
    const onRetry = () => {};
    render(<ErrorState message="err" onRetry={onRetry} />);
    expect(screen.getByText("重试")).toBeTruthy();
  });

  it("calls onRetry when clicked", () => {
    let called = false;
    render(<ErrorState message="err" onRetry={() => { called = true; }} />);
    fireEvent.click(screen.getByText("重试"));
    expect(called).toBe(true);
  });

  it("shows friendly hint for queue full", () => {
    render(<ErrorState message="Queue is full" />);
    expect(screen.getAllByText(/队列已满/).length).toBeGreaterThanOrEqual(1);
  });

  it("shows friendly hint for network error", () => {
    render(<ErrorState message="Failed to fetch" />);
    expect(screen.getAllByText(/连接失败/).length).toBeGreaterThanOrEqual(1);
  });
});
