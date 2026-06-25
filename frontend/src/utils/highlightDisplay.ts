import type { HighlightResult, ScoreComponent } from "../types/video";

// ---- formatScore ----

export function formatScore(value: number, digits = 3): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "0.000";
  const d = Math.max(0, Math.min(digits, 6));
  return value.toFixed(d);
}

// ---- getPrimaryHighlightScore ----

export function getPrimaryHighlightScore(highlight: HighlightResult): number {
  if (typeof highlight.selection_score === "number" && Number.isFinite(highlight.selection_score)) {
    return highlight.selection_score;
  }
  if (typeof highlight.score === "number" && Number.isFinite(highlight.score)) {
    return highlight.score;
  }
  return 0;
}

// ---- formatHighlightReason ----

export function formatHighlightReason(reason: string[] | string | null | undefined): string {
  if (reason == null) return "\u6682\u65e0\u8bc4\u5206\u8bf4\u660e";
  if (Array.isArray(reason)) {
    const filtered = reason.map((s) => (typeof s === "string" ? s.trim() : "")).filter(Boolean);
    if (filtered.length === 0) return "\u6682\u65e0\u8bc4\u5206\u8bf4\u660e";
    return filtered.join("\uff1b");
  }
  if (typeof reason === "string") {
    return reason.trim() || "\u6682\u65e0\u8bc4\u5206\u8bf4\u660e";
  }
  return "\u6682\u65e0\u8bc4\u5206\u8bf4\u660e";
}

// ---- sortHighlightsForDisplay ----

export function sortHighlightsForDisplay(highlights: HighlightResult[]): HighlightResult[] {
  if (!Array.isArray(highlights)) return [];
  return [...highlights].sort((a, b) => {
    const aStartValid = typeof a.start_time === "number" && Number.isFinite(a.start_time);
    const bStartValid = typeof b.start_time === "number" && Number.isFinite(b.start_time);

    // Invalid start_time items go after valid ones
    if (aStartValid !== bStartValid) return aStartValid ? -1 : 1;

    if (aStartValid && bStartValid) {
      if (a.start_time !== b.start_time) return a.start_time - b.start_time;

      // Same start_time: valid end_time first
      const aEndValid = typeof a.end_time === "number" && Number.isFinite(a.end_time);
      const bEndValid = typeof b.end_time === "number" && Number.isFinite(b.end_time);
      if (aEndValid !== bEndValid) return aEndValid ? -1 : 1;

      if (aEndValid && bEndValid && a.end_time !== b.end_time) return a.end_time - b.end_time;
    }

    // Same time: higher selection_score first
    const sa = getPrimaryHighlightScore(a);
    const sb = getPrimaryHighlightScore(b);
    if (sa !== sb) return sb - sa;

    // Same score: id ascending
    if (a.id < b.id) return -1;
    if (a.id > b.id) return 1;
    return 0;
  });
}

// ---- sortHighlightsByScore (deprecated alias) ----

/** @deprecated Use sortHighlightsForDisplay instead. */
export function sortHighlightsByScore(highlights: HighlightResult[]): HighlightResult[] {
  return sortHighlightsForDisplay(highlights);
}

// ---- getScoreDimensions ----

export interface ScoreDimension {
  name: string;
  displayName: string;
  raw: number;
  weight: number;
  weighted: number;
  isPlaceholder: boolean;
}

const DIMENSION_LABELS: Record<string, string> = {
  object: "\u76ee\u6807",
  motion: "\u8fd0\u52a8",
  speech: "\u8bed\u97f3",
  scene: "\u573a\u666f",
  quality: "\u753b\u8d28",
};

const STABLE_DIM_ORDER = ["object", "motion", "speech", "scene", "quality"];

export function getScoreDimensions(breakdown: Record<string, ScoreComponent> | null | undefined): ScoreDimension[] {
  if (!breakdown || typeof breakdown !== "object") return [];

  const results: ScoreDimension[] = [];

  // Process known dimensions in stable order
  for (const dim of STABLE_DIM_ORDER) {
    const comp = breakdown[dim];
    if (comp && typeof comp === "object") {
      const raw = typeof comp.raw === "number" && Number.isFinite(comp.raw) ? comp.raw : 0;
      const weight = typeof comp.weight === "number" && Number.isFinite(comp.weight) ? comp.weight : 0;
      const weighted = typeof comp.weighted === "number" && Number.isFinite(comp.weighted) ? comp.weighted : 0;
      results.push({
        name: dim,
        displayName: DIMENSION_LABELS[dim] || dim,
        raw,
        weight,
        weighted,
        isPlaceholder: dim === "quality",
      });
    }
  }

  // Then unknown dimensions in alphabetical order
  const known = new Set(STABLE_DIM_ORDER);
  const unknownDims = Object.keys(breakdown).filter((k) => !known.has(k)).sort();
  for (const dim of unknownDims) {
    const comp = breakdown[dim];
    if (comp && typeof comp === "object") {
      const raw = typeof comp.raw === "number" && Number.isFinite(comp.raw) ? comp.raw : 0;
      const weight = typeof comp.weight === "number" && Number.isFinite(comp.weight) ? comp.weight : 0;
      const weighted = typeof comp.weighted === "number" && Number.isFinite(comp.weighted) ? comp.weighted : 0;
      results.push({
        name: dim,
        displayName: dim,
        raw,
        weight,
        weighted,
        isPlaceholder: false,
      });
    }
  }

  return results;
}
