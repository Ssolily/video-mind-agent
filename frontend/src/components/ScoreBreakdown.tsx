import React from "react";
import type { HighlightResult } from "../types/video";
import { formatScore, getScoreDimensions } from "../utils/highlightDisplay";
import "./HighlightList.css";

export interface ScoreBreakdownProps {
  highlight: HighlightResult;
  defaultExpanded?: boolean;
  className?: string;
}

function ScoreBreakdown({ highlight, defaultExpanded = false, className }: ScoreBreakdownProps) {
  const dims = getScoreDimensions(highlight.score_breakdown);
  const hasBreakdown = dims.length > 0;

  const mainScore = typeof highlight.selection_score === "number" && Number.isFinite(highlight.selection_score)
    ? highlight.selection_score
    : (typeof highlight.score === "number" && Number.isFinite(highlight.score) ? highlight.score : 0);
  const baseScore = typeof highlight.base_score === "number" && Number.isFinite(highlight.base_score) ? highlight.base_score : null;
  const overlapPenalty = typeof highlight.overlap_penalty === "number" && Number.isFinite(highlight.overlap_penalty) ? highlight.overlap_penalty : null;

  const cls = "score-breakdown" + (className ? " " + className : "");

  if (!hasBreakdown && baseScore == null) {
    return (
      <div className={cls}>
        <div className="score-breakdown__summary">
          <span className="score-breakdown__score">
            {"\u7efc\u5408\u5f97\u5206: " + formatScore(mainScore)}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={cls}>
      <details className="score-breakdown__details" open={defaultExpanded}>
        <summary className="score-breakdown__summary">
          <span className="score-breakdown__score">
            {"\u7efc\u5408\u5f97\u5206: " + formatScore(mainScore)}
          </span>
          <span className="score-breakdown__toggle-hint">
            {defaultExpanded ? "\u25b2 \u6298\u53e0" : "\u25bc \u8be6\u60c5"}
          </span>
        </summary>

        <div className="score-breakdown__body">
          {baseScore != null && (
            <div className="score-breakdown__extra">
              <span className="score-breakdown__extra-label">
                {"\u57fa\u7840\u5f97\u5206: " + formatScore(baseScore)}
              </span>
              <span className="score-breakdown__extra-label">
                {"\u9009\u5165\u5f97\u5206: " + formatScore(mainScore)}
              </span>
              {overlapPenalty != null && overlapPenalty > 0 && (
                <span className="score-breakdown__extra-label score-breakdown__penalty">
                  {"\u91cd\u53e0\u60e9\u7f5a: -" + formatScore(overlapPenalty)}
                </span>
              )}
            </div>
          )}

          {hasBreakdown && (
            <div className="score-breakdown__dimensions">
              {dims.map((dim) => (
                <div key={dim.name} className="score-breakdown__dimension">
                  <span className="score-breakdown__dim-name">
                    {dim.displayName}
                    {dim.isPlaceholder && <span className="score-breakdown__placeholder"> {"(placeholder)"}</span>}
                  </span>
                  <span className="score-breakdown__dim-raw">{formatScore(dim.raw)}</span>
                  <span className="score-breakdown__dim-op">{"\u00d7"}</span>
                  <span className="score-breakdown__dim-weight">{formatScore(dim.weight)}</span>
                  <span className="score-breakdown__dim-op">=</span>
                  <span className="score-breakdown__dim-weighted">{formatScore(dim.weighted)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </details>
    </div>
  );
}

export default ScoreBreakdown;
