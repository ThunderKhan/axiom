import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  AUTH_CHANNEL,
  LOCAL_SIGNOUT_STARTED,
  SIGNED_OUT_MESSAGE,
  SIGNOUT_MARKER_KEY,
  broadcastSignOut,
  isSignOutMessage,
  notifyLocalSignOutStarted,
  resetLocalSignOutStarted,
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
    let otherTabNotifications = 0;
    let unsubscribeOther = () => {};
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
          otherTabNotifications++;
          clearTimeout(timeout);
          resolve();
        });
        unsubscribeOther = stop;
        broadcastSignOut();
      });
      // Let the second (legacy) message be processed before checking duplicates.
      await new Promise((resolve) => setTimeout(resolve, 30));
      assert.equal(otherTabNotifications, 1);
      assert.equal(sameTabNotifications, 0);
    } finally {
      unsubscribeOther();
      unsubscribeSender();
    }
  });

  it("notifies legacy tabs with the original string while suppressing self-redirect", async () => {
    // Legacy tabs only recognize the literal string, not the tagged envelope.
    const legacyTab = new BroadcastChannel(AUTH_CHANNEL);
    let ownTabNotifications = 0;
    const stopOwn = subscribeToSignOut(() => {
      ownTabNotifications++;
    });
    try {
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(
          () => reject(new Error("Legacy tab missed sign-out notification")),
          3000,
        );
        legacyTab.onmessage = (event: MessageEvent<unknown>) => {
          if (!isSignOutMessage(event.data)) return;
          clearTimeout(timeout);
          resolve();
        };
        broadcastSignOut();
      });
      assert.equal(ownTabNotifications, 0);
    } finally {
      legacyTab.close();
      stopOwn();
    }
  });

  it("accepts legacy sign-out strings from older tabs in a new tab", async () => {
    // Give the modern receiver its own module state and sender identity.
    const modernTab = (await import(
      new URL("./auth-sync.ts?legacy-receiver", import.meta.url).href
    )) as typeof import("./auth-sync.ts");
    const legacyTab = new BroadcastChannel(AUTH_CHANNEL);
    let stop = () => {};
    try {
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => {
          stop();
          reject(new Error("Modern tab missed legacy sign-out notification"));
        }, 3000);
        stop = modernTab.subscribeToSignOut(() => {
          clearTimeout(timeout);
          resolve();
        });
        legacyTab.postMessage(SIGNED_OUT_MESSAGE);
      });
    } finally {
      stop();
      legacyTab.close();
    }
  });

  it("re-enables legacy logout handling when login is visited again", async () => {
    // In the app the login form resets a module retained by soft navigation.
    const legacyTab = new BroadcastChannel(AUTH_CHANNEL);
    let notices = 0;
    const stop = subscribeToSignOut(() => {
      notices++;
    });
    let reconnect = () => {};
    try {
      broadcastSignOut(); // This tab is signing out; ignore its own string.
      await new Promise((resolve) => setTimeout(resolve, 30));
      assert.equal(notices, 0);
      resetLocalSignOutStarted(); // LoginForm mounts before the next login.
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(
          () => reject(new Error("Legacy logout was not restored after login")),
          3000,
        );
        // The existing subscription must still receive subsequent sign-outs.
        reconnect = subscribeToSignOut(() => {
          clearTimeout(timeout);
          reconnect();
          resolve();
        });
        legacyTab.postMessage(SIGNED_OUT_MESSAGE);
      });
    } finally {
      // Close the reconnect channel on timeout/rejection as well as success.
      reconnect();
      stop();
      legacyTab.close();
    }
  });

  it("invalidates a pre-existing document even if its listener mounts after logout", async () => {
    // A server-rendered tab can display its private heading before React
    // hydrates. A transient BroadcastChannel notification alone is not enough.
    const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
    const values = new Map<string, string>();
    const fakeWindow = Object.assign(new EventTarget(), {
      localStorage: {
        getItem: (key: string) => values.get(key) ?? null,
        setItem: (key: string, value: string) => {
          values.set(key, value);
        },
      },
      performance: { timeOrigin: Date.now() - 60_000 },
    });
    Object.defineProperty(globalThis, "window", {
      configurable: true,
      value: fakeWindow,
    });
    let unsubscribeLate = () => {};
    let unsubscribeFresh = () => {};
    try {
      const lateTab = (await import(
        new URL("./auth-sync.ts?late-hydration", import.meta.url).href
      )) as typeof import("./auth-sync.ts");
      broadcastSignOut();
      assert.match(values.get(SIGNOUT_MARKER_KEY) ?? "", /^\d{13}$/);
      let invalidations = 0;
      unsubscribeLate = lateTab.subscribeToSignOut(() => {
        invalidations++;
      });
      assert.equal(
        invalidations,
        1,
        "Late-mounted tab must catch missed logout",
      );
      unsubscribeLate();
      unsubscribeLate = () => {};

      // A new login in the same document explicitly acknowledges that event.
      lateTab.resetLocalSignOutStarted();
      unsubscribeFresh = lateTab.subscribeToSignOut(() => {
        invalidations++;
      });
      assert.equal(invalidations, 1, "Old logout must not cancel a new login");
      unsubscribeFresh();
      unsubscribeFresh = () => {};

      // A later logout must be delivered to this newly signed-in tab.
      fakeWindow.performance.timeOrigin = Date.now() - 60_000;
      const next = Date.now() + 1;
      values.set(SIGNOUT_MARKER_KEY, String(next));
      unsubscribeFresh = lateTab.subscribeToSignOut(() => {
        invalidations++;
      });
      assert.equal(invalidations, 2, "New logout must invalidate after login");
    } finally {
      unsubscribeLate();
      unsubscribeFresh();
      // Undo the simulated sender's signing-out flag before the next test.
      resetLocalSignOutStarted();
      if (previous) Object.defineProperty(globalThis, "window", previous);
      else Reflect.deleteProperty(globalThis, "window");
    }
  });

  it("observes a storage event when a second tab misses BroadcastChannel", async () => {
    const previous = Object.getOwnPropertyDescriptor(globalThis, "window");
    const values = new Map<string, string>();
    const fakeWindow = Object.assign(new EventTarget(), {
      localStorage: {
        getItem: (key: string) => values.get(key) ?? null,
        setItem: (key: string, value: string) => values.set(key, value),
      },
      performance: { timeOrigin: Date.now() - 60_000 },
    });
    Object.defineProperty(globalThis, "window", {
      configurable: true,
      value: fakeWindow,
    });
    let stop = () => {};
    try {
      const otherTab = (await import(
        new URL("./auth-sync.ts?storage-fallback", import.meta.url).href
      )) as typeof import("./auth-sync.ts");
      let invalidations = 0;
      stop = otherTab.subscribeToSignOut(() => {
        invalidations++;
      });
      values.set(SIGNOUT_MARKER_KEY, String(Date.now()));
      const event = new Event("storage");
      Object.defineProperty(event, "key", { value: SIGNOUT_MARKER_KEY });
      fakeWindow.dispatchEvent(event);
      assert.equal(invalidations, 1);
      fakeWindow.dispatchEvent(event);
      assert.equal(invalidations, 1, "Duplicate events must not repeat logout");
    } finally {
      stop();
      if (previous) Object.defineProperty(globalThis, "window", previous);
      else Reflect.deleteProperty(globalThis, "window");
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
