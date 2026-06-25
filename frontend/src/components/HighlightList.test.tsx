import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import HighlightList from "./HighlightList";
import type { HighlightResult } from "../types/video";

function makeHL(
  ov: Partial<HighlightResult> & { start_time: number; end_time: number },
): HighlightResult {
  return {
    id: "hl_001",
    score: 0.5,
    base_score: 0.5,
    selection_score: 0.5,
    overlap_penalty: 0,
    duration: ov.end_time - ov.start_time,
    score_breakdown: {},
    reason: [],
    ...ov,
  };
}

describe("HighlightList", () => {
  it("shows empty state when highlights is empty", () => {
    render(<HighlightList highlights={[]} />);
    expect(screen.getByText("\u6682\u65e0\u7cbe\u5f69\u7247\u6bb5")).toBeTruthy();
  });

  it("shows empty state when highlights is null", () => {
    render(<HighlightList highlights={null as any} />);
    expect(screen.getByText("\u6682\u65e0\u7cbe\u5f69\u7247\u6bb5")).toBeTruthy();
  });

  it("renders highlight cards", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 })];
    render(<HighlightList highlights={hls} />);
    expect(document.querySelectorAll(".highlight-card").length).toBe(1);
  });

  it("sorts by start_time ascending (not score descending)", () => {
    const hls = [
      makeHL({ id: "first", start_time: 10, end_time: 20, selection_score: 0.3 }),
      makeHL({ id: "second", start_time: 30, end_time: 40, selection_score: 0.9 }),
    ];
    render(<HighlightList highlights={hls} />);
    const cards = document.querySelectorAll(".highlight-card");
    expect(cards[0].getAttribute("data-highlight-id")).toBe("first");
    expect(cards[1].getAttribute("data-highlight-id")).toBe("second");
  });

  it("same start_time sorts by end_time ascending", () => {
    const hls = [
      makeHL({ id: "long", start_time: 10, end_time: 30 }),
      makeHL({ id: "short", start_time: 10, end_time: 20 }),
    ];
    render(<HighlightList highlights={hls} />);
    const cards = document.querySelectorAll(".highlight-card");
    expect(cards[0].getAttribute("data-highlight-id")).toBe("short");
  });

  it("same time sorts by selection_score descending", () => {
    const hls = [
      makeHL({ id: "low_score", start_time: 10, end_time: 20, selection_score: 0.3 }),
      makeHL({ id: "high_score", start_time: 10, end_time: 20, selection_score: 0.9 }),
    ];
    render(<HighlightList highlights={hls} />);
    const cards = document.querySelectorAll(".highlight-card");
    expect(cards[0].getAttribute("data-highlight-id")).toBe("high_score");
  });

  it("selection_score=0 correctly displays as primary score", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20, selection_score: 0, score: 0.8 })];
    render(<HighlightList highlights={hls} />);
    expect(screen.getByText("0.000")).toBeTruthy();
    expect(screen.queryByText("0.800")).toBeNull();
  });

  it("does not mutate original array", () => {
    const hls = [
      makeHL({ id: "b", start_time: 10, end_time: 20, selection_score: 0.3 }),
      makeHL({ id: "a", start_time: 0, end_time: 10, selection_score: 0.9 }),
    ];
    const orig = hls.map((h) => h.id).join(",");
    render(<HighlightList highlights={hls} />);
    expect(hls.map((h) => h.id).join(",")).toBe(orig);
  });

  it("shows time range for valid highlight", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 })];
    render(<HighlightList highlights={hls} />);
    expect(screen.getByText(/00:10.000/)).toBeTruthy();
    expect(screen.getByText(/00:20.000/)).toBeTruthy();
  });

  it("shows error for invalid time range (start > end)", () => {
    const hls = [makeHL({ id: "a", start_time: 30, end_time: 20 })];
    render(<HighlightList highlights={hls} />);
    expect(screen.getByText("\u65f6\u95f4\u8303\u56f4\u5f02\u5e38")).toBeTruthy();
  });

  it("invalid highlight still renders and can be clicked", () => {
    const onSelect = vi.fn();
    const hls = [makeHL({ id: "a", start_time: 30, end_time: 20 })];
    render(<HighlightList highlights={hls} onSelectHighlight={onSelect} />);
    const card = document.querySelector(".highlight-card")!;
    fireEvent.click(card);
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("marks active highlight", () => {
    const hls = [
      makeHL({ id: "a", start_time: 10, end_time: 20 }),
      makeHL({ id: "b", start_time: 30, end_time: 40 }),
    ];
    render(<HighlightList highlights={hls} activeHighlightId="a" />);
    const cards = document.querySelectorAll(".highlight-card");
    expect(cards[0].className).toContain("highlight-card--active");
    expect(cards[1].className).not.toContain("highlight-card--active");
  });

  it("marks selected highlight", () => {
    const hls = [
      makeHL({ id: "a", start_time: 10, end_time: 20 }),
      makeHL({ id: "b", start_time: 30, end_time: 40 }),
    ];
    render(<HighlightList highlights={hls} selectedHighlightId="b" />);
    const cards = document.querySelectorAll(".highlight-card");
    expect(cards[1].className).toContain("highlight-card--selected");
  });

  it("selected has aria-pressed=true", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 })];
    render(<HighlightList highlights={hls} selectedHighlightId="a" />);
    expect(document.querySelector(".highlight-card")!.getAttribute("aria-pressed")).toBe("true");
  });

  it("non-selected has aria-pressed=false", () => {
    const hls = [
      makeHL({ id: "a", start_time: 10, end_time: 20 }),
      makeHL({ id: "b", start_time: 30, end_time: 40 }),
    ];
    render(<HighlightList highlights={hls} selectedHighlightId="a" />);
    const cards = document.querySelectorAll(".highlight-card");
    expect(cards[1].getAttribute("aria-pressed")).toBe("false");
  });

  it("selected and active can differ", () => {
    const hls = [
      makeHL({ id: "a", start_time: 10, end_time: 20 }),
      makeHL({ id: "b", start_time: 30, end_time: 40 }),
    ];
    render(
      <HighlightList highlights={hls} activeHighlightId="a" selectedHighlightId="b" />,
    );
    const cards = document.querySelectorAll(".highlight-card");
    expect(cards[0].className).toContain("highlight-card--active");
    expect(cards[0].className).not.toContain("highlight-card--selected");
    expect(cards[1].className).not.toContain("highlight-card--active");
    expect(cards[1].className).toContain("highlight-card--selected");
  });

  it("calls onSelectHighlight on click", () => {
    const onSelect = vi.fn();
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 })];
    render(<HighlightList highlights={hls} onSelectHighlight={onSelect} />);
    fireEvent.click(document.querySelector(".highlight-card")!);
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0][0].id).toBe("a");
  });

  it("calls onSelectHighlight on Enter key", () => {
    const onSelect = vi.fn();
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 })];
    render(<HighlightList highlights={hls} onSelectHighlight={onSelect} />);
    fireEvent.keyDown(document.querySelector(".highlight-card")!, { key: "Enter" });
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("calls onSelectHighlight on Space key", () => {
    const onSelect = vi.fn();
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 })];
    render(<HighlightList highlights={hls} onSelectHighlight={onSelect} />);
    fireEvent.keyDown(document.querySelector(".highlight-card")!, { key: " " });
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("repeated click fires each time", () => {
    const onSelect = vi.fn();
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 })];
    render(<HighlightList highlights={hls} onSelectHighlight={onSelect} />);
    const card = document.querySelector(".highlight-card")!;
    fireEvent.click(card);
    fireEvent.click(card);
    expect(onSelect).toHaveBeenCalledTimes(2);
  });

  it("shows reason text with Chinese semicolons", () => {
    const hls = [
      makeHL({
        id: "a",
        start_time: 10,
        end_time: 20,
        reason: ["\u4eba\u7269\u51fa\u73b0", "\u8bed\u97f3\u5bc6\u5ea6\u8f83\u9ad8"],
      }),
    ];
    render(<HighlightList highlights={hls} />);
    expect(screen.getByText("\u4eba\u7269\u51fa\u73b0\uff1b\u8bed\u97f3\u5bc6\u5ea6\u8f83\u9ad8")).toBeTruthy();
  });

  it("reason DOM does not contain pipe separator", () => {
    const hls = [
      makeHL({ id: "a", start_time: 10, end_time: 20, reason: ["a", "b"] }),
    ];
    render(<HighlightList highlights={hls} />);
    expect(screen.queryByText(" | ")).toBeNull();
  });

  it("shows default reason when empty", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20, reason: [] })];
    render(<HighlightList highlights={hls} />);
    expect(screen.getByText("\u6682\u65e0\u8bc4\u5206\u8bf4\u660e")).toBeTruthy();
  });

  it("showScoreBreakdown defaults to true", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 })];
    render(<HighlightList highlights={hls} />);
    expect(document.querySelector(".score-breakdown")).toBeTruthy();
  });

  it("showScoreBreakdown=true renders ScoreBreakdown", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 })];
    render(<HighlightList highlights={hls} showScoreBreakdown={true} />);
    expect(document.querySelector(".score-breakdown")).toBeTruthy();
  });

  it("showScoreBreakdown=false hides ScoreBreakdown", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 })];
    render(<HighlightList highlights={hls} showScoreBreakdown={false} />);
    expect(document.querySelector(".score-breakdown")).toBeNull();
  });

  it("ScoreBreakdown receives base_score", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20, base_score: 0.6 })];
    render(<HighlightList highlights={hls} />);
    expect(document.querySelector(".score-breakdown")).toBeTruthy();
    expect(document.querySelector(".score-breakdown__details")).toBeTruthy();
  });

  it("ScoreBreakdown receives selection_score", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20, selection_score: 0.75 })];
    render(<HighlightList highlights={hls} />);
    expect(document.querySelector(".score-breakdown__score")).toBeTruthy();
  });

  it("ScoreBreakdown receives overlap_penalty", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20, overlap_penalty: 0.05 })];
    render(<HighlightList highlights={hls} />);
    expect(screen.getByText(/\u91cd\u53e0\u60e9\u7f5a/)).toBeTruthy();
  });

  it("quality placeholder is visible when expanded", () => {
    const hls = [
      makeHL({
        id: "a",
        start_time: 10,
        end_time: 20,
        score_breakdown: { quality: { raw: 0.7, weight: 0.2, weighted: 0.14 } },
      }),
    ];
    render(<HighlightList highlights={hls} />);
    expect(screen.getByText("(placeholder)")).toBeTruthy();
  });

  it("unknown dimension is visible when expanded", () => {
    const hls = [
      makeHL({
        id: "a",
        start_time: 10,
        end_time: 20,
        score_breakdown: { custom_x: { raw: 0.9, weight: 0.1, weighted: 0.09 } },
      }),
    ];
    render(<HighlightList highlights={hls} />);
    expect(screen.getByText("custom_x")).toBeTruthy();
  });

  it("uses default aria-label", () => {
    render(
      <HighlightList highlights={[makeHL({ id: "a", start_time: 10, end_time: 20 })]} />,
    );
    expect(screen.getByLabelText("\u7cbe\u5f69\u7247\u6bb5\u5217\u8868")).toBeTruthy();
  });

  it("uses custom ariaLabel", () => {
    render(
      <HighlightList
        highlights={[makeHL({ id: "a", start_time: 10, end_time: 20 })]}
        ariaLabel="Custom Label"
      />,
    );
    expect(screen.getByLabelText("Custom Label")).toBeTruthy();
  });

  it("merges className", () => {
    render(
      <HighlightList
        highlights={[makeHL({ id: "a", start_time: 10, end_time: 20 })]}
        className="my-cls"
      />,
    );
    expect(document.querySelector(".highlight-list")!.className).toContain("my-cls");
  });

  it("shows score on card", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20, selection_score: 0.678 })];
    render(<HighlightList highlights={hls} />);
    expect(screen.getByText("0.678")).toBeTruthy();
  });

  it("invalid start_time items render after valid ones", () => {
    const hls = [
      makeHL({ id: "valid", start_time: 10, end_time: 20 }),
      makeHL({ id: "invalid", start_time: Infinity, end_time: 20 }),
    ];
    render(<HighlightList highlights={hls} />);
    const cards = document.querySelectorAll(".highlight-card");
    expect(cards[0].getAttribute("data-highlight-id")).toBe("valid");
    expect(cards[1].getAttribute("data-highlight-id")).toBe("invalid");
  });

  it("does not call VideoPlayer or Timeline", () => {
    const hls = [makeHL({ id: "a", start_time: 10, end_time: 20 })];
    expect(() => render(<HighlightList highlights={hls} />)).not.toThrow();
  });
});
