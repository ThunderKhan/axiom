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

const workspaceEnabled = process.env.E2E_WORKSPACE_API_READY === "1";
const acceptanceEnabled = process.env.E2E_M1_ACCEPTANCE === "1";
const p0Enabled = process.env.E2E_P0_ACCEPTANCE === "1";
if (p0Enabled && !acceptanceEnabled) {
  throw new Error("P0 acceptance requires explicit M1 provider acceptance");
}
if (acceptanceEnabled && !workspaceEnabled) {
  throw new Error("M1 acceptance must include real workspace provider tests");
}
if (workspaceEnabled) {
  const requiredForWorkspaces = [
    "NEXT_PUBLIC_API_BASE_URL",
    "E2E_SUPABASE_SECOND_EMAIL",
    "E2E_SUPABASE_SECOND_PASSWORD",
  ] as const;
  const missingWorkspace = requiredForWorkspaces.filter(
    (name) => !process.env[name],
  );
  if (missingWorkspace.length) {
    throw new Error(
      "Workspace provider verification needs settings: " +
        missingWorkspace.join(", "),
    );
  }
}

const port = 3101;
const baseURL = "http://127.0.0.1:" + port;

export default defineConfig({
  testDir: "./tests",
  testMatch: acceptanceEnabled
    ? [
        "auth-provider.smoke.spec.ts",
        "workspace-provider.smoke.spec.ts",
        "m1-acceptance.provider.spec.ts",
      ]
    : workspaceEnabled
      ? ["auth-provider.smoke.spec.ts", "workspace-provider.smoke.spec.ts"]
      : "auth-provider.smoke.spec.ts",
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
