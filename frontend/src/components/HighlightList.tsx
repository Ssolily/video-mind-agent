import React, { useMemo, useCallback } from "react";
import type { HighlightResult } from "../types/video";
import { sortHighlightsForDisplay, getPrimaryHighlightScore, formatHighlightReason } from "../utils/highlightDisplay";
import { formatTimestamp, formatDuration } from "../utils/time";
import ScoreBreakdown from "./ScoreBreakdown";
import "./HighlightList.css";

export interface HighlightListProps {
  highlights: HighlightResult[];
  selectedHighlightId?: string | null;
  activeHighlightId?: string | null;
  onSelectHighlight?: (highlight: HighlightResult) => void;
  showScoreBreakdown?: boolean;
  className?: string;
  ariaLabel?: string;
}

function HighlightList({
  highlights,
  selectedHighlightId,
  activeHighlightId,
  onSelectHighlight,
  showScoreBreakdown = true,
  className,
  ariaLabel = "\u7cbe\u5f69\u7247\u6bb5\u5217\u8868",
}: HighlightListProps) {
  const sorted = useMemo(() => sortHighlightsForDisplay(highlights ?? []), [highlights]);

  const handleClick = useCallback(
    (hl: HighlightResult) => {
      onSelectHighlight?.(hl);
    },
    [onSelectHighlight],
  );

  const isValidTime = (hl: HighlightResult): boolean => {
    return (
      typeof hl.start_time === "number" && Number.isFinite(hl.start_time) &&
      typeof hl.end_time === "number" && Number.isFinite(hl.end_time) &&
      hl.end_time > hl.start_time
    );
  };

  const cls = "highlight-list" + (className ? " " + className : "");

  if (!Array.isArray(highlights) || highlights.length === 0) {
    return (
      <div className={cls} role="list" aria-label={ariaLabel}>
        <div className="highlight-list__empty">{"\u6682\u65e0\u7cbe\u5f69\u7247\u6bb5"}</div>
      </div>
    );
  }

  return (
    <div className={cls} role="list" aria-label={ariaLabel}>
      {sorted.map((hl) => {
        const isActive = hl.id === activeHighlightId;
        const isSelected = hl.id === selectedHighlightId;
        const score = getPrimaryHighlightScore(hl);
        const reason = formatHighlightReason(hl.reason);
        const valid = isValidTime(hl);

        let cardCls = "highlight-card";
        if (isActive) cardCls += " highlight-card--active";
        if (isSelected) cardCls += " highlight-card--selected";

        const timeLabel = valid
          ? formatTimestamp(hl.start_time) + " \u2192 " + formatTimestamp(hl.end_time) + " (" + formatDuration(hl.duration) + ")"
          : hl.start_time > hl.end_time || (hl.start_time === hl.end_time)
            ? "\u65f6\u95f4\u8303\u56f4\u5f02\u5e38"
            : (typeof hl.start_time === "number" ? formatTimestamp(hl.start_time) + " \u2192 " : "") +
              (typeof hl.end_time === "number" ? formatTimestamp(hl.end_time) : "");

        return (
          <div
            key={hl.id}
            className={cardCls}
            role="button"
            tabIndex={0}
            aria-label={"\u7cbe\u5f69\u7247\u6bb5 " + (valid ? formatTimestamp(hl.start_time) + " - " + formatTimestamp(hl.end_time) : "") + "\uff0c\u5f97\u5206 " + score.toFixed(3)}
            aria-pressed={isSelected}
            data-highlight-id={hl.id}
            onClick={() => handleClick(hl)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                handleClick(hl);
              }
            }}
          >
            <div className="highlight-card__header">
              <span className="highlight-card__time">{timeLabel}</span>
              <span className="highlight-card__score">{score.toFixed(3)}</span>
            </div>
            <div className="highlight-card__reason">{reason}</div>
            {showScoreBreakdown && <ScoreBreakdown highlight={hl} />}
          </div>
        );
      })}
    </div>
  );
}

export default HighlightList;
