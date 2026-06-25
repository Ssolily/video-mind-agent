// ── reportInsights.ts ──────────────────────────────
// Utility functions for computing report-level insights from highlight data.
// All functions are pure and deterministic — no LLM calls.

import type { HighlightResult, HighlightScoreBreakdown } from "../types/video";

// ── Types ──────────────────────────────────────────

export interface ReportMetrics {
  totalDuration: number;          // Video duration in seconds
  highlightCount: number;
  clipCount: number;
  averageScore: number;
  maxScore: number;
  minScore: number;
  coverageSeconds: number;       // Total unique coverage of highlights
  coveragePercent: number;       // coverageSeconds / totalDuration
  topHighlights: HighlightResult[];
  /** How many highlights have a clip exported */
  clipsHighlightCount: number;
}

export interface DominantDimension {
  name: string;
  averageScore: number;
  displayName: string;
}

export interface BucketInfo {
  bucket: string;    // e.g. "0.0-0.2"
  count: number;
  percent: number;
  highlights: HighlightResult[];
}

type DimKey = keyof HighlightScoreBreakdown;

const DIMENSION_NAMES: Record<string, string> = {
  object: "物体检测",
  motion: "运动强度",
  speech: "语音内容",
  scene: "场景变化",
  quality: "画面质量",
  audio: "音频分析",
  face: "人脸检测",
  text: "文字检测",
};

// ── Helpers ────────────────────────────────────────

function safeScore(v: any): number {
  const n = Number(v);
  return Number.isFinite(n) ? Math.max(0, Math.min(1, n)) : 0;
}

function getBaseScore(hl: HighlightResult): number {
  return safeScore(hl.base_score ?? hl.score);
}

function getSelScore(hl: HighlightResult): number {
  if (Number.isFinite(hl.selection_score) && hl.selection_score > 0) {
    return safeScore(hl.selection_score);
  }
  return safeScore(hl.score);
}

// ── Metrics ────────────────────────────────────────

export function computeMetrics(
  highlights: HighlightResult[],
  clipCount: number,
  videoDuration: number | null,
): ReportMetrics {
  const valid = (highlights ?? []).filter(
    (h) => typeof h.start_time === "number" && typeof h.end_time === "number" && Number.isFinite(h.start_time) && Number.isFinite(h.end_time) && h.end_time > h.start_time,
  );

  const total = videoDuration && Number.isFinite(videoDuration) && videoDuration > 0 ? videoDuration : 0;

  const scores = valid.map(getSelScore);
  const avg = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
  const maxScore = scores.length > 0 ? Math.max(...scores) : 0;
  const minScore = scores.length > 0 ? Math.min(...scores) : 0;

  // Compute total unique coverage (merge overlapping ranges)
  const sorted = [...valid].sort((a, b) => a.start_time - b.start_time);
  let coverageSeconds = 0;
  if (sorted.length > 0) {
    let curStart = sorted[0].start_time;
    let curEnd = sorted[0].end_time;
    for (const h of sorted) {
      if (h.start_time <= curEnd) {
        curEnd = Math.max(curEnd, h.end_time);
      } else {
        coverageSeconds += curEnd - curStart;
        curStart = h.start_time;
        curEnd = h.end_time;
      }
    }
    coverageSeconds += curEnd - curStart;
  }

  const coveragePercent = total > 0 ? (coverageSeconds / total) * 100 : 0;

  // Top highlights by score
  const topHighlights = [...valid]
    .sort((a, b) => getSelScore(b) - getSelScore(a))
    .slice(0, 3);

  const clipsHighlightCount = valid.filter((h) => h.id).length;

  return {
    totalDuration: total,
    highlightCount: valid.length,
    clipCount,
    averageScore: Math.round(avg * 1000) / 1000,
    maxScore: Math.round(maxScore * 1000) / 1000,
    minScore: Math.round(minScore * 1000) / 1000,
    coverageSeconds: Math.round(coverageSeconds * 10) / 10,
    coveragePercent: Math.round(coveragePercent * 10) / 10,
    topHighlights,
    clipsHighlightCount,
  };
}

// ── Score buckets ─────────────────────────────────

export function computeScoreDistribution(highlights: HighlightResult[]): BucketInfo[] {
  const buckets: BucketInfo[] = [
    { bucket: "0.0–0.2", count: 0, percent: 0, highlights: [] },
    { bucket: "0.2–0.4", count: 0, percent: 0, highlights: [] },
    { bucket: "0.4–0.6", count: 0, percent: 0, highlights: [] },
    { bucket: "0.6–0.8", count: 0, percent: 0, highlights: [] },
    { bucket: "0.8–1.0", count: 0, percent: 0, highlights: [] },
  ];

  const valid = (highlights ?? []).filter(
    (h) => typeof h.score === "number" && Number.isFinite(h.score),
  );

  for (const h of valid) {
    const score = safeScore(h.score);
    const idx = score >= 0.8 ? 4 : score >= 0.6 ? 3 : score >= 0.4 ? 2 : score >= 0.2 ? 1 : 0;
    buckets[idx].count++;
    buckets[idx].highlights.push(h);
  }

  const total = valid.length;
  for (const b of buckets) {
    b.percent = total > 0 ? Math.round((b.count / total) * 100) : 0;
  }

  return buckets;
}

// ── Dominant dimension ────────────────────────────

export function computeDominantDimension(highlights: HighlightResult[]): DominantDimension | null {
  const withBreakdown = (highlights ?? []).filter((h) => h.score_breakdown && Object.keys(h.score_breakdown).length > 0);
  if (withBreakdown.length === 0) return null;

  const dimScores: Record<string, number[]> = {};
  for (const h of withBreakdown) {
    for (const [key, comp] of Object.entries(h.score_breakdown)) {
      if (!dimScores[key]) dimScores[key] = [];
      dimScores[key].push(safeScore(comp.raw ?? comp.weighted));
    }
  }

  let bestDim: string | null = null;
  let bestAvg = 0;

  for (const [key, vals] of Object.entries(dimScores)) {
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
    if (avg > bestAvg) {
      bestAvg = avg;
      bestDim = key;
    }
  }

  if (!bestDim) return null;

  return {
    name: bestDim,
    averageScore: Math.round(bestAvg * 1000) / 1000,
    displayName: DIMENSION_NAMES[bestDim] || bestDim,
  };
}

// ── Simple insight description ────────────────────

export function generateInsightDescription(
  metrics: ReportMetrics,
  dominantDim: DominantDimension | null,
): string {
  if (metrics.highlightCount === 0) {
    return "系统未检测到符合条件的精彩片段。视频可能缺乏显著的运动、场景变化或语音内容，建议使用评分权重较低或包含更丰富内容的视频重新分析。";
  }

  const avgDesc = metrics.averageScore >= 0.7
    ? "整体评分较高"
    : metrics.averageScore >= 0.4
      ? "整体评分中等"
      : "整体评分偏低";

  const coverDesc = metrics.coveragePercent >= 30
    ? "覆盖了视频的较大部分"
    : metrics.coveragePercent >= 10
      ? "覆盖了视频的多个片段"
      : "聚焦于少数关键片段";

  let dimDesc = "";
  if (dominantDim) {
    if (dominantDim.name === "speech" || dominantDim.name === "audio") {
      dimDesc = "推荐主要受到语音内容影响，有对话或讲解的片段评分较高。";
    } else if (dominantDim.name === "object") {
      dimDesc = "推荐主要受到物体检测结果影响，目标丰富的片段评分较高。";
    } else if (dominantDim.name === "motion") {
      dimDesc = "推荐主要受到运动强度变化影响，动态场景评分较高。";
    } else if (dominantDim.name === "scene") {
      dimDesc = "推荐主要受到场景变化影响，转换较多的片段评分较高。";
    } else if (dominantDim.name === "quality") {
      dimDesc = "推荐主要受到画面质量因素影响。";
    } else {
      dimDesc = `推荐主要受到${dominantDim.displayName}因素影响。`;
    }
  } else {
    dimDesc = "当前没有可用的评分分解数据来进一步解释推荐理由。";
  }

  return `系统在 ${metrics.highlightCount} 个精彩片段中，${avgDesc}（平均 ${metrics.averageScore.toFixed(3)}），${coverDesc}（覆盖率 ${metrics.coveragePercent}%）。${dimDesc}`;
}

// ── Individual highlight explanation ──────────────

export function generateHLExplanation(hl: HighlightResult): string {
  const parts: string[] = [];
  const score = getSelScore(hl);
  const baseScore = getBaseScore(hl);

  if (baseScore > 0.6) parts.push("基础分较高");
  else if (baseScore > 0.3) parts.push("基础分中等");
  else parts.push("基础分较低");

  if (Array.isArray(hl.reason) && hl.reason.length > 0) {
    parts.push(hl.reason.join("；"));
  }

  if (hl.score_breakdown && Object.keys(hl.score_breakdown).length > 0) {
    const topDim = Object.entries(hl.score_breakdown)
      .map(([k, v]) => ({ name: DIMENSION_NAMES[k] || k, score: safeScore(v.raw ?? v.weighted) }))
      .sort((a, b) => b.score - a.score)
      .slice(0, 2)
      .map((d) => `${d.name}(${d.score.toFixed(2)})`);
    if (topDim.length > 0) {
      parts.push(`主要维度: ${topDim.join("、")}`);
    }
  }

  return parts.length > 0 ? parts.join("；") : `综合评分 ${score.toFixed(3)}`;
}

export { getSelScore, safeScore, DIMENSION_NAMES };
