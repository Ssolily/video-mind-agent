import { useState, useCallback, useEffect } from "react";
import type { TaskHistoryEntry } from "../utils/taskHistory";
import { loadTaskHistory, saveTaskHistory, mergeTaskHistory, removeFromHistory } from "../utils/taskHistory";

export interface UseTaskHistoryReturn {
  tasks: TaskHistoryEntry[];
  addEntry: (entry: TaskHistoryEntry) => void;
  removeEntry: (videoId: string) => void;
  refresh: () => void;
}

export function useTaskHistory(): UseTaskHistoryReturn {
  const [tasks, setTasks] = useState<TaskHistoryEntry[]>(() => loadTaskHistory());

  const addEntry = useCallback((entry: TaskHistoryEntry) => {
    setTasks((prev) => {
      const updated = mergeTaskHistory(prev, entry);
      saveTaskHistory(updated);
      return updated;
    });
  }, []);

  const removeEntry = useCallback((videoId: string) => {
    setTasks((prev) => {
      const updated = removeFromHistory(prev, videoId);
      saveTaskHistory(updated);
      return updated;
    });
  }, []);

  const refresh = useCallback(() => {
    setTasks(loadTaskHistory());
  }, []);

  return { tasks, addEntry, removeEntry, refresh };
}
