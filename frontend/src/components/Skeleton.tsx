import React from "react";
import "./Skeleton.css";

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  rounded?: boolean;
  variant?: "text" | "circle" | "rect";
  lines?: number;
  className?: string;
}

export default function Skeleton({
  width, height, rounded = false, variant = "rect", lines, className,
}: SkeletonProps) {
  if (variant === "text" && lines && lines > 1) {
    return (
      <div className={"skeleton skeleton--text-block" + (className ? " " + className : "")} aria-hidden="true">
        {Array.from({ length: lines }, (_, i) => (
          <div
            key={i}
            className="skeleton skeleton--text"
            style={{ width: i === lines - 1 ? "60%" : "100%", height: "1em", marginBottom: "0.5em" }}
          />
        ))}
      </div>
    );
  }

  const cls = "skeleton"
    + (variant === "circle" ? " skeleton--circle" : variant === "text" ? " skeleton--text" : " skeleton--rect")
    + (rounded ? " skeleton--rounded" : "")
    + (className ? " " + className : "");

  return <div className={cls} style={{ width, height }} aria-hidden="true" />;
}
