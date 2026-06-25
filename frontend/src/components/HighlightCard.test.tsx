// ── Tests for HighlightCard ────────────────────────

import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import HighlightCard from "./HighlightCard";

const makeHL = (overrides: Record<string, any> = {}) => ({
  id: "hl-1",
  start_time: 10,
  end_time: 25,
  duration: 15,
  score: 0.85,
  base_score: 0.8,
  selection_score: 0.85,
  overlap_penalty: 0,
  score_breakdown: {},
  reason: ["场景变化丰富", "物体检测得分高"],
  ...overrides,
});

describe("HighlightCard", () => {
  it("renders time range and score", () => {
    render(<HighlightCard highlight={makeHL()} index={0} isActive={false} isSelected={false} onSelect={() => {}} />);
    expect(screen.getByText(/00:10/)).toBeTruthy();
    expect(screen.getAllByText(/0\.850/).length).toBeGreaterThanOrEqual(1);
  });

  it("shows index number", () => {
    render(<HighlightCard highlight={makeHL()} index={0} isActive={false} isSelected={false} onSelect={() => {}} />);
    expect(screen.getByText("1")).toBeTruthy();
  });

  it("renders reason text", () => {
    render(<HighlightCard highlight={makeHL()} index={0} isActive={false} isSelected={false} onSelect={() => {}} />);
    expect(screen.getByText(/场景变化/)).toBeTruthy();
  });

  it("has play button", () => {
    render(<HighlightCard highlight={makeHL()} index={0} isActive={false} isSelected={false} onSelect={() => {}} />);
    expect(screen.getByText("▶ 播放片段")).toBeTruthy();
  });

  it("has clip button when clip provided", () => {
    const clip = { id: "clip-1", url: "/clip.mp4", start_time: 10, end_time: 25, duration: 15, highlight_id: "hl-1", size_bytes: 1000 };
    render(<HighlightCard highlight={makeHL()} index={0} isActive={false} isSelected={false} clip={clip} onSelect={() => {}} onPlayClip={() => {}} />);
    expect(screen.getByText("🎬 导出片段")).toBeTruthy();
  });

  it("calls onSelect when clicked", () => {
    let called = false;
    render(<HighlightCard highlight={makeHL()} index={0} isActive={false} isSelected={false} onSelect={() => { called = true; }} />);
    const card = document.querySelector("[data-highlight-id]")!;
    fireEvent.click(card);
    expect(called).toBe(true);
  });
});
