import { expect, test } from "@playwright/test";

test("anonymous users cannot activate a forged workspace deep link", async ({
  page,
}) => {
  const foreignId = "33333333-3333-4333-8333-333333333333";
  await page.goto("/app?workspace=" + foreignId);
  await expect(page).toHaveURL(
    /\/login\?returnTo=%2Fapp&notice=auth-unavailable/,
  );
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Work from the right context." }),
  ).toHaveCount(0);
  expect(await page.content()).not.toContain(foreignId);
});

test("anonymous mobile navigation does not reveal remembered private workspace", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/login");
  await page.evaluate(() => {
    sessionStorage.setItem(
      "axiom:workspace:11111111-1111-4111-8111-111111111111",
      "33333333-3333-4333-8333-333333333333",
    );
  });
  await page.goto("/app?workspace=33333333-3333-4333-8333-333333333333");
  await expect(page).toHaveURL(/\/login\?/);
  await expect.poll(() => page.evaluate(() => sessionStorage.length)).toBe(0);
  await expect(
    page.getByRole("heading", { name: "Work from the right context." }),
  ).toHaveCount(0);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
