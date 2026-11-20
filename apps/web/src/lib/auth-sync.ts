/** Sign-out messages must not contain identity, credentials or session data. */
export const AUTH_CHANNEL = "axiom:auth";
export const SIGNED_OUT_MESSAGE = "signed-out";
export const LOCAL_SIGNOUT_STARTED = "axiom:auth:local-signout-started";

// Each browser tab has its own module instance. Other BroadcastChannel objects
// in the sender's *same tab* receive posts too, so tag each sender and ignore
// self-originating events to preserve the initiating server-action redirect.
const TAB_SENDER = crypto.randomUUID();

export function isSignOutMessage(value: unknown): boolean {
  return value === SIGNED_OUT_MESSAGE;
}

type SignOutEnvelope = { type: typeof SIGNED_OUT_MESSAGE; sender: string };

function isOtherTabSignOutMessage(value: unknown): value is SignOutEnvelope {
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
  try {
    const channel = new BroadcastChannel(AUTH_CHANNEL);
    channel.postMessage({ type: SIGNED_OUT_MESSAGE, sender: TAB_SENDER });
    channel.close();
  } catch {
    // Other tabs still revalidate the server session when becoming visible.
    console.warn("Axiom: cross-tab logout notification unavailable");
  }
}

export function subscribeToSignOut(callback: () => void): () => void {
  try {
    const channel = new BroadcastChannel(AUTH_CHANNEL);
    channel.onmessage = (event: MessageEvent<unknown>) => {
      if (isOtherTabSignOutMessage(event.data)) callback();
    };
    return () => channel.close();
  } catch {
    console.warn("Axiom: cross-tab logout subscription unavailable");
    return () => {};
  }
}

/** Cancel this tab's private requests immediately, without redirecting its form. */
export function notifyLocalSignOutStarted(): void {
  window.dispatchEvent(new Event(LOCAL_SIGNOUT_STARTED));
}

export function subscribeToLocalSignOutStarted(callback: () => void): () => void {
  window.addEventListener(LOCAL_SIGNOUT_STARTED, callback);
  return () => window.removeEventListener(LOCAL_SIGNOUT_STARTED, callback);
}
