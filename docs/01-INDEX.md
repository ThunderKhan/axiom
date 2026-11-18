# Project Documentation Index

**Project:** Axiom  
**Repository:** [ThunderKhan/axiom](https://github.com/ThunderKhan/axiom)  
**Last updated:** 18 November 2026 (all six architecture decisions approved; staged capacity gate and scoped documentation approval reconciled)  
**Purpose:** Canonical map of product specifications, architectural decisions, and documentation authority for Axiom.

## Repository-Level Engineering Instructions

The following files live at the repository root and govern engineering work. They are **not** product specifications:

| File | Purpose | Reading order |
|---|---|---|
| [`AGENTS.md`](../AGENTS.md) | Instructions and operating context for coding agents | First |
| [`ENGINEERING.md`](../ENGINEERING.md) | Engineering standards, quality expectations, and development workflow | Second |

**Important:** Read both files in their actual repository versions before planning or implementing code changes. This index records their existence and intended role; it does not reproduce or override their contents. Respect repository filename casing.

## Approved Documents

Only documents explicitly approved by the project owner belong in this section. These are authoritative for product behavior and implementation decisions within their scope.

| Document | Purpose | Status |
|---|---|---|
| [`02-PRD.md`](02-PRD.md) | Product vision, target users, requirements, release objectives, user journeys, acceptance criteria, and constraints | **Approved — v1.0** |
| [`03-MVP.md`](03-MVP.md) | November 26 MVP scope, P0 verification floor, preserved R0 objectives, acceptance tests and release gates | **Approved — v1.0** |
| [`04-USER-FLOWS.md`](04-USER-FLOWS.md) | 15 concrete user journeys, onboarding branching, error states, and test traceability | **Approved — v1.0** |
| [`05-SYSTEM-ARCHITECTURE.md`](05-SYSTEM-ARCHITECTURE.md) | Approved modular system design, data and worker boundaries; vendors still pending verification | **Approved — v1.0** |
| [`06-TRD.md`](06-TRD.md) | Project-specific technical requirements and 500-founder target | **Approved — requirements baseline (vendor choices open)** |
| [`10-MCP-INTEGRATION.md`](10-MCP-INTEGRATION.md) | OAuth 2.1 MCP protocol, tool schemas, scopes and guarded writes; live authorization server/client not verified | **Approved — protocol and security architecture only** |
| [`11-DATA-SOURCES.md`](11-DATA-SOURCES.md) | Broad lawful source acquisition, adapter/provenance policy; individual source permissions not granted | **Approved — integration strategy and access policy only** |
| [`12-UI-UX-SPEC.md`](12-UI-UX-SPEC.md) | Functional screens, onboarding, evidence/CRM workflows; visual style held | **Approved — functional UX only** |
| [`14-TESTING-STRATEGY.md`](14-TESTING-STRATEGY.md) | Test matrix, security/evidence validation, load test policy | **Approved — testing policy** |
| [`16-IMPLEMENTATION-ROADMAP.md`](16-IMPLEMENTATION-ROADMAP.md) | Milestones, implementation dependencies and risk sizing | **Approved — planning baseline** |
| [`17-SECURITY.md`](17-SECURITY.md) | Workspace isolation, source/AI attack boundaries and security tests | **Approved — security policy** |
| [`18-SCALABILITY.md`](18-SCALABILITY.md) | 500-founder architecture; 100/250 preliminary tests before Nov 26, full 500 test before broad production | **Approved — capacity design and staged release gates only** |

**Current access requirement:** The product's entry flow is **landing page → login page → authenticated web app**. Fellowship evaluators receive credentials privately and use the normal application. A public guest sandbox or judge-only demo page is **not** required.

## Technical Designs In Review, Active Register, and Design Hold

**Draft** implementation designs still require final schema, model or selected infrastructure evidence. **ON HOLD** means the Edviro-derived design is waiting for the founder's additional design-system file (the ten-value color palette is already approved). **Scoped approval** of MCP, source policies and capacity design does not certify their provider integration or tested performance. The active decision register is a governance record, not blanket approval of open ADRs.

| Document | Purpose | Status |
|---|---|---|
| [`07-DATABASE-DESIGN.md`](07-DATABASE-DESIGN.md) | Data model, workspace-scoped relationships, migrations and evidence versioning | **Draft — in review** |
| [`08-API-CONTRACTS.md`](08-API-CONTRACTS.md) | REST endpoints, job lifecycle, authentication, typed requests and errors | **Draft — in review** |
| [`09-AI-ENGINE.md`](09-AI-ENGINE.md) | Source-based scoring, AI extraction, verdicts and counterfactual simulations | **Draft — in review** |
| [`13-DESIGN.md`](13-DESIGN.md) | Edviro-clone layout, typography and animations; **founder palette approved for whole website/app**; additional design-system input pending | **ON HOLD — full design not approved** |
| [`15-DEPLOYMENT-RUNBOOK.md`](15-DEPLOYMENT-RUNBOOK.md) | Hosting verification, migrations, secrets, smoke tests and rollback | **Draft — in review** |
| [`DECISIONS.md`](DECISIONS.md) | Active decision register with approved decisions and unresolved vendor/architecture records | **ACTIVE register — not blanket approval of open ADRs** |

**Outstanding review blockers:** `07-DATABASE-DESIGN.md` requires final DDL, RLS and migrations; `08-API-CONTRACTS.md` needs frozen DTOs/OpenAPI and precise errors; `09-AI-ENGINE.md` needs actual Groq/Gemini evaluation, privacy/quota verification and calibrated extraction/decision rules; `15-DEPLOYMENT-RUNBOOK.md` needs selected host plan, working API/worker, backup and OAuth authorization-server deployment evidence. **Approved but not implemented/verified:** MCP's OAuth server/consent/client handshake, each source provider's legal API access (especially Reddit), and actual 100/250/500-user load results. **Design remains ON HOLD** until the founder provides their separate design-system file. No approval asserts working code or provider availability.

## Architecture Decisions

Record consequential architecture decisions in `docs/decisions/` as numbered, dated decision records (ADRs), with **context, options, decision, consequences, and status**.

**The six founder-selected technical decisions**—auth/database, managed hosting, Groq/Gemini routing, broad authorized sources, OAuth MCP clients and staged 500-user production readiness—are individually recorded in [DECISIONS.md](DECISIONS.md). Design source/palette and unresolved provider/configuration work are tracked there separately.

**Approved ADRs (all six interview choices):** [002 — Supabase Auth/Postgres/FastAPI + SQLAlchemy/Alembic](decisions/002-authentication-database-and-api-boundary.md); [008 — managed hosting and dedicated worker](decisions/008-managed-hosting-and-worker.md); [005 — Groq primary, conditional Gemini](decisions/005-ai-inference-providers.md); [004 — broad authorized sources](decisions/004-broad-authorized-source-integration.md); [006 — scoped OAuth 2.1 MCP clients](decisions/006-mcp-oauth-and-write-approval.md); [010 — 100/250 pre-submission tests and 500-founder production gate](decisions/010-staged-500-founder-capacity-release.md). **Strategy approval ≠ deployed/proven technology.** Specific providers, permissions, pricing, consent UX and load measurements require independent evidence.


## Six-decision approval boundary

The owner selected all six architectural strategies on 18 November 2026. **Document-level approval** is limited to the functional/technical architecture, protocol and lawful acquisition *policies*, security/testing expectations, staged scaling plan and project roadmap. It does **not** waive the November 26 P0/R0 release requirements, nor certify that 100/250/500 concurrency, live data, an LLM provider or remote OAuth MCP tools work.

**Capacity rule:** Before the November 26 fellowship submission, execute and honestly report preliminary tests for **100 and 250 actively authenticated founders**. The **complete passing 500-founder load benchmark is a strict precondition for broader public production rollout**, not a fellowship-submission gate; the fellowship still requires its independently approved P0 functional/security gates. See [ADR-010](decisions/010-staged-500-founder-capacity-release.md) and [18-SCALABILITY.md](18-SCALABILITY.md).

## Superseded Documents

**No approved document superseded.** Replaced the unapproved draft `13-DESIGN-SYSTEM.md` with on-hold `13-DESIGN.md`; removed mistakenly created `T-shirt.md` after carrying its relevant risk-sizing summary into the approved implementation roadmap. Both former files remain retrievable from Git history only, not current documentation.

When replacing a previously approved specification:

1. Mark the old document as superseded with its replacement path and date.
2. Move it to `docs/archive/` if historical retention is useful.
3. List it here as **Historical reference only — not implementation authority**.
4. Update links and affected decisions; do not silently delete a decision trail.

## Reading Rules

1. **Read root `AGENTS.md` and `ENGINEERING.md` first**, using their exact case-sensitive paths. Follow their applicable instructions during coding work.
2. **Consult `docs/01-INDEX.md`** before beginning an implementation task.
3. Read the **approved** specifications relevant to the task, starting with `docs/02-PRD.md`.
4. Use only **approved documents and recorded approved decisions** as the authority for product behavior; planned, draft, and superseded documents do not override them.
5. Do not implement superseded requirements. In particular, do not reintroduce unauthenticated judge/guest demo flows removed from the approved PRD.
6. If approved documents, engineering rules, or relevant implementation constraints conflict, **identify and surface the conflict before implementing**; do not silently choose an interpretation.
7. If a requirement is missing or ambiguous, record the question and seek an explicit decision instead of inventing product policy.
8. Treat PRD requirements as the **what**, and approved system design and contracts as the **how**; detailed designs must remain consistent with the PRD or receive explicit change approval.
9. After any document is created, approved, superseded, renamed, or moved, **update this index in the same change**.
10. Keep documentation links, status labels, filenames, and paths accurate. A document is not "Approved" merely because it is committed to GitHub.

## Documentation Status Conventions

- **Approved:** Explicitly accepted by the project owner (or reviewed under the owner's delegated approval); authoritative only within its stated scope. Candidate technologies remain candidates.
- **Draft / In review:** Material implementation choices or evidence unresolved; not implementation authority.
- **On hold:** Final visual direction awaiting the founder's additional design-system Markdown file; the specified Axiom palette is already approved. Do not finalize yet.
- **Active register:** Tracks individually approved and open decisions; its existence is not blanket approval.
- **Superseded:** Replaced by a newer approved source; historical reference only.

---

*This index is a navigation and governance document, not a substitute for reading the underlying specifications.*
