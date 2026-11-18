# ADR-008 — Managed Hosting with Dedicated Research Worker

**Status:** APPROVED — hosting *strategy*, provider assignments pending verification  
**Decision date:** 18 November 2026  
**Decision owner:** Axiom founder (technical decision 2 of 6)  
**Related:** [ADR-002 (identity/database)](002-authentication-database-and-api-boundary.md), [Architecture](../05-SYSTEM-ARCHITECTURE.md), [TRD](../06-TRD.md), [Deployment Runbook](../15-DEPLOYMENT-RUNBOOK.md), [Scalability](../18-SCALABILITY.md)

## Context

Axiom serves an authenticated Next.js app, FastAPI domain API, independently runnable research/AI worker, and Supabase-hosted PostgreSQL/Auth. Research jobs must outlive an individual HTTP request and survive a process restart. The founder intends to design for 500 concurrently active founders, with bounded rather than limitless concurrent AI/source operations. A strict ₹0 **external AI/research API** spend constraint exists, but is not a general prohibition on infrastructure spending.

### Options considered

- **A — Managed services and modest hosting budget:** Use suitable managed frontend and Python process hosting, including a durable worker process, with Supabase Auth/PostgreSQL. Candidate frontend host: Vercel *if terms and plan permit the actual use* or another compatible managed host. Candidate API/worker host: Railway *if pricing, uptime, background-process support, and deployment constraints are acceptable* or an equivalent provider. This is the **approved strategy**.
- **B — Strict ₹0 hosting:** No infrastructure charges; could lack always-on worker/uptime guarantees and impose major capacity/deployment limitations. Rejected as a hard limitation.
- **C — Single self-managed VPS:** Offers process control but increases operational/security burden. Not chosen as the default.

## Approved decision

1. **Managed hosting** is the default deployment strategy. A **modest paid infrastructure budget is permitted where necessary** for stable app/API/worker operations; actual amounts and subscriptions are **not authorized** by this ADR.
2. The web frontend is hosted on a suitable managed web platform. **Vercel is a candidate**, not a final vendor commitment; verify the account's allowed use, plan restrictions, and actual costs before deployment.
3. The **FastAPI API and dedicated Python research/AI worker** deploy as two process roles from the **same modular backend codebase**, with independent start commands and compatible managed runtime. **Railway is a candidate**, not an asserted purchase or successfully tested host.
4. **Supabase Auth and Supabase-hosted PostgreSQL remain approved** under ADR-002; backend/worker access is server-side only, FastAPI remains the only domain-data interface for clients.
5. Use a **durable PostgreSQL-backed job queue**, with bounded leases, retries, idempotency, worker restarts, fair admission, source/model quotas, and visible pending/partial/failure states. Final job implementation and production load capacity require tests.
6. **₹0 external AI/research API expenditure stays in force.** Paying for hosting **does not authorize paid LLM or research APIs** or violate that separate budget classification. Costs of API, database and worker hosting must be tracked independently from AI/research provider usage.
7. Design the deployment to **scale toward 500 concurrently active authenticated founders**, not 500 unlimited simultaneous external AI requests. Horizontal scale, connection pooling and job limits are governed by measured bottlenecks, not assumed from provider marketing.

## Rationale

Managed processes avoid the operational complexity of maintaining a Linux VPS while allowing a dedicated worker, secure secrets/configuration and separate API/frontend deployment. A modest infrastructure budget reduces the risk of choosing a nominally free platform that cannot run a durable worker. This strategy preserves the approved modular system design and future capacity option.

## Explicit non-decisions and safety constraints

- **Not selected or purchased:** final frontend host, Python host/worker plan, exact service region, instance sizes, autoscaling policy, monthly cap, and billing details.
- **Not asserted:** Railway/Vercel free-tier eligibility, permanent hosting, production availability, sustained worker reliability, or success of any 500-user benchmark.
- Production deployment requires founder review of the exact monthly **hosting** expense before enabling a paid resource.
- Hosting may need more than one API replica or worker as benchmarks dictate, subject to PostgreSQL connection limits, rate limits and source/LLM quota.
- Provider terms must permit the intended commercial/fellowship use and external API/MCP access. Do not implicitly rely on a personal-only hosting plan if disallowed.
- No direct public access to privileged worker/database ports; HTTPS for app/API/MCP endpoints; secrets server-side; least-privileged evaluator accounts.

## Verification requirements before marking deployment complete

1. Record actual selected host(s), billing plan, expected monthly range, resource limits, terms, region, and domain/TLS setup.
2. Deploy frontend + FastAPI and a **long-lived worker** process; create a real job, observe completion, terminate/restart worker mid-job and confirm safe retry/deduplication.
3. Connect to the approved Supabase database with bounded pool; run Alembic migrations, workspace isolation and API/MCP authentication negative tests.
4. Verify job queue admission controls, provider 429/timeouts and partial-result reporting with realistic examples.
5. Benchmark the documented 500-active-founder target on a representative actual tier before claiming it; report achieved request rate, latency, queue age, DB connection use and costs.
6. Preserve the original ₹0 external AI/research API limit, with provider usage checks separate from hosting invoices.

## Revisit conditions

If the chosen managed vendor disallows the intended use, the worker cannot run reliably, monthly cost is unacceptable, or capacity cannot meet tested requirements, compare other eligible managed providers (or a revised VPS option) and record an updated ADR. No product scope commitment is waived silently.

**Approval record:** The founder selected **Option A** for technical decision 2 of 6 on 18 November 2026. This document records strategy approval, **not vendor procurement or proof of deployed functionality**.
