import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { publicAuthConfig } from "../auth-config";

/** Per-request Supabase client. Never cache a user's cookie-bound client globally. */
export async function createServerAuthClient(writable = false) {
  const config = publicAuthConfig();
  if (!config) throw new Error("Supabase public Auth configuration is unavailable");
  const store = await cookies();
  return createServerClient(config.url, config.key, {
    auth: { flowType: "pkce" },
    cookies: {
      getAll() {
        return store.getAll();
      },
      setAll(toSet) {
        // Server Components must not write cookies. The Next.js 16 proxy
        // refreshes them before protected rendering. Actions/routes are writable.
        if (!writable) return;
        toSet.forEach(({ name, value, options }) => store.set(name, value, options));
      },
    },
  });
}
