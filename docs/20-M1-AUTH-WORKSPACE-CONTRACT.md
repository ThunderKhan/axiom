# M1 Authentication and Workspace Engineering Contract

**Status:** OWNER-APPROVED ARCHITECTURE; documentation PR pending review; implementation **NOT VERIFIED**  
**Owner approval:** 19 November 2026, separate consolidated approval of all 25 A1–I3 choices  
**Issue:** [#21 — M1 contract documentation](https://github.com/ThunderKhan/axiom/issues/21) (standalone, outside Milestone 1)  
**Independent M1 signoff gate:** [#14](https://github.com/ThunderKhan/axiom/issues/14) (**not completed by this document**)  
**Approved stack:** Supabase Auth + Supabase PostgreSQL + FastAPI-only domain access + SQLAlchemy 2.x/Alembic, per [ADR-002](decisions/002-authentication-database-and-api-boundary.md)  
**Base reviewed:** `main` at `3fcd2fe6405d8078e436a0c9272c4809c006c814`

> **Decision contract, not runtime evidence.** This documentation does not create or verify authentication, RLS, tables, migrations, evaluator users, CI integration, or deployment. No user-facing deletion, privileged account, bypass, external provider purchase or new product feature is authorized by this PR.

## 1. Authority and scope

Governing sources: [AGENTS.md](../AGENTS.md) and [ENGINEERING.md](../ENGINEERING.md) v1.1; [PRD](02-PRD.md) **FR-01, FR-03**; [MVP](03-MVP.md) **MVP-01, MVP-02**; [User Flows](04-USER-FLOWS.md) **UF-01, UF-02**; [Architecture](05-SYSTEM-ARCHITECTURE.md) identity/authorization boundary; [TRD](06-TRD.md) **TRD-FE-01/03, TRD-BE-03, TRD-DB-01/02/03, TRD-SEC-01/02**; [UI/UX](12-UI-UX-SPEC.md); [Testing](14-TESTING-STRATEGY.md) **AUTH-01**; [Roadmap](16-IMPLEMENTATION-ROADMAP.md) **WP-02**; [Security](17-SECURITY.md); [Deployment Topology](19-DOCKER-AND-DEPLOYMENT-TOPOLOGY.md).

This is **only** the Milestone 1 identity/session/application-user/workspace/authorization/API/browser contract for issues [#15](https://github.com/ThunderKhan/axiom/issues/15)–[#20](https://github.com/ThunderKhan/axiom/issues/20). Broader [database design](07-DATABASE-DESIGN.md), [API contracts](08-API-CONTRACTS.md), and [deployment runbook](15-DEPLOYMENT-RUNBOOK.md) remain **DRAFT** outside this M1 slice. An M1-specific conflict is reconciled here without silently approving or rewriting other functionality.

**Not in scope:** product profile/onboarding implementation, research/CRM and other business tables, teams/RBAC/organization sharing, workspace owner transfer, public account/workspace DELETE endpoints, external MCP OAuth authorization server, worker business features, source/AI providers, infrastructure/purchases/provisioning, migrations or application code in this documentation PR. Nothing in this contract replaces #14's separate approval gate or permits merging a PR without the owner's subsequent authorization.

## 2. Binding decisions and provenance

All 25 owner selections were **Option A** and received a **separate explicit consolidated approval** after the interactive consultation. Each linked Issue #21 decision record contains considered alternatives, rationale, risk, requirement trace and acknowledged uncertainty.

| ID | Binding direction | Original record |
|---|---|---|
| A1 | `app_users.id` is the verified Supabase Auth `sub` UUID | [Batch A](https://github.com/ThunderKhan/axiom/issues/21#issuecomment-7004406215) |
| A2 | Explicit verified, idempotent first-login FastAPI bootstrap; `GET /me` read-only | Batch A |
| A3 | Application-controlled `active/suspended/deprovisioned`; deny non-active protected access | [Batch B](https://github.com/ThunderKhan/axiom/issues/21#issuecomment-7004464446) |
| A4 | Individually pre-provisioned normal low-privilege evaluator users, private credentials | Batch B |
| C1 | Supabase SSR + PKCE shared cookies; browser bearer user JWT to FastAPI, no HttpOnly claim | [Batch C](https://github.com/ThunderKhan/axiom/issues/21#issuecomment-7004907231) |
| C2 | Supabase refresh/sign-out + server app-state validation; JWT expiry/revocation caveat | Batch C |
| D1 | Local verified asymmetric JWT + project-bound JWKS and strict claims | [Batch D](https://github.com/ThunderKhan/axiom/issues/21#issuecomment-7004974656) |
| D2 | Bounded JWKS key cache, controlled unfamiliar-key refresh, operator invalidation | Batch D |
| D3 | During provider outage verify only with still-trusted cached keys; fail closed otherwise | Batch D |
| E1 | Application-owned identity table without Auth deletion cascade | [Batch E](https://github.com/ThunderKhan/axiom/issues/21#issuecomment-7005157432) |
| E2 | One owner per workspace; one user can own multiple independent workspaces | Batch E |
| E3 | No user-facing destructive workspace/account delete in M1 | Batch E |
| F1 | Server owner checks + workspace-scoped/composite FKs + RLS `USING/WITH CHECK` | [Batch F](https://github.com/ThunderKhan/axiom/issues/21#issuecomment-7005263401) |
| F2 | Separate least-privilege runtime and privileged migration roles | Batch F |
| F3 | Transaction-local verified identity, safe across SQLAlchemy pool reuse | Batch F |
| G1 | Separate bootstrap, safe `GET /me` and minimal workspace REST/DTO contract | [Batch G](https://github.com/ThunderKhan/axiom/issues/21#issuecomment-7005384188) |
| G2 | Indistinguishable `404 NOT_FOUND` for foreign/nonexistent workspaces | Batch G |
| G3 | Durable owner-scoped idempotency on creates + version-precondition PATCH | Batch G |
| H1 | Protected Next.js rendering, validated internal return paths, independent API auth | [Batch H](https://github.com/ThunderKhan/axiom/issues/21#issuecomment-7005499328) |
| H2 | Remembered workspace is user-namespaced preference, revalidated through FastAPI | Batch H |
| H3 | Partition private caches and discard obsolete in-flight responses | Batch H |
| H4 | Local, database and real nonproduction Supabase/Playwright M1 validation gates | Batch H |
| I1 | Exact M1 API/status/config package; existing `AXIOM_` convention | [Batch I](https://github.com/ThunderKhan/axiom/issues/21#issuecomment-7005678733) |
| I2 | Committed idempotency outcomes retained **at least 24 hours** | Batch I |
| I3 | Maximum **300-second Axiom-local JWKS cache age** (not global revocation SLA) | Batch I |

See the [architecture closeout audit](https://github.com/ThunderKhan/axiom/issues/21#issuecomment-7005578787) for legacy-draft discrepancies and explicitly unverified dependencies. These 25 choices govern M1 only.

## 3. Trust boundaries and invariants

1. Supabase Auth issues normal web access tokens; no invented custom password/session issuer, public guest sandbox or evaluator-only privilege bypass.
2. The browser's Supabase SDK may authenticate only. **All domain-data reads/writes go through FastAPI**, including workspaces and later product, research/CRM, worker and MCP services. Never enable browser-to-Supabase domain-table access.
3. Every private FastAPI request independently verifies the Supabase **user** JWT, checks `app_users.status=active`, and authorizes each requested workspace/object against server-owned ownership. A URL parameter, browser selection, cookie presence, user-supplied ID, or hidden UI button is **never authority**.
4. Tenant protection is layered: explicit FastAPI authorization, PostgreSQL workspace-scoped constraints/composite FKs, and verified RLS for the actual least-privileged runtime role. Never assume a table-owner/`service_role`/`BYPASSRLS` connection is protected by RLS.
5. Invalid JWTs, absent identity, unknown/stale JWKS key, disabled app user, invalid transaction context, foreign workspace and failed required DB checks must **fail closed**; never return a success-shaped fallback.
6. A user must be able to create **at least two** independent workspaces; two is a proof floor, not a maximum. Workspaces have one immutable owner in M1 and no sharing/membership table.
7. Secrets, passwords, tokens and private user data must not appear in source, public builds, PR body, fixture, logs or examples. All tests are tied to a real execution revision/environment; mocked acceptance does not prove an external integration.

## 4. Identity mapping, explicit bootstrap and account lifecycle

### 4.1 Canonical identity

After cryptographic verification, the Supabase Auth access-token subject `sub` (validated UUID) is **exactly** `app_users.id`. There is no alternate internal user UUID and no public ability to select someone else's subject. Do not use mutable email for principal/ownership mapping.

The app-user table is application-owned, with **no automatic foreign-key cascade from managed `auth.users`**. This deliberately means an out-of-band provider deletion may leave an orphaned app record, handled by monitoring and reconciliation rather than silent business-data erasure.

### 4.2 Transactional first-login bootstrap (A2)

1. Frontend obtains a legitimate Supabase Auth user JWT via the reviewed SSR/PKCE flow.
2. It calls **`POST /api/v1/me/bootstrap`** with that token; no client-provided user ID or workspace ID.
3. FastAPI verifies signature, configured issuer/audience, expiry, ordinary user role and UUID `sub` **before** any write.
4. In a properly identity-scoped PostgreSQL transaction, atomically insert the app row with status `active` **if absent**. A simultaneous or repeated bootstrap converges on the same row and must not reset timestamps/status. Use DB uniqueness and insert-on-conflict semantics; no unsafe check-then-insert.
5. A previously `suspended`/`deprovisioned` account gets **403 ACCOUNT_DISABLED**; bootstrap must never reactivate it. A newly created row returns **201**; an already active row returns **200**.
6. **`GET /api/v1/me` remains strictly read-only.** If JWT is valid but provisioning has not occurred, return **409 PROVISIONING_REQUIRED**, not a hidden create. Normal domain calls require an existing active user.

**Necessary bootstrap exception:** first login cannot already have an application user. The bootstrap route therefore requires a narrowly scoped authenticated own-row insert path, not the normal “preexisting active app account” prerequisite. It still requires cryptographically verified identity, strict status checks for existing records, least-privileged DB permissions and tested RLS.

### 4.3 Suspension and deletion

Application state `active` allows independently authorized operations; `suspended` and `deprovisioned` deny all protected domain access even for a still-signed, unexpired JWT. Only a separately controlled operator process changes that state. Planned offboarding marks the app user non-active **before** provider removal; it does not delete owned workspace data.

**Provider limitation:** Supabase Auth user deletion, ban, sign-out or refresh-token revocation does **not** necessarily invalidate all already-issued access JWTs immediately. Out-of-band Auth changes do not immediately reach app-user state without synchronization. Define/verify a reconciliation procedure, measurable detection bound and emergency operator-disable action before a claim of prompt provider-side revocation; do not invent an SLA or silently activate a deprovisioned row.

### 4.4 Evaluator accounts

Admin-provision **individual ordinary** Supabase Auth accounts with strong initial credentials delivered privately, no shared judge password, elevated API role, special judge page or public configuration. Optional example workspaces must be isolated and visibly labeled `DEMO / SYNTHETIC`. Test genuine ordinary login/access, then rotate/revoke/offboard after evaluation under a reviewed operator procedure. Provider account creation, SMTP and secret delivery are **not performed by this document**.

## 5. Session transport, browser security and routing

- Use supported `@supabase/ssr` with **PKCE**. Supabase manages token issuance/refresh/sign-out; Next.js browser/server clients coordinate session cookies and supported callback/refresh behavior. Do not introduce a custom BFF session registry or persistent browser-localStorage token strategy.
- In the standard Supabase SSR model, shared cookies containing auth state are **JavaScript-accessible, not guaranteed HttpOnly**. Protect with production HTTPS, appropriate `Secure`/`SameSite`/domain/path settings, CSP, output encoding/XSS defenses, and no session secrets in URLs/logs. Review CSRF on any automatically cookie-authenticated Next.js mutation/callback endpoints; FastAPI's normal domain calls require explicit `Authorization: Bearer` user access JWT and exact CORS origins.
- A Next.js protected route must verify current Supabase session claims through a supported server-side verification method; **mere cookie presence or unverified decode is insufficient**. FastAPI separately validates its own bearer and app/workspace permissions every time; successful Next.js navigation never grants database rights.
- Anonymous users reach ordinary `/login`. A post-login return target must be a validated **relative, same-origin, allowed internal path**, never an external/protocol-relative/encoded open redirect; the destination's workspace must be reauthorized. Handle refresh, deep links and Next.js prefetch/session timing safely.
- On logout, expiry, account change or refresh failure, clear private visible state, cached requests and workspace preference; subsequent unauthenticated requests fail. Signing out does not guarantee an already issued JWT is unusable before `exp` unless app state or separately verified revocation denies it.
- With zero owned workspaces show truthful creation; with one/many show an explicit picker/resume; with invalid/revoked workspace fall back without private data. The approved Opportunities destination only renders **if actually implemented**; otherwise show an honest M1 authenticated foundation screen, not fabricated research/profile content.
- Store last selected workspace as a preference **namespaced to the verified user**, not server-side permission or an approved DB preference field. Revalidate via FastAPI on reload, deep link or account change.
- Partition private caches/query keys by verified **user + workspace + query parameters**. Abort in-flight requests when possible **and discard** late A results after switch to B with a context-generation guard. Purge private display, SSR data and client caches on logout/account change. An in-flight operation stays bound to its original workspace, never reassigned to the current visible workspace.
