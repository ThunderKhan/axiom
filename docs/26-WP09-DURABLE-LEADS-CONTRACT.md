# WP-09 — Durable CRM foundation (23 November 2026)

**Status:** Implementation in review. **No deployed or browser-verified CRM journey is claimed.**  
**Requirements:** FR-06, MVP-09/10, UF-10/11, CRM-01. **Related:** ADR-002; `docs/23-NOVEMBER-26-SCOPE-CUTLINE.md`.

## Implemented backend boundary

- Authenticated `POST /api/v1/workspaces/{workspace_id}/leads` with a validated `Idempotency-Key` (8–128 ASCII token), returning 201 on first save or 200 with `already_exists=true` for a matching idempotency-key retry. A different key with the same source URL is rejected with an explicit `LEAD_ALREADY_SAVED` 409, not a false successful replay.
- Workspace-scoped `GET /leads` (bounded listing with stage/title filters), `GET /leads/{lead_id}`, version-guarded `PATCH /leads/{lead_id}`, `DELETE /leads/{lead_id}?expected_version=N` (logical archive), and `GET /leads/{lead_id}/activity` (up to 100 recent events).
- Stage choices: `spotted`, `qualified`, `contacted`, `closed_lost`. **Contacted is a founder-recorded state, not evidence of a sent message.**
- Notes, follow-up due date/time with timezone, completion state, and human-editable **unsent** draft. This module has no email, DM, social-posting or delivery code.
- **Only manually supplied HTTPS URLs and excerpts are accepted.** Each record is persistently labeled `source_origin=user_provided`. This is **not** a verified live-source result, provider permission, scraped document, or evidence-engine assessment.
- Saves and activity metadata insert atomically in a PostgreSQL transaction. Event payloads include changed field names, not duplicated private note/draft contents.
- Duplicate request key with a different validated payload produces a typed 409. Reusing a URL with a new key returns a conflict rather than silently creating another lead. Edits use `expected_version`; stale writes return 409. Archived records remain under retention review and are excluded from standard list/read endpoints.

## Persistence and authorization

Migration `m3_0001_leads` follows `m2_0001_profiles`. Two new relations, `axiom.leads` and `axiom.lead_events`, have owner-scoped RLS and restricted insert/update privileges. The `lead_events (workspace_id,lead_id)` composite FK references the equivalent unique key in `leads`, preventing cross-workspace event linkage. Events have no runtime UPDATE or DELETE permission. `Database.ready()` validates the new required revision, table count, RLS policies and exact column grants; it fails closed if migration has not been applied.

Read/write domain operations require a cryptographically verified JWT subject, active account, an explicitly owned workspace and a short transaction with a session-local PostgreSQL subject. Browser and MCP clients must use the same API boundary, never direct Supabase table access.

**No managed Supabase schema change was executed.** Real PostgreSQL test migrations run only in the isolated CI environment, and the existing hosted-M1 migration/security gate remains a separate human-reviewed blocker.

## Explicitly incomplete / follow-on

This release slice is a **backend CRM foundation only**. The browser Save as Lead flow, full source/signal/assessment foreign-key integration, multiple durable notes and follow-up rows, date-driven reminders, stable cross-page pagination, retention/purge policy, AI draft generation, manual export, external MCP `save_lead` tool, deployment, and fresh-login E2E are **not** verified here. The source-link fields must later be connected to genuinely permitted persisted source records; do not upgrade user-provided claims to verified live observations.

### Acceptance evidence to collect

- Required Ruff check, mypy strict, pytest and repository governance/quality CI at the exact PR head.
- Isolated PostgreSQL migrations/RLS tests exercising two principals and workspaces, replay/reused URL, stale writes, user-owned transitions, archived-read denial, append-only event permissions and malicious cross-workspace event FK.
- Independent high-risk review for access-control/migration changes; qualified human review and deployment proofs prior to any release claim.
