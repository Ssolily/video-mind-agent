import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TaskStatusCard from "./TaskStatusCard";
import type { TaskResult } from "../api";

const makeTask = (overrides: Partial<TaskResult> = {}): TaskResult => ({
  task_id: "test-task-1",
  video_id: "test-video-1",
  user_goal: "分析视频",
  status: "running" as const,
  progress: 0.5,
  current_step: "检测物体",
  error: null,
  ...overrides,
});

describe("TaskStatusCard", () => {
  it("renders nothing when task is null", () => {
    const { container } = render(<TaskStatusCard task={null} progressPct={0} />);
    expect(container.innerHTML).toBe("");
  });

  it("shows running status", () => {
    render(<TaskStatusCard task={makeTask()} progressPct={50} />);
    expect(screen.getByText("分析中")).toBeTruthy();
  });

  it("shows progress percentage", () => {
    render(<TaskStatusCard task={makeTask()} progressPct={75} />);
    expect(screen.getByText("75%")).toBeTruthy();
  });

  it("shows current step", () => {
    render(<TaskStatusCard task={makeTask()} progressPct={50} />);
    expect(screen.getByText(/检测物体/)).toBeTruthy();
  });

  it("shows failed status", () => {
    render(<TaskStatusCard task={makeTask({ status: "failed" as const, error: "出错了" })} progressPct={0} />);
    expect(screen.getByText("失败")).toBeTruthy();
    expect(screen.getByText("出错了")).toBeTruthy();
  });

  it("shows cancelled status", () => {
    render(<TaskStatusCard task={makeTask({ status: "cancelled" as const })} progressPct={0} />);
    expect(screen.getByText("已取消")).toBeTruthy();
  });

  it("shows completed status", () => {
    render(<TaskStatusCard task={makeTask({ status: "success" as const })} progressPct={100} />);
    expect(screen.getByText("完成")).toBeTruthy();
  });

  it("shows cancel button for running task", () => {
    render(<TaskStatusCard task={makeTask()} progressPct={50} onCancel={() => {}} />);
    expect(screen.getByText("取消任务")).toBeTruthy();
  });

  it("shows retry button for failed task", () => {
    render(<TaskStatusCard task={makeTask({ status: "failed" as const })} progressPct={0} onRetry={() => {}} />);
    expect(screen.getByText("重试任务")).toBeTruthy();
  });

  it("calls onCancel when clicked", () => {
    let called = false;
    render(<TaskStatusCard task={makeTask()} progressPct={50} onCancel={() => { called = true; }} />);
    fireEvent.click(screen.getByText("取消任务"));
    expect(called).toBe(true);
  });
});
