import { defineConfig, devices } from "@playwright/test";

const port = 3100;
const baseURL = "http://127.0.0.1:" + port;

export default defineConfig({
  testDir: "./tests",
  outputDir: "./playwright-artifacts",
  testMatch: "*.smoke.spec.ts",
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
    timeout: 120_000,
  },
});
