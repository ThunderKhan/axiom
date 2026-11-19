# Axiom Python API and worker foundation — issue #9

This package delivers **runtime packaging, operational health and a scoped
Supabase JWT identity-verification dependency**. The provider integration is not
yet verified against a real Supabase test project; application-user persistence,
workspace authorization, database connections, research and worker job recovery
are not implemented. Both processes use one Python package and Docker image.

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
lock and bounded unknown-key refresh attempts. `JwtVerifier.invalidate()`
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
