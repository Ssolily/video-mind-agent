// ── MobileLayout (Enhanced) ────────────────────────
// Uses new UploadPanel, TaskStatusCard, ErrorState, EmptyState, ResultSummary.

import React from "react";
import RecentTasksPanel from "../components/history/RecentTasksPanel";
import ProductIntroPanel from "../components/history/ProductIntroPanel";
import ThemeToggle from "../components/ThemeToggle";
import { UploadResult, TaskResult, ReportResult, VisualizeResult } from "../api";
import Markdown from "react-markdown";
import ResultWorkspace from "../components/ResultWorkspace";
import UploadPanel from "../components/UploadPanel";
import TaskStatusCard from "../components/TaskStatusCard";
import ErrorState from "../components/ErrorState";
import EmptyState from "../components/EmptyState";
import "./MobileLayout.css";

interface MobileLayoutProps {
  children?: React.ReactNode;
  file: File | null;
  setFile: (f: File | null) => void;
  goal: string;
  setGoal: (v: string) => void;
  sampleFps: number;
  setSampleFps: (v: number) => void;
  topK: number;
  setTopK: (v: number) => void;
  planner: string;
  setPlanner: (v: string) => void;
  state: string;
  uploadResult: UploadResult | null;
  task: TaskResult | null;
  report: ReportResult | null;
  visResult: VisualizeResult | null;
  visLoading: boolean;
  error: string;
  progressPct: number;
  handleStart: () => void;
  onCancel?: () => void;
  onRetry?: () => void;
  videoId?: string;
  onVisualize: () => void;
  appPage?: string;
  onNavigateHome?: () => void;
  onNavigateHistory?: () => void;
  onOpenVideo?: (videoId: string) => void;
  historyTasks?: Array<{ videoId: string; filename: string; status: string; createdAt: string; updatedAt: string; }>;
  onRemoveHistory?: (videoId: string) => void;
}

export default function MobileLayout(props: MobileLayoutProps) {
  const {
    children,
    file, setFile, goal, setGoal, sampleFps, setSampleFps, topK, setTopK, planner, setPlanner,
    state, uploadResult, task, report, visResult, visLoading, error, progressPct,
    handleStart, onVisualize, onCancel, onRetry, videoId,
    appPage, onNavigateHome, onNavigateHistory, onOpenVideo, historyTasks, onRemoveHistory,
  } = props;

  const isBusy = state === "uploading" || state === "analyzing";
  const isDone = state === "done";
  const isError = state === "error";

  return (
    <div className="mobile-layout">
      <header className="mobile-layout__header" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <h1 className="mobile-layout__title">VideoMind Agent</h1>
        <div style={{ display: "flex", gap: "var(--space-2)", alignItems: "center" }}>
          {onNavigateHistory && <button className="mobile-layout__nav-btn" onClick={onNavigateHistory}>历史</button>}
        </div>
      </header>

      <div className="mobile-layout__body">

        <div className="mobile-layout__card">
          <h2 className="mobile-layout__card-title">上传视频</h2>
          <UploadPanel file={file} setFile={setFile} disabled={isBusy} uploading={state === "uploading"} />

          <div className="mobile-layout__field">
            <label className="mobile-layout__label">分析目标</label>
            <input className="mobile-layout__input" type="text" value={goal}
              onChange={(e) => setGoal(e.target.value)} disabled={isBusy}
              placeholder="如：检测物体、字幕、生成报告" />
          </div>

          <div className="mobile-layout__field-row">
            <div className="mobile-layout__field" style={{ flex: 1 }}>
              <label className="mobile-layout__label">FPS</label>
              <input className="mobile-layout__input" type="number" value={sampleFps}
                onChange={(e) => setSampleFps(Number(e.target.value))}
                min={0.1} max={10} step={0.1} disabled={isBusy} />
            </div>
            <div className="mobile-layout__field" style={{ flex: 1 }}>
              <label className="mobile-layout__label">推荐数</label>
              <input className="mobile-layout__input" type="number" value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                min={1} max={20} disabled={isBusy} />
            </div>
          </div>

          <div className="mobile-layout__field">
            <label className="mobile-layout__label">Planner</label>
            <div className="mobile-layout__radio-group">
              <label className="mobile-layout__radio">
                <input type="radio" name="planner" value="rule"
                  checked={planner === "rule"} onChange={() => setPlanner("rule")} disabled={isBusy} />
                Rule
              </label>
              <label className="mobile-layout__radio">
                <input type="radio" name="planner" value="llm"
                  checked={planner === "llm"} onChange={() => setPlanner("llm")} disabled={isBusy} />
                LLM
              </label>
            </div>
          </div>

          <button className="mobile-layout__start-btn" onClick={handleStart} disabled={isBusy || !file}>
            {state === "uploading" ? "上传中..." : state === "analyzing" ? "分析中..." : "开始分析"}
          </button>
        </div>

        {(isBusy || (task && ["running","queued","success","completed","failed","cancelled"].includes(task.status))) && (
          <TaskStatusCard task={task} progressPct={progressPct} onCancel={onCancel} onRetry={onRetry} />
        )}

        {isError && error && (
          <ErrorState message={error} onRetry={onRetry} />
        )}

        {state === "idle" && !file && !error && (
          <EmptyState icon="🎥" title="开始视频分析"
            description="上传视频文件，系统将自动分析视频内容并推荐精彩片段。" />
        )}
        {state === "idle" && historyTasks && historyTasks.length > 0 && (
          <RecentTasksPanel tasks={historyTasks.slice(0, 5)} onOpen={onOpenVideo ? (e) => onOpenVideo(e.videoId) : (() => {})} onViewAll={onNavigateHistory || (() => {})} />
        )}

        {isDone && videoId && <ResultWorkspace videoId={videoId} />}

        {report && (
          <div className="mobile-layout__card">
            <h2 className="mobile-layout__card-title">分析报告</h2>
            <p style={{ fontSize: 13, marginBottom: 12 }}>
              <a href={report.json_url || "#"} target="_blank" rel="noreferrer">JSON</a>
              {" | "}
              <a href={report.markdown_url || "#"} target="_blank" rel="noreferrer">Markdown</a>
            </p>
            {report.markdown && (
              <div className="mobile-layout__report-content">
                <Markdown>{report.markdown}</Markdown>
              </div>
            )}
          </div>
        )}

        {visResult && (
          <div className="mobile-layout__card">
            <h2 className="mobile-layout__card-title">检测可视化</h2>
            <div className="mobile-layout__vis-grid">
              {visResult.image_urls.slice(0, 10).map((url: string, i: number) => (
                <img key={i} src={url} alt={"Frame " + i} style={{ width: "100%", display: "block" }} loading="lazy" />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
