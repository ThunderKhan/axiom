# Axiom

**Axiom** is an evidence-grounded intelligence product for startup founders: discover public customer-demand signals, investigate competitors, evaluate founder/product fit, explore scenarios, and keep relevant opportunities organized.

**Project status:** Product and architecture specifications exist. The first status-only Next.js frontend foundation is available in `apps/web` (issue #8); a limited FastAPI API/idle-worker foundation is available in `services/api` (issue #9). Authentication, workspaces, research, CRM, durable job processing and production deployment remain **unimplemented or unverified**. A documented feature is not an implemented feature, and example research is not live-source evidence.

## Canonical developer setup — Milestone 0 foundation

**Tested foundation only:** a status-only Next.js page, FastAPI health endpoints and a
bounded idle worker. This setup does **not** enable login, database access,
research, durable background jobs, production deployment or user workflows.

### Prerequisites

- **Node.js 22.16.0** (the web package requires `>=22.16.0 <23`) and
  **npm 10.9.2**; lockfile at `apps/web/package-lock.json`.
- **Python 3.12** (CI runtime; the backend also permits 3.13) and
  **uv 0.10.0**; lockfile at `services/api/uv.lock`.
- Docker Desktop with Linux containers / WSL2 on Windows, or a working
  Linux Docker Engine and **Docker Compose v2** supporting `up --wait`.
- Git; Chromium downloaded with `npx playwright install chromium` from `apps/web`.
  An internet connection is required for first-time package/image/browser installs.

Check versions: `node --version`, `npm --version`, `python --version`,
`uv --version`, `docker version` and `docker compose version`.
PowerShell users can check the requested interpreter with `py -3.12 --version`.
Use your Node version manager to select Node 22; do not silently run an unsupported
Node 24 installation.

### Clean checkout and locked installs

From the repository root:

```powershell
cd apps/web
npm ci --no-audit --no-fund
Copy-Item .env.example .env.local
npx playwright install chromium
cd ../services/api
uv sync --locked --all-groups
cd ../..
```

On Linux, use `cp apps/web/.env.example apps/web/.env.local` instead of
`Copy-Item`. The copied file is gitignored. Never place real credentials into
`.env.local` or commit environment files.

### Start frontend, API and worker independently

**Terminal 1 — native Next.js**, from the repository root:

```powershell
cd apps/web
npm run dev
```

Visit `http://127.0.0.1:3000`. It shows the truthful frontend foundation,
not an integrated product. Its public metadata records the configured API base
origin; it does **not** make a backend call on normal page render.

**Terminal 2 — Compose API**, from the repository root:

```powershell
docker compose -f infra/compose.dev.yml config --quiet
docker compose -f infra/compose.dev.yml up -d --build --wait api
docker compose -f infra/compose.dev.yml ps
docker compose -f infra/compose.dev.yml logs --tail=100 api
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/live
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready
```

**Terminal 3 — separate worker process**, from the repository root:

```powershell
docker compose -f infra/compose.dev.yml run --rm --no-deps -e AXIOM_WORKER_RUN_SECONDS=2 worker
```

The worker must print `axiom_worker_ready mode=idle_only queue=not_implemented`
and `axiom_worker_stopped`. It executes no business jobs or durable leases.
No worker network port is published.

### Environment and trust boundary

| Setting | Context | Safe development behavior |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Browser-readable web origin | `http://127.0.0.1:8000` in `apps/web/.env.example`; exact origin, never a secret or a path |
| `AXIOM_CORS_ORIGINS` | API-only | Default `http://127.0.0.1:3000`; explicit comma-separated exact origins, no wildcard or credentialed CORS; HTTP permitted only on loopback |
| `AXIOM_BIND_HOST`, `AXIOM_PORT` | Backend runtime | Native defaults `127.0.0.1:8000`; Compose binds container internally and publishes host port 8000 only on loopback |
| `AXIOM_DATABASE_REQUIRED`, `AXIOM_DATABASE_URL` | Server-only, optional/unimplemented | No database URL is required; setting a DB URL yields HTTP 503 `database_not_verified`; do not set production credentials |
| `AXIOM_WORKER_RUN_SECONDS`, `AXIOM_WORKER_IDLE_SECONDS` | Worker-only behavior | Bounded, finite idle lifecycle; not a production processing loop |

The frontend and API use **different ports**. A public API URL is **not**
permission to expose database/provider keys, user data, or Supabase service
credentials. No privileged `NEXT_PUBLIC_*` keys are defined. API CORS allows
specific origins for health-only GET; browser-side auth and cookies do not exist.

### Real integrated M0 smoke (self-contained after installs)

Stop manual web/API processes on ports **3000/8000/3200** before the smoke run.
From the repository root, after installing both packages and Chromium:

```powershell
python ci/integrated_smoke.py
```

The harness independently builds/starts the API with Compose using an isolated
project name, starts/observes the idle worker, launches native Next.js at
`http://127.0.0.1:3200`, and runs real headless Chromium to fetch FastAPI from
that browser origin. It checks public API metadata, CORS preflight and rejected
origins, API unavailable/wrong address after deliberate API shutdown, API
recovery, worker no-ingress, and process/container cleanup. It does not mock
network startup or run against real provider credentials. On success, prints
`PASS: M0 real Chromium + native web + container API/worker + CORS + negative outage + cleanup`
and exits **0**; otherwise exits nonzero with a diagnostic. Temporary Next.js
logs are printed on failure and deleted during cleanup. The harness starts its
own services; **do not** leave your manual API running on port 8000.

### Quality checks

```powershell
cd apps/web
npm run check:style
npm run typecheck
npm run test:ci
npm run build
npm run audit
cd ../services/api
uv run --frozen python scripts/check_style.py
uv run --frozen mypy app
uv run --frozen pytest -q --junitxml=test-results/junit.xml
uv build --wheel --out-dir dist
uv run --frozen pip-audit --progress-spinner off
cd ../..
python ci/docker_smoke.py
python ci/integrated_smoke.py
```

After both installs, the full repository gate is
`python ci/quality_gate.py self-test`, `python ci/quality_gate.py repository`
and `python ci/quality_gate.py application` **on Linux/WSL2**. It uses Unix
`fcntl` and does not run under native Windows Python; the required GitHub
Actions Linux jobs are the independently verified equivalent. Do not reuse
stale JUnit reports; CI removes and validates fresh output.

### Safe shutdown, failure behavior and troubleshooting

- Stop native Next.js with `Ctrl+C`. Stop Compose with
  `docker compose -f infra/compose.dev.yml down` from the repository root.
  This removes Compose containers and network, not volumes or committed data.
- If a Docker service fails, inspect
  `docker compose -f infra/compose.dev.yml logs --tail=100 api` and Docker
  Desktop's Linux-engine status. `up -d --build --wait api` avoids querying
  the API before its healthcheck passes.
- If a frontend request cannot reach the API, check the public URL in
  `apps/web/.env.local`, backend port 8000, and `AXIOM_CORS_ORIGINS` (default
  port 3000; the M0 harness explicitly configures its port 3200).
  Restart Next.js after changing public environment variables.
- If port 8000 or 3200 is occupied, **stop the existing service** rather than
  killing unidentified processes. If the smoke harness fails, inspect its
  error/logs; it attempts bounded cleanup and reports cleanup failures.
- A missing lockfile, incompatible Python/Node version, or missing Chromium
  cannot be bypassed by a stale report. Reinstall with `npm ci`,
  `uv sync --locked --all-groups`, and `npx playwright install chromium`.
- A worker that reports invalid `AXIOM_*` settings or exits unexpectedly
  must not be treated as a completed job.
- On Windows, `uv run` manages the Python environment without activating
  `.venv`; PowerShell activation policy changes are unnecessary.

### Intended deployment mapping (not deployed)

- **Vercel candidate:** Next.js project root `apps/web`, native build.
- **Railway candidate API:** source/build root `services/api`, shared backend
  Docker image, start command `python -m app.api`.
- **Railway candidate worker:** same `services/api` Docker image, separate
  start command `python -m app.worker`, without public ingress. This is a
  bounded **idle foundation**, not a durable production worker.

No Vercel/Railway services, database, billing, TLS, OAuth, queue, migrations,
recovery or capacity test are provisioned or verified by M0. Actual provider
selection and secret management require separate approval.

## Project documentation

The [documentation index](docs/01-INDEX.md) is the canonical starting point. It links the approved [PRD](docs/02-PRD.md), [MVP](docs/03-MVP.md), [system architecture](docs/05-SYSTEM-ARCHITECTURE.md), [design direction](docs/13-DESIGN.md), [testing strategy](docs/14-TESTING-STRATEGY.md) and [decision register](docs/DECISIONS.md).

## Engineering workflow

Read [AGENTS.md](AGENTS.md) and [ENGINEERING.md](ENGINEERING.md) before changes, and consult [CONTRIBUTING.md](CONTRIBUTING.md) for issue labels, PR expectations, tests, CodeRabbit, and review. Use [SECURITY.md](SECURITY.md) for private vulnerability reports.

Axiom's engineering goals include correctness-first CI, reproducible test evidence, safe workspace isolation, lawful and attributed source ingestion, and a transparent distinction between AI-generated interpretation and observed facts.

**Frontend commands:** See [apps/web/README.md](apps/web/README.md) for the actual npm clean-install, development, build, test and audit commands. The web package displays foundation status only. **Backend commands:** See [services/api/README.md](services/api/README.md) for the real FastAPI/worker, locked dependency, test and Docker commands. Live integrations are not implemented and no deployment is claimed verified.

## Review and release

Changes should be reviewed through pull requests with CI and human review. CodeRabbit provides supplementary automated review, not merge authorization. The November 26 fellowship deliverable and staged 100/250/500-active-founder validation are documented separately; no capacity or provider access is claimed verified without actual test evidence.

**Do not commit credentials, production secrets, private founder data, or customer records.**

**Backend foundation (Milestone 0.2):** `services/api` now contains a real
FastAPI liveness/readiness interface, typed configuration and independent bounded
idle worker, with one non-root Docker image and `infra/compose.dev.yml`.
It does **not** connect Supabase, run production jobs, or implement product APIs.
See [backend setup and tests](services/api/README.md).
