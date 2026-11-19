import { expect, test } from "@playwright/test";

/**
 * Real-provider acceptance. The default CI has no external Auth credentials,
 * so the test is skipped and never represented as successful live verification.
 *
 * Use an authorized nonproduction Supabase project plus a private test user:
 * E2E_SUPABASE_EMAIL and E2E_SUPABASE_PASSWORD must be present only in the
 * local/approved runner process, never checked into source or test reports.
 */
test("real authorized user signs in, survives refresh, then loses private access", async ({
  page,
}) => {
  const email = process.env.E2E_SUPABASE_EMAIL;
  const password = process.env.E2E_SUPABASE_PASSWORD;
  test.skip(
    !email || !password || !process.env.NEXT_PUBLIC_SUPABASE_URL,
    "Real Supabase test-project credentials are not configured",
  );
  await page.goto("/");
  await page.getByRole("link", { name: "Sign in to Axiom" }).click();
  await page.getByRole("textbox", { name: "Email address" }).fill(email!);
  await page.getByLabel("Password", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/app$/);
  await expect(
    page.getByRole("heading", { name: "Your Axiom session is active." }),
  ).toBeVisible();

  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Your Axiom session is active." }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login\?notice=signed-out/);
  await page.goto("/app");
  await expect(page).toHaveURL(/\/login\?/);
  await expect(
    page.getByRole("heading", { name: "Your Axiom session is active." }),
  ).toHaveCount(0);
});
