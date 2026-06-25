import { useRef, useState, useCallback, useEffect } from "react";
import type {
  UseVideoPlaybackOptions,
  UseVideoPlaybackReturn,
  PlaybackSegment,
  SeekRequest,
} from "../types/playback";
import { getMediaErrorMessage } from "../types/playback";

// ---- Helpers --------------------------------------------

function normalizeTime(t: number): number {
  return Number.isFinite(t) && t >= 0 ? t : 0;
}

function isFiniteNumber(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

// ---- Hook ------------------------------------------------

export function useVideoPlayback(options: UseVideoPlaybackOptions): UseVideoPlaybackReturn {
  const {
    src,
    segment,
    seekRequest,
    segmentEndTolerance = 0.1,
    onTimeUpdate,
    onDurationChange,
    onPlayingChange,
    onSegmentEnd,
    onError,
  } = options;

  const videoRef = useRef<HTMLVideoElement | null>(null);

  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [mediaError, setMediaError] = useState<string | null>(null);

  // Track the latest segment so that timeupdate can detect end.
  const segmentRef = useRef<PlaybackSegment | null>(null);
  const segmentEndFiredRef = useRef(false);

  // Track the latest seekRequest requestId to avoid stale seeks.
  const seekRequestRef = useRef<SeekRequest | null>(null);

  // Store callbacks in refs so that event listeners always call the latest version.
  const callbacksRef = useRef({
    onTimeUpdate, onDurationChange, onPlayingChange, onSegmentEnd, onError, segmentEndTolerance
  });
  callbacksRef.current = { onTimeUpdate, onDurationChange, onPlayingChange, onSegmentEnd, onError, segmentEndTolerance };

  // ---- Sync segment ref ----
  useEffect(() => {
    segmentRef.current = segment ?? null;
    segmentEndFiredRef.current = false;
  }, [segment]);

  // ---- Sync seekRequest ----
  useEffect(() => {
    if (!seekRequest) return;
    const req = seekRequest as SeekRequest;
    if (!isFiniteNumber(req.requestId) || !isFiniteNumber(req.time)) return;

    // Avoid re-seeking if this is the same requestId we already processed.
    if (seekRequestRef.current && seekRequestRef.current.requestId === req.requestId) return;
    seekRequestRef.current = { time: req.time, requestId: req.requestId, autoplay: req.autoplay };

    const el = videoRef.current;
    if (!el) return;

    const t = normalizeTime(req.time);
    el.currentTime = t;
    if (req.autoplay) {
      const p = el.play();
      if (p !== undefined) p.catch(() => {});
    }
  }, [seekRequest]);

  // ---- Event handlers ----
  useEffect(() => {
    const el = videoRef.current;
    if (!el) return;

    const handleTimeUpdate = () => {
      const ct = el.currentTime;
      setCurrentTime(ct);
      callbacksRef.current.onTimeUpdate?.(ct);

      // Segment end detection
      const seg = segmentRef.current;
      if (!seg || segmentEndFiredRef.current) return;
      const endTime = normalizeTime(seg.endTime);
      const tolerance = callbacksRef.current.segmentEndTolerance;
      if (ct >= endTime - tolerance) {
        segmentEndFiredRef.current = true;
        el.pause();
        callbacksRef.current.onSegmentEnd?.(seg);
      }
    };

    const handleDurationChange = () => {
      const d = el.duration;
      if (isFiniteNumber(d)) {
        setDuration(d);
        callbacksRef.current.onDurationChange?.(d);
      }
    };

    const handlePlay = () => {
      setPlaying(true);
      callbacksRef.current.onPlayingChange?.(true);
    };

    const handlePause = () => {
      setPlaying(false);
      callbacksRef.current.onPlayingChange?.(false);
    };

    const handleError = () => {
      const msg = getMediaErrorMessage(el.error);
      setMediaError(msg);
      callbacksRef.current.onError?.(msg);
    };

    const handleLoadedMetadata = () => {
      const d = el.duration;
      if (isFiniteNumber(d)) {
        setDuration(d);
        callbacksRef.current.onDurationChange?.(d);
      }
    };

    el.addEventListener("timeupdate", handleTimeUpdate);
    el.addEventListener("durationchange", handleDurationChange);
    el.addEventListener("play", handlePlay);
    el.addEventListener("pause", handlePause);
    el.addEventListener("error", handleError);
    el.addEventListener("loadedmetadata", handleLoadedMetadata);

    return () => {
      el.removeEventListener("timeupdate", handleTimeUpdate);
      el.removeEventListener("durationchange", handleDurationChange);
      el.removeEventListener("play", handlePlay);
      el.removeEventListener("pause", handlePause);
      el.removeEventListener("error", handleError);
      el.removeEventListener("loadedmetadata", handleLoadedMetadata);
    };
  }, []);

  // ---- Segment auto-play ----
  useEffect(() => {
    if (!segment) return;
    const el = videoRef.current;
    if (!el) return;

    const startTime = normalizeTime(segment.startTime);
    el.currentTime = startTime;
    segmentEndFiredRef.current = false;

    const p = el.play();
    if (p !== undefined) p.catch(() => {});
  }, [segment]);

  // ---- Src change: reset state ----
  useEffect(() => {
    setCurrentTime(0);
    setDuration(0);
    setPlaying(false);
    setMediaError(null);
    segmentRef.current = null;
    segmentEndFiredRef.current = false;
    seekRequestRef.current = null;
  }, [src]);

  // ---- Imperative methods ----

  const play = useCallback(async (): Promise<boolean> => {
    const el = videoRef.current;
    if (!el) return false;
    try {
      await el.play();
      return true;
    } catch {
      return false;
    }
  }, []);

  const pause = useCallback(() => {
    videoRef.current?.pause();
  }, []);

  const seek = useCallback(async (time: number, autoplay?: boolean): Promise<boolean> => {
    const el = videoRef.current;
    if (!el) return false;
    el.currentTime = normalizeTime(time);
    if (autoplay) {
      try {
        await el.play();
        return true;
      } catch {
        return false;
      }
    }
    return true;
  }, []);

  const playSegment = useCallback(async (seg: PlaybackSegment): Promise<boolean> => {
    const el = videoRef.current;
    if (!el) return false;

    segmentRef.current = seg;
    segmentEndFiredRef.current = false;
    el.currentTime = normalizeTime(seg.startTime);

    try {
      await el.play();
      return true;
    } catch {
      return false;
    }
  }, []);

  const clearSegment = useCallback(() => {
    segmentRef.current = null;
    segmentEndFiredRef.current = false;
  }, []);

  return {
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
  };
}
