import React, { useCallback } from "react";
import type { TaskHistoryEntry } from "../../utils/taskHistory";
import { STATUS_LABELS } from "../../utils/taskHistory";
import "./TaskHistoryItem.css";

export interface TaskHistoryItemProps {
  entry: TaskHistoryEntry;
  onOpen: (entry: TaskHistoryEntry) => void;
  onRemove: (entry: TaskHistoryEntry) => void;
  onRetry?: (entry: TaskHistoryEntry) => void;
}

const STATUS_COLORS: Record<string, string> = {
  completed: "var(--color-success)", success: "var(--color-success)",
  failed: "var(--color-danger)", running: "var(--color-primary)",
  queued: "var(--color-text-muted)", cancelled: "var(--color-text-muted)",
  timeout: "var(--color-danger)", interrupted: "var(--color-danger)",
  completed_with_errors: "var(--color-warning)",
};

function fmtTime(iso: string): string {
  try { return new Date(iso).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }); } catch { return ""; }
}
function fmtDuration(s: number | undefined): string {
  if (s == null) return ""; const m = Math.floor(s / 60); return m > 0 ? m + "分" + Math.floor(s % 60) + "秒" : Math.floor(s) + "秒";
}

export default function TaskHistoryItem({ entry, onOpen, onRemove, onRetry }: TaskHistoryItemProps) {
  const color = STATUS_COLORS[entry.status] || "var(--color-text-muted)";
  const label = STATUS_LABELS[entry.status] || entry.status;
  const isFailed = ["failed", "timeout", "interrupted"].includes(entry.status);
  const shortId = entry.videoId.length > 8 ? entry.videoId.slice(0, 8) + "..." : entry.videoId;

  const handleOpen = useCallback(() => onOpen(entry), [entry, onOpen]);
  const handleRemove = useCallback(() => onRemove(entry), [entry, onRemove]);
  const handleRetry = useCallback(() => onRetry?.(entry), [entry, onRetry]);

  return (
    <div className="history-item" onClick={handleOpen} role="button" tabIndex={0} onKeyDown={(e) => { if (e.key === "Enter") handleOpen(); }}>
      <div className="history-item__main">
        <div className="history-item__top">
          <span className="history-item__filename" title={entry.filename}>{entry.filename}</span>
          <span className="history-item__status" style={{ color, borderColor: color }}>{label}</span>
        </div>
        <div className="history-item__meta">
          <span className="history-item__id" title={entry.videoId}>{shortId}</span>
          <span>{fmtTime(entry.updatedAt)}</span>
          {entry.duration != null && <span>{fmtDuration(entry.duration)}</span>}
        </div>
        {(entry.highlightCount != null || entry.averageScore != null) && (
          <div className="history-item__stats">
            {entry.highlightCount != null && <span className="history-item__stat">精彩: {entry.highlightCount}</span>}
            {entry.clipCount != null && <span className="history-item__stat">片段: {entry.clipCount}</span>}
            {entry.averageScore != null && <span className="history-item__stat">均分: {entry.averageScore.toFixed(3)}</span>}
          </div>
        )}
      </div>
      <div className="history-item__actions" onClick={(e) => e.stopPropagation()}>
        <button className="history-item__action-btn" onClick={handleOpen} title="打开结果">打开</button>
        {isFailed && onRetry && <button className="history-item__action-btn history-item__retry" onClick={handleRetry} title="重试">重试</button>}
        <button className="history-item__action-btn history-item__remove" onClick={handleRemove} title="从历史中移除（不会删除服务器上的文件）">从历史中移除</button>
      </div>
    </div>
  );
}
