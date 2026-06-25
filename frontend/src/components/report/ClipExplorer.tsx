// ── ClipExplorer ──────────────────────────────────
// Productized clip explorer with play, open, copy actions.

import React, { useCallback } from "react";
import { useToast } from "../toast/useToast";
import type { ClipResult, HighlightResult } from "../../types/video";
import { resolveApiUrl } from "../../api";
import EmptyState from "../EmptyState";
import "./ClipExplorer.css";

export interface ClipExplorerProps {
  clips: ClipResult[];
  highlights: HighlightResult[];
  onPlayClip?: (clip: ClipResult) => void;
  className?: string;
}

function fmtTime(s: number | null): string {
  if (s == null || !Number.isFinite(s)) return "--:--";
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
}

function findScore(clip: ClipResult, highlights: HighlightResult[]): number | null {
  if (clip.highlight_id) {
    const hl = highlights.find((h) => h.id === clip.highlight_id);
    if (hl) return hl.score;
  }
  return null;
}

function ClipExplorer({ clips, highlights, onPlayClip, className }: ClipExplorerProps) {
  const { addToast } = useToast();
  const list = clips ?? [];

  const handleCopyUrl = useCallback(async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      addToast("success", "片段链接已复制");
    } catch { addToast("error", "复制失败"); }
  }, [addToast]);

  if (list.length === 0) {
    return (
      <div className={"clip-explorer" + (className ? " " + className : "")}>
        <h3 className="clip-explorer__title">导出片段</h3>
        <EmptyState icon="🎬" title="暂无导出片段" description="highlight 导出片段尚未生成，或当前视频没有可导出的片段。" />
      </div>
    );
  }

  return (
    <div className={"clip-explorer" + (className ? " " + className : "")}>
      <h3 className="clip-explorer__title">导出片段 ({list.length})</h3>
      <div className="clip-explorer__list">
        {list.map((clip, i) => {
          const score = findScore(clip, highlights);
          const url = resolveApiUrl(clip.url);
          return (
            <div key={clip.id || i} className="clip-explorer__item">
              <div className="clip-explorer__info">
                <span className="clip-explorer__index">#{i + 1}</span>
                <span className="clip-explorer__time">
                  {fmtTime(clip.start_time)} – {fmtTime(clip.end_time)}
                </span>
                {clip.duration != null && (
                  <span className="clip-explorer__duration">{clip.duration.toFixed(1)}s</span>
                )}
                {score != null && (
                  <span className="clip-explorer__score">{score.toFixed(3)}</span>
                )}
              </div>
              <div className="clip-explorer__actions">
                {url && (
                  <button
                    className="clip-explorer__action-btn"
                    onClick={() => onPlayClip?.(clip)}
                    title="播放此片段"
                  >
                    ▶ 播放
                  </button>
                )}
                {url && (
                  <a
                    href={url}
                    target="_blank"
                    rel="noreferrer"
                    className="clip-explorer__action-btn clip-explorer__link-btn"
                  >
                    ↗ 打开
                  </a>
                )}
                {url && (
                  <button
                    className="clip-explorer__action-btn clip-explorer__copy-btn"
                    onClick={() => handleCopyUrl(url)}
                    title="复制链接"
                  >
                    📋 复制
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ClipExplorer;
