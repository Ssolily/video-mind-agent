import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import Skeleton from "./Skeleton";

describe("Skeleton", () => {
  it("renders rect variant by default", () => {
    const { container } = render(<Skeleton width={100} height={20} />);
    const el = container.querySelector(".skeleton");
    expect(el).toBeTruthy();
    expect(el?.className).toContain("skeleton--rect");
  });

  it("renders circle variant", () => {
    const { container } = render(<Skeleton variant="circle" width={40} height={40} />);
    const el = container.querySelector(".skeleton");
    expect(el?.className).toContain("skeleton--circle");
  });

  it("renders text variant", () => {
    const { container } = render(<Skeleton variant="text" width="100%" />);
    const el = container.querySelector(".skeleton");
    expect(el?.className).toContain("skeleton--text");
  });

  it("renders multiple text lines", () => {
    const { container } = render(<Skeleton variant="text" lines={3} />);
    const skeletons = container.querySelectorAll(".skeleton--text");
    expect(skeletons.length).toBe(3);
  });

  it("applies rounded class", () => {
    const { container } = render(<Skeleton width={100} height={20} rounded />);
    const el = container.querySelector(".skeleton");
    expect(el?.className).toContain("skeleton--rounded");
  });

  it("has aria-hidden", () => {
    const { container } = render(<Skeleton width={100} height={20} />);
    expect(container.querySelector(".skeleton")?.getAttribute("aria-hidden")).toBe("true");
  });
});
