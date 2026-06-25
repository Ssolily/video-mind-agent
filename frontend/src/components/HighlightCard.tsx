// ── HighlightCard ──────────────────────────────────
// Individual highlight card with play buttons, score, breakdown.

import React, { useCallback, useState } from "react";
import type { HighlightResult, ClipResult } from "../types/video";
import { getPrimaryHighlightScore, formatHighlightReason } from "../utils/highlightDisplay";
import { formatTimestamp, formatDuration } from "../utils/time";
import ScoreBreakdown from "./ScoreBreakdown";
import "./HighlightCard.css";

export interface HighlightCardProps {
  highlight: HighlightResult;
  index: number;
  isActive: boolean;
  isSelected: boolean;
  clip?: ClipResult | null;
  onSelect: (hl: HighlightResult) => void;
  onPlayClip?: (clip: ClipResult) => void;
  showScoreBreakdown?: boolean;
}

function HighlightCard({ highlight: hl, index, isActive, isSelected, clip, onSelect, onPlayClip, showScoreBreakdown = true }: HighlightCardProps) {
  const score = getPrimaryHighlightScore(hl);
  const reason = formatHighlightReason(hl.reason);
  const valid = typeof hl.start_time === "number" && Number.isFinite(hl.start_time) &&
    typeof hl.end_time === "number" && Number.isFinite(hl.end_time);

  const timeLabel = valid
    ? `${formatTimestamp(hl.start_time)} → ${formatTimestamp(hl.end_time)} (${formatDuration(hl.duration)})`
    : "时间范围异常";

  let cardClass = "highlight-card";
  if (isActive) cardClass += " highlight-card--active";
  if (isSelected) cardClass += " highlight-card--selected";

  const handleClick = useCallback(() => onSelect(hl), [hl, onSelect]);

  const handlePlayClip = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    if (clip && onPlayClip) onPlayClip(clip);
  }, [clip, onPlayClip]);

  return (
    <div
      className={cardClass}
      role="button"
      tabIndex={0}
      aria-label={`精彩片段 ${valid ? formatTimestamp(hl.start_time) + " - " + formatTimestamp(hl.end_time) : ""}，得分 ${score.toFixed(3)}`}
      aria-pressed={isSelected}
      data-highlight-id={hl.id}
      onClick={handleClick}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); handleClick(); } }}
    >
      <div className="highlight-card__index">{index + 1}</div>
      <div className="highlight-card__body">
        <div className="highlight-card__header">
          <span className="highlight-card__time">{timeLabel}</span>
          <span className="highlight-card__score">{score.toFixed(3)}</span>
        </div>
        <div className="highlight-card__reason">{reason}</div>
        {showScoreBreakdown && <ScoreBreakdown highlight={hl} />}
        <div className="highlight-card__actions">
          <button className="highlight-card__play-btn" onClick={handleClick} title="播放此片段">
            ▶ 播放片段
          </button>
          {clip && (
            <button className="highlight-card__clip-btn" onClick={handlePlayClip} title="播放导出片段">
              🎬 导出片段
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export default HighlightCard;
