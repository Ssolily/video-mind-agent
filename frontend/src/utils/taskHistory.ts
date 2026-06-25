// localStorage-backed task history utility.

import type { TaskResult } from "../api";

export const STORAGE_KEY = "videomind-history";
export const MAX_ENTRIES = 50;

export interface TaskHistoryEntry {
  videoId: string;
  taskId?: string;
  filename: string;
  status: string;
  createdAt: string;
  updatedAt: string;
  duration?: number;
  highlightCount?: number;
  clipCount?: number;
  averageScore?: number;
}

export type SortMode = "newest" | "oldest" | "highest_score" | "most_highlights" | "longest_duration";

export interface FilterOptions {
  status: string;
  search: string;
  sort: SortMode;
}

export const STATUS_LABELS: Record<string, string> = {
  pending: "\u7b49\u5f85\u4e2d", queued: "\u6392\u961f\u4e2d", running: "\u5206\u6790\u4e2d",
  success: "\u5df2\u5b8c\u6210", completed: "\u5df2\u5b8c\u6210", completed_with_errors: "\u90e8\u5206\u5b8c\u6210",
  failed: "\u5931\u8d25", cancelled: "\u5df2\u53d6\u6d88", timeout: "\u8d85\u65f6", interrupted: "\u4e2d\u65ad",
};

export function serializeTaskHistory(tasks: TaskHistoryEntry[]): string {
  return JSON.stringify(tasks.slice(0, MAX_ENTRIES));
}

export function deserializeTaskHistory(raw: string | null): TaskHistoryEntry[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.slice(0, MAX_ENTRIES) : [];
  } catch { return []; }
}

export function loadTaskHistory(): TaskHistoryEntry[] {
  try { return deserializeTaskHistory(localStorage.getItem(STORAGE_KEY)); } catch { return []; }
}

export function saveTaskHistory(tasks: TaskHistoryEntry[]): void {
  try { localStorage.setItem(STORAGE_KEY, serializeTaskHistory(tasks)); } catch {}
}

export function mergeTaskHistory(existing: TaskHistoryEntry[], entry: TaskHistoryEntry): TaskHistoryEntry[] {
  const idx = existing.findIndex((e) => e.videoId === entry.videoId || (e.taskId && e.taskId === entry.taskId));
  let updated: TaskHistoryEntry[];
  if (idx >= 0) {
    updated = [...existing];
    updated[idx] = { ...updated[idx], ...entry, updatedAt: new Date().toISOString() };
  } else {
    updated = [entry, ...existing];
  }
  return updated.slice(0, MAX_ENTRIES);
}

export function mergeTaskHistoryBatch(existing: TaskHistoryEntry[], entries: TaskHistoryEntry[]): TaskHistoryEntry[] {
  let result = [...existing];
  for (const e of entries) result = mergeTaskHistory(result, e);
  return result;
}

export function buildEntryFromTask(videoId: string, filename: string, task: Partial<TaskResult>): TaskHistoryEntry {
  return { videoId, taskId: task.task_id, filename, status: task.status || "queued", createdAt: new Date().toISOString(), updatedAt: new Date().toISOString() };
}

export function buildEntryFromResult(result: { video_id: string; status: string; duration?: number | null; highlights?: Array<{ score: number }>; clips?: Array<any> }, filename: string, taskId?: string): TaskHistoryEntry {
  const scores = (result.highlights ?? []).map((h) => h.score).filter((s) => typeof s === "number" && Number.isFinite(s));
  const avg = scores.length > 0 ? Math.round((scores.reduce((a, b) => a + b, 0) / scores.length) * 1000) / 1000 : undefined;
  return {
    videoId: result.video_id, taskId, filename, status: result.status, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(),
    duration: result.duration ?? undefined, highlightCount: result.highlights?.length ?? 0, clipCount: result.clips?.length ?? 0, averageScore: avg,
  };
}

export function filterTaskHistory(tasks: TaskHistoryEntry[], options: FilterOptions): TaskHistoryEntry[] {
  let result = [...tasks];
  if (options.status !== "all") result = result.filter((t) => t.status === options.status);
  if (options.search.trim()) {
    const q = options.search.trim().toLowerCase();
    result = result.filter((t) => t.filename.toLowerCase().includes(q) || t.videoId.toLowerCase().includes(q) || (t.taskId ?? "").toLowerCase().includes(q));
  }
  if (options.sort === "oldest") result.sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());
  else if (options.sort === "highest_score") result.sort((a, b) => (b.averageScore ?? 0) - (a.averageScore ?? 0));
  else if (options.sort === "most_highlights") result.sort((a, b) => (b.highlightCount ?? 0) - (a.highlightCount ?? 0));
  else if (options.sort === "longest_duration") result.sort((a, b) => (b.duration ?? 0) - (a.duration ?? 0));
  else result.sort((a, b) => { const d = new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(); return d !== 0 ? d : new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime(); });
  return result;
}

export function removeFromHistory(tasks: TaskHistoryEntry[], videoId: string): TaskHistoryEntry[] {
  return tasks.filter((t) => t.videoId !== videoId);
}
