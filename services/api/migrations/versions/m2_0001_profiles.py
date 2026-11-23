"""Versioned, owner-scoped product profiles and resumable onboarding drafts.

Revision ID: m2_0001_profiles
Revises: m1_0002_rls
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m2_0001_profiles"
down_revision: str | None = "m1_0002_rls"
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
        "product_profiles",
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("axiom.workspaces.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("draft_revision", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("confirmed_revision", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "draft_answers",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("draft_revision >= 0", name="ck_profile_draft_revision"),
        sa.CheckConstraint("confirmed_revision >= 0", name="ck_profile_confirmed_revision"),
        sa.CheckConstraint(
            "jsonb_typeof(draft_answers) = 'object'", name="ck_profile_draft_object"
        ),
        schema="axiom",
    )
    op.create_table(
        "profile_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("axiom.product_profiles.workspace_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.Column("answers", postgresql.JSONB(), nullable=False),
        sa.Column(
            "confirmed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("revision >= 1", name="ck_profile_version_revision"),
        sa.CheckConstraint("jsonb_typeof(answers) = 'object'", name="ck_profile_version_object"),
        sa.UniqueConstraint(
            "workspace_id", "revision", name="uq_profile_version_workspace_revision"
        ),
        schema="axiom",
    )
    for table in ("product_profiles", "profile_versions"):
        op.execute(f"ALTER TABLE axiom.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_own_read ON axiom.{table} "
            f"FOR SELECT TO axiom_runtime USING ({_OWN})"
        )
        op.execute(
            f"CREATE POLICY {table}_own_insert ON axiom.{table} "
            f"FOR INSERT TO axiom_runtime WITH CHECK ({_OWN})"
        )
    op.execute(
        "CREATE POLICY product_profiles_own_update ON axiom.product_profiles "
        f"FOR UPDATE TO axiom_runtime USING ({_OWN}) WITH CHECK ({_OWN})"
    )
    op.execute("GRANT SELECT ON axiom.product_profiles TO axiom_runtime")
    op.execute(
        "GRANT INSERT (workspace_id, draft_revision, confirmed_revision, draft_answers) "
        "ON axiom.product_profiles TO axiom_runtime"
    )
    op.execute(
        "GRANT UPDATE (draft_revision, confirmed_revision, draft_answers, updated_at) "
        "ON axiom.product_profiles TO axiom_runtime"
    )
    op.execute("GRANT SELECT ON axiom.profile_versions TO axiom_runtime")
    op.execute(
        "GRANT INSERT (id, workspace_id, revision, answers) "
        "ON axiom.profile_versions TO axiom_runtime"
    )


def downgrade() -> None:
    raise RuntimeError("Confirmed founder profiles are immutable; use a reviewed forward fix")
