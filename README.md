# Axiom

**Axiom** is an evidence-grounded intelligence product for startup founders: discover public customer-demand signals, investigate competitors, evaluate founder/product fit, explore scenarios, and keep relevant opportunities organized.

**Project status (18 November 2026):** Product, architecture and design specifications exist; the application is **not yet implemented or deployed**. A documented feature is not an implemented feature, and example research is not live-source evidence.

## Project documentation

The [documentation index](docs/01-INDEX.md) is the canonical starting point. It links the approved [PRD](docs/02-PRD.md), [MVP](docs/03-MVP.md), [system architecture](docs/05-SYSTEM-ARCHITECTURE.md), [design direction](docs/13-DESIGN.md), [testing strategy](docs/14-TESTING-STRATEGY.md) and [decision register](docs/DECISIONS.md).

## Engineering workflow

Read [AGENTS.md](AGENTS.md) and [ENGINEERING.md](ENGINEERING.md) before changes, and consult [CONTRIBUTING.md](CONTRIBUTING.md) for issue labels, PR expectations, tests, CodeRabbit, and review. Use [SECURITY.md](SECURITY.md) for private vulnerability reports.

Axiom's engineering goals include correctness-first CI, reproducible test evidence, safe workspace isolation, lawful and attributed source ingestion, and a transparent distinction between AI-generated interpretation and observed facts.

The repository is intentionally documentation-first. **No install, build, frontend server or backend server command is currently supported on `main`**; commands and lockfiles will be documented as the actual Next.js/FastAPI packages are introduced. Do not use placeholder commands or claim tests that have not run.

## Review and release

Changes should be reviewed through pull requests with CI and human review. CodeRabbit provides supplementary automated review, not merge authorization. The November 26 fellowship deliverable and staged 100/250/500-active-founder validation are documented separately; no capacity or provider access is claimed verified without actual test evidence.

**Do not commit credentials, production secrets, private founder data, or customer records.**
