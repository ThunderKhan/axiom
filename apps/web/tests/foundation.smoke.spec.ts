import { expect, test } from "@playwright/test";

test("the home page loads with an honest, accessible foundation state", async ({
  page,
}) => {
  const response = await page.goto("/");
  expect(response?.status()).toBe(200);
  await expect(
    page.getByRole("heading", { level: 1, name: "Axiom is taking shape." }),
  ).toBeVisible();
  await expect(page.getByRole("main")).toBeVisible();
  await expect(page.getByRole("list", { name: "Current capabilities" })).toBeVisible();
  await expect(
    page.getByRole("listitem").filter({ hasText: "Authentication" }),
  ).toContainText("Not yet available");
  await expect(
    page.getByRole("listitem").filter({ hasText: "Research" }),
  ).toContainText("Not yet available");
  await expect(page.getByRole("link", { name: "Skip to content" })).toHaveAttribute(
    "href",
    "#main-content",
  );
});

test("the landing state fits a narrow mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  const isWithinViewport = await page.evaluate(
    () => document.documentElement.scrollWidth <= window.innerWidth,
  );
  expect(isWithinViewport).toBe(true);
});
