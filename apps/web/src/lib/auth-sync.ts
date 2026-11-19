/** Sign-out messages must not contain identity, credentials or session data. */
export const AUTH_CHANNEL = "axiom:auth";
export const SIGNED_OUT_MESSAGE = "signed-out";

export function isSignOutMessage(value: unknown): boolean {
  return value === SIGNED_OUT_MESSAGE;
}

export function broadcastSignOut(): void {
  try {
    const channel = new BroadcastChannel(AUTH_CHANNEL);
    channel.postMessage(SIGNED_OUT_MESSAGE);
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
      if (isSignOutMessage(event.data)) callback();
    };
    return () => channel.close();
  } catch {
    console.warn("Axiom: cross-tab logout subscription unavailable");
    return () => {};
  }
}
