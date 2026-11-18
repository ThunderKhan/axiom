# Project Documentation Index

**Project:** Axiom  
**Repository:** [ThunderKhan/axiom](https://github.com/ThunderKhan/axiom)  
**Last updated:** 18 November 2026  
**Purpose:** Canonical map of product specifications, architectural decisions, and documentation authority for Axiom.

## Repository-Level Engineering Instructions

The following files live at the repository root and govern engineering work. They are **not** product specifications:

| File | Purpose | Reading order |
|---|---|---|
| [`agents.md`](../agents.md) | Instructions and operating context for coding agents | First |
| [`engineering.md`](../engineering.md) | Engineering standards, quality expectations, and development workflow | Second |

**Important:** Read both files in their actual repository versions before planning or implementing code changes. This index records their existence and intended role; it does not reproduce or override their contents. Respect repository filename casing.

## Approved Documents

Only documents explicitly approved by the project owner belong in this section. These are authoritative for product behavior and implementation decisions within their scope.

| Document | Purpose | Status |
|---|---|---|
| [`02-PRD.md`](02-PRD.md) | Product vision, target users, requirements, release objectives, user journeys, acceptance criteria, and constraints | **Approved — v1.0** |
| [`03-MVP.md`](03-MVP.md) | November 26 MVP scope, P0 verification floor, preserved R0 objectives, acceptance tests and release gates | **Approved — v1.0** |
| [`04-USER-FLOWS.md`](04-USER-FLOWS.md) | 15 concrete user journeys, onboarding branching, error states, and test traceability | **Approved — v1.0** |
| [`05-SYSTEM-ARCHITECTURE.md`](05-SYSTEM-ARCHITECTURE.md) | Approved modular system design, data and worker boundaries; vendors still pending verification | **Approved — v1.0** |

**Current access requirement:** The product's entry flow is **landing page → login page → authenticated web app**. Fellowship evaluators receive credentials privately and use the normal application. A public guest sandbox or judge-only demo page is **not** required.

## In-Review and Planned Documents — Not Yet Approved

Entries marked **Draft — in review** exist but are **not approved implementation authority**. Entries marked **Planned** describe files not yet completed. Approval requires an explicit founder decision; a GitHub commit alone is not approval.

| Planned document | Purpose | Status |
|---|---|---|

| [`06-TRD.md`](06-TRD.md) | Project-specific technology stack, technical requirements, quality/security acceptance | **Draft — in review** |
| `07-DATABASE-DESIGN.md` | Data model, relationships, isolation, migrations, retention | Planned |
| `08-API-CONTRACTS.md` | HTTP APIs, schemas, authentication, error contracts | Planned |
| `09-AI-ENGINE.md` | Discovery, scoring, evidence assessment, simulation, evaluation | Planned |
| `10-MCP-INTEGRATION.md` | MCP server, tools, permissions, and integration behavior | Planned |
| `11-DATA-SOURCES.md` | Public source adapters, access policies, provenance and limitations | Planned |
| `12-UI-UX-SPEC.md` | Landing, login, onboarding, web app screens, interaction design | Planned |
| `13-DESIGN-SYSTEM.md` | Typography, color, components, motion, accessibility | Planned |
| `14-TESTING-STRATEGY.md` | Acceptance tests, security, E2E, CI and release gates | Planned |
| `15-DEPLOYMENT-RUNBOOK.md` | Infrastructure verification, migrations, secrets, smoke and rollback | Planned |
| `16-IMPLEMENTATION-ROADMAP.md` | Milestones, dependencies, verification, deployment, submission | Planned |
| `17-SECURITY.md` | Threat model, permission and incident policy | Planned |
| `DECISIONS.md` | Decision register and unresolved ADR candidates | Planned |
| `T-shirt.md` | Effort sizing, scope dependencies and delivery risk | Planned |

Additional operational documentation (such as a testing strategy, deployment runbook, or decision records) may be added as actual needs arise. Add entries here when created.

## Architecture Decisions

Record consequential architecture decisions in `docs/decisions/` as numbered, dated decision records (ADRs), with **context, options, decision, consequences, and status**.

**Approved decisions recorded:** None yet.

Potential future decisions include authentication provider, persistence model, model/provider choices, data ingestion strategy, background jobs, and hosting. **These are undecided here; do not infer approval from examples.**

## Superseded Documents

**None recorded.**

When replacing a previously approved specification:

1. Mark the old document as superseded with its replacement path and date.
2. Move it to `docs/archive/` if historical retention is useful.
3. List it here as **Historical reference only — not implementation authority**.
4. Update links and affected decisions; do not silently delete a decision trail.

## Reading Rules

1. **Read root `agents.md` and `engineering.md` first**, using their exact case-sensitive paths. Follow their applicable instructions during coding work.
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

- **Approved:** Explicitly accepted by the project owner; authoritative within scope.
- **Draft / In review:** Work in progress; not implementation authority.
- **Planned:** Not yet created or reviewed.
- **Superseded:** Replaced by a newer approved source; historical reference only.

---

*This index is a navigation and governance document, not a substitute for reading the underlying specifications.*
