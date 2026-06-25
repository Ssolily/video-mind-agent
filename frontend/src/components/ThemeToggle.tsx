import React from "react";
import { useTheme } from "../hooks/useTheme";
import "./ThemeToggle.css";

export interface ThemeToggleProps {
  className?: string;
}

function ThemeToggle({ className }: ThemeToggleProps) {
  const { mode, resolved, setMode } = useTheme();

  const cycleMode = () => {
    const next: Record<string, "light" | "dark" | "system"> = {
      light: "dark",
      dark: "system",
      system: "light",
    };
    setMode(next[mode]);
  };

  const icon = mode === "system"
    ? (resolved === "dark" ? "🌙" : "☀️")
    : mode === "dark"
      ? "🌙"
      : "☀️";

  const label = mode === "system" ? "跟随系统" : mode === "dark" ? "暗色" : "亮色";

  return (
    <button
      className={"theme-toggle" + (className ? " " + className : "")}
      onClick={cycleMode}
      title={`当前: ${label} (${mode})`}
      aria-label={`切换主题，当前${label}模式`}
    >
      <span className="theme-toggle__icon">{icon}</span>
      <span className="theme-toggle__label">{label}</span>
    </button>
  );
}

export default ThemeToggle;
