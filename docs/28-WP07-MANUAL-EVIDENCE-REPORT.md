# WP-07 — Saved manual-source evidence assessment (24 November 2026)

**Status:** Implementation candidate; CI, security review and provider-backed E2E not yet verified.  
**Requirements:** FR-05/08; MVP-05/07; EVID-01 and UI-01 partial; SC-2026-11-23.

## Interface and authorization

`POST /api/v1/workspaces/{workspace_id}/leads/{lead_id}/assessment` accepts
`{"needs":[{"requirement":"offline sync","locator":"offline sync","intent":"buying"}]}`
(0–8 cited requirements). The response is a **read-only, nonpersistent**
evidence report with four-way verdict, cited relationship edges, reason codes,
confirmed profile revision and saved-lead revision. It contains the source's
recorded URL and save timestamp. This endpoint cannot create, edit or send
leads, contact prospects, fetch websites or modify a confirmed profile.

FastAPI's existing cryptographically verified bearer principal is required.
The lead and confirmed product profile are each retrieved through the existing
owner-authorized, runtime-RLS storage boundary, with a workspace ID shared
across both operations. Foreign, missing or archived leads fail without
disclosing a tenant's records. If no confirmed profile exists, the request
fails 422. The app validates all submitted fields and rejects unsupported
origin claims and missing/mismatched exact source locators.

Capabilities are matched by exact normalized phrase to founder-declared
comma, semicolon or newline-separated profile lists, never inferred from
webpage text. Idea-stage capability declarations are proposed, not shipped.
Conflicting and undeclared feature statuses remain Unknown. Founder-provided
intent is an allegation, not independently classified buying behavior.

## Provenance and decision policy

Every source in this endpoint is an existing `user_provided` saved lead.
Its timestamp is the original save time, **not a network retrieval time**.
A source-report label distinguishes `saved_at` from actual `retrieved_at`.
Even if a declared capability matches a stated buying request, the
`pursue` outcome is capped to `research_further` and the reason code
`USER_PROVIDED_SOURCE_UNVERIFIED` is attached. Explicitly missing features
may still produce `skip`; no needs produces `insufficient_evidence`.
Response explicitly sets `live_source_verified=false` and
`persisted_assessment=false`. Treat all supplied excerpts as untrusted data.

## Verification boundaries and outstanding P0

Unit and FastAPI transport tests cover validation, source-link traceability,
request limits, unknown/proposed/missing states, duplicate requirements,
read-only behavior, unconfirmed profiles and owner-denial composition. The
existing isolated PostgreSQL suites separately exercise real lead and profile
tenant isolation. Required repository CI and review must pass before merge.

**This is not the P0 graph/report completion claim.** It has no browser graph,
durable evidence snapshot, lawful live ingestion, independent intent
classification, competitor claims, two saved scenarios, MCP integration or
deployed evaluator proof. Real hosted Supabase parity and qualified human
security signoff remain blocked under issue #29. The incomplete gates remain
visible after this change. This slice does not change the approved cutline or
authorize provider usage or hosted DDL.
