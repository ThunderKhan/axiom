# Axiom — User Flows and Interaction States

**Project:** Axiom  
**Document:** `docs/04-USER-FLOWS.md`  
**Version:** 1.0 — approved  
**Prepared:** 18 November 2026  
**Approved:** 18 November 2026  
**Status:** APPROVED  
**Authority:** [Approved PRD](02-PRD.md) and [Approved MVP Scope](03-MVP.md)  
**Related documentation:** [Documentation Index](01-INDEX.md)  
**Submission target:** 26 November 2026, 11:59 PM IST

> **Experience thesis:** Axiom is one continuous founder workflow: **define an idea or product → discover demand → inspect evidence and competitors → compare strategic choices → decide → manage the next action**. It must not feel like several unrelated dashboards connected by navigation links.

## 1. Purpose, boundaries, and terminology

This document specifies **who does what, in which order, with what feedback and recoverable states**. It covers interaction and user-visible behavior, not the final component system, screen pixel layouts, database migrations, API payloads, or the chosen authentication/LLM provider. Those belong in later approved technical and UI specifications.

**Governing decisions (already approved):**

- **Entry is always** a public product landing page → normal login page → authenticated web application. No public guest sandbox, no judge-only experience, and no requirement that evaluators register; evaluators use credentials supplied privately by the founder.
- The default authenticated destination is **Opportunities**, unless a user first needs to create/select a workspace or finish a usable product profile.
- Support **idea-stage founders** and founders of **launched products**, with clearly different language about hypothetical versus observed fit.
- Each account can manage **multiple independent product workspaces**. Workspace context must persist visibly across features; switching context never leaks records.
- Onboarding is **conversational, approximately 10–15 sequential questions, adaptive**, with Back, Skip, Edit, Save and resume, AI assistance, deterministic fallback, and a human-confirmed final profile.
- Research uses permitted source integrations, **hybrid explainable scoring**, hybrid competitor discovery, an **interactive evidence graph plus synchronized accessible report**, an advanced multi-scenario Counterfactual Lab, and a persistent CRM.
- Outreach is limited to **AI-assisted, human-reviewed editable drafts**. Nothing is sent automatically.
- HTTP and authenticated MCP tools expose the same domain behavior and permissions. High-risk writes require appropriate authorization and approval boundaries.
- All material external claims are attributable or explicitly unverified. Exploratory AI hypotheses are allowed **only as labeled hypotheses**, not invented facts.

**Priority interpretation:** `P0` means the minimum release gate; `R0` marks an ambitious November 26 owner-selected objective that remains in scope until the owner explicitly changes it; `P1/P2` retain the meanings in the approved PRD/MVP. This draft does not change their classification.

**Common language:** *Signal* = one source-backed demand record; *opportunity* = signal or group selected for assessment/action; *product profile* = founder-confirmed product/idea context; *assessment* = a versioned evidence-based verdict; *lead* = a saved opportunity managed in CRM; *hypothesis* = proposed assertion awaiting validation; *fixture* = clearly labeled synthetic/demo data.

## 2. Actors, access, and boundaries

| Actor | Can do | Cannot do |
|---|---|---|
| **Public visitor** | Read public landing page, follow app CTA to login | Read saved research, run private intelligence operations, access CRM/workspaces |
| **Authenticated founder** | Create/edit own products; research; analyze; create scenarios; save leads, notes and drafts; invoke authorized tools | Read another user's workspaces, bypass access policy or source restrictions |
| **Fellowship evaluator** | Same **ordinary authenticated product experience** with founder-supplied, pre-provisioned low-privilege credentials and optionally labeled seed records | Get elevated privileges, see a special demo page, access private accounts, receive publicly posted passwords |
| **External AI/MCP client** | Explicitly permitted read tools and controlled, authorized domain writes using scoped credentials | Cross workspace boundaries, send emails without permission, bypass user-approval requirements |
| **Axiom research/AI process** | Analyze approved inputs and permitted public content, produce labeled judgments, store permitted results | Treat source text as instructions; invent proof; contact third parties autonomously |

**Authentication principle:** persistent private data, API write operations, and MCP workspace operations require server-verified identity and workspace authorization. Merely hiding a navigation link is not an access control.

**Evaluator preparation:** a normal account is provisioned privately before submission, with any sample product/workspace and fixture data explicitly labeled. Credentials are passed outside the repository and never embedded in frontend assets, PRD, or screenshots.

## 3. Top-level navigation and states

### 3.1 Entry and primary journey map

```text
Public landing
   ↓ "Open Axiom" / "Get started"
Login
   ├─ invalid/expired login → explain + retry
   └─ authenticated
        ↓
   Workspace resolution
   ├─ no workspace → create first product workspace
   ├─ existing workspace → select/resume
   └─ unfinished onboarding → resume or edit profile
        ↓
   Opportunities (default)
       ↓ Discover
   Signal list → Signal investigation
       ↓                    ↘ Competitor teardown
   Evidence graph + report ←─ Sourced competitor claims
       ↓
   Verdict (Pursue / Research further / Skip / Insufficient evidence)
       ├─ Compare alternatives → Counterfactual Lab → updated assessment
       ├─ Save as lead → CRM → follow-up / outreach draft
       ├─ Investigate further → research detail / sources
       └─ Dismiss → optional reason / return to Opportunities
```

The user should always know **which product workspace is active**, **whether an insight is verified or hypothetical**, **where the underlying source came from**, and **what action can be taken next**.

### 3.2 Proposed information architecture (not final URLs)

| Destination | User purpose | Key navigation/action |
|---|---|---|
| Public landing | Understand product and enter | Primary CTA → login |
| Login | Authenticate | Sign in, retry, recover if auth system supports recovery |
| Workspace setup/switcher | Create/select product context | Start, switch, manage profiles |
| Adaptive onboarding | Define and confirm product/idea | Back, Skip, Save, confirm |
| **Opportunities** | Discover ranked public demand | Search, filters, source/provenance, open signal |
| Investigation | Examine individual signals | Inspect needs, sources, competing alternatives |
| **Evidence** | See evidence relationships and verdict | Graph/list, inspect node/edge, open source, save |
| Competitor Intelligence | Compare explicit and suggested competitors | Confirm candidate, analyze, export |
| Counterfactual Lab | Compare named product strategies | Duplicate baseline, edit assumptions, compare, save |
| CRM | Progress saved leads and next actions | Stage, notes, dates, drafts, activity |
| History / settings | Resume work, view limits and providers | Reopen reports, see disclosures, change workspace |

Navigation model: **persistent compact app navigation + contextual flow actions**. The detailed layout and exact route names remain open until `11-UI-UX-SPEC.md` is approved.

## 4. Detailed user flows

### UF-01 — Public landing → login → app [P0]

**Actor:** visitor / evaluator / returning founder.  
**Entry:** public URL.  
**Preconditions:** deployed landing and authentication system.

**Happy path**
1. Visitor sees an original editorial landing page, accurate Axiom capabilities and non-endorsement YARC attribution.
2. Primary CTA opens the ordinary login screen.
3. User signs in. The server validates the session.
4. An account with a valid product profile lands in **Opportunities** for the last valid/selected workspace. If incomplete, they are routed to workspace creation or resumable onboarding.
5. Refresh and direct deep links retain session and enforce workspace access on the server.

**Alternate/error paths**
- Wrong credentials, expired session, unavailable auth service → clear non-leaking error and retry/recovery action.
- Deep link from an unauthenticated session → login, then return to the permitted destination if safe.
- User signs out → private data cleared from current view and subsequent protected requests rejected.
- User has no workspace → first workspace setup; do not show a fake "no leads" success state.

**Acceptance:** Playwright tests full landing → login → Opportunities flow with evaluator account and unauthorized deep-link rejection. No judge-only/guest route exists.

### UF-02 — Create, select, and switch product workspace [P0]

**Actor:** authenticated founder.  
**Entry:** first successful login, workspace switcher, or "New product".

**Happy path**
1. User creates a workspace with a product/idea name.
2. Axiom records workspace identity and activates it.
3. User completes/continues its product profile.
4. User creates a second workspace, selects either using the same switcher.
5. Opportunities, research history, competitors, CRM, simulations, and drafts update to the selected workspace.

**Alternate/error paths**
- Empty/invalid name → inline validation.
- Save failure → preserve form state and retry; don't duplicate workspaces.
- Workspace removed or access revoked → deny and return to safe valid workspace selection.
- In-flight research begun in workspace A while user switches to B → prevent A's response from appearing as B's result; operations retain originating workspace scope.

**Acceptance:** attempts to read/update a different user's workspace through UI, REST, or MCP fail. Records remain isolated across both workspaces.

### UF-03 — Adaptive conversational onboarding [P0]

**Actor:** idea-stage founder or launched-product founder.  
**Entry:** new product workspace, "Edit profile", resume unfinished onboarding.

**Happy path**
1. Axiom asks whether the user has **an idea** or **a launched product**; the choice changes question phrasing and follow-up relevance.
2. Questions appear **one at a time**, with visible progress and why the answer matters.
3. User answers free-text, selects structured choices, or adds an optional website URL. AI may summarize answers, propose clarifications, and suggest next relevant questions.
4. A short established question bank ensures an approximately 10–15 question path, with conditional skips and branches.
5. At any point user selects Back, Skip, or Save and resume; previous answers persist.
6. Before use, a **profile review screen** shows proposed capabilities, buyer, constraints, sources of information, and unresolved questions. The user edits and confirms.
7. Axiom saves a versioned product profile; discovery and assessments reference this version.

**Alternate/error paths**
- AI times out / free provider quota is exhausted → continue deterministically with a branching question bank without destroying progress.
- URL extraction is blocked → manual description still works; inferred facts remain suggestions, not automatically confirmed features.
- Too little usable context → explain which required minimums are missing and allow revisions; skipped optional fields remain **Unknown**.
- Resume after login/session interruption → return to saved last completed step.
- Changing the product stage → explain that prior assessments may need re-analysis.

**Acceptance:** idea-stage and launched-product branches work, Back/Skip/resume behave, final profile requires explicit confirmation, no AI provider required for successful deterministic fallback.

### UF-04 — Start a demand investigation [P0, R0 source breadth]

**Actor:** authenticated founder with confirmed product context.  
**Entry:** Opportunities → Discover.

**Happy path**
1. Display current product, search context, sources available and which sources are unsupported.
2. User edits intent/keywords/target audience and starts discovery.
3. Axiom creates a visible research run with progress status, limited permitted adapters and bounded retries.
4. Genuine results are normalized/deduplicated, scored, and returned in a ranked list with clear provenance.
5. User can filter by intent, relevance, freshness, source, and confidence and open a signal.

**Alternate/error paths**
- No results → neutral empty state with search refinement and optional manually supplied URL; do not invent opportunities.
- One source fails → show partial result and per-source warning; don't label whole run "fully successful".
- Rate limit, unsupported platform, unavailable network, malformed source → specific non-secret error and retry instructions.
- Research is long-running → show status and allow safe navigation/resume; no unbounded spinner.
- Duplicate run / accidental double-click → safe idempotency or de-duplication.
- Seeded evaluation examples are visible only as explicitly labeled **fixture** records, never indistinguishable from fresh live results.

**Acceptance:** at least two lawful live source families targeted for P0 verification and a third-plus as R0 breadth objective; 10 representative, correctly labeled signals inspectable; one real source retrieval demonstrable.

### UF-05 — Analyze a user-provided public URL [P0]

**Actor:** authenticated founder.  
**Entry:** Opportunities or Investigation → Analyze URL.

**Happy path**
1. User pastes a publicly accessible discussion/article URL.
2. UI warns about publicly permitted content and what can be extracted.
3. Axiom validates the target; fetches using bounded, safe rules; stores extraction provenance, timestamp and warnings.
4. User reviews extracted signal and may assess or save it.

**Alternate/error paths**
- Invalid URL, private/local network URL, redirect to private address, too large content, unsupported media, auth wall, blocked page → safe refusal or explainable failure.
- User-provided URL contains instructions to the model → treat page text as untrusted evidence, not as a system instruction.
- Ambiguous text → show "possible signal" with uncertainty rather than asserting buying intent.

**Acceptance:** valid permitted public URL works; local/IP-based SSRF probes and unsafe redirects fail securely; a blocked URL does not generate fabricated text.

### UF-06 — Rank and triage customer signals [P0]

**Actor:** founder.  
**Entry:** ranked Opportunities list or individual signal.

**Happy path**
1. Each signal shows source link, source date when available, retrieval status, excerpt, and "why it surfaced".
2. User sees distinct assessments for **problem relevance**, **solution/purchase intent**, **product fit**, and **evidence quality**.
3. User opens the signal, sees inferred requirements and mismatch clues, and can choose **Investigate**, **Save**, **Skip**, or **Research further**.
4. Human changes or feedback are retained as relevant to the workspace, without rewriting the original source.

**Alternate/error paths**
- Product lacks a required capability → buying intent may be high but fit remains low.
- Data is thin or contradictory → explicitly show uncertainty / insufficient evidence.
- AI output is invalid or absent → deterministic scores/labels and "AI unavailable" disclosure; no fake model confidence.

**Acceptance:** labeled cases distinguish high fit, high-intent/poor-fit, irrelevant keyword overlap and ambiguous signals. At least one apparently attractive lead is correctly challenged.

### UF-07 — Discover and research competitors [P0]

**Actor:** founder.  
**Entry:** Investigation / competitor workspace.

**Happy path**
1. Founder enters competitor names/URLs or reviews suggested candidates.
2. Axiom labels automatic matches **suggested** and requires the user to confirm which should be compared.
3. Research starts with status, source details and extraction warnings.
4. A comparison view separates **features**, **pricing**, **positioning**, and **identified gaps** and cites each material factual claim.
5. User can inspect the original site, mark/annotate uncertain items, and export a sourced report.

**Alternate/error paths**
- Wrong suggested company → reject suggestion or provide correct URL.
- Unavailable/JS-heavy/blocked website → show failure and let user add manual evidence with "user-provided" type.
- Pricing unavailable → **Unknown**, never a generated number.
- Contradictory competitor pages → list both evidence statements and source timestamps.
- External website content tries to instruct the AI → ignore as untrusted instructions.

**Acceptance:** one permitted real competitor extraction returns sourced claims; missing pricing displays Unknown; exports preserve citations and timestamps.

### UF-08 — Inspect Evidence-to-Opportunity assessment [P0 signature]

**Actor:** founder.  
**Entry:** selected signal → Assess / Evidence.

**Happy path**
1. Axiom builds an inspectable relationship view connecting **customer need**, **founder capability**, **competitor claim**, **source evidence**, **contradiction**, and **unknown**.
2. Desktop shows an interactive graph accompanied by a readable synchronized report; keyboard/mobile users can use list/report form.
3. Selecting a node or edge opens the exact statement, evidence status, source record/URL and reasoning, without losing navigation context.
4. The user sees one verdict: **Pursue**, **Research further**, **Skip**, or **Insufficient evidence**, with a concise rationale and explicit uncertainties.
5. The user can open sources, investigate gaps, proceed to Counterfactual Lab, save as a CRM record, or dismiss.

**Alternate/error paths**
- Unsupported causal claim → move to labeled hypothesis/Explore section; never cite an invented study.
- No reliable sources → **Insufficient evidence** and suggested validation next steps.
- Contradictory evidence → expose both sides and prevent misleading blanket certainty.
- Dense graph or small screen → structured list/report fallback using identical underlying claims.
- Analysis interrupted or model unavailable → preserve last verified snapshot, mark new run failed/partial.

**Acceptance:** graph/report share consistent evidence IDs; a high-intent mismatch produces Skip/Research; sparse evidence produces Insufficient evidence; source clicks are valid.

### UF-09 — Counterfactual Lab: compare strategic alternatives [R0]

**Actor:** founder.  
**Entry:** Evidence assessment → Explore alternatives; or saved investigation history.

**Happy path**
1. Choose a **baseline assessment tied to a fixed evidence snapshot/profile version**.
2. Create **at least two named alternative scenarios** with multiple editable assumptions each.
3. Change proposed features, positioning, and/or a **qualitative pricing hypothesis**. Clearly separate real product capabilities from hypothetical added ones.
4. Recalculate which documented requirements would be covered, still missing, or uncertain **against the same evidence snapshot**.
5. View baseline and scenarios side-by-side: changed assumptions, affected needs, changed qualitative verdict, support/contradictions, and hypothesis tags.
6. Save the scenarios and return to reopen, edit, or compare them.

**Alternate/error paths**
- Simulation could not calculate from evidence → label unsupported/inconclusive, not "high confidence".
- User changes underlying product profile/evidence during a saved simulation → warn of mismatch and offer explicit rebase/new version, never silently mix baselines.
- AI enrichment fails → use deterministic coverage comparison and explicitly mark unavailable qualitative analysis.
- Proposed pricing/positioning lacks market evidence → hypothesis only; no invented revenue lift, conversion rate, or market share.

**Acceptance:** two saved, meaningfully distinct scenarios with multiple assumptions; reload reproduces comparison against frozen evidence; no fabricated business forecasts.

### UF-10 — Save, revisit, and advance a lead in CRM [P0, R0 advanced workflows]

**Actor:** founder.  
**Entry:** signal, assessment, or CRM workspace.

**Happy path**
1. From an investigation, user chooses Save as lead/opportunity.
2. Axiom stores source provenance, selected assessment/version, workspace, and initial stage.
3. CRM displays saved records with stages such as **Spotted → Qualified → Contacted → Closed/Lost** (final labels and customization can be refined by UI spec).
4. User changes stage, adds/edit notes, sets a follow-up due date and state, and sees activity history.
5. Search/filter quickly locates records; returning after sign-out and sign-in restores them.
6. Axiom may help propose next actions, but user owns the decision and any external outreach.

**Alternate/error paths**
- Saving a previously saved signal → detect/handle duplicates instead of creating silent duplicates.
- Required information missing → request only necessary fields, preserve draft state.
- Save fails → explicit failure and retry; no fake success toast.
- Invalid workspace or deleted lead → safe not-found / unauthorized state.
- Marked "Contacted" → reflects a user-recorded real action, not an Axiom email-send claim.

**Acceptance:** lead, note, stage and follow-up survive reload/login; activity history is coherent; cross-workspace writes are rejected. Advanced R0 reminders, filters, and export have separate completion records.

### UF-11 — Create and review an outreach draft [P0 controlled behavior; R0 enhancements]

**Actor:** founder.  
**Entry:** saved lead → Draft outreach.

**Happy path**
1. User requests a draft for a particular saved opportunity.
2. Axiom shows which *public* research context it will use and discloses uncertainty.
3. AI proposes a concise message, using evidence without claiming a relationship that does not exist.
4. User edits and saves a draft; it remains marked **Draft / Not sent**.
5. User may manually copy the message into their chosen external channel subject to relevant consent and platform policy. Axiom records no delivery event.

**Alternate/error paths**
- Low-quality context → advise against outreach or request more context.
- AI unavailable → user may write a manual draft.
- No consent or relevance → avoid automation; public posts do not establish private-contact permission.
- Duplicate generation → preserve previous version rather than silently overwriting.

**Acceptance:** draft generation (when provider available), edit and persistence work; **no sending side effect or fake delivery status** occurs.

### UF-12 — Export, inspect history, and resume investigations [P0 minimal]

**Actor:** authenticated founder.  
**Entry:** assessment, competitor report, scenario, or History.

**Happy path**
1. User selects an older research run and sees its status, profile version, source snapshot and analysis timestamp.
2. Axiom reopens the prior report/graph without pretending old evidence was refreshed.
3. User exports the assessment or competitor brief in a readable **Markdown/HTML or downloadable** format.
4. Export includes source URLs, claim types, retrieved dates, uncertainties, and the difference between real records, hypotheses, and fixtures.

**Alternate/error paths**
- Source URL since disappeared → preserve recorded source metadata and note that the live site may have changed.
- Large/export generation error → explicit retry/error; original report retained.
- Workspace access lost → deny export rather than leaking content.

**Acceptance:** exports match app disclosure semantics, and saved investigations can be reopened.

### UF-13 — External HTTP API consumer [P0]

**Actor:** authorized API client using documented credentials.  
**Entry:** documented discovery or competitor teardown HTTP operation.

**Happy path**
1. Client sends authenticated, validated request with permitted workspace scope.
2. Server executes the same domain operation used by the web app.
3. API returns a typed result with provenance, status, warnings, and stable error semantics.
4. Developer documentation shows actual executable examples and realistic response/error examples.

**Alternate/error paths**
- Missing/expired credentials → unauthorized.
- Wrong workspace → forbidden/not-found as appropriate without cross-account leakage.
- Invalid URL/body → validation failure.
- Rate limit/upstream failure → distinct, bounded and recoverable error.
- Long-running research → asynchronous job reference or bounded response (exact pattern decided in API spec).

**Acceptance:** **two independently callable working endpoints** cover discovery and competitor teardown; automated API contract tests pass. Exact methods and payloads belong to `07-API-CONTRACTS.md`.

### UF-14 — External MCP research and controlled write [P0; R0 breadth]

**Actor:** authenticated external agent/client.  
**Entry:** documented MCP connection.

**Happy path**
1. Agent authenticates and selects only a workspace to which it is authorized.
2. Agent lists available typed tools and calls research tools, obtaining source-aware results.
3. P0 tools: `discover_opportunities`, `research_competitor`, `assess_opportunity`, `list_saved_leads`, `save_lead`.
4. A CRM mutation passes the same authorization, input validation, idempotency and audit rules as a web action.
5. The result is visible in the corresponding user's CRM, without duplicate or cross-workspace effects.

**Additional R0 tools (tracked separately):** `update_lead_stage`, `create_followup`, `inspect_evidence`, `compare_scenarios`, `generate_outreach_draft`, `list_workspaces`, and approved monitoring controls. Releasing the first five does **not** imply the expanded list is complete.

**Alternate/error paths**
- Agent lacks workspace permission or explicit approval scope → deny write.
- Malicious text from a web page is included in a tool result → treated as data, never new MCP instructions.
- Token expiration/transport failure → clear error; no silent retry of non-idempotent writes.
- Client requests emailing or unauthorized scraping → refusal/unsupported capability.

**Acceptance:** real external MCP client can call P0 research tools and an authorized controlled write; unauthorized workspace write fails; audit is recorded.

### UF-15 — Free provider quota, external outages, and partial research [Cross-cutting]

**Actor:** founder or evaluator exercising any AI/data-dependent feature.

1. Axiom clearly distinguishes **loading**, **partial**, **completed**, **failed**, **cached**, and **seeded** states.
2. If an LLM's legitimate free quota expires, retain deterministic functionality where applicable and show which AI enhancement was unavailable.
3. If a source fails, do not synthesize nonexistent live records or mask the adapter error.
4. If all external sources fail, offer retry, modified query, manual URL where permitted, or explicitly marked preloaded examples—still only in the authenticated app.
5. If an operation was safely canceled or re-run, previous verified records remain intact and are not presented as new.
6. User-visible empty states always give an honest next action; never show endless spinners.

**Acceptance:** injected provider failures preserve correct status and do not produce fake citations or successful research claims.

## 5. Adaptive onboarding question contract

The experience should feel **like an intelligent interview, not a blank chatbot**. Use a constrained question bank plus contextual AI phrasing/follow-ups. A user normally sees **approximately 10–15 questions**, not necessarily all entries below. This is a **content contract**, not final copy.

| Step family | Prompt goal | Idea-stage adaptation | Launched-product adaptation |
|---|---|---|---|
| 1 | Name and identity | Name your concept | Name your product/business |
| 2 | Product stage | Proposed | Existing/live |
| 3 | Core problem | What problem do you believe exists? | What problem do customers use it to solve? |
| 4 | Intended audience | Who would experience that problem? | Who currently buys/uses it? |
| 5 | Industry/market | Intended sector(s) | Served sector(s) |
| 6 | Geography/context | Target geographies, if any | Existing target geographies |
| 7 | Existing solution alternatives | What do people do today? | What do users replace with your product? |
| 8 | Capabilities | What will the concept include? | What features really work today? |
| 9 | Missing capabilities | What might you not build yet? | What is not currently supported? |
| 10 | Value/differentiator | Why might this be preferable? | What is evidenced as different? |
| 11 | Price hypothesis | Planned price or Unknown | Confirmed public/prior pricing or Unknown |
| 12 | Website/research links | Optional concept page or source | Optional website; suggestions need confirmation |
| 13 | Competitors | Suspected alternatives | Known/direct competitors |
| 14 | Discovery focus | Which assumptions must be validated? | Which types of customers or signals matter? |
| 15 | Constraints and review | Non-negotiables and profile review | Product limits and profile review |

### Onboarding state contract

```text
not_started → active_step → (back | skip | answer) → active_step
                      ↘ save_and_exit → resumable
active_step → review_profile → (edit_answers | confirm)
confirm → profile_version_created → Opportunities
provider_error → deterministic_question_bank → continue
```

Required principles: preserve user answers across sessions; expose "AI suggestion" versus "founder-confirmed" labels; do not use unconfirmed website extraction as a verified capability; change of stage or key assumptions should trigger versioning and optional reassessment warning. The profile needs a *minimal usable context* (problem, intended audience, stage, proposed or existing capability description), not compulsory completion of every optional question.

## 6. Evidence and simulation interaction rules

### 6.1 One evidence model, multiple views

The graph, report, signal detail, competitor analysis and exported brief must refer to **the same assessment and evidence version**. They can emphasize different aspects but cannot invent conflicting source facts.

**Graph interaction semantics:**
- Node categories: `customer need`, `founder capability`, `competitor assertion`, `source`, `gap/contradiction`, `unknown/hypothesis`.
- Edge categories: `supports`, `contradicts`, `requires`, `satisfies`, `does_not_satisfy`, `uncertain` (final schema defined in AI/domain spec).
- Clicking a relationship shows why it exists, its evidence type, and the source or assumption that produced it.
- Keyboard and mobile users can access the same relationships as a structured list with expandable details.
- UI copy never equates a **model inference** with a **verified external fact**.

### 6.2 Outcome semantics

| Outcome | Meaning | Appropriate user action |
|---|---|---|
| **Pursue** | Sufficient supporting evidence of relevance/fit to justify investigation or user-led contact | Save, research further, prepare careful outreach draft |
| **Research further** | Promising but material uncertainty or contradictory requirements | Inspect missing evidence, check competitors, revisit later |
| **Skip** | Known mismatch, irrelevance, or explicit non-fit | Dismiss with reason; preserve negative evidence |
| **Insufficient evidence** | Cannot responsibly determine value/fit | Gather sources or change search; no fictitious score |

**Never:** use "Pursue" as a guarantee of purchasing, infer consent for outreach, or show made-up financial uplift.

### 6.3 Simulation semantics

Scenarios are separate hypotheses over a **frozen reference assessment**. Only explicitly edited assumptions may change the comparison. The screen must communicate which supported requirements changed, which did not, and which changes are **not evidenced**. Show differences rather than claiming the AI predicts actual future sales.

## 7. Consistent screen and operation states

Every research/action surface should account for:

| State | Visible behavior | Primary next action |
|---|---|---|
| **Empty / not configured** | Explain why there is no content; distinguish no workspace, no profile, no prior runs | Create/confirm product or start search |
| **Loading / queued** | Show task description, source count/progress when known | Continue browsing / cancel safely if supported |
| **Partial success** | Show confirmed partial data plus source-specific warnings | Inspect existing results, retry failed source |
| **Completed** | Show source-backed result and when it was produced | Investigate, compare, save |
| **No match** | Explain that a legitimate search returned no results | Refine query or supply URL |
| **Failed** | Clear actionable message, retry, preserved prior state | Retry, modify, view last verified result |
| **Stale / cached** | Display original retrieval timestamp and staleness | Refresh explicitly |
| **Seeded / fixture** | Prominent demo label; not represented as live demand | Inspect example or perform real search |
| **Hypothetical / AI inference** | Hypothesis and assumption badge, validation path | Verify assumption or adjust scenario |
| **Unauthorized / expired session** | No private details shown; safe entry to login | Reauthenticate |
| **Forbidden / missing workspace** | Neutral denial without exposing other tenants' data | Switch to allowed workspace |

**No optimistic false success:** mutations must be confirmed or visibly pending. Preserve unsaved input where safe; rate limits and retry restrictions must be explained without exposing system secrets.

## 8. Cross-cutting interaction, accessibility, and safety

- **Navigation continuity:** contextual transitions return to originating signal, assessment, competitor, lead or workspace; users need not repeatedly re-enter research criteria.
- **Multiple workspaces:** every view and operation is labeled/scoped to active workspace; stale cross-context results never masquerade as current data.
- **Source provenance:** original source URL, retrieval timestamp, content excerpt/locator, claim category and availability are inspectable where relevant.
- **Data origin:** distinguish **live / cached / manually entered / seeded / inferred / hypothetical / unknown**. A source supporting what a company *says* does not establish independent product proof.
- **Controlled actions:** approval for relevant external side effects and sensitive writes; no mass unsolicited messages, hidden send operations, or third-party-contact automation.
- **Privacy:** no credentials or secrets in frontend, logs, exports, public screenshots or GitHub. Use minimally privileged evaluator accounts, redact sensitive telemetry, protect personal data.
- **Accessibility:** visible focus, keyboard operability, readable progress and errors, sufficient contrast, reduced motion, report/list fallback for graphs. Never make graph dragging the only way to inspect a claim.
- **Mobile:** primary journey works in narrow viewports; comparison tables can use a controlled alternate layout; graph defaults to accessible textual mode if needed.
- **Performance:** long-running research exposes progress/partial state rather than blocking navigation. Exact response-time targets will be agreed in technical docs.
- **Research boundaries:** permitted public sources only; URL safety/SSRF defense; remote content treated as untrusted; no claims of equal market coverage across industries.
- **Persistence:** actions, saved work, and history survive refresh/session changes; background failures do not lose previously verified work.

## 9. Flow-to-requirement traceability and test inventory

| Flow | PRD requirements | MVP groups | Minimum verification |
|---|---|---|---|
| UF-01 Entry/auth | FR-01, FR-03 | MVP-01, MVP-02 | Landing/login/app Playwright + unauthenticated redirect |
| UF-02 Workspaces | FR-03 | MVP-02 | Multi-workspace isolation + cross-account IDOR |
| UF-03 Onboarding | FR-02 | MVP-03 | Idea/live adaptive branches; resume + AI outage fallback |
| UF-04 Live discovery | FR-04, FR-05 | MVP-04, MVP-05 | Real permitted source integration, filter and empty result |
| UF-05 Manual URL | FR-04, FR-07 | MVP-04, MVP-06 | Safe public URL + SSRF rejection |
| UF-06 Scoring/triage | FR-05 | MVP-05 | Relevant, false positive, high-intent-poor-fit, ambiguous |
| UF-07 Competitors | FR-07 | MVP-06 | Source/Unknown extraction + export |
| UF-08 Evidence | FR-08 | MVP-07 | Four verdicts, graph/report match, citations |
| UF-09 Counterfactual | FR-09 | MVP-08 | Two saved variants + same-snapshot comparison |
| UF-10 CRM | FR-06 | MVP-09 | Save/edit/due/reopen and unauthorized denial |
| UF-11 Outreach drafts | FR-06, FR-10 | MVP-10 | Editable draft remains unsent |
| UF-12 History/exports | FR-12 | MVP-14 | Reopen and export with provenance labels |
| UF-13 HTTP | FR-11 | MVP-11 | Discovery + competitor HTTP contracts, auth and errors |
| UF-14 MCP | FR-11 | MVP-12 | Five P0 tools in external client, deny unauthorized write |
| UF-15 Outages | FR-04–FR-11 | MVP-04–MVP-13 | Provider timeout, quota error, retry, no fabricated success |

### Critical browser acceptance sequences

**E2E-A — Idea-stage founder:** authenticated sign-in → create product idea → adaptive interview → confirm hypothetical capabilities → live search → inspect false positive → assess with graph → save to CRM → sign out/in → reopen.

**E2E-B — Launched product:** sign in → select launched workspace → optionally ingest site suggestions → confirm product capability → competitor research from URL → inspect sourced price/unknown → export sourced brief.

**E2E-C — Counterfactual:** inspect existing evidence → make two named alternatives with multiple feature/positioning/pricing edits → compare fixed evidence coverage → save/reopen → confirm speculative claims are labeled.

**E2E-D — Security:** protected deep link without auth → rejected; workspace A tries workspace B by modified URL/ID → rejected on UI/REST/MCP; evaluator account lacks elevated access.

**E2E-E — Failure transparency:** disable AI provider → deterministic onboarding works; source access fails → partial/error status; competitor price unavailable → Unknown; no fake source returned.

**E2E-F — External integration:** authorized external client calls two HTTP endpoints and all five P0 MCP tools, including one safe permitted CRM write; unauthorized mutation fails.

A test is complete only after executable evidence on the expected environment, with date, command/run ID, outcome and known limitations. A drawn screen or mock API response does not count as a completed flow.

## 10. Implementation sequencing dependencies (not architecture decisions)

1. Auth/session + workspace context before user-private research and CRM.
2. Product profile/versioning before product-specific ranking and evidence assessment.
3. Source normalization/provenance before competitor/evidence conclusions.
4. Stable evidence/assessment contract before synchronized graph/report and Counterfactual Lab.
5. CRM persistence and authorization before write-enabled MCP tools.
6. Working domain behavior before marketing demos or screenshots claim the behavior exists.
7. A stable authenticated full journey before final visual/motion polishing and submission recording.

**Feasibility checkpoints inherited from the PRD/MVP:** 19 November live source + sourced competitor proof; 22 November full saved-opportunity journey and explicit R0 breadth review; 24 November nonessential feature freeze; 25 November verification; 26 November submission. None is treated as already completed.

## 11. Unresolved decisions delegated to later documents

The following are **open**, not implicitly approved by this flow draft:

- Visual flow presentation, exact page/route hierarchy, progress style, animation, small-screen graph and CRM layout (`11-UI-UX-SPEC.md`).
- Precise normalized evidence/graph schema, confidence logic, profile versioning and scenario recalculation (`08-AI-ENGINE.md` and `06-DATABASE-DESIGN.md`).
- Authentication provider/session lifecycle, permission middleware, persistence architecture, long-running jobs and deployment ([`05-SYSTEM-ARCHITECTURE.md`](05-SYSTEM-ARCHITECTURE.md)).
- HTTP request/response contracts, status codes, async semantics and API versioning (`07-API-CONTRACTS.md`).
- MCP transport, client auth method, tool schema, approval policy, server/tool audit (`09-MCP-INTEGRATION.md`).
- Final permitted source inventory, source access methods, quota and policy validation (`10-DATA-SOURCES.md`).
- Whether and how scheduled monitoring (P1) ships. Its absence cannot be mislabeled as complete; expanded R0 tool/source objectives require separate tracking and explicit owner decisions.

## 12. Approval and change control

**Approval record:** Founder approved this user-flow specification on 18 November 2026. Flow IDs and acceptance paths now inform the architecture, backend, frontend, AI, and testing work. Any change contradicting the approved PRD or MVP requires explicit scope approval.

**No PRD or MVP obligations are waived by this document.** If a flow proves infeasible in the remaining time, surface its risk and proposed alternative rather than silently omitting it.
