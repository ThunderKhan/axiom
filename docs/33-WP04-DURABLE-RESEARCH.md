# WP-04 — Durable feed research runs

**Status: implementation candidate; no live provider enabled or deployed.**

POST /api/v1/workspaces/{workspace_id}/research/runs accepts an exact
approved feed URL, a confirmed profile version ID, literal query, bounded
limit and Idempotency-Key. It authorizes the workspace and profile before
network access, retrieves only through the existing bounded feed registry
and rechecks the profile after fetching. Storage requires the separate
feed_persist permission and explicit retention review; preview permission
alone is insufficient. The query is applied locally, never sent to the feed.

Successful results have a persisted run ID, immutable profile revision,
retrieval timestamp, feed digest, publisher/review ID and run-scoped UUIDs
for matched items. Empty matching results are truthful completed retrievals,
not successful demand discovery. All intent remains unknown. Concurrent
requests can be rate-limited; identical completed requests replay without
another fetch; changed requests under the same key conflict.

GET /api/v1/workspaces/{workspace_id}/research/runs/{run_id} reopens the
same immutable result. RLS and explicit owner predicates prevent foreign
access; runtime cannot modify or delete completed runs.

Integration tests use an explicitly injected RSS fixture and real isolated
PostgreSQL. They do not prove live provider access, retention rights or
deployed acceptance. The default registry remains disabled. Before
enabling a feed, independently review retention duration, removal and
redisplay requirements, including third-party copyright; indefinite
retention must be expressly compatible with the reviewed policy.

Not implemented here: browser saved-run management, signal-to-CRM linkage,
persisted assessment/competitor report, actual OAuth MCP transport or
worker queues. No queued work or fake live evidence is claimed.


## Retrieved-signal assessment

POST /api/v1/workspaces/{workspace_id}/research/runs/{run_id}/signals/{signal_id}/assessment
runs the existing evidence engine against the stored feed excerpt and its
original immutable founder profile. Only exact cited requirements are
accepted. Intent remains unknown; feed retrieval does not independently
verify the article or demand. The assessment is recomputed, not persisted.
The PostgreSQL fixture test checks invalid locators, missing signals,
historical profile stability and foreign workspace denial. This is not
yet CRM provenance linkage or deployed live acceptance.
