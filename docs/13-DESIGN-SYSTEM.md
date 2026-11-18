# Axiom — Product Design System

**Status:** DRAFT — in review · **Version:** 0.1 · **Date:** 18 November 2026  
**Authority:** [PRD](02-PRD.md), [UI/UX Spec](12-UI-UX-SPEC.md), [User Flows](04-USER-FLOWS.md)

## 1. Design thesis

Axiom should look like a serious research instrument: **editorial hierarchy + precise enterprise interaction**, clear evidence provenance, restrained motion, and distinctive but functional visualization. Not a generic gradient-heavy AI dashboard and not a visual clone of any third-party product.

**Principles:** information before decoration; confidence and uncertainty look different; progressive disclosure rather than endless panels; purposeful motion, high-density data with comfortable reading; accessibility is part of visual quality.

## 2. Proposed visual foundations (not yet approved)

| Token | Candidate | Purpose |
|---|---|---|
| §--bg§ | #F7F7F4 | Warm neutral canvas |
| §--surface§ | #FFFFFF | Cards, forms, reports |
| §--text§ | #171B1B | Main readable text |
| §--muted§ | #626A6A | Supporting descriptions, metadata |
| §--border§ | #DDE1DC | Delicate structural separators |
| §--accent§ | #255D54 | Deep teal/green intentional actions |
| §--accent-soft§ | #E6F0EC | Selected/related evidence |
| §--negative§ | #9A433B | Known mismatches / errors |
| §--caution§ | #8B651D | Uncertain or requires investigation |
| §--focus§ | #2563EB | Keyboard focus indication |

Candidates should be measured for WCAG contrast at actual font sizes; **do not assume every pair meets requirements**. Dark mode optional only if consistent tokens and testing are available; don't ship an incomplete toggle. Avoid using color alone to differentiate evidence origin or verdict.

**Typography:** expressive but professional headline family paired with a highly legible sans-serif for product work and optional monospaced labels for source IDs/timestamps. Prefer open-license system fonts or installable packages that satisfy license requirements. Avoid introducing many font weights/network downloads to make an ordinary page appear premium.

**Scale candidate:** headings 32/26/21/17 px, body 15–16 px, secondary 13–14 px, footnote 12 px minimum where appropriate. Use flexible rem-based tokens and responsive type; line lengths 60–80 characters for long reports, tabular numerals for scores/dates.

**Spacing grid:** 4 px base, increments 4/8/12/16/24/32/48; dense data tables may use 8–12px cell padding. Radius candidate 6–12px for panels, consistent with a modest editorial style. Prefer subtle borders and spacing over oversized shadows.

## 3. Component inventory

Core: AppShell, TopNav, WorkspaceSwitcher, Sidebar, BreadcrumbContext, EditorialHero, PrimaryCTA, QuestionStep, StepProgress, AIHint, ProfileReview, SearchComposer, SourceSelector, SignalRow, ScoreBreakdown, Confidence/ProvenanceLabel, StatusIndicator, CitationLink, EvidenceNode, EvidenceEdgeInspector, EvidenceReport, CompetitorCompareTable, ScenarioEditor, ScenarioDiff, LeadStage, NotesPanel, FollowupControl, DraftEditor, EmptyState, ErrorState, ResearchProgress, ExportAction.

**Component contract:** typed variants, keyboard semantics, disabled/loading states, visible focus, error messages, ARIA/semantic HTML where appropriate, real data only. Shared tokens across landing/app rather than independent styles that feel like two brands.

## 4. Interaction rules

- Every primary action either navigates, produces a valid state change, or explicitly reports why it failed; no inert decorative buttons.
- Hover reveals details but not the *only* way to access a source. Tooltips also work on focus/touch alternatives.
- Progress shows which stage the research is in; do not invent percentage when duration unknown. Honest unknown ETA is better than fake completion.
- Partial data and source errors use readable language, not solely red badges.
- Forms autosave or explicit save consistently; never claim saved without confirmed persistence.
- Workspace switch resets scoped UI data/request cache and prevents previous-workspace response from appearing.
- Graph node/edge selection synchronizes with report; focus restoration on closing side panels.
- Simulation comparisons keep baseline sticky/readable; changed assumption, resulting coverage and uncertainty visibly linked.
- Prefer one contextual primary action per view and graceful empty states over cluttered dashboard KPIs.

## 5. Evidence and verdict visual grammar

| State | Treatment (not color only) |
|---|---|
| Verified/source-supported | Source icon + original link + retrieved-at and excerpt |
| Founder confirmed | User attribution + confirmed date/version |
| Hypothetical or model inference | Distinct dashed/symbolic treatment and literal "Hypothesis" / "Inference" |
| Unknown | Empty/unknown label and suggested validation step |
| Contradiction | Two opposing evidence rows with explicit contradiction marker |
| Pursue | Reasoned assessment, actionable save/research; never "guaranteed customer" |
| Research further | Visible missing evidence checklist |
| Skip | Known mismatch, reason and respectful dismissal |
| Insufficient evidence | Abstention explanation rather than blank score |

Use label text and iconography alongside palette; screen reader descriptions identify relation types and confidence qualifiers.

## 6. Motion, responsiveness and accessibility

**Motion purposes:** entering a research state, opening evidence inspector, focusing related graph nodes, showing a comparison diff, acknowledging persisted action. Default transition range about 100–240ms as a *design proposal*, no distracting looping effects. Respect §prefers-reduced-motion§ with instant changes or none.

**Breakpoints:** mobile narrow, tablet intermediate, desktop wide; exact token values established in implementation after screenshots. Evidence graph becomes readable list/report on narrow screens; competitor and scenario tables use overflow with context/stacking rather than cropped columns. Login/onboarding must work one-handed and via keyboard.

**Accessibility checklist:** semantic labels, logical tab order, focus ring, Escape/close management, heading hierarchy, input validation linked to fields, targets suitable for touch, contrast tested, skip-to-content, screen-reader-friendly graphs via equivalent list, no text embedded in generated images for core content.

## 7. UX acceptance and implementation governance

- Compare implementation to one coherent component/token system across landing/login/app.
- Inspect common desktop and mobile viewports; no horizontal page overflow for normal workflows.
- Run automated accessibility checks **and** manual keyboard path through onboarding, signal detail, graph report, CRM and scenarios.
- Reduce motion mode is effective, dark mode (if present) is functional, interactive control states aren't decorative.
- Track known visual/accessibility defects separately from performance/AI correctness defects.
- Never reuse third-party brand assets/source without permission; inspiration is not a license to clone.

**Open:** final brand clearance, typography, exact palette, graph layout library/theme, component primitives, illustrative images and landing motion. All values here are **draft tokens**, not locked engineering requirements.
