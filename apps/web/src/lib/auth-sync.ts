/** Sign-out messages must not contain identity, credentials or session data. */
export const AUTH_CHANNEL = "axiom:auth";
export const SIGNED_OUT_MESSAGE = "signed-out";
export const LOCAL_SIGNOUT_STARTED = "axiom:auth:local-signout-started";
// This is only a non-secret event timestamp, never an auth token or identity.
// It lets an already-open document catch a logout missed before hydration.
export const SIGNOUT_MARKER_KEY = "axiom:auth:last-signout";

// Each browser tab has its own module instance. Other BroadcastChannel objects
// in the sender's *same tab* receive posts too, so tag each sender and ignore
// self-originating events to preserve the initiating server-action redirect.
const TAB_SENDER = crypto.randomUUID();
// The legacy protocol has no sender identity. This tab must ignore its own
// compatibility string once it starts signing out, so its server-action
// redirect is not replaced with the session-expired navigation.
let localSignOutStarted = false;
let acknowledgedSignOutAt = 0;

function storedSignOutAt(): number | null {
  try {
    const value = window.localStorage.getItem(SIGNOUT_MARKER_KEY);
    if (!value || !/^\d{13}$/.test(value)) return null;
    const at = Number(value);
    return Number.isSafeInteger(at) ? at : null;
  } catch {
    return null;
  }
}

function missedSignOutSinceDocumentOpened(): boolean {
  if (typeof window === "undefined" || localSignOutStarted) return false;
  const at = storedSignOutAt();
  return (
    at !== null &&
    at > window.performance.timeOrigin &&
    at > acknowledgedSignOutAt
  );
}

export function isSignOutMessage(value: unknown): boolean {
  return value === SIGNED_OUT_MESSAGE;
}

function isOtherTabSignOutMessage(value: unknown): boolean {
  if (isSignOutMessage(value)) return !localSignOutStarted;
  return (
    typeof value === "object" &&
    value !== null &&
    "type" in value &&
    isSignOutMessage(value.type) &&
    "sender" in value &&
    typeof value.sender === "string" &&
    value.sender !== TAB_SENDER
  );
}

export function broadcastSignOut(): void {
  localSignOutStarted = true;
  try {
    // A BroadcastChannel event can be missed if a server-rendered second tab
    // hydrates after sign-out. Other tabs also see the storage event promptly.
    window.localStorage.setItem(SIGNOUT_MARKER_KEY, String(Date.now()));
  } catch {
    // BroadcastChannel and visibility-based revalidation still apply.
  }
  try {
    const channel = new BroadcastChannel(AUTH_CHANNEL);
    // New tabs use the tagged message; already-open legacy tabs require the
    // original string. Post tagged first so new receivers can de-duplicate.
    channel.postMessage({ type: SIGNED_OUT_MESSAGE, sender: TAB_SENDER });
    channel.postMessage(SIGNED_OUT_MESSAGE);
    channel.close();
  } catch {
    // Other tabs still revalidate the server session when becoming visible.
    console.warn("Axiom: cross-tab logout notification unavailable");
  }
}

export function subscribeToSignOut(callback: () => void): () => void {
  let notified = false;
  const notifyOnce = () => {
    if (notified || localSignOutStarted) return;
    notified = true;
    callback();
  };
  let channel: BroadcastChannel | null = null;
  try {
    channel = new BroadcastChannel(AUTH_CHANNEL);
    channel.onmessage = (event: MessageEvent<unknown>) => {
      if (isOtherTabSignOutMessage(event.data)) notifyOnce();
    };
  } catch {
    console.warn("Axiom: cross-tab logout subscription unavailable");
  }

  const onStorage = (event: StorageEvent) => {
    if (event.key === SIGNOUT_MARKER_KEY && missedSignOutSinceDocumentOpened())
      notifyOnce();
  };
  if (typeof window !== "undefined") {
    // Install the listener before checking the durable marker so an event
    // between registration and hydration cannot be lost.
    window.addEventListener("storage", onStorage);
    if (missedSignOutSinceDocumentOpened()) notifyOnce();
  }

  return () => {
    channel?.close();
    if (typeof window !== "undefined")
      window.removeEventListener("storage", onStorage);
  };
}

/** Cancel this tab's private requests immediately, without redirecting its form. */
/** A new login attempt re-enables legacy notifications after a soft navigation. */
export function resetLocalSignOutStarted(): void {
  // A new login acknowledges the previous event; do not treat it as a logout
  // for the newly authenticated session reached via Next soft navigation.
  acknowledgedSignOutAt = storedSignOutAt() ?? 0;
  localSignOutStarted = false;
}

export function notifyLocalSignOutStarted(): void {
  localSignOutStarted = true;
  window.dispatchEvent(new Event(LOCAL_SIGNOUT_STARTED));
}

export function subscribeToLocalSignOutStarted(
  callback: () => void,
): () => void {
  window.addEventListener(LOCAL_SIGNOUT_STARTED, callback);
  return () => window.removeEventListener(LOCAL_SIGNOUT_STARTED, callback);
}
