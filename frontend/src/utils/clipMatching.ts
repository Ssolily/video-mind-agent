import type { HighlightResult, ClipResult } from "../types/video";

/**
 * Default tolerance (seconds) for time-based clip-highlight matching.
 * Must be a non-negative finite number.
 */
export const DEFAULT_CLIP_MATCH_TOLERANCE = 0.1;

/**
 * Validate tolerance value.
 * Returns the default tolerance when the given value is invalid.
 */
function validTolerance(tolerance: number | undefined | null): number {
  if (typeof tolerance !== "number" || !Number.isFinite(tolerance) || tolerance < 0) {
    return DEFAULT_CLIP_MATCH_TOLERANCE;
  }
  return tolerance;
}

/**
 * Find the best matching ClipResult for a given HighlightResult.
 *
 * Priority:
 * 1. Explicit highlight_id match (clip.highlight_id === highlight.id)
 * 2. Time-based: smallest total absolute time error, within tolerance
 * 3. No reliable match: returns null
 *
 * Never uses array index fallback.
 * Never establishes false association based on array position.
 *
 * @param highlight The highlight to match
 * @param clips Available clips
 * @param tolerance Time matching tolerance in seconds (default 0.1, must be >= 0)
 * @returns The best matching clip, or null
 */
export function findClipForHighlight(
  highlight: HighlightResult,
  clips: ClipResult[],
  tolerance?: number,
): ClipResult | null {
  if (!Array.isArray(clips) || clips.length === 0) return null;
  const tol = validTolerance(tolerance);

  // Priority 1: explicit highlight_id
  const byId = clips.find(
    (c) => c.highlight_id != null && c.highlight_id === highlight.id,
  );
  if (byId) return byId;

  // Priority 2: time-based match (best error within tolerance)
  if (
    typeof highlight.start_time !== "number" ||
    typeof highlight.end_time !== "number" ||
    !Number.isFinite(highlight.start_time) ||
    !Number.isFinite(highlight.end_time)
  ) {
    return null;
  }

  let best: ClipResult | null = null;
  let bestError = Infinity;

  for (const c of clips) {
    if (
      c.start_time == null || c.end_time == null ||
      !Number.isFinite(c.start_time) || !Number.isFinite(c.end_time)
    ) {
      continue;
    }
    const startErr = Math.abs(c.start_time - highlight.start_time);
    const endErr = Math.abs(c.end_time - highlight.end_time);
    if (startErr > tol || endErr > tol) continue;

    const totalErr = startErr + endErr;
    if (totalErr < bestError) {
      bestError = totalErr;
      best = c;
    } else if (totalErr === bestError && best != null) {
      // Tie-break by clip id ascending
      if (c.id < best.id) {
        best = c;
      }
    }
  }

  return best;
}

/**
 * Find the best matching HighlightResult for a given ClipResult.
 *
 * Priority:
 * 1. Explicit highlight_id match (clip.highlight_id ? highlights.find)
 * 2. Time-based: smallest total absolute time error, within tolerance
 * 3. No reliable match: returns null
 *
 * Never uses array index fallback.
 *
 * @param clip The clip to match
 * @param highlights Available highlights
 * @param tolerance Time matching tolerance in seconds (default 0.1, must be >= 0)
 * @returns The best matching highlight, or null
 */
export function findHighlightForClip(
  clip: ClipResult,
  highlights: HighlightResult[],
  tolerance?: number,
): HighlightResult | null {
  if (!Array.isArray(highlights) || highlights.length === 0) return null;
  const tol = validTolerance(tolerance);

  // Priority 1: explicit highlight_id
  if (clip.highlight_id != null) {
    const byId = highlights.find((h) => h.id === clip.highlight_id);
    if (byId) return byId;
  }

  // Priority 2: time-based match (best error within tolerance)
  if (
    clip.start_time == null || clip.end_time == null ||
    !Number.isFinite(clip.start_time) || !Number.isFinite(clip.end_time)
  ) {
    return null;
  }

  let best: HighlightResult | null = null;
  let bestError = Infinity;

  for (const h of highlights) {
    if (
      typeof h.start_time !== "number" || typeof h.end_time !== "number" ||
      !Number.isFinite(h.start_time) || !Number.isFinite(h.end_time)
    ) {
      continue;
    }
    const startErr = Math.abs(h.start_time - clip.start_time);
    const endErr = Math.abs(h.end_time - clip.end_time);
    if (startErr > tol || endErr > tol) continue;

    const totalErr = startErr + endErr;
    if (totalErr < bestError) {
      bestError = totalErr;
      best = h;
    } else if (totalErr === bestError && best != null) {
      if (h.id < best.id) {
        best = h;
      }
    }
  }

  return best;
}
