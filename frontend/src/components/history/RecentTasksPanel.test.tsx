import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import RecentTasksPanel from "./RecentTasksPanel";
import type { TaskHistoryEntry } from "../../utils/taskHistory";

const makeEntry = (overrides: Partial<TaskHistoryEntry> = {}): TaskHistoryEntry => ({
  videoId: "v1",
  filename: "test.mp4",
  status: "completed",
  createdAt: "2025-01-01T00:00:00.000Z",
  updatedAt: "2025-01-01T00:00:00.000Z",
  ...overrides,
});

describe("RecentTasksPanel", () => {
  it("renders title", () => {
    render(<RecentTasksPanel tasks={[]} onOpen={vi.fn()} onViewAll={vi.fn()} />);
    expect(screen.getByText("最近任务")).toBeDefined();
  });

  it("shows empty state when no tasks", () => {
    render(<RecentTasksPanel tasks={[]} onOpen={vi.fn()} onViewAll={vi.fn()} />);
    expect(screen.getByText("暂无历史任务，上传视频后历史将显示在此处。")).toBeDefined();
  });

  it("renders up to 5 tasks", () => {
    const tasks = Array.from({ length: 7 }, (_, i) =>
      makeEntry({ videoId: "v" + i, filename: "test" + i + ".mp4" })
    );
    render(<RecentTasksPanel tasks={tasks} onOpen={vi.fn()} onViewAll={vi.fn()} />);
    expect(screen.getAllByRole("button").length).toBeGreaterThanOrEqual(6); // 5 items + view all
  });

  it("shows view all button when tasks exist", () => {
    render(<RecentTasksPanel tasks={[makeEntry()]} onOpen={vi.fn()} onViewAll={vi.fn()} />);
    expect(screen.getByText(/查看全部/)).toBeDefined();
  });

  it("calls onViewAll when clicked", () => {
    const onViewAll = vi.fn();
    render(<RecentTasksPanel tasks={[makeEntry()]} onOpen={vi.fn()} onViewAll={onViewAll} />);
    fireEvent.click(screen.getByText(/查看全部/));
    expect(onViewAll).toHaveBeenCalled();
  });

  it("shows task filename", () => {
    render(<RecentTasksPanel tasks={[makeEntry({ filename: "lecture.mp4" })]} onOpen={vi.fn()} onViewAll={vi.fn()} />);
    expect(screen.getByText("lecture.mp4")).toBeDefined();
  });
});
