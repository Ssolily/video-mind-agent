// ── DesktopLayout (Enhanced) ───────────────────────
// Uses new UploadPanel, TaskStatusCard, ErrorState, ResultSummary components.

import React, { useState } from "react";
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
import ResultSummary from "../components/ResultSummary";
import "./DesktopLayout.css";

interface DesktopLayoutProps {
  children?: React.ReactNode;
  videoId: string;
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
  onVisualize: () => void;
  appPage?: string;
  onNavigateHome?: () => void;
  onNavigateHistory?: () => void;
  onOpenVideo?: (videoId: string) => void;
  historyTasks?: Array<{ videoId: string; filename: string; status: string; createdAt: string; updatedAt: string; }>;
  onRemoveHistory?: (videoId: string) => void;
}

export default function DesktopLayout(props: DesktopLayoutProps) {
  const {
    file, setFile, goal, setGoal, sampleFps, setSampleFps, topK, setTopK, planner, setPlanner,
    state, uploadResult, task, report, visResult, visLoading, error, progressPct,
    handleStart, onVisualize, onCancel, onRetry, videoId,
  } = props;

  const isUploading = state === "uploading";
  const isAnalyzing = state === "analyzing";
  const isBusy = isUploading || isAnalyzing;
  const isDone = state === "done";
  const isError = state === "error";

  return (
    <div className="desktop-layout">
      <header className="desktop-layout__header">
        <div>
          <h1 className="desktop-layout__title">VideoMind Agent</h1>
          <p className="desktop-layout__subtitle">视频内容理解与自动剪辑</p>
        </div>
        <div className="desktop-layout__header-right">
          <div className="desktop-layout__planner-badge">
            {planner === "llm" ? "🤖 LLM" : "⚙️ Rule"}
          </div>
          <ThemeToggle />
        </div>
      </header>

      <div className="desktop-layout__body">

        {/* Left sidebar: Upload + Params + Status */}
        <div className="desktop-layout__sidebar">

          {/* Upload card */}
          <div className="desktop-layout__card">
            <h2 className="desktop-layout__card-title">上传视频</h2>
            <UploadPanel
              file={file}
              setFile={setFile}
              disabled={isBusy}
              uploading={isUploading}
            />

            <div className="desktop-layout__params">
              <div className="desktop-layout__field">
                <label className="desktop-layout__label">分析目标</label>
                <input className="desktop-layout__input" type="text" value={goal}
                  onChange={(e) => setGoal(e.target.value)} disabled={isBusy}
                  placeholder="如：检测物体、字幕、生成报告" />
              </div>

              <div className="desktop-layout__field-row">
                <div className="desktop-layout__field">
                  <label className="desktop-layout__label">抽帧 FPS</label>
                  <input className="desktop-layout__input" type="number" value={sampleFps}
                    onChange={(e) => setSampleFps(Number(e.target.value))}
                    min={0.1} max={10} step={0.1} disabled={isBusy} />
                </div>
                <div className="desktop-layout__field">
                  <label className="desktop-layout__label">推荐数</label>
                  <input className="desktop-layout__input" type="number" value={topK}
                    onChange={(e) => setTopK(Number(e.target.value))}
                    min={1} max={20} disabled={isBusy} />
                </div>
              </div>

              <div className="desktop-layout__field">
                <label className="desktop-layout__label">Planner 模式</label>
                <div className="desktop-layout__radio-group">
                  <label className="desktop-layout__radio">
                    <input type="radio" name="planner" value="rule"
                      checked={planner === "rule"}
                      onChange={() => setPlanner("rule")} disabled={isBusy} />
                    Rule
                  </label>
                  <label className="desktop-layout__radio">
                    <input type="radio" name="planner" value="llm"
                      checked={planner === "llm"}
                      onChange={() => setPlanner("llm")} disabled={isBusy} />
                    LLM
                  </label>
                  {planner === "llm" && (
                    <span className="desktop-layout__llm-hint">(需要 DeepSeek API Key)</span>
                  )}
                </div>
              </div>

              <div className="desktop-layout__actions">
                <button className="desktop-layout__start-btn" onClick={handleStart} disabled={isBusy || !file}>
                  {isUploading ? "上传中..." : isAnalyzing ? "分析中..." : "开始分析"}
                </button>
              </div>
            </div>
          </div>

          {/* Task Status Card */}
          {(isAnalyzing || (task && ["running", "queued", "pending", "success", "completed", "completed_with_errors", "failed", "cancelled", "timeout", "interrupted"].includes(task.status))) && (
            <TaskStatusCard
              task={task}
              progressPct={progressPct}
              onCancel={onCancel}
              onRetry={onRetry}
            />
          )}

          {/* Error display using ErrorState */}
          {isError && error && (
            <ErrorState
              message={error}
              onRetry={onRetry}
            />
          )}
        </div>

        {/* Right: Main content area */}
        <div className="desktop-layout__main">

          {/* Idle state */}
          {state === "idle" && !file && !error && (
            <EmptyState
              icon="🎥"
              title="开始视频分析"
              description="上传一个视频文件，系统将自动分析视频内容，检测物体、场景、字幕，并推荐精彩片段。"
            />
          )}

          {state === "idle" && file && !error && (
            <EmptyState
              icon="✅"
              title="文件已就绪"
              description={`已选择 ${file.name}。点击"开始分析"按钮启动分析流程。`}
            />
          )}

          {/* Result Workspace */}
          {isDone && videoId && (
            <>
              <ResultWorkspace videoId={videoId} />
            </>
          )}

          {/* Report */}
          {report && (
            <div className="desktop-layout__card">
              <h2 className="desktop-layout__card-title">分析报告</h2>
              <p style={{ fontSize: 13, marginBottom: 12 }}>
                <a href={report.json_url || "#"} target="_blank" rel="noreferrer">JSON 报告</a>
                {" | "}
                <a href={report.markdown_url || "#"} target="_blank" rel="noreferrer">Markdown 报告</a>
              </p>
              {report.markdown && (
                <div className="desktop-layout__report-content">
                  <Markdown>{report.markdown}</Markdown>
                </div>
              )}
            </div>
          )}

          {/* Visualization */}
          {task?.result?.steps?.some((s: { step: string; status: string }) => s.step === "detect_objects" && s.status === "ok") && (
            <div className="desktop-layout__card">
              <h2 className="desktop-layout__card-title">检测可视化</h2>
              <button className="desktop-layout__vis-btn" onClick={onVisualize} disabled={visLoading}>
                {visLoading ? "生成中..." : "生成可视化"}
              </button>
              {visResult && (
                <>
                  <p style={{ fontSize: 13, color: "#666", marginBottom: 8 }}>
                    共 {visResult.frame_count} 帧，显示前 20 张
                  </p>
                  <div className="desktop-layout__vis-grid">
                    {visResult.image_urls.slice(0, 20).map((url: string, i: number) => (
                      <div key={i} style={{ border: "1px solid #eee", borderRadius: 6, overflow: "hidden" }}>
                        <img src={url} alt={"Frame " + i} style={{ width: "100%", display: "block" }} loading="lazy" />
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
