# Axiom — HTTP API Contracts

**Status:** DRAFT — in review · **Version:** 0.1 · **Date:** 18 November 2026  
**Authority:** [PRD](02-PRD.md), [MVP](03-MVP.md), [Architecture](05-SYSTEM-ARCHITECTURE.md), [TRD](06-TRD.md)

## 1. Normative conventions (proposed)

Base path `/api/v1`; HTTPS and JSON. **ADR-002 approves FastAPI as the sole domain-data access path** (including browser research/CRM, MCP and status). Browser Supabase access is for login/session only. Authentication: `Authorization: Bearer <access_token>` or a reviewed equivalent secure session. Verify user token, **workspace membership** and object scope server-side. Workspace ID in URL is never authority. UUID-style opaque identifiers; timestamps ISO 8601 UTC; null/`unknown` means missing data, not zero.

Async research/teardown: submission returns `202 Accepted`, `run_id` and `status=queued`. Poll per-workspace status; do not pretend accepted means completed. `Idempotency-Key` on research submissions and CRM writes. List pagination uses `limit` (default 20, max 100) + opaque `cursor` with stable sort. Request and response include `request_id` where applicable. Future public version changes require compatibility review and regenerated OpenAPI-derived TypeScript types.

**Errors (single shape):**
```json
{"error":{"code":"WORKSPACE_FORBIDDEN","message":"Workspace is not accessible.","retryable":false,"details":{}},"request_id":"req_example"}
```

Map 400 BAD_REQUEST, 401 AUTH_REQUIRED, 403 WORKSPACE_FORBIDDEN, 404 NOT_FOUND, 409 VERSION_CONFLICT/IDEMPOTENCY_CONFLICT, 422 VALIDATION_FAILED, 429 RATE_LIMITED, 502 SOURCE_UPSTREAM_FAILED, 503 RESEARCH_UNAVAILABLE. Never expose stack traces, credentials or tenant existence inadvertently.

## 2. Endpoint map

| Method/route | Purpose | Priority |
|---|---|---|
| `GET /health` | Safe process liveness | P0 |
| `GET /api/v1/me` | Current caller safe identity | P0 |
| `GET, POST /api/v1/workspaces` | List/create owned workspaces | P0 |
| `GET, PATCH /api/v1/workspaces/{workspace_id}` | Read/update workspace | P0 |
| `GET, POST /api/v1/workspaces/{workspace_id}/profiles` | Confirm/retrieve profile versions | P0 |
| `POST /api/v1/workspaces/{workspace_id}/discovery/runs` | Start bounded research | **P0 required HTTP #1** |
| `GET /api/v1/workspaces/{workspace_id}/research/runs/{run_id}` | Job status, warnings, IDs | P0 |
| `GET /api/v1/workspaces/{workspace_id}/signals` | Ranked signal list + cursor/filter | P0 |
| `POST /api/v1/workspaces/{workspace_id}/competitors/teardowns` | Sourced competitor investigation | **P0 required HTTP #2** |
| `GET /api/v1/workspaces/{workspace_id}/competitors/reports/{report_id}` | Stored sourced report | P0 |
| `POST /api/v1/workspaces/{workspace_id}/assessments` | Evidence graph/report/verdict | P0 |
| `GET /api/v1/workspaces/{workspace_id}/assessments/{assessment_id}` | Same versioned evidence | P0 |
| `POST /api/v1/workspaces/{workspace_id}/assessments/{assessment_id}/scenarios` | Named scenario creation | R0 |
| `GET /api/v1/workspaces/{workspace_id}/assessments/{assessment_id}/scenarios` | Compare saved scenarios | R0 |
| `GET, POST /api/v1/workspaces/{workspace_id}/leads` | CRM list/create | P0 |
| `GET, PATCH /api/v1/workspaces/{workspace_id}/leads/{lead_id}` | CRM detail/stage | P0 |
| `POST /api/v1/workspaces/{workspace_id}/leads/{lead_id}/notes` | Append note | P0 |
| `POST /api/v1/workspaces/{workspace_id}/leads/{lead_id}/followups` | Create due action | P0 |
| `POST /api/v1/workspaces/{workspace_id}/leads/{lead_id}/drafts` | Create/edit **unsent** draft | R0 |
| `GET /api/v1/workspaces/{workspace_id}/exports/{report_id}` | Markdown/HTML brief | P0 |

Final endpoint names/verbs must be frozen and code-generated after approval. **No email send endpoint or public guest API.**

## 3. Example: discovery create

```http
POST /api/v1/workspaces/{workspace_id}/discovery/runs
Authorization: Bearer <access_token>
Idempotency-Key: example-request-key-123
Content-Type: application/json

{"profile_version_id":"00000000-0000-4000-8000-000000000001","query":"looking for offline note-taking tools","source_families":["hacker_news","rss"],"max_records":30}
```

**202 response (illustrative):**
```json
{"run_id":"00000000-0000-4000-8000-000000000011","status":"queued","accepted_sources":["hacker_news","rss"],"request_id":"req_example"}
```

Validate scope, source allowlist, bounded max_records, query length, available sources, free quota and idempotency. A rejected/disabled source is explicitly reported; never return fixtures as live results.

## 4. Example: run status and signal

```json
{
  "run_id":"00000000-0000-4000-8000-000000000011",
  "status":"partial",
  "progress":{"completed_sources":1,"requested_sources":2},
  "warnings":[{"source":"rss","code":"SOURCE_TIMEOUT"}],
  "signal_ids":["00000000-0000-4000-8000-000000000021"],
  "request_id":"req_example"
}
```

```json
{
  "id":"00000000-0000-4000-8000-000000000021",
  "source":{"family":"hacker_news","url":"https://example.com/illustrative-fixture","origin":"seeded","retrieved_at":"2026-11-18T06:00:00Z"},
  "excerpt":"Illustrative synthetic text, not a live post.",
  "scores":{"problem_relevance":{"value":0.8,"method":"rules"},"solution_intent":{"value":0.9,"method":"rules"},"capability_fit":{"value":null,"method":"insufficient_data"},"evidence_quality":{"value":0.4,"method":"rules"}},
  "why_surfaced":"Synthetic example only",
  "uncertainty":["Capability fit unknown"]
}
```

All sample IDs, scores, URLs and excerpts above are **synthetic examples**, not observed product performance.

## 5. Competitor request/report

```http
POST /api/v1/workspaces/{workspace_id}/competitors/teardowns
Authorization: Bearer <access_token>
Content-Type: application/json

{"competitors":[{"name":"Example Company","url":"https://example.com","confirmed":true}],"include":["features","pricing","positioning"]}
```

Return `202` with run ID for long research. Final report fields: `report_id`, `competitor_id`, `claims[]` each with `claim_type`, `text`, `source_record_id` or provenance=unverified, `locator`, `retrieved_at`; `unknowns[]`; `contradictions[]`; `warnings[]`; `status`. An absent price is `Unknown`, never an invented value.

## 6. Assessment and simulation contract

Assessment request references `signal_id` and `profile_version_id` and optional competitor report IDs. Response fields: `assessment_id`, `evidence_snapshot_id`, `verdict` (pursue/research_further/skip/insufficient_evidence), `reason_codes[]`, `nodes[]`, `edges[]`, `source_refs[]`, `hypotheses[]`, `warnings[]`, `profile_version_id`. Graph and report derive from identical saved evidence IDs.

Scenario create: `baseline_assessment_id`, `name`, typed `assumptions[]` (capability add/remove, qualitative pricing, positioning) and idempotency key. Response `scenario_id`, `revision`, `baseline_snapshot_id`, `changed_requirements[]`, `coverage_diff`, `unsupported_assumptions[]`. No cross-snapshot comparison without explicit rebase.

## 7. CRM and controlled writes

Save lead: request contains `signal_id`, optional `assessment_id`, title, stage; successful durable response `lead_id`, `created_at`, `already_exists` (when deduped). PATCH uses record version or `If-Match` to avoid lost updates. Notes/follow-ups are workspace-scoped. Outreach draft is stored with `status=draft/not_sent`; no delivery status or sending function is exposed.

**Conflict behavior:** same idempotency key + same payload repeats prior outcome; same key + different payload returns explicit conflict. Job crashes and duplicate browser clicks cannot silently duplicate leads.

## 8. Security, contract tests and Definition of Done

- Auth, expired token, wrong issuer/audience, wrong workspace, wrong object, payload oversize, unsafe URL, provider timeout, free-quota exhaustion and 429 all have typed contract tests.
- Workspace switching must not mix cached responses; all protected endpoints validate membership.
- OpenAPI generated from implementation; review API diff and regenerate frontend types as part of CI.
- Validate actual curl requests against deployed HTTPS with low-privilege evaluator account; redact token in logs/docs.
- Two real endpoints (discovery+teardown) must execute actual domain behavior, not fixed demo JSON. Missing source service results in explicit failure/partial state.
- MCP tool schemas reference shared use cases and enforce the same decisions as HTTP.

**Open:** final auth transport, pagination style, async cancellation, exact validation caps, post-v1 compatibility and rate limits; these must be resolved before implementation is called contract-complete.
