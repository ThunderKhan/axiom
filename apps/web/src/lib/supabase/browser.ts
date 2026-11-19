"use client";

import { createBrowserClient } from "@supabase/ssr";
import { publicAuthConfig } from "../auth-config";

export function createBrowserAuthClient() {
  const config = publicAuthConfig();
  if (!config) throw new Error("Supabase public Auth configuration is unavailable");
  // This SDK is used exclusively for authentication, not Supabase domain-table access.
  return createBrowserClient(config.url, config.key, {
    auth: { flowType: "pkce" },
  });
}
