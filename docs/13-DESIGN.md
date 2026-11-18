# Axiom — Design Reference and Landing Experience

**Status:** ON HOLD — design reference draft; **not approved**  
**Version:** 0.2 (palette approved; design draft on hold) · **Updated:** 18 November 2026  
**File:** `docs/13-DESIGN.md`  
**Reference implementation:** [ThunderKhan/edviro-clone](https://github.com/ThunderKhan/edviro-clone), specifically [DESIGN.md](https://github.com/ThunderKhan/edviro-clone/blob/main/DESIGN.md), [visual-specification.md](https://github.com/ThunderKhan/edviro-clone/blob/main/docs/visual-specification.md), [motion-forensics.md](https://github.com/ThunderKhan/edviro-clone/blob/main/docs/motion-forensics.md), [interaction-state-machines.md](https://github.com/ThunderKhan/edviro-clone/blob/main/docs/interaction-state-machines.md), [Home.tsx](https://github.com/ThunderKhan/edviro-clone/blob/main/src/components/sites/edviro/Home.tsx), and [globals.css](https://github.com/ThunderKhan/edviro-clone/blob/main/src/app/globals.css).

**Design ownership:** Founder approved the ten-value Axiom brand palette in Section 3 for **both public pages and authenticated application** on 18 November 2026. The founder will still supply an additional design-system Markdown file; the **complete design document remains ON HOLD** pending reconciliation and explicit approval. This draft records structural and motion references from the Edviro clone.

## 1. Design objective and reuse boundary

Axiom's **landing page** should adopt the Edviro clone's **layout grammar, geometry, typography, spacing, navigation behaviors, interaction choreography, scroll-linked sections and responsive structure**, replacing all Edviro facilities content with original Axiom product content. The founder-provided Axiom palette in Section 3 is **approved for all pages**; current Edviro forest greens are **not** Axiom's palette.

Axiom is **not Edviro**: all headings, navigation destinations, screenshots, illustrations, logos, public-source badges, metrics, testimonial claims and dashboard content must be Axiom-specific. Adapt the reusable implementation patterns; do not mechanically ship Edviro brand identity. The clone's README says its app code is MIT-licensed and Geist font uses SIL OFL, but it also includes Edviro-origin logos, photographs and imagery on the basis of an earlier user permission statement for the clone. **That does not independently establish permission to redistribute those assets in the Axiom product.** Default to newly made/licensed Axiom visuals and keep third-party assets out until permitted use for this product is confirmed. Attribute borrowed licensed code as required.

The **authenticated research application** should share typography, spacing, buttons and refinement, but a sticky marketing-page scroll animation must **not** be forcibly applied to dense, task-oriented investigation/CRM workflows. Functional correctness and keyboard accessibility take priority.

## 2. Grounded layout geometry — from the Edviro clone

Source measurements are from the clone's documented desktop 1440 × 900 at DPR 1, mobile 390 × 844. These are **reference targets**, not yet visually validated for Axiom text lengths.

| Element | Reference measurement | Axiom instruction |
|---|---|---|
| Container | 1200px total including 40px gutters (about 1120px inner content) | Use consistent editorial wrap |
| Mobile gutters | 20px below roughly 780px | Maintain content breathing room |
| Header | 76px tall | Match nav height and scroll behavior |
| Large section spacing | 112px desktop, 72px mobile | Reuse primary section rhythm |
| Hero headline | Geist variable 500, 86px / 89.44px, tracking −3.44px (~−4%) | Large editorial headline; wrap to fit Axiom copy |
| Mobile hero headline | 46px | Use deliberate two-/three-line hierarchy |
| H2 | 48px / 49.92px, −1.92px tracking | Preserve size and contrast hierarchy |
| Product headings | ~32px / 1.12 | Inside platform showcase and app previews |
| Body | ~16px / 1.55 | Dense, legible informational text |
| Hero description | 19px / 1.5 | Above real application preview |
| Secondary labels | 14px, weight 500, normal case | Avoid generic all-caps label abuse |
| Standard CTA | 46px high capsule | Main landing action "Open Axiom" to /login |
| Header CTA | 40px high | Smaller action in nav |
| Closing CTA | 54px high | Prominent login entry from final section |
| Marketing dashboard radius | 18px | Real Axiom UI preview |
| Timeline / use-case card radius | 20px | Source-inspired component shape |
| Stacked platform panel radius | 28px | Scroll-driven hero feature stack |
| Integration panel radius | 32px | Bounded visual module |
| Borders | ~1px | Restrained outlines |
| Sticky platform cards | 76px + 14px per index (desktop reference) | Inspect actual overlap/viewport fit |
| Hero showcase gap | ~64px after buttons (desktop), 44px mobile | Preserve narrative transition |

Other reference spacing steps include 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 36, 40, 48, 52, 64, 72, 88, 96, 112 and 150 px, chosen contextually rather than blindly using a uniform eight-pixel grid.

### Typography and font assets

- **Geist Variable** is the reference typography family. Use a properly licensed source font package or an authorized local copy consistent with SIL OFL; keep attribution/license obligations.
- Reference weights: 400 for body, 500 for display, 600 for compact headings.
- Preserve measured line-height, tracking and responsive wrapping. Avoid replacing Geist with a random "modern AI" display typeface.
- Actual Axiom copy differs; test for overflow and odd single-word breaks, particularly 390px mobile.
- All numerical score/date/evidence presentation in the app should use tabular figures where needed for data readability.

## 3. Founder-approved color palette — landing page and full authenticated app

**Decision:** The founder supplied and selected the following exact Axiom palette on 18 November 2026. **These are the approved brand colors across the entire Axiom website:** public landing, login, workspace onboarding, Opportunity Radar, evidence graph/report, competitor intelligence, Counterfactual Lab, CRM, dialogs, exports when styled, and all shared controls. The old Edviro forest-green palette is **not** the product palette, and the previous draft's arbitrary colors are superseded.

### Canonical CSS variables (preserve names and hex values)

```css
:root {
  --bg: #FAF7F1;
  --band: #F1EAE2;
  --ink: #302B32;
  --text: #655B61;
  --muted: #766B70;
  --line: #302B3221;
  --green: #AC4E30;
  --deep: #271F28;
  --leaf: #F2A487;
  --tint: #F6E2D7;
}
```

**Important naming detail:** `--green` is a legacy variable name from the reference design. Its **value is terracotta #AC4E30**, not green; **do not change its value based on its name**.

### Semantic role mapping

| Usage | CSS variable | Intent |
|---|---|---|
| Landing/login/application main background | `--bg` | Warm off-white paper |
| Alternating sections, card surfaces, subtle bands | `--band` | Warm secondary canvas |
| Primary headers, app navigation, titles | `--ink` | Dark charcoal-plum |
| Paragraphs, field labels, descriptions | `--text` | Readable secondary ink |
| Meta-labels, source dates, quiet text | `--muted` | Muted ink, not disabled by itself |
| Separators, understated inputs and outlines | `--line` | Semi-transparent line; use on light surfaces |
| Main CTAs, primary actions, links and selection accents | `--green` | Terracotta brand accent |
| Dark narrative sections, alternate app panels | `--deep` | Deep charcoal-plum |
| Accent on dark backgrounds, highlight details | `--leaf` | Apricot/salmon accent |
| Warm highlight cards, selected states, soft badges | `--tint` | Pale blush-tinted surface |

**CTA behavior:** Capsule buttons use `--green` with `--bg` text, or `--deep` with `--bg` text. Secondary button: `--bg` or `--band` surface with `--ink` content and a visible border. Dark section: `--deep` surface with `--bg` text and `--leaf` highlights. Preserve the Edviro clone's 46px primary, 40px header and 54px final-CTA sizing, but **replace its colors with these variables everywhere**.

**Application components:** Apply the exact same CSS tokens across all authenticated layouts, CRM tables, source chips, citations, graph nodes/edges and scenario comparison controls. Distinguish `Pursue`, `Research further`, `Skip`, `Insufficient evidence`, verified, inferred, and hypothetical with **explicit text, icons, patterns and borders**, not arbitrary green/yellow/red colors. Additional functional state colors require documented accessible derivatives or separate approval; do not overwrite these ten brand variables. Graph/source overlays must remain legible on `--bg`, `--band`, `--tint`, and `--deep`.

### Preliminary contrast check (not a full accessibility audit)

Computed WCAG contrast ratios for solid background/text pairs:
- `--ink` on `--bg`: **12.94:1**
- `--text` on `--bg`: **6.09:1**
- `--muted` on `--bg`: **4.78:1**
- `--green` on `--bg`: **5.05:1**
- `--bg` text on `--green`: **5.05:1**
- `--bg` on `--deep`: **14.96:1**
- `--leaf` on `--deep`: **7.95:1**
- **Caution:** `--green` on `--tint` is only **4.32:1**, below the 4.5:1 normal-text threshold; avoid this pairing for normal text or use `--ink`. Verify actual component states, semi-transparent borders, disabled text, hover, focus, and graph edges during visual QA.

### Approval boundary

**Palette is founder-approved.** The complete **`13-DESIGN.md` remains ON HOLD** until the founder supplies their additional design-system Markdown file, any overriding rules are reconciled, asset rights and responsive examples are reviewed, and the founder approves the finished visual specification. This partial approval does **not** make the full design document approved.

## 4. Edviro homepage section choreography mapped to Axiom

The source homepage recipe is: **hero + dashboard → stats → workflow → dark sticky platform → use-case cards → dark editorial statement → results → integrations → split FAQ → dark CTA → footer**. Preserve its **structural pacing and section transitions**, but choose Axiom-specific content and functional honesty.

| Source segment | Axiom counterpart | Content and integrity requirements |
|---|---|---|
| Header / five grouped menus | Axiom product navigation | Link only real implemented anchors/routes; login via regular login screen; no dead menu items |
| Spacious hero headline + supporting copy + capsule CTAs | "Find demand. Prove your edge." and one clear entry action | Explain founder value; no claimed guaranteed customers |
| Wide multi-column dashboard visual | Real Axiom Opportunity Radar or Evidence preview | Use actual Axiom UI state or prominently tagged synthetic preview; do not copy Edviro maintenance metrics |
| Metrics/stats strip | Grounded product proof or methodology facts | No fabricated market counts, companies, accuracy rates or testimonials; omit/replace if no actual metrics exist |
| Five-step timeline | Define → Discover → Verify → Compare → Act | Source-inspired timeline with evidence-focussed illustrations and human review |
| Dark four-panel scroll/sticky platform | Radar → Competitor intelligence → Evidence graph → Scenario/CRM | Keep four panel stacking and progress linked tabs where accessible; use authentic Axiom depictions |
| Day/night industry hotspot cards | Axiom founder use cases | Six use-case illustrations or adapted interactions with original assets; clickable only when real destinations exist |
| Deep editorial statement band | Honest negative-decision message | Emphasize "not every signal is a customer" and abstention |
| Customer results/testimonials | Sourced example assessments / case walkthrough | Fixtures labeled; no fake customers or ROI metrics |
| Logo/integrations panel | Data connectors & MCP capabilities | Only mark connector "Live" after real integration; no Edviro vendor logo collage |
| Split FAQ | Axiom FAQs | Privacy, public sources, idea-stage caveats, manual outreach, limitations, costs |
| Dark closing CTA | Open Axiom | CTA → normal /login |
| Multi-column footer | Product, Method, Sources, GitHub, Legal | All links functional, attribution appropriate |

**Important:** Edviro's homepage "Results" category tabs are **visual spans**, not working filters, and source dashboard controls may be illustrative. Axiom must not transplant these as deceptively clickable research controls. If an Axiom element looks interactive, make it function or visibly label it as a preview. Axiom's real app filtering/CRM operations must be implemented independently and correctly.

## 5. Header, navigation and menu interaction

Clone evidence: five hover/focus grouped menus; 14px radius dropdown, approximate 160ms opacity + y(−6px → 0) entry; keyboard focus access and Escape dismissal for desktop; directional scroll header hides when scrolling down and returns on upward scroll, with translucent stuck surface and a ~350ms curve (cubic-bezier(.22,.8,.3,1)). At <780px, grouped mobile links appear in a two-column presentation with a Menu toggle. The source clone's mobile Escape behavior differs; **Axiom should improve keyboard accessibility** by allowing Escape to close any open mobile dialog/menu and restore focus, even if the visual reference differs.

Mapping of five groups is an information-architecture proposal; actual labels/content must be grounded in Axiom routes. Suggested labels: **Product, How it works, Research, Developers, About**; if a destination is not implemented, point to an actual landing section or omit it rather than link to an empty page. The main CTA and existing user sign-in both lead to /login.

## 6. Motion specification from the clone

Reference [motion forensics](https://github.com/ThunderKhan/edviro-clone/blob/main/docs/motion-forensics.md) identifies driver types. Copy **trigger behavior and timing semantics**, not arbitrary animated flourishes.

| Element | Trigger | Reference behavior |
|---|---|---|
| Hero headline | On initial page load | Two-line rise, second delayed ~80ms; ~700ms cubic-bezier(.2,.7,.2,1) |
| Hero copy and buttons | On load | Opacity entrance, about 200/300ms delays; ~700ms |
| Dashboard preview | On load | Rise ~36px, delay ~350ms, ~900ms same easing |
| Preview rows / details | On load | Rows rise ~10px staggered ~90ms from ~850ms; detail children stagger ~1.6–2.9s; chart draw ~900ms |
| General section reveal | First viewport entry | Opacity 0→1, translateY(22px→0), ~700ms; IntersectionObserver threshold .15 and bottom root margin −6%; **once**, not looping on reverse scroll |
| Workflow connector | On entry | Horizontal scaleX desktop / vertical scaleY mobile over ~1.8s cubic-bezier(.4,0,.2,1) |
| Counter-style metrics | On entry, only when meaningful | Count ~1.1s cubic ease-out from 0 to **real** target; no fictional metrics |
| Four-panel platform | Scroll position | Desktop sticky cards, card top offset increment 14px, scale reduction ~0.045 as subsequent card approaches, progressive darkening; reverse scroll restores |
| Platform tabs | Click and scroll | Scroll to corresponding card; active indication follows actual scroll, no autoplay |
| Use-case hotspots | Idle + hover | Subtle ~2.6s pulse; hover/focus pauses pulse, exposes label |
| Use-case image | Hover | Alternate layer crossfades ~700ms and scales ~1.04 over ~1.4s; **original Axiom assets** |
| Header | Scroll direction | Hides downward, returns upward; ~350ms ease |
| FAQ | User click | Semantic native details/summary; initially one item may be open; independent toggles |

Do **not** add Lenis/inertial scrolling, generic spring physics, blur-to-focus entrances, automatic tab rotation or continuous workflow autoplay. Clone evidence specifically did not observe those behaviors on the homepage. Reuse the clone's animation patterns selectively and honor `prefers-reduced-motion` (skip parallax/stack motion and show content immediately).

The separate autonomous 13-step work-order demo on an Edviro *secondary route* is not part of Axiom's landing-page motion system; do not carry over facilities-domain autoplay or fake actions. Motion for graph investigations is different: evidence interactions must be task-driven, keyboard-operable, and never delay critical research.

## 7. Responsive behavior from measured reference

- At **1040px and below**: workflow transitions to vertical layout, use-case grid becomes two columns, source illustrative dashboard sidebar is hidden. Axiom's live app must instead provide a functional compact navigation; never hide crucial actions/data.
- At **780px and below**: switch to mobile nav, hero headline ~46px, single-column content, cards lose desktop sticky pinning, integrations two-column logo/tile grid where appropriate, source dashboard details disappear in marketing *preview* only.
- Reference target **390 × 844**; also test 320/360/375/430/768/1024/1440 widths plus realistic long Axiom copy.
- Graph and analysis in the **authenticated app** have equivalent accessible report/list modes. Do not transfer landing-page stacking behavior into the CRM or graph.

## 8. Concrete implementation map to clone repository

| Reference code | Role | Reuse/adaptation |
|---|---|---|
| `src/app/globals.css` | Typography, geometry, motion primitives, media queries | Extract geometry/motion tokens; **replace all colors later** |
| `src/components/sites/edviro/Home.tsx` | Header, Hero, Dashboard, Stats, Workflow, Platform, Buildings, Results, Integrations, FAQ, CTA, Footer composition | Derive Axiom components and content; only keep interactions appropriate to function |
| `src/components/sites/edviro/data.ts` | Menu groups and section data | Replace with Axiom navigation, workflows, use cases and FAQ |
| `docs/visual-specification.md` | Measured desktop/mobile bounding boxes | Use as geometry QA baseline |
| `docs/motion-forensics.md` | Timing/driver observations | Establish animation regression checklist |
| `docs/interaction-state-machines.md` | Hover/focus/scroll/menu behavior | Map to actual Axiom interactions |
| `src/app/layout.tsx` | Geist preload and layout | Adapt font loading to Axiom, preserve license |
| `src/components/ui/button.tsx` | CTA component structure | Adapt capsules and states, check accessibility |
| `tests/` and visual comparison scripts | Regression methods | Reuse methodology and allowed code, not Edviro copyrighted visuals |

Implementation policy: **reference the clone's source but do not import Edviro components as runtime dependencies**; author independent Axiom components so product-specific UI and data types remain clean. Confirm license of reusable source code and separately confirm all assets.

## 9. Visual QA and acceptance gate

- Capture matched 1440×900 and 390×844 screenshots with fonts loaded and the same scroll positions.
- Compare Axiom geometry to the clone **as a reference**, with deliberate deviations for Axiom's original content and the approved palette. Do not set "pixel-perfect Edviro copy" as product identity requirement.
- Test header scroll down/up, mobile menu, dropdown focus/Escape, CTA navigation, initial hero entrance, first-entry reveal, four stacked card reversals, FAQ, reduced motion and footer.
- Confirm visible data is actual or explicitly labeled synthetic; "connected" integrations actually exist; no broken menu link.
- Confirm all buttons have correct semantic actions, source links and keyboard access. Page speed and 500-founder API capacity are **separate system quality properties**, not proof from marketing visuals.
- Do not copy Edviro images/logos/text or publish its clone disclaimer as Axiom's identity.

## 10. Approval hold and next inputs

**Approved component:** All ten founder-provided color values in Section 3 for landing, login and authenticated app. **Still not approved:** imagery/background assets, final Axiom logo, the founder's forthcoming design-system Markdown file, and resulting full visual specification. This document remains **ON HOLD** until:
1. Founder supplies their additional design-system Markdown file (palette already received).
2. Resolve conflicts between that design system and the Edviro-derived structural reference (founder decides).
3. Select permitted assets and confirm licensing.
4. Review sample Axiom desktop/mobile compositions and focus/reduced-motion behavior.
5. Explicitly approve `docs/13-DESIGN.md`.

**Authority boundary:** This draft does not supersede approved functional PRD/MVP/user flows, and it does not turn Edviro-specific visual demos into Axiom implementation requirements.
