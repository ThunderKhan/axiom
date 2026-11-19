import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { authCookieOptions } from "./cookie-policy.ts";

describe("M1 C1 cookie policy", () => {
  it("marks production session cookies Secure with Lax and root path", () => {
    assert.deepEqual(authCookieOptions(true), { secure: true, sameSite: "lax", path: "/" });
  });
  it("keeps local development HTTP compatible", () => {
    assert.deepEqual(authCookieOptions(false), { secure: false, sameSite: "lax", path: "/" });
  });
});
