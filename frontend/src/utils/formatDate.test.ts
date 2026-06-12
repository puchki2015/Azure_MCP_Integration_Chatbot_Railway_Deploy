import { describe, expect, it } from "vitest";
import { formatDate } from "./formatDate";

describe("formatDate", () => {
  it("formats a date string", () => {
    expect(formatDate("2025-01-01T00:00:00Z")).toContain("2025");
  });
});
