# Axiom — Product Requirements Document (PRD)

**Project:** Axiom  
**Product category:** AI-native market, demand, and competitive intelligence  
**Program:** YARC Builder Fellowship 2027 — Track 04, Technology Division (*Acquire + Differentiate*)  
**Reference:** YARC-F68A43FD  
**Version:** 1.0 — approved  
**Prepared:** 17 November 2026  
**Approved:** 18 November 2026  
**Submission deadline:** 26 November 2026, 11:59 PM IST  
**Status:** APPROVED — canonical product requirements in `docs/02-PRD.md`

> **Product thesis:** Finding people discussing a problem is not enough. Axiom connects observed demand, a founder's actual or proposed capabilities, and sourced competitor evidence to recommend what to investigate, pursue, improve, or decline.

## 1. Executive summary

Axiom is a web-based, AI-native opportunity intelligence workspace for solo founders, indie hackers, idea-stage entrepreneurs, and pre-seed or early-stage startups. It helps a founder describe an idea or live product, discover relevant unmet needs from legitimately accessible public sources, evaluate buying intent and product fit, examine competitors, organize opportunities in a persistent CRM, and explore hypothetical product changes through a Counterfactual Lab.

Axiom's signature capability is the **Evidence-to-Opportunity Engine**. Rather than assign an opaque “hot lead” score, it connects customer requirements to product capabilities, supported competitor claims, contradictions, missing information, and an explainable next action. It may explicitly advise **not** pursuing an opportunity. AI exploration is encouraged, but verified facts, sourced interpretations, user declarations, and unsupported hypotheses must remain distinguishable.

The product entry flow is **public landing page → login page → authenticated web application**. Evaluators use credentials supplied privately by the founder; they do not need to create accounts. There is no unauthenticated research workspace or judge-specific demo page. Authenticated users can persist multiple product workspaces. The core services will be accessible through documented HTTP APIs and authenticated MCP tools.

**Non-negotiable release principle:** a visually impressive interface does not substitute for a working, independently testable end-to-end user journey.

## 2. Problem, opportunity, and principles

### Problems

1. Founders struggle to find public discussions that contain genuine customer demand rather than unrelated keyword matches or self-promotion.
2. Lead-generation tools often blur “someone expresses buying intent” with “our product actually fits that person.”
3. Competitor research is scattered, frequently unverifiable, and difficult to connect to individual customer needs.
4. Founders maintain leads, research notes, decisions, and follow-ups in disconnected tools.
5. Idea-stage founders may mistakenly treat assumptions about an unbuilt product as verified market fit.

### Product principles

- **Evidence before confidence:** preserve original source URLs, retrieval times, relevant excerpts, and uncertainty.
- **A useful negative answer:** “not a fit” and “insufficient evidence” are successful outcomes.
- **Workflow over dashboard sprawl:** discovery → investigation → assessment → action is one coherent journey.
- **Human control:** never autonomously contact third parties or make unsupported claims on a founder's behalf.
- **Transparent AI:** disclose what the model did, what deterministic logic did, and where neither could answer.
- **Honest demos:** seed data, hypothetical scenarios, mock integrations, and live results carry explicit labels.
- **Build for extension, ship for proof:** document future breadth without misrepresenting it as shipped functionality.

## 3. Target users and scope of markets

### Primary users

- **Solo founder / indie hacker with a working product:** needs to find potential early customers and prioritize fit.
- **Idea-stage founder:** needs to discover observed demand and test hypotheses without implying that a product exists.
- **Pre-seed or early-stage startup operator:** needs repeatable research, multiple product workspaces, lead follow-ups, and competitor briefs.

### Market strategy

**Full vision:** founders from any industry can describe a product or idea.  
**Submission reality:** available public sources may overrepresent software and technology discussions. Axiom must show source coverage, search limitations, and unsupported-market gaps rather than suggest equivalent coverage for every industry. User-supplied URLs and descriptions offer broader input without claiming broad automatic discovery.

### Two product-stage modes

| Mode | Founder's input | How Axiom describes results |
| --- | --- | --- |
| **Idea-stage** | Proposed audience, problems, capabilities, constraints, assumptions | Hypothetical fit / validation opportunities; never confirmed product-market fit |
| **Live product** | Website and/or manually confirmed capabilities, pricing, audience, limitations | Evidence-backed compatibility assessment using declared or verified capabilities |

Users may change their stage and revise their product profile; assessments should record the profile version used.

## 4. Positioning and primary outcome

**Positioning:** *Market intelligence grounded in evidence.*  
**Working landing-page line:** *Find demand. Prove your edge.*  
**Primary outcome:** a founder can identify an actionable public market opportunity, understand why it does or does not fit, inspect competing alternatives, and choose a documented next step.

**North-star behavioral metric (initial):** completion of an **evidence-backed opportunity decision**—an assessment inspected by a user and either saved with a next action or deliberately dismissed with a reason. This is not a claim that the opportunity will convert to a sale.

## 5. Required end-to-end journeys

### J1. New founder discovers an opportunity

1. Open the public landing page and select the application entry point.
2. Continue to the login page and authenticate. Fellowship evaluators use privately supplied, pre-provisioned credentials.
3. Complete adaptive onboarding, resume an existing product workspace, or inspect a clearly labeled seeded example within the normal authenticated app.
4. Confirm a structured product profile; specify idea-stage versus live-product status.
5. Start discovery from permitted public sources or analyze a user-provided URL.
6. Inspect ranked signals, with original links and explanations.
7. Select one signal; inspect customer needs and fit assessment.
8. Inspect a sourced competitor comparison; recognize unknowns and contradictions.
9. Save the opportunity with stage, note, and follow-up; verify persistence in the authenticated product workspace.
10. Return and reopen the same assessment and CRM record.

### J2. Founder rejects a false-positive lead

A public post shares keywords with the product but requires a feature the product lacks. Axiom marks the mismatch and advises **skip** or **research**, explaining the reason instead of promoting the lead as high-fit.

### J3. Idea-stage counterfactual investigation

A founder with an unbuilt product compares at least two hypothetical strategy variants (for example, adding offline support versus changing an entry plan), sees which **stated requirements** would be covered under each assumption, and reads an explanation of what remains unsupported. No predicted revenue, conversion rate, or causal market-share result is presented.

### J4. Responsible outreach preparation

A user asks for a contextual outreach draft linked to a saved lead. Axiom cites or references the relevant context, produces a reviewable message, allows editing, and stores draft status. No message is sent automatically. Public visibility of a post is not consent for unsolicited private contact.

### J5. External AI client via MCP

An authenticated MCP client can discover opportunities, inspect assessments, conduct a competitor teardown, and perform a controlled CRM update under the same workspace authorization and audit rules as the web app.

## 6. Functional requirements

Priority meanings: **P0** = fellowship-required or essential end-to-end functionality; **R0** = a founder-requested **November 26 release objective** that has not been waived, even if high-risk; **P1** = advisor-proposed enhancement; **P2** = longer-term vision. A dated feasibility gate can trigger an explicit scope-change decision, but it does **not** automatically downgrade an R0 requirement. The founder selected a **breadth-first** release: thin but *genuinely functioning* vertical slices are acceptable; static UI shells are not.

### FR-01. Public landing page and product access [P0]

- A branded, responsive landing page explains Axiom's distinct purpose, displays genuine product screenshots or interactive examples, provides working entry points, links to repository and documentation, and accurately notes “Built for the YARC Builder Fellowship 2027.”
- Fellowship attribution must not imply endorsement, ownership, or official partnership.
- The primary CTA opens the login page; successful authentication enters the normal Axiom web application. There is no separate evaluator-only page or unauthenticated application mode.

**Acceptance:** landing page → login page → authenticated app works end-to-end using a valid account, including evaluator credentials; no broken critical navigation or mobile overflow.

### FR-02. Adaptive conversational onboarding [P0]

- Use a sequential, conversational question experience: **typically 10–15 questions**, branching by product stage and prior answers.
- Ask about: business/idea name, short description, problem, target customer, industry, geography (if relevant), stage, URL (optional), key capabilities, missing capabilities, price or pricing hypothesis, competitors (optional), differentiators, restrictions, and desired opportunity signals.
- A URL may prefill candidate facts, but the user must confirm or edit them. Never promote an unconfirmed website inference to a verified product capability.
- Allow **Back**, **Skip**, **Edit**, **Save and resume** for authenticated users, and a final profile review.
- If the AI is unavailable, use a predefined branching question bank; label AI-assisted versus fallback behavior honestly.
- Pre-provisioned evaluator accounts may contain clearly labeled sample product profiles or research records within ordinary application workspaces; onboarding behavior and access checks remain the same for all accounts.

**Acceptance:** both idea-stage and live-product profiles can be created, corrected, and used in downstream analysis; skipping a nonessential question does not block the journey.

### FR-03. Multiple product workspaces and account isolation [P0]

- Authenticated users can create and switch between multiple independent product workspaces.
- Workspace-scoped records include product profiles, source searches, signals, assessments, competitor reports, leads, notes, drafts, and scenario versions.
- All API and MCP access must enforce server-side workspace authorization.
- Evaluators use ordinary, low-privilege authenticated accounts with isolated workspaces and, where useful, clearly labeled seeded examples. Evaluation credentials grant no bypass of normal authorization or access to other users' records.
- Team collaboration/invitations are **P2**, not an implicit requirement of “startup audience.”

**Acceptance:** a user cannot read or modify another user's workspace by changing request IDs; workspace switching changes all scoped data.

### FR-04. Opportunity Radar and source ingestion [P0 core; R0 many-source breadth]

- Given a product profile and search intent, retrieve candidate public discussions through legitimately accessible source adapters.
- **P0:** at least two functioning, independently verified source families plus manual public-URL analysis, or a clearly documented source limitation if terms/access prohibit one. Target candidates include Hacker News and suitable RSS feeds.
- **R0 release objective:** integrate three or more permitted source families, such as a verified Bluesky integration. The founder selected **many sources**, but any platform blocked by legal, policy, or technical access is a documented gap requiring an explicit tradeoff decision, not a pretext for forbidden access.
- Show source identity, original URL, publication time when available, retrieval time, excerpt, duplicate state, and provenance.
- Support user-entered search context and a visible distinction between live results and synthetic/seeded results.
- Preserve a normalized adapter contract so future Reddit, Instagram, or other integrations can be evaluated separately; do not bypass provider policies or authentication requirements.

**Acceptance:** evaluators can inspect **at least ten representative signal records** with explanation of ranking; records must identify which are real and which are demo fixtures. At least one live retrieval is demonstrated when source connectivity is available.

### FR-05. Explainable ranking [P0]

- Distinguish **problem relevance**, **purchase/solution-seeking intent**, **product capability fit**, **freshness**, and **evidence quality**; do not hide them inside one unexplained score.
- Use a hybrid process: transparent rules/deterministic filters plus optional semantic/LLM analysis with structured outputs.
- Results include a concise “why surfaced” explanation, important source text, and reasons for low confidence or rejection.
- Implement deduplication, irrelevant-content filtering, and an uncertainty/abstention state.

**Acceptance:** at least one strong match, one false positive, and one ambiguous example produce different, inspectable outcomes. A keyword match alone does not force a high-fit verdict.

### FR-06. Persistent advanced mini-CRM [P0 core; R0 advanced workflow objective]

- **P0:** saved opportunities, stages (*spotted, qualified, contacted, closed/lost*, with appropriate customization), searchable lead records, notes, follow-up due date/state, owner/workspace boundaries, timestamps, and activity history.
- **R0 submission objective:** richer reminders, filters, AI-assisted personalized draft generation, draft edits, follow-up workflows, and export.
- **P2 vision:** team pipelines, approved provider integrations, real delivery events, and sophisticated automation, subject to compliance and permissions.
- This PRD explicitly does **not** authorize or require automatic cold outreach in the fellowship MVP. The Round 3 decision for human-reviewed drafts governs how the earlier “advanced CRM” ambition is delivered.

**Acceptance:** a lead and note survive refresh/sign-in; a due follow-up persists; an outreach draft can be reviewed and edited without sending anything.

### FR-07. Hybrid competitor discovery and sourced teardowns [P0]

- Accept user-supplied competitor names and URLs, optionally suggest competitors automatically, and require user confirmation before treating suggested firms as direct competitors.
- Extract feature, pricing, positioning, and differentiation claims where available and permitted.
- Every material factual claim must carry a usable source reference (URL, quote/excerpt or locator, retrieval timestamp), or be explicitly labeled **unverified/unknown**; exploratory hypotheses must not masquerade as sourced facts.
- Produce a comparison table, strengths/weaknesses or gaps where evidence supports them, and an exportable one-page “why we may win / why we may lose” briefing.
- Handle unavailable, blocked, JS-heavy, or sparse sites with transparent errors and manual evidence entry; defend against untrusted page instructions and unsafe target URLs.

**Acceptance:** an unfamiliar competitor URL can produce a sourced report or an honest failure; intentionally missing pricing is reported as unknown rather than invented.

### FR-08. Evidence-to-Opportunity Engine [P0 — signature]

- Connect customer problems and requirements, founder-declared or verified capabilities, competitor assertions, supporting and opposing source evidence, and identified gaps.
- Use typed entities and relationships; the evidence network must be inspectable rather than an opaque AI narrative.
- Return one of **Pursue / Research further / Skip / Insufficient evidence**, with reason codes and supporting/contradictory evidence.
- Classify each statement as **sourced fact**, **user-declared capability**, **model inference**, **hypothesis**, or **unknown**.
- An exploratory mode may propose hypotheses and strategic options, but these appear under a clearly labeled **Explore** section with assumptions and validation tasks.
- A readable report must accompany the interactive graph; mobile may default to list/report mode.

**Acceptance:** at least one demo shows an apparently high-intent signal rejected because of product incompatibility, with traceable reasons; one scenario abstains because critical information is missing.

### FR-09. Advanced Counterfactual Lab [R0 founder-requested MVP capability]

- Preserve the selected full-vision requirement: multiple alternative product strategies, including feature, positioning, and pricing-hypothesis changes, with side-by-side comparison.
- **Minimum demonstrable advanced release slice:** allow at least **two named scenarios**, multiple editable assumptions per scenario (including features and a qualitative pricing/positioning hypothesis), evidence-grounded comparisons against the same saved source records, and AI-generated qualitative considerations clearly marked exploratory. The founder requested advanced simulation **in the MVP**, so deferral must be a deliberate reviewed scope change, not an assumed stretch downgrade.
- Show the exact changed assumptions, affected customer requirements, changed assessment, unsupported premises, and how the conclusion differs from the baseline.
- Do not imply that hypothetical feature coverage predicts real conversion, market share, growth, revenue, or causal outcomes.

**Acceptance:** changing a hypothetical capability changes only justified compatibility judgments; a saved scenario can be reopened and compared; the output explains its limits.

### FR-10. Controlled agentic operations [P0 bounded; P1 expansion]

- Axiom may perform multiple internal research steps once a user starts or approves an investigation.
- Show task status, operations attempted, warnings, progress, and cancellation where feasible.
- Human approval is required for external side effects or sensitive CRM modifications; autonomous contact and spam are prohibited.
- Scheduled market monitoring is part of the full vision. **P1:** a bounded schedule using approved connectors; no requirement to ship a reliable multi-tenant monitoring platform in nine days.

**Acceptance:** failure of one research step does not create false success or duplicate records; no external message sends occur as a side effect of research.

### FR-11. MCP and documented HTTP integration [P0 foundation; R0 extensive-tool objective]

- Provide at least **two documented HTTP endpoints**, including discovery and competitor teardown, as YARC explicitly requires. Example contracts: `GET /api/v1/opportunities` and `POST /api/v1/competitors/teardown` (exact payloads specified in the API document).
- Implement a real, authenticated MCP surface over the same domain services rather than a disconnected showcase.
- **P0 MCP tools:** `discover_opportunities`, `research_competitor`, `assess_opportunity`, `list_saved_leads`, `save_lead` (a write operation must enforce authorization and approval semantics).
- **R0 expanded MCP-tool objective:** `update_lead_stage`, `create_followup`, `inspect_evidence`, `compare_scenarios`, `generate_outreach_draft`, `list_workspaces`, and suitable monitoring controls after security review.
- Tools must have typed input/output schemas, explicit error responses, workspace scoping, rate limits, and audit events for writes.
- Do not expose administrative or unrestricted sending capabilities to evaluator accounts or third-party agents.

**Acceptance:** another client can invoke the documented discovery and teardown operations; an MCP tool cannot act on a workspace for which it lacks permission.

### FR-12. User-controlled exports and activity history [P0 minimal; P1 extended]

- Users can export competitor reports and opportunity assessments in a clean, shareable format (at least Markdown/HTML or a downloadable file).
- Preserve generated report versions and timestamps where practical.
- Record meaningful AI analysis and CRM changes for auditability, while not logging secrets or private content unnecessarily.

**Acceptance:** exported content includes the source disclosures and hypothesis labels visible in the app; a user can identify when an assessment was produced.

## 7. Experience requirements

### Public website

An original, high-quality, editorial landing page with a concise headline, product narrative, real capability demonstrations, prominent CTA, credible technical and privacy disclosures, GitHub/documentation links, and accurate YARC attribution. Design inspirations may inform layout and craft; do not copy third-party brand assets or proprietary source code without permission.

### Application information architecture

1. **Product onboarding / profile review** (adaptive conversational steps).
2. **Opportunities** (default first destination: ranked feed and discovery control).
3. **Investigation** (signal details, competitor research, evidence graph + linked report).
4. **CRM** (saved opportunities, stages, notes, drafts, follow-ups).
5. **Counterfactual Lab** (scenario editor and comparison).
6. **Workspace switcher, history, settings, integration disclosures**.

**Navigation:** compact persistent navigation with contextual “Discover → Investigate → Evaluate → Act” transitions. Avoid a crowded multi-dashboard shell. The evidence graph is a primary desktop interaction, but its nodes, links, source citations, and conclusions must remain available in an accessible list/report format.

**Visual direction:** editorial intelligence platform—strong typography, information hierarchy, purposeful motion, refined color system, responsive layouts, polished skeletons, and deliberate empty/error states. Detailed design tokens belong in `docs/13-DESIGN-SYSTEM.md`.

## 8. AI behavior, truthfulness, and evaluation

- **Source trust:** retrieved webpages and public posts are untrusted data, not instructions to execute.
- **Provenance:** every externally derived competitor fact and customer-source claim is linked to an identifiable source record; fake, synthetic, inaccessible, and user-provided evidence are labeled accordingly.
- **Separation of claims:** distinguish verified/source-supported statements from interpretation and speculation. A source may support what a competitor *claims* without independently proving that feature works.
- **Ranking:** establish a small labeled evaluation set with relevant, irrelevant, high-intent-but-poor-fit, ambiguous, and contradictory cases across multiple industries.
- **Failure behavior:** model timeout, empty source, invalid JSON, and conflicting evidence produce explicit errors, lower-confidence findings, or a deterministic fallback—not a fabricated final answer.
- **Adversarial tests:** prompt injection in retrieved pages; manipulated competitor text; misleading prices; duplicates; synthetic lead content masquerading as live evidence.
- **Model transparency:** disclose provider/model (where used), prompt/pipeline purpose, approximate cost or quota, fallback, and limitations. Free-tier availability is not a guarantee of capacity.

**Initial acceptance targets (proposed; subject to baseline measurement):** 100% of displayed material factual competitor claims have a source or explicit “unverified” label; 100% of simulated/scored scenarios are labeled as such; evaluated false positives are visibly rejectable; zero knowingly invented source URLs. Precision/recall targets should be set after building a labeled dataset, not invented in advance.

## 9. Privacy, consent, safety, and security

- No scraping or API use that violates a provider's access terms; every source adapter has a documented legality/access decision before enablement.
- No collection of nonpublic account data, login credentials, or enrichment with private personal information.
- Do not scrape private messages or enable mass unsolicited outreach. Human-reviewed messaging drafts are not authorization to send.
- Apply URL validation, SSRF protections, bounded fetch sizes, redirects policy, timeouts, per-source rate limits, and HTML sanitization for third-party content.
- Require server-side authentication/authorization for all persistent multi-user data and MCP write tools; protect against IDOR and cross-workspace leakage.
- Supply evaluator credentials privately through the submission channel. Never publish passwords in the repository, documents, landing page, client bundle, or logs. Keep evaluator workspaces and labeled fixtures separate from real customer data; use low-privilege accounts and rotate or revoke credentials after evaluation.
- Store only necessary data; establish retention, deletion, and source attribution policies in the technical/security documents.
- Log operational events with redaction; prevent API keys and private tokens from reaching the client, repository, or telemetry.

## 10. Non-functional requirements and accessibility

| Area | Requirement / release target |
| --- | --- |
| **Availability** | Public landing page, login page, and authenticated application accessible at a stable HTTPS URL during judging; documented failure modes for external services |
| **Performance** | Responsive UI; show meaningful progress for searches and long-running research; no unbounded synchronous request blocking |
| **Responsiveness** | All critical journeys work on common desktop and mobile viewports; evidence graph has a list-mode alternative |
| **Accessibility** | Keyboard navigation, visible focus states, accessible labels, sufficient contrast, reduced-motion handling, readable source disclosures |
| **Reliability** | Retries only where safe, timeouts, idempotent saves and job-state handling; failures never appear as successful research |
| **Observability** | Structured logs, request/correlation IDs, user-visible job status, redacted errors, health checks |
| **Testability** | Unit, API, data-layer, AI-schema, security, and Playwright E2E tests for core journeys |
| **Data isolation** | Authenticated user and evaluator workspace isolation, workspace-authorization tests, and no cross-tenant access |
| **Cost** | **₹0 planned external API expenditure**; use legitimate free tiers/open-source and enforce request quotas. Hosting and available quota must be confirmed before claiming zero operating cost. |

## 11. Scope reconciliation: vision versus November 26 delivery

The final interview deliberately prioritized **breadth**, **advanced scenario analysis within the MVP**, **many sources**, **exploratory AI**, **free APIs**, **end-to-end journeys**, and **extensive MCP tools**. The earlier advanced-CRM and controlled-autonomy choices remain, subject to the later decision for human-reviewed outreach drafts. These owner choices are recorded as **R0 release objectives** and cannot be silently downgraded.

**Engineering conflict:** all features at production depth, broad social API coverage, advanced autonomous CRM, and extensive authenticated MCP cannot credibly be guaranteed within the remaining nine-day window and a zero-rupee API budget. **Approved delivery approach:** preserve every R0 objective, implement the broadest possible *tested* vertical slices, and use explicit cutline reviews if feasibility fails. The verification floor below does **not** waive the ambitious R0 objectives.

| Area | Full product vision | Nov 26 minimum verification floor (not an R0 waiver) | At-risk expansion requiring explicit cutline decision |
| --- | --- | --- | --- |
| Markets | All industries | Industry-neutral profiles; honest source-coverage limits | Industry-specialized ranking |
| Onboarding | Adaptive AI interviewer across 10–15 prompts | Adaptive question bank + AI enhancement when available; profile confirmation | Complex agent memory/orchestration |
| Discovery | Broad multi-platform monitoring | 2 verified live source families + manual URLs; 3rd source targeted | Additional restricted platform integrations |
| Ranking | Hybrid explainable relevance and intent | Rules + available structured model assessment + uncertainty | Sophisticated personalization models |
| CRM | Advanced CRM and automation | Persistent stages, notes, follow-ups, reviewable outreach drafts | Provider sending, autonomous campaigns, teams |
| Competitors | Auto + manual discovery and detailed teardowns | User URLs + suggestions where available, sourced comparison, export | Continuous change monitoring |
| Frontier engine | Evidence graph + adversarial reasoning | Explainable verdict, graph/report, counterexamples and abstention | Large-scale graph analytics |
| Counterfactual Lab | Multiple AI-driven what-if strategies | At least 2 scenarios, multi-assumption editing, evidence-grounded comparison | Probabilistic forecasting, elaborate optimization |
| MCP | Extensive agent-control surface | Working read and controlled write tools; 5-tool P0 set | Broad agent orchestration and schedules |
| Access | Public landing → login → authenticated app | Normal app journey using pre-provisioned evaluator credentials, isolated sample workspace, and clearly labeled examples | Optional self-service registration or public access in future versions |
| Design | Distinctive premium web product | Polished landing + core responsive application | Nonessential animation flourishes |

**Decision gates:** On **19 Nov**, verify at least one lawful live source retrieval and one sourced competitor extraction. On **22 Nov**, require an actual end-to-end saved-opportunity flow **and assess progress on R0 advanced simulation, multi-source breadth, advanced CRM, and extensive MCP**. On **24 Nov**, freeze new nonessential additions and prioritize browser verification. If an R0 goal is infeasible, present the tradeoff for explicit owner approval; do not silently mark it complete or quietly remove it. These dates are targets, not evidence of completed work.

## 12. Acceptance criteria for fellowship submission

Axiom passes the **P0 release gate** only when all of the following are evidenced, not merely coded:

1. The public landing page, login page, and authenticated application load through HTTPS, with working links and visible YARC attribution.
2. An evaluator signs in using the privately supplied account credentials, enters the ordinary web app without a special demo page, and can inspect labels distinguishing live results from seeded examples.
3. An authenticated user can complete/adapt onboarding, confirm a product profile, and access the opportunities workspace.
4. At least one approved public-source path retrieves candidate signals, and the promised second source family is demonstrably functional or the release explicitly acknowledges the limitation rather than pretending coverage.
5. Ten representative examples are reviewable with rank explanations, including a false positive.
6. The CRM persists and restores a saved lead, stage, note, and follow-up without cross-workspace leakage.
7. Competitor teardown produces source-linked factual claims or explicitly unknown fields; user-selected competitor URLs are supported.
8. The Evidence Engine explains a pursue/research/skip/insufficient-evidence decision and supports an inspectable graph and readable report.
9. A demonstrable multi-scenario Counterfactual Lab is included as an **R0 requested MVP objective**; if its release slice is not functional, report the unmet requirement and seek explicit scope revision rather than claiming full acceptance. Unsupported predictions are never presented as facts.
10. At least two working HTTP endpoints are documented with request/response and curl examples; P0 MCP tools function with permissions.
11. AI models, external data integrations, fees/quotas, failure behavior, and mocks are disclosed in README/docs.
12. Critical unit, API, and Playwright browser tests run successfully in an environment corresponding to the deployed build; manual smoke-test evidence is recorded.
13. An evaluator who has been given valid login credentials can independently complete the primary journey without developer intervention; broken external services degrade honestly.

**Submission artifacts:** GitHub repository, deployed app URL, concise architecture/decisions explanation, documented endpoints, source and AI disclosures, test evidence, and a short demonstration recording as backup. The deployed app is the primary proof.

## 13. Metrics and evaluation plan

- **Primary:** number/rate of completed evidence-backed opportunity decisions in controlled evaluation and authenticated evaluator testing.
- **Discovery:** relevant-signal precision on a labeled evaluation sample; false-positive rejection rate; source coverage and failures.
- **Competitor research:** source-coverage rate, unsupported-claim count, missing-data honesty, successful extraction rate.
- **Evidence Engine:** contradiction detection, correct abstention, and consistency between graph links and report statements.
- **Product usability:** completion rate and observed friction for onboarding → discovery → assessment → save.
- **Engineering:** deployment smoke test, E2E completion, unauthorized-access tests, and documented API/MCP calls.
- **Cost:** per-session calls, free-tier quota usage, ability to disable/restrict expensive operations safely.

No unsupported numerical accuracy, conversion, revenue, or growth promises are accepted as success metrics.

## 14. Dependencies, risks, and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| External API restrictions, unavailable feeds, or rate limits | No live discovery | Verify access early; use permitted sources and manual URLs; label seed fallback |
| ₹0 API budget and unpredictable free-tier quotas | AI and demo failures | Quotas, caching, deterministic fallback, bounded requests, optional user-configured providers later |
| Broad scope in short deadline | Untested or incomplete system | Thin vertical slices, dated gates, feature freeze, no cosmetic-only completion |
| Hallucinated research claims | Trust and evaluation failure | Provenance types, abstention, citations, verification tests, explicit hypotheses |
| Graph complexity / poor mobile experience | Inaccessible signature feature | Synchronized structured report and list alternative |
| Multi-user plus MCP authorization errors | Data exposure | Shared permission checks, deny-by-default tools, cross-workspace tests |
| Website ingestion security | SSRF, injection, broken workers | URL allow/deny rules, fetch isolation, response caps, escaping, untrusted-content boundaries |
| Overlapping CRM features with another project | Schedule and ownership issues | Independent Axiom implementation; do not copy employer-owned code without authorization |
| Existing “Axiom” brand usage | Trademark/branding conflict | Treat as working fellowship name pending clearance; use descriptive identity and avoid affiliation claims |

## 15. Explicit non-goals for the submission

- Claims of verified product-market fit or guaranteed sales/conversion outcomes.
- Unsupervised cold-email campaigns, messaging strangers, bulk contact extraction, or spam automation.
- Full Salesforce/HubSpot replacement, billing, organization-wide RBAC, or team invitation platform.
- Unrestricted scraping of Reddit, Instagram, LinkedIn, or other restricted sources.
- Causal or statistical predictions from counterfactual capability toggles without appropriate data.
- A fully autonomous multi-agent system with unrestricted third-party side effects.
- A perfect pixel-level copy of another company's website or reuse of proprietary assets without permission.

## 16. Open decisions for the next planning documents

These are deliberately **not** fixed in a product PRD:

1. Exact free-tier model/provider and whether sufficient legal/demo quota is available; fallback behavior is required regardless.
2. Specific approved source adapters, their provider terms, and feasible third live source.
3. Hosting platforms, background-job execution, operational free-tier limits, and cost ceiling for ongoing hosting.
4. Authentication provider, secure evaluator-account provisioning, credential rotation, retention/deletion period, and workspace security rules.
5. Exact data model, confidence algorithm, normalized evidence schema, API payloads, and MCP transport.
6. Visual tokens, fonts, iconography, animation rules, and final product interaction specifications.
7. Final release cutline if November 19/22 quality gates expose feasibility issues.
8. Brand/domain/trademark clearance for the name **Axiom**.

## 17. Required follow-on documents

- [`docs/03-MVP.md`](03-MVP.md) — approved scope, breadth targets, quality gates, and owner-controlled cutlines.
- [`docs/04-USER-FLOWS.md`](04-USER-FLOWS.md) — detailed journey states, edge cases, errors, and acceptance test scenarios (draft pending approval).
- [`docs/05-SYSTEM-ARCHITECTURE.md`](05-SYSTEM-ARCHITECTURE.md), `docs/07-DATABASE-DESIGN.md`, `docs/08-API-CONTRACTS.md`.
- `docs/09-AI-ENGINE.md`, `docs/10-MCP-INTEGRATION.md`, `docs/11-DATA-SOURCES.md`.
- `docs/12-UI-UX-SPEC.md`, `docs/13-DESIGN-SYSTEM.md`, `docs/16-IMPLEMENTATION-ROADMAP.md`.
- Additional engineering references: testing strategy, deployment runbook, decision log.

---

**Approval record:** Founder approved the PRD on 18 November 2026 with authenticated-only evaluator access. The **landing page → login page → web app** is the single product entry flow. All R0 objectives remain recorded; any scope reduction requires explicit review and must never be presented as completed work.