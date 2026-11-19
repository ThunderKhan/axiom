import { NextResponse, type NextRequest } from "next/server";
import { refreshAuthCookies } from "./lib/supabase/proxy";

export async function proxy(request: NextRequest) {
  const response = await refreshAuthCookies(request);
  if (request.nextUrl.pathname.startsWith("/app")) {
    // A successful response must not become a shared/CDN/browser stored private page.
    response.headers.set("Cache-Control", "private, no-store, max-age=0");
    response.headers.set("Vary", "Cookie");
  }
  response.headers.set("X-Content-Type-Options", "nosniff");
  return response;
}

export const config = { matcher: ["/app/:path*", "/login", "/auth/callback"] };
