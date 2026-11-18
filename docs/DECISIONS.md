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

**Crucial distinction:** the owner approved the auth/data stack ([ADR-002](decisions/002-authentication-database-and-api-boundary.md)) and managed-hosting strategy ([ADR-008](decisions/008-managed-hosting-and-worker.md)); **no particular frontend/worker vendor, subscription, cost, uptime, AI provider, source API, or deployed capacity is verified or purchased**.

## 3. Open technology decisions

| ID | Question | Candidate/default | Evidence required | Status |
|---|---|---|---|---|
| ADR-001 | Backend app/worker process deployment | One FastAPI codebase + worker process | Hosting probe, durable lease/restart | Proposed |
| [ADR-002](decisions/002-authentication-database-and-api-boundary.md) | Identity and workspace policy | Supabase Auth, JWT validation, FastAPI-only domain access, RLS defense | Real login and cross-tenant tests still required | **Approved choice — implementation unverified** |
| ADR-003 | Database hosting and migration implementation | **Chosen:** Supabase PostgreSQL, SQLAlchemy 2.x + Alembic (per ADR-002) | Actual DB project/quota, migrations, backup, pooling and RLS tests | **Approved stack — implementation unverified** |
| ADR-004 | Permitted discovery source families | HN, approved RSS, Bluesky candidate | Live retrieval, terms, usefulness, limits | Open |
| [ADR-005](decisions/005-ai-inference-providers.md) | Groq primary; Gemini conditional privacy/consent-gated fallback | Verify current no-charge quotas, provider terms, model quality and real calls | **Approved strategy — implementation unverified** |
| ADR-006 | MCP remote auth and version | Python SDK, Streamable HTTP | External client handshake, scope/denied write | Open |
| ADR-007 | Frontend/graph libraries and visual tokens | Next.js + accessible graph/list | Build, interaction/accessibility stress | Open |
| [ADR-008](decisions/008-managed-hosting-and-worker.md) | Managed frontend + FastAPI API + dedicated worker; modest hosting spend allowed | Actual host choice, terms/pricing, worker restart, HTTPS and capacity load tests | **Approved strategy — provider/cost and deployment unverified** |
| ADR-009 | Data retention and source excerpts | Minimal permitted excerpts | Policy/terms and deletion review | Open |

## 3A. Founder-approved technical decision 1 of 6 (18 November 2026)

**Option A selected:** Supabase Auth + Supabase-hosted PostgreSQL + FastAPI sole application data API + SQLAlchemy 2.x + Alembic. See [ADR-002](decisions/002-authentication-database-and-api-boundary.md). This approves the stack and access boundary, **not** the configuration, cost, throughput, or operational verification. Remaining infrastructure, model, sources and MCP choices are still open.

## 3B. Founder-approved technical decision 2 of 6 (18 November 2026)

**Option A selected:** Managed hosting with a modest infrastructure budget: a suitable web frontend host (Vercel or an eligible equivalent), a continuously runnable FastAPI service and **separately executed durable research worker** (Railway or an eligible equivalent), and previously approved Supabase Auth/PostgreSQL. [ADR-008](decisions/008-managed-hosting-and-worker.md) governs. Provider selection and paid plan costs require a separate review before purchase. **The ₹0 external AI/research API budget remains unchanged.** No claim of tested hosting/500-user capacity.

## 3C. Founder-approved technical decision 3 of 6 (18 November 2026)

**Option C:** Groq as primary inference, Gemini as a privacy/terms-gated fallback through a shared model adapter ([ADR-005](decisions/005-ai-inference-providers.md)). No silent fallback of confidential founder ideas, profiles, CRM data or mixed inputs to a free tier with unverified data-use conditions; use deterministic/manual degradation if not permissible. **₹0 paid external AI/research API spending** remains unchanged. Provider model IDs, terms, quotas, actual requests and quality remain unverified.

## 3A. New founder requirements (18 November 2026)

| ID | Decision / scope | Status | Notes |
|---|---|---|---|
| DEC-007 | Design for **500 founders concurrently active**; no untested concurrency guarantee | **Owner requested** | Capacity implementation and exact release gate are unapproved pending [18-SCALABILITY.md](18-SCALABILITY.md) testing/decision |
| DEC-008 | Use [edviro-clone](https://github.com/ThunderKhan/edviro-clone) layout, typography, spacing, navigation and landing animations as Axiom design **reference**, with Axiom-specific content | **Owner direction** | Final colors and user-supplied design-system file pending; [13-DESIGN.md](13-DESIGN.md) **ON HOLD** |
| DEC-009 | Remove accidental T-shirt effort-sizing document; maintain necessary effort/risk notes in roadmap | **Owner clarification** | [16-IMPLEMENTATION-ROADMAP.md](16-IMPLEMENTATION-ROADMAP.md) records sizing |

| DEC-010 | Founder-approved Axiom palette (`--bg` #FAF7F1, `--band` #F1EAE2, `--ink` #302B32, `--text` #655B61, `--muted` #766B70, `--line` #302B3221, `--green` #AC4E30, `--deep` #271F28, `--leaf` #F2A487, `--tint` #F6E2D7) applies to all public and authenticated pages | **Approved — 18 Nov 2026** | [13-DESIGN.md](13-DESIGN.md) Section 3; **full design still ON HOLD** |

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

- Confirm R0 3+ source families under lawful access and ₹0 provider budget.
- **Hosting strategy approved:** managed web/API plus durable worker, modest infrastructure charges permitted. Confirm an **actual worker** runs on selected hosting; choose specific providers, instance costs and test restart before deployment acceptance.
- **AI routing approved** ([ADR-005](decisions/005-ai-inference-providers.md)); verify real Groq/Gemini no-charge inference, terms/data handling/consent, structured outputs, quota and deterministic degraded path.
- Resolve MCP client auth and write approval, not just a tool list.
- **Stack chosen:** Supabase Auth/PostgreSQL/FastAPI/SQLAlchemy/Alembic. **Still verify** exact PostgreSQL schema, JWT validation, RLS/privileged server behavior and actual deployment.
- Reconcile scope and tech targets at November 19 and 22 gates; record evidence.

This register tracks decisions, **not implementation completion**. See [16-IMPLEMENTATION-ROADMAP.md](16-IMPLEMENTATION-ROADMAP.md) and [14-TESTING-STRATEGY.md](14-TESTING-STRATEGY.md).
