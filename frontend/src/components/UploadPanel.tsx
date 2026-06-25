// ── UploadPanel ────────────────────────────────────
// Enhanced upload panel with drag-drop, format hints, file info, upload state.

import React, { useState, useCallback, useRef } from "react";
import { useToast } from "./toast/useToast";
import "./UploadPanel.css";

const ACCEPTED_FORMATS = [".mp4", ".mov", ".avi"];
const ACCEPTED_STRING = ACCEPTED_FORMATS.join(",");
const MAX_SIZE_MB = 1024;
const FORMAT_HINT = `支持 ${ACCEPTED_FORMATS.join("、")} 格式，最大 ${MAX_SIZE_MB} MB`;

export interface UploadPanelProps {
  file: File | null;
  setFile: (f: File | null) => void;
  disabled: boolean;
  uploading: boolean;
}

function UploadPanel({ file, setFile, disabled, uploading }: UploadPanelProps) {
  const { addToast } = useToast();
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((f: File) => {
    const ext = "." + f.name.split(".").pop()?.toLowerCase();
    if (!ACCEPTED_FORMATS.includes(ext)) {
      addToast("error", "文件格式不支持", "支持的格式：" + ACCEPTED_FORMATS.join(", "));
      return;
    }
    if (f.size > 1024 * 1024 * 1024) {
      addToast("warning", "文件较大", "超过 1GB 的视频可能需要较长时间处理");
    }
    setFile(f);
  }, [setFile, addToast]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setDragOver(false);
  }, []);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) handleFile(f);
  }, [handleFile]);

  const handleRemove = useCallback(() => {
    setFile(null);
    if (inputRef.current) inputRef.current.value = "";
  }, [setFile]);

  const formatSize = (bytes: number): string => {
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + " MB";
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + " GB";
  };

  const dropZoneClass =
    "upload-panel__dropzone" +
    (dragOver ? " upload-panel__dropzone--dragover" : "") +
    (disabled ? " upload-panel__dropzone--disabled" : "");

  return (
    <div className="upload-panel">
      <div
        className={dropZoneClass}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => !disabled && inputRef.current?.click()}
      >
        {uploading ? (
          <div className="upload-panel__uploading">
            <div className="upload-panel__spinner" />
            <span>正在上传...</span>
          </div>
        ) : file ? (
          <div className="upload-panel__file-info" onClick={(e) => e.stopPropagation()}>
            <div className="upload-panel__file-icon">🎬</div>
            <div className="upload-panel__file-details">
              <div className="upload-panel__file-name">{file.name}</div>
              <div className="upload-panel__file-meta">
                {formatSize(file.size)} · {file.name.split(".").pop()?.toUpperCase()}
              </div>
            </div>
            <button
              className="upload-panel__remove-btn"
              onClick={handleRemove}
              disabled={disabled}
              title="移除文件"
            >
              ✕
            </button>
          </div>
        ) : (
          <div className="upload-panel__placeholder">
            <div className="upload-panel__icon">📁</div>
            <div className="upload-panel__text">
              <strong>点击选择</strong> 或将视频文件拖拽到此处
            </div>
            <div className="upload-panel__hint">{FORMAT_HINT}</div>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_STRING}
          onChange={handleChange}
          disabled={disabled}
          style={{ display: "none" }}
        />
      </div>
    </div>
  );
}

export default UploadPanel;
