# Project Documentation Index

**Project:** Axiom  
**Repository:** [ThunderKhan/axiom](https://github.com/ThunderKhan/axiom)  
**Last updated:** 18 November 2026 (reviewed documentation; 500-user target added)  
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
| [`12-UI-UX-SPEC.md`](12-UI-UX-SPEC.md) | Functional screens, onboarding, evidence/CRM workflows; visual style held | **Approved — functional UX only** |
| [`14-TESTING-STRATEGY.md`](14-TESTING-STRATEGY.md) | Test matrix, security/evidence validation, load test policy | **Approved — testing policy** |
| [`16-IMPLEMENTATION-ROADMAP.md`](16-IMPLEMENTATION-ROADMAP.md) | Milestones, implementation dependencies and risk sizing | **Approved — planning baseline** |
| [`17-SECURITY.md`](17-SECURITY.md) | Workspace isolation, source/AI attack boundaries and security tests | **Approved — security policy** |

**Current access requirement:** The product's entry flow is **landing page → login page → authenticated web app**. Fellowship evaluators receive credentials privately and use the normal application. A public guest sandbox or judge-only demo page is **not** required.

## Technical Designs In Review, Active Register, and Design Hold

**Draft** implementation designs are not yet authoritative; they contain missing provider/schema/client decisions. **ON HOLD** means do not finalize visual styling before founder-provided colors and design-system instructions. The active decision register is a governance record, not blanket approval of every open ADR. A GitHub commit alone never means approval.

| Document | Purpose | Status |
|---|---|---|
| [`07-DATABASE-DESIGN.md`](07-DATABASE-DESIGN.md) | Data model, workspace-scoped relationships, migrations and evidence versioning | **Draft — in review** |
| [`08-API-CONTRACTS.md`](08-API-CONTRACTS.md) | REST endpoints, job lifecycle, authentication, typed requests and errors | **Draft — in review** |
| [`09-AI-ENGINE.md`](09-AI-ENGINE.md) | Source-based scoring, AI extraction, verdicts and counterfactual simulations | **Draft — in review** |
| [`10-MCP-INTEGRATION.md`](10-MCP-INTEGRATION.md) | MCP tool schemas, scope permissions, transport and external-client tests | **Draft — in review** |
| [`11-DATA-SOURCES.md`](11-DATA-SOURCES.md) | Permitted source registry, safe public URL fetching, provenance, coverage and limitations | **Draft — in review** |
| [`13-DESIGN.md`](13-DESIGN.md) | Edviro-clone-derived layout, typography, responsive behavior and motion; final colors and founder design system pending | **ON HOLD — not approved** |
| [`15-DEPLOYMENT-RUNBOOK.md`](15-DEPLOYMENT-RUNBOOK.md) | Hosting verification, migrations, secrets, smoke tests and rollback | **Draft — in review** |
| [`18-SCALABILITY.md`](18-SCALABILITY.md) | Owner-requested 500-founder concurrent capacity model, queue/pooling design and load-test criteria | **Draft — requires capacity test and review** |
| [`DECISIONS.md`](DECISIONS.md) | Active decision register with approved decisions and unresolved vendor/architecture records | **ACTIVE register — not blanket approval of open ADRs** |

**Review blockers:** Database design needs final DDL/RLS/migrations; API contracts need complete frozen schemas; AI engine needs model evaluation and deterministic threshold verification; MCP requires production auth/write-consent design and client handshake; source adapters need legal/technical access proof; deployment runbook needs actual hosting/worker choice. Design awaits founder palette/design-system file. Scaling awaits measured capacity. **None of these drafts proves implementation or provider availability.**

## Architecture Decisions

Record consequential architecture decisions in `docs/decisions/` as numbered, dated decision records (ADRs), with **context, options, decision, consequences, and status**.

**Approved product and architectural direction decisions**, the founder-requested 500-user target, Edviro design reference, and unresolved architecture issues are tracked in [DECISIONS.md](DECISIONS.md). No provider-specific ADRs are approved yet.

Pending provider-specific decisions include authentication, persistence/migrations, model/provider choices, data ingestion, job execution and hosting. **Approval of the system architecture does not select a hosting vendor or validate a free tier.**

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
- **On hold:** Visual/design direction awaiting the founder's additional design-system file and palette; do not finalize.
- **Active register:** Tracks individually approved and open decisions; its existence is not blanket approval.
- **Superseded:** Replaced by a newer approved source; historical reference only.

---

*This index is a navigation and governance document, not a substitute for reading the underlying specifications.*
