// ── ScoreBreakdownBars ────────────────────────────
// Horizontal bars showing each dimension in score_breakdown.

import React from "react";
import type { HighlightScoreBreakdown } from "../../types/video";
import { safeScore, DIMENSION_NAMES } from "../../utils/reportInsights";
import "./ScoreBreakdownBars.css";

export interface ScoreBreakdownBarsProps {
  breakdown: HighlightScoreBreakdown;
  className?: string;
}

function ScoreBreakdownBars({ breakdown, className }: ScoreBreakdownBarsProps) {
  const entries = Object.entries(breakdown || {});
  if (entries.length === 0) {
    return <p className="score-breakdown-bars__empty">暂无评分分解数据</p>;
  }

  return (
    <div className={"score-breakdown-bars" + (className ? " " + className : "")}>
      {entries.map(([key, comp]) => {
        const score = safeScore(comp.raw ?? comp.weighted);
        const name = DIMENSION_NAMES[key] || key;
        const pct = Math.min(score * 100, 100);
        return (
          <div key={key} className="score-breakdown-bars__item">
            <span className="score-breakdown-bars__name">{name}</span>
            <div className="score-breakdown-bars__track">
              <div
                className="score-breakdown-bars__fill"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="score-breakdown-bars__score">{score.toFixed(3)}</span>
          </div>
        );
      })}
    </div>
  );
}

export default ScoreBreakdownBars;
