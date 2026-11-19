/** Production auth cookies are Secure; non-Secure cookies are local-development only. */
export function authCookieOptions(isProduction: boolean) {
  return { secure: isProduction, sameSite: "lax" as const, path: "/" };
}
