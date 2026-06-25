// ── ReportOverview ─────────────────────────────────
// Top overview metrics for the report.

import React from "react";
import type { ReportMetrics } from "../../utils/reportInsights";
import "./ReportOverview.css";

export interface ReportOverviewProps {
  metrics: ReportMetrics;
  status: string;
  className?: string;
}

function fmtTime(s: number): string {
  if (!s || !Number.isFinite(s)) return "00:00";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

function ReportOverview({ metrics, status, className }: ReportOverviewProps) {
  return (
    <div className={"report-overview" + (className ? " " + className : "")}>
      <div className="report-overview__header">
        <h2 className="report-overview__title">分析概览</h2>
        <span className={"report-overview__badge report-overview__badge--" + status}>
          {status === "completed" || status === "success" ? "已完成" : status === "completed_with_errors" ? "部分完成" : status}
        </span>
      </div>
      <div className="report-overview__grid">
        <div className="report-overview__item">
          <span className="report-overview__value">{fmtTime(metrics.totalDuration)}</span>
          <span className="report-overview__label">视频时长</span>
        </div>
        <div className="report-overview__item">
          <span className="report-overview__value">{metrics.highlightCount}</span>
          <span className="report-overview__label">精彩片段</span>
        </div>
        <div className="report-overview__item">
          <span className="report-overview__value">{metrics.clipCount}</span>
          <span className="report-overview__label">导出片段</span>
        </div>
        <div className="report-overview__item">
          <span className="report-overview__value">{metrics.averageScore.toFixed(3)}</span>
          <span className="report-overview__label">平均分</span>
        </div>
        <div className="report-overview__item">
          <span className="report-overview__value">{fmtTime(metrics.coverageSeconds)}</span>
          <span className="report-overview__label">覆盖时长</span>
        </div>
        <div className="report-overview__item">
          <span className="report-overview__value">{metrics.coveragePercent}%</span>
          <span className="report-overview__label">覆盖率</span>
        </div>
      </div>
    </div>
  );
}

export default ReportOverview;
