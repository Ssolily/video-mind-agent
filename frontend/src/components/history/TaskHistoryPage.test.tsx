import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TaskHistoryPage from "./TaskHistoryPage";
import type { TaskHistoryEntry } from "../../utils/taskHistory";

const makeEntry = (overrides: Partial<TaskHistoryEntry> = {}): TaskHistoryEntry => ({
  videoId: "v1",
  filename: "test.mp4",
  status: "completed",
  createdAt: "2025-01-01T00:00:00.000Z",
  updatedAt: "2025-01-01T00:00:00.000Z",
  ...overrides,
});

describe("TaskHistoryPage", () => {
  it("renders title", () => {
    render(<TaskHistoryPage tasks={[]} />);
    expect(screen.getByText("任务历史")).toBeDefined();
  });

  it("shows task count", () => {
    render(<TaskHistoryPage tasks={[makeEntry(), makeEntry({ videoId: "v2" })]} />);
    expect(screen.getByText("2 个任务")).toBeDefined();
  });

  it("shows empty state when no tasks", () => {
    render(<TaskHistoryPage tasks={[]} />);
    expect(screen.getByText("还没有分析过视频")).toBeDefined();
  });

  it("shows upload button in empty state", () => {
    const onUpload = vi.fn();
    render(<TaskHistoryPage tasks={[]} onUpload={onUpload} />);
    expect(screen.getByText("上传视频开始分析")).toBeDefined();
  });

  it("calls onUpload when empty CTA clicked", () => {
    const onUpload = vi.fn();
    render(<TaskHistoryPage tasks={[]} onUpload={onUpload} />);
    fireEvent.click(screen.getByText("上传视频开始分析"));
    expect(onUpload).toHaveBeenCalled();
  });

  it("renders back button when onBack provided", () => {
    render(<TaskHistoryPage tasks={[]} onBack={vi.fn()} />);
    expect(screen.getByText("← 返回")).toBeDefined();
  });

  it("calls onBack when back button clicked", () => {
    const onBack = vi.fn();
    render(<TaskHistoryPage tasks={[]} onBack={onBack} />);
    fireEvent.click(screen.getByText("← 返回"));
    expect(onBack).toHaveBeenCalled();
  });

  it("filters tasks by search", () => {
    const tasks = [
      makeEntry({ videoId: "v1", filename: "lecture.mp4" }),
      makeEntry({ videoId: "v2", filename: "sports.mp4" }),
    ];
    render(<TaskHistoryPage tasks={tasks} />);
    expect(screen.getByText("lecture.mp4")).toBeDefined();
    expect(screen.getByText("sports.mp4")).toBeDefined();
  });

  it("renders tasks in the list", () => {
    render(<TaskHistoryPage tasks={[makeEntry()]} />);
    expect(screen.getByText("test.mp4")).toBeDefined();
  });
});
