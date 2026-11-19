import { defineConfig, devices } from "@playwright/test";

/** Separate, explicitly authorized real-provider test; NEVER use the traced CI config. */
const required = [
  "NEXT_PUBLIC_SUPABASE_URL",
  "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
  "E2E_SUPABASE_EMAIL",
  "E2E_SUPABASE_PASSWORD",
] as const;
const missing = required.filter((name) => !process.env[name]);
if (missing.length > 0) {
  throw new Error(
    "Real Supabase verification requires private test environment settings: " +
      missing.join(", "),
  );
}

const port = 3101;
const baseURL = "http://127.0.0.1:" + port;

export default defineConfig({
  testDir: "./tests",
  testMatch: "auth-provider.smoke.spec.ts",
  forbidOnly: true,
  retries: 0,
  fullyParallel: false,
  reporter: [["list"]],
  // Prevent failure context snapshots from persisting to disk.
  preserveOutput: "never",
  use: {
    baseURL,
    ...devices["Desktop Chrome"],
    // Login requests and Set-Cookie headers contain credentials and bearer tokens.
    // Do not generate traces, screenshots, video or HTML report artifacts.
    trace: "off",
    screenshot: "off",
    video: "off",
  },
  webServer: {
    command: "npm run dev -- --port " + port,
    url: baseURL,
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
