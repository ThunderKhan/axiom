"""Durable founder consent records for read-only delegated MCP access.

Revision ID: m5_0001_mcp_consent
Revises: m4_0001_scenarios
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m5_0001_mcp_consent"
down_revision: str | None = "m4_0001_scenarios"
branch_labels = None
depends_on = None

_OWN = (
    "user_id = axiom.current_subject() AND "
    "EXISTS (SELECT 1 FROM axiom.workspaces w "
    "WHERE w.id = workspace_id AND w.owner_user_id = axiom.current_subject()) AND "
    "EXISTS (SELECT 1 FROM axiom.app_users a "
    "WHERE a.id = axiom.current_subject() AND a.status = 'active')"
)


def upgrade() -> None:
    op.create_table(
        "mcp_client_grants",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("resource", sa.String(256), primary_key=True),
        sa.Column("scopes", postgresql.JSONB(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["user_id"], ["axiom.app_users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["axiom.workspaces.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "jsonb_typeof(scopes) = 'array' AND jsonb_array_length(scopes) BETWEEN 1 AND 3 "
            'AND scopes <@ \'["research:run","evidence:read","crm:read"]\'::jsonb',
            name="ck_mcp_grant_scopes",
        ),
        sa.CheckConstraint(
            "char_length(resource) BETWEEN 1 AND 256 AND resource LIKE 'https://%/mcp'",
            name="ck_mcp_grant_resource",
        ),
        sa.CheckConstraint("expires_at > created_at", name="ck_mcp_grant_expiry"),
        sa.CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_mcp_grant_revocation",
        ),
        schema="axiom",
    )
    op.execute("ALTER TABLE axiom.mcp_client_grants ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY mcp_grants_own_read ON axiom.mcp_client_grants "
        f"FOR SELECT TO axiom_runtime USING ({_OWN})"
    )
    op.execute(
        "CREATE POLICY mcp_grants_own_insert ON axiom.mcp_client_grants "
        f"FOR INSERT TO axiom_runtime WITH CHECK ({_OWN} AND revoked_at IS NULL)"
    )
    op.execute(
        "CREATE POLICY mcp_grants_own_revoke ON axiom.mcp_client_grants "
        f"FOR UPDATE TO axiom_runtime USING ({_OWN} AND revoked_at IS NULL) "
        f"WITH CHECK ({_OWN} AND revoked_at IS NOT NULL)"
    )
    op.execute("GRANT SELECT ON axiom.mcp_client_grants TO axiom_runtime")
    op.execute(
        "GRANT INSERT (user_id, client_id, workspace_id, resource, scopes, expires_at) "
        "ON axiom.mcp_client_grants TO axiom_runtime"
    )
    op.execute("GRANT UPDATE (revoked_at) ON axiom.mcp_client_grants TO axiom_runtime")


def downgrade() -> None:
    raise RuntimeError("MCP consent history requires reviewed forward recovery")
