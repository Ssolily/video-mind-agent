// ── Tests for EmptyState ──────────────────────────

import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import EmptyState from "./EmptyState";

describe("EmptyState", () => {
  it("renders title", () => {
    render(<EmptyState title="测试标题" />);
    expect(screen.getByText("测试标题")).toBeTruthy();
  });

  it("renders description", () => {
    render(<EmptyState title="Test" description="描述文本" />);
    expect(screen.getByText("描述文本")).toBeTruthy();
  });

  it("renders custom icon", () => {
    render(<EmptyState icon="🎥" title="Test" />);
    expect(screen.getByText("🎥")).toBeTruthy();
  });

  it("renders action node", () => {
    render(<EmptyState title="Test" action={<button>Action</button>} />);
    expect(screen.getByText("Action")).toBeTruthy();
  });
});
