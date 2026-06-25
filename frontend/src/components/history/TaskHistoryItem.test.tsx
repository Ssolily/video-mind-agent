import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TaskHistoryItem from "./TaskHistoryItem";
import type { TaskHistoryEntry } from "../../utils/taskHistory";

const makeEntry = (overrides: Partial<TaskHistoryEntry> = {}): TaskHistoryEntry => ({
  videoId: "v1",
  taskId: "t1",
  filename: "test.mp4",
  status: "completed",
  createdAt: "2025-01-01T00:00:00.000Z",
  updatedAt: "2025-01-01T00:00:00.000Z",
  duration: 120,
  highlightCount: 5,
  clipCount: 2,
  averageScore: 0.75,
  ...overrides,
});

describe("TaskHistoryItem", () => {
  const defaultOnOpen = vi.fn();
  const defaultOnRemove = vi.fn();

  it("renders filename", () => {
    render(<TaskHistoryItem entry={makeEntry()} onOpen={defaultOnOpen} onRemove={defaultOnRemove} />);
    expect(screen.getByText("test.mp4")).toBeDefined();
  });

  it("renders open button", () => {
    render(<TaskHistoryItem entry={makeEntry()} onOpen={defaultOnOpen} onRemove={defaultOnRemove} />);
    expect(screen.getByText("打开")).toBeDefined();
  });

  it("calls onOpen when clicked", () => {
    const onOpen = vi.fn();
    render(<TaskHistoryItem entry={makeEntry()} onOpen={onOpen} onRemove={defaultOnRemove} />);
    fireEvent.click(screen.getByText("打开"));
    expect(onOpen).toHaveBeenCalledWith(makeEntry());
  });

  it("renders retry button for failed tasks", () => {
    render(<TaskHistoryItem entry={makeEntry({ status: "failed" })} onOpen={defaultOnOpen} onRemove={defaultOnRemove} onRetry={vi.fn()} />);
    expect(screen.getByText("重试")).toBeDefined();
  });

  it("renders retry button for timeout tasks", () => {
    render(<TaskHistoryItem entry={makeEntry({ status: "timeout" })} onOpen={defaultOnOpen} onRemove={defaultOnRemove} onRetry={vi.fn()} />);
    expect(screen.getByText("重试")).toBeDefined();
  });

  it("does not render retry button for completed", () => {
    render(<TaskHistoryItem entry={makeEntry()} onOpen={defaultOnOpen} onRemove={defaultOnRemove} />);
    expect(screen.queryByText("重试")).toBeNull();
  });

  it("calls onRetry when retry clicked", () => {
    const onRetry = vi.fn();
    render(<TaskHistoryItem entry={makeEntry({ status: "failed" })} onOpen={defaultOnOpen} onRemove={defaultOnRemove} onRetry={onRetry} />);
    fireEvent.click(screen.getByText("重试"));
    expect(onRetry).toHaveBeenCalled();
  });

  it("renders remove button", () => {
    render(<TaskHistoryItem entry={makeEntry()} onOpen={defaultOnOpen} onRemove={defaultOnRemove} />);
    expect(screen.getByText("从历史中移除")).toBeDefined();
  });

  it("calls onRemove when remove clicked", () => {
    const onRemove = vi.fn();
    render(<TaskHistoryItem entry={makeEntry()} onOpen={defaultOnOpen} onRemove={onRemove} />);
    fireEvent.click(screen.getByText("从历史中移除"));
    expect(onRemove).toHaveBeenCalled();
  });

  it("renders stats for completed tasks", () => {
    render(<TaskHistoryItem entry={makeEntry()} onOpen={defaultOnOpen} onRemove={defaultOnRemove} />);
    expect(screen.getByText(/精彩: 5/)).toBeDefined();
    expect(screen.getByText(/片段: 2/)).toBeDefined();
  });
});
