import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ConfirmDialog from "./ConfirmDialog";

describe("ConfirmDialog", () => {
  it("does not render when open=false", () => {
    const { container } = render(<ConfirmDialog open={false} title="test" message="msg" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(container.querySelector(".confirm-dialog")).toBeNull();
  });

  it("renders when open=true", () => {
    render(<ConfirmDialog open={true} title="确认删除" message="确定要删除吗？" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    expect(screen.getByText("确认删除")).toBeDefined();
    expect(screen.getByText("确定要删除吗？")).toBeDefined();
  });

  it("has role=dialog and aria-modal=true", () => {
    render(<ConfirmDialog open={true} title="test" message="msg" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    const dialog = screen.getByRole("dialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
  });

  it("calls onCancel when overlay clicked", () => {
    const onCancel = vi.fn();
    render(<ConfirmDialog open={true} title="test" message="msg" onConfirm={vi.fn()} onCancel={onCancel} />);
    fireEvent.click(screen.getByRole("dialog"));
    expect(onCancel).toHaveBeenCalled();
  });

  it("calls onCancel when cancel button clicked", () => {
    const onCancel = vi.fn();
    render(<ConfirmDialog open={true} title="test" message="msg" onConfirm={vi.fn()} onCancel={onCancel} />);
    fireEvent.click(screen.getByText("取消"));
    expect(onCancel).toHaveBeenCalled();
  });

  it("calls onConfirm when confirm button clicked", () => {
    const onConfirm = vi.fn();
    render(<ConfirmDialog open={true} title="test" message="msg" onConfirm={onConfirm} onCancel={vi.fn()} />);
    fireEvent.click(screen.getByText("确认"));
    expect(onConfirm).toHaveBeenCalled();
  });

  it("renders with danger variant", () => {
    render(<ConfirmDialog open={true} title="test" message="msg" variant="danger" onConfirm={vi.fn()} onCancel={vi.fn()} />);
    const dialog = screen.getByRole("dialog");
    expect(dialog.querySelector(".confirm-dialog--danger")).toBeTruthy();
  });
});
