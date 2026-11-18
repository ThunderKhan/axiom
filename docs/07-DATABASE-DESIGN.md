# Axiom — Database Design

**Status:** DRAFT — in review · **Version:** 0.1 · **Date:** 18 November 2026  
**Authority:** [PRD](02-PRD.md), [MVP](03-MVP.md), [Architecture](05-SYSTEM-ARCHITECTURE.md), [TRD](06-TRD.md)

## 1. Design intent

Recommend **PostgreSQL** as the sole durable record system. Use normalized relational rows for identity, research, source provenance, evidence and CRM; typed nodes/edges represent the evidence graph. No separate graph/vector database is necessary for initial scale. These are **proposed schema contracts**, not migrations already applied.

Invariants:
1. All private records are scoped to a workspace owned by an authenticated principal.
2. API/MCP/worker access verifies workspace membership regardless of user-provided IDs; Supabase service-role/secret key **bypasses RLS**, so application-level authorization remains essential.
3. Source snapshots and confirmed product-profile versions referenced by an assessment are immutable or versioned.
4. A "verified source-backed" competitor claim cites a real stored source/locator. Unknown remains null/unknown.
5. Scenario comparisons replay against **the same frozen evidence snapshot**.
6. Lead saves and job executions are safe under duplicates/retries.
7. Demo records have clear §seeded§ provenance, never impersonate live research.

## 2. Proposed table catalogue

| Table | Required fields / examples | Constraints/relationships |
|---|---|---|
| §workspaces§ | id, owner_user_id, name, created_at | PK UUID; owner index; names nonempty |
| §product_profiles§ | id, workspace_id, name, stage, current_version_id | stage idea/live |
| §profile_versions§ | id, workspace_id, profile_id, revision, audience, problem, capabilities jsonb, limitations jsonb, confirmed_at | unique(profile_id, revision); immutable once referenced |
| §research_runs§ | id, workspace_id, profile_version_id, query, status, created_at, finished_at | queued/running/partial/completed/failed/cancelled |
| §source_records§ | id, workspace_id, provider, provider_record_id, canonical_url, origin, excerpt, published_at, retrieved_at, digest | source, timestamps and origin mandatory; bounded excerpts |
| §signals§ | id, workspace_id, run_id, source_record_id, summary, needs jsonb, relevance, intent, fit, evidence_quality | scores 0–1 or null, foreign keys |
| §competitors§ | id, workspace_id, name, site_url, user_confirmed | suggestions cannot be assumed direct |
| §competitor_claims§ | id, workspace_id, competitor_id, source_record_id?, claim_type, text, locator, provenance | missing facts unverified/unknown |
| §evidence_snapshots§ | id, workspace_id, digest, source_revision_set jsonb, created_at | frozen assessment source list |
| §assessments§ | id, workspace_id, signal_id, profile_version_id, evidence_snapshot_id, verdict, reasons jsonb | four-verdict enum |
| §evidence_nodes§ | id, workspace_id, assessment_id, node_type, label, claim/source pointer, origin | type, provenance constraints |
| §evidence_edges§ | id, workspace_id, assessment_id, from_node_id, to_node_id, type, reason, source pointer | endpoints same workspace and assessment |
| §scenarios§ | id, workspace_id, baseline_assessment_id, name, revision, assumptions jsonb, result jsonb, created_at | baseline immutable, explicit assumption patch |
| §leads§ | id, workspace_id, signal_id?, assessment_id?, title, stage, created_at, updated_at | unique(workspace_id,signal_id) when present |
| §lead_notes§ | id, workspace_id, lead_id, author_id, text, created_at | append/audit |
| §followups§ | id, workspace_id, lead_id, due_at, state, note | due/completed/cancelled |
| §outreach_drafts§ | id, workspace_id, lead_id, content, version, status | only unsent drafts in MVP |
| §jobs§ | id, workspace_id, initiator_id, kind, status, payload, progress, lease_until, attempts, next_attempt_at, idempotency_key | durable leased queue, unique request key |
| §audit_events§ | id, workspace_id, actor_kind, actor_id, object_id, action, safe_metadata, request_id, created_at | redact secrets |

**Naming:** actual SQL naming conventions, enums, indices and foreign keys must be fixed in migration PR. Use UTC §timestamptz§ and UUID identifiers. Avoid persisting raw third-party webpage bodies beyond terms and retention policy.

## 3. Cross-workspace referential integrity

A simple independent §workspace_id§ on each table is insufficient: a lead in workspace A could accidentally point to a signal in workspace B if its foreign key is only on signal ID. Preferred pattern: **composite unique keys (workspace_id,id) and composite FKs** across all workspace-owned relationships.

Illustrative partial SQL (**not a full migration**):

§§§sql
CREATE TABLE workspaces (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_user_id uuid NOT NULL,
  name text NOT NULL CHECK (char_length(trim(name)) BETWEEN 1 AND 120),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (id, owner_user_id)
);
CREATE INDEX ix_workspaces_owner ON workspaces(owner_user_id);

CREATE TABLE source_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  provider text NOT NULL,
  canonical_url text NOT NULL,
  origin text NOT NULL CHECK
    (origin IN ('live','cached','seeded','user_provided','inferred','hypothetical','unknown')),
  excerpt text,
  retrieved_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(workspace_id,id)
);

CREATE TABLE research_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  status text NOT NULL CHECK
    (status IN ('queued','running','partial','completed','failed','cancelled')),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(workspace_id,id)
);

CREATE TABLE signals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  run_id uuid NOT NULL,
  source_record_id uuid NOT NULL,
  relevance numeric(5,4) CHECK(relevance BETWEEN 0 AND 1),
  intent numeric(5,4) CHECK(intent BETWEEN 0 AND 1),
  fit numeric(5,4) CHECK(fit BETWEEN 0 AND 1),
  FOREIGN KEY (workspace_id,run_id) REFERENCES research_runs(workspace_id,id),
  FOREIGN KEY (workspace_id,source_record_id) REFERENCES source_records(workspace_id,id)
);
§§§

Implement equivalent checks for claims/assessments/graph nodes+edges/scenarios/leads/notes/followups. **Composite FK tests and server-side checks are both required**.

### RLS when Supabase is selected

For each private table enable RLS and add ownership policies using valid membership (e.g., join §workspaces.owner_user_id = auth.uid()§), with both §USING§ and §WITH CHECK§ on mutations. A privileged backend may bypass policies; use explicit authorization in repository/use-case layer even if RLS exists. Account ID mapping from Auth to DB must be verified rather than assumed.

## 4. Snapshot, versioning and transaction boundaries

- Product review creates version N; edits create N+1; assessments refer to one confirmed version.
- Source retrieval records URL, provider ID, timestamp, excerpt locator, digest and origin. Refresh creates another revision.
- Evidence snapshot locks a set of actual observed source versions. Graph and report refer to one assessment/snapshot.
- Scenario edits do not rewrite baseline; save versions and compute changes on frozen evidence. New data requires explicit rebase.
- Create research run + job in a transaction. Claim job with bounded lease/row locking, retry after expiry with idempotency.
- Save lead + audit event in a transaction; duplicate signal save returns same lead or explicit conflict.
- Write a scenario revision + result atomically.
- Sample job claim: §SELECT id FROM jobs WHERE status='queued' AND next_attempt_at<=now() ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1§ inside transaction, then update lease/status. Additional reclaim/renew logic required.

## 5. Indices, retention and migrations

Suggested indices: workspaces(owner_user_id); runs(workspace_id,created_at DESC); signals(workspace_id,run_id); sources(workspace_id,provider,canonical_url); assessments(workspace_id,signal_id); graph nodes/edges(workspace_id,assessment_id); leads(workspace_id,stage,updated_at); followups(workspace_id,status,due_at); jobs(status,next_attempt_at,lease_until); audit(workspace_id,created_at). Validate with EXPLAIN instead of indexing every field.

Pick **Alembic or coherent SQL migrations**, not both as conflicting sources. Requirements: clean install, upgrade migration, schema-drift check, downgrade or forward-fix recovery, backups before destructive changes, and dry run with realistic data. Never commit evaluator passwords.

Retention and deletion windows are not invented in this document; define after source terms, privacy and operational review. Prefer bounded excerpts and hashes. Encrypt transit, secure provider credentials, redact audits.

## 6. Acceptance and open decisions

- Two users + two workspaces: cross-user reads, modified IDs and composite foreign-key injections are rejected.
- Lead, note, follow-up, scenario and evidence report survive login/refresh.
- Duplicate create and crashed worker retries cannot double-write business records.
- An assessment remains reproducible after new product version and newer source retrieval.
- Live vs cached vs seeded records are differentiated in data and UI.
- Clean/upgrade migrations pass in CI; backup+restore works on selected host.

**Open:** Supabase project/provider selection, actual auth/user table linkage, SQLAlchemy vs SQL migration workflow, exact JSONB boundaries, RLS role strategy, retention policy, and deletion semantics. See [Deployment Runbook](15-DEPLOYMENT-RUNBOOK.md).
