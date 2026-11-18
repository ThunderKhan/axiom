# Contributing to Axiom

Axiom uses a **correctness-first** engineering process. Read [AGENTS.md](AGENTS.md), [ENGINEERING.md](ENGINEERING.md), and the [canonical documentation index](docs/01-INDEX.md) **before** planning code or changing product behavior.

## Issues and work planning

Use the GitHub issue forms for reproducible bugs, new feature proposals, and engineering tasks. Provide acceptance criteria and expected failure/authorization cases. Do not submit secrets, private customer data, or live vulnerability details in issues; see [SECURITY.md](SECURITY.md).

Use shared **issues and PR labels** from [the catalog](.github/labels.json): one `type:*` and `area:*` where applicable, appropriate `priority:*` and `status:*` for issues, and `risk:high` for sensitive changes. GitHub labels are shared between issues and PRs rather than two separate label namespaces. CodeRabbit **suggests** labels; humans review/assign them.

**Label synchronization:** [Sync repository labels](.github/workflows/sync-labels.yml) runs automatically on trusted `main` changes to `.github/labels.json`, with serialized, non-cancelled execution. The initial catalog has been provisioned and custom labels are in use; if a later sync fails, a maintainer can manually dispatch it from `main`. The sync is additive and preserves unrelated labels.

## Pull requests

1. Create a branch from current `main`: `feat/*`, `fix/*`, `ci/*`, `docs/*`, or `chore/*` (consistent descriptive suffix).
2. Keep changes focused and link the issue, requirement IDs, approved ADRs, behavior and acceptance criteria in the PR template.
3. Run actual build, lint, type checks, automated tests and security checks for affected packages. **Never use placeholder commands or silently suppress missing tests.**
4. PRs that introduce the first application code must add the project’s actual lockfiles, test files and `ci/quality.toml` scripts in the **same change**, as documented in [ci/README.md](ci/README.md).
5. Disclose real test commands, revision, results, skipped tests and limitations. Mocked sources/models are not evidence of working live integrations.
6. Review CodeRabbit findings; fix reproducible correctness/security issues, respond with evidence to false positives. AI review does **not** replace CI or qualified human review.
7. Do not merge or deploy without authorization and passing protected checks. Production secrets, migrations and external API entitlements need separate verified approval.

**Protected default branch:** The [active `main` ruleset](https://github.com/ThunderKhan/axiom/rules/27560167) requires a PR with passing `Quality / repository integrity`, `Quality / application readiness`, and `Governance / configuration` checks, an up-to-date branch, and resolved review conversations. Force-pushes and deletion are blocked. Approvals are set to **0** for this solo-maintained repository; the maintainer remains responsible for review and merge decisions.

## Review risk

- **Low:** documentation or local nonbehavioral edits — focused tests and review.
- **Medium:** API/feature logic and routine schema — regression/integration tests and independent review where possible.
- **High:** auth, multi-tenant RLS, privacy, migrations, CI trust, MCP OAuth and production infrastructure — adversarial tests, qualified human decision and environment-specific release evidence.

For security-sensitive files, [CODEOWNERS](.github/CODEOWNERS) records the initial owner. If the owner is the sole contributor, configure required independent review rules **only once another eligible reviewer exists**, or PRs can become unmergeable.

## Submission and release

The November 26 fellowship requires genuine deployed product evidence and appropriate P0 security checks. The 500-concurrent-founder capability is a **design target** requiring separate measured verification before broader production rollout, per [ADR-010](docs/decisions/010-staged-500-founder-capacity-release.md).

Contributors should prefer the smallest tested coherent vertical slice over unverified scaffolding.
