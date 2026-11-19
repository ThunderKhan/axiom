import { expect, test } from "@playwright/test";

test("public entry opens an accessible ordinary login page", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Sign in to Axiom" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(
    page.getByRole("heading", { level: 1, name: "Welcome back." }),
  ).toBeVisible();
  await expect(
    page.getByRole("textbox", { name: "Email address" }),
  ).toBeVisible();
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "AXIOM" })).toHaveAttribute(
    "href",
    "/",
  );
  await expect(
    page.getByRole("link", { name: "Skip to sign in" }),
  ).toHaveAttribute("href", "#login-main");
});

test("unconfigured auth reports failure rather than accepting fake credentials", async ({
  page,
}) => {
  await page.goto("/login");
  await expect(
    page.locator(".auth-card .auth-error[role=alert]"),
  ).toContainText("not configured");
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("textbox", { name: "Email address" }),
  ).toBeDisabled();
  expect(await page.content()).not.toContain("sb_secret_");
});

test("direct private navigation fails closed with no session or provider", async ({
  page,
}) => {
  await page.goto("/app");
  await expect(page).toHaveURL(
    /\/login\?returnTo=%2Fapp&notice=auth-unavailable/,
  );
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
  expect(await page.getByText("Your Axiom session is active.").count()).toBe(0);
});

test("malicious returnTo never becomes a redirect or a hidden form value", async ({
  page,
}) => {
  await page.goto("/login?returnTo=https%3A%2F%2Fevil.example%2Fsteal");
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
  await expect(page.locator('input[name="returnTo"]')).toHaveValue("/app");
  await page.goto("/login?returnTo=%2F%2Fevil.example");
  await expect(page.locator('input[name="returnTo"]')).toHaveValue("/app");
});

test("unapproved callback query is refused with no private page", async ({
  page,
}) => {
  await page.goto("/auth/callback?code=dummy&next=https%3A%2F%2Fevil.example");
  await expect(page).toHaveURL(/\/login\?notice=auth-unavailable$/);
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
});

test("mobile login has no overflow and the keyboard can reach public navigation", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/login");
  await expect(
    page.getByRole("heading", { name: "Welcome back." }),
  ).toBeVisible();
  const within = await page.evaluate(
    () => document.documentElement.scrollWidth <= window.innerWidth,
  );
  expect(within).toBe(true);
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to sign in" }),
  ).toBeFocused();
});

test("prototype-related notice parameters are ignored, not rendered as objects", async ({
  page,
}) => {
  for (const notice of ["__proto__", "constructor", "toString"]) {
    const response = await page.goto("/login?notice=" + notice);
    expect(response?.status()).toBe(200);
    await expect(
      page.getByRole("heading", { name: "Welcome back." }),
    ).toBeVisible();
  }
});

test("login after expired or unavailable private session clears stale private storage", async ({
  page,
}) => {
  await page.goto("/login");
  for (const target of ["/app", "/login?notice=session-expired"]) {
    await page.evaluate(() => {
      window.localStorage.setItem(
        "axiom:workspace:previous-owner",
        "private-workspace",
      );
      window.sessionStorage.setItem(
        "axiom:private:previous-owner:query",
        "private-query",
      );
      window.localStorage.setItem("color-scheme", "light");
    });
    await page.goto(target);
    await expect(page).toHaveURL(/\/login\?(?:returnTo=|notice=)/);
    await expect
      .poll(() =>
        page.evaluate(() => ({
          workspace: window.localStorage.getItem(
            "axiom:workspace:previous-owner",
          ),
          query: window.sessionStorage.getItem(
            "axiom:private:previous-owner:query",
          ),
          unrelated: window.localStorage.getItem("color-scheme"),
        })),
      )
      .toEqual({ workspace: null, query: null, unrelated: "light" });
  }
});
