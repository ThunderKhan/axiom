# WP-05/07 — Deterministic evidence decision core

**Status:** code in review; **not deployed or integrated with a live source**.  
**Requirements:** FR-05 / FR-08, MVP-05 / MVP-07, DISC-01 / EVID-01, SC-2026-11-23.

Source is an immutable record with HTTPS URL, id, bounded text, timestamp and explicit origin (live/cached/seeded/user-provided). A customer requirement must have an exact locator inside the actual source excerpt. Capability availability is a *founder declaration*, never independently verified by this engine.

The pure engine produces four verdicts: Pursue, Research further, Skip, Insufficient evidence. Missing feature overrides high buying intent; unknown or proposed-but-not-shipped stays Research; no linked requirements abstains; idea-stage is hypothetical. It returns stable source/need/capability relationship IDs and matching human-readable report lines. All synthetic tests are seeded, not live API claims.

**Still required:** admitted permitted real sources and access policy review, actual safe retrieval/normalization, workspace-owned persistence and snapshots, real competitor comparison, browser graph/report, full negative cases, two source families, deployment and evaluator acceptance. This isolated core cannot by itself satisfy the full P0 signature engine.
