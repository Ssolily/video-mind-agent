// ── ScoreDistribution ─────────────────────────────
// Simple CSS bar chart showing score distribution across buckets.

import React from "react";
import type { BucketInfo } from "../../utils/reportInsights";
import { computeScoreDistribution } from "../../utils/reportInsights";
import type { HighlightResult } from "../../types/video";
import "./ScoreDistribution.css";

export interface ScoreDistributionProps {
  highlights: HighlightResult[];
  className?: string;
}

function ScoreDistribution({ highlights, className }: ScoreDistributionProps) {
  const buckets = computeScoreDistribution(highlights);
  const isEmpty = buckets.every((b) => b.count === 0);

  return (
    <div className={"score-distribution" + (className ? " " + className : "")}>
      <h3 className="score-distribution__title">评分分布</h3>
      {isEmpty ? (
        <p className="score-distribution__empty">暂无评分数据</p>
      ) : (
        <div className="score-distribution__bars">
          {buckets.map((b) => (
            <div key={b.bucket} className="score-distribution__item">
              <span className="score-distribution__label">{b.bucket}</span>
              <div className="score-distribution__bar-track">
                <div
                  className="score-distribution__bar-fill"
                  style={{ width: `${Math.max(b.percent, 2)}%` }}
                />
              </div>
              <span className="score-distribution__count">{b.count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ScoreDistribution;
