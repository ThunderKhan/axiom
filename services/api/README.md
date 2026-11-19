# Axiom Python API, worker and M1 database foundation

This package delivers **runtime packaging, operational health and a scoped
Supabase JWT identity-verification dependency**. The provider integration is not
yet verified against a real Supabase test project; database-backed account and
workspace persistence primitives are available only in the backend, but M1
application-user/workspace HTTP endpoints, live provider verification, research
and worker job recovery remain unimplemented. Both processes use one Python
package and Docker image.

## Runtime and dependency contract

- Python **3.12** is tested in CI; `pyproject.toml` supports 3.12–3.13.
- `uv==0.10.0`, pinned direct runtime/development dependencies (including patched Starlette 1.10.0 and pytest 9.0.3) and a
  committed, hash-bearing `uv.lock`. Install and Docker builds use `--locked` to reject a stale lockfile; subsequent `uv run --frozen` commands use the previously validated environment.
- The Python base image is `python:3.12.12-slim-bookworm` pinned to its reviewed
  OCI multi-platform SHA-256 digest in the Dockerfile.
- Runtime dependencies: FastAPI 0.165.0 (MIT), Uvicorn 0.48.0 (BSD-3-Clause),
  Pydantic Settings 2.14.2 (MIT). Tooling: uv 0.10.0 (MIT or Apache-2.0);
  pytest, Ruff, mypy and pip-audit are locked in the developer group. Consult
  upstream licenses and transitive package metadata before redistribution.

## Windows PowerShell: native API and worker

From the repository root:

```powershell
py -3.12 --version
uv --version
cd services/api
uv sync --locked --all-groups
uv run --frozen python -m app.api
```

In a second PowerShell terminal, from `services/api`:

```powershell
uv run --frozen python -m app.worker
```

The API binds `127.0.0.1:8000` by default. Visit:

- `http://127.0.0.1:8000/api/v1/health/live` — HTTP 200,
  `{"status":"alive","service":"axiom-api"}`
- `http://127.0.0.1:8000/api/v1/health/ready` — HTTP 200,
  `{"status":"ready","scope":"foundation_only","dependencies":"none_configured"}`
- `http://127.0.0.1:8000/docs` — FastAPI OpenAPI documentation for **health only**

If `AXIOM_DATABASE_URL` is configured, readiness deliberately returns **HTTP
503**, `{"status":"not_ready","scope":"foundation_only","dependencies":"database_not_verified"}`.
This is not a database connectivity test. With `AXIOM_DATABASE_REQUIRED=true`
and no URL, configuration validation **fails startup**. The liveness route reports
the API process, not external dependency availability.

The worker prints `axiom_worker_ready mode=idle_only queue=not_implemented`,
waits for a bounded `AXIOM_WORKER_RUN_SECONDS` (default 30), then prints
`axiom_worker_stopped`. It handles SIGINT/SIGTERM on POSIX; on Windows,
`Ctrl+C` stops the terminal-run process. No jobs are claimed or processed, and
no worker listener is opened. It is **not** a production long-lived worker.

The [canonical developer guide](../../README.md#canonical-developer-setup--milestone-0-foundation)
explains how to run the real integrated browser/API/worker smoke and its cleanup.

## Configuration

Settings are typed and read from `AXIOM_*` environment variables.
`AXIOM_CORS_ORIGINS` defaults to the exact development origin
`http://127.0.0.1:3000` (or may be set explicitly to a comma-separated
list of exact HTTP(S) origins). Plain HTTP is restricted to loopback;
credentialed and wildcard CORS are not enabled. A browser from an unapproved
origin does not receive CORS authorization. For the integrated smoke, the harness
configures its frontend origin `http://127.0.0.1:3200` explicitly.
`AXIOM_BIND_HOST` must be a literal IP address (default `127.0.0.1` native,
`0.0.0.0` in the Docker image). `AXIOM_PORT` must be 1–65535 (default 8000).
`AXIOM_DATABASE_URL` is optional and secret; configuring it **does not connect**
to a database at this milestone. `AXIOM_DATABASE_REQUIRED` defaults false.
`AXIOM_WORKER_RUN_SECONDS` must be 0.1–300 and idle seconds 0.05–5.
Invalid values fail startup with a redacted message. No actual secret is needed.

`.env.example` lists safe configuration names. No live `.env` file is loaded by
default; set environment variables in your terminal or your private secret store.

## Required quality checks (from `services/api`)

```powershell
uv sync --locked --all-groups
uv run --frozen python scripts/check_style.py
uv run --frozen mypy app
uv run --frozen pytest -q --junitxml=test-results/junit.xml
uv build --wheel --out-dir dist
uv run --frozen pip-audit --progress-spinner off
```

## Docker and Compose (from repository root)

```powershell
docker build -f services/api/Dockerfile -t axiom-api:dev services/api
docker compose -f infra/compose.dev.yml config --quiet
docker compose -f infra/compose.dev.yml up -d --build api
docker compose -f infra/compose.dev.yml run --rm --no-deps -e AXIOM_WORKER_RUN_SECONDS=1 worker
docker compose -f infra/compose.dev.yml ps
docker compose -f infra/compose.dev.yml logs api
docker compose -f infra/compose.dev.yml logs worker
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/live
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready
docker compose -f infra/compose.dev.yml down
```

The worker intentionally stops after its bounded interval; inspect the
`docker compose run` output for its startup and shutdown markers. The API
publishes **only** port 8000 bound to `127.0.0.1`, and the worker publishes
no port. CI performs actual Docker smoke tests through
`python ci/docker_smoke.py`. Docker Desktop with Linux containers and WSL2
integration enabled is recommended on Windows.

Production hosting, paid services, credentials, database migrations, queue
durability/recovery and provider integrations are **not implemented or verified**.

## Issue #15 — Supabase JWT principal boundary (M1 D1–D3, I3)

`app.auth` exposes a reusable `get_verified_principal` FastAPI dependency and a
`VerifiedPrincipal` whose `user_id` is the validated Supabase JWT `sub` UUID.
This identity is **not** an active application user or workspace owner. It must
be followed by application-user status and object authorization in later issues.
No fake `/api/v1/me` or bootstrap response is implemented here: both require
app-user database state owned by #16/#18. Tests attach a private test-only route
at runtime to exercise the dependency end-to-end via HTTP.

Configure all three non-secret test-project values in the backend environment:
`AXIOM_AUTH_ISSUER=https://<project-ref>.supabase.co/auth/v1`,
`AXIOM_AUTH_AUDIENCE=authenticated`,
`AXIOM_AUTH_JWKS_URL=https://<project-ref>.supabase.co/auth/v1/.well-known/jwks.json`.
The JWKS URL must exactly match the configured project issuer, and
`AXIOM_JWKS_CACHE_MAX_SECONDS` is bounded between 1 and 300 (default 300).
Only RS256/ES256 signed ordinary authenticated-user tokens are eligible;
HS256, service-role, anon, unsigned, foreign issuer/audience and unknown keys
are rejected. The verifier uses the configured HTTPS JWKS, bounded response
size/network timeout, a 300-second-or-less cache age, a single-flight refresh
lock, a five-second backoff after failed JWKS fetches (while never using stale
keys), and a fixed 30-second cooldown on actual unknown-key refresh attempts.
Failed key retrieval returns a safe retryable 503; rejected unknown signing-key
requests cannot perpetually postpone a later successful key rotation. `JwtVerifier.invalidate()`
provides process-local operator invalidation to be wired to an authenticated
operational control in later deployment work; no public invalidation route exists.

On missing or invalid credentials the protected dependency returns 401
`AUTH_REQUIRED`; unavailable required signing metadata returns 503
`AUTH_UNAVAILABLE`, with safe request-ID error envelopes. When Auth is
configured but still lacks provider and app-user validation, foundation
readiness remains truthful (`503 auth_not_verified`); unconfigured health-only
M0 behavior stays unchanged. No bearer or secret is logged or put in errors.
A still-valid JWT can outlive provider logout or refresh-session revocation;
trusted signature verification alone cannot guarantee immediate revocation.
Supabase edge caches can outlive the local 300-second cache; this is **not** a
global five-minute key-revocation guarantee.

Run isolated fixture-based checks from `services/api` using
`uv run --frozen pytest -q tests/test_auth.py`. Then run the existing mandatory
repository checks as described above and in `ci/README.md`. Provider-backed
authentication requires a separately authorized nonproduction Supabase project
with asymmetric Auth signing and a real normal-user access token, supplied
privately and never pasted into repository, logs, screenshots or PR text.

## M1.3 — approved database foundation (Issue #16)

This package additionally contains **three owner-approved M1 SQLAlchemy models** in
`app/models.py`, a bounded runtime engine/verified-principal transaction context in
`app/database.py`, and private backend-only bootstrap/list/create persistence
primitives in `app/workspace_store.py`. **No `/me` or `/workspaces` REST
endpoints have been implemented**; those belong to Issue #18. No background job,
CRM, research schema, browser Supabase table access, or live provider deployment
is part of this change.

**Versioned migrations:** `m1_0001_schema` creates the private `axiom` schema,
`app_users`, `workspaces`, `workspace_create_idempotency`, owner foreign keys,
name/status/version checks and the ordered owner-list index.
`m1_0002_rls` grants a separate `axiom_runtime` role only required SELECT,
INSERT-column, and UPDATE-column capabilities, establishes reviewed
`USING`/`WITH CHECK` RLS, and publishes a SECURITY INVOKER transaction-local
subject function. The role owning the tables (`axiom_migrator`) is **not**
a valid API connection: it can bypass RLS by ownership. Explicit server-side
authorization must always precede operations even if privileged credentials
are used by a later operator.

- Runtime secret: `AXIOM_DATABASE_URL` (only the least-privileged application role).
- Migration-only secret: `AXIOM_MIGRATION_DATABASE_URL`. Never expose this to
  API/worker processes or store it under public Next.js variables.
- Local disposable-only variables: `AXIOM_TEST_ADMIN_DATABASE_URL` and
  `AXIOM_TEST_RUNTIME_DATABASE_URL`. These are **not production settings**.
- Schema is private (`axiom`) rather than Supabase's default Data API exposed
  `public` schema. Required migrations are **explicit**, never import/startup/request
  side effects. Runtime SQLAlchemy sessions use transaction-local
  `set_config('app.current_user_id', <verified UUID>, true)` and are rolled back/
  closed/returned to the pool. RLS is defense in depth; custom settings do
  not protect against arbitrary injected SQL.
- Successful committed workspace-create replay is retained **at least 24 hours**
  by a DB CHECK. Replay is conservative while the record still exists. After a
  deliberate operator purge of an expired record, a very late retry may create a
  second workspace; the pending client retry/deadline contract belongs to #19.
  There is **no scheduled cleanup** in this scope. A duplicate name with a
  different key remains a new workspace.
- Owner suspension/deprovisioning is operator-controlled and is never reset by
  ordinary bootstrap. No public or runtime DELETE/owner-transfer operation.

### Isolated Windows PowerShell verification

From the repository root in Docker Desktop/PowerShell, start **only** the
disposable PostgreSQL 17 service. The service binds **127.0.0.1:55432** and
stores its test data in container tmpfs (no durable named volume). It deliberately
uses a *trust-authenticated test-only* loopback port: **never point this setup
at a production, shared-network or customer database**.

```powershell
docker compose -f infra/compose.db-test.yml up -d --wait
docker compose -f infra/compose.db-test.yml ps
cd services/api
uv sync --locked --all-groups
$env:AXIOM_TEST_ADMIN_DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/axiom_test"
$env:AXIOM_MIGRATION_DATABASE_URL = "postgresql://axiom_migrator@127.0.0.1:55432/axiom_test"
$env:AXIOM_TEST_RUNTIME_DATABASE_URL = "postgresql://axiom_runtime@127.0.0.1:55432/axiom_test"
uv run --frozen alembic history
uv run --frozen python scripts/run_db_integration.py
```

The runner refuses any other database, host or port. It verifies the additive
revision path (clean/upgrade/repeat), Alembic metadata drift (including a
deliberately injected and safely removed test-only extra index), tests actual
non-owner PostgreSQL RLS, transaction-local identity reset, concurrent
bootstrap/create, role privileges, constraints, and safe readiness. Re-running
it against the *same isolated test database* is supported. Do not interpret
these tests as verified Supabase-hosted role or pooler behavior.

To exercise the API with this local database from `services/api`:

```powershell
$env:AXIOM_DATABASE_URL = $env:AXIOM_TEST_RUNTIME_DATABASE_URL
$env:AXIOM_DATABASE_REQUIRED = "true"
uv run --frozen python -m app.api
```

In another PowerShell terminal, inspect
`http://127.0.0.1:8000/api/v1/health/live` (public liveness) and
`http://127.0.0.1:8000/api/v1/health/ready` (real DB revision/role/RLS checks).
A properly migrated isolated database should return `database_verified`;
unavailable/incompatible/privileged configurations return HTTP 503 without
credentials. This **does not prove real Supabase Auth**.

From `services/api`, run the existing Python quality checks:
`uv run --frozen python scripts/check_style.py`,
`uv run --frozen mypy app`,
`uv run --frozen pytest -q`, and
`uv run --frozen pip-audit --progress-spinner off`.
From repo root, preserve the existing `python ci/docker_smoke.py` and
`python ci/integrated_smoke.py` checks. Stop the API with Ctrl+C, then from
the repository root use `docker compose -f infra/compose.db-test.yml down`
to stop the isolated test service (its tmpfs contents are intentionally ephemeral).

### Forward recovery and provider evidence

Migrations are transactional PostgreSQL DDL; `downgrade` deliberately refuses
destructive rollback or disabling RLS. Test the migration on an isolated copy
and use a **reviewed forward-fix** if a database is incompatible. Before any
deployment migration, separately approve backup, account/role provisioning,
connection pool mode, TLS and rollback/recovery operation. Current real
Supabase issuer, JWKS signing mode, runtime-role/grant feasibility, and shared
pooler behavior are **not verified** by these local tests.
