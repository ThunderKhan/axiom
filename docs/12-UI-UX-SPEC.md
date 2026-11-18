# Axiom — UI/UX Specification

**Status:** DRAFT — in review · **Version:** 0.1 · **Date:** 18 November 2026  
**Authority:** [PRD](02-PRD.md), [MVP](03-MVP.md), [Approved User Flows](04-USER-FLOWS.md), [Architecture](05-SYSTEM-ARCHITECTURE.md)

## 1. Experience principles

**Editorial market intelligence, not another generic AI dashboard.** Axiom has a clear primary narrative: define a product → discover actual demand → inspect why it matters → understand competition → test alternative strategies → decide and save follow-up. Each screen should enable meaningful progression, not display vanity metrics.

The user begins at **public landing → normal login → authenticated application**. Evaluators use ordinary pre-provisioned accounts; no public sandbox, judge page or permission bypass. Authenticated first destination is **Opportunities**, unless a product workspace/profile must be created or resumed.

Design is content-first, accessible, information-dense where needed but breathable. Use purpose-driven motion for transitions, evidence focus and job progress; no decorative particle backgrounds or misleading simulated activity.

## 2. Proposed application routes

| Route candidate | Main purpose / required controls |
|---|---|
| `/` | Public landing; real product narrative and CTA to login, accurate YARC attribution |
| `/login` | Secure normal login, validation, errors and session recovery as supported |
| `/app` or `/app/opportunities` | Current workspace opportunity feed, discovery, filters and state |
| `/app/workspaces/new` | Create product workspace |
| `/app/onboarding/[workspaceId]` | Adaptive conversational questions, save/resume/profile confirmation |
| `/app/opportunities/[signalId]` | Signal detail, intent/fit reasoning, source links |
| `/app/evidence/[assessmentId]` | Graph, report, verdict, provenance and actions |
| `/app/competitors` | Search/suggest, confirm, analyze and compare competitors |
| `/app/scenarios/[assessmentId]` | Counterfactual alternatives and baseline comparison |
| `/app/crm` | Saved leads, stages, notes, follow-ups, drafts |
| `/app/history` | Saved runs, reports and exports |
| `/app/settings` | Profile, integrations, provider and data limitations |

These are **proposed UI URLs**, not final API contracts. Route authorization and workspace selection must be enforced server-side, not merely through navigation.

## 3. Landing and login

**Landing:** editorial headline (*Find demand. Prove your edge.* as a working option), restrained hero, concise workflow demonstration, screenshots only if accurate, source/evidence credibility section, genuine feature highlights, open-source/GitHub links and honest YARC attribution. One primary CTA goes to login. Show meaningful product proof rather than imaginary conversion metrics or fabricated user logos.

**Login:** simple accessible email/password or reviewed provider-supported mechanism, show/hide password, error messages without revealing whether an account exists, loading/disabled submit, session expiration/return-to route handling. There is **no need for evaluators to sign up**: provide credentials privately. If self-service signup exists for normal users, keep it separate from evaluation requirement.

## 4. Workspace and adaptive onboarding

Workspace switcher is persistent and prominent enough to prevent editing the wrong product. A new user creates a product workspace and chooses **Idea** or **Live product**. Stage alters language and capability interpretation.

**Question interaction:** one of typically 10–15 questions at a time. A question card includes why it matters, contextual free text or structured options, visible progress, Back/Skip/Save-and-resume and a short AI clarification where useful. Suggested answers from URL extraction are explicitly marked "suggested; confirm". A deterministic question-bank fallback must work when AI is down. Do not require 15 questions if enough context exists; skip irrelevant branches.

**Minimum question families:** product name and stage, problem, target customer, industry, geography if relevant, present alternative, planned/confirmed capabilities, absent capabilities, differentiation, pricing hypothesis, optional URL, competitors, preferred customer signals, limitations, profile review.

**Review and confirm:** editable structured summary, labels for confirmed/proposed/unknown, profile version and "Start discovery". Without minimum context, request only missing required fields. Keep answers across logout/resume.

## 5. Opportunities and investigation

**Default app view:** focused search prompt and visible source selection/coverage; ranked signal feed. Each signal row/card presents public source family, date if known, excerpt, separate relevance/solution intent/product fit/evidence confidence, "why surfaced", and clear actions: Inspect, Save, Skip. Do not obscure low fit behind one seductive score.

**Research state:** queued/running/partial/completed/empty/failed/rate-limited/cached/seeded each has specific copy and next action. Partial source failure still displays successful results with warning. No skeleton that simulates fabricated activity; no "100 leads found" claims without underlying records.

**Signal detail:** original source accessible, exact unmet need, fit/mismatch, current profile version, source timestamps, comparison context and a prominent "Investigate evidence" action. A user can always navigate back to the originating feed/filter state.

## 6. Competitor intelligence

Two entry points: user-entered URL or **suggested competitor requiring confirmation**. List known/confirmed competitors separately from candidates. Teardown has features/pricing/positioning/gaps in a compact comparable grid with source URLs per material claim, retrieval timestamp, unknown labels and short commentary. Unavailable site or price shows honest error/Unknown and user-provided evidence alternative.

Provide export that preserves evidence metadata. No invented prices, market shares or confidence percentages.

## 7. Evidence graph — signature screen

**Desktop layout proposal:** main canvas or graph region, adjacent evidence report and a contextual inspector. Nodes distinguish customer need, founder capability, competitor assertion, supporting source, contradiction and unknown/hypothesis. Selecting an edge reveals relation, reasoning and origin/locator. Verdict is prominent yet supported, with **Pursue / Research further / Skip / Insufficient evidence** and clear next actions.

**Report parity:** an accessible ordered list/table mirrors graph relationships, source links, contradictions, unmet requirements and verdict reasons. On mobile, list/report first; graph optional, zoom/pan never sole interaction. Keyboard selects focusable nodes/relationships, Escape returns from inspector; hover is not required to access citations.

**Empty or contradictory:** when evidence insufficient, don't draw an impressive fake network; show limited nodes and a prompt to collect evidence.

## 8. Counterfactual Lab (R0)

Baseline is locked to visible evidence/profile version. The user creates **at least two named alternatives**. Each has multiple editable assumption controls: feature add/remove/modify, audience/positioning hypothesis and qualitative pricing hypothesis. Side-by-side comparison shows exactly which customer requirements change status and which remain uncertain.

Display "Hypothetical" prominently; never predict revenue or causal sales lift. Save/reopen versions and allow explicit "Rebase on new evidence" when source snapshot changes, with warning before losing comparability. If AI qualitative suggestions are unavailable, deterministic diff stays usable and is labeled.

## 9. CRM and outreach

Stages, saved leads, search/filter, notes, due follow-ups, activity timeline and draft editor. Save/modify records must persist after refresh and across sessions; cross-workspace access forbidden. Reviewable outreach draft clearly says **Draft — not sent**; user can edit/copy, never a disguised sending button. Marking "contacted" is user-recorded status, not a delivery metric.

On small screens prioritize accessible list/detail layouts over a cramped multi-column kanban.

## 10. States, accessibility and acceptance

Every page: not-configured/empty, loading/queued, partial, completed, error, stale, seeded and hypothetical states where relevant. Retry actions do not duplicate writes; preserve unsaved edits where feasible. Data source links are real or visibly fixture placeholders.

Accessibility: consistent focus, keyboard form fields, sufficient contrast, reduced motion, semantic headings/labels, alternative graph/list, understandable error text, touch targets. Performance: workspace switch never shows stale prior-workspace content; long research displays progress without blocking.

**User testing:** 1) evaluator login → workspace → discovery → evidence → scenario → CRM save/reopen; 2) idea-stage onboarding + unknown capability; 3) negative verdict and unavailable source; 4) graph on keyboard/mobile; 5) mis-scoped workspace denied; 6) editable unsent draft.

**Open design decisions:** exact wireframes, breakpoints, typography/colors in [Design System](13-DESIGN-SYSTEM.md), graph component, command shortcuts, advanced multi-panel behavior and motion thresholds. Do not treat this draft as approved component implementation.
