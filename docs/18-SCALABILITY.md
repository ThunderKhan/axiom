# Axiom — Scalability and Capacity Design (500 Concurrent Founders)

**Status:** DRAFT — capacity architecture target proposed; **not load-tested or approved as achieved**  
**Version:** 0.1 · **Date:** 18 November 2026  
**Owner requirement:** Axiom should be engineered to accommodate **at least 500 founders actively using the application concurrently**.  
**References:** [System Architecture](05-SYSTEM-ARCHITECTURE.md), [TRD](06-TRD.md), [Database Design](07-DATABASE-DESIGN.md), [API Contracts](08-API-CONTRACTS.md), [Testing](14-TESTING-STRATEGY.md), [Deployment](15-DEPLOYMENT-RUNBOOK.md)

## 1. Capacity objective and honest interpretation

**500 concurrent founders** means up to 500 simultaneously authenticated, active user sessions using Axiom's product and navigating/reading/updating workspaces. It does **not** inherently mean 500 simultaneous expensive LLM inferences, 500 new external crawls per second, or 500 open database connections. Heavy research is **asynchronous** and must be fairly queued, admission-controlled and rate-limited rather than silently overloading providers.

There are three distinct test dimensions:

1. **Sessions/active users:** 500 authenticated virtual users hold and use normal workspaces.
2. **Interactive throughput:** reads, workspace changes and CRM updates meet measured latency and correctness targets under load.
3. **Research capacity:** users can enqueue bounded jobs, see honest progress, and get fair completion subject to **measured** worker/provider throughput and quotas.

**Current state:** Neither 500-user capacity nor the hosting/AI provider budgets have been tested. This is a **design and test target**, not a guarantee, capacity claim or assertion that it fits a ₹0 deployment. The founder's ₹0 objective applies to **external AI/research API spending**; under [ADR-008](decisions/008-managed-hosting-and-worker.md), **modest paid managed infrastructure is permitted** after exact cost approval; appropriate production compute/database tiers may still need further resources or adjusted expectations at 500 active users.

## 2. Workload model (assumptions requiring validation)

For the first capacity benchmark, simulate **500 concurrent authenticated founders** with at least 500 separate user identities or realistically provisioned access tokens, and separate workspace-owned objects.

| Operation category | Illustrative request mix | Notes |
|---|---|---|
| Read opportunities, profiles, saved evidence, competitor reports, CRM | ~65% of interactive API requests | Cached or indexed reads, no live provider call |
| CRM notes/stage/follow-ups and workspace changes | ~25% | Transactional, idempotent writes |
| Submit discovery, competitor, assessment and scenario jobs | ~10% | Submission returns job ID; provider processing is queued |
| Background status checks | **Additional measured traffic** | Poll with jitter/backoff; never every 1s from all 500 clients |
| Landing / static asset delivery | Separate CDN/browser metric | Do not use application database for static assets |

Assume an illustrative average **3 interactive API requests per founder per minute**: 500 × 3 / 60 ≈ **25 API requests/second**, plus status polls. A heavier 6 requests/founder/minute implies **50 requests/second** before status checks. These are *traffic model examples*, not measured workload, and could be higher during synchronized use. An initial target is steady mixed **25 requests/s**, a heavier test at **50 requests/s**, and an admission spike in which many founders submit research close together.

**Important:** long research processing is not included in fast REST completion latency; it has separate acceptance and queue fairness checks. A benchmark that only keeps 500 idle browser sessions open is insufficient.

## 3. Capacity requirements and proposed SLOs

| ID | Proposed requirement under 500-founder realistic mixed load | Measurement |
|---|---|---|
| CAP-01 | 500 simultaneous authenticated active sessions remain isolated and usable for 15-minute steady load | k6/Locust or equivalent test |
| CAP-02 | Cached/DB-backed reads p95 ≤ **1.0s** at 25 req/s steady; evaluate at 50 req/s burst | API latency histogram, server and DB metrics |
| CAP-03 | Simple CRM writes p95 ≤ **2.0s**, with zero duplicate persisted effects under retries | Load with idempotency/DB assertions |
| CAP-04 | Research job submission p95 ≤ **2.0s** (returns accepted/job ID), not including external fetch/inference | API response 202 and durable job verification |
| CAP-05 | ≤ **1%** unexpected **internal** HTTP 5xx failures during test; explicit 429/provider failures recorded separately, never hidden | Tagged error metrics and job outcomes |
| CAP-06 | **0 cross-workspace access violations** across mixed-tenant load and adverse IDs | API/MCP isolation tests |
| CAP-07 | Research queue is bounded, durable, observable and fair; no starved workspace due to a single heavy user | Queue age/distribution, completed/failed state |
| CAP-08 | Worker restart preserves job state and prevents duplicate CRM/domain side effects | Forced restart/lease recovery test |
| CAP-09 | No memory/DB connection/resource exhaustion and no unbounded accumulation of stuck jobs in a 60-minute soak | Memory, CPU, connection, queue telemetry |
| CAP-10 | UI stays responsive, shows partial/failure/quota state and does not poll aggressively when backgrounded | Browser plus network trace |

**Targets are provisional:** confirm traffic mix, test infrastructure and available hosting quotas before adopting them as contractual SLOs. Critical user journeys remain more important than ungrounded headline concurrency metrics. Never claim "handles 500 concurrent founders" until the deployed topology passes the benchmark.

## 4. Logical topology for horizontal growth

§§§mermaid
flowchart TD
  U[500 active founders] --> CDN[CDN / Static frontend / TLS]
  CDN --> WEB[Stateless Next.js serving]
  WEB --> LB[API ingress / rate limiting]
  EXT[Authorized MCP clients] --> LB
  LB --> API[Stateless FastAPI replicas, if host allows]
  API --> POOL[Bounded DB connection pool / PgBouncer where offered]
  POOL --> PG[(Managed PostgreSQL)]
  API --> JOBS[Durable Postgres research queue]
  JOBS --> WORKERS[Bounded Python worker pool]
  WORKERS --> SOURCES[Permitted external source APIs]
  WORKERS --> LLM[Verified free or configured model inference]
  API --> C[Per-workspace short-TTL cache, optional]
§§§

**Modular monolith remains valid** for 500 concurrent active founders; load does not automatically justify splitting everything into microservices. Keep the API stateless, pool database connections, and isolate long-running network/AI work in durable workers. Increase replicas and pool sizes only after measuring bottlenecks and respecting managed database connection caps.

## 5. API and frontend load design

- **Keep expensive work off request path:** discovery and competitor research create bounded durable jobs and return 202 promptly. Even "compare scenarios" may use a job for complex AI enrichment while deterministic diff can be responsive.
- **Limit pagination:** default 20, max 100; filter by workspace and indexed columns; use cursor pagination for large feeds.
- **Cache conservatively:** derived read-only feed/report lists with short TTL/ETag or per-workspace keys; invalidate on workspace writes; **never share private cached objects across users/workspaces**. HTTP caching of authenticated responses must be explicitly scoped or disabled.
- **No client polling storm:** initial polling no more frequent than ~5 seconds with jitter, back off to 10–30s on long jobs, pause or reduce while tab hidden, stop on terminal result. 500 users polling every 5s adds **100 req/s**; this alone can exceed a free-tier host.
- **Separate control and data plane:** the API should answer profile/CRM reads while worker/source APIs are slow or rate-limited.
- **Frontend:** CDN-cached public assets; dynamic/authenticated content only from authorized paths, with loading/errors and no false live results.

## 6. PostgreSQL and tenancy performance

- Use targeted composite indexes on §(workspace_id,created_at)§, §(workspace_id,stage,updated_at)§, §(workspace_id,run_id)§, §(workspace_id,assessment_id)§ and job lease/status. Verify real query plans with §EXPLAIN ANALYZE§ and representative data.
- Every query includes workspace scope; composite FKs prevent cross-tenant attachment. Tenant isolation is a correctness requirement even under pooled connections.
- **Bound connection pools**: calculate §API_replicas × pool_per_replica + worker_connections + migrations/maintenance ≤ DB max_connections§, allowing headroom. Avoid opening one DB connection per active user.
- Use transaction boundaries for run+job creation, lead+audit save and scenario snapshot; keep DB transactions short while external fetch/inference runs **outside** transactions.
- Worker leasing: transactional row claim with §FOR UPDATE SKIP LOCKED§, lease expiry/renewal, bounded attempts and idempotency. Heavy writes may batch but cannot compromise referential integrity.
- Protect against hot rows in per-workspace quota counters (atomic updates with appropriate contention management).
- Use performance test data at least comparable to anticipated load (e.g., hundreds of workspaces, thousands of source records/signals, saved assessments and lead records). Do not test an empty DB and declare scale achieved.

## 7. Research workload, fairness, and provider budgets

Research is the primary capacity bottleneck, not the ability to render 500 client screens.

- Separate per-workspace/user submission limits from global provider worker concurrency, to avoid one account exhausting all free quota.
- Partition or fairly schedule jobs across workspaces (round-robin/weighted fair scheduling is an option); cap in-flight jobs per user and global source/API tasks.
- Publish job status **queued/running/partial/completed/failed/cancelled**, queue position/estimated availability only if actually computable, and source-specific errors.
- Cache/dedupe identical lawful source fetches under explicit attribution/retention limits; model cache keyed by model/schema/prompt/profile/source digest, with tenant privacy controls.
- Apply source rate limits and exponential backoff (with jitter and strict caps); provider quota exhausted → truthful 429/degraded/failed, not invented research.
- Avoid synchronous model calls in web and MCP request loops. MCP can return a run ID and a documented status polling tool.
- Record queue wait p50/p95, run duration, completion/failure, per-source calls, model tokens, cost/quota and pending age.
- **Do not promise all 500 founders can run expensive research simultaneously for ₹0** without verified compute/provider capacity. A queued experience that communicates limits is acceptable for first capacity objective only if the product remains usable and user expectations are honest.

## 8. Load test plan

### Phases

1. **Fixture correctness baseline:** reproduce 2 users/2 workspaces negative isolation, duplicates, and source provenance checks before load.
2. **Read/write baseline:** warm the test DB with realistic workspace contents; 50 users → 100 → 250 → **500** over 10 minutes, monitoring CPU, memory, query time, pool pressure and errors.
3. **Steady state:** 500 active authenticated virtual users for ≥15 minutes at target mix and measured 25 req/s aggregate; record p50/p95/p99 reads and writes.
4. **Burst:** maintain 500 sessions with 50 req/s interactive mix, plus a **bounded cluster** of research submissions (e.g., 50–75 near-simultaneously), verifying fast acceptance/throttling and queue fairness. Do not require that all 75 external research jobs finish immediately.
5. **Soak:** 60 minutes under the agreed mix; observe connection leakage, queue-age drift, memory and retry accumulation.
6. **Failure injection:** stop worker mid-job, simulate source 429/model outage, invalidate auth, restart API; normal read/write functionality must remain available and data must stay isolated.
7. **Security under concurrency:** concurrent cross-workspace requests, repeated idempotency keys and racing CRM stage edits; zero unauthorized access and no duplicate side effects.
8. **Report:** include test date, environment, code SHA, host resource tier, DB limits, user count, exact requests/s, rate limits, latency distributions, 5xx, 429, queue depth/wait times, CPU/memory/DB, provider quota and conclusion. Report cannot overclaim beyond measured workload.

### Suggested tools

Use **k6** or **Locust** for application-level virtual users, plus **Playwright** for a small set of concurrent realistic UI sessions. Do not simulate 500 headless Chromium browsers as the sole measure if the load generator itself becomes the bottleneck. Use low-privilege synthetic/test identities; do not send real outreach or trigger unbounded source fetches against third parties during stress testing. Stub/mock external providers for capacity benchmarks, then run a **small separately bounded live-provider integration sample**, accurately labeling each.

## 9. Capacity, cost and release decisions

- **Before claiming 500 users:** benchmark actual deployment or representative production-like tier, not only localhost.
- **If a chosen managed hosting tier cannot pass:** document the measured bottleneck and legitimate paid resource upgrades or reduce the claimed service level with **explicit owner approval**; do not silently loosen test loads, quota constraints or interpretation.
- **If database connection caps are low:** adjust pool sizes/replicas, consider approved managed pooling and cache; quantify benefit before adding another service.
- **If worker concurrency is low:** preserve 500-user interactive app usability while transparently queueing/limiting external research, and report queue completion limits.
- **If provider terms or budget prohibit testing with real traffic:** run isolated provider mocks with clear labels and separately verify actual permitted live adapter behavior.

**Review gates:** CAP-01–CAP-10, confirmed host/provider free-tier limits, traffic mix, source/LLM rates and retention. Record decisions in [DECISIONS.md](DECISIONS.md). The 500-founder objective is owner-requested but **performance acceptance is pending load evidence**.

## 10. Relationship to November 26 MVP

The approved release gates still require an actual deployable end-to-end research journey. Design for scalable stateless services, pooling and bounded queue **now**, but do not abandon working core features to build speculative multi-region infrastructure. The 500-founder design is an explicit nonfunctional target to validate. Whether it is a **hard November 26 release block** versus a post-submission capacity milestone must be recorded as an explicit owner decision, not inferred from this draft.

**Status at creation:** no load tests run, no production concurrency measured, no 500-user capacity verified.

## 11. Hosting cost/scale decision boundary

The founder approved **managed infrastructure with a modest potential hosting budget**, [ADR-008](decisions/008-managed-hosting-and-worker.md). Scaling from one API process/worker to multiple replicas may incur additional costs and DB connection pressure; **no capacity-based scaling purchase is authorized without exact plan and cost review**. The separate **₹0 paid external AI/research API** rule still applies. 500 active founders is a **performance design and load-test target**, not an achieved guarantee, and never means 500 simultaneous free-LLM calls.

## 12. Broad provider scaling and fairness

[ADR-004](decisions/004-broad-authorized-source-integration.md) expands the target integration families. Each enabled adapter has **independent** provider-wide rate limits, backoff, circuit-breaker/disable controls, per-workspace quotas and availability reporting. Under 500 active founders, a single source's quota/permission loss cannot stall unrelated source jobs, and no user may monopolize public-source processing. New providers are activated only after legitimate access and real sample tests; Reddit/additional services are **not** assumed available. Synthetic load testing must use provider stubs to avoid violating platform policies or spending on external research APIs; real provider smoke stays bounded.
