# WP-04 — Source acquisition security foundation

**Status:** Initial safe-fetch/normalizer module in review, **not a live provider integration**.  
**Requirements:** MVP-04 / FR-04 / SRC-SEC-01 / approved \`docs/11-DATA-SOURCES.md\` / SC-2026-11-23.  
**Design date:** 23 November 2026.

## Included in this PR

- A reusable standard-library-only, bounded public HTTP(S) fetch boundary in \`services/api/app/public_source.py\`. Outbound requests are **denied by default** and require the caller to affirm source-specific policy approval, which must be recorded separately. **No HTTP route or worker calls the fetcher in this PR.**
- URL validation (no credentials, query secrets, fragment, unexpected port, localhost/internal host, control characters, unsafe schemes). Each hostname is resolved before connection, **every DNS result** is checked for public routability, and the socket uses a vetted numeric IP with original-host TLS certificate verification (no proxy/environment routing). Mixed private+public DNS answers fail.
- No redirects, at most 64 KiB bytes and four-second connection timeout; reject compressed, oversized, empty, executable or unsupported responses. All transports are closed in a finally block.
- Bounded visible text extraction using standard-library parser. Scripts/styles are not retained as excerpts; no source text is interpreted as instructions. Persistable records contain a real fetch timestamp, digest, canonical URL, \`manual_url\` family and \`live\` origin **only after a real fetch**; publication date stays unknown rather than guessed. Stable record identifiers and deterministic dedupe.

## Explicit limitations and follow-up

The \`access_reviewed\` argument is **not a substitute for actual policy review**. No production route or worker is permitted to set it until a source registry records approved terms/retention, quotas, review owner and live permission. No outbound provider integration, persistent source table, live scored signals, research queue, browser experience or second source family ships in this PR. This module does not implement robots.txt or authorization for arbitrary publisher access, so broad manual URL fetch remains **disabled** until a reviewed access policy is integrated.

The default v1 manual URL contract disallows query parameters to avoid storing bearer/token query strings. Some legitimate pages therefore remain unsupported; no URL rewriting or secret-bearing link is silently stored.

Next mandatory steps: (1) provider-specific source authorization and permitted live HN/feed probes, (2) a backend-only source registry that gates connections, (3) persistent, workspace-RLS source records + research runs/jobs, (4) deterministic ranking with ten labeled evaluation cases, (5) stable source-linked API and React evidence display, (6) real network and SSRF/DNS rebinding tests on intended host. Existing hosted M1/M2 parity and human security signoff remain blocked under issue #29.

**No user/production data, credentials, hosted database or runtime deployment is mutated by this PR.**
