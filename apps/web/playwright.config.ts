import { defineConfig, devices } from "@playwright/test";

const port = 3100;
const baseURL = "http://127.0.0.1:" + port;

export default defineConfig({
  testDir: "./tests",
  outputDir: "./playwright-artifacts",
  testMatch: "*.smoke.spec.ts",
  // Credential-bearing provider tests must never enter the traced CI suite.
  testIgnore: ["auth-provider.smoke.spec.ts", "workspace-provider.smoke.spec.ts"],
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL,
    ...devices["Desktop Chrome"],
  },
  webServer: {
    command: "npm run dev -- --port " + port,
    url: baseURL,
    reuseExistingServer: false,
    // Deterministic negative suite must not inherit local/CI Supabase credentials.
    env: {
      NEXT_PUBLIC_SUPABASE_URL: "",
      NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "",
      E2E_SUPABASE_EMAIL: "",
      E2E_SUPABASE_PASSWORD: "",
    },
    timeout: 120_000,
  },
});
