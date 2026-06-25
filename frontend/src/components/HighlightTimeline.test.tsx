import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import HighlightTimeline from "./HighlightTimeline";
import type { HighlightResult } from "../types/video";

function makeHL(ov: Partial<HighlightResult> & { start_time: number; end_time: number }): HighlightResult {
  return { id: "hl_001", score: 0.5, base_score: 0.5, selection_score: 0.5, overlap_penalty: 0, duration: ov.end_time - ov.start_time, score_breakdown: {}, reason: [], ...ov };
}

describe("HighlightTimeline", () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  it("renders empty state when duration is 0", () => {
    render(<HighlightTimeline duration={0} highlights={[]} currentTime={0} />);
    expect(screen.getByText("视频时长无效")).toBeTruthy();
  });

  it("renders empty state when duration is NaN", () => {
    render(<HighlightTimeline duration={NaN} highlights={[]} currentTime={0} />);
    expect(screen.getByText("视频时长无效")).toBeTruthy();
  });

  it("uses default aria-label", () => {
    render(<HighlightTimeline duration={120} highlights={[]} currentTime={0} />);
    expect(screen.getAllByLabelText("精彩片段时间轴").length).toBeGreaterThanOrEqual(1);
  });

  it("uses custom ariaLabel", () => {
    render(<HighlightTimeline duration={120} highlights={[]} currentTime={0} ariaLabel="My Timeline" />);
    expect(screen.getAllByLabelText("My Timeline").length).toBeGreaterThanOrEqual(1);
  });

  it("renders highlight as native button", () => {
    render(<HighlightTimeline duration={120} highlights={[makeHL({ id: "a", start_time: 10, end_time: 20 })]} currentTime={0} />);
    const buttons = document.querySelectorAll("button");
    expect(buttons.length).toBeGreaterThanOrEqual(1);
    expect(buttons[0].getAttribute("type")).toBe("button");
  });

  it("renders highlight bars for valid highlights", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 })];
    render(<HighlightTimeline duration={120} highlights={hls} currentTime={0} />);
    expect(document.querySelectorAll("[data-highlight-id]").length).toBe(1);
  });

  it("skips invalid highlights (start >= end)", () => {
    const hls = [makeHL({ id: "v", start_time: 10, end_time: 20 }), makeHL({ id: "i", start_time: 30, end_time: 20 })];
    render(<HighlightTimeline duration={120} highlights={hls} currentTime={0} />);
    expect(document.querySelectorAll("[data-highlight-id]").length).toBe(1);
  });

  it("renders all-invalid state", () => {
    render(<HighlightTimeline duration={120} highlights={[makeHL({ id: "x", start_time: 30, end_time: 20 })]} currentTime={0} />);
    expect(screen.getByText("所有精彩片段无效")).toBeTruthy();
  });

  it("does not render end_time=Infinity highlight", () => {
    render(<HighlightTimeline duration={120} highlights={[makeHL({ id: "inf", start_time: 10, end_time: Infinity })]} currentTime={0} />);
    expect(document.querySelectorAll("[data-highlight-id]").length).toBe(0);
  });

  it("renders playhead at correct position", () => {
    render(<HighlightTimeline duration={120} highlights={[]} currentTime={60} />);
    const ph = document.querySelector(".highlight-timeline__playhead") as HTMLElement;
    expect(ph.style.left).toBe("50%");
  });

  it("marks active highlight based on currentTime", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 }), makeHL({ id: "b", start_time: 30, end_time: 40 })];
    render(<HighlightTimeline duration={120} highlights={hls} currentTime={15} />);
    const bars = document.querySelectorAll("[data-highlight-id]");
    expect(bars[0].className).toContain("highlight-timeline__bar--active");
    expect(bars[1].className).not.toContain("highlight-timeline__bar--active");
  });

  it("activeHighlightId overrides auto-detection", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 }), makeHL({ id: "b", start_time: 30, end_time: 40 })];
    render(<HighlightTimeline duration={120} highlights={hls} currentTime={15} activeHighlightId="b" />);
    const bars = document.querySelectorAll("[data-highlight-id]");
    expect(bars[0].className).not.toContain("highlight-timeline__bar--active");
    expect(bars[1].className).toContain("highlight-timeline__bar--active");
  });

  it("activeHighlightId=null clears active", () => {
    render(<HighlightTimeline duration={120} highlights={[makeHL({ id: "a", start_time: 10, end_time: 20 })]} currentTime={15} activeHighlightId={null} />);
    expect(document.querySelector("[data-highlight-id]")!.className).not.toContain("highlight-timeline__bar--active");
  });

  it("marks selected highlight", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 }), makeHL({ id: "b", start_time: 30, end_time: 40 })];
    render(<HighlightTimeline duration={120} highlights={hls} currentTime={0} selectedHighlightId="b" />);
    expect(document.querySelectorAll("[data-highlight-id]")[1].className).toContain("highlight-timeline__bar--selected");
  });

  it("selected has aria-pressed=true", () => {
    render(<HighlightTimeline duration={120} highlights={[makeHL({ id: "a", start_time: 10, end_time: 20 })]} currentTime={0} selectedHighlightId="a" />);
    expect(document.querySelector("[data-highlight-id]")!.getAttribute("aria-pressed")).toBe("true");
  });

  it("non-selected has aria-pressed=false", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 }), makeHL({ id: "b", start_time: 30, end_time: 40 })];
    render(<HighlightTimeline duration={120} highlights={hls} currentTime={0} selectedHighlightId="a" />);
    expect(document.querySelectorAll("[data-highlight-id]")[1].getAttribute("aria-pressed")).toBe("false");
  });

  it("selected and active can be different", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 }), makeHL({ id: "b", start_time: 30, end_time: 40 })];
    render(<HighlightTimeline duration={120} highlights={hls} currentTime={15} selectedHighlightId="b" />);
    const bars = document.querySelectorAll("[data-highlight-id]");
    expect(bars[0].className).toContain("highlight-timeline__bar--active");
    expect(bars[0].className).not.toContain("highlight-timeline__bar--selected");
    expect(bars[1].className).not.toContain("highlight-timeline__bar--active");
    expect(bars[1].className).toContain("highlight-timeline__bar--selected");
  });

  it("calls onSelectHighlight when clicking a bar", () => {
    const onSelect = vi.fn();
    render(<HighlightTimeline duration={120} highlights={[makeHL({ id: "a", start_time: 10, end_time: 20 })]} currentTime={0} onSelectHighlight={onSelect} />);
    fireEvent.click(document.querySelector("[data-highlight-id]")!);
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("no double trigger", () => {
    const onSelect = vi.fn();
    render(<HighlightTimeline duration={120} highlights={[makeHL({ id: "a", start_time: 10, end_time: 20 })]} currentTime={0} onSelectHighlight={onSelect} />);
    const bar = document.querySelector("[data-highlight-id]")!;
    fireEvent.click(bar);
    fireEvent.click(bar);
    expect(onSelect).toHaveBeenCalledTimes(2);
  });

  it("calls onSeek when clicking empty track", () => {
    const onSeek = vi.fn();
    render(<HighlightTimeline duration={120} highlights={[]} currentTime={0} onSeek={onSeek} />);
    const track = document.querySelector(".highlight-timeline__track")!;
    vi.spyOn(track, "getBoundingClientRect").mockReturnValue({ left: 0, width: 800, top: 0, right: 800, bottom: 40, height: 40, x: 0, y: 0, toJSON: () => ({}) });
    fireEvent.click(track, { clientX: 200 });
    expect(onSeek).toHaveBeenCalledWith(30);
  });

  it("does not call onSeek when clicking on highlight bar", () => {
    const onSeek = vi.fn();
    const onSelect = vi.fn();
    render(<HighlightTimeline duration={120} highlights={[makeHL({ id: "a", start_time: 10, end_time: 20 })]} currentTime={0} onSeek={onSeek} onSelectHighlight={onSelect} />);
    const track = document.querySelector(".highlight-timeline__track")!;
    vi.spyOn(track, "getBoundingClientRect").mockReturnValue({ left: 0, width: 800, top: 0, right: 800, bottom: 40, height: 40, x: 0, y: 0, toJSON: () => ({}) });
    fireEvent.click(document.querySelector("[data-highlight-id]")!);
    expect(onSeek).not.toHaveBeenCalled();
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("renders highlight with correct left% and width%", () => {
    render(<HighlightTimeline duration={120} highlights={[makeHL({ id: "a", start_time: 30, end_time: 60 })]} currentTime={0} />);
    const bar = document.querySelector("[data-highlight-id]") as HTMLElement;
    expect(bar.style.left).toBe("25%");
    expect(bar.style.width).toBe("25%");
  });

  it("aria-label includes selection_score", () => {
    render(<HighlightTimeline duration={120} highlights={[makeHL({ id: "a", start_time: 10, end_time: 20, selection_score: 0.789 })]} currentTime={0} />);
    expect(document.querySelector("[data-highlight-id]")!.getAttribute("aria-label")).toContain("0.789");
  });

  it("empty reason shows default text", () => {
    render(<HighlightTimeline duration={120} highlights={[makeHL({ id: "a", start_time: 10, end_time: 20, reason: [] })]} currentTime={0} />);
    expect(document.querySelector("[data-highlight-id]")!.getAttribute("aria-label")).toContain("00:10.000 - 00:20.000");
    expect(document.querySelector("[data-highlight-id]")!.getAttribute("aria-label")).toContain("得分");
  });

  it("merges className", () => {
    render(<HighlightTimeline duration={120} highlights={[]} currentTime={0} className="my-class" />);
    expect(document.querySelector(".highlight-timeline")!.className).toContain("my-class");
  });

  it("shows current time display", () => {
    render(<HighlightTimeline duration={120} highlights={[]} currentTime={65} />);
    expect(screen.getByText(/01:05.000/)).toBeTruthy();
  });

  it("currentTime at end_time is not active (half-open)", () => {
    render(<HighlightTimeline duration={120} highlights={[makeHL({ id: "a", start_time: 10, end_time: 20 }), makeHL({ id: "b", start_time: 20, end_time: 30 })]} currentTime={20} />);
    const bars = document.querySelectorAll("[data-highlight-id]");
    expect(bars[0].className).not.toContain("highlight-timeline__bar--active");
    expect(bars[1].className).toContain("highlight-timeline__bar--active");
  });

  it("does not crash with null highlights", () => {
    render(<HighlightTimeline duration={120} highlights={null as any} currentTime={0} />);
    expect(document.querySelector(".highlight-timeline")).toBeTruthy();
  });

  it("does not render NaN or Infinity in style", () => {
    render(<HighlightTimeline duration={120} highlights={[makeHL({ id: "a", start_time: -10, end_time: 200, score: NaN })]} currentTime={NaN} />);
    const bar = document.querySelector("[data-highlight-id]") as HTMLElement;
    expect(bar.style.left).toBe("0%");
    expect(bar.style.width).toBe("100%");
  });
});
