import React, { useState, useMemo } from "react";
import type { TaskHistoryEntry, FilterOptions } from "../../utils/taskHistory";
import { filterTaskHistory } from "../../utils/taskHistory";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useToast } from "../toast/useToast";
import TaskFilters from "./TaskFilters";
import TaskHistoryList from "./TaskHistoryList";
import ConfirmDialog from "../ConfirmDialog";
import "./TaskHistoryPage.css";

interface TaskHistoryPageProps {
  tasks: TaskHistoryEntry[];
  onOpen?: (entry: TaskHistoryEntry) => void;
  onRetry?: (entry: TaskHistoryEntry) => void;
  onRemove?: (entry: TaskHistoryEntry) => void;
  onClearAll?: () => void;
  onBack?: () => void;
  onUpload?: () => void;
}

export default function TaskHistoryPage({
  tasks,
  onOpen,
  onRetry,
  onRemove,
  onClearAll,
  onBack,
  onUpload,
}: TaskHistoryPageProps) {
  const { addToast } = useToast();
  const [filters, setFilters] = useState<FilterOptions>({ status: "all", search: "", sort: "newest" });
  const [confirmOpen, setConfirmOpen] = useState(false);

  // Debounce search by 250ms
  const debouncedSearch = useDebouncedValue(filters.search, 250);

  const debouncedFilters: FilterOptions = useMemo(
    () => ({ ...filters, search: debouncedSearch }),
    [filters, debouncedSearch]
  );

  const filteredTasks = useMemo(
    () => filterTaskHistory(tasks, debouncedFilters),
    [tasks, debouncedFilters]
  );

  const handleChange = (opts: FilterOptions) => setFilters(opts);

  const handleClearAll = () => {
    onClearAll?.();
    setConfirmOpen(false);
    addToast("info", "本地历史已清空", "不会删除服务器上的视频或分析结果。");
  };

  return (
    <div className="history-page">
      <header className="history-page__header">
        {onBack && (
          <button className="history-page__back-btn" onClick={onBack}>
            ← 返回
          </button>
        )}
        <h1 className="history-page__title">任务历史</h1>
        <div className="history-page__header-actions">
          {tasks.length > 0 && (
            <button
              className="history-page__clear-btn"
              onClick={() => setConfirmOpen(true)}
              title="清空本地历史记录（不会删除服务器文件）"
            >
              清空本地历史
            </button>
          )}
          <span className="history-page__count">{tasks.length} 个任务</span>
        </div>
      </header>

      <TaskFilters options={filters} onChange={handleChange} />

      <TaskHistoryList
        tasks={filteredTasks}
        emptyMessage={filters.search || filters.status !== "all" ? "没有匹配的任务" : "还没有分析过视频"}
        emptyAction={
          onUpload ? (
            <button className="history-page__upload-btn" onClick={onUpload}>
              上传视频开始分析
            </button>
          ) : undefined
        }
        onOpen={onOpen}
        onRetry={onRetry}
        onRemove={(entry) => {
          onRemove?.(entry);
          addToast("info", "已从本地历史移除", entry.filename);
        }}
      />

      <ConfirmDialog
        open={confirmOpen}
        title="清空本地历史"
        message="确定要清空所有本地历史记录吗？此操作不会删除服务器上的视频或分析结果，仅清除浏览器本地记录。"
        confirmLabel="清空"
        cancelLabel="取消"
        variant="warning"
        onConfirm={handleClearAll}
        onCancel={() => setConfirmOpen(false)}
      />
    </div>
  );
}
