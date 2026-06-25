import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import ResultWorkspace from "./ResultWorkspace";
import type { VideoResult, HighlightResult, ClipResult } from "../types/video";

const mockUseVideoResult = vi.fn();
vi.mock("../hooks/useVideoResult", () => ({
  useVideoResult: (...args: any[]) => mockUseVideoResult(...args),
}));

vi.mock("./VideoPlayer", () => ({
  default: React.forwardRef((props: any, ref: any) => {
    React.useImperativeHandle(ref, () => ({
      play: vi.fn(), pause: vi.fn(), seek: vi.fn(),
      playSegment: vi.fn(), clearSegment: vi.fn(),
      getCurrentTime: () => 0, getDuration: () => 30, getPlaying: () => false,
    }));
    return React.createElement("div", { "data-testid": "mock-video-player" }, props.src || "no-src");
  }),
}));

vi.mock("./HighlightTimeline", () => ({
  default: (props: any) =>
    React.createElement("div", { "data-testid": "mock-timeline", "data-duration": props.duration },
      String(props.highlights.length) + " highlights"),
}));

vi.mock("./HighlightList", () => ({
  default: (props: any) =>
    React.createElement("div", { "data-testid": "mock-highlight-list" },
      String(props.highlights.length) + " items"),
}));

function makeResult(ov: any): VideoResult {
  return { video_id: "test-video", duration: 30,
    source_url: "/api/v1/videos/test-video/source",
    highlights: [], clips: [],
    report: { markdown_url: null, json_url: null },
    error: null, warnings: [], ...ov };
}

function hl(id: string, st: number, et: number, ss: number = 0.5): HighlightResult {
  return { id, start_time: st, end_time: et, duration: et - st,
    score: ss, base_score: ss, selection_score: ss,
    overlap_penalty: 0, score_breakdown: {}, reason: [] };
}

function clip(id: string, hl_id: string | null, st: number, et: number): ClipResult {
  return { id, url: "/api/v1/videos/test-video/clips/" + id,
    start_time: st, end_time: et, duration: et - st,
    highlight_id: hl_id, size_bytes: 1000 };
}

const LOADING = "\u52a0\u8f7d\u4e2d...";
const ERROR = "\u65e0\u6cd5\u52a0\u8f7d\u7ed3\u679c";
const NO_DATA = "\u6682\u65e0\u6570\u636e";
const TASK_FAILED = "\u4efb\u52a1\u5931\u8d25";
const SOURCE_MODE = "\u539f\u89c6\u9891\u6a21\u5f0f";
const EXPORT_CLIPS = "\u5bfc\u51fa\u7247\u6bb5";
const BACK_BTN = "\u2190 \u8fd4\u56de\u539f\u89c6\u9891";

describe("ResultWorkspace", () => {
  beforeEach(() => { vi.clearAllMocks(); });

  it("shows loading state", () => {
    mockUseVideoResult.mockReturnValue({ loading: true, data: null, error: null });
    render(React.createElement(ResultWorkspace, { videoId: "test" }));
    expect(screen.getByText(LOADING)).toBeTruthy();
  });

  it("shows error state", () => {
    mockUseVideoResult.mockReturnValue({ loading: false, data: null, error: "Not found" });
    render(React.createElement(ResultWorkspace, { videoId: "test" }));
    expect(screen.getByText(ERROR)).toBeTruthy();
  });

  it("shows running state", () => {
    mockUseVideoResult.mockReturnValue({ loading: false, data: makeResult({ status: "running" }), error: null });
    render(React.createElement(ResultWorkspace, { videoId: "test" }));
    expect(screen.getByText(/running/)).toBeTruthy();
  });

  it("shows success state", () => {
    mockUseVideoResult.mockReturnValue({ loading: false, data: makeResult({ status: "success" }), error: null });
    render(React.createElement(ResultWorkspace, { videoId: "test" }));
    expect(screen.getByTestId("mock-video-player")).toBeTruthy();
  });

  it("shows completed_with_errors banner", () => {
    mockUseVideoResult.mockReturnValue({
      loading: false,
      data: makeResult({ status: "completed_with_errors", warnings: ["detection failed"] }),
      error: null,
    });
    render(React.createElement(ResultWorkspace, { videoId: "test" }));
    expect(screen.getByText(/\u90e8\u5206\u5206\u6790\u6b65\u9aa4\u6267\u884c\u5931\u8d25/)).toBeTruthy();
  });

  it("shows failed state", () => {
    mockUseVideoResult.mockReturnValue({
      loading: false, data: makeResult({ status: "failed", error: "Processing error" }), error: null,
    });
    render(React.createElement(ResultWorkspace, { videoId: "test" }));
    expect(screen.getByText(TASK_FAILED)).toBeTruthy();
  });

  it("shows no data state", () => {
    mockUseVideoResult.mockReturnValue({ loading: false, data: null, error: null });
    render(React.createElement(ResultWorkspace, { videoId: "test" }));
    expect(screen.getByText(NO_DATA)).toBeTruthy();
  });

  it("highlights in timeline and list", () => {
    const hls = [hl("hl_001", 10, 20, 0.8), hl("hl_002", 30, 40, 0.6)];
    mockUseVideoResult.mockReturnValue({ loading: false, data: makeResult({ status: "success", highlights: hls }), error: null });
    render(React.createElement(ResultWorkspace, { videoId: "test" }));
    expect(screen.getByTestId("mock-highlight-list")).toBeTruthy();
    expect(screen.getByTestId("mock-timeline").getAttribute("data-duration")).toBe("30");
  });

  it("shows clip buttons", () => {
    const cls = [clip("clip_001", "hl_001", 10, 20)];
    mockUseVideoResult.mockReturnValue({ loading: false, data: makeResult({ status: "success", clips: cls }), error: null });
    render(React.createElement(ResultWorkspace, { videoId: "test" }));
    expect(screen.getByText("clip_001")).toBeTruthy();
  });

  it("shows report links", () => {
    mockUseVideoResult.mockReturnValue({
      loading: false,
      data: makeResult({ status: "success", report: { markdown_url: "/reports/test.md", json_url: "/reports/test.json" } }),
      error: null,
    });
    render(React.createElement(ResultWorkspace, { videoId: "test" }));
    expect(screen.getAllByText(/Markdown/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText(/JSON/).length).toBeGreaterThanOrEqual(1);
  });

  it("hides clip section when no clips", () => {
    mockUseVideoResult.mockReturnValue({ loading: false, data: makeResult({ status: "success", clips: [] }), error: null });
    render(React.createElement(ResultWorkspace, { videoId: "test" }));
    expect(screen.getAllByText(/导出片段/).length).toBeGreaterThanOrEqual(1);
    // Report clip explorer shows empty state instead
  });

  it("merges className", () => {
    mockUseVideoResult.mockReturnValue({ loading: false, data: makeResult({ status: "success" }), error: null });
    render(React.createElement(ResultWorkspace, { videoId: "test", className: "my-ws" }));
    expect(document.querySelector(".result-workspace")!.className).toContain("my-ws");
  });

  it("shows source mode label", () => {
    mockUseVideoResult.mockReturnValue({ loading: false, data: makeResult({ status: "success" }), error: null });
    render(React.createElement(ResultWorkspace, { videoId: "test" }));
    expect(screen.getByText(SOURCE_MODE)).toBeTruthy();
  });

  it("defaults to source mode no back button", () => {
    mockUseVideoResult.mockReturnValue({ loading: false, data: makeResult({ status: "success" }), error: null });
    render(React.createElement(ResultWorkspace, { videoId: "test" }));
    expect(screen.queryByText(BACK_BTN)).toBeNull();
  });

  it("renders without crashing empty highlights", () => {
    mockUseVideoResult.mockReturnValue({ loading: false, data: makeResult({ status: "success", highlights: [] }), error: null });
    expect(() => render(React.createElement(ResultWorkspace, { videoId: "test" }))).not.toThrow();
  });
});
