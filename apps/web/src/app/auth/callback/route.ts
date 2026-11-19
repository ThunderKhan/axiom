import { NextResponse, type NextRequest } from "next/server";
import { publicAuthConfig } from "../../../lib/auth-config";
import { createServerAuthClient } from "../../../lib/supabase/server";

/** PKCE callback only; never honor a caller-supplied redirect or OAuth token. */
export async function GET(request: NextRequest) {
  const fail = () =>
    NextResponse.redirect(new URL("/login?notice=auth-unavailable", request.url), {
      headers: { "Cache-Control": "no-store", "Referrer-Policy": "no-referrer" },
    });
  const code = request.nextUrl.searchParams.get("code");
  if (
    !publicAuthConfig() ||
    !code ||
    code.length > 4096 ||
    !/^[A-Za-z0-9._~-]+$/.test(code) ||
    request.nextUrl.searchParams.has("error")
  ) {
    return fail();
  }
  try {
    const client = await createServerAuthClient(true);
    const exchanged = await client.auth.exchangeCodeForSession(code);
    if (exchanged.error || !exchanged.data.session) return fail();
    const verified = await client.auth.getClaims();
    if (
      verified.error ||
      !verified.data?.claims ||
      verified.data.claims.role !== "authenticated" ||
      verified.data.claims.is_anonymous === true
    ) {
      await client.auth.signOut({ scope: "local" });
      return fail();
    }
    return NextResponse.redirect(new URL("/app", request.url), {
      headers: { "Cache-Control": "no-store", "Referrer-Policy": "no-referrer" },
    });
  } catch {
    return fail();
  }
}
