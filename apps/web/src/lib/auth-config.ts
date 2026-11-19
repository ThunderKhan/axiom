/** Only the publicly publishable Supabase Auth configuration may reach Next.js. */
export type PublicAuthConfig = Readonly<{ url: string; key: string }>;

export function validateAuthConfig(
  rawUrl: string | undefined,
  rawKey: string | undefined,
): PublicAuthConfig | null {
  if (!rawUrl || !rawKey) return null;
  if (rawUrl.trim() !== rawUrl || rawKey.trim() !== rawKey) return null;
  let parsed: URL;
  try {
    parsed = new URL(rawUrl);
  } catch {
    return null;
  }
  const local =
    parsed.protocol === "http:" &&
    ["localhost", "127.0.0.1", "[::1]"].includes(parsed.hostname);
  if (
    (parsed.protocol !== "https:" && !local) ||
    parsed.origin !== rawUrl ||
    parsed.username ||
    parsed.password ||
    parsed.pathname !== "/" ||
    parsed.search ||
    parsed.hash
  ) {
    return null;
  }
  // Accept only Supabase's public publishable-key format, never service/secret keys.
  if (!/^sb_publishable_[A-Za-z0-9_-]{8,256}$/.test(rawKey)) return null;
  return { url: parsed.origin, key: rawKey };
}

export function publicAuthConfig(): PublicAuthConfig | null {
  // Literal public names ensure Next.js includes only these documented browser settings.
  return validateAuthConfig(
    process.env.NEXT_PUBLIC_SUPABASE_URL,
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY,
  );
}
