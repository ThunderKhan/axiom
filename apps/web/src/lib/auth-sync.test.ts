import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { AUTH_CHANNEL, SIGNED_OUT_MESSAGE, isSignOutMessage } from "./auth-sync.ts";

describe("M1 H3 cross-tab sign-out messages", () => {
  it("accepts only non-secret signout notifications", () => {
    assert.equal(AUTH_CHANNEL, "axiom:auth");
    assert.equal(isSignOutMessage(SIGNED_OUT_MESSAGE), true);
    for (const invalid of [null, undefined, "", "SIGNED_IN", { type: "signed-out" }, { token: "secret" }]) {
      assert.equal(isSignOutMessage(invalid), false);
    }
  });
});
