// ── EmptyState ─────────────────────────────────────
// Reusable empty state component for consistent UI.

import React from "react";
import "./EmptyState.css";

export interface EmptyStateProps {
  icon?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

function EmptyState({ icon = "📭", title, description, action, className }: EmptyStateProps) {
  return (
    <div className={"empty-state" + (className ? " " + className : "")}>
      <div className="empty-state__icon">{icon}</div>
      <div className="empty-state__title">{title}</div>
      {description && <div className="empty-state__description">{description}</div>}
      {action && <div className="empty-state__action">{action}</div>}
    </div>
  );
}

export default EmptyState;
