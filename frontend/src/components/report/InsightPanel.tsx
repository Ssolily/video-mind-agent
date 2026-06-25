// ── InsightPanel ──────────────────────────────────
// Explains why highlights were recommended, based on local heuristics.

import React from "react";
import type { ReportMetrics, DominantDimension } from "../../utils/reportInsights";
import { generateInsightDescription } from "../../utils/reportInsights";
import "./InsightPanel.css";

export interface InsightPanelProps {
  metrics: ReportMetrics;
  dominantDim: DominantDimension | null;
  className?: string;
}

function InsightPanel({ metrics, dominantDim, className }: InsightPanelProps) {
  const description = generateInsightDescription(metrics, dominantDim);
  const isEmpty = metrics.highlightCount === 0;

  return (
    <div className={"insight-panel" + (isEmpty ? " insight-panel--empty" : "") + (className ? " " + className : "")}>
      <h3 className="insight-panel__title">
        {isEmpty ? "💡 分析建议" : "🔍 推荐解释"}
      </h3>
      <p className="insight-panel__description">{description}</p>
      {!isEmpty && dominantDim && (
        <div className="insight-panel__dim-bar">
          <span className="insight-panel__dim-label">主要影响维度:</span>
          <span className="insight-panel__dim-name">{dominantDim.displayName}</span>
          <div className="insight-panel__dim-score-bar">
            <div
              className="insight-panel__dim-score-fill"
              style={{ width: `${Math.min(dominantDim.averageScore * 100, 100)}%` }}
            />
          </div>
          <span className="insight-panel__dim-score">{dominantDim.averageScore.toFixed(3)}</span>
        </div>
      )}
      {!isEmpty && metrics.topHighlights.length > 0 && (
        <div className="insight-panel__top-hls">
          <span className="insight-panel__top-label">Top 3 精彩片段:</span>
          {metrics.topHighlights.map((hl, i) => (
            <span key={hl.id} className="insight-panel__top-item">
              #{i + 1} {fmtTime(hl.start_time)}–{fmtTime(hl.end_time)} ({hl.score.toFixed(3)})
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function fmtTime(s: number): string {
  if (!Number.isFinite(s)) return "00:00";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

export default InsightPanel;
