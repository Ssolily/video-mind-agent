import type { HighlightResult } from "../types/video";

export interface NormalizedHighlightRange {
  startTime: number;
  endTime: number;
  duration: number;
}

function safeFinite(v: unknown, fallback = 0): number {
  return typeof v === "number" && Number.isFinite(v) ? v : fallback;
}

export function normalizeHighlightRange(
  highlight: Pick<HighlightResult, "start_time" | "end_time">,
  videoDuration: number,
): NormalizedHighlightRange | null {
  const dur = safeFinite(videoDuration);
  if (dur <= 0) return null;
  if (typeof highlight.start_time !== "number" || !Number.isFinite(highlight.start_time)) return null;
  if (typeof highlight.end_time !== "number" || !Number.isFinite(highlight.end_time)) return null;
  const st = Math.max(0, Math.min(highlight.start_time, dur));
  const et = Math.max(0, Math.min(highlight.end_time, dur));
  if (et <= st) return null;
  return { startTime: st, endTime: et, duration: et - st };
}

export function findActiveHighlight(
  highlights: HighlightResult[],
  currentTime: number,
  videoDuration: number,
  selectedHighlightId?: string | null,
): HighlightResult | null {
  if (!Array.isArray(highlights)) return null;
  const ct = safeFinite(currentTime);
  const candidates: HighlightResult[] = [];
  for (const hl of highlights) {
    const range = normalizeHighlightRange(hl, videoDuration);
    if (!range) continue;
    if (ct >= range.startTime && ct < range.endTime) {
      candidates.push(hl);
    }
  }
  if (candidates.length === 0) return null;
  if (candidates.length === 1) return candidates[0];
  const safeScore = (hl: HighlightResult): number => {
    const s = hl.selection_score ?? hl.score ?? 0;
    return Number.isFinite(s) ? s : -Infinity;
  };
  candidates.sort((a, b) => {
    if (selectedHighlightId != null) {
      if (a.id === selectedHighlightId) return -1;
      if (b.id === selectedHighlightId) return 1;
    }
    const sDiff = safeScore(b) - safeScore(a);
    if (sDiff !== 0) return sDiff;
    const stDiff = a.start_time - b.start_time;
    if (stDiff !== 0) return stDiff;
    const etDiff = a.end_time - b.end_time;
    if (etDiff !== 0) return etDiff;
    return a.id.localeCompare(b.id);
  });
  return candidates[0];
}

export function highlightLeftPercent(range: NormalizedHighlightRange, videoDuration: number): number {
  const dur = safeFinite(videoDuration);
  if (dur <= 0) return 0;
  return Math.min(100, Math.max(0, (range.startTime / dur) * 100));
}

export function highlightWidthPercent(range: NormalizedHighlightRange, videoDuration: number): number {
  const dur = safeFinite(videoDuration);
  if (dur <= 0) return 0;
  const left = highlightLeftPercent(range, videoDuration);
  return Math.min(100 - left, Math.max(0, (range.duration / dur) * 100));
}

export function playheadLeftPercent(currentTime: number, videoDuration: number): number {
  const dur = safeFinite(videoDuration);
  if (dur <= 0) return 0;
  const ct = Math.max(0, Math.min(safeFinite(currentTime), dur));
  return (ct / dur) * 100;
}

export function xToTime(clientX: number, trackRect: { left: number; width: number }, videoDuration: number): number {
  const dur = safeFinite(videoDuration);
  if (dur <= 0 || trackRect.width <= 0) return 0;
  const ratio = (clientX - trackRect.left) / trackRect.width;
  return Math.max(0, Math.min(ratio * dur, dur));
}
