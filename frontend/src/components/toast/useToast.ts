import { createContext, useContext } from "react";

export interface ToastItem {
  id: string;
  type: "success" | "error" | "warning" | "info";
  title: string;
  message?: string;
}

export interface ToastContextValue {
  toasts: ToastItem[];
  addToast: (type: ToastItem["type"], title: string, message?: string) => void;
  removeToast: (id: string) => void;
  clearAll: () => void;
}

export const ToastContext = createContext<ToastContextValue>({
  toasts: [],
  addToast: () => {},
  removeToast: () => {},
  clearAll: () => {},
});

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  return ctx;
}
