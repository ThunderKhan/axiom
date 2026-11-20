import { expect, test } from "@playwright/test";

/** Real-provider test: trace-free, explicit opt-in, only nonproduction accounts. */
test("two authorized users create and isolate workspaces", async ({
  page,
}, testInfo) => {
  if (
    testInfo.project.use.trace !== "off" ||
    testInfo.project.use.screenshot !== "off" ||
    testInfo.project.use.video !== "off"
  )
    throw new Error("Provider tests require trace-free execution.");

  const firstEmail = process.env.E2E_SUPABASE_EMAIL!;
  const firstPassword = process.env.E2E_SUPABASE_PASSWORD!;
  const secondEmail = process.env.E2E_SUPABASE_SECOND_EMAIL!;
  const secondPassword = process.env.E2E_SUPABASE_SECOND_PASSWORD!;

  async function signIn(email: string, password: string) {
    await page.goto("/login");
    await page.getByRole("textbox", { name: "Email address" }).fill(email);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    await expect(page).toHaveURL(/\/app(?:\?.*)?$/);
    await expect(
      page.getByRole("heading", { name: "Work from the right context." }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: /Create your first workspace|Choose a workspace/,
      }),
    ).toBeVisible();
  }
  async function create(name: string) {
    await page.getByLabel("Product or idea name").fill(name);
    await page.getByRole("button", { name: "Create workspace" }).click();
    await expect(page.locator(".workspace-active strong")).toHaveText(name);
    const value = await page
      .locator(".workspace-active p")
      .first()
      .textContent();
    const id = value?.match(
      /[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}/i,
    )?.[0];
    expect(id).toBeTruthy();
    return id!;
  }

  const suffix = crypto.randomUUID().slice(0, 8);
  const nameA = "A1 " + suffix;
  const nameB = "A2 " + suffix;
  const nameOther = "B1 " + suffix;

  await signIn(firstEmail, firstPassword);
  const firstId = await create(nameA);
  const secondId = await create(nameB);
  await expect(
    page.getByRole("button", { name: new RegExp(nameA) }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: new RegExp(nameB) }),
  ).toBeVisible();

  // A request that finishes after the B selection must not restore A's content.
  await page.route("**/api/v1/workspaces/" + firstId, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 700));
    try {
      await route.continue();
    } catch {
      // An intentionally canceled request can reject the intercepted response.
    }
  });
  await page.getByRole("button", { name: new RegExp(nameA) }).click();
  await page.getByRole("button", { name: new RegExp(nameB) }).click();
  await expect(page.locator(".workspace-active strong")).toHaveText(nameB);
  await page.waitForTimeout(850);
  await expect(page.locator(".workspace-active strong")).toHaveText(nameB);
  await page.reload();
  await expect(page.locator(".workspace-active strong")).toHaveText(nameB);
  await expect(page).toHaveURL(new RegExp("workspace=" + secondId));

  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login\?notice=signed-out/);
  await signIn(secondEmail, secondPassword);
  await expect(
    page.getByRole("button", { name: new RegExp(nameA) }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: new RegExp(nameB) }),
  ).toHaveCount(0);
  await create(nameOther);
  await page.goto("/app?workspace=" + firstId);
  await expect(
    page.getByRole("heading", { name: "Work from the right context." }),
  ).toBeVisible();
  await expect(page.locator(".workspace-active strong")).not.toHaveText(nameA);
  await expect(
    page.getByRole("button", { name: new RegExp(nameA) }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login\?notice=signed-out/);
});
