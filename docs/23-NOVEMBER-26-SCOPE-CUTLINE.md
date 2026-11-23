# Axiom — 23 November 2026 Submission Recovery and Scope-Cut Decision

**Decision:** SC-2026-11-23 · **Approved by:** project owner in conversation, 23 November 2026 · **Deadline:** 26 November 2026, 23:59 IST  
**Authority:** `docs/02-PRD.md`, `docs/03-MVP.md`, `docs/16-IMPLEMENTATION-ROADMAP.md`, `AGENTS.md`, `ENGINEERING.md` v1.1  
**State:** APPROVED RELEASE-CUTLINE DECISION — not an assertion of implementation or acceptance

## Why this decision is necessary

The approved 22 November end-to-end saved-opportunity checkpoint was missed. At the 23 November review, M0 was implemented; M1 Auth and isolated-PostgreSQL acceptance passed, but the managed Supabase schema, real runtime/pooler/RLS parity, deployment and independent human security signoff remained unverified under [issue #29](https://github.com/ThunderKhan/axiom/issues/29). WP-03 through WP-11 have no corresponding verified, integrated product delivery evidence on `main`. Expanding features before completing the first founder journey creates material risk of submitting a nonfunctional product.

**Submission strategy:** preserve the independent P0 acceptance floor and build one genuine vertical slice before optional breadth: landing → login → authorized workspace → confirmed/versioned profile → permitted live source → explainable verdict + competitor evidence → saved opportunity and follow-up → reopen. Complete the minimum graph/report, scenarios and P0 HTTP/MCP tools against the same domain data where feasible; never substitute static demos for implemented endpoints. Record every unmet P0 honestly; this decision does not make an incomplete release "accepted."

## Explicit changes to previous R0 commitments

These are **owner-approved reductions for the 26 November submission**, not an assertion that deferred work is complete. Future dates require a new plan; **post-submission** means not claimed shipped by November 26.

| Requirement | Keep for 26 November | Defer after 26 November | Reason / demo impact |
| --- | --- | --- | --- |
| FR-02 / MVP-03 — conversational onboarding | Stage-aware 10–15-question bank, back/skip/save/resume, human-confirmed versioned profile; deterministic AI-outage fallback | Advanced generative question planning, conversational memory and richer AI interviewing | Genuine profile input remains testable; provider quota cannot block onboarding |
| FR-04 / MVP-04 — broad sources | Target two independently verified lawful live families (HN and individually permitted RSS/Atom), safe manual public-URL ingestion, provenance and honest blocked-provider states | R0 three-plus source-family breadth; Bluesky, Reddit and other platforms pending access/policy/limits checks | Narrower market coverage must be disclosed; never mislabel fixtures as live |
| FR-05 / MVP-05 — rich personalization | Deterministic intent/relevance/fit/evidence separation, deduplication, ten labeled examples, uncertainty and source citations; bounded structured AI only if verified | R0 sophisticated semantic personalization and exploratory breadth | Honest decisions, including wrong-fit and abstention cases, remain |
| FR-06 / MVP-09/10 — advanced CRM | Persistent CRUD, stages, searchable records, notes, follow-up due/completed, history, editable **unsent** draft, workspace isolation | R0 elaborate reminder workflows, automated follow-up orchestration, advanced export and deeper draft personalization | Working action/resume loop preserved; no autonomous messaging |
| FR-07 / MVP-06 — competitor expansion | Confirmed user URL, safely fetched sourced feature/position/price claims or Unknown, comparison and minimal report/export | Continuous monitoring, high-volume automatic discovery and expansive comparisons | Keeps real proof; no invented pricing or inaccessible-page success |
| FR-08 / MVP-07 — graph expansion | Four explainable verdicts, typed source-linked relationships, synchronized basic graph and accessible report/list | R0 advanced graph analytics and broad exploratory relationship visualization | Signature assessment and traceability preserved |
| FR-09 / MVP-08 — Counterfactual | Baseline + **two named saved scenarios**, multiple editable assumptions incl. features and qualitative position/price hypotheses, fixed evidence snapshot, grounded recomputation and comparison | R0 richer multi-strategy AI exploration, probabilistic modeling and optimization | Real what-if logic retained; no revenue, conversion or causal prediction |
| FR-11 / MVP-11/12 — expanded MCP | Two working documented HTTP domain operations; **five** authenticated P0 MCP tools sharing workspace permission checks, consent/approval for writes and external-client verification | R0 extra MCP tools, monitoring/scheduling/agent orchestration | Basic external integration remains a high-risk gate; not a fake tool registry |
| FR-01 / MVP-01/14 — polish | Responsive legitimate landing/app routes, accurate attribution, error and loading states, keyboard-readable evidence report | Decorative animation and nonessential dashboard/screen proliferation | Prioritize usability and evaluator independence |

**No new waivers:** All P0 requirements remain binding. In particular, do not cut real database tenancy, safe URL handling, source provenance, an actual competitor fetch, the Evidence Engine, persistent CRM, the two-scenario minimum, the two HTTP endpoints, five MCP tools, deployment smoke, or honest test outcomes merely to meet a calendar date. The 100/250-active-user preliminary tests remain planned; attempt/report actual results after a working deployment, never fabricate numbers. The full successful 500-active-user benchmark remains a prerequisite for broad production rollout, not for this fellowship submission.

## Execution order and decision gates (IST)

1. **23 Nov — Security boundary and profile foundation:** keep issue #29 blocked until a reviewed operator can privately provision credentials, verify recoverability and execute real Alembic and hosted RLS/pooler tests. In parallel implement WP-03 database-backed versioned profiles, minimum API and interface. Never run privileged hosted DDL through a management shortcut or persist secrets in Git.
2. **24 Nov — Critical founder vertical slice:** implement lawful source retrieval/normalization, ranking and source references, one verifiable competitor extraction path, evidence verdicts and a durable saved opportunity. By end of day, exercise the actual browser/profile/source/save/reopen journey. Freeze new nonessential scope.
3. **25 Nov — Complete minimum and prove it:** basic graph/report and saved comparative scenarios, two HTTP operations and five scoped MCP tools; deploy and test with ordinary evaluator credentials. Run real negative, integration and Playwright cases. Any unverified external surface stays explicitly blocked.
4. **26 Nov — Release evidence and submission:** final hardened deploy smoke, README limitations, demo recording, evaluator walkthrough and package submission. Internal target is **21:00 IST** to leave contingency before the 23:59 IST deadline.

### Escalation / stop-go

- **After 24 Nov:** if no complete genuine saved-opportunity flow exists, reassess and publish an evidence-backed incomplete-scope cutline. Do not replace missing features with prerecorded mock API responses, seeded-as-live data or security bypasses.
- **After 25 Nov:** freeze discretionary development; spend remaining time on correcting critical failures and truthful submission artifacts. Record any unmet P0/R0 acceptance gate as **NOT VERIFIED / BLOCKED**.
- Human review of M1 security, deployed tenant isolation and release risk is still required. The owner's broad development authorization is **not** independent qualified security approval.
- Actual deployment, nonproduction migrations, credentials and provider changes are distinguished from repository CI. Paid services must not be silently enabled; `₹0` planned external AI/research API spend remains.

## Required tracking and future backlog

Use `docs/03-MVP.md` and `docs/14-TESTING-STRATEGY.md` for P0 requirement IDs and acceptance checks; issues/PRs must link implemented changes to evidence and exact tested commit. Maintain a simple triage status for each: **verified**, **in progress**, **blocked**, **deferred by SC-2026-11-23**. Do not close a gate by changing its wording.

**Post-submission backlog:** (1) wider permitted social/source adapters, subject to legal/provider review; (2) advanced AI interviewing and personalization; (3) richer saved competitor intelligence and graph analytics; (4) advanced CRM reminders, export and human-reviewed drafting workflows; (5) sophisticated qualitative Counterfactual Lab; (6) extended MCP tools and bounded scheduled monitoring; (7) verified 500-founder concurrency and production recovery exercises before broad rollout. Open/size dedicated issues after the actual submission and preserve this decision as history.

**Document change record:** This decision explicitly amends the former **R0 November 26 target breadth** in the approved PRD/MVP; unchanged P0 and safety contracts continue to govern. The 18 November plans and checkpoints remain useful as historical baselines, not as evidence that missed deliverables shipped.
