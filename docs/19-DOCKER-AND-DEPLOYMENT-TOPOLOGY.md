# Axiom — Monorepo, Docker and Deployment Boundaries

**Status:** Approved implementation setup (18 November 2026); **not yet implemented or deployed**. This document refines [System Architecture](05-SYSTEM-ARCHITECTURE.md), [TRD](06-TRD.md), [Implementation Roadmap](16-IMPLEMENTATION-ROADMAP.md), and the [managed-hosting strategy](decisions/008-managed-hosting-and-worker.md). The owner's selection is to include Docker and keep independently deployable frontend/backend folders. **Vercel and Railway are intended candidates, not provisioned or billing-approved services.**

## 1. One repository, distinct deployment roots

```text
axiom/
├── apps/
│   └── web/                         # Next.js / React / TypeScript; Vercel project root
│       ├── package.json
│       ├── <actual JS lockfile>
│       └── src/ ...
├── services/
│   └── api/                         # One Python package, two runtime processes
│       ├── pyproject.toml
│       ├── <actual Python lockfile>
│       ├── Dockerfile               # One production image for API and worker
│       ├── .dockerignore
│       ├── app/
│       │   ├── main.py             # FastAPI entrypoint
│       │   ├── worker.py           # Independent worker entrypoint
│       │   └── ...
│       └── tests/ ...
├── contracts/                       # Versioned/generated API contracts as needed
├── infra/
│   └── compose.dev.yml             # Local API + worker; optional test services
├── ci/
│   ├── quality_gate.py
│   ├── README.md
│   └── quality.toml                 # Add with actual application packages
├── docs/
└── .github/workflows/
```

The tree is **the target layout, not a claim these files currently exist**. Do not commit an unbuildable Dockerfile, pretend lockfiles exist, or create empty application scaffolds to satisfy appearance. The first application-code PR (WP-01) must create only functional package files alongside real tests and CI configuration. Existing architecture uses `apps/web` and `services/api`; no second repository, Python microservice split or monorepo framework is necessary.

## 2. Deployment ownership and path mapping

| Deployed process | GitHub source directory | Proposed service | Build / run contract |
|---|---|---|---|
| Public and authenticated web | `apps/web` | Vercel project | Set **Root Directory = `apps/web`**; use native Next.js builds, not a required web Docker image |
| FastAPI REST + MCP | `services/api` | Railway service `axiom-api` | Set **Root Directory = `services/api`**; build the `Dockerfile` in that directory; start actual ASGI entrypoint, bind the provider-provided port |
| Durable research worker | `services/api` | Separate Railway service `axiom-worker` | Same Git source, Dockerfile and image recipe; **different start command** invoking the Python worker entrypoint; no public ingress |
| Authentication and database | External managed service | Supabase Auth + PostgreSQL | Not a production Compose database; only server components possess privileged database credentials |

Railway API and worker are **two independently deployed services** using the same Python package, not separate backend codebases. Configure their environment variables, health behavior, concurrency/restart settings, and network ingress separately. Verify the provider's actual support for sustained worker execution, restart handling, root-directory behavior, plans and price before deployment.

The browser uses a public `NEXT_PUBLIC_API_BASE_URL` with an explicit production HTTPS origin. Never put `DATABASE_URL`, service keys, AI keys or other privileged values in `NEXT_PUBLIC_*`. Set API CORS allowed origins precisely; enforce authentication and workspace authorization server-side. Keep migrations separately authorized and backward compatible across independent web/API releases.

For a standard single-package backend, Railway should find `services/api/Dockerfile` when the service root is `services/api`. If we later change the build context or use a nonstandard filename, review Railway's `RAILWAY_DOCKERFILE_PATH` settings rather than assuming the default still works. Reference: [Railway Dockerfiles](https://docs.railway.com/builds/dockerfiles), [Railway monorepos](https://docs.railway.com/deployments/monorepo), [Vercel monorepos](https://vercel.com/docs/monorepos).

## 3. Docker and Compose contract (to implement in WP-01)

- Build **one multi-stage, reproducible Python production image**, using the actual locked backend dependencies. Pin reviewed base image versions/digests, run as a non-root user, omit dev tools/secrets from the final image, and copy only required runtime files. Use `.dockerignore` to exclude `.env*`, local credentials, caches, VCS metadata and generated artifacts.
- Give the API and worker **independent runtime commands**. The API listens on the assigned port and has a real health/readiness route. The worker runs a bounded queue-processing entrypoint and can restart without corrupting jobs; a Docker healthcheck alone does not establish job durability.
- Add `infra/compose.dev.yml` **when the backend exists**, reusing the same Docker image/build configuration for local API and worker. Point to explicitly chosen local/test Supabase/Postgres configuration; avoid implicitly provisioning a second production data store. No real secrets or evaluator credentials in Compose.
- Keep local Next.js development **native by default** for fast refresh. Dockerizing the web project is optional and not required by the Vercel deployment path.
- These artifacts are **not created in this documentation-only change** because the Python application, lockfile, worker entrypoint and tests do not exist yet. The WP-01 PR must build/run them for real.

## 4. CI impact and fail-closed acceptance

The existing `.github/workflows/quality.yml` jobs are protected branch check names and **must not be renamed or skipped**:

1. `Quality / repository integrity`
2. `Quality / application readiness`
3. `Governance / configuration`

**Current state:** They validate repository integrity/governance. The application job correctly reports no application implementation; **it does not build Docker images today**.

**In the same PR that creates the first backend source and Docker artifacts:**

1. Add both real application packages to `ci/quality.toml` with their own actual manifests, lockfiles, tests and fresh test reports. `apps/web` and `services/api` are the package directories, not the repository root.
2. Extend the required **`Quality / application readiness`** job (or a required, non-skippable dependency of that job) to run `docker build --file services/api/Dockerfile services/api` on every PR and `main` push when the backend is present. Ensure the Docker step **fails closed** for missing/broken Dockerfiles, never a green placeholder or conditional skip when backend source exists.
3. Validate `docker compose -f infra/compose.dev.yml config --quiet`, then perform an actual container smoke run/health check using synthetic configuration; assert both API and worker image startup paths are valid. Add container/image vulnerability and secret checks with reviewed tooling when available, and keep lockfile dependency audits mandatory.
4. Test that altered Dockerfile/Compose/config breaks CI deliberately, and confirm healthy cases pass in GitHub Actions. Keep network-dependent DB/worker crash-recovery tests separate if they require authorized staging, and do not treat mocks as evidence of a functioning external service.
5. Keep existing branch protection and triggers for **all PRs**. Do not exempt Docker or deployment changes via broad path filters. CI builds images **without publishing or deploying** them; deploys and paid resources need separate owner approval.

**Why not wire Docker build into the current workflow now?** There is no Python app or Dockerfile to build. A mandatory Docker build would block all documentation PRs; a dummy Dockerfile or unconditional success would create misleading green results. The first functional backend PR is the correct atomic point to add real container CI.

## 5. WP-01 acceptance (no fake green evidence)

- [ ] `apps/web` builds with its actual lockfile and passes lint, type, unit and browser smoke checks.
- [ ] `services/api` exposes a real FastAPI health route, with real tests, dependency locks and clean import.
- [ ] API and worker both build from `services/api/Dockerfile` and start independently.
- [ ] Compose syntax, container startup and credential-exclusion tests pass on CI.
- [ ] All three existing protected checks pass on the exact PR revision; missing Docker checks fail the required application job once backend source exists.
- [ ] Vercel `apps/web` and Railway `services/api` roots, host plans, env separation and worker restart behavior are verified **before** deployment is called complete.
- [ ] No deployment, infrastructure spend or provider availability is claimed by this document.

**Scope:** This is a packaging/deployment topology decision, not a change to the approved product feature set, Supabase/Auth choice, external API spending constraints, or approval of any specific hosting bill.
