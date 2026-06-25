import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import ToastProvider from "./ToastProvider";
import { useToast } from "./useToast";
import React from "react";

// TestHarness only triggers addToast, does NOT duplicate the toast DOM
function TestHarness() {
  const { addToast, toasts, clearAll } = useToast();
  return (
    <div>
      <button onClick={() => addToast("success", "成功", "操作成功")}>add-success</button>
      <button onClick={() => addToast("error", "失败", "操作失败")}>add-error</button>
      <button onClick={() => addToast("warning", "警告")}>add-warning</button>
      <button onClick={() => addToast("info", "信息")}>add-info</button>
      <button onClick={() => clearAll()}>clear-all</button>
      <span data-testid="count">{toasts.length}</span>
    </div>
  );
}

describe("ToastProvider", () => {
  it("renders children", () => {
    render(<ToastProvider><div>child</div></ToastProvider>);
    expect(screen.getByText("child")).toBeDefined();
  });

  it("shows success toast via toast-container", () => {
    render(<ToastProvider><TestHarness /></ToastProvider>);
    fireEvent.click(screen.getByText("add-success"));
    expect(screen.getByText("成功")).toBeDefined();
  });

  it("shows success with message", () => {
    render(<ToastProvider><TestHarness /></ToastProvider>);
    fireEvent.click(screen.getByText("add-success"));
    expect(screen.getByText("操作成功")).toBeDefined();
  });

  it("shows error toast", () => {
    render(<ToastProvider><TestHarness /></ToastProvider>);
    fireEvent.click(screen.getByText("add-error"));
    expect(screen.getByText("失败")).toBeDefined();
  });

  it("shows warning toast", () => {
    render(<ToastProvider><TestHarness /></ToastProvider>);
    fireEvent.click(screen.getByText("add-warning"));
    expect(screen.getByText("警告")).toBeDefined();
  });

  it("shows info toast", () => {
    render(<ToastProvider><TestHarness /></ToastProvider>);
    fireEvent.click(screen.getByText("add-info"));
    expect(screen.getByText("信息")).toBeDefined();
  });

  it("has role=alert for error toasts", () => {
    render(<ToastProvider><TestHarness /></ToastProvider>);
    fireEvent.click(screen.getByText("add-error"));
    const alerts = document.querySelectorAll('[role="alert"]');
    expect(alerts.length).toBeGreaterThanOrEqual(1);
  });

  it("has role=status for non-error toasts", () => {
    render(<ToastProvider><TestHarness /></ToastProvider>);
    fireEvent.click(screen.getByText("add-success"));
    const statuses = document.querySelectorAll('[role="status"]');
    expect(statuses.length).toBeGreaterThanOrEqual(1);
  });

  it("manually closes toast", () => {
    render(<ToastProvider><TestHarness /></ToastProvider>);
    fireEvent.click(screen.getByText("add-success"));
    const closeBtn = document.querySelector(".toast__close") as HTMLButtonElement;
    expect(closeBtn).toBeTruthy();
    fireEvent.click(closeBtn);
    expect(document.querySelector(".toast")).toBeNull();
  });

  it("limits to max 4 toasts", () => {
    render(<ToastProvider><TestHarness /></ToastProvider>);
    for (let i = 0; i < 6; i++) {
      fireEvent.click(screen.getByText("add-info"));
    }
    const toasts = document.querySelectorAll(".toast");
    expect(toasts.length).toBeLessThanOrEqual(4);
  });

  it("clearAll removes all toasts", () => {
    render(<ToastProvider><TestHarness /></ToastProvider>);
    fireEvent.click(screen.getByText("add-success"));
    fireEvent.click(screen.getByText("add-error"));
    expect(screen.queryByText("成功")).toBeTruthy();
    expect(screen.queryByText("失败")).toBeTruthy();
    fireEvent.click(screen.getByText("clear-all"));
    expect(document.querySelectorAll(".toast").length).toBe(0);
  });
});
