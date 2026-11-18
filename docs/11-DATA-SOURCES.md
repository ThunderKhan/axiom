# Axiom — Data Sources, Access and Provenance

**Status:** DRAFT — in review · **Version:** 0.1 · **Date:** 18 November 2026  
**Authority:** [PRD](02-PRD.md), [MVP](03-MVP.md), [System Architecture](05-SYSTEM-ARCHITECTURE.md), [AI Engine](09-AI-ENGINE.md)

## 1. Goals and non-negotiable policy

Opportunity Radar discovers relevant **publicly accessible expressions of demand** through permitted integrations. It never implies that a public author consented to unsolicited private contact. The source adapter must respect service terms, robots/access controls where applicable, quotas, and data minimization; **working API access is not automatically permission for every use or retention pattern**.

P0 verification floor: **two independently functioning permitted source families plus a safe user-supplied public URL pathway**. R0 November 26 objective: **three or more permitted source families** and as much broad coverage as actually feasible. An RSS feed count is not the same as an independent platform family; never count seeded fixtures as a live integration.

## 2. Adapter registry — proposed, unverified

| Family | Candidate access | Why useful | Status / decision gate |
|---|---|---|---|
| **Hacker News** | Official HN API, with bounded recent item walk; alternatively HN Search API if terms and access suitable | Public technology problems and solution requests | **Candidate — live retrieval, limits, terms not yet confirmed in deployment** |
| **Public RSS/Atom** | Allowed publisher/community feeds with source attribution | Broader topical discussions | **Candidate — inspect individual feed terms, quality and retention** |
| **Bluesky** | Official documented public endpoints subject to rate limits and policy | Additional public discussion family | **Candidate R0 — verify permitted endpoints and accuracy** |
| **User-entered public URLs** | Secure bounded fetch of permitted URL | Research beyond built-in platforms | **Required capability, fetch/SSRF test outstanding** |
| **Reddit** | Official/API-authorized use only after terms and credential check | Potential buying-intent communities | **Not approved / not assumed available** |
| **Other platforms** | Only legitimate approved APIs/feeds | Future coverage | **Not approved** |

**Important:** Official Hacker News item API provides item/story access, not arbitrary full-text search. If full-text query is required, verify a separate authorized search method or build an honest bounded item-scan pipeline; avoid promising complete HN search. HN Search by Algolia is a separate service/data access route with its own terms/limits. Never assume a query can find *all* matching discussions.

Official references: [HN API](https://github.com/HackerNews/API), [HN Search API](https://hn.algolia.com/api), [Bluesky docs](https://docs.bsky.app/).

## 3. Approved adapter lifecycle

Before enabling any connector, record a row in a maintained source registry with:
- Source name + exact endpoint/method + provider terms URL, date reviewed and responsible reviewer.
- Access mechanism/credentials (never secrets in docs), whether auth is required.
- Allowed use: retrieval, processing, excerpt retention, attribution, redisplay and permitted redistribution.
- API limits, backoff, concurrency and budget with explicit §₹0§ external API spending.
- Query semantics, index coverage, date range, regional/industry skew and recall limitations.
- Normalization strategy, source identifier, canonical URL, retrieval/published time, deletion/update policy.
- Unit fixtures, successful live test evidence and known failure states.
- Enabled/disabled status; must not be enabled merely because a future adapter exists in code.

## 4. Normalized public source record

§§§json
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
§§§

Use §live§ for genuinely retrieved permitted records, §cached§ with original retrieval time for snapshots, §seeded§ for demonstration fixtures, §user_provided§ for manual evidence, §inferred§ for derived interpretation, and §unknown§ for unavailable facts. Display these states in UI, graph, exports and API/MCP.

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

Choose each initial feed with owner-approved data-use evidence; verify HN acquisition strategy; test Bluesky API access; verify actual free quotas; agree on excerpt retention and deletion rules; document per-source discovery accuracy. Record adapter decisions in [DECISIONS.md](DECISIONS.md). Do not call integration "live" until a real request succeeded and results can be inspected.
