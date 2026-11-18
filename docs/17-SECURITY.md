# Axiom — Security, Privacy and Threat Model

**Status:** APPROVED — security requirements baseline; implementation and provider choices unverified · **Version:** 1.0 · **Approved:** 18 November 2026  
**Authority:** [PRD](02-PRD.md), [Architecture](05-SYSTEM-ARCHITECTURE.md), [TRD](06-TRD.md), [Database](07-DATABASE-DESIGN.md)

## 1. Scope and security boundaries

Axiom is a multi-workspace, authenticated research product that accepts user-entered URLs and untrusted public webpages/posts, generates AI interpretations and exposes HTTP/MCP interfaces. Principal risks: **cross-tenant data leakage**, **SSRF through user URLs**, **prompt-injection turning source content into actions**, **hallucinated source facts**, and **compromised integration credentials**.

Assets: accounts and session tokens, product profiles (may contain private startup ideas), CRM/notes/drafts, source snapshots, model provider credentials, database/worker secrets, MCP integration scopes and evaluator accounts.

Trust boundaries:
1. Public browser vs authenticated app/API.
2. Identity provider token vs authorization for a specific workspace.
3. Public source/user-provided URL vs safe fetch and prompt boundary.
4. Optional LLM output vs validated domain data and tool execution.
5. MCP client authorization vs privileged domain writes.
6. Worker background execution vs original initiator/workspace.
7. Managed database/service-role connection vs row-level access policies.

**Non-negotiable access flow:** public landing → login → authenticated web app. No public guest sandbox or judge-only bypass.

## 2. Threat and control matrix

| Threat | Impact | Mitigation | Blocking test |
|---|---|---|---|
| User modifies workspace_id or resource ID | Access other founders' research/CRM | Server-side user + workspace + object authorization on every path; composite FKs | Cross-user REST/MCP/worker/DB IDOR |
| Supabase service-role key bypasses RLS | Cross-tenant reads/writes | Secret server only; explicit scoped repository methods; RLS as defense where applicable | Privileged path negative test |
| Stolen JWT or MCP bearer | Unauthorized private access | Signed issuer/audience/expiry validation, short lifespan/revocation where supported, scoped MCP access | Invalid/expired/wrong-audience denial |
| Public URL SSRF/DNS rebinding | Internal network or metadata access | Safe resolver IP policy, every redirect/new connection recheck, port/type/time/size caps | Private, loopback, metadata, redirect and rebinding probes |
| Malicious HTML script/XSS | Steal sessions or manipulate UI | Parse text safely, escape/sanitize, CSP where feasible, no rendering unsafe HTML | Script/attribute injection fixture |
| Prompt injection in community post/site | Unauthorized tool calls, secret exfiltration | Treat third-party text as data; limit tools/permissions; validate output references | Hidden hostile instructions have no side effect |
| Fabricated source-backed competitor claim | Wrong founder decisions | Claim/source ID and locator validation; unknown/abstain; audit claim type | Fake competitor price, forged URL test |
| Excessive provider calls | ₹0 quota exhaustion, denial of service | Per-workspace/user/provider budgets, limits, caches, concurrency caps | Flood/quota/429 test |
| Duplicate job/CRM write | Corrupted state/outreach drafts | DB transactions, idempotency keys, retry leasing, optimistic concurrency | Restart/double-click test |
| Unauthorized outbound contact | Spam/privacy harm | No sending endpoint; drafts manually reviewed; monitoring cannot message | Assert no send tool/job exists |
| Secrets in app, logs or GitHub | Credential compromise | Secrets manager, git ignore, redacted logs, secret scan, private evaluator distribution | Built asset/log/repo secret checks |
| External source terms violation | Legal/reliability risk | Per-adapter authorization/terms/retention review before enablement | Registry + access gate |

## 3. Identity and authorization requirements

- JWT: cryptographically verify issuer, audience, signature/JWKS, expiration and relevant claims; never accept unsigned tokens or client-supplied user ID as proof.
- Each workspace has an authorized owner; every query filters by workspace and membership; no cross-tenant joins without guards.
- Low-privilege evaluator accounts are real users, provisioned in admin-controlled workflow with sample data clearly marked.
- External MCP credentials are revocable and scoped to user/workspace/tool capabilities; `crm:write` must be explicitly consented to. High-risk writes require approval design.
- Admin/service role credentials are never sent to browser; work performed with privileged DB access remains subject to application-level authorization.
- Only necessary role actions exposed; avoid broad "admin" endpoints for a hackathon demo.

## 4. Research input and AI safety

- URL validation must occur before fetch and after redirect; reject localhost, private/reserved IP, IPv6 equivalents, internal hostnames, non-HTTP schemes, credentials-in-URL, oversized/unsupported resources.
- Public posts must not contain executable instructions for the assistant. Model instructions are defined by developer-owned templates; source text is delimited untrusted evidence.
- Returned LLM JSON is validated; model cannot generate a valid "source" absent an actual source record and locator.
- Claim categories distinguish source-supported, company assertion, founder-confirmed, hypothesis, inference, unknown and fixture.
- No collection of private platform messages, enrichment with nonpublic personal data or unsolicited mass outreach. Founder manually reviews outbound drafts.

## 5. Data protection and privacy

Collect only needed founder/profile and public research excerpts. Store secret provider credentials outside source control; redact API/MCP logs and avoid raw personal message bodies in operational telemetry. Establish retention/deletion policy after source terms review; never invent policy or claim GDPR compliance based solely on documentation.

Enforce encryption in transit via HTTPS/TLS; choose managed database encryption/backup capabilities after deployment validation. Audits record action IDs, time, workspace and actor without unnecessary content. Source posts later removed upstream require policy-aware deletion/purge handling.

Evaluator account credentials are shared privately and rotated/revoked after judging; never publish them in repo, landing, screenshot, Markdown or frontend JavaScript.

## 6. Incident handling

1. Detect (auth anomaly, unexpected cross-tenant response, unsafe fetch, quota spike).
2. Contain (revoke token, disable affected adapter/tool, pause worker and cut unauthenticated access if necessary).
3. Preserve redacted request IDs and security evidence; do not leak private details in public issue reports.
4. Patch and add regression negative test.
5. Restore service from known deploy and validated data; communicate degraded state honestly.
6. Record incident and follow-up in internal decision/incident log.

**Stop-ship:** any successful cross-tenant access, unsafe SSRF, exposed privileged key, unauthorized agent write, automatic unsolicited messaging, or false factual claims knowingly presented as evidence.

## 7. Security validation checklist

- [ ] Two users/two workspaces negative API, MCP and DB tests pass.
- [ ] Session invalid/expired/wrong-issuer/audience rejected.
- [ ] Supabase RLS policies and privileged backend bypass assumptions tested.
- [ ] SSRF/redirect/DNS safety and HTML/XSS fixtures tested.
- [ ] Prompt-injection source text cannot perform tools/writes.
- [ ] Every material competitor fact cited or explicitly unverified; fixtures visibly labeled.
- [ ] No sending endpoints; CRM drafts remain unsent.
- [ ] Source adapter terms/retention approved.
- [ ] Secrets scan clean; production logs redacted; evaluator creds private.
- [ ] Rate limits, worker retries and audit events verified.

**Open decisions:** exact identity/MCP OAuth implementation, data retention period, RLS roles, source storage/licensing, CSP/session strategy, backup capabilities, abuse thresholds and incident operator. This is a technical draft, not a certification.

## 8. Additional controls for 500 active founders

- Enforce per-principal, per-workspace and provider-wide quotas with safe responses under overload; do not let one founder monopolize workers or free source/API quotas.
- Central authorization and scope checks apply under pooled database connections and across API replicas. Cache keys must be workspace- and identity-aware to avoid leaking private research between founders.
- Burst/retry load must not multiply tool writes; enforce idempotency, short transactions and bounded worker leases. Avoid PII in load-generator accounts.
- Run concurrent tenant-isolation tests alongside the [scalability benchmark](18-SCALABILITY.md). Passing a throughput test without isolation is **not** a release acceptance.

**Approval boundary:** These are mandatory security **controls and tests**, not a claim that any authentication scheme, RLS policy, MCP server or deployed instance is already secure.

## 9. Confidential inputs and multi-provider inference

[ADR-005](decisions/005-ai-inference-providers.md) approves **Groq primary** with **Gemini as a policy-gated fallback**, not blanket data sharing. Classify startup ideas, confirmed product profiles, CRM notes, drafts, and mixed/unknown context as confidential by default. Confirm exact current plan-specific provider data-use/retention terms and any required user disclosure/consent before transmission. **Never silently route confidential founder content to Gemini free tier** if those checks have not been satisfied. Use separate server-only credentials, data minimization, a request-level policy gate, tenant-isolated caches, redacted call logs and explicit blocked/degraded states. Test that forbidden fallback transmits zero private payloads. This document does not assert that current Groq or Gemini offerings meet any particular privacy condition.
