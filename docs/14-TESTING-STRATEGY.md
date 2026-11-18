# Axiom — Testing Strategy and Quality Gates

**Status:** APPROVED — testing policy and gates; test execution not claimed · **Version:** 1.0 · **Approved:** 18 November 2026  
**Authority:** [MVP](03-MVP.md), [User Flows](04-USER-FLOWS.md), [TRD](06-TRD.md) and [Architecture](05-SYSTEM-ARCHITECTURE.md)

## 1. Definition of done

"Implemented" means a feature has real data or validated deterministic behavior, correct authorization, persistence if needed, honest errors, executable automated tests and proof on an environment matching deployment. A rendered component, fixture response, simulated network call, self-reported AI confidence or a green unit test alone does **not** prove a live integration.

Each feature tracked with: `requirement_id`, owner, branch/commit, status (Not started / In progress / Blocked / Verified / Owner-approved changed), test IDs, test run evidence, provider dependency, source/seeded labeling, and last verified timestamp. **Do not change an R0 commitment without explicit owner approval**.

## 2. Test layers

| Layer | Core tools | Required coverage |
|---|---|---|
| Unit | pytest, TS test runner if selected | Scoring/fit rules, dedupe, schema validation, scenario diff, graph reason codes |
| API/contract | pytest/FastAPI test client, OpenAPI validation | Auth, request/response schemas, typed errors, 2 required HTTP endpoints |
| Database | PostgreSQL test DB, migration runner | Clean/upgrade migrations, FK/workspace integrity, idempotency, frozen evidence |
| Integration | Real permitted source smoke, real competitor fetch | Actual returned URLs, correct timestamps, terms/quota, safe fetch failures |
| AI evaluation | Labeled fixed fixtures and actual model-call subset | Citation validity, abstain/negative cases, malformed JSON, prompt injection |
| MCP | Official or compatible external MCP client | Initialize, list, call P0 tools, permission denial and R0 tracking |
| Browser E2E | Playwright | Landing/login/app, adaptive onboarding, search, graph, simulation, CRM, exports |
| Accessibility | axe integration plus manual keyboard test | Graph report parity, form labels, focus/reduced-motion |
| Security | API negative tests + URL probes + secrets audit | IDOR, RLS/service bypass assumptions, SSRF, XSS, auth, MCP write boundary |
| Operations | Deployed smoke, restart/recovery, quota tests | Worker leases, status, degraded AI, HTTPS, DB migration, evaluator credentials |

CI fixture tests must be repeatable without internet and **separate** from live-network smoke. A test seeded with synthetic data isn't presented as a live API test.

## 3. Traceability matrix

| Test suite | PRD/MVP references | User flow | Pass condition |
|---|---|---|---|
| AUTH-01 | FR-01/03, MVP-01/02 | UF-01/02 | Normal login, workspace selection, expired session, cross-user rejection |
| ONB-01 | FR-02, MVP-03 | UF-03 | Idea/live branches, 10–15 adaptive questions, skip/back/resume, confirmed profile |
| DISC-01 | FR-04/05, MVP-04/05 | UF-04/05/06 | Live permitted source, normalization, 10 labeled examples, false-positive rejection |
| SRC-SEC-01 | FR-04/07, MVP-04/06 | UF-05/07 | DNS/redirect/local-network SSRF refusal, HTML sanitization |
| COMP-01 | FR-07, MVP-06 | UF-07 | Sourced real competitor claims, unknown price, blocked-site fallback, export |
| EVID-01 | FR-08, MVP-07 | UF-08 | Four verdicts, linked graph/report, supported source IDs and abstain |
| SIM-01 | FR-09, MVP-08 | UF-09 | Two named alternatives, multiple assumptions, same snapshot, save/reload |
| CRM-01 | FR-06, MVP-09/10 | UF-10/11 | Save stage/notes/follow-up, draft unsent, duplicate protection, persistence |
| HTTP-01 | FR-11, MVP-11 | UF-13 | Discovery and teardown callable via real HTTP; errors/auth/schema |
| MCP-01 | FR-11, MVP-12 | UF-14 | Five P0 tools; unauthorized write rejected, safe idempotency |
| OUTAGE-01 | FR-04–11, MVP-13 | UF-15 | Quota, timeout, malformed model, partial source and no fabricated success |
| UI-01 | FR-01/08, MVP-14 | UF-01/08/12 | Mobile/desktop, keyboard report, no critical console/accessibility issues |
| DEPLOY-01 | FR-01–12 | All critical | Production-like E2E, secrets, DB, worker, HTTPS, evaluator credentials |

## 4. Fixed evaluation fixtures (at least ten)

Create an explicit synthetic fixture file or test seeding command for:
1. Strong user problem, explicit solution request, real capability fit.
2. High solution intent with a critical missing feature.
3. General discussion with no buying intent.
4. Irrelevant keyword collision.
5. Contradictory requirements.
6. Insufficient evidence → abstain.
7. Competitor price unavailable → Unknown.
8. Competitor price hallucination attempt.
9. Prompt injection inside source HTML/comment.
10. Idea-stage capability incorrectly asserted as shipping.
11. Duplicate public post across runs.
12. Two hypothetical scenarios changing coverage, not revenue.

Each seed is labeled `seeded` in UI, database, API and exports. Actual live retrieved records must use real URLs/timestamps from source and be tested separately.

## 5. Security negative tests (release blockers)

- Anonymous or wrong-issuer JWT cannot access private workspace.
- User A changes workspace ID to B on read, mutation, export, research job and MCP → denial.
- Authenticated workspace A cannot attach competitor/source from workspace B through foreign keys.
- Privileged backend paths enforce workspace policy even if Supabase service role bypasses RLS.
- Read-only MCP client cannot call save_lead; duplicate MCP write creates no duplicates.
- URL to 127.0.0.1, private IP, metadata endpoint, redirect to internal DNS, DNS rebinding or oversized body is rejected.
- Untrusted website prompt injection cannot exfiltrate secrets or create tool calls.
- Render malicious HTML safely; scan build/logs for evaluator/API credentials.
- No autonomous email-send operation exists; drafts never mark sent.

## 6. CI gates and developer commands

Exact commands follow repository root `engineering.md` and the chosen package managers. Typical commands (illustrative, not claims they exist yet):

```bash
# Web (once configured)
pnpm install --frozen-lockfile
pnpm --dir apps/web lint
pnpm --dir apps/web exec tsc --noEmit
pnpm --dir apps/web build

# Python (once configured)
python -m pytest tests/unit tests/api
python -m pytest tests/security
# migration tool upgrade / schema diff
# Playwright E2E against deployed-like services
```

CI stages: **PR fast** (build/type/lint/unit/API/fixtures) → **migration and security** → **integration** (real allowed services, controlled quotas) → **E2E** → **deployment smoke**. A test failure cannot be "waived" by an automated agent without explicit owner decision.

## 7. Release gate report template

| Gate | Required proof | Status at document creation |
|---|---|---|
| RG-01 Identity | Login, evaluator account, workspace isolation | Not verified |
| RG-02 Discovery | 2 genuine permitted families targeted; R0 3+ assessed | Not verified |
| RG-03 Competitors | Real sourced claim or explicit Unknown | Not verified |
| RG-04 Evidence | Four verdicts, graph/report same source | Not verified |
| RG-05 Scenarios | Two saved alternatives, multiple edits | Not verified |
| RG-06 CRM | Persist/reopen lead, note, followup, unsent draft | Not verified |
| RG-07 Integrations | 2 HTTP endpoints + five P0 MCP tools, auth/write denial | Not verified |
| RG-08 Experience | Full browser E2E + mobile/accessibility | Not verified |
| RG-09 Disclosure | README provider, source, quota and fixture notices | Not verified |
| RG-10 Deployment | HTTPS app/API, DB, worker and recovery | Not verified |

**Pass rule:** No P0 gate is accepted without a recorded passing test on the relevant code/deployment. Track expanded R0 tools/sources/scenarios independently; unmet R0 needs explicit scope-change review. Link evidence to commit, test run, date, environment and known limitations.

## 8. Checkpoints

19 Nov first real source and competitor extraction; 22 Nov end-to-end saved research and R0 status review; 24 Nov nonessential freeze; 25 Nov complete tests and evaluator rehearsal; 26 Nov final production smoke/submission. These are scheduled goals, not proof of completion.

## 9. 500-founder concurrency and load verification

The founder requests support for **500 concurrently active authenticated users**. This is a **target, not a claim of achieved capacity**. [18-SCALABILITY.md](18-SCALABILITY.md) holds the provisional workload design and pending SLA agreement.

- Use **k6/Locust (or equivalent)** with 500 distinct virtual user principals/workspaces and representative indexed data; do not confuse 500 idle sockets with 500 actively using the product.
- Run a 10-minute ramp, ≥15-minute steady-state mixed workload (~25 req/s target assumption), heavier ~50 req/s stress, ~60-minute soak, and bounded burst of queued research submissions; record actual achieved rate.
- Record p50/p95/p99 read/write/job-acceptance latencies, internal 5xx, explicit 429, queue age, worker completion, CPU, memory, database pool saturation and external API quotas.
- Require **zero cross-workspace data leaks and duplicate mutation effects** under concurrent retries, worker restart and authorization probes.
- Use stubbed third-party providers for **high-volume load generation**, clearly separate from small lawful real-source integration probes. Do not flood HN, RSS publishers or LLM free APIs.
- 500-user capacity is **not verified** until a production-like/deployed test passes and its exact environment is recorded. If free hosting cannot sustain the objective, report a blocker and seek an explicit owner scope/release decision, not a fictitious green test.
