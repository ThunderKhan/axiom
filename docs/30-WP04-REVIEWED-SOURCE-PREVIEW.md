# WP-04 / WP-06 — Reviewed public source and competitor previews

**Status:** Bounded authenticated transport implementation candidate; no
production-approved provider or real deployed source fetch is verified.

**Traceability:** FR-04/07, MVP-04/06/11 (partial), SRC-SEC-01,
[Data Sources](11-DATA-SOURCES.md), [API Contracts](08-API-CONTRACTS.md),
and [Scope Cutline](23-NOVEMBER-26-SCOPE-CUTLINE.md).

## Source permission registry

`AXIOM_REVIEWED_SOURCES` is a server-only JSON array of zero to 32 exact HTTPS
URLs and source-specific review records. Default: empty/disabled. Each entry
requires publisher, terms URL, review ID, reviewer, reviewed date, allowed
purposes, explicit permission for retrieval and excerpt redisplay, robots/access
review, and minimum request interval. It is not a user-supplied permission flag.
It must be populated only after checking actual permission, attribution and
provider limits; no wildcard or query-bearing URL is accepted.

The current official Hacker News API documentation
(https://github.com/HackerNews/API) describes public access and no documented
rate limit. That does not by itself establish commercial reuse and retention
rights for third-party posts. YC's current terms
(https://www.ycombinator.com/legal/) restrict commercial exploitation and
automated collection absent authorization. HN remains disabled pending a
source-specific determination; publisher RSS rights also require individual
review. No third-party content is embedded in the registry. A public or
successful HTTP response alone is not a permission record.

## HTTP interfaces

- `POST /api/v1/workspaces/{workspace_id}/research/public-url/preview` with
  `{"url":"<reviewed exact HTTPS URL>"}`.
- `POST /api/v1/workspaces/{workspace_id}/competitors/preview` with
  `{"name":"<competitor>","url":"<reviewed exact HTTPS URL>","confirmed":true,"candidates":[{"kind":"features","locator":"<exact phrase>"}]}`.
  Claim kinds are features, pricing and positioning; unmatched categories
  remain Unknown. Founder categories are not independently inferred facts.

Both operations authorize the existing workspace owner before any outbound
effect. Only a purpose explicitly covered by the configured entry can be
fetched through the pinned-IP, TLS-validating, redirect-denying source
boundary. Response includes actual retrieval time, content digest, bounded
visible excerpt, publisher and policy review ID. A real publisher statement
is not independent proof of a shipped feature or a market signal. Responses
are private no-store previews, not persistent research jobs or reports.

The process permits one simultaneous fetch and a five-second global minimum
interval plus each URL's configured interval (10–3600 seconds). Failed
attempts count against the quota; no automatic retries. These are process-local
limits only: multi-instance distributed rate limiting and total source quota
must be addressed before broad deployment. Missing permissions return 403;
rate limit returns 429; upstream failure returns 502. No arbitrary scraping,
redirects, XML feed parsing, AI instructions, outbound outreach or secret
transmission to source websites.

## Structured feed preview (RSS 2.0 / Atom 1.0)

`POST /api/v1/workspaces/{workspace_id}/research/feed/preview` accepts
`{"url":"<reviewed feed URL>","query":"optional literal terms","limit":10}`.
The exact URL must have the separate `feed_preview` permission. The same
owner authorization, pinned-IP HTTPS transport, global/per-URL throttling,
64 KiB body bound and no-redirect rule apply. Entry URLs are never fetched.
The parser accepts UTF-8/ASCII RSS 2.0 or Atom 1.0, rejects DTD/entity
declarations and unsupported documents, limits structure and scanned entries,
and returns at most 20 deduplicated HTTPS article citations. Nested XML/XHTML
content, private/numeric authorities, query-bearing and fragment links are
not supported. Only explicit timezone-aware publication timestamps are retained.

The result includes feed digest, actual retrieval timestamp, publisher and
review metadata. Entry excerpts are inert, bounded text. The optional query
is literal all-term matching against title and excerpt, not intent inference,
fit scoring or comprehensive search. Empty matches are legitimate. The
response is not a saved run and cannot authorize a later article fetch.
The registry remains empty by default; tests use explicit deterministic
fixtures, not a verified publisher or successful live deployment.

## Workspace browser integration

The reviewed-source panel is mounted only inside the authorized workspace's
ready CRM state and reuses its verified bearer-token client. It accepts an
exact HTTPS URL or confirmed named competitor with optional exact feature,
pricing and positioning phrases. The client rejects mismatched workspace IDs,
URLs, unverified provenance and inconsistent claim/unknown responses. React
renders retrieved text as inert text, not HTML. Request cancellation and
workspace/sign-out unmounting discard stale results.

Source-blocked, rate-limited and unavailable outcomes remain explicit; no
automatic retry or fabricated preview is introduced. Results are intentionally
not saved or copied into the manual-source CRM as verified live evidence.
No reviewed URL is enabled by this UI.

## Release evidence still required

Tests use an injected deterministic transport, clearly identified as fixtures;
they verify authorization before fetch, exact URL/purpose denial, registry
validation, quotas and observed versus unknown competitor claims. The existing
network-boundary tests verify SSRF behavior. Required repository CI and review
must pass. Actual approved source acquisition, two permitted source families,
durable source/signal/report storage, real discovery ranking, browser
acceptance and deployment verification remain release-blocking. This is not
the full approved asynchronous discovery/teardown contract.
