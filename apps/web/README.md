# Axiom web — foundation plus M1.4 Supabase Auth

Issue #17 adds ordinary email/password login, SSR/PKCE cookies, a Next.js 16
session-refresh proxy, server-verified protected /app, safe internal login
redirection and sign-out. The existing public / foundation page and M0
browser/API smoke remain working. **This does not implement the Edviro landing
redesign, workspace APIs, onboarding, live research or CRM.**

The frontend can run with no provider configured but denies access to /app and
explains why login is unavailable. NEXT_PUBLIC_API_BASE_URL remains public
and validates the original API origin. Supabase SDK access is **Auth-only**.
No real provider project or credentials have been verified by this PR.

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
services and does not verify a real Supabase login. The deterministic auth tests
cover public login, unconfigured mode, unsafe redirects, unauthenticated
protected-page denial, keyboard, mobile and error states.

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

The landing redesign, authenticated workspace APIs, onboarding, source
ingestion, model inference, and CRM are owned by later issues. The integrated
web authentication is not a declaration of application-user or workspace
authorization, or proof of real Supabase provider configuration.

## M1.4 local identity setup and protected-route testing (Windows PowerShell)

From the repository root, use the reviewed Node.js 22.16.0 and npm 10.9.2.
Run these commands inside apps/web:

    npm ci
    Copy-Item .env.example .env.local
    notepad .env.local
    npm run dev

Set NEXT*PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
in the *ignored* .env.local file, from an explicitly authorized **nonproduction**
Supabase project. NEXT_PUBLIC_API_BASE_URL can remain the public loopback
API origin. Only the public key prefixed sb_publishable* is supported; never
use a sb_secret/service_role key, private signing material, evaluator credentials
or database URL in NEXT_PUBLIC variables.

The Supabase Auth provider should have email/password enabled with an
individually provisioned ordinary test user. For a PKCE callback verify
the exact allowed URL http://127.0.0.1:3000/auth/callback in Supabase's Auth
redirect allowlist. Configure a separate matching HTTPS callback at a later
authorized deployment. This PR does not provision provider resources or
enable new social, signup or password-recovery flows.

Open http://127.0.0.1:3000/ and use "Sign in to Axiom". Valid credentials
should reach the server-protected /app foundation; wrong credentials display a
non-enumerating error. Direct /app navigation without a verified session goes
to /login. Refresh with a valid session should retain /app; expiration or
failed verification should deny private rendering. Sign out, then try Back:
restored cached private content must not remain accessible. The only allowed
post-login return destination is /app. The page never invents workspace data.

The frontend uses @supabase/ssr 0.12.7 and @supabase/supabase-js 2.119.1,
both exact-pinned in package.json and package-lock.json. Server actions use
Next.js's built-in Origin/Host CSRF checks, and the proxy refreshes auth
cookies before server rendering. Next.js protected components verify signed
claims independently of cookie presence. Supabase SSR shared cookies are NOT
guaranteed HttpOnly. No access or refresh token is intentionally sent to
metadata or logs. The browser SDK cannot query Supabase domain tables.

On signout, provider revocation is attempted and local cookies/preferences
are removed. Remote revocation is not guaranteed: an already-issued JWT can
remain valid until expiry. Authenticated identity also does not prove an
active application-user record or authorized workspace; future FastAPI
workspace APIs must enforce this separately.

### Verification commands

    npm run lint
    npm run format:check
    npm run typecheck
    npm run test:unit
    npx playwright install chromium
    npm run test:smoke
    npm run test:ci
    npm run build
    npm run audit

The default CI browser tests run **without real Supabase credentials**.
They are real browser tests of error/negative/routing behavior, not a
successful provider sign-in. Real nonproduction provider login, session
refresh, logout, cookie persistence, two-user isolation and FastAPI API
authorization remain a separate H4 verification gate.

From repository root, Docker Desktop/WSL2 is required for the existing
real-integrated smoke, with no changes to application policies:

    python ci/docker_smoke.py
    python ci/integrated_smoke.py

Troubleshooting: use nvm use 22.16.0 if Node mismatches. Use npm ci for the
locked install, not a lockfile mutation. Restart Next.js after changing
.env.local. If the provider refuses login, check URL/publishable key/project
identity and its email-password configuration without exposing credentials.
For callback mismatch check exact hostname/port and allowlists; for cookie
loss, inspect browser cookie settings without pasting cookie values into
logs or reports. Resolve a dev port conflict with npm run dev -- --port 3001
and configure the corresponding callback. Install Chromium via Playwright
when missing. For FastAPI CORS errors verify the **exact** web origin on the
backend; a frontend session does not grant API ownership. Never change
provider security settings merely to turn tests green.

**No real Supabase project, hosted backend, production deploy, account
provisioning or billable resource is touched by this change.**
