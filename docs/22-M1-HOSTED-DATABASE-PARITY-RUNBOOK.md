# M1 — Hosted Supabase Postgres, RLS and Pooler Verification

**Status:** OPERATOR PROCEDURE / NOT EXECUTED · **Scope:** hosted M1 parity and current M7 schema readiness · **Approval gate:** [Issue #29](https://github.com/ThunderKhan/axiom/issues/29)

This runbook does **not** certify the hosted database. The successful
[real-provider run #44850664291](https://github.com/ThunderKhan/axiom/actions/runs/44850664291)
used live Supabase Auth with an **isolated CI PostgreSQL 17 database**.
Read-only hosted inspection on 21 November 2026 found the M1 application
schema, roles, migration revision and policies absent. Do not treat a SQL
Editor connection as proof of least-privileged RLS: the management
`postgres` role has `BYPASSRLS`.

## 1. Authorization and stop conditions

- Use **only** dedicated nonproduction project `axiom-m1-auth-test`
  (reference `zmlgecokvbjdpuclvlqe`, region `ap-south-1`). Never
  run these instructions on VSPH or an evaluator/production project.
- Obtain separate qualified reviewer approval of role setup, schema
  ownership, migration execution and host/pooler selection **before**
  changing the hosted database. No paid upgrade or service activation is
  authorized. Review Supabase's [Postgres roles](https://supabase.com/docs/guides/database/postgres/roles)
  and [connection modes](https://supabase.com/docs/guides/database/connecting-to-postgres).
- Inspect project identity, current roles, `axiom` schema, version
  table and policies. If any are present unexpectedly or partially,
  **STOP** for a forward-recovery review; do not rerun or `DROP`
  to reset. Before DDL, record the managed backup/restore capabilities
  actually available on this plan; do not assume free-tier PITR.
- Migration and runtime URLs/passwords stay in an operator-managed
  private environment/secret manager, never GitHub issues, PR comments,
  PowerShell history, public workflows, chat or frontend `NEXT_PUBLIC_*`.
  Never print a connection URL or database driver error with credentials.
- **Do not use** `services/api/tests/postgres_roles.sql` or
  `scripts/run_db_integration.py` on hosted: both intentionally assume
  disposable local `axiom_test` and loopback-only credentials.
- No table deletion, reset, `alembic downgrade`, privileged API service
  role, Auth user deletion, or reuse of production passwords.

## 2. Provision the two dedicated PostgreSQL identities

Only after review, connect to the correct project's PostgreSQL database
as the administrator, using the exact **direct endpoint** in Supabase's
Connect panel (or explicitly reviewed session-pooler alternative).
Require TLS. The SQL below must be executed once **only if both
roles are absent**, as verified through `pg_roles`. It is not an Alembic
migration and must not be run as a generic application SQL migration:

```sql
-- Reviewed nonproduction-only DBA provisioning. Does not set passwords.
CREATE ROLE axiom_migrator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
CREATE ROLE axiom_runtime  LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
GRANT CONNECT ON DATABASE postgres TO axiom_migrator, axiom_runtime;
GRANT CREATE ON DATABASE postgres TO axiom_migrator;
GRANT USAGE, CREATE ON SCHEMA public TO axiom_migrator;
```

As an authorized DBA, use `psql`'s **interactive**
`\password axiom_migrator` and `\password axiom_runtime` commands
to set different, strong passwords without embedding cleartext passwords
in scripts or command history. Role passwords must be configured
before making either connection; no temporary trust-auth shortcut.

Record a credential-free verification query:

```sql
SELECT rolname, rolcanlogin, rolcreatedb, rolcreaterole,
       rolsuper, rolbypassrls
FROM pg_roles
WHERE rolname IN ('axiom_migrator','axiom_runtime')
ORDER BY rolname;
```

Both roles must have `rolcanlogin=true` and every privilege flag
`rolcreatedb/rolcreaterole/rolsuper/rolbypassrls=false`.
The runtime role must not own the application tables and must not
inherit migrator/administrator privileges. No broad Supabase
`authenticated`/`anon` grants to `axiom`.

## 3. Execute *real Alembic*, once, under the migration identity

Use an isolated operator shell in `services/api`. Supply
`AXIOM_MIGRATION_DATABASE_URL` privately, pointing to this project's
**actual `axiom_migrator` login** and the `postgres` database.
Prefer Supabase's direct connection; do not guess a region's pooler
hostname or put credentials in shell scripts.

Verify the role and project identity **before** running Alembic.
Then run:

```sh
uv sync --frozen
uv run --frozen alembic upgrade head
uv run --frozen alembic check
```

The current version-controlled migration chain is `m1_0001_schema` (three M1 tables),
`m1_0002_rls` (seven M1 policies and minimum runtime grants), followed
by `m2_0001_profiles` (two profile tables and five additional owner-scoped
policies/grants), then `m3_0001_leads` (two CRM tables and five policies)
`m4_0001_scenarios` (one immutable comparison table and two policies),
`m5_0001_mcp_consent` (one grant table and three policies),
`m6_0001_research_runs` (one run table and two policies), and
`m7_0001_lead_provenance` (immutable lead provenance and tenant-bound run FK).
**The Nov 21 M1 evidence was collected at the older
three-table/seven-policy revision; it is historical, not a current-head pass.**
Alembic must create/update its real `public.alembic_version`; **never
insert or fake `version_num` manually** or replay copied DDL and call
it a migration.

Verify, via **read-only** SQL, that:
- revision equals the **exact current code head `m7_0001_lead_provenance`**
  at the reviewed November 24 checkpoint; re-check `HEAD_REVISION` before execution;
- exactly **ten** reviewed `axiom` application tables exist with RLS enabled;
- exactly **twenty-four** reviewed owner-scoped policies target `axiom_runtime`
  and include correct `USING`/`WITH CHECK` clauses;
- `axiom.current_subject()` exists, is `SECURITY INVOKER`, and is
  granted only as approved;
- runtime can read only necessary tables and insert/update the
  explicitly permitted columns; it cannot CREATE, DELETE a workspace,
  or update `owner_user_id`; it cannot update/delete confirmed profile versions,
  lead events or saved scenario comparisons; MCP grants are immutable except
  one-way revocation;
- `anon` and `authenticated` cannot access `axiom` domain tables.
  
Stop if role ownership, revision, policy count or grants differ.

## 4. Test the *real runtime login* through Supavisor

Use the Connect panel to obtain a separate private
`AXIOM_HOSTED_TEST_DATABASE_URL` for the project's
`axiom_runtime` login. Supavisor uses a pooler-specific login name
(`axiom_runtime.<project-ref>`). Check the actual host and mode in
Supabase, not a guessed URL. The verifier permits **only one**
operator-approved hostname matching `aws-<pool-number>-ap-south-1.pooler.supabase.com`;
multi-host libpq syntax (including commas) is rejected. Require
**`sslmode=verify-full`**, never `require` or `verify-ca` alone.
Configure a trusted CA root **before** connecting, using the certificate
bundle supplied/approved for the project (e.g. private `sslrootcert`
path in the URL, or the trusted default libpq root file). If the root
is missing or the hostname does not match the server certificate,
the connection must **fail closed**. Do not disable certificate
verification to get a green result.

Run the shipped verifier separately in both supported modes, setting:

- `AXIOM_HOSTED_TEST_CONFIRMATION=I_CONFIRM_AXIOM_M1_NONPRODUCTION`
- `AXIOM_HOSTED_TEST_POOLER_MODE=session` for the real session
  pooler endpoint (`5432`), then `transaction` for the real transaction
  pooler endpoint (`6543`);
- `AXIOM_HOSTED_TEST_DATABASE_URL` to the matching secret URL;
- `AXIOM_HOSTED_TEST_APPROVED_POOLER_HOST` to the single exact hostname
  chosen from this project's Supabase Connect panel (no IPs,
  commas, additional hosts or guessed names).

```sh
cd services/api
uv run --frozen python scripts/verify_hosted_m1_parity.py
```

The script is **fail-closed**: it requires the exact dedicated project
reference, expected runtime login, genuine Supavisor host/port, TLS,
`Database.ready()` under the actual unprivileged role, and a
two-subject `USING`/`WITH CHECK` isolation probe. It intentionally
rolls back all temporary rows; a foreign write must fail with the
PostgreSQL permissions/RLS error state, not an arbitrary connection or
SQL failure. It also proves transaction-local identity disappears
after rollback. It prints only sanitized PASS/BLOCKED labels.

**Prepared-statement note:** Supavisor transaction mode does not support
server-side prepared statements. Axiom disables psycopg3 automatic
preparation on the approved `*.pooler.supabase.com:6543` runtime path
only; it preserves defaults for direct and session connections. A test
of this configuration belongs in Quality and does not replace the
actual hosted test.

## 5. Preserve proof and obtain independent security signoff

Capture *redacted* evidence with:
project reference, PostgreSQL version, application migration revision,
table/policy/grant checks, actual Supavisor mode (without secrets),
runtime-role probe result, CI run/commit SHA and operator/reviewer
decision. Re-run appropriate API test/deployed HTTPS security checks
after switching the API from disposable CI DB to the managed runtime
connection. Never represent this script's use of synthetic principals
as proof of actual Supabase Auth JWT validation; that remains the
separate protected provider run.

Review the Supabase advisor's `auth_leaked_password_protection` warning
for Free-tier availability. Do not silently purchase a plan or disable
authentication requirements to remove the warning.

A **qualified, independent human security reviewer** must explicitly
review the actual hosted role/RLS/pooler evidence, session/JWT
boundary, cross-tenant behavior, credential handling and outstanding
deployment risks. Update `docs/21-M1-ACCEPTANCE-LEDGER.md`, secure
the operator evidence, and close [issue #29](https://github.com/ThunderKhan/axiom/issues/29)
only if all mandated acceptance gates pass. Otherwise label M1
**INCOMPLETE VERIFICATION** or **REQUIRES HUMAN REVIEW**.

## Historical WP-03 / M2 compatibility addendum — 23 November 2026

The historical five-table expectation below is superseded by the M7 chain
and ten-table/twenty-four-policy checks in section 3. The M1 verifier checks
current schema readiness plus M1 isolation; it is not a substitute for
current CRM/scenario domain and browser acceptance.

The held M1 hosted-DB gate [issue #29](https://github.com/ThunderKhan/axiom/issues/29) cannot be considered complete by inspecting only the old three M1 tables: the next integrated revision introduces two profile tables and five additional owner-scoped RLS policies. After WP-03 is merged, run **ordered genuine Alembic upgrade head as the dedicated migration identity** only after private credentials/backup/qualified operator approval and full prereview. Validate the latest five-table/twelve-policy state, forbid UPDATE/DELETE on confirmed `profile_versions`, then rerun both supported real pooler modes as `axiom_runtime` and appropriate profile cross-owner security tests. No hosted migration or direct database work is authorized solely by this doc change; the previously recorded provider Auth tests remain separate from hosted schema/parity.
