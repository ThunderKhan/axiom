# ADR-005 — Groq Primary, Gemini Conditional Fallback for AI Inference

**Status:** APPROVED — provider strategy; integration and current policy checks outstanding  
**Decision date:** 18 November 2026  
**Decision owner:** Axiom founder (technical decision 3 of 6)  
**References:** [System Architecture](../05-SYSTEM-ARCHITECTURE.md), [TRD](../06-TRD.md), [AI Engine](../09-AI-ENGINE.md), [Security](../17-SECURITY.md), [Testing](../14-TESTING-STRATEGY.md)

## Context

Axiom needs model-backed adaptive onboarding, public-demand intent extraction, competitor claim analysis, evidence explanation, and qualitative scenario interpretation. Inference must be source-grounded, affordable under the approved **₹0 external AI/research API spending** constraint, and safe for founders' potentially confidential startup plans. Both quota and current data-processing terms depend on the exact API account, endpoint and plan; no provider integration has yet been validated.

Four approaches were proposed: Groq alone with an abstraction (A); Gemini free tier alone (B); Groq primary + Gemini privacy-gated fallback (C); or self-hosted open models (D).

## Approved decision — Option C

1. **Primary:** Groq's legitimate no-charge inference API, using a suitable model chosen only after live structured-output tests, rate/quota checks and policy/license review.
2. **Conditional secondary:** Google's Gemini API (free-access tier where genuinely permitted) is a **fallback**, not an automatic second processor of every prompt. It may receive a request **only if** its exact current plan's data-use and processing terms permit that request's data classification, and the user has the required disclosure/consent where applicable.
3. **Provider-independent adapter:** The application and research worker call a shared typed inference router; prompts, task schema, response validation, evidence/citation checks, and business rules are not hardcoded to either vendor.
4. **Default data posture:** Founder product ideas, user profiles, CRM details, notes, private drafts, credentials and other confidential content **must not silently fail over to Gemini free tier**. For such content, unless appropriate terms and permission are independently established, the system stays on an eligible provider or uses a truthful deterministic/manual fallback.
5. **Public-source-only jobs:** Model enrichment of genuinely permitted public source excerpts may use Gemini fallback **if** current API terms permit it and content is stripped of unrelated private founder information, secrets, personal data and unnecessary identifiers. "Public" does not automatically mean unrestricted rights to submit or retain content; verify source and model-provider terms.
6. **Explicit router outcomes:** `completed_groq`, `completed_gemini`, `degraded_rules`, `blocked_by_policy`, `provider_unavailable` (illustrative event names), with provider/model IDs, timestamp, prompt schema version, reason, quota/error and any permissible consent evidence. Do not imply the secondary provider ran when it did not.
7. **Evidence and output integrity:** Pydantic/JSON schema validation, existing source IDs/locators, unsupported-claim rejection, deterministic negative/abstention rules and frozen Counterfactual baselines apply **regardless of provider**. Neither model can modify authorization policy, run unapproved actions or send outreach.
8. **Cost and fallback limits:** Keep total paid external inference/research API spend at **₹0**; configure quotas, bounded retries and alerting. No paid tier, credit, overage or automatic paid upgrade is authorized by this ADR. Managed hosting budget permitted under ADR-008 remains a separate category.

## Recommended routing sequence

1. Classify the task and data: `public_source_only`, `founder_private`, or `mixed/unknown` (treat mixed/unknown as private until validated).
2. Minimize the prompt and redact keys, private identities and unnecessary profile fields.
3. Try Groq **only after verifying its current API processing/privacy conditions for the classified content** and actual no-charge quota.
4. If Groq is unavailable, validate secondary data policy and required consent for this **particular request**. If permissible, call Gemini under no-charge quotas, validating the response identically.
5. Otherwise degrade explicitly to deterministic extraction/question-bank/coverage checks or report a policy/provider block; do **not** quietly copy private data to Gemini.
6. Attribute model output and sources precisely, record redacted audit metadata, never present provider availability or synthetic results as a successfully completed live model call.

```text
task, classified_data, source_snapshot
          |
       Groq allowed + available? --> yes --> structured call --> citation validation
          |
          no
          v
Gemini allowed by current terms AND required consent/data minimization?
          | yes --> structured call --> citation validation
          | no
          v
deterministic/manual fallback OR explicit blocked/unavailable outcome
```

## Alternatives and rationale

| Alternative | Result |
|---|---|
| A. Groq only | Simpler, but lacks provider-level failover when free quota or access fails |
| B. Gemini only | More concentrated free-tier data-use and quota dependencies for founder-confidential workloads |
| **C. Groq + conditional Gemini fallback** | **Selected.** Resilience when permitted, with explicit privacy and zero-spend gates |
| D. Self-hosted model | Not selected for current release due to compute, deployment, quality and maintenance burden |

**Privacy caution:** The free/no-charge tier of an external provider can have materially different data-use rights from paid/enterprise tiers. Avoid blanket claims that all Groq or Gemini offerings are confidential, never used for training, or permanently free. **Verify the specific current terms** before enabling a route for real user content. If either provider's terms fail the review, keep that route disabled; this does not change the selected abstraction strategy.

## Outstanding verification — not approved as achieved

- Obtain access/API credentials and test **actual no-charge** Groq and Gemini calls; list approved model IDs/versions and output formats.
- Read and record **current official provider data-use and retention terms** for the exact tier, region/account, and intended workload, including any source content handling.
- Confirm lawful input minimization, founder disclosure/consent design, and private-prompt blocking/fallback behavior.
- Evaluate 10+ labeled extraction/intent/fit/citation cases on each eligible route and compare model disagreement.
- Test quotas, rate limits, unsupported JSON, wrong citations, prompt injection, timeouts, circuit-breaker/failover rules and no unexpected paid charge.
- Document schema/SDK/API compatibility, logs/redaction, cache isolation and prompt versioning; benchmark latency and concurrency under 500-active-founder traffic assumptions (external provider stress tests must stay bounded).
- Model choice, pricing tiers, per-model output support, provider status and privacy policy may change; reverify before deployment.

**Approval record:** The founder chose **technical decision 3, Option C** on 18 November 2026. This ADR approves the **Groq-primary, privacy-gated Gemini-fallback strategy**, not actual service availability, model selection or permission to transmit confidential founder information under unverified terms.

**Provider references for verification:** [Groq docs](https://console.groq.com/docs/overview), [Groq privacy](https://groq.com/privacy-policy/), [Gemini API pricing](https://ai.google.dev/gemini-api/docs/pricing), [Gemini API terms](https://ai.google.dev/gemini-api/terms).
