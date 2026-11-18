# Axiom — Deployment and Operations Runbook

**Status:** DRAFT — in review · **Version:** 0.1 · **Date:** 18 November 2026  
**Authority:** [Architecture](05-SYSTEM-ARCHITECTURE.md), [TRD](06-TRD.md), [MVP](03-MVP.md), [Testing](14-TESTING-STRATEGY.md)

## 1. Deployment objective and unknowns

Axiom must be reachable via stable **HTTPS landing page → login → authenticated app**, with working API, managed PostgreSQL, and actual research execution (separate worker if host supports it). **No specific cloud provider/free tier is approved or proven yet.** ₹0 external AI/research API spending is planned; actual persistent worker/free hosting feasibility needs a real deployment probe. Never state production is deployed until confirmed.

### Proposed topology

§§§text
HTTPS Browser → Next.js Frontend → FastAPI REST + MCP
                                  ↓
                          PostgreSQL / Auth
                                  ↑
                        Python Research Worker
                                  ↓
              Permitted source APIs / free inference if verified
§§§

No separate evaluator-only page, public guest sandbox, bulk sending service or unrestricted agent runtime.

## 2. Pre-deployment decisions (blockers)

1. Select frontend/API/worker hosts with persistent runtime, outbound HTTPS, service-to-DB connectivity, TLS and transparent free quotas; document actual billing/usage risk.
2. Confirm secure identity provider and privileged credential handling. Pre-provision a low-privilege evaluator account; distribute password **privately** through submission channel.
3. Verify database migrations, backups, schema isolation and connection limits with chosen PostgreSQL environment.
4. Prove a worker can claim a queued job, survive restart and resume; if free worker is impossible, stop and obtain approved architecture adjustment.
5. Confirm at least one permitted live public source fetch, competitor website extraction and model call if marketing AI as working.
6. Confirm MCP transport/client compatibility and auth scheme. Don't publicly expose write-enabled MCP before tests.
7. Choose actual app/domain URLs and valid CORS/origin rules; avoid wildcard credentialed CORS.
8. Confirm secrets and environment keys needed by deployed processes; no actual values in this document.

## 3. Environment variable catalogue (names illustrative)

| Process | Example variable | Handling |
|---|---|---|
| Frontend | §NEXT_PUBLIC_API_BASE_URL§ | Public config only |
| Frontend | §NEXT_PUBLIC_SUPABASE_URL§ / publishable key if selected | Public config, **not** secret/service key |
| API/worker | §DATABASE_URL§ | Secret, server only |
| API | §AUTH_ISSUER§, §AUTH_AUDIENCE§, §AUTH_JWKS_URL§ | Verify against chosen auth provider |
| API | §CORS_ALLOWED_ORIGINS§ | Specific HTTPS origins |
| API/worker | §SOURCE_ALLOWED_FAMILIES§, §FETCH_TIMEOUT_S§ | Reviewed adapter policy |
| Worker | §JOB_LEASE_SECONDS§, §JOB_MAX_ATTEMPTS§, §WORKER_CONCURRENCY§ | Bounded and tested |
| API/worker | §AI_PROVIDER§ / provider-specific API key | Secret, only after actual zero-cost provider verified |
| MCP | §MCP_RESOURCE_AUDIENCE§, §MCP_AUTH_ISSUER§ | Provider-aligned client auth |
| All | §LOG_LEVEL§, §ENVIRONMENT§, §APP_VERSION§ | Redacted logs, traceability |

Keep §.env.example§ with names/placeholders, not tokens. Use hosting secrets manager or protected environment; never expose admin/service-role key via §NEXT_PUBLIC_*§. Do not commit real evaluator password, API key or personal token.

## 4. Deployment procedure (once host selected)

1. Record current commit SHA/tag and host configuration; back up database if migrations change persistent data.
2. Install from lockfile; ensure frontend build, Python imports/type/lint/tests, migration check and API schema generation pass.
3. Provision database/auth resources with least-privilege secrets; enable and verify RLS where appropriate, while enforcing app-layer workspace checks.
4. Apply versioned migrations transactionally/with a forward-fix plan; verify schema version, essential indices and constraints.
5. Deploy API and separate worker (same Python source, different start command). Validate §/health§ and readiness DB probe.
6. Deploy frontend with **public** API/Auth configuration; check HTTPS, redirect to login, CORS and cookies/tokens.
7. Run real bounded source retrieval and competitor teardown through API; confirm worker actually processes queued jobs.
8. Test persisted profile, graph/report and Counterfactual scenario re-open; create lead, note, follow-up and unsent draft.
9. Exercise two documented HTTP endpoints and five core MCP tools using an actual client; denied write should fail.
10. Test low-privilege evaluator credentials privately, including session expiration and access to only evaluator workspace.
11. Record log/trace/request IDs, final commit, source/model versions, screenshots and test run results; publish an honest README limitations section.

## 5. Smoke test checklist

- [ ] Landing at stable HTTPS URL; CTA reaches ordinary login; no public demo route.
- [ ] Valid provisioned credentials sign in; invalid credentials safely rejected.
- [ ] Separate users/workspaces cannot read each other's records.
- [ ] Adaptive onboarding and existing product profile load correctly.
- [ ] Genuine permitted discovery source returns actual source URL/time; fixture data labeled.
- [ ] Competitor report cites actual public page or explicitly reports unknown/blocked.
- [ ] Graph and accessible report agree on source IDs and verdict.
- [ ] Two saved scenarios compare same evidence snapshot; no invented business uplift.
- [ ] CRM saves/reopens stage, note, follow-up, editable **unsent** draft.
- [ ] API jobs show partial/failure statuses, worker completes real queued task.
- [ ] HTTP discovery+teardown and MCP core tools function with scoped auth.
- [ ] No credentials in client bundle, logs, repo or exports.
- [ ] Mobile/desktop E2E and security negative checks pass.
- [ ] External provider quotas and fallback behavior disclosed; ₹0 budget not exceeded.

## 6. Monitoring and incident response

Observe API liveness/readiness, DB connectivity, worker last lease/heartbeat, queued job age, source adapter failures, model quota/error, MCP denied writes, auth failures, request latency and error rates. Correlate by opaque request/run ID. Avoid logging raw post bodies, credentials or sensitive drafts.

**Incident path:** identify affected component → mark jobs partial/failed or disable problematic adapter → protect user data and avoid new false research claims → communicate status in app → restore source/worker/auth safely → rerun smoke. If security incident, revoke affected tokens and restrict vulnerable endpoints before re-enabling.

## 7. Backup, rollback and data recovery

- Verify whether selected managed DB free tier includes automated backups; do **not assume**. If not, define authorized export/backup and safe restore test.
- Before schema change, snapshot DB; migrations should be reversible or have a documented forward-only recovery path.
- App rollback to known commit/deploy; preserve compatibility with schema changes or coordinate DB rollback carefully.
- Retain source evidence lineage and workspaces when restoring; don't replace verified results with fixtures without disclosure.
- Worker retry state may be stale after rollback; inspect leases and idempotency before replay.
- Log recovery rehearsal date, operator, lost data risk, and redacted verification result.

## 8. Evaluator account and submission

Account must be **normal authenticated user**, low-privilege, with preloaded optional, clearly labeled example product records. Test login in clean browser and ordinary app, no developer-only shortcuts. Share credentials privately in fellowship submission, **never in GitHub, screenshots or frontend JS**; rotate/revoke after judging.

Submit deployed app URL, repo, documented APIs/MCP, source/data/AI disclosures, tests, architecture summary and optional recording as backup. Recording cannot substitute for functioning deployed system.

## 9. Stop/go release criteria

Do not claim release complete if P0 gates remain unverified, a protected route is publicly accessible, AI research is faked, source terms are violated, cross-tenant tests fail or a worker is nonfunctional. Any R0 objective not met requires explicit owner-approved adjustment and honest release notes, not silent scope erosion.
