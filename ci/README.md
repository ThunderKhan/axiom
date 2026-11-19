# Quality CI contract

Axiom now has its first **status-only frontend** at `apps/web` (issue #8), using npm, a committed `package-lock.json`, Node.js 22 native unit tests/JUnit, and Playwright Chromium smoke. The first Python backend foundation is supplied in issue #9 with one locked API/worker package and mandatory Docker/Compose validation. Every pull request and push to `main` runs two stable quality status checks:

- **Quality / repository integrity** — run CI regression tests; parse actual Markdown links and fenced blocks, reject malformed/duplicate workflow YAML keys, missing triggers, filtered/skippable required jobs, unsafe token overrides, referenced production secrets, and obvious committed credential patterns.
- **Quality / application readiness** — runs actual frontend checks for `apps/web` and locked Python install, Ruff lint/format, mypy, pytest/JUnit, wheel build and pip-audit for `services/api`; it then executes `python ci/docker_smoke.py` on every PR/push for actual non-root image build, Compose validation, API health/worker lifecycle and failure-path checks. The required application job also runs `python ci/integrated_smoke.py` after
backend Docker smoke, launching real native Next.js, Chromium, a Compose API,
and a separate worker to test cross-origin connectivity, failure detection and
cleanup. See the [canonical developer guide](../README.md#canonical-developer-setup--milestone-0-foundation).
If later application code is added without corresponding `ci/quality.toml` checks, the gate fails. A passing foundation gate does **not** prove the unfinished product or deployment works.

When creating Next.js/FastAPI application code, add `ci/quality.toml` in **the same PR**. The manifest, **distinct ecosystem-matched lockfile**, and real test files must exist; unconfigured application source (including TypeScript `.mts`/`.cts`), skipped jobs, generic test globs matching production files, and placeholder commands are errors. The test runner must generate a **fresh JUnit XML report** at `test_report`, with at least one passing testcase; an all-skipped, empty, stale, missing or failed report fails the gate. The actual `test` script must be configured to write that path (for example, Vitest's JUnit reporter or pytest's `--junitxml`). **Go packages use `go test -json` instead**, and must emit at least one passing, executed test. Build/lint/typecheck/security commands are still reviewed and never assumed effective just because they exit zero. No frontend/backend package manager or script is assumed before implementation.

Example **only**, to adapt to the *actual* frontend scripts and package manager:

```toml
version = 1

[packages.web]
directory = "apps/web"
manifest = "package.json"
lockfile = "pnpm-lock.yaml"
test_files = ["src/**/*.test.ts", "tests/**/*.spec.ts"]
test_report = "build/test-results/junit.xml"  # must be written fresh by test:ci
install = ["corepack", "pnpm", "install", "--frozen-lockfile"]
lint = ["corepack", "pnpm", "run", "lint"]
typecheck = ["corepack", "pnpm", "run", "typecheck"]
test = ["corepack", "pnpm", "run", "test:ci"]
build = ["corepack", "pnpm", "run", "build"]
security = ["corepack", "pnpm", "audit", "--audit-level", "high"]
```

Use another `[packages.api]` entry with `directory = "services/api"` for the eventual Python backend with its **actual Python environment setup, reproducible lockfile, lint/type/pytest/build and dependency audit commands**, and a real test glob. **Docker is an approved backend packaging requirement:** in the same PR that first creates Python source and `services/api/Dockerfile`, extend the required `Quality / application readiness` job (without renaming or weakening it) to fail on broken Docker builds, invalid `infra/compose.dev.yml`, or failed API/worker container startup smoke checks. Do not add dummy Docker checks before there is an application to build; see [the deployment topology plan](../docs/19-DOCKER-AND-DEPLOYMENT-TOPOLOGY.md). This gate recognizes Node (`package.json` + an npm/pnpm/yarn/bun lockfile), Python (`pyproject.toml` + uv/Poetry/PDM lockfile or `requirements.lock`), Rust (`Cargo.toml`/`Cargo.lock`), and Go (`go.mod`/`go.sum`) artifact pairs. Source coverage and test filenames are validated, but arbitrary configured commands **cannot be proved meaningful by syntax alone**—they must be reviewed and tested against failures. If it chooses tools not present on the GitHub runner, update `.github/workflows/quality.yml` to install them. All commands execute without a shell in the declared package directory.

Ordinary PR checks deliberately use no production secrets or live paid AI/research services. The lightweight secret-pattern scan is **not** a substitute for GitHub secret scanning or independent security review. The repository job uses pinned PyYAML and markdown-it-py for safe YAML and CommonMark parsing. Staging database/migration/integration/MCP testing and 500-founder performance testing require separately approved services and evidence. The status-check names are stable for branch protection.

**Runner notes:** For Node and Python tests, configure a genuine JUnit-compatible reporter and use `test_report` relative to the package directory. The gate removes any previous report before executing the command, then validates the newly generated XML; a report that describes zero passing tests is not accepted. Go's streaming JSON verifier instead prints stdout/stderr **even when the test command fails**, preserving diagnostic details. The first application-code PR must supply the actual runner, report configuration and lockfiles—this policy does not imply application tests currently exist.

## M1.3 — mandatory real database gate

The protected `Quality / application readiness` job now provisions **isolated
PostgreSQL 17** and invokes `services/api/scripts/run_db_integration.py` after
the existing application checks, *before* the mandatory Docker and integrated
Chromium smoke jobs. The runner rejects any non-loopback, non-`axiom_test`
connection target; it checks two Alembic revisions, metadata drift, runtime
roles, real non-owner RLS, concurrent data invariants and DB readiness.
Tests marked `postgres` are skipped in the generic no-DB pytest invocation
but **must actually execute** in the dedicated real database CI step.
Skipped, absent or failed database integration checks are not acceptable
verification of Issue #16. No hosted Supabase resources or production
credentials are involved.
