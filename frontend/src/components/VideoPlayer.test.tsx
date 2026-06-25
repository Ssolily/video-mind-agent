import React from "react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import VideoPlayer from "./VideoPlayer";
import type { PlaybackSegment, SeekRequest, VideoPlayerHandle } from "../types/playback";
import * as api from "../api";

// ---- Mock resolveApiUrl ----
vi.mock("../api", () => ({
  resolveApiUrl: vi.fn((url: string | null | undefined) => {
    if (!url) return null;
    if (/^[A-Za-z]:\\/.test(url)) return null;
    if (url.startsWith("javascript:") || url.startsWith("data:")) return null;
    if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("/")) return url;
    return url;
  }),
}));

// ---- Create a ref creator helper ----
function createRef() {
  return React.createRef<VideoPlayerHandle>();
}

// ---- Tests ----

describe("VideoPlayer", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders placeholder when src is null", () => {
    render(React.createElement(VideoPlayer, { src: null }));
    expect(screen.getByText("\u65e0\u89c6\u9891\u6e90")).toBeTruthy();
  });

  it("renders <video> element when src is provided", () => {
    render(React.createElement(VideoPlayer, { src: "/api/v1/videos/abc/source" }));
    const video = document.querySelector("video");
    expect(video).toBeTruthy();
    expect(video!.getAttribute("aria-label")).toBe("\u89c6\u9891\u64ad\u653e\u5668");
  });

  it("sets video src to resolved URL", () => {
    render(React.createElement(VideoPlayer, { src: "/api/v1/videos/abc/source" }));
    const video = document.querySelector("video")!;
    expect(video.src).toContain("/api/v1/videos/abc/source");
  });

  it("video has controls and preload metadata", () => {
    render(React.createElement(VideoPlayer, { src: "/test.mp4" }));
    const video = document.querySelector("video")!;
    expect(video.controls).toBe(true);
    expect(video.preload).toBe("metadata");
  });

  it("rejects Windows absolute path", () => {
    render(React.createElement(VideoPlayer, { src: "D:\\videos\\test.mp4" }));
    expect(screen.queryByText("\u89c6\u9891\u8d44\u6e90\u5730\u5740\u4e0d\u53ef\u7528")).toBeTruthy();
    expect(document.querySelector("video")).toBeNull();
  });

  it("rejects javascript: URL", () => {
    render(React.createElement(VideoPlayer, { src: "javascript:alert(1)" }));
    expect(screen.queryByText("\u89c6\u9891\u8d44\u6e90\u5730\u5740\u4e0d\u53ef\u7528")).toBeTruthy();
  });

  it("rejects data: URL", () => {
    render(React.createElement(VideoPlayer, { src: "data:text/html,<script>" }));
    expect(screen.queryByText("\u89c6\u9891\u8d44\u6e90\u5730\u5740\u4e0d\u53ef\u7528")).toBeTruthy();
  });

  it("accepts full HTTP URL", () => {
    render(React.createElement(VideoPlayer, { src: "https://example.com/video.mp4" }));
    const video = document.querySelector("video")!;
    expect(video.src).toContain("example.com");
  });

  it("calls onTimeUpdate callback", () => {
    const onTimeUpdate = vi.fn();
    render(React.createElement(VideoPlayer, { src: "/test.mp4", onTimeUpdate }));
    const video = document.querySelector("video")!;
    act(() => { video.dispatchEvent(new Event("timeupdate")); });
    expect(onTimeUpdate).toHaveBeenCalled();
  });

  it("calls onDurationChange on loadedmetadata", () => {
    const onDurationChange = vi.fn();
    render(React.createElement(VideoPlayer, { src: "/test.mp4", onDurationChange }));
    const video = document.querySelector("video")!;
    // jsdom duration is NaN by default; set it so isFiniteNumber check passes
    Object.defineProperty(video, "duration", { get: () => 88, configurable: true });
    act(() => { video.dispatchEvent(new Event("loadedmetadata")); });
    expect(onDurationChange).toHaveBeenCalledWith(88);
  });

  it("calls onPlayingChange on play/pause events", () => {
    const onPlayingChange = vi.fn();
    render(React.createElement(VideoPlayer, { src: "/test.mp4", onPlayingChange }));
    const video = document.querySelector("video")!;

    act(() => { video.dispatchEvent(new Event("play")); });
    expect(onPlayingChange).toHaveBeenCalledWith(true);

    act(() => { video.dispatchEvent(new Event("pause")); });
    expect(onPlayingChange).toHaveBeenCalledWith(false);
  });

  it("calls onError callback on error event", () => {
    const onError = vi.fn();
    render(React.createElement(VideoPlayer, { src: "/test.mp4", onError }));
    const video = document.querySelector("video")!;

    act(() => { video.dispatchEvent(new Event("error")); });
    expect(onError).toHaveBeenCalled();
  });

  it("exposes imperative handle via ref", () => {
    const ref = createRef();
    render(React.createElement(VideoPlayer, { ref, src: "/test.mp4" }));
    expect(ref.current).toBeTruthy();
    expect(typeof ref.current!.play).toBe("function");
    expect(typeof ref.current!.pause).toBe("function");
    expect(typeof ref.current!.seek).toBe("function");
    expect(typeof ref.current!.playSegment).toBe("function");
    expect(typeof ref.current!.clearSegment).toBe("function");
    expect(typeof ref.current!.getCurrentTime).toBe("function");
    expect(typeof ref.current!.getDuration).toBe("function");
    expect(typeof ref.current!.getPlaying).toBe("function");
  });

  it("play() via imperative handle calls video.play()", async () => {
    const ref = createRef();
    render(React.createElement(VideoPlayer, { ref, src: "/test.mp4" }));
    const video = document.querySelector("video")!;
    vi.spyOn(video, "play").mockResolvedValue(undefined);

    const ok = await ref.current!.play();
    expect(ok).toBe(true);
    expect(video.play).toHaveBeenCalled();
  });

  it("seek() via imperative handle sets currentTime", async () => {
    const ref = createRef();
    render(React.createElement(VideoPlayer, { ref, src: "/test.mp4" }));
    const video = document.querySelector("video")!;

    await ref.current!.seek(42);
    expect(video.currentTime).toBeCloseTo(42, 1);
  });

  it("seek() with autoplay calls play", async () => {
    const ref = createRef();
    render(React.createElement(VideoPlayer, { ref, src: "/test.mp4" }));
    const video = document.querySelector("video")!;
    vi.spyOn(video, "play").mockResolvedValue(undefined);

    await ref.current!.seek(10, true);
    expect(video.currentTime).toBeCloseTo(10, 1);
    expect(video.play).toHaveBeenCalled();
  });

  it("playSegment() seeks to start and calls play", async () => {
    const ref = createRef();
    render(React.createElement(VideoPlayer, { ref, src: "/test.mp4" }));
    const video = document.querySelector("video")!;
    vi.spyOn(video, "play").mockResolvedValue(undefined);

    const seg: PlaybackSegment = { startTime: 5, endTime: 15 };
    const ok = await ref.current!.playSegment(seg);
    expect(ok).toBe(true);
    expect(video.currentTime).toBeCloseTo(5, 1);
    expect(video.play).toHaveBeenCalled();
  });

  it("pause() via imperative handle calls pause", () => {
    const ref = createRef();
    render(React.createElement(VideoPlayer, { ref, src: "/test.mp4" }));
    const video = document.querySelector("video")!;
    vi.spyOn(video, "pause");

    ref.current!.pause();
    expect(video.pause).toHaveBeenCalled();
  });

  it("clearSegment() via imperative handle does not throw", () => {
    const ref = createRef();
    render(React.createElement(VideoPlayer, { ref, src: "/test.mp4" }));
    expect(() => ref.current!.clearSegment()).not.toThrow();
  });

  it("getCurrentTime/getDuration/getPlaying return values", () => {
    const ref = createRef();
    render(React.createElement(VideoPlayer, { ref, src: "/test.mp4" }));
    expect(typeof ref.current!.getCurrentTime()).toBe("number");
    expect(typeof ref.current!.getDuration()).toBe("number");
    expect(typeof ref.current!.getPlaying()).toBe("boolean");
  });

  it("applies custom className", () => {
    const { container } = render(React.createElement(VideoPlayer, { src: "/test.mp4", className: "custom-class" }));
    const div = container.firstChild as HTMLElement;
    expect(div.className).toBe("custom-class");
  });

  it("renders fallback text inside <video>", () => {
    render(React.createElement(VideoPlayer, { src: "/test.mp4" }));
    const video = document.querySelector("video")!;
    expect(video.textContent).toContain("\u60a8\u7684\u6d4f\u89c8\u5668\u4e0d\u652f\u6301");
  });
});
