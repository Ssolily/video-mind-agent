/** A time segment within a video for playback. */
export interface PlaybackSegment {
  startTime: number;
  endTime: number;
  highlightId?: string | null;
}

/**
 * A seek request with an incrementing requestId.
 *
 * The requestId ensures that seeking to the same time multiple times
 * (e.g. replaying the same highlight) is always honoured.
 */
export interface SeekRequest {
  time: number;
  requestId: number;
  autoplay?: boolean;
}

/** Whether the player is showing the full video or constrained to a segment. */
export type PlaybackMode = "full" | "segment";

// ---- Playback hook options / return ------------------

export interface UseVideoPlaybackOptions {
  src: string | null;
  segment?: PlaybackSegment | null;
  seekRequest?: SeekRequest | null;
  segmentEndTolerance?: number;
  onTimeUpdate?: (currentTime: number) => void;
  onDurationChange?: (duration: number) => void;
  onPlayingChange?: (playing: boolean) => void;
  onSegmentEnd?: (segment: PlaybackSegment) => void;
  onError?: (message: string) => void;
  onLoadedMetadata?: () => void;
}

export interface UseVideoPlaybackReturn {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  currentTime: number;
  duration: number;
  playing: boolean;
  mediaError: string | null;
  play: () => Promise<boolean>;
  pause: () => void;
  seek: (time: number, autoplay?: boolean) => Promise<boolean>;
  playSegment: (segment: PlaybackSegment) => Promise<boolean>;
  clearSegment: () => void;
}

// ---- VideoPlayer component props / handle ------------

export interface VideoPlayerProps {
  src: string | null;
  segment?: PlaybackSegment | null;
  seekRequest?: SeekRequest | null;
  segmentEndTolerance?: number;
  className?: string;
  ariaLabel?: string;
  onTimeUpdate?: (currentTime: number) => void;
  onDurationChange?: (duration: number) => void;
  onPlayingChange?: (playing: boolean) => void;
  onSegmentEnd?: (segment: PlaybackSegment) => void;
  onError?: (message: string) => void;
  onLoadedMetadata?: () => void;
}

export interface VideoPlayerHandle {
  play: () => Promise<boolean>;
  pause: () => void;
  seek: (time: number, autoplay?: boolean) => Promise<boolean>;
  playSegment: (segment: PlaybackSegment) => Promise<boolean>;
  clearSegment: () => void;
  getCurrentTime: () => number;
  getDuration: () => number;
  getPlaying: () => boolean;
}

// ---- Media error messages ----------------------------

export const MEDIA_ERROR_MESSAGES: Record<number, string> = {
  1: "\u89c6\u9891\u52a0\u8f7d\u88ab\u7528\u6237\u6216\u6d4f\u89c8\u5668\u4e2d\u65ad",
  2: "\u89c6\u9891\u683c\u5f0f\u4e0d\u652f\u6301\u6216\u7f51\u7edc\u9519\u8bef",
  3: "\u89c6\u9891\u89e3\u7801\u5931\u8d25\uff0c\u7f16\u7801\u683c\u5f0f\u4e0d\u53d7\u652f\u6301",
  4: "\u89c6\u9891\u8d44\u6e90\u4e0d\u53ef\u7528\u6216\u683c\u5f0f\u4e0d\u652f\u6301",
};

export function getMediaErrorMessage(error: MediaError | null): string {
  if (!error) return "\u672a\u77e5\u5a92\u4f53\u9519\u8bef";
  return MEDIA_ERROR_MESSAGES[error.code] || "\u5a92\u4f53\u9519\u8bef (\u4ee3\u7801 " + error.code + ")";
}
