"""Harden M1 tables with explicit runtime grants and transaction-scoped RLS.

Revision ID: m1_0002_rls
Revises: m1_0001_schema
"""

from __future__ import annotations

from alembic import op

revision: str = "m1_0002_rls"
down_revision: str | None = "m1_0001_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This must execute as a dedicated migration-role table owner, never runtime.
    op.execute("REVOKE ALL ON SCHEMA axiom FROM PUBLIC")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA axiom FROM PUBLIC")
    op.execute(
        """CREATE FUNCTION axiom.current_subject() RETURNS uuid
           LANGUAGE sql STABLE SECURITY INVOKER SET search_path = pg_catalog AS $fn$
           SELECT CASE
             WHEN current_setting('app.current_user_id', true) ~
               '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
             THEN current_setting('app.current_user_id', true)::uuid
             ELSE NULL::uuid
           END
           $fn$"""
    )
    op.execute("REVOKE ALL ON FUNCTION axiom.current_subject() FROM PUBLIC")
    for table in ("app_users", "workspaces", "workspace_create_idempotency"):
        op.execute(f"ALTER TABLE axiom.{table} ENABLE ROW LEVEL SECURITY")

    op.execute(
        """CREATE POLICY app_user_own_read ON axiom.app_users
           FOR SELECT TO axiom_runtime
           USING (id = axiom.current_subject())"""
    )
    op.execute(
        """CREATE POLICY app_user_own_bootstrap ON axiom.app_users
           FOR INSERT TO axiom_runtime
           WITH CHECK (id = axiom.current_subject() AND status = 'active')"""
    )
    for table in ("workspaces", "workspace_create_idempotency"):
        owner = "owner_user_id"
        active = (
            f"{owner} = axiom.current_subject() AND EXISTS "
            "(SELECT 1 FROM axiom.app_users a "
            " WHERE a.id = axiom.current_subject() AND a.status = 'active')"
        )
        op.execute(
            f"CREATE POLICY {table}_own_read ON axiom.{table} "
            f"FOR SELECT TO axiom_runtime USING ({active})"
        )
        op.execute(
            f"CREATE POLICY {table}_own_insert ON axiom.{table} "
            f"FOR INSERT TO axiom_runtime WITH CHECK ({active})"
        )
    op.execute(
        """CREATE POLICY workspace_own_update ON axiom.workspaces
           FOR UPDATE TO axiom_runtime
           USING (
              owner_user_id = axiom.current_subject()
              AND EXISTS (
                 SELECT 1 FROM axiom.app_users
                 WHERE id = axiom.current_subject() AND status = 'active'
              )
           )
           WITH CHECK (
              owner_user_id = axiom.current_subject()
              AND EXISTS (
                 SELECT 1 FROM axiom.app_users
                 WHERE id = axiom.current_subject() AND status = 'active'
              )
           )"""
    )
    op.execute("GRANT USAGE ON SCHEMA axiom TO axiom_runtime")
    op.execute("GRANT EXECUTE ON FUNCTION axiom.current_subject() TO axiom_runtime")
    op.execute("GRANT SELECT ON axiom.app_users TO axiom_runtime")
    op.execute("GRANT INSERT (id) ON axiom.app_users TO axiom_runtime")
    op.execute("GRANT SELECT ON axiom.workspaces TO axiom_runtime")
    op.execute("GRANT INSERT (id, owner_user_id, name) ON axiom.workspaces TO axiom_runtime")
    op.execute(
        "GRANT UPDATE (name, updated_at, version) ON axiom.workspaces TO axiom_runtime"
    )
    op.execute(
        "GRANT SELECT ON axiom.workspace_create_idempotency TO axiom_runtime"
    )
    op.execute(
        "GRANT INSERT (owner_user_id, operation, key, fingerprint, response_status, "
        "response_body, expires_at) ON axiom.workspace_create_idempotency TO axiom_runtime"
    )
    # Read-only schema revision allows an unprivileged API to detect drift honestly.
    op.execute("GRANT SELECT ON public.alembic_version TO axiom_runtime")


def downgrade() -> None:
    raise RuntimeError(
        "Removing RLS or least-privilege grants would violate M1 isolation; forward-fix only"
    )
