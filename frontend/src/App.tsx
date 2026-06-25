import { useState, useRef, useEffect, useCallback } from "react";
import { uploadVideo, startAgentRun, pollTask, getReport, visualizeDetections, cancelTask, retryTask, type UploadResult, type TaskResult, type ReportResult, type VisualizeResult } from "./api";
import { useDevice } from "./hooks/useDevice";
import ToastProvider from "./components/toast/ToastProvider";
import { useTaskHistory } from "./hooks/useTaskHistory";
import TaskHistoryPage from "./components/history/TaskHistoryPage";
import DesktopLayout from "./layouts/DesktopLayout";
import MobileLayout from "./layouts/MobileLayout";

type PageState = "home" | "idle" | "uploading" | "analyzing" | "done" | "error";
type AppPage = "home" | "history" | "results";

export default function App() {
  const [appPage, setAppPage] = useState<AppPage>("home");
  const { tasks: historyTasks, addEntry: addHistoryEntry, removeEntry: removeHistoryEntry, refresh: refreshHistory } = useTaskHistory();

  const [file, setFile] = useState<File | null>(null);
  const [goal, setGoal] = useState("分析视频");
  const [sampleFps, setSampleFps] = useState(1);
  const [topK, setTopK] = useState(5);
  const [planner, setPlanner] = useState("rule");

  const [state, setState] = useState<PageState>("home");
  const [videoId, setVideoId] = useState(() => {
    const hash = window.location.hash.replace("#", "");
    return hash || "";
  });
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [task, setTask] = useState<TaskResult | null>(null);
  const [report, setReport] = useState<ReportResult | null>(null);
  const [visResult, setVisResult] = useState<VisualizeResult | null>(null);
  const [visLoading, setVisLoading] = useState(false);
  const [error, setError] = useState("");
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [progressPct, setProgressPct] = useState(0);
  const filenameRef = useRef("");

  useEffect(() => {
    document.title = "VideoMind Agent";
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  useEffect(() => {
    if (state === "uploading") document.title = "VideoMind - 上传中...";
    else if (state === "analyzing") document.title = "VideoMind - 分析中...";
    else if (state === "done") document.title = "VideoMind - 分析完成";
    else if (state === "error") document.title = "VideoMind - 错误";
    else document.title = "VideoMind Agent";
  }, [state]);

  function startPoll(taskId: string) {
    const iv = setInterval(async () => {
      try {
        const t = await pollTask(taskId);
        setTask(t);
        setProgressPct(Math.round(t.progress * 100));
        if (t.status === "success" || t.status === "completed" || t.status === "completed_with_errors") {
          clearInterval(iv);
          pollRef.current = null;
          try {
            const rpt = await getReport(t.video_id);
            setReport(rpt);
          } catch (_) {}
          setState("done");
        } else if (t.status === "failed" || t.status === "timeout" || t.status === "interrupted") {
          clearInterval(iv);
          pollRef.current = null;
          setError(t.error || "Task failed");
          setState("error");
        }
      } catch (e: any) {
        clearInterval(iv);
        pollRef.current = null;
        setError("Poll error: " + e.message);
        setState("error");
      }
    }, 2000);
    pollRef.current = iv;
  }

  async function handleStart() {
    if (!file) { setError("请选择一个视频文件"); return; }
    setError("");
    setState("uploading");
    setTask(null);
    setReport(null);
    setVisResult(null);
    setProgressPct(0);
    filenameRef.current = file.name;
    try {
      const up = await uploadVideo(file);
      setUploadResult(up);
      setVideoId(up.video_id);
      addHistoryEntry({
        videoId: up.video_id,
        filename: up.filename,
        status: "queued",
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
      setAppPage("results");
      setState("analyzing");
      const { task_id } = await startAgentRun(up.video_id, goal, sampleFps, topK, planner);
      setTask((prev) => prev ? { ...prev, task_id } : { task_id, video_id: up.video_id, user_goal: goal, status: "queued", progress: 0, current_step: "", error: null });
      startPoll(task_id);
    } catch (e: any) {
      setError(e.message || "Unknown error");
      setState("error");
    }
  }

  // Add to history when task completes
  useEffect(() => {
    if ((state === "done" || state === "error") && videoId) {
      addHistoryEntry({
        videoId,
        taskId: task?.task_id,
        filename: filenameRef.current || videoId,
        status: state === "error" ? "failed" : (task?.status || "completed"),
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      });
    }
  }, [state, videoId]);

  async function handleVisualize() {
    if (!videoId) return;
    setVisLoading(true);
    try {
      const v = await visualizeDetections(videoId);
      setVisResult(v);
    } catch (e: any) { alert("可视化失败: " + e.message); }
    setVisLoading(false);
  }

  async function handleCancel() {
    if (!task?.task_id) return;
    try {
      await cancelTask(task.task_id);
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      setState("idle");
      setError("任务已取消");
    } catch (e: any) {
      setError("取消失败: " + e.message);
    }
  }

  async function handleRetry() {
    if (!task?.task_id) return;
    setError("");
    setState("analyzing");
    try {
      const { new_task_id } = await retryTask(task.task_id);
      startPoll(new_task_id);
    } catch (e: any) {
      setError("重试失败: " + e.message);
      setState("error");
    }
  }

  const handleNavigateHome = useCallback(() => {
    setAppPage("home");
    setState("home");
    setVideoId("");
    setTask(null);
    setReport(null);
    setError("");
    setVisResult(null);
    window.location.hash = "";
  }, []);

  const handleNavigateHistory = useCallback(() => {
    setAppPage("history");
  }, []);

  const handleOpenVideo = useCallback((vid: string) => {
    setVideoId(vid);
    setAppPage("results");
    setState("done");
    window.location.hash = vid;
  }, []);

  // Page routing
  if (appPage === "history") {
    const historyContent = (
      <TaskHistoryPage
        tasks={historyTasks}
        onOpen={(entry) => handleOpenVideo(entry.videoId)}
        onRemove={(entry) => removeHistoryEntry(entry.videoId)}
        onBack={handleNavigateHome}
        onClearAll={() => { removeHistoryEntry(""); localStorage.removeItem("videomind-history"); refreshHistory(); }}
        onUpload={() => { setAppPage("home"); setState("home"); }}
      />
    );
    // Wrap in minimal layout for history page
    return (<ToastProvider>
      <div className="desktop-layout" style={{ minHeight: "100vh", background: "var(--color-bg)" }}>
        <header className="desktop-layout__header" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "var(--space-4) var(--space-5)" }}>
          <h1 className="desktop-layout__title" style={{ fontSize: "var(--font-size-lg)", margin: 0 }}>VideoMind Agent</h1>
        </header>
        <div style={{ padding: "var(--space-3)" }}>
          {historyContent}
        </div>
      </div></ToastProvider>
    );
  }

  const layoutProps = {
    videoId,
    file, setFile, goal, setGoal, sampleFps, setSampleFps, topK, setTopK, planner, setPlanner,
    state, uploadResult, task, report, visResult, visLoading, error, progressPct,
    handleStart,
    onCancel: handleCancel,
    onRetry: handleRetry,
    onVisualize: handleVisualize,
    appPage,
    onNavigateHome: handleNavigateHome,
    onNavigateHistory: handleNavigateHistory,
    onOpenVideo: handleOpenVideo,
    historyTasks,
    onRemoveHistory: removeHistoryEntry,
  };

  const { isMobile } = useDevice();
  return <ToastProvider>{isMobile ? <MobileLayout {...layoutProps} /> : <DesktopLayout {...layoutProps} />}</ToastProvider>;
}
