# Axiom — Decision Register

**Status:** ACTIVE — canonical decision register (individual decision statuses remain authoritative) · **Date:** 18 November 2026  
**Authority:** [Documentation Index](01-INDEX.md), [PRD](02-PRD.md), [MVP](03-MVP.md), [Architecture](05-SYSTEM-ARCHITECTURE.md)

## 1. Decision states

**Approved:** explicitly authorized by the founder, with scope and date. **Proposed:** recommended but not decided. **Blocked:** external verification missing. **Superseded:** replaced by later approved decision. GitHub commits alone do not mean approval.

## 2. Recorded founder-approved decisions

| ID | Decision | Status | Evidence |
|---|---|---|---|
| DEC-001 | Product Axiom: market-demand discovery + competitor intelligence + evidence-driven decisions for idea-stage and launched founders | Approved | PRD v1.0, 18 Nov |
| DEC-002 | Full breadth-first November 26 MVP including R0 advanced Counterfactual, CRM, many sources and extensive MCP objectives | Approved | MVP v1.0, 18 Nov |
| DEC-003 | Single entry flow public landing → normal login → authenticated app; private evaluator credentials; no guest/judge demo | Approved | PRD v1.0 |
| DEC-004 | Adaptive 10–15-question onboarding; default Opportunities; evidence graph + accessible report; editorial UX | Approved | PRD, User Flows v1.0 |
| DEC-005 | Modular FastAPI system, shared domain use cases and bounded independently runnable worker as **architectural direction** | Approved | Architecture v1.0, 18 Nov |
| DEC-006 | ₹0 planned external AI/research API spending, genuine sources, clear seeded/hypothetical labeling, human-reviewed unsent drafts | Approved | PRD/MVP |

**Crucial distinction:** six architectural **strategies** have been approved. None of this asserts a purchased host, deployed worker, functioning AI/source API, configured MCP OAuth authorization server, correct live-provider permissions, or measured 100/250/500 active-user capacity. Exact vendor plans and any purchases still require approval.

## 3. Open technology decisions

| ID | Question | Candidate/default | Evidence required | Status |
|---|---|---|---|---|
| ADR-001 | Backend app/worker process deployment | One FastAPI codebase + worker process | Hosting probe, durable lease/restart | Proposed |
| [ADR-002](decisions/002-authentication-database-and-api-boundary.md) | Identity and workspace policy | Supabase Auth, JWT validation, FastAPI-only domain access, RLS defense | Real login and cross-tenant tests still required | **Approved choice — implementation unverified** |
| ADR-003 | Database hosting and migration implementation | **Chosen:** Supabase PostgreSQL, SQLAlchemy 2.x + Alembic (per ADR-002) | Actual DB project/quota, migrations, backup, pooling and RLS tests | **Approved stack — implementation unverified** |
| [ADR-004](decisions/004-broad-authorized-source-integration.md) | Data-source acquisition | **Broad permitted-platform target**, including HN, RSS, Bluesky and Reddit only with specific access authorization | Terms, credentials, quotas, legal approval, live results | **Approved strategy — source access unverified** |
| [ADR-005](decisions/005-ai-inference-providers.md) | AI inference providers | **Groq primary + Gemini conditional privacy/consent-gated fallback** | Provider terms, consent/data handling, actual no-charge calls, model quality | **Approved strategy — model integration unverified** |
| [ADR-006](decisions/006-mcp-oauth-and-write-approval.md) | MCP client authorization | **OAuth 2.1 delegated tokens**, PKCE, consent and scopes; no initial personal tokens | Choose AS, metadata, revocation, external client and safe writes | **Approved strategy — MCP integration unverified** |
| ADR-007 | Frontend/graph libraries and visual tokens | Next.js + accessible graph/list | Build, interaction/accessibility stress | Open |
| [ADR-008](decisions/008-managed-hosting-and-worker.md) | Hosting and worker | **Managed web/API + dedicated worker**, modest hosting spend allowed | Exact host/tier, price, restart, security, scale tests | **Approved strategy — hosting unverified** |
| ADR-009 | Data retention and source excerpts | Minimal permitted excerpts | Policy/terms and deletion review | Open |
| [ADR-010](decisions/010-staged-500-founder-capacity-release.md) | Capacity/release gate | **Option B**: design for 500 now; test 100/250 before Nov 26; pass 500 before broad production | Test harness, actual 100/250 results and pre-launch 500 benchmark | **Approved staging — capacity unverified** |

## 3A. Founder-approved technical decision 1 of 6 (18 November 2026)

**Option A selected:** Supabase Auth + Supabase-hosted PostgreSQL + FastAPI sole application data API + SQLAlchemy 2.x + Alembic. See [ADR-002](decisions/002-authentication-database-and-api-boundary.md). This approves the stack and access boundary, **not** the configuration, cost, throughput, or operational verification. Remaining infrastructure, model, sources and MCP choices are still open.

## 3B. Founder-approved technical decision 2 of 6 (18 November 2026)

**Option A selected:** Managed hosting with a modest infrastructure budget: a suitable web frontend host (Vercel or an eligible equivalent), a continuously runnable FastAPI service and **separately executed durable research worker** (Railway or an eligible equivalent), and previously approved Supabase Auth/PostgreSQL. [ADR-008](decisions/008-managed-hosting-and-worker.md) governs. Provider selection and paid plan costs require a separate review before purchase. **The ₹0 external AI/research API budget remains unchanged.** No claim of tested hosting/500-user capacity.

## 3C. Founder-approved technical decision 3 of 6 (18 November 2026)

**Option C:** Groq as primary inference, Gemini as a privacy/terms-gated fallback through a shared model adapter ([ADR-005](decisions/005-ai-inference-providers.md)). No silent fallback of confidential founder ideas, profiles, CRM data or mixed inputs to a free tier with unverified data-use conditions; use deterministic/manual degradation if not permissible. **₹0 paid external AI/research API spending** remains unchanged. Provider model IDs, terms, quotas, actual requests and quality remain unverified.

## 3D. Founder-approved technical decision 4 of 6 (18 November 2026)

**Option C selected:** Broad multi-platform opportunity discovery with Hacker News, permitted RSS/Atom, Bluesky, **Reddit when specifically authorized**, safe manual public URLs and additional legitimate sources (see [ADR-004](decisions/004-broad-authorized-source-integration.md)). **This expands target scope beyond a three-family ceiling**, while preserving the P0 two-live-family floor and R0 at least three live families plus further breadth. Every provider must separately pass legal/API access, terms, cost/quota, attribution, deletion and live-results verification. **Reddit is a candidate requiring permission, not a presumed free API.** ₹0 paid external AI/research API spending is unchanged; unauthorized scraping is prohibited. No adapters are asserted deployed.

## 3E. Founder-approved technical decision 5 of 6 (18 November 2026)

**Option A:** OAuth 2.1 scoped remote MCP clients with PKCE, resource-bound tokens, discovery, user consent and revocation ([ADR-006](decisions/006-mcp-oauth-and-write-approval.md)). Supabase Auth authenticates users but **is not automatically an MCP OAuth authorization server**. Select/integrate a compatible authorization server and prove the real remote-client flow. Scope and write-consent architecture approved; specific provider, consent UI, token issuance and client handshake are not verified. No initial personal API tokens.

## 3F. Founder-approved technical decision 6 of 6 (18 November 2026)

**Option B selected:** Build the scalable API/DB/worker architecture for **500 concurrently active founders now**, run/report realistic **100- and 250-active-user** preliminary benchmarks before the November 26 fellowship submission, and **block wider public production rollout until a 500-active-founder load/soak/failure benchmark passes**. See [ADR-010](decisions/010-staged-500-founder-capacity-release.md) and [18-SCALABILITY.md](18-SCALABILITY.md). A fellowship deployment may be accurately labeled limited-capacity without the full 500 test if independent P0 functional/security release gates pass. No capacity tests have been verified yet.

## 3G. Additional founder directives (18 November 2026)

| ID | Decision / scope | Status | Notes |
|---|---|---|---|
| DEC-007 | Design for **500 active founders**; preliminary 100/250-user tests before submission, complete 500-user pass before wider production | **Approved — Option B** | [ADR-010](decisions/010-staged-500-founder-capacity-release.md); **performance unverified** |
| DEC-008 | **Directly reuse the Edviro-clone landing-page source code** inside Axiom, preserving layout, typography, animations, navbar and CTAs; replace all Edviro sections/content/images/brand | **Approved — 18 Nov 2026** | [13-DESIGN.md](13-DESIGN.md) v1.0; Axiom-owned adapted source, applicable MIT/font license notices and original/licensed imagery |
| DEC-009 | Remove accidental T-shirt effort-sizing document; maintain necessary effort/risk notes in roadmap | **Owner clarification** | [16-IMPLEMENTATION-ROADMAP.md](16-IMPLEMENTATION-ROADMAP.md) records sizing |
| DEC-010 | Founder-approved Axiom palette (`--bg` #FAF7F1, `--band` #F1EAE2, `--ink` #302B32, `--text` #655B61, `--muted` #766B70, `--line` #302B3221, `--green` #AC4E30, `--deep` #271F28, `--leaf` #F2A487, `--tint` #F6E2D7) applies to all public and authenticated pages | **Approved — 18 Nov 2026** | [13-DESIGN.md](13-DESIGN.md) v1.0 approved, with no additional design-system document required |

## 3H. Documentation review decision after six approvals

**Formally approved as architecture, standards, design direction or policies (not implementation proof):** `02-PRD.md`, `03-MVP.md`, `04-USER-FLOWS.md`, `05-SYSTEM-ARCHITECTURE.md`, `06-TRD.md`, `10-MCP-INTEGRATION.md` (protocol/permissions only), `11-DATA-SOURCES.md` (lawful acquisition policy only), `12-UI-UX-SPEC.md` (functional UX only), `14-TESTING-STRATEGY.md`, `16-IMPLEMENTATION-ROADMAP.md`, `17-SECURITY.md`, `18-SCALABILITY.md` (staged architecture/release gate only). Six ADRs are individually approved: 002, 008, 005, 004, 006 and 010.

**Not ready for whole-document approval:** `07-DATABASE-DESIGN.md` (exact DDL/RLS/migrations), `08-API-CONTRACTS.md` (frozen DTOs/OpenAPI/error model), `09-AI-ENGINE.md` (validated source/citation algorithms and provider/model evaluations), `15-DEPLOYMENT-RUNBOOK.md` (actual host/provisioning/backup/MCP OAuth provider/probes). `13-DESIGN.md` is **APPROVED** for direct Edviro landing-source reuse and full ten-token Axiom palette. Any image/branding substitution and responsive/animation tests are implementation work, not pending design approvals. Active register and documentation index are governance records, not product approvals.

**The founder has now approved the complete landing-page design direction and removed the prior design hold.** Directly copy the authorized Edviro clone's landing implementation into Axiom's own modules; replace Edviro brand/data/assets with Axiom equivalents and apply the approved palette to both public and authenticated pages. Code copying, asset replacement and QA remain implementation tasks, not additional approval questions.

All provider integrations, 100/250 preliminary load tests and 500-user production benchmark are **unverified until real evidence exists**. Approval of a design baseline does not waive its release gates.

## 4. ADR template and procedure

When a consequential decision is resolved, create `docs/decisions/NNN-topic.md` containing:
- **Date/status/decision owner**
- **Context and driving requirement IDs**
- **Options compared, tradeoffs and cost/security constraints**
- **Selected decision and actual test evidence**
- **Consequences, rejected alternatives and rollback path**
- **Affected docs/contracts and whether product requirements changed**

If a proposal affects an approved PRD/MVP commitment, require founder's **explicit product scope approval**, then update docs/index/ADR in same change. Do not silently treat an expired deadline, provider outage, or assistant preference as approval.

## 5. Pending issue / risk ledger

- **Broad authorized acquisition approved** ([ADR-004](decisions/004-broad-authorized-source-integration.md)); verify P0 two live families and R0 three-plus with further permitted-platform breadth. Reddit/additional sources remain gated by specific approval, live API access, source terms, quotas and ₹0 external research API spending.
- **Hosting strategy approved:** managed web/API plus durable worker, modest infrastructure charges permitted. Confirm an **actual worker** runs on selected hosting; choose specific providers, instance costs and test restart before deployment acceptance.
- **AI routing approved** ([ADR-005](decisions/005-ai-inference-providers.md)); verify real Groq/Gemini no-charge inference, terms/data handling/consent, structured outputs, quota and deterministic degraded path.
- **OAuth 2.1 MCP authorization strategy approved** ([ADR-006](decisions/006-mcp-oauth-and-write-approval.md)); authorization-server choice, actual scopes/consent, write-confirmation behavior, external client tests and revocation still require verification.
- **Stack chosen:** Supabase Auth/PostgreSQL/FastAPI/SQLAlchemy/Alembic. **Still verify** exact PostgreSQL schema, JWT validation, RLS/privileged server behavior and actual deployment.
- Reconcile scope and tech targets at November 19 and 22 gates; record evidence.

This register tracks decisions, **not implementation completion**. See [16-IMPLEMENTATION-ROADMAP.md](16-IMPLEMENTATION-ROADMAP.md) and [14-TESTING-STRATEGY.md](14-TESTING-STRATEGY.md).
