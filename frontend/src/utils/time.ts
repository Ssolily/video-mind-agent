// ---- Safe number helpers ----

function safeSeconds(v: unknown): number {
  if (typeof v !== "number" || !Number.isFinite(v) || v < 0) return 0;
  return v;
}

function pad(n: number, width: number): string {
  const s = String(Math.floor(n));
  if (s.length >= width) return s;
  return "0".repeat(width - s.length) + s;
}

// ---- Public API ----

/**
 * Format a timestamp in seconds to MM:SS.mmm or HH:MM:SS.mmm.
 *
 * Examples:
 *   0          -> "00:00.000"
 *   5.2        -> "00:05.200"
 *   42.5       -> "00:42.500"
 *   61.2       -> "01:01.200"
 *   3661.25    -> "01:01:01.250"
 */
export function formatTimestamp(seconds: number): string {
  const s = safeSeconds(seconds);
  const totalMs = Math.round(s * 1000);
  const absMs = Math.abs(totalMs);

  const ms = absMs % 1000;
  const totalSec = (absMs - ms) / 1000;
  const sec = totalSec % 60;
  const totalMin = (totalSec - sec) / 60;
  const min = totalMin % 60;
  const hr = (totalMin - min) / 60;

  if (hr > 0) {
    return `${pad(hr, 2)}:${pad(min, 2)}:${pad(sec, 2)}.${pad(ms, 3)}`;
  }
  return `${pad(min, 2)}:${pad(sec, 2)}.${pad(ms, 3)}`;
}

/**
 * Format a duration in seconds to a human-readable string.
 *
 * - Less than 60 seconds: "18.7s"
 * - 60 seconds or more: uses formatTimestamp
 */
export function formatDuration(seconds: number): string {
  const s = safeSeconds(seconds);
  if (s < 60) {
    return `${s.toFixed(1)}s`;
  }
  return formatTimestamp(s);
}
