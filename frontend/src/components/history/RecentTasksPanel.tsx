import React from "react";
import type { TaskHistoryEntry } from "../../utils/taskHistory";
import "./RecentTasksPanel.css";

export interface RecentTasksPanelProps {
  tasks: TaskHistoryEntry[];
  onOpen: (entry: TaskHistoryEntry) => void;
  onViewAll: () => void;
}

export default function RecentTasksPanel({ tasks, onOpen, onViewAll }: RecentTasksPanelProps) {
  const recent = tasks.slice(0, 5);
  return (
    <div className="recent-tasks">
      <div className="recent-tasks__header">
        <h3 className="recent-tasks__title">最近任务</h3>
        {tasks.length > 0 && <button className="recent-tasks__view-all" onClick={onViewAll}>查看全部 ({tasks.length})</button>}
      </div>
      {recent.length === 0 ? (
        <p className="recent-tasks__empty">暂无历史任务，上传视频后历史将显示在此处。</p>
      ) : (
        <div className="recent-tasks__list">
          {recent.map((e) => (
            <button key={e.videoId} className="recent-tasks__item" onClick={() => onOpen(e)}>
              <span className="recent-tasks__name">{e.filename}</span>
              <span className="recent-tasks__status" data-status={e.status}>{e.status}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
