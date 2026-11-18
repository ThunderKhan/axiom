# Axiom — Decision Register

**Status:** DRAFT — working register · **Date:** 18 November 2026  
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

**Crucial distinction:** approving architecture **does not approve or verify** a specific hosting provider, source API, auth system, AI model or background worker's deployed feasibility. Those remain open below.

## 3. Open technology decisions

| ID | Question | Candidate/default | Evidence required | Status |
|---|---|---|---|---|
| ADR-001 | Backend app/worker process deployment | One FastAPI codebase + worker process | Hosting probe, durable lease/restart | Proposed |
| ADR-002 | Identity and workspace policy | Supabase Auth + server JWT checks + app ownership/RLS defense | Real login and cross-tenant tests | Open |
| ADR-003 | Database and migrations | Managed PostgreSQL, SQLAlchemy/Alembic or SQL | Real quota, migrations, backup, authorization | Open |
| ADR-004 | Permitted discovery source families | HN, approved RSS, Bluesky candidate | Live retrieval, terms, usefulness, limits | Open |
| ADR-005 | Free AI provider/model | Pluggable structured LLM | Actual call, quotas, output validation and fallback | Open |
| ADR-006 | MCP remote auth and version | Python SDK, Streamable HTTP | External client handshake, scope/denied write | Open |
| ADR-007 | Frontend/graph libraries and visual tokens | Next.js + accessible graph/list | Build, interaction/accessibility stress | Open |
| ADR-008 | Production hosting | Candidate free hosts | HTTPS worker/API/DB health and stability | Blocked by verification |
| ADR-009 | Data retention and source excerpts | Minimal permitted excerpts | Policy/terms and deletion review | Open |

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
- Confirm a **real** worker can run on deployed hosting or approve an alternative.
- Confirm LLM free structured output availability; document deterministic degraded path.
- Resolve MCP client auth and write approval, not just a tool list.
- Validate exact PostgreSQL schema and RLS/privileged server behavior.
- Reconcile scope and tech targets at November 19 and 22 gates; record evidence.

This register tracks decisions, **not implementation completion**. See [16-IMPLEMENTATION-ROADMAP.md](16-IMPLEMENTATION-ROADMAP.md) and [14-TESTING-STRATEGY.md](14-TESTING-STRATEGY.md).
