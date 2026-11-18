# Quality CI contract

Axiom is currently **documentation-only**: there is no frontend/backend code, package manager, lockfile or application test suite yet. Every pull request and push to `main` runs two stable status checks:

- **Quality / repository integrity** — run CI regression tests; parse actual Markdown links and fenced blocks, reject malformed/duplicate workflow YAML keys, missing triggers, filtered/skippable required jobs, unsafe token overrides, referenced production secrets, and obvious committed credential patterns.
- **Quality / application readiness** — explicitly reports **application not verified** while no application source exists. Once source appears, the job **fails** unless `ci/quality.toml` declares the *actual*, executable checks and real tests for every application package. Checks run with non-zero exit codes enforced.

When creating Next.js/FastAPI application code, add `ci/quality.toml` in **the same PR**. The manifest, **distinct ecosystem-matched lockfile**, and real test files must exist; unconfigured application source (including TypeScript `.mts`/`.cts`), skipped jobs, generic test globs matching production files, and placeholder commands are errors. The test runner itself must report nonzero on missing/failed tests; **Go packages additionally require `go test -json` and actual executed-test events**. No frontend/backend package manager or script is assumed before implementation.

Example **only**, to adapt to the *actual* frontend scripts and package manager:

```toml
version = 1

[packages.web]
directory = "apps/web"
manifest = "package.json"
lockfile = "pnpm-lock.yaml"
test_files = ["src/**/*.test.ts", "tests/**/*.spec.ts"]
install = ["corepack", "pnpm", "install", "--frozen-lockfile"]
lint = ["corepack", "pnpm", "run", "lint"]
typecheck = ["corepack", "pnpm", "run", "typecheck"]
test = ["corepack", "pnpm", "run", "test:ci"]
build = ["corepack", "pnpm", "run", "build"]
security = ["corepack", "pnpm", "audit", "--audit-level", "high"]
```

Use another `[packages.api]` entry for the eventual Python backend with its **actual Python environment setup, reproducible lockfile, lint/type/pytest/build and dependency audit commands**, and a real test glob. This gate recognizes Node (`package.json` + an npm/pnpm/yarn/bun lockfile), Python (`pyproject.toml` + uv/Poetry/PDM lockfile or `requirements.lock`), Rust (`Cargo.toml`/`Cargo.lock`), and Go (`go.mod`/`go.sum`) artifact pairs. Source coverage and test filenames are validated, but arbitrary configured commands **cannot be proved meaningful by syntax alone**—they must be reviewed and tested against failures. If it chooses tools not present on the GitHub runner, update `.github/workflows/quality.yml` to install them. All commands execute without a shell in the declared package directory.

Ordinary PR checks deliberately use no production secrets or live paid AI/research services. The lightweight secret-pattern scan is **not** a substitute for GitHub secret scanning or independent security review. The repository job uses pinned PyYAML and markdown-it-py for safe YAML and CommonMark parsing. Staging database/migration/integration/MCP testing and 500-founder performance testing require separately approved services and evidence. The status-check names are stable for branch protection.
