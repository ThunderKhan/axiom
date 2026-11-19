/** Only an implemented, server-protected destination may follow login. */
const protectedEntry = "/app" as const;

export function safeReturnPath(value: unknown): "/app" {
  // Only /app is implemented. Do not forward foreign IDs or encoded paths to
  // unimplemented workspace routes until server-side authorization is available.
  if (typeof value !== "string" || value !== protectedEntry) {
    return protectedEntry;
  }
  return value;
}

export function loginDestination(notice?: string): string {
  const allowed = new Set([
    "session-required",
    "session-expired",
    "auth-unavailable",
    "signed-out",
    "signed-out-local",
  ]);
  const params = new URLSearchParams({ returnTo: protectedEntry });
  if (notice && allowed.has(notice)) params.set("notice", notice);
  return "/login?" + params.toString();
}
