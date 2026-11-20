import { expect, test } from "@playwright/test";

/**
 * This file runs ONLY via the dedicated, trace-free provider Playwright config.
 * Default CI excludes this file entirely, including when provider secrets exist.
 *
 * Use an authorized nonproduction Supabase project plus a private test user:
 * E2E_SUPABASE_EMAIL and E2E_SUPABASE_PASSWORD must be present only in the
 * local/approved runner process, never checked into source or test reports.
 */
test("real authorized user signs in, survives refresh, then loses private access", async ({
  page,
  context,
}, testInfo) => {
  // Fail before entering credentials if a runner re-enables trace capture.
  if (
    testInfo.project.use.trace !== "off" ||
    testInfo.project.use.screenshot !== "off" ||
    testInfo.project.use.video !== "off"
  ) {
    throw new Error(
      "Real-provider authentication requires trace-free and media-free execution",
    );
  }
  const email = process.env.E2E_SUPABASE_EMAIL!;
  const password = process.env.E2E_SUPABASE_PASSWORD!;
  await page.goto("/");
  await page.getByRole("link", { name: "Sign in to Axiom" }).click();
  await page.getByRole("textbox", { name: "Email address" }).fill(email!);
  await page.getByLabel("Password", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/app(?:\?.*)?$/);
  await expect(
    page.getByRole("heading", { name: "Work from the right context." }),
  ).toBeVisible();

  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Work from the right context." }),
  ).toBeVisible();

  const otherTab = await context.newPage();
  await otherTab.goto("/app");
  await expect(
    otherTab.getByRole("heading", { name: "Work from the right context." }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login\?notice=signed-out/);
  await expect(otherTab).toHaveURL(/\/login\?notice=session-expired/);
  await expect(
    otherTab.getByRole("heading", { name: "Work from the right context." }),
  ).toHaveCount(0);
  await page.goto("/app");
  await expect(page).toHaveURL(/\/login\?/);
  await expect(
    page.getByRole("heading", { name: "Work from the right context." }),
  ).toHaveCount(0);
});
