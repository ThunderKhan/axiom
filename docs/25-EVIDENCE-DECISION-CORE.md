# WP-05/07 — Deterministic evidence decision core

**Status:** code in review; **not deployed or integrated with a live source**.  
**Requirements:** FR-05 / FR-08, MVP-05 / MVP-07, DISC-01 / EVID-01, SC-2026-11-23.

Source is an immutable record with HTTPS URL, id, bounded text, timestamp and explicit origin (live/cached/seeded/user-provided). A customer requirement must have an exact locator inside the actual source excerpt. Capability availability is a *founder declaration*, never independently verified by this engine.

The pure engine produces four verdicts: Pursue, Research further, Skip, Insufficient evidence. Missing feature overrides high buying intent; unknown or proposed-but-not-shipped stays Research; no linked requirements abstains; idea-stage is hypothetical. It returns stable source/need/capability relationship IDs and matching human-readable report lines. All synthetic tests are seeded, not live API claims.

**Still required:** admitted permitted real sources and access policy review, actual safe retrieval/normalization, workspace-owned persistence and snapshots, real competitor comparison, browser graph/report, full negative cases, two source families, deployment and evaluator acceptance. This isolated core cannot by itself satisfy the full P0 signature engine.

## Independent review corrections

Usable evidence URLs now require an actual HTTPS authority, without embedded control/whitespace, invalid ports or userinfo. An idea-stage proposed capability is recorded as an *unverified hypothesis* in each relationship and report item, never silently counted as an already supported shipped feature. A separate `hypothetical_need_ids` field and stable hypothesis reason code survive a mixed investigation containing unknown or explicitly missing needs. Additional negative tests cover malformed citations and mixed-state verdicts. These changes remain pure domain logic, not provider access or a verified real research journey.
