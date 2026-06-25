// ── ErrorState ─────────────────────────────────────
// Reusable error state with friendly message and optional retry.

import React from "react";
import "./ErrorState.css";

export interface ErrorStateProps {
  title?: string;
  message: string;
  hint?: string;
  onRetry?: () => void;
  className?: string;
}

const RESOURCE_ERROR_MAP: Record<string, { title: string; hint: string }> = {
  "413": { title: "文件过大", hint: "当前上传文件大小超出限制（最大 1024 MB），请压缩后再试。" },
  "File too large": { title: "文件过大", hint: "当前上传文件大小超出限制，请压缩后再试。" },
  "Queue is full": { title: "队列已满", hint: "当前分析任务队列已满，请等待现有任务完成后再试。" },
  "queue is full": { title: "队列已满", hint: "当前分析任务队列已满，请稍后再试。" },
  "Disk space": { title: "磁盘空间不足", hint: "后端磁盘空间不足，无法处理新任务。请清理磁盘后重试。" },
  "disk space": { title: "磁盘空间不足", hint: "后端磁盘空间不足，请清理后重试。" },
  "Video too long": { title: "视频过长", hint: "视频时长超出系统限制（最长 7200 秒），请剪辑后重试。" },
  "duration": { title: "视频时长超限", hint: "视频时长超出系统限制，请剪辑较短视频后重试。" },
  "Unsupported": { title: "不支持的格式", hint: "仅支持 MP4、MOV、AVI 格式的视频文件，请重新选择。" },
  "file type": { title: "不支持的格式", hint: "文件类型不被支持，请选择 MP4、MOV 或 AVI 格式的视频。" },
  "File type": { title: "不支持的格式", hint: "文件类型不被支持，请选择视频格式的文件。" },
};

function getFriendlyError(msg: string): { title: string; hint: string } {
  if (!msg) return { title: "操作失败", hint: msg };
  for (const [key, val] of Object.entries(RESOURCE_ERROR_MAP)) {
    if (msg.includes(key)) return val;
  }
  if (msg.includes("Failed to fetch") || msg.includes("NetworkError")) {
    return { title: "连接失败", hint: "无法连接到后端服务，请确认后端已启动（http://127.0.0.1:8000）。" };
  }
  if (msg.includes("500") || msg.includes("Internal Server Error")) {
    return { title: "服务器错误", hint: "后端服务内部错误，请检查 logs/backend.log 获取详细信息。" };
  }
  if (msg.includes("timeout") || msg.includes("Timeout") || msg.includes("超时")) {
    return { title: "任务超时", hint: "任务运行时间超过系统限制，请尝试分析较短视频或提高抽帧间隔。" };
  }
  if (msg.includes("cancelled") || msg.includes("Cancelled") || msg.includes("取消")) {
    return { title: "任务已取消", hint: "任务已被取消，你可以重新上传视频并开始新的分析。" };
  }
  return { title: "操作失败", hint: msg };
}

function ErrorState({ title, message, hint, onRetry, className }: ErrorStateProps) {
  const friendly = getFriendlyError(message);
  return (
    <div className={"error-state" + (className ? " " + className : "")}>
      <div className="error-state__icon">⚠️</div>
      <div className="error-state__title">{title || friendly.title}</div>
      <div className="error-state__message">{hint || friendly.hint}</div>
      {onRetry && (
        <button className="error-state__retry-btn" onClick={onRetry}>
          重试
        </button>
      )}
    </div>
  );
}

export default ErrorState;
