# Axiom — AI and Evidence Engine

**Status:** DRAFT — in review · **Version:** 0.1 · **Date:** 18 November 2026  
**Source:** [PRD](02-PRD.md), [MVP](03-MVP.md), [Architecture](05-SYSTEM-ARCHITECTURE.md), [TRD](06-TRD.md)

## 1. Objective and epistemic rules

Connect observed customer needs, founder-confirmed/proposed capabilities and source-backed competitor claims to an actionable verdict. **Success includes telling a founder to Skip or Research further**. This is not a sales predictor.

Idea-stage capabilities are **hypothetical**, even when the user confidently describes them. Launched-product capabilities can be founder-confirmed or independently sourced, with provenance distinguished. Company websites substantiate that *a company claims X*, not that X objectively works. Model inference and speculative advice must be labeled and must never be presented as cited external fact.

## 2. Pipeline

§§§mermaid
flowchart LR
  P[Confirmed profile version] --> Q[Discovery query]
  Q --> S[Lawful source adapters]
  S --> N[Normalize and dedupe]
  N --> D[Deterministic candidate filter]
  D --> L[Optional structured AI extraction]
  L --> V[Schema and citation validator]
  V --> R[Intent relevance fit evidence scoring]
  R --> G[Typed evidence graph and contradictions]
  G --> O[Pursue Research Skip Abstain]
  O --> U[Graph report CRM scenarios]
§§§

1. **Input contract:** selected workspace, confirmed profile version, permitted source/query and bounded record count.
2. **Fetch:** only allowed public source/adapters; URL policy, timestamps, excerpt and live/cached/seeded origin.
3. **Normalize:** canonical provider/record ID and URL; simple text cleanup; hashes and duplicate grouping; no invented excerpts.
4. **Rules:** find candidate problem/intent and obvious mismatches using transparent deterministic signals.
5. **AI, if actually available:** infer structured needs, intent, capability matches and exploratory suggestions; validate Pydantic/JSON schema and exact source IDs/locators.
6. **Validation:** external claims lacking matching source record/credible locator become unverified or rejected. Source text is untrusted, never tool commands.
7. **Assessment:** typed graph, hard-rule verdict, explanations and uncertainty. Save snapshot and immutable profile version.
8. **Presentation:** the graph, accessible report and export use the same stored assessment object and evidence IDs.

## 3. Structured data contracts

§SourceRecord§ fields: §id§, §family§, §canonical_url§, §origin§ live/cached/seeded/user_provided, §excerpt§, §published_at§ nullable, §retrieved_at§, §content_hash§.  
§CustomerNeed§: §id§, §text§, §source_record_id§, §locator§, §confidence_label§, §claim_type§.  
§CompetitorClaim§: §competitor_id§, §claim_type§ feature/pricing/positioning, §text§, §source_record_id§ nullable, §locator§ nullable, §provenance§ sourced/unverified, §retrieved_at§.  
§EvidenceNode§: §id§, §type§ source/need/capability/competitor_claim/gap/unknown, §label§, §origin§, §source_ref§ nullable.  
§EvidenceEdge§: §id§, §from§, §to§, §relation§ supports/contradicts/requires/satisfies/does_not_satisfy/uncertain, §reason_code§, §source_ref§ nullable.  
§Assessment§: §profile_version_id§, §evidence_snapshot_id§, §verdict§, §reason_codes§, §nodes§, §edges§, §unknowns§, §model_metadata§.

## 4. Scoring and verdict algorithm

Represent separate **nullable** 0–1 dimensions: problem relevance (R), solution-seeking intent (I), capability fit (F), evidence quality (E), freshness (T). Do not equate buying intent to fit. Explain rule/model contribution and unknown data.

**Provisional ordering formula only:** §0.27R + 0.23I + 0.32F + 0.18E§ with bounded, visible freshness tie-break. These weights are **not calibrated or approved statistical probabilities**. Missing F/E does not become 1; instead communicate uncertainty and avoid a high-confidence decision.

**Hard constraints:**
- If no trustworthy needs/evidence → **Insufficient evidence**.
- If a critical confirmed requirement is unsupported → **Skip** or **Research further**, regardless of high intent.
- If evidence contradicts or a material capability is uncertain → **Research further**.
- If relevant requirements are supported, contradictions bounded, and evidence sufficient → **Pursue** *as an investigation priority*, not purchase certainty.
- Unsupported idea-stage claims are hypothetical, not verified fit.
- Never claim estimated sales, growth, market share or conversion lift from the above score.

Exact "critical requirement" definition/thresholds to be tested against labeled cases and documented.

## 5. Competitor research procedure

- User chooses known competitors and confirms auto-suggested candidates; no unconfirmed candidate is treated as direct competition.
- Safe network fetch obtains bounded, permitted HTML/text, page URL and retrieval timestamp.
- Extract pricing/features/positioning phrases with exact excerpt or locator; source is retained.
- Model may propose structured claims, but validator ensures each claimed citation matches a real fetched source. Failed verification is §unverified§ or removed.
- Absent price = **Unknown**; contradictions kept with both sources and dates.
- Generate sourced comparison + limits + suggested validation steps; never invent a competitor's pricing or features.

## 6. Counterfactual Lab (R0 advanced)

**Baseline** = immutable assessment + profile version + frozen evidence snapshot. Founder creates **at least two named alternatives**, each with multiple feature, qualitative pricing and positioning edits.

1. Copy capability set into hypothetical scenario context; do not mutate confirmed profile.
2. Apply typed assumption patches, keeping trace of every change.
3. Recompute covered/missing/uncertain **existing** requirements against identical evidence.
4. Show baseline versus variants, changed coverage, reason for each difference, contradictory evidence and unknowns.
5. Optionally add clearly labeled AI exploratory tradeoffs and next validation experiments.
6. Save scenario version/results; reopen reproduces comparison. Re-evaluating with newer research requires an explicit rebase/version.

No future revenue/causal change prediction without rigorous independent data.

## 7. Model/provider handling

Define §ModelAdapter§ by task, prompt-template version, bounded input excerpts, structured output schema, per-call timeout, quota, provider/model identifier and trace ID. Inputs must exclude secrets, private evaluator credentials and unnecessary personal data.

- Verify a legitimate **free** provider and quota with actual call; no model is selected/connected merely by being named in docs.
- Pydantic/JSON validation required; limited retry/repair; enforce bounded tokens/concurrency.
- Cache by profile version + source snapshot digest + schema/prompt version where allowed.
- If provider unavailable, use deterministic rule fallback **labeled no model used/degraded**; not pretend model-assisted analysis occurred.
- Failures show real source/model error states. Model never autonomously sends messages or bypasses workspace policy.
- Retrieved texts wrapped as untrusted data. Prompt injection should not modify system/tool instructions; server validates outputs independently.

## 8. Evaluation and release gates

Minimum labeled suite (10+): clear high-fit intent; high-intent poor fit; generic chatter; keyword false positive; contradictory claim; missing evidence; missing competitor price; fabricated-source attempt; prompt-injection page; idea-stage proposed capability; duplicate source; scenario that improves requirement coverage without implying sales.

Measure relevant precision@k, intent/fit confusion, false-positive rejection, citation coverage/validity, abstention correctness, schema-validation rate, model fallback, and scenario replay. **Do not invent achieved accuracy figures.**

Ship gates: 100% of material competitor facts source-cited or explicitly marked unverified; fixtures/hypotheses labeled; no knowingly fabricated source URL; negative verdict and abstention demonstrated; seeded vs actual live integrations clearly separated.

**Open:** chosen LLM/provider, quota and licenses, evaluated thresholds, optional embeddings, exact claim entailment validator, source retention and how to handle stale external content.
