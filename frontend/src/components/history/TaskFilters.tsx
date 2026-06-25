import React from "react";
import type { SortMode, FilterOptions } from "../../utils/taskHistory";
import "./TaskFilters.css";

export interface TaskFiltersProps {
  options: FilterOptions;
  onChange: (options: FilterOptions) => void;
}

const STATUSES = ["all", "queued", "running", "completed", "failed", "cancelled"];
const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: "newest", label: "\u6700\u65b0" }, { value: "oldest", label: "\u6700\u65e9" },
  { value: "highest_score", label: "\u5f97\u5206" }, { value: "most_highlights", label: "\u7cbe\u5f69\u6570" },
  { value: "longest_duration", label: "\u65f6\u957f" },
];

const STATUS_LABEL: Record<string, string> = { all: "\u5168\u90e8", queued: "\u6392\u961f\u4e2d", running: "\u5206\u6790\u4e2d", completed: "\u5df2\u5b8c\u6210", failed: "\u5931\u8d25", cancelled: "\u5df2\u53d6\u6d88" };

export default function TaskFilters({ options, onChange }: TaskFiltersProps) {
  return (
    <div className="task-filters">
      <input className="task-filters__search" type="text" placeholder="\u641c\u7d22\u6587\u4ef6\u540d\u6216 ID..." value={options.search}
        onChange={(e) => onChange({ ...options, search: e.target.value })} />
      <div className="task-filters__statuses">
        {STATUSES.map((s) => (
          <button key={s} className={"task-filters__status-btn" + (options.status === s ? " task-filters__status-btn--active" : "")}
            onClick={() => onChange({ ...options, status: s })}
            aria-pressed={options.status === s}>{STATUS_LABEL[s] || s}</button>
        ))}
      </div>
      <select className="task-filters__sort" value={options.sort} onChange={(e) => onChange({ ...options, sort: e.target.value as SortMode })}
          aria-label="排序方式">
        {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </div>
  );
}
