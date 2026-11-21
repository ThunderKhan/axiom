# Milestone 1.7 — Security Acceptance Evidence Ledger

**Status: M1 INCOMPLETE VERIFICATION / ACCEPTANCE BLOCKED**
**Outstanding gate:** [#29](https://github.com/ThunderKhan/axiom/issues/29) | **Merged implementation:** [#20 / PR #28](https://github.com/ThunderKhan/axiom/pull/28) | **Work package:** WP-02 | **Governing policy:** AGENTS.md 1.1, ENGINEERING.md 1.1
**Approved authority:** docs/20-M1-AUTH-WORKSPACE-CONTRACT.md, ADR-002
**Starting main:** a55e0d1a2735d9b0669e78791840c2386002d20e
**Recorded:** 20 November 2026; **updated with live evidence:** 21 November 2026. This is an execution ledger, not an approved new design.

All six prerequisite stages and the acceptance harness (PR #28) have
merged into main. On 20 November, real provider execution had not yet run.
The owner authorized pausing only VSPH Supabase to free a zero-cost
project slot; VSPH was paused, not deleted. A dedicated Axiom-only
Free-tier project, `axiom-m1-auth-test` in ap-south-1, was created.
The initial security-advisor check reported no findings. No paid
services were enabled.

**21 November update:** Genuine Supabase Auth/browser/API acceptance
**PASSED** against an **isolated PostgreSQL 17 CI container**, not the
managed Supabase database. Hosted database inspection found no `axiom`
schema, M1 application tables, Alembic revision, application roles or
RLS policies; the current security advisor warns that leaked-password
protection is disabled. **Hosted schema/migration/RLS/pooler parity
and independent qualified human security signoff remain outstanding.**
Issue #29 remains open; Milestone 1 has not been signed off.

## 21 November — real-provider pass and hosted Supabase read-only audit

**Environment:** dedicated `axiom-m1-auth-test` Free-tier project
(Mumbai, `ap-south-1`), healthy, PostgreSQL **17.12**. Read-only
catalog queries through the Supabase connection; no hosted DDL,
schema migration, database user creation, credential changes or
billed services were performed.

**Actual successful run:** [real-provider security acceptance
#44850664291](https://github.com/ThunderKhan/axiom/actions/runs/44850664291)
reported `PASS: 3 real-provider Playwright tests` at
`9e72d8872d48c7aae54aebcf8abe7fc1ca465f6a`. The same
`main` SHA passed [Quality #44850011295](https://github.com/ThunderKhan/axiom/actions/runs/44850011295)
and [Governance #44850011270](https://github.com/ThunderKhan/axiom/actions/runs/44850011270).
The workflow explicitly identifies its evidence as **real Supabase
Auth + isolated FastAPI/PostgreSQL/RLS**, not a hosted database test.

| Required hosted parity | Supabase catalog observation | Current status |
|---|---|---|
| Managed PostgreSQL version and project health | ACTIVE_HEALTHY, PostgreSQL 17.12 | VERIFIED |
| `axiom` schema | Does not exist | BLOCKED |
| `axiom.app_users`, `axiom.workspaces`, `axiom.workspace_create_idempotency` | All absent | BLOCKED |
| `public.alembic_version` revision | Absent; Supabase-managed migration list also empty | BLOCKED |
| Dedicated `axiom_migrator` and non-bypass `axiom_runtime` | Neither role exists | BLOCKED |
| Seven `axiom` RLS policies and enabled RLS on three tables | No application policies/tables exist | BLOCKED |
| Actual least-privileged FastAPI DB role + direct/pooler transaction reuse | Cannot test until schema, roles, private connection credentials and reviewed deployment exist | NOT VERIFIED |
| Hosted pooler endpoint / mode and tenant isolation | SQL management query does not exercise the pooler | NOT VERIFIED |
| Supabase security advisor | Leaked-password protection disabled (WARN) | REVIEW NEEDED |

**Crucial separation:** `postgres` in the managed project has
`BYPASSRLS`, while the approved API design requires a separate
non-owner `axiom_runtime` with no `BYPASSRLS`. A successful SQL
Editor/administrative query cannot prove ordinary runtime RLS.
The approved `services/api/migrations/versions/m1_0001_schema.py`
and `m1_0002_rls.py` require a dedicated migration-role owner and
create the three tables plus seven policies. The repository's
`services/api/tests/postgres_roles.sql` is explicitly **local
disposable CI only**; never run it against hosted Supabase.

**Remaining hosted acceptance, separately reviewed/authorized:**
1. Approve the nonproduction database role/credential provisioning
   procedure and a forward-only Alembic migration plan, with schema
   ownership and `public.alembic_version` grants reviewed first.
   Run through an authorized migration identity, **not** the runtime
   principal. Do not implicitly enable a paid plan or use production.
2. Verify hosted revision and seven RLS policies through catalog
   queries, and verify `Database.ready()` under the actual
   `axiom_runtime` login with no elevated roles or bypass.
3. With two authorized ordinary identities, run real hosted
   transaction-bound RLS `USING`/`WITH CHECK`, wrong-principal
   and `SET LOCAL` reuse probes through the selected Supavisor
   session/transaction pooler mode. Check prepared-statement and
   transaction-pooler constraints for the chosen driver.
4. Document host, mode and SHA **without passwords or connection
   strings**. Assess the leaked-password-protection warning against
   the Free-tier entitlement; do not change the setting without
   owner review. Obtain **independent qualified human security
   approval** of the JWT, session, RLS, pooler and CI boundary.
5. Record verified evidence, reviewer identity/decision and
   no-go exceptions here, then close [issue #29](https://github.com/ThunderKhan/axiom/issues/29)
   **only after** all release acceptance requirements pass.

**No release signoff:** The live Auth pass does not substitute for
hosted database parity, deploy/HTTPS checks, operational readiness or
human approval. Axiom M1 remains **INCOMPLETE VERIFICATION**.

## Requirements, implementation and actual evidence boundary

| ID | Implementation / test | Verified and missing |
|---|---|---|
| M1-AUTH-01 | FastAPI JwtVerifier, Supabase SSR login and bootstrap; test_auth.py, isolated workspace HTTP tests | Genuine Supabase login + API acceptance PASSED at 9e72d887; DB for this run was isolated PostgreSQL, not hosted |
| M1-AUTH-02 | App-user status, suspension and blocked bootstrap | Isolated PG tested; provider deletion/revocation NOT VERIFIED |
| M1-JWKS-01 | 300s bounded local JWKS, unknown kid/rotation/outage fixture tests | Genuine JWT/JWKS positive acceptance PASSED; live signing-key rotation/outage scenario NOT VERIFIED |
| M1-DB-01 | Alembic m1_0001_schema / m1_0002_rls, drift, repeat and refusal of unsafe downgrade | Isolated PG tested; managed Supabase DB NOT VERIFIED |
| M1-RLS-01 | Nonowner axiom_runtime, RLS USING/WITH CHECK, pool and transaction principal | Isolated PG tested; hosted pooler NOT VERIFIED |
| M1-RLS-02 | Explicit owner predicates under privileged migrator role | Isolated test_privileged_rls_bypass_is_not_app_authorization tested |
| M1-API-01 | Six FastAPI endpoints, status/DTO/404 equivalence tests | Live authenticated API/tenant denial PASSED with real Supabase identity + isolated PostgreSQL |
| M1-API-02 | 25h idempotency, concurrency/replay/restart/expiry and optimistic PATCH | Isolated PG tested; real uncertain network bounds NOT VERIFIED |
| M1-WEB-01 | Next.js auth and workspace picker, 12 prior anonymous Chromium tests | Three genuine provider browser/API test cases PASSED at 9e72d887, including A1/A2/B1 and sign-out flows |
| M1-WEB-02 | Browser subject-scoped preference and stale async generation | Live browser cross-account isolation / cross-tab signout PASSED in protected provider acceptance |
| M1-OPS-01 | Runtime/role configuration and separate protected provider harness | Protected provider workflow PASSED; no managed Axiom tables/roles/policies exist; hosted DB/pooler, deployed HTTPS and evaluator operation NOT VERIFIED |
| M1-CI-01 | Required Quality/Governance, Docker/browser smoke and protected provider gate | Quality #44850011295, Governance #44850011270 and provider #44850664291 ALL PASS on main 9e72d887 |

The new provider-only Playwright test obtains **two independent genuine
Supabase-authenticated browser sessions** and the user bearer actually sent
from the app to FastAPI (never logged). It verifies asymmetric JWT
headers and exact issuer/audience/role, creates A1/A2/B1 through the UI,
switches/reloads, lists/reads through FastAPI, probes foreign GET/PATCH,
equivalent missing/foreign 404, spoofed owner 422, stale PATCH 409,
idempotency replay/conflict 409, missing/malformed/tampered bearer 401,
deep-link denial, browser logout, keyboard/mobile and optional ordinary
evaluator login. Existing provider tests also cover slow A→B switching
and cross-tab logout. No live provider run is claimed by writing this test.

The existing scripts/run_db_integration.py exercises *actual* isolated
PostgreSQL 17 with separate admin/migration/least-privilege runtime roles,
Alembic upgrade/drift/negative downgrade, 7 RLS policies, USING/WITH CHECK,
absent/malformed principal, commit/rollback/pool reuse, concurrency,
privileged bypass plus independent application denial, constraints, and
idempotency. The test runner refuses non-loopback URLs and libpq overrides.
Local DB evidence does not establish managed Supabase pooler parity.

## The fail-closed acceptance gate

- python ci/m1_acceptance.py self-test: offline proof that absent
  credentials, mismatched SHA, unapproved test mode, changed issuer,
  same identity, missing/failed/skipped report and forged test counts
  do not pass. Also uses a disposable Git repository to prove clean
  checkouts pass while tracked edits and untracked executable inputs
  fail closed. Required by existing Quality / repository integrity job.
- python ci/m1_acceptance.py preflight: exact 40-hex commit, canonical
  HTTPS Supabase project/issuer/JWKS, publishable browser key, two
  ordinary distinct test accounts, explicit authorized nonproduction
  marker, loopback FastAPI and required DB. This is a prerequisite,
  **not evidence of successful provider interaction**.
- python ci/m1_acceptance.py run: rejects any tracked or untracked
  Git checkout changes before and after the provider suite (ignored
  local secrets/dependency installations are not enumerated), probes
  actual API database_verified readiness, runs all three named provider
  Playwright tests with no media/traces/HTML, captures credential-bearing
  output **in memory only**, rejects skipped/failed/unreported tests,
  and re-verifies exact SHA. Only sanitized PASS count/SHA are printed.
- .github/workflows/m1-security-acceptance.yml: MANUAL
  workflow_dispatch with owner-controlled, reviewer-protected
  m1-nonproduction GitHub Environment, explicit consent input,
  exact SHA, ephemeral real PostgreSQL and RLS suite, live provider
  browser acceptance and no token-bearing report uploads.
  **The manual protected workflow has been run successfully at the
  documented main SHA.** Its reviewer-rule configuration has not been
  independently audited and it is not established as a required
  status on main. Never add secrets to an unprotected environment.
  There is no pull_request trigger exposing secrets to unreviewed PR code.

A successful manual technical gate **still does not prove** hosted
PostgreSQL parity, deployed HTTPS/HSTS, global token revocation,
backup/restore, or qualified human release approval. Do not rename,
disable or bypass the original three required Quality/Governance jobs.
The dedicated test project now exists, but the gate stays BLOCKED
until genuine Auth identities, verified asymmetric signing, protected CI,
hosted database parity and qualified human security approval are documented.

## Dedicated zero-cost Supabase project — remaining operator setup

Project `axiom-m1-auth-test` (Mumbai, ap-south-1) is active in the
existing Free-tier organization, quoted at **$0/month**. The owner
explicitly authorized pausing `vsph-supabase`, which was verified
INACTIVE. VSPH-dependent services are unavailable until it is
restored; no database was deleted. Do not restore it without confirming
a free active-project slot or accidentally enabling a paid plan.

The available connectors do not support creating ordinary Auth users,
configuring hosted Auth signing/redirect settings, setting GitHub
Environment secrets/reviewers or dispatching the manual workflow.
An authorized operator must complete these steps:

1. Under the new Supabase project's **Authentication** settings, check
   that the active signing key is **ES256 or RS256**, verify its public
   `/auth/v1/.well-known/jwks.json` endpoint and allow both
   `http://127.0.0.1:3000/auth/callback` and
   `http://127.0.0.1:3101/auth/callback` as redirect URLs.
   Create two distinct, ordinary **confirmed** Auth test accounts
   via Supabase Auth (not direct inserts into `auth.users`).
2. In GitHub Settings → Environments, create `m1-nonproduction`
   with required independent reviewers. Set environment variables
   `M1_NONPRODUCTION_SUPABASE_URL`,
   `M1_NONPRODUCTION_ISSUER` and
   `M1_NONPRODUCTION_JWKS_URL` for the same Axiom test project.
   The last two are the Supabase origin plus `/auth/v1` and
   `/auth/v1/.well-known/jwks.json` respectively.
3. Set environment secrets `M1_NONPRODUCTION_PUBLISHABLE_KEY`,
   `M1_NONPRODUCTION_EMAIL_A`, `M1_NONPRODUCTION_PASSWORD_A`,
   `M1_NONPRODUCTION_EMAIL_B`, `M1_NONPRODUCTION_PASSWORD_B`.
   Optional evaluator email and password must be paired. Never
   commit credentials or paste them in issues, logs or chat.
4. From the repository Actions tab, manually dispatch **M1
   real-provider security acceptance** against the exact reviewed
   40-character `main` SHA and explicitly confirm nonproduction
   authorization. Obtain required environment approval.
5. Save redacted passing evidence and separately verify hosted
   nonproduction Supabase database/migration/RLS/pooler parity;
   the workflow's PostgreSQL database is an isolated CI container.
   Obtain qualified human security signoff before M1 acceptance.

Real-provider acceptance passed on 21 November 2026. No hosted application
schema migration or hosted pooler/RLS acceptance test has yet run.

## Windows PowerShell — reproducible local testing

**Windows testing not run here; existing GitHub CI uses Linux.**
Prerequisites: Windows, VS Code, Git, Node 22.16.0+ but below 23,
npm 10.9.2, Python 3.12, uv 0.10.0 in CI, Docker Desktop with WSL2,
Docker Compose v2, local PostgreSQL 17-alpine test image, pinned
Playwright 1.65.1. Check tools using node --version, npm --version,
python --version, uv --version, docker version, docker compose version.

### Terminal A — feature checkout, test database and migrations

Existing clone:

    cd D:\Projects\axiom
    git status
    git fetch origin
    git switch main
    git pull --ff-only origin main
    docker compose -f infra/compose.db-test.yml up -d --wait
    cd services/api
    uv sync --locked --all-groups
    $env:AXIOM_TEST_ADMIN_DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/axiom_test"
    $env:AXIOM_MIGRATION_DATABASE_URL = "postgresql://axiom_migrator@127.0.0.1:55432/axiom_test"
    $env:AXIOM_TEST_RUNTIME_DATABASE_URL = "postgresql://axiom_runtime@127.0.0.1:55432/axiom_test"
    uv run --frozen python scripts/run_db_integration.py

Fresh clone: git clone https://github.com/ThunderKhan/axiom.git,
cd axiom; its default branch is main. Preserve local changes before
switching branches; do not reset or force discard uncommitted work.

### Terminal B — FastAPI with normal runtime role ONLY

From repo root in a **new PowerShell** terminal:

    cd services/api
    uv sync --locked --all-groups
    Remove-Item Env:AXIOM_TEST_ADMIN_DATABASE_URL -ErrorAction SilentlyContinue
    Remove-Item Env:AXIOM_MIGRATION_DATABASE_URL -ErrorAction SilentlyContinue
    $env:AXIOM_DATABASE_URL = "postgresql://axiom_runtime@127.0.0.1:55432/axiom_test"
    $env:AXIOM_DATABASE_REQUIRED = "true"
    $env:AXIOM_CORS_ORIGINS = "http://127.0.0.1:3000,http://127.0.0.1:3101"
    $env:AXIOM_AUTH_ISSUER = Read-Host "Authorized project issuer (https://PROJECT.supabase.co/auth/v1)"
    $env:AXIOM_AUTH_AUDIENCE = "authenticated"
    $env:AXIOM_AUTH_JWKS_URL = "$env:AXIOM_AUTH_ISSUER/.well-known/jwks.json"
    uv run --frozen python -m app.api

From another terminal:

    Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/live
    Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready

The latter must say database_verified. The user JWT must actually
pass independent FastAPI signature verification. Never configure
service_role, privileged migration credentials or legacy HS256 fallback
for the ordinary API.

### Terminal C — Next.js with public nonproduction config

    cd apps/web
    npm ci
    Copy-Item .env.example .env.local
    notepad .env.local
    npm run dev

In ignored .env.local put ONLY NEXT_PUBLIC_SUPABASE_URL,
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY (sb_publishable_ prefix), and
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000. No passwords,
service keys or database secrets. The approved test Supabase Auth
callback allowlist must include BOTH local callbacks on ports 3000
and 3101 ending /auth/callback. Restart Next.js after any env change.

### Terminal D — private real-provider acceptance (authorized ONLY)

From repo root, enter two distinct ordinary Supabase test accounts
through private PowerShell prompts (never shell-history literals):

    $env:NEXT_PUBLIC_SUPABASE_URL = Read-Host "Authorized test Supabase HTTPS origin"
    $env:NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY = Read-Host "Public publishable key"
    $env:NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000"
    $env:M1_ACCEPTANCE_ISSUER = "$env:NEXT_PUBLIC_SUPABASE_URL/auth/v1"
    $env:AXIOM_AUTH_ISSUER = $env:M1_ACCEPTANCE_ISSUER
    $env:AXIOM_AUTH_AUDIENCE = "authenticated"
    $env:AXIOM_AUTH_JWKS_URL = "$env:M1_ACCEPTANCE_ISSUER/.well-known/jwks.json"
    $env:AXIOM_DATABASE_REQUIRED = "true"
    $env:M1_ACCEPTANCE_HEAD_SHA = (git rev-parse HEAD).Trim()
    $env:E2E_WORKSPACE_API_READY = "1"
    $env:E2E_M1_ACCEPTANCE = "1"
    $env:E2E_SUPABASE_EMAIL = Read-Host "Ordinary user A email"
    $env:E2E_SUPABASE_SECOND_EMAIL = Read-Host "Ordinary user B email"
    $env:E2E_SUPABASE_PASSWORD = [System.Net.NetworkCredential]::new("", (Read-Host "User A password" -AsSecureString)).Password
    $env:E2E_SUPABASE_SECOND_PASSWORD = [System.Net.NetworkCredential]::new("", (Read-Host "User B password" -AsSecureString)).Password

ONLY after verifying actual approval:

    $env:M1_ACCEPTANCE_NONPRODUCTION = "I_CONFIRM_NONPRODUCTION"
    python ci/m1_acceptance.py self-test
    python ci/m1_acceptance.py preflight
    python ci/m1_acceptance.py run

Optional evaluator identity: set both E2E_SUPABASE_EVALUATOR_EMAIL and
E2E_SUPABASE_EVALUATOR_PASSWORD privately. It uses the same ordinary
login; never elevate evaluator roles. Tests run a separate Chromium
on port 3101 without traces, screenshots, video or retained reports.
The runner captures test output privately to avoid credential leaks.
A failed command means **NOT VERIFIED**; never alter the test reporter
to fake results or disclose tokens to debug.

Manual browser smoke (localhost:3000): login A, create A1/A2, switch,
reload and confirm A2; sign out. Login B in another session, create
B1, try /app?workspace=A1_UUID and verify no A private data.
The M1 provider test performs the stronger direct API/owner/foreign
GET/PATCH/401/404/409/422 probes using separate genuine user tokens.

### Negative and failure tests

Missing/malformed bearer requests must return 401, not a success:

    try { Invoke-RestMethod http://127.0.0.1:8000/api/v1/me -ErrorAction Stop } catch { "Missing token denied" }
    try { Invoke-RestMethod http://127.0.0.1:8000/api/v1/me -Headers @{ Authorization = "Bearer malformed" } -ErrorAction Stop } catch { "Malformed token denied" }

These catch snippets do not prove an exact status; pytest and the M1
provider test assert the actual 401 and safe code. Wrong issuer,
audience, key, algorithm, expiry, unknown kid, disabled account,
foreign owner, stale version, replay, invalid cursor, DB migration
drift and pooled runtime RLS are exercised by the existing controlled
backend tests. Do not paste real user JWTs into PowerShell history.
For isolated DB outage/recovery ONLY use disposable compose:

    docker compose -f infra/compose.db-test.yml stop postgres-test
    docker compose -f infra/compose.db-test.yml start postgres-test
    docker compose -f infra/compose.db-test.yml up -d --wait

Re-run isolated migrations if the tmpfs service has lost data. This is
NOT a production backup/restore rehearsal or approved provider outage.

### Full quality suite

From apps/web:

    npm run lint
    npm run format:check
    npm run typecheck
    npm run test:unit
    npm run test:smoke
    npm run test:ci
    npm run build
    npm run audit

From services/api:

    uv run --frozen python scripts/check_style.py
    uv run --frozen mypy app
    uv run --frozen pytest -q --junitxml=test-results/junit.xml
    uv build --wheel --out-dir dist
    uv run --frozen pip-audit --progress-spinner off

From repository root on Linux/WSL2 (quality_gate uses fcntl):

    python ci/quality_gate.py self-test
    python ci/quality_gate.py repository
    python ci/quality_gate.py application
    python ci/docker_smoke.py
    python ci/integrated_smoke.py
    python ci/m1_acceptance.py self-test

The PostgreSQL integration uses Terminal A's explicit test URLs.
Quality/Governance CI must pass at exact PR SHA. The separate manual
M1 provider workflow cannot be declared passed without authorized
provider credentials, actual execution and independent security review.

### Deferred operational verification

Before signoff separately verify selected project signing/JWKS
and refresh semantics, managed runtime/migration grants and pooler mode,
account suspension/provider deletion reconciliation, emergency
operator denial/rotation, real HTTPS/Secure/SameSite/cookies,
HSTS/CSP/XSS/CSRF/CORS, backups/restore, test evaluator retirement,
redacted logs, and staged capacity tests under ADR-010. A 300-second
local JWKS age limit does not guarantee global JWT revocation.
Worker business ingress and future MCP OAuth are not implemented here;
do not invent tests for nonexistent routes.

### Shutdown and return to main

Stop native API and web with Ctrl+C; from repo root:

    docker compose -f infra/compose.db-test.yml down

Do not delete volumes, hosted data or accounts without permission.
Clear test passwords from current PowerShell process:

    "E2E_SUPABASE_PASSWORD","E2E_SUPABASE_SECOND_PASSWORD","E2E_SUPABASE_EVALUATOR_PASSWORD" | ForEach-Object { Remove-Item "Env:$_" -ErrorAction SilentlyContinue }

After preserving local work:

    git status
    git switch main
    git pull --ff-only origin main

**Quick-start sequence:** Terminal A fetch branch, Docker up, run
isolated migration/RLS suite. Terminal B run FastAPI with the runtime
role/authorized issuer. Terminal C npm ci and start Next.js. Terminal D
privately set two test users, run M1 self-test, preflight and real provider
run; run quality checks; shut down services. Do NOT merge or mark M1
accepted merely because local-only checks pass.

## Final disposition

**M1 ACCEPTANCE BLOCKED / INCOMPLETE VERIFICATION:** All three required
[Quality](https://github.com/ThunderKhan/axiom/actions/runs/44850011295),
[Governance](https://github.com/ThunderKhan/axiom/actions/runs/44850011270)
and [real-provider acceptance](https://github.com/ThunderKhan/axiom/actions/runs/44850664291)
workflows **PASS** at `9e72d8872d48c7aae54aebcf8abe7fc1ca465f6a`.
However, the managed Supabase project has **no Axiom application schema,
runtime roles, migrations or RLS policies**, and hosted pooler parity
has not been exercised. Human security review and final explicit approval
are also outstanding. Issue #29 remains OPEN; do not claim deployed,
hosted database parity or release readiness. No production, paid service
or hosted database mutation was performed by the 21 November audit.
