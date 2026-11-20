import { expect, test, type BrowserContext, type Page } from "@playwright/test";

/**
 * M1 H4 / AUTH-01: genuine, explicitly authorized nonproduction provider test.
 * Every credential stays in process memory; traces, media and HTML are disabled.
 * NOT a fixture/JWT simulation. The API and database must already be running.
 */
test("M1 genuine JWT and two-user cross-tenant API acceptance", async ({
  browser,
  request,
}, testInfo) => {
  if (
    testInfo.project.use.trace !== "off" ||
    testInfo.project.use.screenshot !== "off" ||
    testInfo.project.use.video !== "off"
  ) {
    throw new Error("M1 real-provider acceptance requires trace-free execution");
  }
  if (
    process.env.M1_ACCEPTANCE_NONPRODUCTION !== "I_CONFIRM_NONPRODUCTION" ||
    process.env.E2E_M1_ACCEPTANCE !== "1"
  ) {
    throw new Error("M1 real-provider acceptance is not explicitly authorized");
  }

  const apiOrigin = process.env.NEXT_PUBLIC_API_BASE_URL!;
  const issuer = process.env.M1_ACCEPTANCE_ISSUER!;
  const emailA = process.env.E2E_SUPABASE_EMAIL!;
  const passA = process.env.E2E_SUPABASE_PASSWORD!;
  const emailB = process.env.E2E_SUPABASE_SECOND_EMAIL!;
  const passB = process.env.E2E_SUPABASE_SECOND_PASSWORD!;
  const a = await browser.newContext();
  const b = await browser.newContext();
  const readJWT = (part: string): Record<string, unknown> => {
    const decoded: unknown = JSON.parse(
      Buffer.from(part, "base64url").toString("utf8"),
    );
    if (
      typeof decoded !== "object" ||
      decoded === null ||
      Array.isArray(decoded)
    ) {
      throw new Error("Provider JWT has an invalid structure");
    }
    return decoded as Record<string, unknown>;
  };

  async function login(
    context: BrowserContext,
    email: string,
    password: string,
  ) {
    const page = await context.newPage();
    await page.goto("/");
    await page.getByRole("link", { name: "Sign in to Axiom" }).click();
    await page.getByRole("textbox", { name: "Email address" }).fill(email);
    await page.getByLabel("Password", { exact: true }).fill(password);
    // Capture only a token that the *real web app* actually sent to FastAPI.
    // Never write it to disk or a test assertion error/message.
    const captured = page.waitForRequest(
      (req) =>
        req.url() === apiOrigin + "/api/v1/me/bootstrap" &&
        (req.headers()["authorization"] ?? "").startsWith("Bearer "),
      { timeout: 30000 },
    );
    await page.getByRole("button", { name: "Sign in", exact: true }).click();
    const authHeader = (await captured).headers()["authorization"];
    expect(authHeader?.startsWith("Bearer ")).toBe(true);
    const jwt = authHeader!.slice("Bearer ".length);
    const sections = jwt.split(".");
    expect(sections).toHaveLength(3);
    const header = readJWT(sections[0]);
    const claims = readJWT(sections[1]);
    expect(["RS256", "ES256"]).toContain(header.alg);
    expect(typeof header.kid).toBe("string");
    expect(claims.iss).toBe(issuer);
    expect(claims.aud).toBe("authenticated");
    expect(claims.role).toBe("authenticated");
    expect(claims.is_anonymous).not.toBe(true);
    expect(claims.sub).toMatch(/^[0-9a-f]{8}-[0-9a-f-]{27,}$/i);
    expect(typeof claims.exp).toBe("number");
    expect(claims.exp as number).toBeGreaterThan(Math.floor(Date.now() / 1000));
    await expect(page).toHaveURL(/\/app(?:\?.*)?$/);
    await expect(
      page.getByRole("heading", { name: "Work from the right context." }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", {
        name: /Create your first workspace|Choose a workspace/,
      }),
    ).toBeVisible();
    return { page, jwt, subject: claims.sub as string };
  }

  async function createThroughBrowser(
    page: Page,
    name: string,
  ): Promise<string> {
    await page.getByLabel("Product or idea name").fill(name);
    await page.getByRole("button", { name: "Create workspace" }).click();
    await expect(page.locator(".workspace-active strong")).toHaveText(name);
    const value = new URL(page.url()).searchParams.get("workspace");
    expect(value).toMatch(/^[0-9a-f]{8}-[0-9a-f-]{27,}$/i);
    return value!;
  }

  async function assertError(
    response: Awaited<ReturnType<typeof request.get>>,
    status: number,
    code: string,
  ) {
    expect(response.status()).toBe(status);
    const body = await response.json();
    expect(Object.keys(body).sort()).toEqual(["error", "request_id"]);
    expect(body.error.code).toBe(code);
    expect(body.error.details).toEqual({});
    return body.error;
  }

  try {
    const ownerA = await login(a, emailA, passA);
    const ownerB = await login(b, emailB, passB);
    expect(ownerA.subject).not.toBe(ownerB.subject);

    // These API clients represent distinct *real user JWTs*, never a caller-supplied
    // principal UUID. The same FastAPI request authorization applies to both.
    const apiA = await request.newContext({
      baseURL: apiOrigin,
      extraHTTPHeaders: { Authorization: "Bearer " + ownerA.jwt },
    });
    const apiB = await request.newContext({
      baseURL: apiOrigin,
      extraHTTPHeaders: { Authorization: "Bearer " + ownerB.jwt },
    });
    const anonymous = await request.newContext({ baseURL: apiOrigin });
    try {
      const meA = await apiA.get("/api/v1/me");
      const meB = await apiB.get("/api/v1/me");
      expect(meA.status()).toBe(200);
      expect(meB.status()).toBe(200);
      expect((await meA.json()).id).toBe(ownerA.subject);
      expect((await meB.json()).id).toBe(ownerB.subject);

      const idSuffix = crypto.randomUUID().slice(0, 10);
      const nameA1 = "M1 A1 " + idSuffix;
      const nameA2 = "M1 A2 " + idSuffix;
      const nameB1 = "M1 B1 " + idSuffix;
      const a1 = await createThroughBrowser(ownerA.page, nameA1);
      const a2 = await createThroughBrowser(ownerA.page, nameA2);
      const b1 = await createThroughBrowser(ownerB.page, nameB1);
      expect(new Set([a1, a2, b1]).size).toBe(3);

      const listA = await apiA.get("/api/v1/workspaces?limit=100");
      const listB = await apiB.get("/api/v1/workspaces?limit=100");
      expect(listA.status()).toBe(200);
      expect(listB.status()).toBe(200);
      type WorkspaceListItem = { id: string; name: string };
      const itemsA: WorkspaceListItem[] = (await listA.json()).items;
      const itemsB: WorkspaceListItem[] = (await listB.json()).items;
      expect(itemsA.map((item) => item.id)).toEqual(
        expect.arrayContaining([a1, a2]),
      );
      expect(itemsB.map((item) => item.id)).toContain(b1);
      expect(itemsA.some((item) => item.id === b1)).toBe(false);
      expect(
        itemsB.some((item) => item.id === a1 || item.id === a2),
      ).toBe(false);

      await ownerA.page
        .getByRole("button", { name: new RegExp(nameA1) })
        .click();
      await expect(
        ownerA.page.locator(".workspace-active strong"),
      ).toHaveText(nameA1);
      await ownerA.page
        .getByRole("button", { name: new RegExp(nameA2) })
        .click();
      await expect(
        ownerA.page.locator(".workspace-active strong"),
      ).toHaveText(nameA2);
      await ownerA.page.reload();
      await expect(ownerA.page.locator(".workspace-active strong")).toHaveText(nameA2);
      await expect(ownerA.page).toHaveURL(new RegExp("workspace=" + a2));

      const own = await apiA.get("/api/v1/workspaces/" + a1);
      expect(own.status()).toBe(200);
      const oldVersion = (await own.json()).version as number;
      const updated = await apiA.patch("/api/v1/workspaces/" + a1, {
        data: { name: nameA1 + " updated", expected_version: oldVersion },
      });
      expect(updated.status()).toBe(200);
      expect((await updated.json()).version).toBe(oldVersion + 1);
      await assertError(
        await apiA.patch("/api/v1/workspaces/" + a1, {
          data: { name: "Stale", expected_version: oldVersion },
        }),
        409,
        "VERSION_CONFLICT",
      );

      const unknown = crypto.randomUUID();
      const foreignB = await assertError(
        await apiB.get("/api/v1/workspaces/" + a1),
        404,
        "NOT_FOUND",
      );
      const missingB = await assertError(
        await apiB.get("/api/v1/workspaces/" + unknown),
        404,
        "NOT_FOUND",
      );
      expect(foreignB).toEqual(missingB);
      await assertError(
        await apiB.get("/api/v1/workspaces/" + a2),
        404,
        "NOT_FOUND",
      );
      await assertError(
        await apiA.get("/api/v1/workspaces/" + b1),
        404,
        "NOT_FOUND",
      );
      await assertError(
        await apiB.patch("/api/v1/workspaces/" + a1, {
          data: { name: "Stolen", expected_version: 1 },
        }),
        404,
        "NOT_FOUND",
      );
      await assertError(
        await apiB.post("/api/v1/workspaces", {
          headers: { "Idempotency-Key": "m1-owner-spoof-" + idSuffix },
          data: { name: "Spoofed", owner_user_id: ownerA.subject },
        }),
        422,
        "VALIDATION_FAILED",
      );

      // Genuine FastAPI idempotency across different HTTP requests and DB sessions.
      const key = "m1-replay-" + crypto.randomUUID();
      const first = await apiA.post("/api/v1/workspaces", {
        headers: { "Idempotency-Key": key },
        data: { name: "M1 replay " + idSuffix },
      });
      const replay = await apiA.post("/api/v1/workspaces", {
        headers: { "Idempotency-Key": key },
        data: { name: "  M1 replay " + idSuffix + "  " },
      });
      expect(first.status()).toBe(201);
      expect(replay.status()).toBe(201);
      expect(await replay.json()).toEqual(await first.json());
      await assertError(
        await apiA.post("/api/v1/workspaces", {
          headers: { "Idempotency-Key": key },
          data: { name: "Changed payload" },
        }),
        409,
        "IDEMPOTENCY_CONFLICT",
      );

      await assertError(
        await anonymous.get("/api/v1/me"),
        401,
        "AUTH_REQUIRED",
      );
      await assertError(
        await anonymous.get("/api/v1/me", {
          headers: { Authorization: "Bearer malformed" },
        }),
        401,
        "AUTH_REQUIRED",
      );
      // Same claims but a changed signature must not authenticate.
      const segments = ownerA.jwt.split(".");
      const signature = segments[2];
      const tampered =
        signature.slice(0, -2) +
        (signature.at(-2) === "A" ? "B" : "A") +
        signature.at(-1);
      await assertError(
        await anonymous.get("/api/v1/me", {
          headers: {
            Authorization:
              "Bearer " + segments[0] + "." + segments[1] + "." + tampered,
          },
        }),
        401,
        "AUTH_REQUIRED",
      );

      // B's authenticated browser must not reauthorize A's forged deep link.
      await ownerB.page.goto("/app?workspace=" + a1);
      await expect(
        ownerB.page.getByRole("heading", { name: "Work from the right context." }),
      ).toBeVisible();
      await expect(
        ownerB.page.locator(".workspace-active strong"),
      ).not.toHaveText(nameA1);
      await expect(
        ownerB.page.getByRole("button", { name: new RegExp(nameA1) }),
      ).toHaveCount(0);

      await ownerB.page.setViewportSize({ width: 375, height: 812 });
      expect(
        await ownerB.page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBe(true);
      const ownButton = ownerB.page.getByRole("button", {
        name: new RegExp(nameB1),
      });
      await ownButton.focus();
      await expect(ownButton).toBeFocused();
      await ownerB.page.keyboard.press("Enter");
      await expect(
        ownerB.page.locator(".workspace-active strong"),
      ).toHaveText(nameB1);

      // Cookie removal simulates missing browser session state, not revoked JWTs.
      await a.clearCookies();
      await ownerA.page.reload();
      await expect(ownerA.page).toHaveURL(/\/login\?/);
      await expect(
        ownerA.page.getByRole("heading", { name: "Work from the right context." }),
      ).toHaveCount(0);

      await ownerB.page.getByRole("button", { name: "Sign out" }).click();
      await expect(ownerB.page).toHaveURL(/\/login\?notice=signed-out/);
      await ownerB.page.goto("/app?workspace=" + a1);
      await expect(ownerB.page).toHaveURL(/\/login\?/);
      await expect(
        ownerB.page.locator(".workspace-active strong"),
      ).toHaveCount(0);

      // An evaluator must use the same ordinary flow; optional when provisioned.
      const evaluatorEmail = process.env.E2E_SUPABASE_EVALUATOR_EMAIL;
      const evaluatorPassword = process.env.E2E_SUPABASE_EVALUATOR_PASSWORD;
      if (evaluatorEmail && evaluatorPassword) {
        const evaluatorContext = await browser.newContext();
        try {
          const evaluator = await login(
            evaluatorContext,
            evaluatorEmail,
            evaluatorPassword,
          );
          await evaluator.page.getByRole("button", { name: "Sign out" }).click();
          await expect(evaluator.page).toHaveURL(/\/login\?notice=signed-out/);
        } finally {
          await evaluatorContext.close();
        }
      }
    } finally {
      await Promise.all([apiA.dispose(), apiB.dispose(), anonymous.dispose()]);
    }
  } finally {
    await Promise.all([a.close(), b.close()]);
  }
});
