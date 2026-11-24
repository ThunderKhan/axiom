"""Persist immutable scenario comparisons and their frozen evidence.

Revision ID: m4_0001_scenarios
Revises: m3_0001_leads
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m4_0001_scenarios"
down_revision: str | None = "m3_0001_leads"
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
        "scenario_comparisons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_version", sa.BigInteger(), nullable=False),
        sa.Column("profile_revision", sa.BigInteger(), nullable=False),
        sa.Column("create_key", sa.String(length=128), nullable=False),
        sa.Column("create_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "lead_id"],
            ["axiom.leads.workspace_id", "axiom.leads.id"],
            ondelete="RESTRICT",
            name="fk_scenario_comparison_lead",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "profile_revision"],
            ["axiom.profile_versions.workspace_id", "axiom.profile_versions.revision"],
            ondelete="RESTRICT",
            name="fk_scenario_comparison_profile",
        ),
        sa.UniqueConstraint(
            "workspace_id", "create_key", name="uq_scenario_comparison_workspace_key"
        ),
        sa.CheckConstraint("lead_version >= 1", name="ck_scenario_comparison_lead_version"),
        sa.CheckConstraint("profile_revision >= 1", name="ck_scenario_comparison_profile_revision"),
        sa.CheckConstraint(
            "char_length(create_key) BETWEEN 8 AND 128 "
            "AND create_key ~ '^[A-Za-z0-9][A-Za-z0-9_-]*$'",
            name="ck_scenario_comparison_key",
        ),
        sa.CheckConstraint(
            "char_length(create_fingerprint) = 64 AND create_fingerprint ~ '^[0-9a-f]+$'",
            name="ck_scenario_comparison_fingerprint",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(snapshot) = 'object' AND octet_length(snapshot::text) <= 65536",
            name="ck_scenario_comparison_snapshot",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(result) = 'object' AND octet_length(result::text) <= 262144",
            name="ck_scenario_comparison_result",
        ),
        schema="axiom",
    )
    op.create_index(
        "ix_scenario_comparison_workspace_lead_created",
        "scenario_comparisons",
        ["workspace_id", "lead_id", sa.text("created_at DESC")],
        schema="axiom",
    )
    op.execute("ALTER TABLE axiom.scenario_comparisons ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY scenario_comparisons_own_read ON axiom.scenario_comparisons "
        f"FOR SELECT TO axiom_runtime USING ({_OWN})"
    )
    op.execute(
        "CREATE POLICY scenario_comparisons_own_insert ON axiom.scenario_comparisons "
        f"FOR INSERT TO axiom_runtime WITH CHECK ({_OWN})"
    )
    op.execute("GRANT SELECT ON axiom.scenario_comparisons TO axiom_runtime")
    op.execute(
        "GRANT INSERT (id, workspace_id, lead_id, lead_version, profile_revision, "
        "create_key, create_fingerprint, snapshot, result) "
        "ON axiom.scenario_comparisons TO axiom_runtime"
    )


def downgrade() -> None:
    raise RuntimeError("Saved scenario comparisons require reviewed forward recovery")
