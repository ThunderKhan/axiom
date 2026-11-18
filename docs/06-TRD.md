# Axiom — Technical Requirements Document (TRD)

**Status:** APPROVED — technical requirement baseline; vendor/hosting choices remain unapproved  
**Version:** 1.0 · **Date:** 18 November 2026 · **Release:** 26 November 2026, 23:59 IST  
**Authority:** [PRD](02-PRD.md) · [MVP](03-MVP.md) · [User Flows](04-USER-FLOWS.md) · [System Architecture](05-SYSTEM-ARCHITECTURE.md)

## 1. Scope, precedence and terminology

The TRD states **technology choices, engineering constraints and objectively testable technical requirements**. It does not replace product specifications, implementation-oriented coding rules in root `ENGINEERING.md`, or agent instructions in root `AGENTS.md`. The [documentation index](01-INDEX.md) governs status/reading order. Technology options below are **proposed**, not asserted to be deployed. Unresolved vendor/free-host choices must pass feasibility tests and be recorded as decisions.

**P0** is the essential verified product release floor; **R0** is an additional founder-requested November 26 objective that cannot be silently deferred. Advanced Counterfactual Lab, 3+ permitted sources, advanced CRM and extensive MCP are R0, not automatically out of scope. **₹0 planned external AI/research API expenditure** is an explicit constraint; don't infer hosting, quota or capacity is free.

## 2. Proposed technology selection

| Layer | Candidate | Decision/proof |
|---|---|---|
| Web | Next.js maintained LTS, React, TypeScript strict | Pin compatible package versions and run production build |
| UI | Tailwind CSS + accessible component primitives; purpose-built editorial layouts | Test focus, keyboard, mobile, reduced motion |
| Evidence graph | @xyflow/react, or measured equivalent | Test keyboard/list parity and dense graphs |
| API | Python 3.12+, FastAPI, Pydantic v2 | Type validation, OpenAPI and deployment support |
| Database | **Supabase-hosted PostgreSQL (approved)** | Migrations, isolation, quota and persistence proof |
| Auth | **Supabase Auth (approved)** | Verified JWT issuer/signature/audience/expiry, normal login |
| DB access | **SQLAlchemy 2.x + Alembic (approved)** | Verify clean-install, upgrade and role isolation |
| Async jobs | PostgreSQL-backed queue, independent Python worker process | Test live process, lease and restart on actual host |
| Data sources | **Broad acquisition:** Hacker News, allowed RSS/Atom, Bluesky, Reddit **if officially authorized**, manual URLs and more vetted platforms ([ADR-004](decisions/004-broad-authorized-source-integration.md)) | Strategy approved, per-provider permission/terms/quotas/live usage unverified |
| Model | **Groq primary with conditional Gemini fallback** ([ADR-005](decisions/005-ai-inference-providers.md)) | Verify current no-charge quota, policy/consent, models, typed output and latency |
| External agent protocol | **MCP Streamable HTTP + OAuth 2.1 delegated scoped clients** ([ADR-006](decisions/006-mcp-oauth-and-write-approval.md)) | Authorization server, PKCE/metadata, resource-bound tokens, consent/revocation and actual client test required |
| Quality | pytest, Playwright, lint/type/build, migrations and security tests | CI and deployed smoke evidence |
| Hosting | **Managed web + managed FastAPI/worker + Supabase** ([ADR-008](decisions/008-managed-hosting-and-worker.md)) | Strategy approved; provider/plan, cost and real worker uptime not verified |

**TRD-STACK-01:** Production dependencies must have reproducible lockfiles; record chosen version and license.
**TRD-STACK-02:** **Modest paid hosting/infrastructure is allowed under ADR-008**; require explicit approval of any specific paid plan/cost before provisioning. **Paid AI/research APIs remain excluded** under the ₹0 external API constraint; do not use inaccessible or policy-incompatible services.
**TRD-STACK-03:** Main API and research worker share typed domain services, not duplicated business rules. Avoid unnecessary Redis/Kafka/microservices for initial release.

## 3. Web requirements

- **TRD-FE-01 (P0):** Landing → login → authenticated application. No public judge-only or guest workspace.
- **TRD-FE-02:** Main application must support multiple workspaces, conversational adaptive onboarding (approximately 10–15 questions), opportunity feed, investigation, competitors, graph+report, scenarios and CRM.
- **TRD-FE-03:** TypeScript strict mode; typed API contracts generated/validated from OpenAPI; current workspace ID included in query/cache isolation.
- **TRD-FE-04:** On every async operation render distinct queued, running, partial, completed, empty, failed, stale/cache and seeded states; never show false completion.
- **TRD-FE-05:** Evidence graph accessible by keyboard and equivalent textual/report UI on mobile; do not require dragging to inspect citations.
- **TRD-FE-06:** Proper focus, labels, contrast, reduced-motion and responsive behavior; no privileged tokens bundled client-side.
- **TRD-FE-07 (R0):** Real multi-scenario editor/compare and advanced lead/follow-up workflows, not static demonstration screens.

**Verify:** real login and workspace-switch Playwright tests, mobile viewports, graph keyboard access, no cross-workspace stale display, proper session expiration.

## 4. Backend, data and job requirements

- **TRD-BE-01:** Versioned JSON API with typed request/response DTOs, consistent validation/errors, health/readiness endpoints.
- **TRD-BE-02:** At least two independently callable real HTTP operations: discovery and competitor teardown. Web and MCP call identical application/domain use cases.
- **TRD-BE-03:** Authenticate and authorize *every* private read/write, including downloads, job progress and MCP calls; supplied workspace IDs do not prove authority.
- **TRD-BE-04:** Long research/extraction operations use bounded jobs, retries, rate limits, correlation IDs and durable progress state; no unbounded synchronous requests.
- **TRD-BE-05:** A crash/restart probe must prove a job is retried without duplicate business mutations. Prove a persistent worker on the chosen managed tier; paid infrastructure can be considered within an owner-reviewed hosting budget, but no unverified provider is accepted.
- **TRD-DB-01:** Workspace-scoped foreign keys, profile/source snapshot versioning, relational evidence nodes/edges, transactional CRM writes, idempotency.
- **TRD-DB-02:** Clean-install + upgrade migration tests, backup/restore plan and documented data deletion/retention policy.
- **TRD-DB-03:** Privileged Supabase service/secret credentials bypass RLS; server-side workspace checks remain mandatory, with RLS defense in depth where applicable.

**Verify:** migration dry run, cross-tenant IDOR on API/MCP, worker crash recovery, repeated lead-save and scenario replay test.

## 5. AI, provenance and research

- **TRD-AI-01:** Every public record records canonical URL, actual provider/source ID, fetched timestamp, excerpt, origin (live/cached/seeded/user-provided), limitations and stable evidence references.
- **TRD-AI-02:** Score relevance, solution intent, capability fit, freshness and evidence quality separately; rule/model methods and missing confidence exposed.
- **TRD-AI-03:** Structured LLM outputs validated with schema, source IDs and quoted locators; unsupported factual assertions marked unverified/unknown or rejected.
- **TRD-AI-04:** A company advertising a feature is sourced as *a claim*, not proof it works. Idea-stage features remain hypothetical.
- **TRD-AI-05:** Explicit Pursue, Research further, Skip and Insufficient evidence verdicts; hard mismatches/contradictions override attractive composite scores.
- **TRD-AI-06 (R0):** Two+ named scenarios with multiple assumptions/positioning and qualitative pricing changes; compare against frozen evidence snapshot; persist and reopen; no fabricated conversion/revenue forecasts.
- **TRD-AI-07:** Provider outages, exhausted free quotas and invalid model JSON yield honest deterministic degradation or failure, not fake model research.
- **TRD-DATA-01:** Only legitimately accessible public sources; source adapter registry must document terms, permissions, quota, usage and fallback.
- **TRD-DATA-02:** Safe external URL fetch with DNS/IP and redirect revalidation, size/time limits, HTML escaping, no bypass of authentication/paywalls.

**Verify:** labeled 10+ cases including strong fit, false positive, high intent/poor fit, unknown pricing, absent evidence, prompt injection, model outage and scenario reproducibility. All material external competitor statements must be cited or explicitly unverified.

## 6. MCP and integration

- **TRD-MCP-01 (P0):** Real authenticated external MCP client can invoke discover_opportunities, research_competitor, assess_opportunity, list_saved_leads and save_lead.
- **TRD-MCP-02 (R0):** Independently track update_lead_stage, create_followup, inspect_evidence, compare_scenarios, generate_outreach_draft, list_workspaces and appropriate monitoring tools.
- **TRD-MCP-03:** Typed inputs, outputs, error codes, workspace scoping, least-privilege authorization, audit and safe idempotency for writes.
- **TRD-MCP-04:** User-approved scopes and sensitive-action approval semantics; no unrestricted write/admin token, autonomous sending, secret exposure or bypass via agent content.
- **TRD-MCP-05:** Test MCP transport/protocol version and deployment host/origin settings using a genuine client.

## 7. Security and privacy

- **TRD-SEC-01:** Verify JWT cryptographically (issuer, signature, audience and expiry); fail closed; provision evaluator credentials privately without committing them.
- **TRD-SEC-02:** Enforce workspace membership on every object and background job, even with service-role database access.
- **TRD-SEC-03:** SSRF/DNS rebinding, redirects, XSS and prompt-injection test fixtures required before public URL analysis.
- **TRD-SEC-04:** No automatic cold outreach; AI drafts are editable and explicitly unsent.
- **TRD-SEC-05:** Redacted audit logs, per-workspace quotas, secure secrets and private data retention/deletion decision.
- **TRD-SEC-06:** Avoid leaking competitors' raw HTML or sources into client rendering without sanitization.

## 8. Proposed non-functional targets

Targets below are **proposals until benchmarked**; do not advertise them as achieved SLAs.

| Area | Candidate acceptance | How to measure |
|---|---|---|
| UI responsiveness | User sees accepted research job state within ~1s | Browser traces |
| Cached API p95 | ≤800ms at light demo load, excluding upstream source fetch | Repeatable benchmark |
| Authenticated app usability | First useful view ≤3s on typical broadband, excluding live research | Playwright 20 runs |
| Tenant isolation | Zero unauthorized cross-tenant access in negative suite | API, DB, MCP tests |
| Data integrity | No duplicate CRM writes after retry/double submission | Idempotency and crash tests |
| Fact attribution | Every external competitor fact source-backed or tagged unverified | Labeled assessment set |
| Accessibility | No critical automated audit failures; keyboard paths functional | Playwright/axe and manual |
| Deployment | HTTPS frontend+API+worker actually function and recover | Production-like smoke/restore |
| Budget | ₹0 paid external AI/research API usage | Actual provider quotas and usage |

## 9. Required operations and documentation

- Lockfiles, .env.example (variable **names only**), local/test/deployment instructions, versioned migrations, OpenAPI, documented real model/source provider IDs and fallbacks.
- CI checks: install, build, lint, type, unit/API/security and DB migration tests; separate real-source and hosted browser smoke.
- Structured logs with request/run/workspace IDs (opaque) and redacted secrets; no production passwords or sensitive prompts in logs.
- Release proof: tested evaluator account, two live source families targeted and 3+ R0 coverage assessed, real competitor extraction, graph/report, 2 saved scenarios, CRM persistence and external MCP.
- Requirement traceability to PRD FR-01…FR-12, MVP-01…MVP-14 and [14-TESTING-STRATEGY.md](14-TESTING-STRATEGY.md).

## 10. Open technical decisions

| Decision | Proof needed | Status |
|---|---|---|
| Auth and DB implementation | **Approved stack: Supabase Auth, PostgreSQL, FastAPI-only domain access, SQLAlchemy + Alembic**. Verify login, JWT, RLS and API ownership | **Chosen — not implemented** |
| Hosting and worker | Real deployment, queue claim, completion after restart | Open |
| Free model/provider | **Groq primary, Gemini conditional strategy approved**; actual provider calls, privacy/consent, quotas and failures | **Chosen — not verified** |
| Broad source-family program | **Approved target**: 3+ families R0 plus additional authorized platforms, Reddit permission pending. Require lawful access, live samples, quota and provenance | **Scope approved — integration unverified** |
| MCP auth/protocol | **OAuth 2.1 strategy approved** ([ADR-006](decisions/006-mcp-oauth-and-write-approval.md)); choose AS, implement metadata, scoped consent and denied writes, test client | **Chosen — not implemented** |
| Migrations / ORM | Clean/upgrade/schema drift test | Open |
| Graph library | Keyboard/mobile accessible view + performance sample | Open |

**Approval:** Technology choices and targets remain proposed until reviewed; architectural direction approved on 18 November 2026 does not imply any hosted provider or specific library has been tested.

**Official implementation references:** [Next.js supported releases](https://nextjs.org/support-policy), [Supabase JWT](https://supabase.com/docs/guides/auth/jwts), [Supabase RLS](https://supabase.com/docs/guides/database/postgres/row-level-security), [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).

**Selected foundation (owner decision 1 of 6):** [ADR-002](decisions/002-authentication-database-and-api-boundary.md) governs Supabase Auth/PostgreSQL, FastAPI-only domain data reads/writes and SQLAlchemy 2.x/Alembic. This supersedes the conflicting *candidate* wording above without asserting operational completion.

## 11. Owner-requested capacity target: 500 concurrent founders

**TRD-CAP-01:** Design for at least **500 concurrently active, authenticated founders**, not 500 unlimited simultaneous external AI/crawler jobs. The 500-user target concerns active sessions and responsive normal workflows; expensive research uses bounded, fair asynchronous jobs with truthful status/quotas.

**TRD-CAP-02:** Implement and benchmark **25 requests/s** steady and **50 requests/s** heavier interactive traffic as initial *model assumptions* (not measured production traffic), with 500 simulated active identities/workspaces. Profile p95 DB-backed reads, CRM writes, job acceptance, error rates, queue wait, DB connections, worker capacity and source/model quota.

**TRD-CAP-03:** No service may open one DB connection per founder; stateless API, pooled connections, indexed workspace queries, bounded worker concurrency and jittered/backoff job polling are required. Denial-of-service and cross-tenant correctness tests remain release blockers.

**TRD-CAP-04:** This capacity objective cannot be marketed as **achieved** until the selected deployment passes the reproducible load/soak/failure test in [18-SCALABILITY.md](18-SCALABILITY.md). Whether 500 verified users is a hard November 26 gate or a later capacity milestone remains a founder decision; it is **not silently a waived objective**.

**Approval boundary:** Owner-approved TRD requirements and architecture direction are authoritative; every technology labeled candidate/proposed stays contingent on real provider, cost, license, and deployability evidence. Approval does not claim a built backend or 500-user capacity.

## 12. Approved managed-hosting strategy (decision 2 of 6)

[ADR-008](decisions/008-managed-hosting-and-worker.md) approves a **managed frontend, independently running managed FastAPI API and research worker, and Supabase Auth/PostgreSQL**. Vercel and Railway are **candidate hosts only**. Distinguish *permitted infrastructure spend* from the **still-₹0 external AI/research API spending** requirement. Record actual host/plan price, allowed use, worker/restart results, scaling limits and database connection caps before deployment approval. No deployment or 500-founder capacity has been verified by the document change.

## 13. AI model routing requirements (decision 3 of 6)

- **TRD-AI-08:** A single typed model adapter sends eligible jobs to Groq first. Gemini free-tier fallback requires per-request data classification, verified current terms permitting that input and applicable consent; **no silent disclosure of founder-private ideas, profile, CRM, notes, drafts, or mixed/unknown content**.
- **TRD-AI-09:** If neither route is permissible or available, show honest deterministic/manual degradation or blocked/unavailable status; keep source/citation validation, bounded retries and redacted model trace information.
- **TRD-AI-10:** Verify actual no-charge API calls, model versions, data policies, limits, 429/timeout behavior, license/terms, and maintain **₹0 paid external AI/research API** spend. See [ADR-005](decisions/005-ai-inference-providers.md). This is strategy approval, **not** integration completion.

## 14. Broad source strategy — decision 4 of 6

- **TRD-DATA-03:** Per [ADR-004](decisions/004-broad-authorized-source-integration.md), maintain an extensible source-adapter registry for HN, permitted RSS/Atom, Bluesky, Reddit **after specific authorization**, manual safe URLs and further legitimate platforms. Track target/disabled/permission-pending/verified-live per family, with current terms, license, quota, retention and actual sample evidence.
- **TRD-DATA-04:** Neither an adapter name nor internet reachability proves provider permission. **Do not run Reddit or any access-restricted API before permitted credentials and acceptable terms are verified**; do not circumvent API restrictions or pay external research API charges under the current ₹0 rule.
- **TRD-DATA-05:** Keep P0 two genuine families and R0 three-plus families, **plus expanded legal platform breadth as a founder-approved target**. Report status of each target and escalate blockers for explicit founder scope decisions. Count distinct connectors/platform families; label manually provided, seeded, cached, and live evidence honestly.
- **TRD-DATA-06:** Apply normalized schemas, source attribution, rate-limit/error controls, dedupe, SSRF-safe URL checks and 500-founder fair job admission to every enabled adapter. This approval does not verify or implement any source.

## 15. MCP authorization requirements (technical decision 5 of 6)

- **TRD-MCP-06:** Use OAuth 2.1 Authorization Code + PKCE S256 for user-delegated remote MCP connections with protected resource and authorization-server metadata/discovery, resource/audience-bound tokens and correct issuer validation.
- **TRD-MCP-07:** Select a compatible OAuth authorization server/broker integrating **Supabase Auth user identity**; a browser Supabase JWT must not automatically be accepted as a token for Axiom MCP resource. Confirm consent and client registration/discovery support.
- **TRD-MCP-08:** Each tool call checks granted scopes **and** user/workspace/object authorization; enforce revocation, idempotent low-risk consented CRM writes, separate confirmation for sensitive changes, and complete audit.
- **TRD-MCP-09:** Initial remote MCP mode excludes personal API tokens and hybrid auth. [ADR-006](decisions/006-mcp-oauth-and-write-approval.md) is strategy approval, **not** verified AS or tool compatibility.
