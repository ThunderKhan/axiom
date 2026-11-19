# Axiom

**Axiom** is an evidence-grounded intelligence product for startup founders: discover public customer-demand signals, investigate competitors, evaluate founder/product fit, explore scenarios, and keep relevant opportunities organized.

**Project status:** Product and architecture specifications exist. The first status-only Next.js frontend foundation is available in `apps/web` (issue #8); a limited FastAPI API/idle-worker foundation is available in `services/api` (issue #9). Authentication, workspaces, research, CRM, durable job processing and production deployment remain **unimplemented or unverified**. A documented feature is not an implemented feature, and example research is not live-source evidence.

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
