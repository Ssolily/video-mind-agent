// ── ReportActions ─────────────────────────────────
// Copy summary, copy timestamps, open markdown, print.

import React, { useCallback } from "react";
import { useToast } from "../toast/useToast";
import type { ReportMetrics } from "../../utils/reportInsights";
import "./ReportActions.css";

export interface ReportActionsProps {
  metrics: ReportMetrics;
  markdownUrl: string | null;
  highlights: Array<{ id: string; start_time: number; end_time: number; score: number }>;
  className?: string;
}

function fmtTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

function buildSummaryText(metrics: ReportMetrics): string {
  const top = metrics.topHighlights[0];
  const topStr = top
    ? `Top highlight: ${fmtTime(top.start_time)} - ${fmtTime(top.end_time)}`
    : "No highlights";
  return [
    "VideoMind Agent Analysis Summary",
    `Duration: ${fmtTime(metrics.totalDuration)}`,
    `Highlights: ${metrics.highlightCount}`,
    `Clips: ${metrics.clipCount}`,
    `Average score: ${metrics.averageScore.toFixed(3)}`,
    topStr,
  ].join("\n");
}

function buildTimestampsText(
  highlights: Array<{ id: string; start_time: number; end_time: number; score: number }>,
): string {
  return (highlights ?? [])
    .filter((h) => Number.isFinite(h.start_time) && Number.isFinite(h.end_time))
    .map((h, i) => `#${i + 1} ${fmtTime(h.start_time)} - ${fmtTime(h.end_time)} score=${h.score.toFixed(3)}`)
    .join("\n");
}

function ReportActions({ metrics, markdownUrl, highlights, className }: ReportActionsProps) {
  const { addToast } = useToast();
  const handleCopySummary = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(buildSummaryText(metrics));
      addToast("success", "摘要已复制");
    } catch { addToast("error", "复制失败"); }
  }, [metrics, addToast]);

  const handleCopyTimestamps = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(buildTimestampsText(highlights));
      addToast("success", "时间段已复制");
    } catch { addToast("error", "复制失败"); }
  }, [highlights, addToast]);

  const handlePrint = useCallback(() => {
    window.print();
    addToast("info", "已打开浏览器打印窗口");
  }, [addToast]);

  return (
    <div className={"report-actions" + (className ? " " + className : "")}>
      <h3 className="report-actions__title">操作</h3>
      <div className="report-actions__buttons">
        <button className="report-actions__btn" onClick={handleCopySummary} title="复制分析摘要">
          📋 复制摘要
        </button>
        <button className="report-actions__btn" onClick={handleCopyTimestamps} title="复制所有精彩片段时间段">
          ⏱ 复制时间段
        </button>
        {markdownUrl ? (
          <a
            href={markdownUrl}
            target="_blank"
            rel="noreferrer"
            className="report-actions__btn report-actions__link"
          >
            📄 Markdown 报告
          </a>
        ) : (
          <button className="report-actions__btn report-actions__btn--disabled" disabled title="暂无 Markdown 报告">
            📄 Markdown 报告
          </button>
        )}
        <button className="report-actions__btn" onClick={handlePrint} title="打印报告">
          🖨 打印
        </button>
      </div>
    </div>
  );
}

export default ReportActions;
