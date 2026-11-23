"""Owner-scoped saved leads and immutable audit metadata.

Revision ID: m3_0001_leads
Revises: m2_0001_profiles
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m3_0001_leads"
down_revision: str | None = "m2_0001_profiles"
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
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("axiom.workspaces.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_excerpt", sa.Text(), nullable=False),
        sa.Column(
            "source_origin", sa.String(length=30), nullable=False, server_default="user_provided"
        ),
        sa.Column("stage", sa.String(length=20), nullable=False, server_default="spotted"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("follow_up_at", sa.DateTime(timezone=True)),
        sa.Column("follow_up_done", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("unsent_draft", sa.Text(), nullable=False, server_default=""),
        sa.Column("create_key", sa.String(length=128), nullable=False),
        sa.Column("create_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "stage IN ('spotted', 'qualified', 'contacted', 'closed_lost')",
            name="ck_leads_stage",
        ),
        sa.CheckConstraint("char_length(title) BETWEEN 1 AND 180 AND btrim(title) <> ''", name="ck_leads_title"),
        sa.CheckConstraint("char_length(source_url) <= 2048", name="ck_leads_source_url"),
        sa.CheckConstraint(
            "char_length(source_excerpt) BETWEEN 1 AND 500", name="ck_leads_excerpt"
        ),
        sa.CheckConstraint("char_length(note) <= 2000", name="ck_leads_note"),
        sa.CheckConstraint("char_length(unsent_draft) <= 4000", name="ck_leads_draft"),
        sa.CheckConstraint("version >= 1", name="ck_leads_version"),
        sa.CheckConstraint(
            "NOT follow_up_done OR follow_up_at IS NOT NULL", name="ck_leads_followup_state"
        ),
        sa.CheckConstraint("source_origin = 'user_provided'", name="ck_leads_origin"),
        sa.CheckConstraint(
            "char_length(create_key) BETWEEN 8 AND 128 "
            "AND create_key ~ '^[A-Za-z0-9][A-Za-z0-9_-]*$'",
            name="ck_leads_create_key",
        ),
        sa.CheckConstraint(
            "char_length(create_fingerprint) = 64 "
            "AND create_fingerprint ~ '^[0-9a-f]+$'",
            name="ck_leads_fingerprint",
        ),
        sa.UniqueConstraint("workspace_id", "id", name="uq_leads_workspace_id"),
        sa.UniqueConstraint("workspace_id", "create_key", name="uq_leads_workspace_create_key"),
        sa.UniqueConstraint("workspace_id", "source_url", name="uq_leads_workspace_source"),
        schema="axiom",
    )
    op.create_index(
        "ix_leads_workspace_stage_updated",
        "leads",
        ["workspace_id", "stage", sa.text("updated_at DESC")],
        schema="axiom",
    )
    op.create_table(
        "lead_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("axiom.app_users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("changed_fields", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "lead_id"],
            ["axiom.leads.workspace_id", "axiom.leads.id"],
            ondelete="RESTRICT",
            name="fk_lead_events_workspace_lead",
        ),
        sa.CheckConstraint(
            "event_type IN ('created', 'updated', 'archived')",
            name="ck_lead_events_type",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(changed_fields) = 'array'", name="ck_lead_events_changes"
        ),
        schema="axiom",
    )
    op.create_index(
        "ix_lead_events_workspace_lead_created",
        "lead_events",
        ["workspace_id", "lead_id", sa.text("created_at DESC")],
        schema="axiom",
    )
    for table in ("leads", "lead_events"):
        op.execute(f"ALTER TABLE axiom.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_own_read ON axiom.{table} "
            f"FOR SELECT TO axiom_runtime USING ({_OWN})"
        )
        owner_only = _OWN
        if table == "lead_events":
            owner_only += " AND actor_id = axiom.current_subject()"
        op.execute(
            f"CREATE POLICY {table}_own_insert ON axiom.{table} "
            f"FOR INSERT TO axiom_runtime WITH CHECK ({owner_only})"
        )
    op.execute(
        "CREATE POLICY leads_own_update ON axiom.leads "
        f"FOR UPDATE TO axiom_runtime USING ({_OWN}) WITH CHECK ({_OWN})"
    )
    op.execute("GRANT SELECT ON axiom.leads TO axiom_runtime")
    op.execute(
        "GRANT INSERT (id, workspace_id, title, source_url, source_excerpt, "
        "stage, note, follow_up_at, follow_up_done, unsent_draft, "
        "create_key, create_fingerprint) ON axiom.leads TO axiom_runtime"
    )
    op.execute(
        "GRANT UPDATE (stage, note, follow_up_at, follow_up_done, "
        "unsent_draft, archived_at, version, updated_at) "
        "ON axiom.leads TO axiom_runtime"
    )
    op.execute("GRANT SELECT ON axiom.lead_events TO axiom_runtime")
    op.execute(
        "GRANT INSERT (id, workspace_id, lead_id, actor_id, "
        "event_type, changed_fields) ON axiom.lead_events TO axiom_runtime"
    )


def downgrade() -> None:
    raise RuntimeError("Saved CRM records and audit events require reviewed forward recovery")
