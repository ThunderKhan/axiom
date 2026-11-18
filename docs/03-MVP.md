# Axiom — Minimum Viable Product Scope

**File:** docs/03-MVP.md  
**Project:** Axiom  
**Program:** YARC Builder Fellowship 2027 — Track 04 (Acquire + Differentiate)  
**Version:** 0.1 — review draft  
**Prepared:** 18 November 2026  
**Release deadline:** 26 November 2026, 11:59 PM IST  
**Status:** DRAFT / NOT YET APPROVED  
**Source of truth:** [Approved PRD](02-PRD.md)

> **Release thesis:** A founder can sign in, describe a proposed or existing product, find a real expression of customer demand, examine sourced competitor evidence, reach an explainable pursue/research/skip decision, explore alternative product strategies, and save the opportunity and next action — using one working, coherent application.

## 1. Purpose and precedence

This document translates the approved PRD into a finite, demonstrable November 26 release. It defines **what must work**, **which broader features remain explicit release objectives**, **how each result will be tested**, and **what requires an owner-approved change**. It is not a system architecture, final schema, or an assertion that any feature is already implemented.

If this draft conflicts with the approved PRD, **the PRD controls** until the founder explicitly approves a PRD change. Technical design documents may refine implementation without changing product behavior. Read root agents.md, engineering.md, and [01-INDEX.md](01-INDEX.md) under the repository's documented reading rules before implementation.

### Priority / commitment notation

| Label | Meaning | Release policy |
|---|---|---|
| **P0** | Foundational, essential, or directly required for the fellowship; release-blocking verification floor | A missing P0 means the release is not accepted |
| **R0** | Founder-requested **November 26 objective**, including difficult breadth/depth goals | Not automatically deferred. If unmet, record it openly and obtain an **explicit owner decision** before changing scope |
| **P1** | Useful enhancement beyond the verified core | Implement only after P0 is operational and R0 risks are assessed |
| **P2** | Post-fellowship/full-product roadmap | Not a November 26 release claim |

**Important:** "Minimum verification floor" describes the smallest independently demonstrable behavior, not permission to silently cancel R0 ambitions. **Breadth first** means thin *working* slices across modules rather than many static screens or fake endpoint stubs.

## 2. Product boundaries and user promise

### In scope for the first release

- Founder-controlled SaaS web app for **idea-stage and launched products**, initially one human account controlling **multiple independent product workspaces**.
- Industry-neutral product input, with transparent limits to the actual industry/source coverage achieved.
- Live public-source opportunity discovery, explainable ranking, persistent CRM, sourced competitor teardown, and evidence-grounded decision support.
- Interactive **Evidence-to-Opportunity** graph synchronized with a readable, accessible report.
- Multiple named strategy scenarios in an **advanced Counterfactual Lab**, changing stated capabilities and qualitative pricing/positioning assumptions.
- Controlled AI research, honestly labeled inference, user-reviewed outreach drafts, documented HTTP endpoints, and authenticated MCP integrations.
- Original product landing page, normal login, authenticated app, and evaluator accounts provisioned in advance.

### Explicitly out of scope / prohibited

- Public guest sandbox, login-free evaluator app, or dedicated judge-only demo pages.
- Autonomous emailing/contacting third parties, unsolicited mass outreach, unauthorized data enrichment, or undisclosed third-party scraping.
- Team invitations, enterprise organizations, billing/payments, full CRM replacement, unbounded multi-agent autonomy.
- Claims of validated product-market fit, guaranteed conversions, causal uplift, or financial forecasts from unvalidated what-if scenarios.
- Pretending mocked/seeded research is live, or treating a competitor's marketing claim as independent proof of that feature.
- Buying API credits: **₹0 external model/research API expenditure planned**. Free-tier capacity, hosting, and source permissions must be verified.

## 3. One complete release journey (P0)

**Flow:** public landing page → login page → authenticated web app → choose/create product workspace → adaptive onboarding or existing profile → discover → investigate → compare competitors → evidence-backed decision → save lead/follow-up → reopen saved work.

1. **Entry and identity.** Landing page contains a working app CTA. Login accepts a valid provisioned account; no signup is required of judges. Unauthenticated workspace/API requests fail securely.
2. **Product definition.** User chooses idea-stage or launched-product mode, completes/edits an adaptive 10–15-question experience (with skip/back/save/resume), confirms capabilities and assumptions. Optional website URL can suggest but not silently assert product facts.
3. **Demand discovery.** User starts a search using their profile. Results identify real source URLs, source family, excerpts, observed/retrieved times where available, live-versus-seeded state, and reasons for relevance.
4. **Intent/fit screening.** Results separately explain problem relevance, solution/buying intent, capability fit, and uncertainty. An irrelevant or high-intent-but-incompatible example is not promoted.
5. **Competitor research.** User confirms suggested competitors and/or enters URLs; Axiom extracts available feature/pricing/positioning claims, cites them, and marks missing claims unknown.
6. **Opportunity assessment.** Evidence graph and accompanying report connect customer needs, founder capabilities, competitor claims, contradictions, and gaps. Outcome is **Pursue / Research further / Skip / Insufficient evidence**, with inspectable reasons.
7. **Counterfactual exploration.** User creates at least two named alternatives, changes multiple product assumptions, compares requirement coverage and qualitative consequences, and sees explicit simulation limitations.
8. **Action.** User saves an opportunity to the CRM, edits stage and notes, sets a follow-up, optionally generates an editable outreach draft without sending, and can return after a fresh login to the same records.
9. **External integration.** At least two documented HTTP calls and authenticated MCP research/write operations operate on the same persisted, workspace-scoped data.

**Acceptance scenario AX-E2E-01:** The entire journey completes on the deployed URL using a pre-provisioned low-privilege evaluator account without developer intervention; tests and screenshots/log evidence identify which steps used live, cached, or seeded data.

## 4. MVP scope matrix — product features

| ID | Area | P0 minimum verified behavior | Additional R0 objective (not waived) | Primary proof |
|---|---|---|---|---|
| **MVP-01** | Public experience | Editorial, responsive landing → login → authenticated app; accurate YARC attribution, working GitHub/docs links | — | Browser smoke + mobile check |
| **MVP-02** | Identity/workspaces | Provisioned login, logout/session handling, create/switch **multiple** product workspaces, server-authorized isolation | — | Cross-workspace API tests |
| **MVP-03** | AI-assisted onboarding | Adaptive 10–15 question flow, stage-specific branches, editable confirmed profile, URL optional, skip/back/save/resume, deterministic fallback | More adaptive AI question generation where valid free quota allows | Idea + launched-product E2E |
| **MVP-04** | Live source discovery | **Two independently functioning permitted source families** targeted (e.g., HN plus lawful RSS), and user-supplied public URL analysis; honest error/coverage states | **Three or more** permitted live source families; broader sources where legitimately accessible | Source adapter integration tests |
| **MVP-05** | Signals & ranking | Normalized records, dedupe, 10 labeled representative examples, rules + structured AI where available, separate relevance/intent/fit/evidence, uncertainty | Wider semantic coverage and personalization within free budget | Labeled-sample evaluation |
| **MVP-06** | Competitor research | Manual competitor URLs, suggested candidates where available, URL confirmation, sourced features/pricing/positioning/gaps, unknown handling, export | Broader competitor discovery and richer comparative analysis | Live extraction + failure test |
| **MVP-07** | Evidence Engine | Typed claim/need/capability/evidence relationships; graph + synchronized report; four verdicts with contradiction/abstention support | Advanced investigation depth, richer causal-looking relationship inspection without causal claims | Negative fit + abstain cases |
| **MVP-08** | Counterfactual Lab | **Two named saved scenarios**, multiple assumptions each, feature toggles + qualitative pricing/positioning hypotheses, baseline comparison, source-linked fit changes | Multiple advanced strategy alternatives, richer qualitative AI exploration and comparison (no revenue forecasts) | Save/reload/compare E2E |
| **MVP-09** | Persistent CRM | Lead/opportunity CRUD, stage, note, follow-up date/state, activity history, filters/search, idempotent writes, workspace scoping | Advanced follow-up reminders/workflows, export, AI-written personalized drafts and edits | Persist/reopen + access tests |
| **MVP-10** | Outreach | User-reviewed, editable contextual drafts stored as drafts; **no sending** | Better personalizations and draft workflow, always human-controlled | Draft/edit/no-send test |
| **MVP-11** | HTTP integration | At least **two functional documented endpoints** for discovery and competitor teardown, auth, validation/errors, request and response examples | Additional read/write domain endpoints as needed | curl/API integration tests |
| **MVP-12** | MCP integration | Working authenticated tools: discover_opportunities, research_competitor, assess_opportunity, list_saved_leads, save_lead | Expanded tools: update_lead_stage, create_followup, inspect_evidence, compare_scenarios, generate_outreach_draft, list_workspaces, and appropriate monitoring controls | External MCP client + denied-write test |
| **MVP-13** | Responsible AI | Sourced facts vs user declarations vs model inferences vs hypotheses vs unknown, provenance, prompt-injection boundaries, fallbacks, disclosure | Exploratory strategic suggestions, explicitly separated and tied to validation steps | Fact/unknown/injection tests |
| **MVP-14** | Product quality | Accessible responsive core journeys, errors/empty/loading states, activity history, Markdown/HTML report export, basic health/observability | Additional motion, advanced views, reporting/export polish | Playwright + accessibility smoke |

**Clarifications:** A target of two live source families for P0 is a **verification floor**, not the R0 requirement to pursue many. The PRD allows an explicit and documented limitation when source access/terms prohibit an adapter; it does **not** permit misrepresenting seeded fixtures as actual integrations. Scheduled monitoring is part of the full product vision and is **P1 per the approved PRD**, while user-triggered discovery is P0. The founder's final Round 4 preference puts the **advanced scenario release slice** and **expanded MCP breadth** in the R0 category.

## 5. Detailed acceptance contracts

### MVP-01 / 02 — Entry, security, and workspaces

- [ ] Home/landing includes real product positioning and non-misleading fellowship attribution.
- [ ] Main CTA points to login; after authentication, user reaches opportunities or a valid onboarding route.
- [ ] Evaluator accounts are pre-provisioned and supplied **privately**, with no password in repository, static assets, docs, or client-side environment.
- [ ] Creating two workspaces produces isolated product profiles and records; switcher works throughout app.
- [ ] Missing/expired credentials return a safe error; user A cannot use user B's workspace ID on REST or MCP.
- [ ] Key screens work at desktop and common mobile widths; the evidence graph offers an accessible report/list fallback.

### MVP-03 — Conversational onboarding

- [ ] Founder chooses **idea** or **launched** stage; question progression depends on stage and previous answers.
- [ ] Coverage includes name, product problem, audience, industry/geography when relevant, differentiators, capability assumptions, known limits, pricing hypothesis, and desired signals.
- [ ] Back, Skip, Save and resume, and final human confirmation work; blank optional values remain unknown.
- [ ] Optional product URL yields **proposed** profile facts, not verified claims until confirmed.
- [ ] AI-failure path reverts to a deterministic branching bank without losing progress.
- [ ] Analysis references a specific saved profile version, not an untraceable changing description.

### MVP-04 / 05 — Live discovery and scoring

- [ ] Adapter contract normalizes source family, canonical URL, source record identifier (where available), content/excerpt, timestamps, retrieval state, and permissions/limits.
- [ ] Search can return **genuine live records** from allowed sources; user-entered public URLs are separately analyzable.
- [ ] At least ten reviewable signal examples (live or clearly flagged fixtures) span high fit, poor fit, false positive, and insufficient evidence.
- [ ] Duplicate records are filtered or linked; source failures, rate limits, stale caches, and missing data are visible.
- [ ] Ranking exposes separate relevance, buying/solution-seeking intent, founder-product fit, and evidence-quality signals. It does not label every problem mention as a purchase lead.
- [ ] There is at least one example where keyword overlap is high but actual capability fit is low.

### MVP-06 / 07 — Competitors, evidence, decisions

- [ ] User may provide competitor URLs and confirm AI-suggested competitors before comparison.
- [ ] A working permitted extraction path obtains at least one *real* website claim with a resolvable source URL and retrieval timestamp; fetch errors are never silently replaced by invention.
- [ ] Features, pricing, positioning, and gaps are represented separately; unavailable pricing is **Unknown**.
- [ ] Every material external fact has source metadata or an **unverified** tag. The source can prove only that a website made a claim, not necessarily that the capability works.
- [ ] Graph nodes/edges and report items share stable evidence references; selecting a connection exposes its explanation and source.
- [ ] P0 verdicts supported: **Pursue, Research further, Skip, Insufficient evidence**.
- [ ] One deliberately unsuitable opportunity yields **Skip/Research**, and one evidence-poor case yields **Insufficient evidence**.
- [ ] Exported competitor and opportunity briefs preserve citations, timestamps, unknowns, and hypothetical labels.

### MVP-08 — Advanced what-if exploration

- [ ] User creates baseline and **at least two named alternative scenarios**, with multiple edits in each.
- [ ] Changed properties may include available/proposed features, target positioning, and qualitative pricing hypothesis.
- [ ] Recompute the supported requirement coverage **against the same evidence snapshot** to prevent a changed source set from falsely appearing as simulation improvement.
- [ ] Show baseline versus scenarios, changed requirements, supporting evidence, unsupported assumptions, and qualitative AI strategic options clearly marked exploratory.
- [ ] Saving, reopening, and comparing scenarios works across sessions.
- [ ] No unsupported prediction of future revenue, sales lift, market share, or conversions.

### MVP-09 / 10 — CRM and human control

- [ ] Save a signal as an opportunity/lead; update stage, notes, due date and due/completed status.
- [ ] Activity history identifies meaningful changes without exposing credentials or sensitive logging.
- [ ] Search/filter and follow-up management work across refresh/sign-in.
- [ ] Generate an outreach draft from existing lead context, edit it, and save revision/status; **no send endpoint or background send** is triggered.
- [ ] Publicly accessible discussion data is **not** treated as permission for unsolicited private outreach.

### MVP-11 / 12 — HTTP and MCP

- [ ] Two real and independently callable documented HTTP operations: **discovery** and **competitor teardown** (final methods/paths in API contract).
- [ ] Requests implement authentication/workspace authorization, input validation, bounded operations, typed result/error structures, and operational failures.
- [ ] At least the five approved PRD P0 MCP tools are invocable by a real external client, not only screenshots or descriptions.
- [ ] MCP and HTTP use the **same domain permissions and data**, including denial for cross-workspace reads/writes.
- [ ] Mutating tools enforce explicit user authorization, appropriate approval boundaries, idempotency safeguards, and audit traces.
- [ ] Record the tested client invocation and outputs (with private credentials redacted).
- [ ] Track expanded R0 tools individually rather than marking "MCP complete" when only the first five exist.

## 6. Proposed data objects (conceptual only)

These name required **business concepts**, not approved SQL table names or a fixed data model:

| Concept | Required relationship / reason |
|---|---|
| User / session | Identity and authorization |
| Product workspace / profile version | Separate products and preserve assumption history |
| Search run / source adapter | Know when/how discovery occurred |
| Source record / evidence snapshot | Stable provenance, URL, retrieved-at, excerpt, cache/demo status |
| Signal / normalized customer need | Rank and explain actual observed demand |
| Competitor / sourced claim | Tie features, prices, and positioning to sources and dates |
| Opportunity assessment / evidence relationship | Reconstruct verdict, contradictions, unknowns |
| Lead / stage / note / follow-up / audit event | Persist actions and trace CRM changes |
| Outreach draft | Human-reviewed message with **no delivery** |
| Counterfactual scenario / scenario assumption | Replay and compare against same underlying evidence |
| AI execution / tool run | Provider/fallback status, quota, observability, errors |

Final entities, database constraints, APIs, and hosting are **TBD** in the approved technical documents; do not treat this table as a migration plan.

## 7. Integrations and third-party dependencies

### Source readiness checklist

Maintain a separate, reviewed entry for every adapter in the future data-sources document: service, access method, allowable use, authentication/quota needs, rate limits, test URL, current test result, fallback, and whether results are live, cached, or seeded.

| Candidate | Reason | Decision at MVP drafting |
|---|---|---|
| Hacker News public endpoints | Inspectable technology/customer problem discussions | **Candidate — live read not yet verified** |
| Permitted public RSS/Atom sources | Diverse searchable publications/discussions | **Candidate — permission/feed quality not yet verified** |
| Bluesky public access | Potential third independently functioning family | **Candidate — endpoint/terms/quota not yet verified** |
| User-provided public URLs | Founder-controlled research input beyond preset adapters | **P0 capability; URL safety validation required** |
| Reddit or other restricted platforms | Potential broader coverage | **Do not claim available until access terms and actual integration are verified** |

**₹0 budget constraint:** Choose truly usable free APIs/models and cache/restrict requests; show degradation if quotas expire. Never treat an assumed free tier or unknown cloud hosting cost as guaranteed available. Provider choice and environment configuration belong to the architecture and AI specs. No credentials committed to source control.

## 8. Evaluation fixtures and honesty rules

Prepare a small reproducible **10+ signal evaluation set** with source type and provenance labels; include at least:
- Clear pain + explicit solution-seeking intent + matching capability.
- High-intent but product-incapable mismatch.
- Generic conversation with no buyer intent.
- Irrelevant keyword match.
- Ambiguous/contradictory demand.
- Missing competitor pricing.
- Blocked/unavailable competitor website.
- Unsupported idea-stage capability.
- Prompt-injection attempt embedded in fetched content.
- Scenario feature improvement that changes requirement coverage, but **not** a revenue forecast.

Fixture records must be labeled **DEMO / SYNTHETIC**. Real records carry real accessible source URLs and actual retrieval state. Cached observations identify snapshot age. **No fabricated quotations, fake citations, fake "live" connections, or predetermined apparent success** masquerading as fresh research. Allow research to return empty/negative results.

## 9. Test strategy and definition of done

A feature is **implemented** only when all relevant items below pass, not when UI is drawn:

1. **Functional path:** real request → actual domain operation → persisted or grounded response → display; no hard-coded success response.
2. **Contracts:** typed validation, explicit empty/error states, authorization, no unsafe side effects.
3. **Unit/API tests:** deterministic scoring, schema parsing, source-adapter boundaries, scenario recalculation, access control and idempotency.
4. **Integration tests:** real permitted source pull and actual competitor extraction on allowed targets, with separate recorded fixture fallback.
5. **AI evaluation:** evidence attribution, wrong-fit rejection, abstention, invalid-output fallback, prompt-injection resistance; unverified facts stay clearly labeled.
6. **Browser E2E:** login, onboarding, research, evidence/graph, scenario save/compare, CRM persist/reopen, mobile fallback.
7. **Security checks:** cross-workspace IDOR attempts, MCP write permission denial, URL/SSRF handling, secrets redaction, quotas.
8. **Operational checks:** build/lint/typecheck/tests defined in engineering standards, deployed health, DB migrations, HTTPS, documented configuration, provider-free-quota behavior.
9. **Evidence:** test command/result, timestamp, URL or run identifier, screenshots/video where useful, and any known limitations.
10. **Tracking:** item status is **Not started / In progress / Blocked / Verified / Waived by owner**; never convert blocked or untested into Verified.

### Release gate matrix

| Gate | Evidence required | Result |
|---|---|---|
| **RG-01 Authentication** | Login works, evaluator account works, workspace A cannot inspect B | Not yet tested |
| **RG-02 Demand** | Live source retrieval, normalization and traceable ranked signals; 2 sources P0 target | Not yet tested |
| **RG-03 Competitive research** | Sourced feature/positioning/pricing result or explicit Unknown | Not yet tested |
| **RG-04 Intelligence** | Four verdict states, graph/report agreement, false-positive rejection and abstention | Not yet tested |
| **RG-05 Scenarios** | Two saved alternatives with multiple assumptions and grounded diff | Not yet tested |
| **RG-06 CRM** | Save/edit/reopen lead, note, stage, follow-up; editable unsent draft | Not yet tested |
| **RG-07 Integrations** | 2 HTTP endpoints, P0 MCP tools, denied unauthorized write | Not yet tested |
| **RG-08 Experience** | Landing → login → app; full E2E; desktop/mobile; no fatal console issues | Not yet tested |
| **RG-09 Disclosure** | README disclosures: AI providers, sources/permissions, mocks, quotas, limitations | Not yet tested |
| **RG-10 Deployment** | Stable HTTPS app and API, working migrations, runtime health, final smoke evidence | Not yet tested |

## 10. Schedule, dependencies, and decision gates

These are **target checkpoints**, not claims of completed work. November 26 is the fixed submission date.

| Date (IST) | Intended deliverable / gate |
|---|---|
| **18 Nov** | Approve MVP scope and map open decisions to architecture, AI, API, data-sources and UX documents |
| **19 Nov** | Feasibility gate: first permitted live source result **and** sourced competitor extraction; confirm actual free-provider limits |
| **20–21 Nov** | Working vertical slice: login/workspaces, onboarding, discovery, scoring, persistence, competitor report |
| **22 Nov** | Integration gate: complete saved-opportunity journey; review status of **all R0 objectives** (3+ sources, advanced CRM, advanced scenarios, expanded MCP) |
| **23 Nov** | Evidence graph/report, scenario comparison, MCP real-client integrations; close major blockers |
| **24 Nov** | Freeze nonessential changes; concentrate on responsive product polish, negative tests, reliability |
| **25 Nov** | Reproducible automated tests, deployed E2E, evaluator account smoke, disclosures, demo recording |
| **26 Nov** | Submission audit, stable production credentials, GitHub/documentation, deployed URLs, final submission before 11:59 PM IST |

### Prerequisite technical decisions (not approved by this draft)

1. Auth implementation and pre-provisioned evaluator lifecycle.
2. Legal/technical source-adapter feasibility and final minimum source count.
3. Free model/AI pipeline, budgets, fallback execution and structured schemas.
4. Database ownership, transaction boundaries, evidence snapshot model, workspace permission enforcement.
5. Background execution/job queue constraints, including whether scheduled monitoring is feasible.
6. Actual HTTP/MCP transport, authentication, tool-approval and audit semantics.
7. Deployment hosting/free-tier constraints, CI and rollback pathway.
8. Exact UI patterns and accessible evidence graph/list pairing.

These should be resolved in system, data, AI, API, MCP and UI docs **before their respective components are implemented**; avoid overdesigning the entire platform while the first real source and competitor extraction remain unverified.

## 11. Scope risks and owner-controlled changes

### Critical tensions

- **Maximum breadth vs eight days:** R0 calls for many source families, advanced scenarios, expanded MCP, and advanced CRM under a short schedule. A fully polished implementation of all has substantial delivery risk.
- **Industry-neutral product vs source skew:** Tech-heavy public sources cannot prove broad customer discovery quality for every industry. Display source/market limitations.
- **Exploratory AI vs evidence trust:** Hypotheses may be imaginative but must be labeled. Material competitor facts still need sources or **Unknown**.
- **₹0 external API spend vs rich AI features:** Free tiers may lack availability or quota. Have deterministic and cached *labeled* fallback paths; do not secretly use paid APIs or present an AI-disabled shell as working AI.
- **Multiple workspaces + external MCP writes:** Shared authorization and audit rules are not optional.

### Change-control protocol

If a deadline gate fails or an R0 objective becomes infeasible:

1. Record the affected requirement ID, evidence of the blocker, alternative solutions, expected demo impact, and risk.
2. Propose a specific cutline, with **keep / reduce / defer** options, to the founder.
3. **Obtain explicit founder approval** before reducing or removing a P0/R0 commitment; update the approved PRD if the change alters its contract.
4. Update this MVP scope, [01-INDEX.md](01-INDEX.md), downstream specs, the release tracker and disclosures together.
5. Mark shipped functionality from observed tests only; list unshipped items and limitations honestly.

No silently waived requirements. A failed experiment is information, not evidence of a working feature.

## 12. Submission package / reviewer checklist

- [ ] Public HTTPS landing page with product narrative and accurate fellowship attribution.
- [ ] Normal login page; **privately supplied evaluator credentials** verified on deployment.
- [ ] Authenticated app demonstrating the actual end-to-end research and CRM journey.
- [ ] Clearly labeled **live**, **cached**, **seeded**, and **hypothetical** data.
- [ ] Live source discovery and real cited competitor investigation with visible limits.
- [ ] Evidence graph plus accessible report; good and negative decisions.
- [ ] Advanced side-by-side scenario comparison and persisted follow-ups.
- [ ] Documented/callable two HTTP endpoints and real authenticated MCP tools.
- [ ] README with architecture overview, data-source decisions, free-provider/AI disclosures, safe setup, test commands, and limitations.
- [ ] Evidence of unit, integration, security, and browser E2E tests, with dated results.
- [ ] Short pre-recorded walkthrough as fallback if external providers experience an outage (recorded demo is **not** a substitute for the deployed app).
- [ ] Track each R0 commitment as verified, blocked, or explicitly changed; do not imply completion without proof.
- [ ] Repository and working deployed URL submitted by **26 November 2026, 11:59 PM IST**.

---

**Approval requested:** Confirm this November 26 MVP's **P0 verification floor**, the preserved **R0 objectives**, and the owner-controlled cutline rule. This draft does **not** itself waive or change any requirement in [02-PRD.md](02-PRD.md).
