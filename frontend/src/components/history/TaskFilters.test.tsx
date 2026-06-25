import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import TaskFilters from "./TaskFilters";
import type { FilterOptions } from "../../utils/taskHistory";

const baseOptions: FilterOptions = { status: "all", search: "", sort: "newest" };

describe("TaskFilters", () => {
  it("renders search input", () => {
    render(<TaskFilters options={baseOptions} onChange={vi.fn()} />);
    const input = document.querySelector(".task-filters__search");
    expect(input).toBeTruthy();
  });

  it("calls onChange on search input", () => {
    const onChange = vi.fn();
    render(<TaskFilters options={baseOptions} onChange={onChange} />);
    const input = document.querySelector(".task-filters__search") as HTMLInputElement;
    expect(input).toBeTruthy();
    fireEvent.change(input, { target: { value: "test" } });
    expect(onChange).toHaveBeenCalledWith({ ...baseOptions, search: "test" });
  });

  it("renders status filter buttons", () => {
    render(<TaskFilters options={baseOptions} onChange={vi.fn()} />);
    expect(screen.getByText("全部")).toBeDefined();
    expect(screen.getByText("已完成")).toBeDefined();
  });

  it("highlights active status button", () => {
    render(<TaskFilters options={{ ...baseOptions, status: "completed" }} onChange={vi.fn()} />);
    const btn = screen.getByText("已完成");
    expect(btn.className).toContain("task-filters__status-btn--active");
  });

  it("calls onChange when status button clicked", () => {
    const onChange = vi.fn();
    render(<TaskFilters options={baseOptions} onChange={onChange} />);
    fireEvent.click(screen.getByText("已完成"));
    expect(onChange).toHaveBeenCalledWith({ ...baseOptions, status: "completed" });
  });

  it("renders sort dropdown", () => {
    render(<TaskFilters options={baseOptions} onChange={vi.fn()} />);
    expect(screen.getByText("最新")).toBeDefined();
  });
});
