import React, { forwardRef, useImperativeHandle, useMemo, useCallback } from "react";
import { useVideoPlayback } from "../hooks/useVideoPlayback";
import type {
  VideoPlayerProps,
  VideoPlayerHandle,
  PlaybackSegment,
} from "../types/playback";
import { getMediaErrorMessage } from "../types/playback";
import { resolveApiUrl } from "../api";

const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(
  (
    {
      src,
      segment,
      seekRequest,
      segmentEndTolerance = 0.1,
      className,
      ariaLabel = "\u89c6\u9891\u64ad\u653e\u5668",
      onTimeUpdate,
      onDurationChange,
      onPlayingChange,
      onSegmentEnd,
      onError,
      onLoadedMetadata,
    },
    ref,
  ) => {
    const safeSrc = useMemo(() => resolveApiUrl(src), [src]);
    const urlError = useMemo(() => {
      if (!src) return null;
      if (!safeSrc) return "\u89c6\u9891\u8d44\u6e90\u5730\u5740\u4e0d\u53ef\u7528";
      return null;
    }, [src, safeSrc]);

    const hookOptions = useMemo(
      () => ({
        src: safeSrc,
        segment,
        seekRequest,
        segmentEndTolerance,
        onTimeUpdate,
        onDurationChange,
        onPlayingChange,
        onSegmentEnd,
        onError,
      }),
      [
        safeSrc,
        segment,
        seekRequest,
        segmentEndTolerance,
        onTimeUpdate,
        onDurationChange,
        onPlayingChange,
        onSegmentEnd,
        onError,
      ],
    );

    const {
      videoRef,
      currentTime,
      duration,
      playing,
      mediaError,
      play,
      pause,
      seek,
      playSegment,
      clearSegment,
    } = useVideoPlayback(hookOptions);

    useImperativeHandle(
      ref,
      () => ({
        play,
        pause,
        seek,
        playSegment,
        clearSegment,
        getCurrentTime: () => currentTime,
        getDuration: () => duration,
        getPlaying: () => playing,
      }),
      [play, pause, seek, playSegment, clearSegment, currentTime, duration, playing],
    );

    const displayError = mediaError || urlError;

    const handleLoadedMetadata = useCallback(() => {
      onLoadedMetadata?.();
    }, [onLoadedMetadata]);

    return (
      <div className={className} style={{ position: "relative" }}>
        {safeSrc ? (
          <video
            ref={videoRef}
            src={safeSrc}
            controls
            preload="metadata"
            aria-label={ariaLabel}
            style={{ width: "100%", display: "block" }}
            onLoadedMetadata={handleLoadedMetadata}
          >
            {"\u60a8\u7684\u6d4f\u89c8\u5668\u4e0d\u652f\u6301 HTML5 \u89c6\u9891\u64ad\u653e\u3002"}
          </video>
        ) : (
          <div
            style={{
              width: "100%",
              aspectRatio: "16 / 9",
              background: "#f0f0f0",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#999",
              fontSize: "14px",
            }}
          >
            {displayError || "\u65e0\u89c6\u9891\u6e90"}
          </div>
        )}
      </div>
    );
  },
);

VideoPlayer.displayName = "VideoPlayer";

export default VideoPlayer;
