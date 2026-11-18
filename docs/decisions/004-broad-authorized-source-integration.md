# ADR-004 — Broad Multi-Platform, Permission-Gated Source Acquisition

**Status:** APPROVED — integration strategy and target scope; source access and release readiness unverified  
**Decision date:** 18 November 2026  
**Decision owner:** Founder, technical decision 4 of 6 (Option C)  
**References:** [PRD](../02-PRD.md), [MVP](../03-MVP.md), [Architecture](../05-SYSTEM-ARCHITECTURE.md), [TRD](../06-TRD.md), [Data Sources](../11-DATA-SOURCES.md), [Security](../17-SECURITY.md), [Roadmap](../16-IMPLEMENTATION-ROADMAP.md)

## Context and options

Axiom's Opportunity Radar must find genuine demand signals, not fabricated leads. The founder was offered (A) Hacker News + RSS/Atom + Bluesky + manual URLs; (B) Hacker News + RSS/Atom + Reddit + manual URLs; and (C) broad multi-platform discovery including all these and additional authorized platforms. **The founder selected Option C.**

## Approved decision

1. **Broad adapter ecosystem, not a three-source ceiling.** Target distinct independently functioning source families: **Hacker News**, **permitted RSS/Atom feeds**, **Bluesky**, **Reddit where independently authorized**, **manual user-provided public URLs**, and **additional authorized platforms** supported by legitimate provider APIs/feeds. Third-party websites/feeds are not automatically authorized by being reachable.
2. **Per-provider legal/operational gate.** An adapter is **disabled until** documented access method, applicable terms, licensing/retention, credentials (if required), expected usage, rate limits, safety controls, and a successful real live sample. This ADR approves exploring and building these integrations, **not** scraping restricted services or claiming permission.
3. **Reddit is a target, not assured access.** Use only access explicitly permitted for the intended product and use case, taking current API terms, permission/approval, paid/commercial restrictions and data handling into account. If authorization cannot be obtained within budget/terms, record **blocked** and do not use circumvention, unofficial APIs, login scraping, disguised browser identities, or unapproved redistribution.
4. **Additional platform selection:** add any future source family only after a source-registry entry, terms/permission and live-request proof. Examples such as GitHub Discussions, Stack Exchange or other public communities are **evaluation candidates only**, not approved for automatic ingestion by this decision. LinkedIn, Instagram, X and other restricted platforms are likewise **not assumed available**.
5. **Two-level scope tracking:** retain the existing P0 minimum **two genuinely working, permitted source families plus safe manual URL ingestion**, and R0 **at least three permitted families plus broader authorized integration coverage**. The founder's choice to pursue broad multi-platform support **does not waive** the November 26 R0 goal or silently collapse the scope to only three. Record every planned family as **implemented, verified live, blocked, disabled, or pending**.
6. **No invented coverage:** UI, API and MCP must disclose which adapters are live/allowed, degraded, cached, disabled or seeded, and represent platform-specific retrieval gaps. Never report synthetic fixtures as real leads or describe API item scanning as complete global search.
7. **Common adapter interface:** shared typed `SourceAdapter` contract with `discover`, normalize, deduplicate, source timestamps/provenance, quotas, and errors; provider terms/access policies owned by a central registry. User-supplied URLs follow strict SSRF-safe public fetching.
8. **Safe, fair usage:** respect provider policy/robots where applicable, attribution/erasure obligations, rate limits and founder/workspace quotas. No private messages, bypassing authentication/paywalls, sensitive personal profiling, or automated cold outreach.
9. **Budget:** ₹0 paid external AI/research API spend remains in effect. The already approved modest managed-hosting budget is separate and is **not authorization to pay Reddit or any data-provider API fees**.
10. **Deployment gate:** live allowed-source evidence, actual domain relevance and provenance must be demonstrated independently for every claimed integrated provider. Add integration tests and quota/consent checks before marking a source operational.

## Work plan and dependencies

**Initial research implementation track (priority, not a scope cut):**
- Build the shared source registry, canonical record model and safe public URL pipeline.
- Implement and prove live Hacker News and permitted RSS/Atom adapters with real attributable posts/feeds (the HN official item API is not an all-purpose full-text search API).
- Investigate and implement Bluesky via current permitted public APIs with measurable coverage and rate limits.
- In parallel, investigate **Reddit API access/licensing for the actual SaaS use case**; if allowed, implement an official, credentialed bounded adapter; if unavailable, surface the precise blocker promptly.
- Evaluate further authorized platforms using the same security/permission checklist, minimizing duplicate content, and preserving 500-founder fair queue/rate-limit behavior.

**This ordering does not mean Reddit or the additional approved target families are deferred without the founder's knowledge.** Maintain a dated gap register and explicitly ask for owner scope direction if terms, time, quota, or legal access makes a target impossible.

## Explicit non-decisions

- No exact Reddit or other provider authorization has been granted by this ADR; no successful API request, licence, current rate limit, or free use has been checked.
- No unapproved commercial scraping, paywall/login bypass or copying other providers' copyrighted content into product storage.
- No guarantee that 500 users can run simultaneous live searches within external quotas, nor that a platform returns complete search results.
- No replacement of source attribution with fabricated model summaries.
- No external API payments; payment would require separate founder approval changing the ₹0 research API constraint.

## Acceptance evidence

For each provider enabled:
1. Source-registry approval with dated terms/access review, data minimization and retention restrictions.
2. Reproducible legitimate live fetch on intended deployment, actual source URL/provider record ID/retrieval timestamp, and no fabricated examples.
3. Rate limit, timeout, 429, unsupported search, deletion and terms-change behavior.
4. Normalization, dedupe, provenance/citation consistency and cross-workspace auth tests.
5. A quality sample of actual relevant and irrelevant demand signals; false positives and source bias disclosed.
6. Clear feature-flag/status indicator in UI and per-source integration documentation.
7. For Reddit/restricted platforms, specific affirmative authorization for the intended usage before enabling.

**Approval record:** Founder selected **technical decision 4, Option C** on 18 November 2026. This ADR approves a broad **permission-gated integration strategy**, not proof that specific platforms, especially Reddit, are technically or contractually available.
