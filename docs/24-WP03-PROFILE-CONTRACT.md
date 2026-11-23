# WP-03 — Versioned profile contract (23 November 2026)

**Status: WP-03 implementation in review; browser and real-DB verification pending.**  
**Requirements:** FR-02 / MVP-03 / UF-03. **Architecture:** ADR-002 (Supabase Auth, FastAPI-only domain writes, transaction-local PostgreSQL principal, RLS).

## Surface

Authenticated owners can read \`GET /api/v1/workspaces/{workspace_id}/profile\`, save a resumable draft with \`PUT /api/v1/workspaces/{workspace_id}/profile/draft\` using \`expected_revision\`, and confirm a founder-declared immutable version with \`POST /api/v1/workspaces/{workspace_id}/profile/confirm\`. A saved draft increments its revision; confirming a complete draft also increments the draft revision, preventing a delayed repeated POST from creating another confirmed version.

A draft can omit any question. Confirmation requires a stage (idea/live), name, customer problem, audience and proposed/verified-by-founder capability *description*. Website URLs are stored only as **unverified user declarations**; onboarding does not fetch, trust or automatically promote URL content as product fact. Other questions may remain unknown. Version records are append-only, and drafts are separate from versions used in downstream research.

## Data boundaries and migration

Migration \`m2_0001_profiles\` builds the 1:1 \`product_profiles\` workspace draft and append-only \`profile_versions\` snapshot table atop \`m1_0002_rls\`; it is forward-only. Runtime role grants only required SELECT/INSERT on both and UPDATE on the draft, never UPDATE/DELETE of confirmed versions; new RLS policies cover both data relations and enforce an active verified owner. FastAPI independently checks account activation and workspace ownership before every operation.

**Important M1 gate interaction:** \`Database.ready()\` checks the latest schema head and exact RLS/grants; existing M1 acceptance evidence on prior SHA is historical and **does not** certify this newer schema or hosted deployment. Existing managed Supabase still needs privately set role credentials, real ordered Alembic, backup review, nonprivileged pooler parity and qualified human security review. No hosted SQL executed as part of WP-03 implementation.

## Verification

Run Python type/style/unit tests, guarded isolated PostgreSQL migrations and RLS integration with wrong-user read/write, stale revision, immutable version, backend unprivileged DDL denial, then browser login/refresh/resume. No claim of provider-hosted parity or a complete P0 onboarding journey without actual passing evidence and UI integration.

## Browser integration

The selected workspace shows a stage-aware one-question-at-a-time editor, 15 bounded question families, Back/Skip, explicit draft save/resume, human review, and confirmed version state. All drafts/confirmations call the FastAPI boundary with current Supabase access tokens after verifying the same signed-in subject. No browser storage persists private answers; lost write responses require inspection rather than an automatic duplicate. The public app must still pass real-provider/DB browser tests before this is called a verified journey.

## Review-driven correctness changes (23 November)

A saved interview draft now also commits the current 0–14 question position atomically with its answers and optimistic revision, and restores that step on next sign-in. Inputs are disabled during save/confirm to prevent unpersisted edits being mistaken for success. The hidden 11,000-character aggregate limit was removed: the fifteen typed fields already have fixed, independently enforced field limits totaling a bounded payload. This avoids rejecting valid input after the founder follows each displayed maximum. These are functional corrections to Codex's review findings, not relaxed authorization or skipped tests.

## Additional independent review remedies

The browser validates URL scheme and individual Unicode-code-point field limits before save/confirm and provides an actionable API-validation error, while retaining unverified website provenance. All answers reject embedded NUL before PostgreSQL JSONB encoding; this is a deterministic 422 validation error rather than a retryable database outage. TypeScript response validation counts Unicode code points like Python and respects each declared field maximum.
