# Axiom — Data Sources, Access and Provenance

**Status:** APPROVED — lawful acquisition strategy, provenance and adapter policy; **individual provider permissions/live integrations NOT verified** · **Version:** 1.0 · **Approved:** 18 November 2026  
**Authority:** [PRD](02-PRD.md), [MVP](03-MVP.md), [System Architecture](05-SYSTEM-ARCHITECTURE.md), [AI Engine](09-AI-ENGINE.md)

**Founder-approved acquisition strategy:** [ADR-004](decisions/004-broad-authorized-source-integration.md) — Option C (broad multi-platform sources), not a source-permission or live-integration approval.

## 1. Goals and non-negotiable policy

Opportunity Radar discovers relevant **publicly accessible expressions of demand** through permitted integrations. It never implies that a public author consented to unsolicited private contact. The source adapter must respect service terms, robots/access controls where applicable, quotas, and data minimization; **working API access is not automatically permission for every use or retention pattern**.

P0 verification floor: **two independently functioning permitted source families plus a safe user-supplied public URL pathway**. R0 November 26 objective: **three or more permitted source families plus broader authorized platform coverage** (not merely stopping at three). The founder specifically selected a broad-source strategy: Hacker News, permitted RSS/Atom, Bluesky, **Reddit if specifically authorized**, and additional legitimate providers. Source-target approval does **not** mean access is legally granted, a connector is ready, or an API is free. An RSS feed count is not the same as an independent platform family; never count seeded fixtures as a live integration.

## 2. Adapter registry — proposed, unverified

| Family | Candidate access | Why useful | Status / decision gate |
|---|---|---|---|
| **Hacker News** | Official HN API, with bounded recent item walk; alternatively HN Search API if terms and access suitable | Public technology problems and solution requests | **Candidate — live retrieval, limits, terms not yet confirmed in deployment** |
| **Public RSS/Atom** | Allowed publisher/community feeds with source attribution | Broader topical discussions | **Candidate — inspect individual feed terms, quality and retention** |
| **Bluesky** | Official documented public endpoints subject to rate limits and policy | Additional public discussion family | **Candidate R0 — verify permitted endpoints and accuracy** |
| **User-entered public URLs** | Secure bounded fetch of permitted URL | Research beyond built-in platforms | **Required capability, fetch/SSRF test outstanding** |
| **Reddit** | **Only an officially permitted API/integration for this intended SaaS use**, after terms, licensing, credentials and payment/usage review | Problem-rich community discussion | **Approved target under ADR-004; API permission, cost and integration NOT approved/verified** |
| **Additional platforms** | Individually vetted legitimate APIs/feeds; GitHub Discussions, Stack Exchange, and others are evaluation candidates, **not access approvals** | Broader industry and developer demand | **Approved expansion strategy; each adapter disabled pending explicit terms/rights/quota and live proof** |

**Important:** Official Hacker News item API provides item/story access, not arbitrary full-text search. If full-text query is required, verify a separate authorized search method or build an honest bounded item-scan pipeline; avoid promising complete HN search. HN Search by Algolia is a separate service/data access route with its own terms/limits. Never assume a query can find *all* matching discussions.

Official references: [HN API](https://github.com/HackerNews/API), [HN Search API](https://hn.algolia.com/api), [Bluesky docs](https://docs.bsky.app/).

## 3. Approved adapter lifecycle

Before enabling any connector, record a row in a maintained source registry with:
- Source name + exact endpoint/method + provider terms URL, date reviewed and responsible reviewer.
- Access mechanism/credentials (never secrets in docs), whether auth is required.
- Allowed use: retrieval, processing, excerpt retention, attribution, redisplay and permitted redistribution.
- API limits, backoff, concurrency and budget with explicit `₹0` external API spending.
- Query semantics, index coverage, date range, regional/industry skew and recall limitations.
- Normalization strategy, source identifier, canonical URL, retrieval/published time, deletion/update policy.
- Unit fixtures, successful live test evidence and known failure states.
- Enabled/disabled status; must not be enabled merely because a future adapter exists in code.

## 4. Normalized public source record

```json
{
  "source_record_id": "example-id",
  "source_family": "hacker_news",
  "provider_record_id": "example-provider-id",
  "canonical_url": "https://example.com/fictional-record",
  "title": "Illustrative only",
  "excerpt": "A clearly synthetic example, not a real customer comment.",
  "published_at": null,
  "retrieved_at": "2026-11-18T06:00:00Z",
  "origin": "seeded",
  "content_digest": "illustrative-hash",
  "access_status": "fixture",
  "attribution": "SYNTHETIC EXAMPLE"
}
```

Use `live` for genuinely retrieved permitted records, `cached` with original retrieval time for snapshots, `seeded` for demonstration fixtures, `user_provided` for manual evidence, `inferred` for derived interpretation, and `unknown` for unavailable facts. Display these states in UI, graph, exports and API/MCP.

## 5. Safe network acquisition protocol

- Allow only HTTP(S), with normalized host and no embedded credentials.
- Reject private/loopback/link-local/reserved addresses, internal DNS aliases, cloud metadata and unacceptable ports.
- Resolve host and **validate every actual destination address and redirect**; mitigate DNS rebinding and redirect-to-private-host attacks. Enforce allowlist for adapters when possible.
- Bounded content length, types, redirects, connect/read timeouts, concurrency and per-source rate limit. No downloading arbitrary executable archives.
- Parse HTML to text in constrained environment; escape/strip scripts, events and unsafe markup before rendering.
- Avoid obeying instructions embedded in source content; do not treat retrieved source as higher-priority instruction.
- Source auth wall/blocked JS/paywall returns a truthful failure or manual user-provided evidence option; never bypass.

## 6. Deduplication, quality and coverage

Canonicalize URLs carefully without destroying source IDs. Prefer provider ID + source family as primary identity; fallback stable URL+digest and normalized-text near-duplicates when justified. Preserve origin source IDs for traceability.

Track result count, successful live/partial/failed adapters, retrieval latency, response age, repeated content, empty results, relevance, intent/fit disagreements, and source-level errors. Do not assert all industries are equally represented; surface technology skew and coverage gaps.

Discovery may return **zero** results. This must be a meaningful product outcome with suggested query refinement or safe manual URL analysis, not an excuse to fabricate demand.

## 7. Attribution, retention, consent and deletion

- Always provide original URL, platform, timestamps, excerpt/locator, and whether sourced content is a **claim** versus independently verified fact.
- Save only minimum necessary bounded text and metadata. Full-page cache retention depends on provider terms and data policy, not a presumed universal right.
- If an upstream post is deleted or no longer available, avoid silently rehydrating it; define retention/purge policy and preserve only lawful/auditable historical identifiers as permitted.
- Do not collect private profiles/messages or infer sensitive personal traits. No bulk contact extraction or autonomous outreach.
- Evaluator fixture data is clearly labeled and isolated in ordinary authenticated workspaces.

## 8. Acceptance matrix

| Test | Expected |
|---|---|
| Real HN/approved feed fetch | Actual URL and fetched timestamp, provider identified |
| Unsupported/restricted source | Disabled or explicit access/terms limitation |
| Source timeout or 429 | Partial/failed status; bounded retry and quota |
| HTML with prompt injection | Data-only processing; no tool execution |
| Redirect/DNS to private IP | Rejected |
| Duplicate post via two runs | Same canonical source identity or explicit dedupe |
| Live and seeded mixed examples | Each correctly labeled in UI, API, export |
| Unknown published date | Null, not an invented date |
| High-intent non-fit post | High intent but low fit or research verdict |
| 3+ source R0 target unmet | Explicit R0 gap and owner decision |

## 9. Open decisions and operational checklist

Apply the **owner-approved broad acquisition strategy** ([ADR-004](decisions/004-broad-authorized-source-integration.md)) and maintain a source-by-source *candidate/permission-pending/blocked/verified-live/disabled* registry. Verify HN retrieval strategy; test Bluesky; **obtain specific, appropriate Reddit access before enabling it**; evaluate additional authorized platforms. Review actual free quotas, source data rights, retention/deletion, relevance and search coverage. Do not silently reduce scope to only HN/RSS/Bluesky if broader targets are blocked; report blockers and request owner direction. Record adapter decisions in [DECISIONS.md](DECISIONS.md). Do not call integration "live" until a real request succeeded and results can be inspected.

## 10. Approved breadth strategy, provider gates, and coverage status (decision 4 of 6)

The founder chose **Option C** in [ADR-004](decisions/004-broad-authorized-source-integration.md): implement a **broad, compliant, extensible source-adapter program** including Hacker News, RSS/Atom, Bluesky, Reddit **only if separately authorized**, manual public URLs, and additional authorized platforms. This is **approved target scope**, not authorization to obtain data from each provider. Restricted sites may require prior API approval, paid access or prohibit the planned use; the ₹0 external paid research API rule still applies, so these integrations must remain **disabled/blocked** rather than bypass policy when unavailable.

**Provider readiness register (initial, not implementation claims):**

| Source | Strategy status | Integration proof / policy gate |
|---|---|---|
| Hacker News | Target selected; not verified live | Actual permitted item/search retrieval; legitimate attribution and query-coverage limits |
| RSS/Atom | Target selected; not verified live | Specific publisher feed terms and live fetched/attributed results |
| Bluesky | Target selected; not verified live | Current supported public endpoints, rate limits, usage permission, live sample |
| Reddit | Target selected; **permission pending** | Affirmative terms/API access rights for Axiom's SaaS use; approved quotas/cost; live sample |
| Manual public URLs | Target selected; SSRF proof outstanding | Bounded public fetch with per-hop DNS/IP revalidation, safe HTML extraction |
| Further providers | Discovery/evaluation candidates | Distinct platform family; explicit provider permit/terms/cost; evidence of permitted live use |

Track *enabled*, *failed*, *blocked by policy*, *permission pending*, *seeded/cached*, and *live verified* independently. Count only real, separate permitted source families toward P0/R0 gates; do not count several RSS feeds as several source **families** or manual URL entry as a distinct platform integration. All newly enabled families must use the same normalized source schema, canonical dedupe, validation, quota, attribution and data-retention review.

**Risks and escalation:** Broad integration scope increases time/quality/privacy risk before November 26. Implement reusable adapter contracts and genuine sources in a deliberate order **without quietly cancelling Reddit/additional-platform targets**. When platform access cannot be established lawfully within the ₹0 external research API constraint, record the exact blocker and seek founder scope guidance rather than scrape or fabricate availability.

## 11. Formal source policy and strategy approval scope

**Approved as an acquisition policy/adapter design:** broad, permission-gated multi-platform target under [ADR-004](decisions/004-broad-authorized-source-integration.md), normalized provenance schema, source registry, SSRF safety, per-provider legal/terms/quotas checks, honest cached/seeded/live states, P0 two genuine permitted family verification floor and R0 three-plus families with additional authorized breadth. **Not approved as available or shipped:** any individual provider's current permission, pricing, access token, RSS publisher rights, Reddit SaaS use, third-party content retention/redisplay, actual source quality/recall, production quotas or live integrated functionality. Source adapters remain disabled until their independently recorded authorization and real test results satisfy the gating policy. Review and approve provider-specific records separately. This approval is **not permission to scrape restricted services or pay external research API fees**.
