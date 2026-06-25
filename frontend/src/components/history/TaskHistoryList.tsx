import React from "react";
import type { TaskHistoryEntry } from "../../utils/taskHistory";
import TaskHistoryItem from "./TaskHistoryItem";
import "./TaskHistoryList.css";

interface TaskHistoryListProps {
  tasks: TaskHistoryEntry[];
  loading?: boolean;
  error?: string | null;
  emptyMessage?: string;
  emptyAction?: React.ReactNode;
  onOpen?: (entry: TaskHistoryEntry) => void;
  onRetry?: (entry: TaskHistoryEntry) => void;
  onRemove?: (entry: TaskHistoryEntry) => void;
}

export default function TaskHistoryList({
  tasks,
  loading = false,
  error = null,
  emptyMessage = "暂无历史记录",
  emptyAction,
  onOpen,
  onRetry,
  onRemove,
}: TaskHistoryListProps) {
  if (loading) {
    return (
      <div className="history-list history-list--loading">
        <div className="history-list__spinner" />
        <span className="history-list__loading-text">加载中...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="history-list history-list--error">
        <span className="history-list__error-icon">⚠️</span>
        <span className="history-list__error-text">{error}</span>
      </div>
    );
  }

  if (tasks.length === 0) {
    return (
      <div className="history-list history-list--empty">
        <span className="history-list__empty-icon">📋</span>
        <p className="history-list__empty-text">{emptyMessage}</p>
        {emptyAction && <div className="history-list__empty-action">{emptyAction}</div>}
      </div>
    );
  }

  return (
    <div className="history-list">
      {tasks.map((task) => (
        <TaskHistoryItem
          key={task.videoId}
          entry={task}
          onOpen={onOpen || (() => {})}
          onRemove={onRemove || (() => {})}
          onRetry={onRetry}
        />
      ))}
    </div>
  );
}
