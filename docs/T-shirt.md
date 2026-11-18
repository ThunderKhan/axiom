# Axiom — T-Shirt Sizing and Delivery Risk

**Status:** DRAFT — estimation worksheet · **Date:** 18 November 2026  
**Purpose:** Rough effort/uncertainty sizing, not fixed promises or an approved reduction of MVP scope.  
**References:** [Approved MVP](03-MVP.md), [Roadmap](16-IMPLEMENTATION-ROADMAP.md), [Decisions](DECISIONS.md)

## 1. Size vocabulary

| Size | Illustrative engineering effort (one experienced contributor) | Typical complexity |
|---|---|---|
| XS | Under 2 focused hours | Small copy, token/validator update |
| S | 2–4 hours | Scoped UI form or one thin endpoint with tests |
| M | 0.5–1 day | Single cohesive feature with persistence/tests |
| L | 1–2 days | Cross-layer flow, external dependency or auth |
| XL | 2–4+ days | Multi-stage intelligence, integrated high-risk feature |
| XXL | Several days to multiple weeks | Multi-provider or broad platform-level work |

These sizes are **subjective relative estimates** and explicitly **not delivery guarantees**. Integration, unfamiliar APIs, platform restrictions, debugging and testing can dramatically expand them. Uncertainty grows with external systems and parallel cross-layer changes.

## 2. Initial feature sizing

| Work package | Estimated size | Confidence | Risk driver |
|---|---|---|---|
| Repo foundation, CI, environment baseline | M–L | Medium | Existing files/quality rules unknown |
| Auth + multi-workspace isolation | L–XL | Medium-low | Provider setup, RLS and IDOR |
| Adaptive onboarding, profile versions | L–XL | Medium | AI fallback and resume |
| 2 verified live source families | XL–XXL | Low | Access semantics, quality and policies |
| Third+ R0 source family | L–XXL each | Low | External access and quota |
| Hybrid ranking/false-positive logic | L–XL | Medium-low | Evaluation labels and AI |
| Sourced competitor extraction | XL | Low | Safe URL fetch, JS/blocked sites, citation proof |
| Evidence node/edge model, graph/report | XL | Medium-low | Model and UI consistency |
| Advanced saved scenario engine (R0) | XL–XXL | Low | Frozen snapshots, multi-assumption reasoning |
| Persistent CRM + follow-ups | L | Medium | Auth, transactions |
| AI-assisted outreach drafts | M–L | Low | Free model provider |
| Two HTTP endpoints and schemas | M–L | Medium | Depends on domain operations |
| Five P0 MCP tools | L–XL | Medium-low | Client auth and deployment |
| Expanded R0 MCP tools | XL | Low | Approvals, additional use cases |
| Deploy API+worker+DB for ₹0 | XL–XXL | Very low | Hosting durability/quotas |
| Full E2E, adversarial security and release | XL | Medium-low | Integration stabilization |

## 3. Critical insight

Adding these estimates sequentially would exceed the remaining pre-November-26 working window. This is **not permission to remove the founder's R0 priorities**. It is evidence that implementation must use integrated vertical slices, reuse domain contracts, parallelize only independent work, and verify highest-risk external dependencies immediately.

**First feasibility spikes:** 1) real permitted source result; 2) competitor sourced claim; 3) managed DB/login; 4) worker that runs after restart; 5) actual free model call; 6) external MCP authentication handshake. If any fails, record blocker and seek an explicit owner cutline decision.

## 4. Tracking template

| Item | Estimate | Owner | Started | Verified | Blocker / evidence |
|---|---|---|---|---|---|
| Example: live source adapter | XL | TBD | No | No | Awaiting permitted live integration |
| Example: worker | XL | TBD | No | No | Awaiting actual host probe |

"Verified" requires real tests linked to commit/environment, not code authored or screen rendered. Update sizing as evidence arrives; preserve historical estimates to calibrate planning.

## 5. Contingency rules

- 19 Nov: if source/worker feasibility fails, escalate immediately before adding UI polish.
- 22 Nov: evaluate P0 journey and every R0 source/scenario/CRM/MCP goal; owner decides changes.
- 24 Nov: freeze nonessential changes, fix regressions/authorization/availability before expansion.
- 25–26 Nov: prioritize tested deployed user journey, independent evaluator login, honest documentation and submission.

**Open:** Team size, actual time availability, existing implementation/code, provider quotas, and deployment readiness were not measured when this worksheet was created. Re-estimate after first working vertical slice.
