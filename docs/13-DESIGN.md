# Axiom — Design Reference and Landing Experience

**Status:** ON HOLD — design reference draft; **not approved**  
**Version:** 0.1 · **Prepared:** 18 November 2026  
**File:** \`docs/13-DESIGN.md\`  
**Reference implementation:** [ThunderKhan/edviro-clone](https://github.com/ThunderKhan/edviro-clone), specifically [DESIGN.md](https://github.com/ThunderKhan/edviro-clone/blob/main/DESIGN.md), [visual-specification.md](https://github.com/ThunderKhan/edviro-clone/blob/main/docs/visual-specification.md), [motion-forensics.md](https://github.com/ThunderKhan/edviro-clone/blob/main/docs/motion-forensics.md), [interaction-state-machines.md](https://github.com/ThunderKhan/edviro-clone/blob/main/docs/interaction-state-machines.md), [Home.tsx](https://github.com/ThunderKhan/edviro-clone/blob/main/src/components/sites/edviro/Home.tsx), and [globals.css](https://github.com/ThunderKhan/edviro-clone/blob/main/src/app/globals.css).

**Design ownership:** Founder will supply an additional, authoritative design-system Markdown file and final colors. **Do not lock brand colors or mark this document approved until that material is supplied, reconciled, and explicitly approved.** This draft records measurable structural and motion references already available in the Edviro clone.

## 1. Design objective and reuse boundary

Axiom's **landing page** should adopt the Edviro clone's **layout grammar, geometry, typography, spacing, navigation behaviors, interaction choreography, scroll-linked sections and responsive structure**, replacing all Edviro facilities content with original Axiom product content. The final color palette will be founder-provided; current Edviro greens are **not** Axiom's approved palette.

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

## 3. Color system — intentionally unselected

**Axiom's colors are awaiting founder input.** The clone's paper/forest/dark palette documents the original visual behavior, but its hex values **must not be copied as the final Axiom color contract**.

Define semantic tokens now, set values only after the founder supplies them:

\`\`\`css
:root {
  --color-canvas: unset;        /* founder palette pending */
  --color-surface: unset;
  --color-ink: unset;
  --color-body: unset;
  --color-muted: unset;
  --color-primary: unset;
  --color-primary-contrast: unset;
  --color-dark-band: unset;
  --color-accent: unset;
  --color-border: unset;
  --color-error: unset;
  --color-warning: unset;
  --color-source: unset;
  --color-hypothesis: unset;
  --color-focus: unset;
}
\`\`\`

These placeholders describe required roles, **not executable production CSS to merge as-is**. Verify contrast ratios on selected colors, including source/citation labels and graph/decision states; do not convey evidence reliability by color alone.

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

Do **not** add Lenis/inertial scrolling, generic spring physics, blur-to-focus entrances, automatic tab rotation or continuous workflow autoplay. Clone evidence specifically did not observe those behaviors on the homepage. Reuse the clone's animation patterns selectively and honor \`prefers-reduced-motion\` (skip parallax/stack motion and show content immediately).

The separate autonomous 13-step work-order demo on an Edviro *secondary route* is not part of Axiom's landing-page motion system; do not carry over facilities-domain autoplay or fake actions. Motion for graph investigations is different: evidence interactions must be task-driven, keyboard-operable, and never delay critical research.

## 7. Responsive behavior from measured reference

- At **1040px and below**: workflow transitions to vertical layout, use-case grid becomes two columns, source illustrative dashboard sidebar is hidden. Axiom's live app must instead provide a functional compact navigation; never hide crucial actions/data.
- At **780px and below**: switch to mobile nav, hero headline ~46px, single-column content, cards lose desktop sticky pinning, integrations two-column logo/tile grid where appropriate, source dashboard details disappear in marketing *preview* only.
- Reference target **390 × 844**; also test 320/360/375/430/768/1024/1440 widths plus realistic long Axiom copy.
- Graph and analysis in the **authenticated app** have equivalent accessible report/list modes. Do not transfer landing-page stacking behavior into the CRM or graph.

## 8. Concrete implementation map to clone repository

| Reference code | Role | Reuse/adaptation |
|---|---|---|
| \`src/app/globals.css\` | Typography, geometry, motion primitives, media queries | Extract geometry/motion tokens; **replace all colors later** |
| \`src/components/sites/edviro/Home.tsx\` | Header, Hero, Dashboard, Stats, Workflow, Platform, Buildings, Results, Integrations, FAQ, CTA, Footer composition | Derive Axiom components and content; only keep interactions appropriate to function |
| \`src/components/sites/edviro/data.ts\` | Menu groups and section data | Replace with Axiom navigation, workflows, use cases and FAQ |
| \`docs/visual-specification.md\` | Measured desktop/mobile bounding boxes | Use as geometry QA baseline |
| \`docs/motion-forensics.md\` | Timing/driver observations | Establish animation regression checklist |
| \`docs/interaction-state-machines.md\` | Hover/focus/scroll/menu behavior | Map to actual Axiom interactions |
| \`src/app/layout.tsx\` | Geist preload and layout | Adapt font loading to Axiom, preserve license |
| \`src/components/ui/button.tsx\` | CTA component structure | Adapt capsules and states, check accessibility |
| \`tests/\` and visual comparison scripts | Regression methods | Reuse methodology and allowed code, not Edviro copyrighted visuals |

Implementation policy: **reference the clone's source but do not import Edviro components as runtime dependencies**; author independent Axiom components so product-specific UI and data types remain clean. Confirm license of reusable source code and separately confirm all assets.

## 9. Visual QA and acceptance gate

- Capture matched 1440×900 and 390×844 screenshots with fonts loaded and the same scroll positions.
- Compare Axiom geometry to the clone **as a reference**, with deliberate deviations for Axiom's original content and palette. Do not set "pixel-perfect Edviro copy" as product identity requirement.
- Test header scroll down/up, mobile menu, dropdown focus/Escape, CTA navigation, initial hero entrance, first-entry reveal, four stacked card reversals, FAQ, reduced motion and footer.
- Confirm visible data is actual or explicitly labeled synthetic; "connected" integrations actually exist; no broken menu link.
- Confirm all buttons have correct semantic actions, source links and keyboard access. Page speed and 500-founder API capacity are **separate system quality properties**, not proof from marketing visuals.
- Do not copy Edviro images/logos/text or publish its clone disclaimer as Axiom's identity.

## 10. Approval hold and next inputs

**Not approved:** palette values, any imagery/background asset, final Axiom logo, any user-supplied design-system file not yet provided, and resulting final visual specifications. This document remains **ON HOLD** until:
1. Founder provides final palette and their own design-system Markdown file.
2. Resolve conflicts between that design system and the Edviro-derived structural reference (founder decides).
3. Select permitted assets and confirm licensing.
4. Review sample Axiom desktop/mobile compositions and focus/reduced-motion behavior.
5. Explicitly approve \`docs/13-DESIGN.md\`.

**Authority boundary:** This draft does not supersede approved functional PRD/MVP/user flows, and it does not turn Edviro-specific visual demos into Axiom implementation requirements.
