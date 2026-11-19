import assert from "node:assert/strict";
import { chromium } from "@playwright/test";

const [webOrigin, expectedApiOrigin] = process.argv.slice(2);
if (!webOrigin || !expectedApiOrigin) {
  throw new Error(
    "Usage: node scripts/m0-browser-smoke.mjs WEB_ORIGIN API_ORIGIN",
  );
}

const browser = await chromium.launch();
try {
  const page = await browser.newPage();
  const response = await page.goto(webOrigin, {
    waitUntil: "domcontentloaded",
    timeout: 30000,
  });
  assert.equal(
    response?.status(),
    200,
    "Next.js entrypoint must return HTTP 200",
  );
  assert.equal(
    await page
      .locator('meta[name="axiom-api-base-url"]')
      .getAttribute("content"),
    expectedApiOrigin,
    "the rendered public API base must match the intended container address",
  );
  assert.ok(
    await page
      .getByRole("heading", { level: 1, name: "Axiom is taking shape." })
      .isVisible(),
    "the real frontend foundation must render",
  );
  const result = await page.evaluate(async (origin) => {
    const response = await fetch(origin + "/api/v1/health/live");
    return { status: response.status, body: await response.json() };
  }, expectedApiOrigin);
  assert.deepEqual(
    result,
    {
      status: 200,
      body: { status: "alive", service: "axiom-api" },
    },
    "the real browser must be permitted to fetch the separate FastAPI container",
  );
  assert.ok(
    !(await page.content()).includes("axiom-private-test-sentinel"),
    "server-only sentinel must never appear in browser-visible markup",
  );
  console.log(
    "PASS: real Chromium loads native Next.js and fetches containerized FastAPI using public API origin",
  );
} finally {
  await browser.close();
}
