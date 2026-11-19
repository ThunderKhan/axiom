# Axiom web foundation (issue #8)

This is the **first functional frontend package**. Its `/` route displays
implementation status, not login, authenticated workspaces, live research, or CRM.
The standalone web package can start without an API URL, but integrated development
uses the public, non-secret `NEXT_PUBLIC_API_BASE_URL` from `.env.example`.
No provider credentials are read or exposed in the browser. The public origin
is validated and emitted as a metadata value for integration verification.

## Prerequisites

- Node.js **22.16.0** (see `.nvmrc`; Node 22 is used in CI)
- npm **10.9.2** (declared in `package.json`)
- An internet connection for first-time dependency and browser installation

## Local commands

Run from `apps/web`:

```sh
npm ci
# On PowerShell: Copy-Item .env.example .env.local
npm run dev
# Open http://127.0.0.1:3000
```

Other checks:

```sh
npm run lint
npm run format:check
npm run typecheck
npm run test:unit
npx playwright install chromium
npm run test:smoke
npm run test:ci
npm run build
npm run start
npm run audit
```

`test:ci` executes unit tests **and** Chromium smoke tests. Node.js writes fresh
JUnit XML to `test-results/junit.xml`. The repo-level quality gate intentionally
removes a prior report before every test invocation and rejects missing, empty,
skipped-only or failing reports.

Playwright keeps list output and writes an HTML report without opening it
interactively (including when a test fails locally). `test:ci` enables tracing
and verifies the HTML report and attached trace archives after the browser tests,
with artifacts isolated in `playwright-artifacts/` rather than inside
`playwright-report/` or `test-results/`. The generated reports are ignored
by Git.

The smoke suite uses a private local development server at
`http://127.0.0.1:3100` to avoid clashing with a manual server on port 3000.
It requires Chromium downloaded by Playwright. It does not contact external
services and does not verify any user login or external API.

Integrated setup, native web + Docker API/worker smoke and safe cleanup are
specified in the [canonical developer guide](../../README.md#canonical-developer-setup--milestone-0-foundation).
The integrated smoke runs the frontend separately on port 3200 and uses real
Chromium to fetch FastAPI; it does not add product UI or fake backend data.

## Deployability

When a Vercel project is provisioned separately, set **Root Directory** to
`apps/web` and retain native Next.js build/start behavior. No deployment has
been performed or verified by issue #8. Never place server credentials in
`NEXT_PUBLIC_*` or commit a real `.env` file.

## Out of scope

The landing redesign, authentication, API, databases, source ingestion,
model inference, and CRM are owned by later issues. This package deliberately
does not simulate any of those capabilities.
