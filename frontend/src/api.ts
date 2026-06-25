const BASE = import.meta.env.VITE_API_BASE_URL || "";

// ── Safe URL resolution ─────────────────────────────

/** Schemes considered safe for media playback. */
const SAFE_SCHEMES = new Set(["http:", "https:", ""]);

/**
 * Resolve an API-relative URL to an absolute URL, or return null for unsafe paths.
 *
 * - Relative API URLs (e.g. ``/api/v1/...``) are prefixed with BASE.
 * - Windows absolute paths (e.g. ``D:\\...``) are rejected.
 * - Unsafe schemes (e.g. ``file:``, ``data:``) are rejected.
 */
export function resolveApiUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  // Reject Windows drive-letter paths
  if (/^[A-Za-z]:\\/.test(url) || /^[A-Za-z]:\//.test(url)) return null;
  // Reject file:, data: and other unsafe schemes
  const schemeMatch = url.match(/^([a-zA-Z][a-zA-Z0-9+.-]*):\/\//);
  const scheme = schemeMatch ? schemeMatch[1] + ":" : "";
  // Also handle data: URIs (no ://)
  if (url.startsWith("data:")) return null;
  if (scheme && !SAFE_SCHEMES.has(scheme)) return null;
  // Relative URL — prefix with BASE
  if (url.startsWith("/")) return BASE + url;
  // Already absolute http/https — return as-is
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  // Relative path without leading slash — prefix with BASE + /
  return BASE + "/" + url;
}

// ── API Error ───────────────────────────────────────

/** Structured error from API calls. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ── Normalize video result ─────────────────────────

/**
 * Normalize a raw JSON response from the Result API into a well-typed object.
 *
 * Handles:
 * - Missing or null fields from historical results.
 * - NaN / Infinity in numeric fields.
 * - Reason as a string (old format) vs array (new format).
 */
export function normalizeVideoResult(raw: any): import("./types/video").VideoResult {
  if (!raw || typeof raw !== "object") raw = {};
  const safeNum = (v: any): number => {
    if (v === null || v === undefined) return 0;
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
  };

  const highlights = (raw.highlights ?? []).map((h: any, i: number) => ({
    id: String(h.id || `hl_${i + 1}`),
    start_time: safeNum(h.start_time),
    end_time: safeNum(h.end_time),
    duration: safeNum(h.duration),
    score: safeNum(h.score ?? h.selection_score),
    base_score: safeNum(h.base_score ?? h.score ?? h.selection_score),
    selection_score: safeNum(h.selection_score ?? h.score),
    overlap_penalty: safeNum(h.overlap_penalty),
    score_breakdown: h.score_breakdown ?? {},
    reason: Array.isArray(h.reason) ? h.reason : (h.reason ? [String(h.reason)] : []),
  }));

  const clips = (raw.clips ?? []).map((c: any) => ({
    id: String(c.id || ""),
    url: String(c.url || ""),
    start_time: c.start_time != null ? safeNum(c.start_time) : null,
    end_time: c.end_time != null ? safeNum(c.end_time) : null,
    duration: c.duration != null ? safeNum(c.duration) : null,
    highlight_id: c.highlight_id != null ? String(c.highlight_id) : null,
    size_bytes: c.size_bytes != null ? safeNum(c.size_bytes) : null,
  }));

  return {
    video_id: String(raw.video_id || ""),
    status: raw.status || "uploaded",
    duration: raw.duration != null ? safeNum(raw.duration) : null,
    source_url: raw.source_url || null,
    highlights,
    clips,
    report: {
      markdown_url: raw.report?.markdown_url || null,
      json_url: raw.report?.json_url || null,
      candidates_url: raw.report?.candidates_url || null,
    },
    error: raw.error || null,
    warnings: Array.isArray(raw.warnings) ? raw.warnings : [],
  };
}

// ── Result API ─────────────────────────────────────

/**
 * Fetch the unified video result from ``GET /api/v1/videos/{video_id}/result``.
 *
 * Supports AbortController for request cancellation.
 * Returns a normalized ``VideoResult``.
 */
export async function getVideoResult(
  videoId: string,
  signal?: AbortSignal,
): Promise<import("./types/video").VideoResult> {
  const res = await fetch(BASE + "/api/v1/videos/" + encodeURIComponent(videoId) + "/result", {
    signal,
  });
  if (res.status === 404) {
    throw new ApiError("Video not found", 404, "Video not found");
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(
      body.detail || "Failed to fetch video result",
      res.status,
      body.detail || res.statusText,
    );
  }
  const raw = await res.json();
  return normalizeVideoResult(raw);
}

export interface UploadResult {
  video_id: string;
  filename: string;
  source_url: string;
  status: string;
  metadata?: { duration: number; fps: number; width: number; height: number; frame_count: number };
}

export interface TaskResult {
  task_id: string;
  video_id: string;
  user_goal: string;
  status: "pending" | "queued" | "running" | "success" | "completed" | "completed_with_errors" | "failed" | "cancelled" | "timeout" | "interrupted";
  progress: number;
  current_step: string;
  error: string | null;
  result?: {
    video_id: string;
    user_goal: string;
    plan: string[];
    steps: Array<{ step: string; status: string; detail?: string }>;
  };
}

export interface ReportResult {
  markdown: string;
  markdown_url?: string;
  json_url?: string;
}


export async function cancelTask(taskId: string): Promise<{ task_id: string; status: string }> {
  const res = await fetch(BASE + "/api/v1/tasks/" + encodeURIComponent(taskId) + "/cancel", { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Cancel failed");
  }
  return res.json();
}

export async function retryTask(taskId: string): Promise<{ task_id: string; new_task_id: string; status: string }> {
  const res = await fetch(BASE + "/api/v1/tasks/" + encodeURIComponent(taskId) + "/retry", { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Retry failed");
  }
  return res.json();
}

export async function uploadVideo(file: File): Promise<UploadResult> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(BASE + "/api/v1/videos/upload", { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

export async function startAgentRun(
  videoId: string,
  userGoal: string,
  sampleFps = 1,
  topK = 5,
  plannerProvider = "",
): Promise<{ task_id: string; status: string }> {
  const params = new URLSearchParams({ user_goal: userGoal, sample_fps: String(sampleFps), top_k: String(topK), planner_provider: plannerProvider });
  const res = await fetch(BASE + "/api/v1/videos/" + videoId + "/agent-run?" + params.toString(), { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Agent run failed");
  }
  return res.json();
}

export async function pollTask(taskId: string): Promise<TaskResult> {
  const res = await fetch(BASE + "/api/tasks/" + taskId);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Task poll failed");
  }
  return res.json();
}

export async function getReport(videoId: string): Promise<ReportResult> {
  const res = await fetch(BASE + "/api/v1/videos/" + videoId + "/report");
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Report fetch failed");
  }
  return res.json();
}


export interface VisualizeResult {
  video_id: string;
  frame_count: number;
  image_urls: string[];
}

export async function visualizeDetections(
  videoId: string,
  maxFrames = 500,
): Promise<VisualizeResult> {
  const params = new URLSearchParams({ max_frames: String(maxFrames) });
  const res = await fetch(
    BASE + "/api/v1/videos/" + videoId + "/visualize-detections?" + params.toString(),
    { method: "POST" },
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Visualize failed");
  }
  return res.json();
}
