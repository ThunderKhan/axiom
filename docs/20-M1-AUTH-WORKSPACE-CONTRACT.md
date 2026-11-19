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

## 6. JWT cryptographic verification, JWKS and outages (D1–D3, I3)

FastAPI MUST use a mature JWT verification library and independently verify **every** user bearer token. The trusted project configuration is fixed server-side, not constructed from token-supplied URLs. Require:

- Cryptographically valid signature under **project-approved asymmetric** algorithm(s) and a trusted current public key from the project's canonical HTTPS JWKS. Verify header key ID/algorithm/key type coherence; never allow `none`, arbitrary algorithms, attacker-provided JWK/JWKS URLs, or unverified decoding.
- Expected, exact Supabase Auth issuer `iss`; applicable fixed audience `aud`; unexpired `exp`; valid `iat` and `nbf` where present; UUID `sub`; ordinary `authenticated` user role and non-anonymous identity. Reject provider `anon`, `service_role`, malformed/non-user or foreign-project tokens as ordinary founders. Treat provider session metadata (e.g. `session_id`) appropriately, but a correctly signed session claim is **not** proof the session has not since been revoked.
- Server-owned §app_users.status=active` and workspace ownership **after** cryptographic verification. No app role/owner identity may be inferred from untrusted token metadata or client input.
- Actual Supabase project signing mode and supported key algorithms are **not yet verified**. The selected design requires asymmetric signing; existing legacy/symmetric HS256 credentials are not an approved production fallback. Confirm or separately authorize/configure migration in the real nonproduction Supabase test project.

### 6.1 Controlled JWKS cache and key rotation

Accept public keys from the configured project's canonical JWKS only. The **maximum permitted local key age is 300 seconds** since successful trusted retrieval. Refresh boundedly, including rate-limited/cache-throttled unknown-`kid` attempts with backoff to prevent unbounded external calls. Support administrative cache invalidation for rotation/security incidents. A token signed by a freshly unknown key must remain **denied** until its signature can be verified using a trusted refreshed key. New signing keys and revoked keys require explicit rotation tests.

Supabase documents **roughly ten-minute JWKS edge caching** and potentially other layers. The 300-second Axiom cache maximum does **not** guarantee a revoked upstream signing key is rejected within five minutes. Urgent compromise may require local cache purge, temporarily blocking affected accounts/requests, provider operations and post-incident evidence. See [Supabase JWT verification](https://supabase.com/docs/guides/auth/jwts) and [JWT signing keys](https://supabase.com/docs/guides/auth/signing-keys).

### 6.2 Provider outage/failure behavior

When Auth/JWKS cannot be contacted, a request can proceed **only if** every required JWT property is verified with a trusted locally cached key **within its 300-second bound** AND local PostgreSQL can still confirm an active app user and authorized owner/object. Never extend JWT `exp`, bypass account checks or accept an unknown/stale signature. If keys are stale/unavailable or application/DB authorization cannot safely complete, fail closed with the appropriate safe 401/503 distinction. Offline signature verification cannot detect newly revoked refresh sessions or out-of-band provider-side user deletion. New logins and refreshes may be unavailable during outage; do not promise otherwise.

## 7. Minimum PostgreSQL schema and transactional invariants (E1–E3, F1, G3)

**Schema authority for future implementation:** SQLAlchemy 2.x and Alembic, one migration source. These are **normative M1 table requirements, not SQL migrations or a declaration of existing tables**. All timestamp fields use UTC-capable PostgreSQL `timestamptz`; IDs are UUIDs.

| Table | Normative columns and data constraints | Owner and lifecycle |
|---|---|---|
| `app_users` | `id uuid PRIMARY KEY` = verified Supabase `sub`; server-owned `status` constrained to `active`, `suspended`, `deprovisioned`; `created_at` and `updated_at` required | No cascading FK from `auth.users`; ordinary user status is not client-mutable; trusted own-row read permitted for bootstrap/account guard |
| `workspaces` | `id uuid PRIMARY KEY` generated by server; `owner_user_id uuid NOT NULL REFERENCES app_users(id) ON DELETE RESTRICT`; `name text NOT NULL` validated to canonical 1–120 characters; required `created_at`/`updated_at`; `version bigint NOT NULL DEFAULT 1 CHECK (version >= 1)` | One immutable owner; no workspace membership, no unique owner or unique workspace name constraint, no M1 delete/owner-transfer operation |
| `workspace_create_idempotency` (or equivalent table) | Owner UUID FK, operation discriminator, bounded request key, digest of canonical payload, safely serializable committed result (status + response/resource), `created_at` and `expires_at`; `UNIQUE(owner_user_id, operation, key)` | Durable owner-only replay; **retain committed result at least 24 hours**; cleanup with safe concurrency semantics |

**Indexes:** an index supporting owner-scoped listing ordered by `created_at DESC, id DESC`, and uniqueness/lookup for the idempotency tuple. Index behavior must be measured, not invented as production-tuned. Client-supplied workspace IDs and owner IDs never confer permission. Two workspace creations for the same owner must both succeed; different products may have identical names.

**Name normalization:** FastAPI trims leading/trailing whitespace, rejects whitespace-only names, unsafe control characters and any resulting length outside **1–120 Unicode characters**. Use the same canonical representation in persistence and idempotency digest. DB constraints must reject null, empty and oversized names and must not accidentally contradict the application Unicode normalization policy; test Unicode/whitespace boundaries in PostgreSQL. Reject extra or privileged writable JSON fields.

**Future child tables:** §docs/07-DATABASE-DESIGN.md` proposes workspace-owned product/research/CRM records beyond M1. Later implementation must use `workspace_id` on private tables and suitable `UNIQUE(workspace_id,id)` / composite FKs for cross-workspace relationships so a child in A cannot reference a parent in B. That broader DDL is **not frozen** by this contract.

**Delete and retention:** E3 forbids public M1 destructive account/workspace deletion. The broader draft's child `ON DELETE CASCADE` examples illustrate DB effects of deliberately deleting parent rows, **not authorization** for an end-user delete or provider-deletion cascade. Parent owner FK must be restrictive; privacy-law requests, export/purge and backup retention need a separate approved operator policy. Suspension/deprovisioning retains business records until such policy applies.

### 7.1 Bootstrap atomicity and workspace creation replay

- Identity bootstrap uses the verified subject as the unique key; concurrent insert-on-conflict operations converge, and an existing non-active row is never reset to active.
- Workspace `POST` requires an `Idempotency-Key` header. Bind a **bounded, validated** key transactionally to **authenticated owner + operation + fingerprint of the canonical normalized request**. Insert workspace and record the successful response as one atomic logical unit; an aborted transaction cannot record a successful replay.
- Same owner/operation/key + same canonical payload **within retained window** returns exactly the original committed **201**, workspace ID and safe response body. Same key with changed canonical payload returns **409 IDEMPOTENCY_CONFLICT** without a new workspace. Independent keys (even with equal name) are new operations.
- Concurrent duplicate requests must converge on one durable result, including after a lost HTTP response or application process restart. Store enough outcome data for replay without a secondary read accidentally exposing another tenant.
- Retain committed outcomes **at least 24 hours** after success. After expiry and actual deletion of the idempotency record, reuse **may create a new operation**; do not promise indefinite deduplication. Expiry/cleanup must not race with an in-flight operation. The exact bounded header character syntax/storage scheduler is an implementation-level safety detail to verify, not permission to weaken this guarantee.
- Workspace PATCH uses a positive integer `expected_version` in the body, checks ownership and version atomically, returns **409 VERSION_CONFLICT** with no partial write if stale. On an actual committed update, advance version exactly once and timestamp. A no-change request must still verify the supplied version; it need not manufacture an unrelated data mutation. Never last-write-wins silently.

## 8. Least-privilege DB roles, RLS and transaction-local principal (F1–F3)

### 8.1 Database credentials

The ordinary SQLAlchemy API connection runs as a dedicated, non-table-owner, non-superuser, **non-`BYPASSRLS`** PostgreSQL role with narrowly granted table/schema/function rights. It cannot perform Alembic DDL. Privileged migrations run through a **separate migration credential** supplied only to an authorized schema-management process. A future background worker requires a separately reviewed least-privileged, job-origin-scoped capability and cannot impersonate arbitrary users or bypass workspace checks. The chosen managed Supabase project's actual role/grant feasibility and pool limits are **unverified**.

RLS is enabled on each M1 private table and checked under the actual API DB login: owner-scoped `USING` predicates for reads/updates; owner-scoped `WITH CHECK` predicates for inserts/updates; absent/invalid context denies. No public or ordinary user DELETE policy in M1. Runtime DB grants must not permit broad administrative operations or permission changes. An app-user's **own** status row must be readable by the trusted auth guard (including when suspended) to enforce denial; normal business operations then require status active. Bootstrap may insert only a verified subject-matching row with default active status, never an arbitrary user/status.

### 8.2 Identity in direct PostgreSQL connections

Supabase §auth.uid()` is naturally populated through supported Supabase API request context; **it is not automatically populated in a raw SQLAlchemy PostgreSQL connection**. After JWT verification, FastAPI establishes its trusted UUID principal **within each protected database transaction before SQL**. One reviewed approach is parameterized transaction-local PostgreSQL configuration (conceptually `set_config('app.current_user_id', verified_uuid, true)`). Policies read a safely parsed UUID from that transaction setting; missing/malformed context denies by default.

The transaction-local setting must disappear at COMMIT/ROLLBACK, including on exceptions and connection reuse across users A/B. Do not place per-user identity in persistent connection-level `SET`, global mutable Python state or a shared worker process context. Test actual SQLAlchemy begin/commit/rollback, async/concurrent operations, Supabase direct/session/transaction pooler mode, and connection reuse.

**Security limitation:** a custom PostgreSQL GUC can also be set by SQL executed with the same runtime role. It mitigates missed workspace filters under a disciplined backend but is **not tamper-proof evidence against arbitrary SQL injection**. Use parameterized statements, constrained SQL execution, explicit FastAPI authorization and defense-in-depth RLS; a client cannot set the trusted principal itself. Migration and service/owner DB roles may bypass RLS, and backend owner checks must still prevent cross-tenant requests even where a privileged connection was used.

### 8.3 Mandatory isolation invariants

- A user A may list/read/modify only A's workspaces; B has the analogous isolated rights. User A changing URL/body/local storage to B's ID never provides access.
- RLS `USING` prevents foreign/absent-context visibility; `WITH CHECK` prevents wrong-owner inserts and ownership-changing updates. Cross-workspace composite FKs deny mismatched references when child tables are later implemented.
- Prove that table owner/privileged credentials may bypass RLS, then prove application authorization **still** denies foreign requests. Tests performed solely as a privileged DB owner do not establish RLS coverage.
- The account bootstrap own-row insert and account-status query must work without creating a universal RLS/credential bypass. Failed authorization, missing context, and unavailable database return truthful errors, not empty success responses.

## 9. Exact M1 HTTP contracts and error envelope (G1–G3, I1)

**Transport:** JSON over HTTPS, base path `/api/v1`, user bearer in `Authorization: Bearer <Supabase access JWT>`. Server derives owner from verified `sub`, never client body. OpenAPI/TypeScript types must match the reviewed DTO exactly; all examples below are synthetic.

### 9.1 Endpoints

| Method / path | Required request | Successful response |
|---|---|---|
| `POST /api/v1/me/bootstrap` | Verified ordinary user JWT; no caller user ID | **201** newly provisioned or **200** existing active app user; `{"user":{"id":"<uuid>","status":"active","created_at":"<UTC-ISO8601>"},"created":true|false}` |
| `GET /api/v1/me` | Verified JWT, no mutation | **200** `{"id":"<uuid>","status":"active","created_at":"<UTC-ISO8601>"}`; valid but unbootstrapped caller → **409 PROVISIONING_REQUIRED** |
| `GET /api/v1/workspaces` | Optional `limit` (default 20, max 100) and validated opaque `cursor` | **200** `{"items":[Workspace...],"next_cursor":null|string}`, owner-scoped, deterministic `created_at DESC,id DESC` |
| `POST /api/v1/workspaces` | Required `Idempotency-Key` header; JSON `{"name":"<trimmed name>"}` | **201** canonical `Workspace`; same committed key+payload within retention replays original 201/body/ID |
| `GET /api/v1/workspaces/{workspace_id}` | UUID path and verified owner | **200** canonical `Workspace`; foreign/missing → identical **404** |
| `PATCH /api/v1/workspaces/{workspace_id}` | UUID path; JSON `{"name":"<trimmed name>","expected_version":<positive integer>}` | **200** updated `Workspace`; version conflict → **409** without mutation |

Safe canonical `Workspace` response:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "name": "Example product",
  "created_at": "2026-11-19T10:00:00Z",
  "updated_at": "2026-11-19T10:00:00Z",
  "version": 1
}
```

**No writable owner/ID/status field** is accepted. Return and request shape are intentionally minimal. The name is 1–120 characters after canonical trim; versions positive integer; UUID malformed → validation error. List cursor is opaque, validated and bound to authorized query/owner; malformed or foreign cursor cannot cause data leakage. Empty workspace list is a valid 200 response. Body fields not in the contract are rejected. No DELETE or owner-transfer endpoint is approved.

### 9.2 Error contract

Error JSON must have the same safe shape for every endpoint:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Workspace not found.",
    "retryable": false,
    "details": {}
  },
  "request_id": "req_example"
}
```

| Status | Code | Required behavior |
|---|---|---|
| **401** | `AUTH_REQUIRED` | Missing, invalid, wrong-issuer/audience/signature/role or expired JWT; no private data |
| **403** | `ACCOUNT_DISABLED` | Verified but suspended/deprovisioned application principal |
| **404** | `NOT_FOUND` | **Identical response** for foreign and nonexistent workspace ID on read/update; do not confirm another tenant exists |
| **409** | `PROVISIONING_REQUIRED` | Valid JWT but app-user bootstrap absent on ordinary `GET /me` / protected operation |
| **409** | `VERSION_CONFLICT` | Workspace PATCH expected version stale, no lost update |
| **409** | `IDEMPOTENCY_CONFLICT` | Same owner/operation/key with a different canonical POST payload |
| **422** | `VALIDATION_FAILED` | Missing required create key, malformed UUID/body, invalid name/version/limit, unapproved writable field |
| **503** | Safe typed dependency code (e.g. `AUTH_UNAVAILABLE` / `DATABASE_UNAVAILABLE`) | Required verification/authorization cannot proceed safely; indicate retry only when genuinely applicable |

Use typed, non-secret validation details and opaque `request_id`; never log bearer, JWT contents, cookies, evaluator credentials, sensitive request bodies or database URLs. A 401 is not a disabled-account 403. Missing/foreign workspace 404 must agree on response code, message and externally visible details; do not claim constant-time guarantees without tests. A provider-side outage cannot be transformed into an authorized success.

**Draft reconciliation:** §docs/08-API-CONTRACTS.md` proposed `403 WORKSPACE_FORBIDDEN` for foreign workspaces; G2 owner choice **overrides this for M1 workspace read/update only**. The rest of the general API draft remains DRAFT.
