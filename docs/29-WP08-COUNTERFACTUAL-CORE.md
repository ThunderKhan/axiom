# WP-08 — Frozen-evidence counterfactual comparison

**Status:** Deterministic calculation implementation; persistence, authenticated
HTTP, browser comparison and deployed replay remain incomplete.

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

## Verification and remaining acceptance

`services/api/tests/test_counterfactual.py` covers two distinct alternatives,
immutable replay, changed source/profile fingerprints, equivalent UTC instants,
unsupported assumptions, proposed-vs-declared capabilities, manual provenance,
invalid alternatives and duplicate names. Required CI/review must pass.

The full P0 scenario journey is **not verified** until the baseline snapshot
is persisted and bound to an authorized workspace/profile version, named
scenarios and results are stored atomically and idempotently, a browser
comparison and authenticated read/write endpoints exist, and two alternatives
survive reload and fresh login. Do not expose arbitrary caller-provided
snapshots as trusted evidence. Do not conflate an in-memory fingerprint with
durable storage or claim successful deployed E2E.
