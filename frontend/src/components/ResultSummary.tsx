// ── ResultSummary ──────────────────────────────────
// Summary header showing video info and task status.

import React from "react";
import type { VideoResult } from "../types/video";
import "./ResultSummary.css";

export interface ResultSummaryProps {
  videoId: string;
  data: VideoResult;
  className?: string;
}

function fmtDuration(s: number | null): string {
  if (s == null || !Number.isFinite(s)) return "未知";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return m > 0 ? `${m}分${sec}秒` : `${sec}秒`;
}

const STATUS_BADGES: Record<string, { label: string; className: string }> = {
  uploaded: { label: "已上传", className: "badge--neutral" },
  pending: { label: "等待中", className: "badge--neutral" },
  running: { label: "分析中", className: "badge--running" },
  success: { label: "完成", className: "badge--success" },
  completed: { label: "完成", className: "badge--success" },
  completed_with_errors: { label: "部分完成", className: "badge--warning" },
  failed: { label: "失败", className: "badge--error" },
};

function ResultSummary({ videoId, data, className }: ResultSummaryProps) {
  const badge = STATUS_BADGES[data.status] || { label: data.status, className: "badge--neutral" };
  const hlCount = data.highlights?.length ?? 0;
  const clipCount = data.clips?.length ?? 0;

  return (
    <div className={"result-summary" + (className ? " " + className : "")}>
      <div className="result-summary__info">
        <div className="result-summary__title-row">
          <h2 className="result-summary__title">视频分析结果</h2>
          <span className={"result-summary__badge " + badge.className}>{badge.label}</span>
        </div>
        <div className="result-summary__meta">
          <span className="result-summary__meta-item">时长: {fmtDuration(data.duration)}</span>
          <span className="result-summary__meta-item">精彩片段: {hlCount}</span>
          {clipCount > 0 && <span className="result-summary__meta-item">导出片段: {clipCount}</span>}
        </div>
      </div>
      {data.warnings.length > 0 && (
        <div className="result-summary__warnings">
          {data.warnings.map((w, i) => <span key={i}>{w}</span>)}
        </div>
      )}
    </div>
  );
}

export default ResultSummary;
