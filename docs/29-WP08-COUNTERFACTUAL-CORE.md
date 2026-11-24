# WP-08 — Frozen-evidence counterfactual comparison

**Status:** Deterministic core, authenticated preview and durable comparison implementation
candidate; browser comparison and deployed replay remain incomplete.

**Traceability:** FR-09, MVP-08, SC-2026-11-23; approved
[AI engine](09-AI-ENGINE.md), [database design](07-DATABASE-DESIGN.md) and
[API contracts](08-API-CONTRACTS.md).

## Implemented calculation boundary

`services/api/app/counterfactual.py` accepts one immutable, bounded tuple-based
evidence snapshot, containing exact sources, needs, founder-declared capabilities,
confirmed profile revision and product stage. Its SHA-256 fingerprint includes
all of these values and the original retrieval instant (normalized to UTC).
The fingerprint is a replay identity, **not an authorization token**.

A comparison requires two to eight unique named alternatives. Every alternative
contains at least one explicitly hypothetical feature addition/removal and a
qualitative pricing or positioning assumption. Conflicting edits to the same
normalized feature are rejected. All alternatives are evaluated on exactly the
same source and need values, and cannot change the confirmed profile.

A feature added to cover a cited requirement becomes hypothetical coverage,
never an actually shipped capability. Existing declarations and missing/unknown
states are kept distinct. Uncited feature edits, redundant additions, and
unsupported pricing/positioning effects are disclosed without manufacturing
new source relationships or predicted commercial outcomes.

Projected verdicts describe alternatives, not real recommendations to pursue.
A positive baseline sourced only or partly from seeded or user-provided
requirements is capped to research further. No revenue, conversion, market-share,
or causal-impact model is introduced.

## Authenticated preview boundary

`POST /api/v1/workspaces/{workspace_id}/leads/{lead_id}/scenario-comparison/preview`
accepts cited needs, expected lead version, expected confirmed profile revision and
two to eight named alternatives. The server reads the lead and profile under the
same verified principal and independently enforces workspace ownership through
both existing stores. Stale versions return 409; foreign resources return 404;
invalid locators and assumptions return 422. The server constructs the snapshot;
the request cannot supply source origin, capability status, or a baseline digest.

The response contains the baseline fingerprint, coverage comparison, limitations,
lead/profile versions and original manual-source provenance. It explicitly reports
`persisted_comparison=false` and `live_source_verified=false`. This preview
does not implement the durable assessment/scenario collection contract.

## Durable comparison sets

`POST /api/v1/workspaces/{workspace_id}/leads/{lead_id}/scenario-comparisons`
accepts the preview payload and an Idempotency-Key. A new immutable comparison
set stores the exact frozen evidence, profile revision, lead version, named
alternatives and computed outcomes atomically. Identical retries return the
original set (200); reusing a key for a different payload returns 409.
A new key intentionally creates a separate set, not an edit to an old baseline.
`GET` on the same collection reopens up to 50 newest sets for an active owned
lead, even if its profile or lead version subsequently changes.

Migration `m4_0001_scenarios` adds one append-only table with composite foreign
keys to the lead and confirmed profile revision, owner-scoped SELECT/INSERT
RLS, restricted runtime grants and bounded JSONB payloads. No runtime UPDATE
or DELETE grants are introduced. Readiness checks the new head, eight tables,
19 policies and required scenario privileges. Old evidence remains explicitly
manual and unverified. Archived leads remain hidden through ordinary collection
reads; retained historical rows require a separate retention decision.

The isolated PostgreSQL suite exercises idempotency, stale versions,
fresh-process reopen, cross-tenant denial and direct mutation denial.
No hosted migration or real provider/browser acceptance is claimed.

## Verification and remaining acceptance

`services/api/tests/test_counterfactual.py` covers two distinct alternatives,
immutable replay, changed source/profile fingerprints, equivalent UTC instants,
unsupported assumptions, proposed-vs-declared capabilities, manual provenance,
invalid alternatives and duplicate names. Required CI/review must pass.

The full P0 scenario journey is **not verified** until required CI passes,
the browser comparison is wired, the actual hosted migration and security
review are completed, and two saved alternatives survive browser reload and
fresh login. This collection is a bounded lead-based implementation, not the
full generalized assessment/scenario revision API. Do not expose arbitrary caller-provided
snapshots as trusted evidence. Do not conflate an in-memory fingerprint with
durable storage or claim successful deployed E2E.
