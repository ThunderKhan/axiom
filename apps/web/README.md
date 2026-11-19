# Axiom web — M1.4 identity and M1.6 workspace selection

Issue #17 adds ordinary email/password login, SSR/PKCE cookies, a Next.js 16
session-refresh proxy, server-verified protected /app, safe internal login
redirection and sign-out. The existing public / foundation page and M0
browser/API smoke remain working. **M1.6 now integrates the approved FastAPI workspace APIs for authenticated
creation, selection and isolation. The landing redesign, product onboarding,
research and CRM remain outside this milestone.**

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

`test:ci` executes unit tests **and unconfigured-provider Chromium smoke tests only**. Node.js writes fresh
JUnit XML to `test-results/junit.xml`. The repo-level quality gate intentionally
removes a prior report before every test invocation and rejects missing, empty,
skipped-only or failing reports.

Playwright keeps list output and writes an HTML report without opening it
interactively (including when a test fails locally). `test:ci` enables tracing **only for the deterministic, credential-free suite**
and verifies the HTML report and attached trace archives after those browser tests,
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

The default CI browser tests force Supabase Auth **unconfigured** and exclude the
real-provider test file, even if a developer has credentials in their shell.
The traced CI/HTML-report pipeline never performs the genuine login.
They are real browser tests of error/negative/routing behavior, not a
successful provider sign-in. Real nonproduction provider login, session
refresh, logout, cookie persistence, two-user isolation and FastAPI API
authorization remain a separate H4 verification gate.

### Separate real-provider login verification (no traces or recordings)

The provider-backed test requires an explicitly authorized nonproduction
Supabase test account. It is **not** part of `npm run test:ci` or
`npm run test:smoke`. Its dedicated `playwright.provider.config.ts` selects
only the real-provider test, uses **list output only**, and disables trace,
screenshots, video and HTML report storage to avoid recording passwords or
session cookies. Do **not** override these security settings with CLI flags.
The test now also checks a second tab loses its private view after sign-out.

Use PowerShell in `apps/web` and your authorized test project settings.
Public provider settings must be available to the Playwright process, not
only in `.env.local` (which Next.js loads separately). Use the exact local
test origin `http://127.0.0.1:3101` if checking callbacks:

```powershell
$env:NEXT_PUBLIC_SUPABASE_URL = "https://YOUR-TEST-PROJECT.supabase.co"
$env:NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY = "YOUR-PUBLIC-PUBLISHABLE-KEY"
$env:E2E_SUPABASE_EMAIL = Read-Host "Test account email"
$securePassword = Read-Host "Test account password" -AsSecureString
$env:E2E_SUPABASE_PASSWORD = [System.Net.NetworkCredential]::new("", $securePassword).Password
npm run test:provider
Remove-Item Env:E2E_SUPABASE_PASSWORD -ErrorAction SilentlyContinue
Remove-Item Env:E2E_SUPABASE_EMAIL -ErrorAction SilentlyContinue
Remove-Variable securePassword -ErrorAction SilentlyContinue
```

Do not put test credentials in package scripts, Playwright traces, browser
screenshots, committed files, CI artifacts, PR descriptions, or command
arguments. The separate test fails on missing credentials rather than
silently passing or skipping; an actual provider round-trip remains
unverified until run against the authorized provider. Keep the test-runner
environment and any process logs access-controlled and redacted.

### Cookies and logout verification

All Supabase SSR client factories (browser, server action and proxy) set
`Secure` on session cookies whenever `NODE_ENV=production`; local
`next dev` on loopback allows non-Secure cookies. `SameSite=Lax` and root
path are explicit. Production requires HTTPS, and HSTS/first-HTTP-request
handling needs verification on the actual deployed host. Shared SSR
cookies are **not guaranteed HttpOnly**.

Sign-out broadcasts a _credential-free_ notification to open tabs, and
other tabs also revalidate their server session when brought back into
view. Storage cleanup failures are safely reported without logging private
storage content and never prevent navigation. Invalid session recovery,
cross-tab behavior and cookie flags require real-provider/HTTPS evidence
before any release claim.

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

## M1.6 — authenticated workspace creation and selection (Issue #19)

The existing server-verified /app route now hosts workspace bootstrap, creation,
selection, reauthorization and recovery. The browser obtains its normal Supabase
user access JWT and calls only FastAPI for domain data. The backend separately
verifies the JWT, active app-user status and workspace ownership. No new provider,
schema migration, service-role client, product onboarding, research or CRM.

A first login explicitly bootstraps the active application user through
POST /api/v1/me/bootstrap. A zero-workspace account sees a real creation form;
there is no synthetic product data. The owner can create two or more independent
workspaces, switch, and reload. Any deep link /app?workspace=UUID and any saved
selection is treated as an _untrusted candidate_: FastAPI reauthorizes it before
display. Foreign/missing IDs use identical safe fallback.

The current preference is stored in sessionStorage only under the verified
axiom:workspace:<user-id> key. Logout, account change, expired auth or failed
authorization clears private state and cancels outstanding requests. Switching
invalidates a request generation and aborts prior selections so even a late
response cannot restore another workspace's context. No private domain-data
cache is introduced. Existing cross-tab logout/visibility rechecks remain.

Workspace creation binds a cryptographically random Idempotency-Key and a
canonical name to one user/attempt. Double submission is prevented. If a
POST transport fails or the backend reports unavailable after a possible write,
the outcome is **uncertain**, not a certain failure. No automatic retry is
performed because the maximum client/proxy/network delivery delay has not
been verified for a deployment. Inspect the owned workspace list before
choosing to begin a separate creation. Duplicate outcomes remain possible
after a very late retry past retention expiry and purge.

### Windows PowerShell — isolated end-to-end setup

From the repository root, use Docker Desktop/WSL2 and disposable local
PostgreSQL 17. Terminal A (dedicated database verification; never production):

    docker compose -f infra/compose.db-test.yml up -d --wait postgres-test
    cd services/api
    uv sync --locked --all-groups
    $env:AXIOM_TEST_ADMIN_DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/axiom_test"
    $env:AXIOM_MIGRATION_DATABASE_URL = "postgresql://axiom_migrator@127.0.0.1:55432/axiom_test"
    $env:AXIOM_TEST_RUNTIME_DATABASE_URL = "postgresql://axiom_runtime@127.0.0.1:55432/axiom_test"
    uv run --frozen python scripts/run_db_integration.py

Terminal B (ordinary API; do not copy privileged test credentials into it):

    cd services/api
    Remove-Item Env:AXIOM_MIGRATION_DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:AXIOM_TEST_ADMIN_DATABASE_URL -ErrorAction SilentlyContinue
    $env:AXIOM_DATABASE_URL = "postgresql://axiom_runtime@127.0.0.1:55432/axiom_test"
    $env:AXIOM_DATABASE_REQUIRED = "true"
    $env:AXIOM_CORS_ORIGINS = "http://127.0.0.1:3000"
    $env:AXIOM_AUTH_ISSUER = "https://YOUR-TEST-PROJECT.supabase.co/auth/v1"
    $env:AXIOM_AUTH_AUDIENCE = "authenticated"
    $env:AXIOM_AUTH_JWKS_URL = "$env:AXIOM_AUTH_ISSUER/.well-known/jwks.json"
    uv run --frozen python -m app.api

Replace the test project placeholder locally with a separately authorized
nonproduction Supabase Auth project issuing approved asymmetric user JWTs.
The API listens on 127.0.0.1:8000; verify
/api/v1/health/live and /api/v1/health/ready using Invoke-RestMethod.

Terminal C (Node 22.16.0, npm 10.9.2, from repository root):

    cd apps/web
    npm ci
    Copy-Item .env.example .env.local
    notepad .env.local
    npm run dev

In ignored .env.local set only NEXT*PUBLIC_API_BASE_URL (default
http://127.0.0.1:8000), NEXT_PUBLIC_SUPABASE_URL and public
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY, with the sb_publishable* prefix. Do not
put credentials, service keys, signing keys or DB URLs in browser settings.
The exact http://127.0.0.1:3000/auth/callback must be allowed by the
nonproduction provider. Restart Next.js after changing .env.local.

Open http://127.0.0.1:3000, sign in with an ordinary preprovisioned account,
wait for app-user bootstrap, create workspace A, create B, select A and B,
reload to check the remembered valid selection, then sign out. Sign in as a
distinct second account; it must not see A or B. Test a fabricated/foreign
/app?workspace=UUID, expired session, Back after logout, and DevTools
network delay while switching A to B. Simulate a dropped creation response:
the UI must show uncertain completion without submitting another POST.
The backend remains authoritative regardless of local preference injection.

### Verification and evidence boundaries

In apps/web:

    npm ci
    npm run lint
    npm run format:check
    npm run typecheck
    npm run test:unit
    npx playwright install chromium
    npm run test:smoke
    npm run test:ci
    npm run build
    npm run audit

In services/api:

    uv run --frozen python scripts/check_style.py
    uv run --frozen mypy app
    uv run --frozen pytest -q --junitxml=test-results/junit.xml

Run scripts/run_db_integration.py only from Terminal A with all three
isolated DB URLs still present. From root, backend Docker/worker and
existing M0 browser integration smoke commands are:

    python ci/docker_smoke.py
    python ci/integrated_smoke.py

Ordinary traced Playwright CI intentionally forces Supabase unconfigured.
It verifies denied private access and deterministic client/unit contracts,
**not real login or browser-to-DB acceptance**. Real-provider testing stays
separate via npm run test:provider (trace/screenshot/video off, list-only,
no retained artifacts). To opt into the real two-account workspace journey,
set E2E_WORKSPACE_API_READY=1, valid NEXT_PUBLIC_API_BASE_URL and the private
E2E_SUPABASE_SECOND_EMAIL/PASSWORD in addition to the ordinary first-account
E2E_SUPABASE_EMAIL/PASSWORD. Set API CORS to allow
http://127.0.0.1:3101 for that test. This opt-in writes genuine test
workspaces: run only on a separately authorized nonproduction project.
No real-provider, Windows, deployed HTTPS or full browser-to-database test
is claimed merely by adding that test.

Troubleshooting: use nvm use 22.16.0; verify Docker with docker info; ensure
Postgres test role/grants/RLS are initialized by the isolated DB runner; verify
API origin, port 8000, CORS exact Next.js origin, issuer/JWKS, and provider
signing mode. 401 requires new authentication; 403 indicates disabled app
account; 409 can signal missing bootstrap or create-key conflict; 503 means
provider/DB unavailable, not an empty workspace list. Install Chromium with
npx playwright install chromium if missing. Never paste token-containing
request headers, credentials or SQL URLs into public logs or discussions.

Stop the API and web native processes using Ctrl+C. From repository root:

    docker compose -f infra/compose.db-test.yml down

Do not add -v or delete persistent volumes. Before returning to main, inspect
git status, commit/stash local changes, then git switch main and
git pull --ff-only origin main. To update an existing checked-out feature
branch after saving work, use git pull --ff-only origin
feat/19-workspace-selection-ui. Browser-to-Supabase-to-FastAPI-to-RLS live
acceptance remains issue #20; qualified human security review is required.
