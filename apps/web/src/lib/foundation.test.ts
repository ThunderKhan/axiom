import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { capabilities, statusLabel } from "./foundation.ts";

describe("public foundation capability contract", () => {
  it("truthfully exposes only the working frontend as available", () => {
    const available = capabilities.filter((item) => item.state === "available");
    assert.deepEqual(
      available.map((item) => item.id),
      ["foundation"],
    );
    assert.equal(
      capabilities.find((item) => item.id === "authentication")?.state,
      "unavailable",
    );
    assert.equal(
      capabilities.find((item) => item.id === "research")?.state,
      "unavailable",
    );
  });

  it("provides distinct, accessible status text for each state", () => {
    assert.equal(statusLabel("available"), "Available");
    assert.equal(statusLabel("unavailable"), "Not yet available");
  });

  it("keeps every capability uniquely identified for stable rendering", () => {
    assert.equal(
      new Set(capabilities.map((item) => item.id)).size,
      capabilities.length,
    );
  });
});
