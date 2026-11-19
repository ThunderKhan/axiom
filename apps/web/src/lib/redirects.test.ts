import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { loginDestination, safeReturnPath } from "./redirects.ts";

describe("M1 H1 fail-closed redirect allowlist", () => {
  it("keeps only the implemented, protected /app destination", () => {
    assert.equal(safeReturnPath("/app"), "/app");
    for (const value of [
      undefined,
      null,
      [],
      0,
      "",
      "/",
      "/login",
      "/app/other-workspace",
      "/app?workspace=foreign",
      "/app#stale",
      "//external.test/app",
      "https://external.test",
      "javascript:alert(1)",
      "/%2F%2Fevil.example",
      "/%5c%5cevil.example",
      "/app%0d%0aLocation:%20https://evil.example",
      "/app\\evil",
    ]) {
      assert.equal(safeReturnPath(value), "/app");
    }
  });
  it("never reflects untrusted login notices", () => {
    assert.equal(
      loginDestination("session-expired"),
      "/login?returnTo=%2Fapp&notice=session-expired",
    );
    assert.equal(
      loginDestination("https://external.test"),
      "/login?returnTo=%2Fapp",
    );
  });
});
