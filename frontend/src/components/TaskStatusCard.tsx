// ── TaskStatusCard ─────────────────────────────────
// Displays task progress, status, steps, cancel/retry buttons.

import React from "react";
import { useToast } from "./toast/useToast";
import type { TaskResult } from "../api";
import "./TaskStatusCard.css";

export interface TaskStatusCardProps {
  task: TaskResult | null;
  progressPct: number;
  onCancel?: () => void;
  onRetry?: () => void;
  className?: string;
}

const STATUS_LABELS: Record<string, { label: string; icon: string; color: string }> = {
  pending: { label: "等待中", icon: "⏳", color: "#6b7280" },
  queued: { label: "排队中", icon: "🔄", color: "#6b7280" },
  running: { label: "分析中", icon: "⏳", color: "#4f46e5" },
  success: { label: "完成", icon: "✅", color: "#16a34a" },
  completed: { label: "完成", icon: "✅", color: "#16a34a" },
  completed_with_errors: { label: "部分完成", icon: "⚠️", color: "#d97706" },
  failed: { label: "失败", icon: "❌", color: "#dc2626" },
  cancelled: { label: "已取消", icon: "🚫", color: "#6b7280" },
  timeout: { label: "超时", icon: "⏰", color: "#dc2626" },
  interrupted: { label: "中断", icon: "🔌", color: "#dc2626" },
};

function TaskStatusCard({ task, progressPct, onCancel, onRetry, className }: TaskStatusCardProps) {
  const { addToast } = useToast();
  if (!task) return null;

  const statusInfo = STATUS_LABELS[task.status] || { label: task.status, icon: "❓", color: "#6b7280" };
  const isTerminal = ["success", "completed", "completed_with_errors", "failed", "cancelled", "timeout", "interrupted"].includes(task.status);
  const isFailed = ["failed", "timeout", "interrupted"].includes(task.status);
  const isCancelled = task.status === "cancelled";
  const isRunning = task.status === "running" || task.status === "queued" || task.status === "pending";

  // Calculate elapsed time if created_at is available
  const created = (task as any).created_at ? new Date((task as any).created_at) : null;
  const started = (task as any).started_at ? new Date((task as any).started_at) : null;
  const finished = (task as any).finished_at ? new Date((task as any).finished_at) : null;

  const fmtTime = (d: Date | null) => {
    if (!d || isNaN(d.getTime())) return "";
    return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  };

  const elapsedSec = finished && started
    ? Math.round((finished.getTime() - started.getTime()) / 1000)
    : started && isRunning
      ? Math.round((Date.now() - started.getTime()) / 1000)
      : 0;

  const fmtDuration = (s: number) => {
    if (s < 60) return s + "秒";
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m + "分" + sec + "秒";
  };

  const cardClass = "task-status-card task-status-card--" + task.status + (className ? " " + className : "");

  return (
    <div className={cardClass}>
      <div className="task-status-card__header">
        <span className="task-status-card__status-icon">{statusInfo.icon}</span>
        <span className="task-status-card__status-label" style={{ color: statusInfo.color }}>
          {statusInfo.label}
        </span>
        {isRunning && (
          <span className="task-status-card__elapsed">
            {elapsedSec > 0 ? fmtDuration(elapsedSec) : ""}
          </span>
        )}
      </div>

      {isRunning && (
        <div className="task-status-card__progress-section">
          <div className="task-status-card__progress-bar">
            <div
              className="task-status-card__progress-fill"
              style={{ width: Math.min(progressPct, 100) + "%" }}
            />
          </div>
          <span className="task-status-card__progress-text">{progressPct}%</span>
        </div>
      )}

      {task.current_step && isRunning && (
        <div className="task-status-card__step">当前步骤: {task.current_step}</div>
      )}

      {isFailed && task.error && (
        <div className="task-status-card__error">{task.error}</div>
      )}

      {isCancelled && (
        <div className="task-status-card__cancelled-msg">任务已被取消</div>
      )}

      {created && (
        <div className="task-status-card__times">
          <span>创建: {fmtTime(created)}</span>
          {started && <span>开始: {fmtTime(started)}</span>}
          {finished && <span>完成: {fmtTime(finished)}</span>}
        </div>
      )}

      <div className="task-status-card__actions">
        {isRunning && onCancel && (
          <button className="task-status-card__cancel-btn" onClick={() => { onCancel(); addToast("info", "任务取消请求已发送"); }}>
            取消任务
          </button>
        )}
        {isFailed && onRetry && (
          <button className="task-status-card__retry-btn" onClick={() => { onRetry(); addToast("info", "任务重试已提交"); }}>
            重试任务
          </button>
        )}
      </div>

      {task.result?.steps && task.result.steps.length > 0 && (
        <div className="task-status-card__steps">
          <div className="task-status-card__steps-title">分析步骤</div>
          {task.result.steps.map((s, i) => (
            <div key={i} className={"task-status-card__step-item task-status-card__step-item--" + s.status}>
              <span className="task-status-card__step-icon">
                {s.status === "ok" ? "✅" : s.status === "running" ? "⏳" : s.status === "failed" ? "❌" : "⬜"}
              </span>
              <span className="task-status-card__step-name">{s.step || s.detail}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default TaskStatusCard;
