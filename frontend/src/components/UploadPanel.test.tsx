// ── Tests for UploadPanel ──────────────────────────

import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import UploadPanel from "./UploadPanel";

describe("UploadPanel", () => {
  it("shows format hint", () => {
    render(<UploadPanel file={null} setFile={() => {}} disabled={false} uploading={false} />);
    expect(screen.getByText(/mp4/)).toBeTruthy();
    expect(screen.getByText(/mov/)).toBeTruthy();
    expect(screen.getByText(/avi/)).toBeTruthy();
  });

  it("shows file info when file selected", () => {
    const file = new File([""], "test.mp4", { type: "video/mp4" });
    Object.defineProperty(file, "size", { value: 1024 * 1024 });
    render(<UploadPanel file={file} setFile={() => {}} disabled={false} uploading={false} />);
    expect(screen.getByText("test.mp4")).toBeTruthy();
    expect(screen.getByText(/MP4/)).toBeTruthy();
  });

  it("shows uploading state", () => {
    render(<UploadPanel file={null} setFile={() => {}} disabled={true} uploading={true} />);
    expect(screen.getByText("正在上传...")).toBeTruthy();
  });

  it("has remove button when file selected", () => {
    const file = new File([""], "test.mp4", { type: "video/mp4" });
    render(<UploadPanel file={file} setFile={() => {}} disabled={false} uploading={false} />);
    const removeBtn = document.querySelector(".upload-panel__remove-btn");
    expect(removeBtn).toBeTruthy();
  });
});
