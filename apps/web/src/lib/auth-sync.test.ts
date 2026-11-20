import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  AUTH_CHANNEL,
  LOCAL_SIGNOUT_STARTED,
  SIGNED_OUT_MESSAGE,
  broadcastSignOut,
  isSignOutMessage,
  notifyLocalSignOutStarted,
  subscribeToLocalSignOutStarted,
  subscribeToSignOut,
} from "./auth-sync.ts";

describe("M1 H3 cross-tab sign-out messages", () => {
  it("accepts only non-secret signout notifications", () => {
    assert.equal(AUTH_CHANNEL, "axiom:auth");
    assert.equal(isSignOutMessage(SIGNED_OUT_MESSAGE), true);
    for (const invalid of [
      null,
      undefined,
      "",
      "SIGNED_IN",
      { type: "signed-out" },
      { token: "secret" },
    ]) {
      assert.equal(isSignOutMessage(invalid), false);
    }
  });
  it("notifies only local workspace cleanup before the redirect", () => {
    assert.equal(LOCAL_SIGNOUT_STARTED, "axiom:auth:local-signout-started");
    const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
    Object.defineProperty(globalThis, "window", {
      configurable: true,
      value: new EventTarget(),
    });
    try {
      let notifications = 0;
      const stop = subscribeToLocalSignOutStarted(() => {
        notifications++;
      });
      notifyLocalSignOutStarted();
      assert.equal(notifications, 1);
      stop();
      notifyLocalSignOutStarted();
      assert.equal(notifications, 1);
    } finally {
      if (previous) Object.defineProperty(globalThis, "window", previous);
      else Reflect.deleteProperty(globalThis, "window");
    }
  });

  it("delivers to another tab without redirecting subscribers in the sending tab", async () => {
    // Separate module instances emulate separate browser-tab sender identities.
    const otherTab = (await import(
      new URL("./auth-sync.ts?different-tab", import.meta.url).href
    )) as typeof import("./auth-sync.ts");
    let sameTabNotifications = 0;
    const unsubscribeSender = subscribeToSignOut(() => {
      sameTabNotifications++;
    });
    try {
      await new Promise<void>((resolve, reject) => {
        let stop = () => {};
        const timeout = setTimeout(() => {
          stop();
          reject(new Error("Cross-tab logout notification was not delivered"));
        }, 3000);
        stop = otherTab.subscribeToSignOut(() => {
          clearTimeout(timeout);
          stop();
          resolve();
        });
        broadcastSignOut();
      });
      assert.equal(sameTabNotifications, 0);
    } finally {
      unsubscribeSender();
    }
  });

  it("delivers a cross-tab logout event without any credentials", async () => {
    const otherTab = (await import(
      new URL("./auth-sync.ts?another-tab", import.meta.url).href
    )) as typeof import("./auth-sync.ts");
    await new Promise<void>((resolve, reject) => {
      let stop = () => {};
      const timeout = setTimeout(() => {
        stop();
        reject(new Error("Cross-tab logout notification was not delivered"));
      }, 3000);
      stop = subscribeToSignOut(() => {
        clearTimeout(timeout);
        stop();
        resolve();
      });
      otherTab.broadcastSignOut();
    });
  });
});
