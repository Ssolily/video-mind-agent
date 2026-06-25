import React, { useState, useCallback, useRef, useEffect } from "react";
import { ToastContext, type ToastItem } from "./useToast";
import "./ToastProvider.css";

const MAX_TOASTS = 4;
const DEFAULT_DURATION_MS = 3000;

let idCounter = 0;
function nextId(): string { return "toast-" + (++idCounter); }

export default function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) { clearTimeout(timer); timersRef.current.delete(id); }
  }, []);

  const addToast = useCallback((type: ToastItem["type"], title: string, message?: string) => {
    const id = nextId();
    const item: ToastItem = { id, type, title, message };
    setToasts((prev) => {
      const next = [...prev, item];
      return next.length > MAX_TOASTS ? next.slice(next.length - MAX_TOASTS) : next;
    });
    const timer = setTimeout(() => removeToast(id), DEFAULT_DURATION_MS);
    timersRef.current.set(id, timer);
  }, [removeToast]);

  const clearAll = useCallback(() => {
    timersRef.current.forEach((t) => clearTimeout(t));
    timersRef.current.clear();
    setToasts([]);
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => { timersRef.current.forEach((t) => clearTimeout(t)); };
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast, clearAll }}>
      {children}
      <div className="toast-container" aria-live="polite" aria-relevant="additions">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={"toast toast--" + t.type}
            role={t.type === "error" ? "alert" : "status"}
          >
            <div className="toast__content">
              <span className="toast__title">{t.title}</span>
              {t.message && <span className="toast__message">{t.message}</span>}
            </div>
            <button className="toast__close" onClick={() => removeToast(t.id)} aria-label="关闭通知">&times;</button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
