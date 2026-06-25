// ── HighlightTimeline (Enhanced) ───────────────────
// Timeline with tooltip on hover, time scale, cursor, active highlight.

import React, { useCallback, useRef, useMemo, useState } from "react";
import type { HighlightResult } from "../types/video";
import { normalizeHighlightRange, findActiveHighlight, highlightLeftPercent, highlightWidthPercent, playheadLeftPercent, xToTime } from "../utils/highlightTimeline";
import { formatTimestamp, formatDuration } from "../utils/time";
import "./HighlightTimeline.css";

export interface HighlightTimelineProps {
  duration: number;
  highlights: HighlightResult[];
  currentTime: number;
  selectedHighlightId?: string | null;
  activeHighlightId?: string | null;
  onSelectHighlight?: (highlight: HighlightResult) => void;
  onSeek?: (time: number) => void;
  className?: string;
  ariaLabel?: string;
}

interface TooltipInfo {
  x: number;
  highlight: HighlightResult;
  startTime: number;
  endTime: number;
  label: string;
}

function HighlightTimeline(props: HighlightTimelineProps) {
  const {
    duration, highlights, currentTime, selectedHighlightId,
    activeHighlightId: activeHighlightIdProp,
    onSelectHighlight, onSeek, className, ariaLabel = "精彩片段时间轴"
  } = props;
  const trackRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<TooltipInfo | null>(null);

  const validDuration = typeof duration === "number" && Number.isFinite(duration) && duration > 0;

  const ranges = useMemo(() => {
    if (!validDuration) return [];
    return (highlights ?? [])
      .map((hl) => {
        const range = normalizeHighlightRange(hl, duration);
        return range ? { highlight: hl, range } : null;
      })
      .filter((x): x is { highlight: HighlightResult; range: { startTime: number; endTime: number; duration: number } } => x !== null);
  }, [highlights, duration, validDuration]);

  const autoActiveId = useMemo(() => {
    if (!validDuration) return null;
    if (activeHighlightIdProp === null) return null;
    if (activeHighlightIdProp !== undefined) return activeHighlightIdProp;
    const found = findActiveHighlight(highlights ?? [], currentTime, duration, selectedHighlightId ?? null);
    return found ? found.id : null;
  }, [highlights, currentTime, duration, validDuration, activeHighlightIdProp, selectedHighlightId]);

  const activeId = activeHighlightIdProp === undefined ? autoActiveId : (activeHighlightIdProp ?? null);

  const handleTrackClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!trackRef.current || !validDuration) return;
    if ((e.target as HTMLElement).closest("[data-highlight-id]")) return;
    const rect = trackRef.current.getBoundingClientRect();
    const time = xToTime(e.clientX, { left: rect.left, width: rect.width }, duration);
    onSeek?.(time);
  }, [duration, validDuration, onSeek]);

  const handleBarMouseEnter = useCallback((hl: HighlightResult, range: { startTime: number; endTime: number; duration: number }, e: React.MouseEvent) => {
    const bar = e.currentTarget as HTMLElement;
    const rect = bar.getBoundingClientRect();
    const selScore = Number.isFinite(hl.selection_score) ? hl.selection_score : (Number.isFinite(hl.score) ? hl.score : 0) ?? 0;
    setTooltip({
      x: rect.left + rect.width / 2,
      highlight: hl,
      startTime: range.startTime,
      endTime: range.endTime,
      label: `${formatTimestamp(range.startTime)} - ${formatTimestamp(range.endTime)} (${formatDuration(range.duration)})\n得分: ${selScore.toFixed(3)}`,
    });
  }, []);

  const handleBarMouseLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  if (!validDuration) {
    return (
      <div className={"highlight-timeline highlight-timeline--empty " + (className ?? "")} role="region" aria-label={ariaLabel}>
        <div className="highlight-timeline__track">
          <span className="highlight-timeline__empty-text">视频时长无效</span>
        </div>
      </div>
    );
  }

  const allInvalid = ranges.length === 0 && (highlights ?? []).length > 0;
  if (allInvalid) {
    return (
      <div className={"highlight-timeline highlight-timeline--empty " + (className ?? "")} role="region" aria-label={ariaLabel}>
        <div className="highlight-timeline__labels"><span>{formatTimestamp(0)}</span><span>{formatTimestamp(duration)}</span></div>
        <div className="highlight-timeline__track"><span className="highlight-timeline__empty-text">所有精彩片段无效</span></div>
      </div>
    );
  }

  // Generate time scale ticks
  const numTicks = Math.min(10, Math.max(4, Math.floor(duration / 30)));
  const tickInterval = duration / numTicks;

  return (
    <div className={"highlight-timeline " + (className ?? "")} role="region" aria-label={ariaLabel}>
      <div className="highlight-timeline__labels">
        <span>{formatTimestamp(0)}</span>
        <span>{formatTimestamp(duration)}</span>
      </div>
      <div
        ref={trackRef}
        className="highlight-timeline__track"
        onClick={handleTrackClick}
        style={{ position: "relative" }}
      >
        {/* Time scale ticks */}
        {Array.from({ length: numTicks + 1 }, (_, i) => {
          const pct = (i * tickInterval / duration) * 100;
          return (
            <div
              key={i}
              className="highlight-timeline__tick"
              style={{ left: pct + "%", position: "absolute", bottom: 0, width: 1, height: 8, background: "#d1d5db" }}
            />
          );
        })}

        {ranges.map(({ highlight: hl, range }) => {
          const left = highlightLeftPercent(range, duration);
          const width = highlightWidthPercent(range, duration);
          const isActive = hl.id === activeId;
          const isSelected = hl.id === selectedHighlightId;
          let bc = "highlight-timeline__bar";
          if (isActive) bc += " highlight-timeline__bar--active";
          if (isSelected) bc += " highlight-timeline__bar--selected";
          const selScore = (Number.isFinite(hl.selection_score) ? hl.selection_score : (Number.isFinite(hl.score) ? hl.score : 0)) ?? 0;
          const timeLabel = formatTimestamp(range.startTime) + " - " + formatTimestamp(range.endTime);

          return (
            <button
              key={hl.id}
              type="button"
              className={bc}
              style={{ left: left + "%", width: width + "%", position: "absolute" }}
              data-highlight-id={hl.id}
              aria-label={timeLabel + "，得分" + selScore.toFixed(3)}
              title={""}
              aria-pressed={isSelected}
              onClick={() => onSelectHighlight?.(hl)}
              onMouseEnter={(e) => handleBarMouseEnter(hl, range, e)}
              onMouseLeave={handleBarMouseLeave}
            />
          );
        })}

        {/* Playhead cursor */}
        <div
          className="highlight-timeline__playhead"
          style={{ left: playheadLeftPercent(currentTime, duration) + "%" }}
          aria-hidden="true"
        />
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="highlight-timeline__tooltip"
          style={{ left: Math.min(Math.max(tooltip.x - 80, 0), window.innerWidth - 180) + "px" }}
        >
          {tooltip.label.split("\n").map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      )}

      <div className="highlight-timeline__current-time">
        {formatTimestamp(currentTime)} / {formatTimestamp(duration)}
      </div>
    </div>
  );
}

export default HighlightTimeline;
