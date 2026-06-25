import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ScoreBreakdown from "./ScoreBreakdown";
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

describe("ScoreBreakdown", () => {
  it("renders main score in summary", () => {
    render(
      <ScoreBreakdown highlight={makeHL({ start_time: 0, end_time: 10, selection_score: 0.75 })} />,
    );
    const matches = screen.getAllByText(/0.750/);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  it("shows base_score in summary when present", () => {
    render(
      <ScoreBreakdown highlight={makeHL({ start_time: 0, end_time: 10, base_score: 0.6 })} />,
    );
    expect(screen.getByText(/0.600/)).toBeTruthy();
  });

  it("shows base_score label text", () => {
    render(
      <ScoreBreakdown highlight={makeHL({ start_time: 0, end_time: 10, base_score: 0.6 })} />,
    );
    const match = screen.getByText(/\u57fa\u7840\u5f97\u5206/);
    expect(match).toBeTruthy();
  });

  it("shows selection_score label in body when expanded", () => {
    render(
      <ScoreBreakdown highlight={makeHL({ start_time: 0, end_time: 10, selection_score: 0.75 })} defaultExpanded={true} />,
    );
    expect(screen.getByText(/\u9009\u5165\u5f97\u5206/)).toBeTruthy();
  });

  it("shows overlap_penalty when > 0", () => {
    render(
      <ScoreBreakdown highlight={makeHL({ start_time: 0, end_time: 10, overlap_penalty: 0.05 })} defaultExpanded={true} />,
    );
    expect(screen.getByText(/\u91cd\u53e0\u60e9\u7f5a/)).toBeTruthy();
  });

  it("collapsed by default has open=false on details", () => {
    const hl = makeHL({
      start_time: 0,
      end_time: 10,
      score_breakdown: { object: { raw: 0.8, weight: 0.25, weighted: 0.2 } },
    });
    render(<ScoreBreakdown highlight={hl} />);
    const details = document.querySelector("details");
    expect(details).not.toBeNull();
    expect(details!.hasAttribute("open")).toBe(false);
  });

  it("defaultExpanded=true sets open attribute", () => {
    const hl = makeHL({
      start_time: 0,
      end_time: 10,
      score_breakdown: { object: { raw: 0.8, weight: 0.25, weighted: 0.2 } },
    });
    render(<ScoreBreakdown highlight={hl} defaultExpanded={true} />);
    const details = document.querySelector("details");
    expect(details).not.toBeNull();
    expect(details!.hasAttribute("open")).toBe(true);
  });

  it("no breakdown and no base_score renders minimal view without details", () => {
    const hl = makeHL({ start_time: 0, end_time: 10 });
    const minimalHL = { ...hl, base_score: undefined as any };
    render(<ScoreBreakdown highlight={minimalHL} />);
    expect(document.querySelector("details")).toBeNull();
  });

  it("marks quality as placeholder", () => {
    const hl = makeHL({
      start_time: 0,
      end_time: 10,
      score_breakdown: { quality: { raw: 0.7, weight: 0.2, weighted: 0.14 } },
    });
    render(<ScoreBreakdown highlight={hl} defaultExpanded={true} />);
    expect(screen.getByText("(placeholder)")).toBeTruthy();
  });

  it("merges className", () => {
    render(
      <ScoreBreakdown highlight={makeHL({ start_time: 0, end_time: 10 })} className="my-cls" />,
    );
    expect(document.querySelector(".score-breakdown")!.className).toContain("my-cls");
  });

  it("renders dimension with raw x weight = weighted format", () => {
    const hl = makeHL({
      start_time: 0,
      end_time: 10,
      score_breakdown: { object: { raw: 0.8, weight: 0.25, weighted: 0.2 } },
    });
    render(<ScoreBreakdown highlight={hl} defaultExpanded={true} />);
    expect(screen.getByText("0.800")).toBeTruthy();
    expect(screen.getByText("0.250")).toBeTruthy();
    expect(screen.getByText("0.200")).toBeTruthy();
  });

  it("shows unknown dimension in expanded state", () => {
    const hl = makeHL({
      start_time: 0,
      end_time: 10,
      score_breakdown: { custom_x: { raw: 0.9, weight: 0.1, weighted: 0.09 } },
    });
    render(<ScoreBreakdown highlight={hl} defaultExpanded={true} />);
    expect(screen.getByText("custom_x")).toBeTruthy();
  });

  it("shows both base and selected scores when expanded", () => {
    const hl = makeHL({
      start_time: 0,
      end_time: 10,
      base_score: 0.7,
      selection_score: 0.65,
      score_breakdown: { object: { raw: 0.8, weight: 0.25, weighted: 0.2 } },
    });
    render(<ScoreBreakdown highlight={hl} defaultExpanded={true} />);
    expect(screen.getByText(/0.700/)).toBeTruthy();
    const scoreMatches = screen.getAllByText(/0.650/);
    expect(scoreMatches.length).toBeGreaterThanOrEqual(2);
  });

  it("show both base and overlap penalty labels when expanded", () => {
    const hl = makeHL({
      start_time: 0,
      end_time: 10,
      base_score: 0.7,
      selection_score: 0.65,
      overlap_penalty: 0.05,
      score_breakdown: { object: { raw: 0.8, weight: 0.25, weighted: 0.2 } },
    });
    render(<ScoreBreakdown highlight={hl} defaultExpanded={true} />);
    expect(screen.getByText(/\u57fa\u7840\u5f97\u5206/)).toBeTruthy();
    expect(screen.getByText(/\u9009\u5165\u5f97\u5206/)).toBeTruthy();
    expect(screen.getByText(/\u91cd\u53e0\u60e9\u7f5a/)).toBeTruthy();
  });
});
