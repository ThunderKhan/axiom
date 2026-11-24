"""Persist completed permission-reviewed feed discovery runs.

Revision ID: m6_0001_research_runs
Revises: m5_0001_mcp_consent
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m6_0001_research_runs"
down_revision: str | None = "m5_0001_mcp_consent"
branch_labels = None
depends_on = None

_OWN = (
    "EXISTS (SELECT 1 FROM axiom.workspaces w "
    "WHERE w.id = workspace_id AND w.owner_user_id = axiom.current_subject() "
    "AND EXISTS (SELECT 1 FROM axiom.app_users a "
    "WHERE a.id = axiom.current_subject() AND a.status = 'active'))"
)


def upgrade() -> None:
    op.create_table(
        "research_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_revision", sa.BigInteger(), nullable=False),
        sa.Column("create_key", sa.String(128), nullable=False),
        sa.Column("create_fingerprint", sa.String(64), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "profile_revision"],
            ["axiom.profile_versions.workspace_id", "axiom.profile_versions.revision"],
            name="fk_research_run_profile",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("workspace_id", "create_key", name="uq_research_run_key"),
        sa.CheckConstraint(
            "char_length(create_key) BETWEEN 8 AND 128 "
            "AND create_key ~ '^[A-Za-z0-9][A-Za-z0-9_-]*$'",
            name="ck_research_run_key",
        ),
        sa.CheckConstraint(
            "char_length(create_fingerprint) = 64 AND create_fingerprint ~ '^[0-9a-f]+$'",
            name="ck_research_run_fingerprint",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(result) = 'object' AND octet_length(result::text) <= 131072",
            name="ck_research_run_result",
        ),
        schema="axiom",
    )
    op.create_index(
        "ix_research_run_workspace_created",
        "research_runs",
        ["workspace_id", sa.text("created_at DESC")],
        schema="axiom",
    )
    op.execute("ALTER TABLE axiom.research_runs ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY research_runs_own_read ON axiom.research_runs "
        f"FOR SELECT TO axiom_runtime USING ({_OWN})"
    )
    op.execute(
        "CREATE POLICY research_runs_own_insert ON axiom.research_runs "
        f"FOR INSERT TO axiom_runtime WITH CHECK ({_OWN})"
    )
    op.execute("GRANT SELECT ON axiom.research_runs TO axiom_runtime")
    op.execute(
        "GRANT INSERT (id, workspace_id, profile_revision, create_key, create_fingerprint, result) "
        "ON axiom.research_runs TO axiom_runtime"
    )


def downgrade() -> None:
    raise RuntimeError("Saved research runs require reviewed forward recovery")
