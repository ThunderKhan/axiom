# Axiom Python API and worker foundation — issue #9

This package delivers **runtime packaging and operational health only**, not
Supabase authorization, a database connection, research, AI, a job queue or durable
worker recovery. Both processes use one Python package and Docker image.

## Runtime and dependency contract

- Python **3.12** is tested in CI; `pyproject.toml` supports 3.12–3.13.
- `uv==0.10.0`, pinned direct runtime/development dependencies and a
  committed, hash-bearing `uv.lock`. Only a lockfile-based sync is supported.
- The Python base image is `python:3.12.12-slim-bookworm` pinned to its reviewed
  OCI multi-platform SHA-256 digest in the Dockerfile.
- Runtime dependencies: FastAPI 0.128.2 (MIT), Uvicorn 0.48.0 (BSD-3-Clause),
  Pydantic Settings 2.14.1 (MIT). Tooling: uv 0.10.0 (MIT or Apache-2.0);
  pytest, Ruff, mypy and pip-audit are locked in the developer group. Consult
  upstream licenses and transitive package metadata before redistribution.

## Windows PowerShell: native API and worker

From the repository root:

```powershell
py -3.12 --version
uv --version
cd services/api
uv sync --frozen --all-groups
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

## Configuration

Settings are typed and read from `AXIOM_*` environment variables.
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
uv sync --frozen --all-groups
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
