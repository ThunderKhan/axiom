# ADR-010 — Staged Validation and Production Gate for 500 Concurrent Founders

**Status:** APPROVED — capacity release strategy; performance NOT yet verified  
**Date:** 18 November 2026  
**Decision owner:** Axiom founder, technical decision **6 of 6**, Option **B**  
**References:** [System Architecture](../05-SYSTEM-ARCHITECTURE.md), [TRD](../06-TRD.md), [Scalability](../18-SCALABILITY.md), [Testing](../14-TESTING-STRATEGY.md), [Deployment](../15-DEPLOYMENT-RUNBOOK.md), [Roadmap](../16-IMPLEMENTATION-ROADMAP.md), [MVP](../03-MVP.md)

## Problem and options

The founder requires an architecture capable of serving at least **500 concurrently active authenticated founders**, with correct multi-workspace isolation and durable async research. The November 26, 2026 fellowship submission is a near-term deadline; the deployed host, workloads and external provider limits have not yet been measured.

- **A — 500-user pass required for November 26:** strongest immediate gate, high deadline risk.
- **B — Scalable architecture now, preliminary 100–250-user tests before submission, verified 500-user benchmark before wider production rollout:** **APPROVED.**
- **C — Attempt 500 before November 26, allow a labeled limited-capacity fellowship fallback:** not selected as the release policy.

## Decision — Option B

1. **Now, architect for 500:** Keep FastAPI stateless, use bounded DB connection pooling and workspace-indexed queries, and move research into a durable PostgreSQL job queue processed by independent managed workers. Enforce fair per-workspace admission/quota, idempotency, retries, caching isolation and jittered/backoff status polling. No unnecessary multi-region architecture or service proliferation is required solely for this target.
2. **Before the November 26 submission**, run and record **preliminary authenticated-load tests at 100 and 250 simultaneously active users** on a representative deploy/staging tier, with realistic read/write/job-submit traffic and explicit source-provider stubs for high volume. Record attempts, results, environment/commit, p50/p95 latencies, error/429 rates, queue depths, resource use and security outcomes. If tests cannot be completed or pass, disclose the limitation and remediation rather than fabricate capacity.
3. **Fellowship release:** An honest, functional **limited-capacity fellowship deployment may be submitted** if all separately approved **P0 functional/security release gates** pass, regardless of whether a 500-user load test has been run. The 100–250 preliminary tests remain a **pre-submission validation objective and reporting obligation**, not a new automatic 500-user submission gate. No claim of tested 500-founder support is permitted.
4. **Broader public production rollout:** **BLOCKED** until the **actual intended managed tier** (or a defensibly production-equivalent tier) passes a reproducible **500 concurrently active authenticated founder** benchmark and critical security, reliability, DB-pool and queue fairness checks. Do not treat 500 idle sockets as 500 users conducting real workflows.
5. **Capacity workload:** Use the provisional 25 requests/second steady and 50 requests/second heavier mix in [18-SCALABILITY.md](../18-SCALABILITY.md) as **starting test assumptions, not certified SLOs**. Real launch thresholds and request mix require measured evidence and an explicit documented performance acceptance decision before production rollout.
6. **External research separation:** 500 active users **does not imply** 500 simultaneous LLM/source fetches. Protect legitimate no-charge third-party API quotas with async job admission, per-provider limits, fair queueing, and truthful partial/queued/failed state.
7. **Budget:** Modest managed hosting spend is allowed only with plan/price approval under [ADR-008](008-managed-hosting-and-worker.md); the **₹0 paid external AI/research API constraint** remains unchanged. If production capacity requires a larger hosting budget, report the specific upgrade and secure approval before procurement.
8. **Escalation:** If 100/250 tests fail, identify bottlenecks, correct critical security/data integrity issues before submission, and disclose throughput limitations. If the 500 benchmark fails, defer broader rollout, tune architecture/infrastructure, retest and report actual achieved load. No quiet redefinition of "active founder," reduced load, or removal of this objective.

## Staged acceptance and evidence

| Stage | Timing and gate | Evidence / disposition |
|---|---|---|
| **S0 — Correctness baseline** | Before concurrency tests | Two users/two workspaces isolation, migration, job idempotency, source provenance and auth pass |
| **S1 — Preliminary capacity** | **Before 26 November 2026 submission** | Test at **100 and 250 active authenticated users**, record achieved RPS, p50/p95/p99, internal errors, 429, DB connections/CPU/RAM, worker queue, external provider mocks; report failures transparently |
| **S2 — Fellowship submission** | **26 November 2026, 23:59 IST** | Existing P0 release gates verified; label the deployment as **capacity-unverified or limited capacity** if 500-user gate not passed; no unsupported scalability marketing |
| **S3 — Broad production launch** | **After successful 500-user verification** | 500 distinct active user contexts, mixed traffic, ≥15-minute steady state, 50-RPS burst trial, 60-minute soak, restart and security/adversarial tests on intended tier; meet documented accepted thresholds |
| **S4 — Growth monitoring** | After rollout | Observe actual traffic, queue wait, DB pool, provider quota, incidents, and re-benchmark on deployment/topology changes |

### Initial benchmark design (subject to measured acceptance)
- 100 → 250 preliminary concurrent active user tests, with realistic CRM/reads and bounded queued research, before the fellowship deadline; do not hammer external social/LLM APIs.
- Production acceptance: 500 active identities, approximately 25 interactive requests/s steady mix (traffic assumption only), a heavier 50 requests/s burst, and a ≥60-minute soak; quantify queue/poll traffic separately and tune sampling.
- Proposed p95 read ≤1s / simple CRM write ≤2s / enqueue ≤2s, ≤1% internal 5xx; critical gate is **zero successful cross-tenant data access and no duplicate committed business writes**. Candidate performance targets require actual calibration before being claimed as SLAs.
- For any measured result, report deployment tier, commit SHA, test script, scenario, run date, p50/p95/p99, throughput, error and 429, DB pool, worker queue, CPU/RAM, provider mocks versus permitted live probes, and reproduction steps.

## Approval boundary

This ADR approves **Option B and staged release gating**, not proven 100/250 or 500 concurrency, not specific hosting tier pricing, and not a relaxation of unrelated MVP, source compliance, privacy, OAuth or security requirements. [13-DESIGN.md](../13-DESIGN.md) remains on hold pending the founder's complete design-system file. All other open technology and integration verifications remain open.

**Owner approval:** Axiom technical decision 6 of 6 — founder selected **B** on **18 November 2026**.
