# ADR-002 — Supabase Authentication, PostgreSQL, and FastAPI Domain Data Boundary

**Status:** APPROVED by founder  
**Decision date:** 18 November 2026  
**Decision owner:** Founder  
**Applies to:** Axiom authenticated web application, HTTP API, research worker, and MCP domain services  
**References:** [System Architecture](../05-SYSTEM-ARCHITECTURE.md), [TRD](../06-TRD.md), [Database Design](../07-DATABASE-DESIGN.md), [Security](../17-SECURITY.md)

## Context

Axiom requires ordinary login (including privately provisioned evaluator accounts), per-user isolation of multiple product workspaces, a durable relational evidence/CRM model, consistent HTTP and MCP behavior, and migrations that can be tested and reproduced. Three candidates were offered: (A) Supabase Auth + hosted PostgreSQL + FastAPI-only domain access, (B) Supabase Auth with direct browser data access via Supabase and split domain logic, and (C) custom authentication + PostgreSQL.

## Approved decision — Option A

1. **Identity:** Supabase Auth handles user authentication and session issuance. The app has public landing and login pages; the browser may use Supabase's public client SDK **for authentication only**.
2. **Database:** PostgreSQL hosted by Supabase is Axiom's durable primary data store, subject to real capacity/quota/availability testing.
3. **Domain access:** **All application business data reads and writes go through FastAPI**, including workspaces, product profiles, opportunity signals, research results, competitors, evidence, simulations, CRM, exports and background job status. No direct browser-to-Supabase domain table access.
4. **Backend and external integrations:** REST and MCP handlers share the same FastAPI application/use-case layer with consistent workspace authorization. The research worker uses server-only scoped data access, constrained to its initiating workspace/job.
5. **ORM and migrations:** **SQLAlchemy 2.x** for Python persistence/domain repositories and **Alembic** for versioned PostgreSQL schema migrations. Avoid a second parallel ORM or disconnected migration source.
6. **Security:** FastAPI validates Supabase-issued JWT signature/JWKS, issuer, applicable audience and expiration, then checks workspace ownership on **every** private operation. No client-supplied workspace ID grants authorization by itself. Apply RLS/least-privilege database roles as defense in depth where applicable; **service-role credentials can bypass RLS**, so explicit server authorization and negative cross-tenant tests are mandatory.
7. **Secret handling:** Supabase service/secret keys and database credentials are server-side only. The browser may contain only provider-documented public auth configuration. Evaluator credentials are privately distributed and low privilege.

## Why this was selected

- One authoritative backend authorization boundary for web, HTTP API, MCP and background research.
- PostgreSQL transactions and relational constraints support evidence provenance, scenario snapshots, workspace isolation and CRM.
- Managed authentication avoids implementing password hashing, sessions, reset and identity security from scratch under the submission deadline.
- SQLAlchemy + Alembic gives one consistent Python persistence/migration convention.

## Alternatives considered

- **B — Direct browser Supabase domain data via RLS:** fewer FastAPI read endpoints but more complex, divergent client/MCP permissions and domain contracts; not selected.
- **C — Custom auth + PostgreSQL:** greater security/operational workload with no clear MVP benefit; not selected.

## Consequences and non-decisions

- FastAPI is the *sole domain-data ingress* for browser and external callers; API availability must be considered a product availability dependency.
- SQLAlchemy connection pooling and migration discipline must be configured for the selected hosting tier and 500-active-founder design objective.
- **Still unverified/not approved as implemented:** Supabase project configuration, actual free-tier quotas, DB connection limits, JWKS settings, migrations, RLS policy DDL, real evaluator provisioning, server hardening, and deployed 500-user capacity.
- **Not decided by this ADR:** frontend/API/worker hosting vendors and topology, job queue deployment, AI provider, source adapters, remote MCP OAuth/token mechanism, or final per-table database schema.
- Any revision of this choice requires a new superseding ADR and index update; only owner approval can alter scope/authorization policy.

## Acceptance checks before calling implementation complete

- Two separate authenticated users and workspaces; all cross-tenant REST/MCP/worker reads and writes denied.
- A valid Supabase login and JWT issuer/signature/audience/expiry validation confirmed on deployed API.
- FastAPI executes all domain reads/writes; browser does not query domain tables directly.
- Clean-install and upgrade migrations pass with SQLAlchemy 2.x + Alembic.
- RLS/privileged-credential bypass assumptions tested, not inferred.
- DB pool and throughput measured in the real hosting environment.

**Record:** The founder explicitly selected **Option A** during the six-decision interview on 18 November 2026. This ADR records the decision; it does **not** assert implementation or deployment.
