// ── TechnicalInfoPanel ────────────────────────────
// Shows raw JSON result, steps, warnings for tech-savvy users.

import React, { useCallback, useState } from "react";
import type { VideoResult } from "../../types/video";
import "./TechnicalInfoPanel.css";

export interface TechnicalInfoPanelProps {
  data: VideoResult;
  className?: string;
}

function TechnicalInfoPanel({ data, className }: TechnicalInfoPanelProps) {
  const [copied, setCopied] = useState(false);

  const handleCopyJson = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  }, [data]);

  const steps = (data as any).steps;

  return (
    <details className={"technical-info-panel" + (className ? " " + className : "")}>
      <summary className="technical-info-panel__summary">🔧 技术信息</summary>
      <div className="technical-info-panel__body">
        {Array.isArray(steps) && steps.length > 0 && (
          <div className="technical-info-panel__section">
            <h4 className="technical-info-panel__section-title">分析步骤</h4>
            <div className="technical-info-panel__steps">
              {steps.map((s: any, i: number) => (
                <div key={i} className={"technical-info-panel__step technical-info-panel__step--" + (s.status || "unknown")}>
                  <span className="technical-info-panel__step-icon">
                    {s.status === "ok" ? "✅" : s.status === "error" ? "❌" : "⬜"}
                  </span>
                  <span className="technical-info-panel__step-name">{s.step || s.detail || `Step ${i + 1}`}</span>
                  {s.detail && <span className="technical-info-panel__step-detail">{s.detail}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {data.warnings.length > 0 && (
          <div className="technical-info-panel__section">
            <h4 className="technical-info-panel__section-title">警告</h4>
            <ul className="technical-info-panel__warnings">
              {data.warnings.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          </div>
        )}

        <div className="technical-info-panel__section">
          <h4 className="technical-info-panel__section-title">原始结果 (JSON)</h4>
          <button className="technical-info-panel__copy-btn" onClick={handleCopyJson}>
            {copied ? "✅ 已复制" : "📋 复制 JSON"}
          </button>
          <pre className="technical-info-panel__json">
            {JSON.stringify(data, null, 2).slice(0, 3000)}
            {JSON.stringify(data, null, 2).length > 3000 ? "\n...(truncated)" : ""}
          </pre>
        </div>
      </div>
    </details>
  );
}

export default TechnicalInfoPanel;
