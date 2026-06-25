import React, { useState, useMemo, useCallback, useRef, useEffect } from "react";
import type { HighlightResult, ClipResult } from "../types/video";
import type { PlaybackSegment, SeekRequest } from "../types/playback";
import { useVideoResult } from "../hooks/useVideoResult";
import VideoPlayer from "./VideoPlayer";
import HighlightTimeline from "./HighlightTimeline";
import HighlightList from "./HighlightList";
import { findActiveHighlight } from "../utils/highlightTimeline";
import { findClipForHighlight, findHighlightForClip } from "../utils/clipMatching";
import "./ResultWorkspace.css";
import ReportOverview from "./report/ReportOverview";
import InsightPanel from "./report/InsightPanel";
import ScoreDistribution from "./report/ScoreDistribution";
import ClipExplorer from "./report/ClipExplorer";
import ReportActions from "./report/ReportActions";
import TechnicalInfoPanel from "./report/TechnicalInfoPanel";
import { computeMetrics, computeDominantDimension } from "../utils/reportInsights";

// ---- Types ----

export interface ResultWorkspaceProps {
  videoId: string;
  className?: string;
}

type PlaybackMode = "source" | "clip";

// ---- Constants ----

const SRC_CHANGE_DELAY_MS = 80;

// ---- Component ----

function ResultWorkspace({ videoId, className }: ResultWorkspaceProps) {
  // ---- Data ----
  const { loading, data, error } = useVideoResult(videoId);
  const playerRef = useRef<React.ComponentRef<typeof VideoPlayer>>(null);
  const seekRef = useRef({ requestId: 0 });
  const pendingSegmentRef = useRef<PlaybackSegment | null>(null);

  // ---- State ----
  const [mode, setMode] = useState<PlaybackMode>("source");
  const [selectedClipId, setSelectedClipId] = useState<string | null>(null);
  const [selectedHighlightId, setSelectedHighlightId] = useState<string | null>(null);
  const [seekRequest, setSeekRequest] = useState<SeekRequest | null>(null);
  const [playerCurrentTime, setPlayerCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // ---- Cleanup on videoId change ----
  useEffect(() => {
    return () => {
      setMode("source");
      setSelectedClipId(null);
      setSelectedHighlightId(null);
      setSeekRequest(null);
      setPlayerCurrentTime(0);
      setDuration(0);
      pendingSegmentRef.current = null;
    };
  }, [videoId]);

  // ---- Derived data ----
  const highlights = useMemo(() => data?.highlights ?? [], [data]);
  const clips = useMemo(() => data?.clips ?? [], [data]);
  const videoDuration = data?.duration ?? 0;

  const selectedClip = useMemo(
    () => (selectedClipId ? clips.find((c) => c.id === selectedClipId) ?? null : null),
    [selectedClipId, clips],
  );

  // ---- Source display time ----
  // In source mode: raw player time
  // In clip mode: map clip position back to source timeline
  const sourceDisplayTime = useMemo(() => {
    if (mode === "source") {
      return playerCurrentTime;
    }
    if (mode === "clip" && selectedClip) {
      const cs = selectedClip.start_time;
      if (cs != null && Number.isFinite(cs)) {
        const mapped = cs + playerCurrentTime;
        if (mapped < 0) return 0;
        if (videoDuration > 0 && mapped > videoDuration) return videoDuration;
        return mapped;
      }
    }
    return 0;
  }, [mode, selectedClip, playerCurrentTime, videoDuration]);

  // ---- Active highlight (single derived source) ----
  // In source mode: findActiveHighlight with sourceDisplayTime
  // In clip mode: if selectedClip has explicit highlight_id, use it; else try findHighlightForClip
  const activeHighlightId = useMemo<string | null>(() => {
    if (mode === "clip" && selectedClip) {
      // Priority: explicit highlight_id association
      if (selectedClip.highlight_id != null) {
        const matched = highlights.find((h) => h.id === selectedClip.highlight_id);
        if (matched) return matched.id;
      }
      // No explicit id: try time-based matching
      const byTime = findHighlightForClip(selectedClip, highlights);
      if (byTime) return byTime.id;
      // Still no match: fall through to time-based detection via findActiveHighlight
    }
    // Source mode, or clip mode fallback: use time-based detection
    const active = findActiveHighlight(highlights, sourceDisplayTime, videoDuration, selectedHighlightId);
    return active?.id ?? null;
  }, [mode, selectedClip, highlights, sourceDisplayTime, videoDuration, selectedHighlightId]);

  // ---- Player src ----
  const playerSrc = useMemo(() => {
    if (mode === "clip" && selectedClip) {
      return selectedClip.url || data?.source_url || null;
    }
    return data?.source_url ?? null;
  }, [mode, selectedClip, data]);

  // ---- Playback handlers ----

  // Handle source metadata ready -> execute pending segment
  const handleLoadedMetadata = useCallback(() => {
    const seg = pendingSegmentRef.current;
    if (seg && playerRef.current) {
      pendingSegmentRef.current = null;
      playerRef.current.playSegment(seg);
    }
  }, []);

  // Handle highlight selection
  const handleSelectHighlight = useCallback(
    (hl: HighlightResult) => {
      setSelectedHighlightId(hl.id);

      if (mode === "clip") {
        // Switching from clip to source: clear clip state
        setMode("source");
        setSelectedClipId(null);
        // Source src will change -> wait for loadedmetadata, then play segment
        pendingSegmentRef.current = {
          startTime: hl.start_time,
          endTime: hl.end_time,
          highlightId: hl.id,
        };
        // Reset player time (src change resets native video)
        setPlayerCurrentTime(0);
        return;
      }

      // Already in source mode: play segment directly
      if (playerRef.current) {
        playerRef.current.playSegment({
          startTime: hl.start_time,
          endTime: hl.end_time,
          highlightId: hl.id,
        });
      }
    },
    [mode],
  );

  // Handle timeline blank-area seek
  const handleTimelineSeek = useCallback(
    (time: number) => {
      if (mode === "clip") {
        // Seeking on timeline in clip mode: switch to source at that position
        setMode("source");
        setSelectedClipId(null);
        setPlayerCurrentTime(0);
        pendingSegmentRef.current = null;
        const id = ++seekRef.current.requestId;
        setSeekRequest({ time, requestId: id, autoplay: true });
      } else if (playerRef.current) {
        playerRef.current.clearSegment();
        playerRef.current.seek(time, true);
      }
    },
    [mode],
  );

  // Handle clip button click
  const handleClipClick = useCallback(
    (clip: ClipResult) => {
      if (!clip.url || clip.start_time == null) return;

      setMode("clip");
      setSelectedClipId(clip.id);
      pendingSegmentRef.current = null;

      // Update selectedHighlightId based on clip association
      if (clip.highlight_id != null) {
        setSelectedHighlightId(clip.highlight_id);
      } else {
        // Try time-based match (don't use index)
        const matched = findHighlightForClip(clip, highlights);
        setSelectedHighlightId(matched?.id ?? null);
      }

      // Clear segment before src change
      if (playerRef.current) {
        playerRef.current.clearSegment();
      }

      // Schedule seek to 0 after src change
      setTimeout(() => {
        const id = ++seekRef.current.requestId;
        setSeekRequest({ time: 0, requestId: id, autoplay: true });
      }, SRC_CHANGE_DELAY_MS);
    },
    [highlights],
  );

  // Handle "back to source" button
  const handleBackToSource = useCallback(() => {
    if (!selectedClip) return;

    // Compute return time: clip.start_time + clip current player time
    const cs = selectedClip.start_time;
    const returnTime = (cs != null && Number.isFinite(cs))
      ? cs + playerCurrentTime
      : 0;

    setMode("source");
    setSelectedClipId(null);
    setPlayerCurrentTime(0);
    pendingSegmentRef.current = null;

    const id = ++seekRef.current.requestId;
    // Seek to the mapped return time, do NOT autoplay (user must explicitly play)
    setSeekRequest({ time: returnTime, requestId: id, autoplay: false });
  }, [selectedClip, playerCurrentTime]);

  const handleTimeUpdate = useCallback((time: number) => {
    setPlayerCurrentTime(time);
    // No longer sets activeHighlightId here - it's derived via useMemo
  }, []);

  const handleDurationChange = useCallback((dur: number) => {
    setDuration(dur);
  }, []);

  // ---- Status rendering ----
  const cls = "result-workspace" + (className ? " " + className : "");

  if (loading) {
    return (
      <div className={cls}>
        <div className="result-workspace__status">
          <div className="result-workspace__spinner" />
          <p>{"\u52a0\u8f7d\u4e2d..."}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cls}>
        <div className="result-workspace__status result-workspace__status--error">
          <p>{"\u65e0\u6cd5\u52a0\u8f7d\u7ed3\u679c"}</p>
          <p className="result-workspace__error-detail">{error}</p>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className={cls}>
        <div className="result-workspace__status">
          <p>{"\u6682\u65e0\u6570\u636e"}</p>
        </div>
      </div>
    );
  }

  if (data.status === "uploaded" || data.status === "pending" || data.status === "running") {
    return (
      <div className={cls}>
        <div className="result-workspace__status">
          <div className="result-workspace__spinner" />
          <p>{"\u4efb\u52a1\u72b6\u6001: "}<strong>{data.status}</strong></p>
          {data.warnings.length > 0 && (
            <div className="result-workspace__warnings">
              {data.warnings.map((w, i) => <p key={i} className="result-workspace__warning">{w}</p>)}
            </div>
          )}
        </div>
      </div>
    );
  }

  if (data.status === "failed") {
    return (
      <div className={cls}>
        <div className="result-workspace__status result-workspace__status--error">
          <p>{"\u4efb\u52a1\u5931\u8d25"}</p>
          {data.error && <p className="result-workspace__error-detail">{data.error}</p>}
          {data.warnings.length > 0 && (
            <div className="result-workspace__warnings">
              {data.warnings.map((w, i) => <p key={i} className="result-workspace__warning">{w}</p>)}
            </div>
          )}
          {highlights.length > 0 && (
            <div className="result-workspace__partial">
              <p>{"\u90e8\u5206\u7ed3\u679c\u53ef\u7528"}</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  const showReportLinks = data.report && (data.report.markdown_url || data.report.json_url);
  const reportMetrics = useMemo(
    () => computeMetrics(data.highlights ?? [], data.clips?.length ?? 0, data.duration),
    [data.highlights, data.clips, data.duration],
  );
  const dominantDim = useMemo(
    () => computeDominantDimension(data.highlights ?? []),
    [data.highlights],
  );
  const currentDuration = duration > 0 ? duration : videoDuration;

  return (
    <div className={cls}>
      {data.status === "completed_with_errors" && (
        <div className="result-workspace__banner banner--warning">
          <span>{"\u90e8\u5206\u5206\u6790\u6b65\u9aa4\u6267\u884c\u5931\u8d25"}</span>
          {data.warnings.length > 0 && (
            <ul className="result-workspace__banner-list">
              {data.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          )}
        </div>
      )}

      <div className="result-workspace__player-section">
        <div className="result-workspace__mode-bar">
          <span className="result-workspace__mode-label">
            {mode === "source" ? "\u539f\u89c6\u9891\u6a21\u5f0f" : "\u7247\u6bb5\u6a21\u5f0f"}
          </span>
          {mode === "clip" && (
            <button className="result-workspace__back-btn" onClick={handleBackToSource} type="button">
              {"\u2190 \u8fd4\u56de\u539f\u89c6\u9891"}
            </button>
          )}
        </div>
        <VideoPlayer
          ref={playerRef}
          src={playerSrc ?? null}
          seekRequest={seekRequest}
          onTimeUpdate={handleTimeUpdate}
          onDurationChange={handleDurationChange}
          onLoadedMetadata={handleLoadedMetadata}
          onError={(msg) => { console.warn("VideoPlayer error:", msg); }}
        />
      </div>

      <div className="result-workspace__timeline-section">
        <HighlightTimeline
          duration={currentDuration}
          highlights={highlights}
          currentTime={sourceDisplayTime}
          selectedHighlightId={selectedHighlightId}
          activeHighlightId={activeHighlightId}
          onSelectHighlight={handleSelectHighlight}
          onSeek={handleTimelineSeek}
        />
      </div>

      <div className="result-workspace__body">
        <div className="result-workspace__list-section">
          <HighlightList
            highlights={highlights}
            selectedHighlightId={selectedHighlightId}
            activeHighlightId={activeHighlightId}
            onSelectHighlight={handleSelectHighlight}
          />
        </div>

        <div className="result-workspace__info-section">
          {clips.length > 0 && (
            <div className="result-workspace__clips-card">
              <h3 className="result-workspace__card-title">{"\u5bfc\u51fa\u7247\u6bb5"}</h3>
              <div className="result-workspace__clip-list">
                {clips.map((clip) => {
                  const matchedHL = clip.highlight_id != null
                    ? highlights.find((hl) => hl.id === clip.highlight_id)
                    : null;
                  return (
                    <button
                      key={clip.id}
                      type="button"
                      className={
                        "result-workspace__clip-btn" +
                        (selectedClipId === clip.id ? " result-workspace__clip-btn--active" : "")
                      }
                      onClick={() => handleClipClick(clip)}
                    >
                      <span className="result-workspace__clip-name">
                        {clip.id}
                        {matchedHL && (
                          <span className="result-workspace__clip-score">
                            {" "}({matchedHL.selection_score.toFixed(3)})
                          </span>
                        )}
                      </span>
                      <span className="result-workspace__clip-duration">
                        {clip.duration != null ? clip.duration.toFixed(1) + "s" : ""}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {showReportLinks && (
            <div className="result-workspace__reports-card">
              <h3 className="result-workspace__card-title">{"\u5206\u6790\u62a5\u544a"}</h3>
              <div className="result-workspace__report-links">
                {data.report.markdown_url && (
                  <a href={data.report.markdown_url} target="_blank" rel="noreferrer" className="result-workspace__report-link">
                    {"Markdown \u62a5\u544a"}
                  </a>
                )}
                {data.report.json_url && (
                  <a href={data.report.json_url} target="_blank" rel="noreferrer" className="result-workspace__report-link">
                    {"JSON \u62a5\u544a"}
                  </a>
                )}
              </div>
            </div>
          )}

          {data.warnings.length > 0 && data.status !== "completed_with_errors" && (
            <div className="result-workspace__warnings-card">
              <h3 className="result-workspace__card-title">{"\u8b66\u544a"}</h3>
              <ul className="result-workspace__warnings-list">
                {data.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* ── Report / Insight Section ── */}
      {(data.status as string) !== "uploaded" && (data.status as string) !== "pending" && (
        <div className="result-workspace__report-section">
          <ReportOverview metrics={reportMetrics} status={data.status} />
          <InsightPanel metrics={reportMetrics} dominantDim={dominantDim} />
          <div className="result-workspace__report-row">
            <div className="result-workspace__report-col">
              <ScoreDistribution highlights={data.highlights ?? []} />
            </div>
            <div className="result-workspace__report-col">
              <ReportActions
                metrics={reportMetrics}
                markdownUrl={data.report?.markdown_url ?? null}
                highlights={data.highlights ?? []}
              />
            </div>
          </div>
          <ClipExplorer
            clips={data.clips ?? []}
            highlights={data.highlights ?? []}
            onPlayClip={(clip) => {
              setMode("clip");
              setSelectedClipId(clip.id);
              setSelectedHighlightId(clip.highlight_id);
            }}
          />
          <TechnicalInfoPanel data={data} />
        </div>
      )}
    </div>
  );
}

export default ResultWorkspace;
