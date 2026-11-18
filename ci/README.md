# Quality CI contract

Axiom is currently **documentation-only**: there is no frontend/backend code, package manager, lockfile or application test suite yet. Every pull request and push to `main` runs two stable status checks:

- **Quality / repository integrity** — run CI regression tests; parse actual Markdown links and fenced blocks, reject malformed/duplicate workflow YAML keys, missing triggers, filtered/skippable required jobs, unsafe token overrides, referenced production secrets, and obvious committed credential patterns.
- **Quality / application readiness** — explicitly reports **application not verified** while no application source exists. Once source appears, the job **fails** unless `ci/quality.toml` declares the *actual*, executable checks and real tests for every application package. Checks run with non-zero exit codes enforced.

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
