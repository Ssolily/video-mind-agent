import { describe, it, expect } from "vitest";
import { formatTimestamp, formatDuration } from "./time";

describe("formatTimestamp", () => {
  it('formats 0 as "00:00.000"', () => {
    expect(formatTimestamp(0)).toBe("00:00.000");
  });

  it('formats 5.2 as "00:05.200"', () => {
    expect(formatTimestamp(5.2)).toBe("00:05.200");
  });

  it('formats 42.5 as "00:42.500"', () => {
    expect(formatTimestamp(42.5)).toBe("00:42.500");
  });

  it('formats 61.2 as "01:01.200"', () => {
    expect(formatTimestamp(61.2)).toBe("01:01.200");
  });

  it('formats 3661.25 as "01:01:01.250"', () => {
    expect(formatTimestamp(3661.25)).toBe("01:01:01.250");
  });

  it("handles NaN as 0", () => {
    expect(formatTimestamp(NaN)).toBe("00:00.000");
  });

  it("handles Infinity as 0", () => {
    expect(formatTimestamp(Infinity)).toBe("00:00.000");
  });

  it("handles negative as 0", () => {
    expect(formatTimestamp(-5)).toBe("00:00.000");
  });

  it("rounds milliseconds stably", () => {
    expect(formatTimestamp(1.2345)).toBe("00:01.235");
  });

  it("does not produce 60 seconds", () => {
    // 59.999 seconds is 59.999s, not 60s
    expect(formatTimestamp(59.999)).toBe("00:59.999");
  });

  it("formats exactly 3600 as 01:00:00.000", () => {
    expect(formatTimestamp(3600)).toBe("01:00:00.000");
  });

  it("formats 86399.999 seconds correctly", () => {
    expect(formatTimestamp(86399.999)).toBe("23:59:59.999");
  });
});

describe("formatDuration", () => {
  it('formats 0 as "0.0s"', () => {
    expect(formatDuration(0)).toBe("0.0s");
  });

  it('formats 18.7 as "18.7s"', () => {
    expect(formatDuration(18.7)).toBe("18.7s");
  });

  it('formats 60 as "01:00.000"', () => {
    expect(formatDuration(60)).toBe("01:00.000");
  });

  it("handles NaN", () => {
    expect(formatDuration(NaN)).toBe("0.0s");
  });

  it("handles Infinity", () => {
    expect(formatDuration(Infinity)).toBe("0.0s");
  });

  it("handles negative", () => {
    expect(formatDuration(-10)).toBe("0.0s");
  });
});
