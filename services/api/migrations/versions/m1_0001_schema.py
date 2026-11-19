"""Create minimal M1 account, workspace and committed-create records.

Revision ID: m1_0001_schema
Revises:
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m1_0001_schema"
down_revision: str | None = None
branch_labels = None
depends_on = None

_NAME_CHECK = (
    "char_length(name) BETWEEN 1 AND 120 "
    (
        r"AND name = btrim(name, U&'\0009\000A\000B\000C\000D\001C\0"
        r"01D\001E\001F\0020\0085\00A0\1680\2000\2001\2002\2003\2004"
        r"\2005\2006\2007\2008\2009\200A\2028\2029\202F\205F\3000') "
    )
    + "AND name !~ '[[:cntrl:]]'"
)


def upgrade() -> None:
    op.execute("CREATE SCHEMA axiom")
    op.create_table(
        "app_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'active'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('active', 'suspended', 'deprovisioned')", name="ck_app_users_status"
        ),
        schema="axiom",
    )
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "owner_user_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("axiom.app_users.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default=sa.text("1")),
        sa.CheckConstraint(_NAME_CHECK, name="ck_workspaces_name"),
        sa.CheckConstraint("version >= 1", name="ck_workspaces_version"),
        schema="axiom",
    )
    op.create_index(
        "ix_workspaces_owner_created_id",
        "workspaces",
        ["owner_user_id", sa.text("created_at DESC"), sa.text("id DESC")],
        schema="axiom",
    )
    op.create_table(
        "workspace_create_idempotency",
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.String(40), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_user_id"], ["axiom.app_users.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("owner_user_id", "operation", "key"),
        sa.CheckConstraint("operation = 'workspace.create'", name="ck_idempotency_operation"),
        sa.CheckConstraint(
            "char_length(key) BETWEEN 8 AND 128 AND key ~ '^[A-Za-z0-9][A-Za-z0-9_-]*$'",
            name="ck_idempotency_key",
        ),
        sa.CheckConstraint(
            "char_length(fingerprint) = 64 AND fingerprint ~ '^[0-9a-f]+$'",
            name="ck_idempotency_fingerprint",
        ),
        sa.CheckConstraint("response_status = 201", name="ck_idempotency_response_status"),
        sa.CheckConstraint(
            "expires_at >= created_at + interval '24 hours'",
            name="ck_idempotency_retention",
        ),
        schema="axiom",
    )


def downgrade() -> None:
    raise RuntimeError(
        "M1 schema downgrade would destroy owned user/workspace data; use a reviewed forward fix"
    )
