/** Only an implemented, server-protected destination may follow login. */
export function safeReturnPath(value: unknown): "/app" {
  // No wildcard workspace routes until their FastAPI authorisation exists.
  // Reject encoded paths, schemes, slashes, separators and lookalikes by default.
  return value === "/app" ? "/app" : "/app";
}

export function loginDestination(notice?: string): string {
  const allowed = new Set([
    "session-required",
    "session-expired",
    "auth-unavailable",
    "signed-out",
    "signed-out-local",
  ]);
  const params = new URLSearchParams({ returnTo: "/app" });
  if (notice && allowed.has(notice)) params.set("notice", notice);
  return "/login?" + params.toString();
}
