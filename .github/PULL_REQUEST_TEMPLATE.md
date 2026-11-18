## Summary and scope

What changed, why, and what was deliberately left out?

## Requirements and linked issues

- Requirement IDs / approved documents:
- Closes # (if applicable):
- Related ADRs / API contracts:

## Risk and security impact

- [ ] Low (docs / isolated nonfunctional changes)
- [ ] Medium (application behavior / API / regular schema changes)
- [ ] High (auth, tenant isolation, data integrity, migrations, secrets, CI trust, MCP or production)
- Permissions, data handling, external provider or migration effects:
- Rollback / forward-recovery plan, if applicable:

## Verification — actual evidence

| Check | Exact command, environment or run URL | Result |
|---|---|---|
| Build | | Not run / Pass / Fail |
| Lint and formatting | | Not run / Pass / Fail |
| Type checking | | Not run / Pass / Fail |
| Automated tests (name/count) | | Not run / Pass / Fail |
| Security/tenant isolation | | Not run / Pass / Fail |
| Browser/integration/migration (if relevant) | | Not run / Pass / Fail |

Include the **commit SHA** tested and explicitly disclose skipped/unavailable checks.
Do not claim a live provider, deployment or test is verified from mocks or docs alone.

## UI, migrations and deployment

- Screenshots or recording for UI changes (if applicable):
- Database/API changes and migration/compatibility notes:
- Required environment variables/secrets (names only; do not paste values):
- Deployment performed? **No**, unless separately authorized and evidenced.

## Reviewer checklist

- [ ] Matches approved PRD/MVP, current `AGENTS.md` and `ENGINEERING.md`.
- [ ] Success, failure, permissions and retry/idempotency cases considered.
- [ ] New behavior has meaningful tests; no required checks are silently skipped.
- [ ] Documentation/index updated when contracts or decisions changed.
- [ ] No credentials, private user data or invented metrics/results.
- [ ] CodeRabbit findings evaluated; substantive findings fixed or explained.
- [ ] Independent review requested for medium/high-risk changes where feasible.

**Merge/deploy requires separate authorization and successful required checks.**
