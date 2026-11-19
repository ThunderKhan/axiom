/** The public API origin is not a credential or a promise of API availability. */
export function validatePublicApiBaseUrl(value?: string): string {
  if (value === undefined || value === "") return "";
  if (value.trim() !== value) throw new Error("API base URL must not contain whitespace");
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must be an absolute URL");
  }
  if (
    !["https:", "http:"].includes(url.protocol) ||
    !url.hostname ||
    url.username ||
    url.password ||
    url.search ||
    url.hash ||
    url.pathname !== "/" ||
    url.origin !== value
  ) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL must be an exact origin without credentials");
  }
  if (url.protocol === "http:" && !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)) {
    throw new Error("Plain HTTP API origins are allowed only on loopback");
  }
  return url.origin;
}

// The literal key lets Next.js inline only the approved public setting.
export const publicApiBaseUrl = validatePublicApiBaseUrl(
  process.env.NEXT_PUBLIC_API_BASE_URL,
);
