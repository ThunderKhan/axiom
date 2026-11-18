import { describe, expect, it } from "vitest";
import { capabilities, statusLabel } from "./foundation";

describe("public foundation capability contract", () => {
  it("truthfully exposes only the working frontend as available", () => {
    const available = capabilities.filter((item) => item.state === "available");
    expect(available.map((item) => item.id)).toEqual(["foundation"]);
    expect(capabilities.find((item) => item.id === "authentication")?.state).toBe(
      "unavailable",
    );
    expect(capabilities.find((item) => item.id === "research")?.state).toBe(
      "unavailable",
    );
  });

  it("provides distinct, accessible status text for available and unavailable states", () => {
    expect(statusLabel("available")).toBe("Available");
    expect(statusLabel("unavailable")).toBe("Not yet available");
  });

  it("keeps every capability uniquely identified for stable rendering", () => {
    expect(new Set(capabilities.map((item) => item.id)).size).toBe(
      capabilities.length,
    );
  });
});
