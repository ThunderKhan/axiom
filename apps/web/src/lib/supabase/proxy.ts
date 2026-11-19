import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { publicAuthConfig } from "../auth-config";
import { authCookieOptions } from "./cookie-policy";

/** Next.js 16 proxy: refresh cookies without treating cookie contents as authority. */
export async function refreshAuthCookies(
  request: NextRequest,
): Promise<NextResponse> {
  const config = publicAuthConfig();
  if (!config) return NextResponse.next({ request });
  let response = NextResponse.next({ request });
  const policy = authCookieOptions(process.env.NODE_ENV === "production");
  const client = createServerClient(config.url, config.key, {
    auth: { flowType: "pkce" },
    cookieOptions: policy,
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(toSet, headers) {
        toSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        toSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, { ...options, ...policy }),
        );
        Object.entries(headers ?? {}).forEach(([name, value]) =>
          response.headers.set(name, value),
        );
      },
    },
  });
  try {
    // getClaims verifies the signature, issuer and expiry; getSession is not an auth guard.
    await client.auth.getClaims();
  } catch {
    // Route rendering itself re-verifies and denies access; never mark this as authenticated.
  }
  return response;
}
