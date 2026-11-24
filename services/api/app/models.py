"""Owner-approved M1 persistence models. Alembic is the only schema writer."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    MetaData,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

SCHEMA = "axiom"
HEAD_REVISION = "m5_0001_mcp_consent"
# PostgreSQL's U& literal enumerates Python str.strip() whitespace codepoints.
_TRIM = (
    r"U&'\0009\000A\000B\000C\000D\001C\001D\001E\001F\0020\0085\0"
    r"0A0\1680\2000\2001\2002\2003\2004\2005\2006\2007\2008\2009\2"
    r"00A\2028\2029\202F\205F\3000'"
)
NAME_CHECK = (
    f"char_length(name) BETWEEN 1 AND 120 AND name = btrim(name, {_TRIM}) AND name !~ '[[:cntrl:]]'"
)


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA)


class AppUser(Base):
    __tablename__ = "app_users"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'suspended', 'deprovisioned')",
            name="ck_app_users_status",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Workspace(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        CheckConstraint(NAME_CHECK, name="ck_workspaces_name"),
        CheckConstraint("version >= 1", name="ck_workspaces_version"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    owner_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("axiom.app_users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("1"))


Index(
    "ix_workspaces_owner_created_id",
    Workspace.owner_user_id,
    Workspace.created_at.desc(),
    Workspace.id.desc(),
)


class WorkspaceCreateIdempotency(Base):
    __tablename__ = "workspace_create_idempotency"
    __table_args__ = (
        CheckConstraint("operation = 'workspace.create'", name="ck_idempotency_operation"),
        CheckConstraint(
            "char_length(key) BETWEEN 8 AND 128 AND key ~ '^[A-Za-z0-9][A-Za-z0-9_-]*$'",
            name="ck_idempotency_key",
        ),
        CheckConstraint(
            "char_length(fingerprint) = 64 AND fingerprint ~ '^[0-9a-f]+$'",
            name="ck_idempotency_fingerprint",
        ),
        CheckConstraint("response_status = 201", name="ck_idempotency_response_status"),
        CheckConstraint(
            "expires_at >= created_at + interval '24 hours'",
            name="ck_idempotency_retention",
        ),
    )

    owner_user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("axiom.app_users.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    operation: Mapped[str] = mapped_column(String(40), primary_key=True)
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    response_status: Mapped[int] = mapped_column(nullable=False)
    response_body: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProductProfile(Base):
    """One mutable onboarding draft per owned workspace; confirmed versions are append-only."""

    __tablename__ = "product_profiles"
    __table_args__ = (
        CheckConstraint("draft_revision >= 0", name="ck_profile_draft_revision"),
        CheckConstraint("draft_step BETWEEN 0 AND 14", name="ck_profile_draft_step"),
        CheckConstraint("confirmed_revision >= 0", name="ck_profile_confirmed_revision"),
        CheckConstraint("jsonb_typeof(draft_answers) = 'object'", name="ck_profile_draft_object"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("axiom.workspaces.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    draft_revision: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    draft_step: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("0"))
    confirmed_revision: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text("0")
    )
    draft_answers: Mapped[dict[str, object]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProfileVersion(Base):
    """Immutable, owner-scoped founder-confirmed profile snapshot."""

    __tablename__ = "profile_versions"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="ck_profile_version_revision"),
        CheckConstraint("jsonb_typeof(answers) = 'object'", name="ck_profile_version_object"),
        UniqueConstraint("workspace_id", "revision", name="uq_profile_version_workspace_revision"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("axiom.product_profiles.workspace_id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    answers: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Lead(Base):
    """One workspace-owned, idempotent manual-source opportunity, never a verified live signal."""

    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint(
            "stage IN ('spotted', 'qualified', 'contacted', 'closed_lost')",
            name="ck_leads_stage",
        ),
        CheckConstraint(
            "char_length(title) BETWEEN 1 AND 180 AND btrim(title) <> ''",
            name="ck_leads_title",
        ),
        CheckConstraint("char_length(source_url) <= 2048", name="ck_leads_source_url"),
        CheckConstraint("char_length(source_excerpt) BETWEEN 1 AND 500", name="ck_leads_excerpt"),
        CheckConstraint("char_length(note) <= 2000", name="ck_leads_note"),
        CheckConstraint("char_length(unsent_draft) <= 4000", name="ck_leads_draft"),
        CheckConstraint("version >= 1", name="ck_leads_version"),
        CheckConstraint(
            "NOT follow_up_done OR follow_up_at IS NOT NULL", name="ck_leads_followup_state"
        ),
        CheckConstraint("source_origin = 'user_provided'", name="ck_leads_origin"),
        CheckConstraint(
            "char_length(create_key) BETWEEN 8 AND 128 "
            "AND create_key ~ '^[A-Za-z0-9][A-Za-z0-9_-]*$'",
            name="ck_leads_create_key",
        ),
        CheckConstraint(
            "char_length(create_fingerprint) = 64 AND create_fingerprint ~ '^[0-9a-f]+$'",
            name="ck_leads_fingerprint",
        ),
        UniqueConstraint("workspace_id", "id", name="uq_leads_workspace_id"),
        UniqueConstraint("workspace_id", "create_key", name="uq_leads_workspace_create_key"),
        UniqueConstraint("workspace_id", "source_url", name="uq_leads_workspace_source"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("axiom.workspaces.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_excerpt: Mapped[str] = mapped_column(Text, nullable=False)
    source_origin: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'user_provided'")
    )
    stage: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'spotted'"))
    note: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    follow_up_done: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    unsent_draft: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    create_key: Mapped[str] = mapped_column(String(128), nullable=False)
    create_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("1"))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


Index(
    "ix_leads_workspace_stage_updated",
    Lead.workspace_id,
    Lead.stage,
    Lead.updated_at.desc(),
)


class LeadEvent(Base):
    """Append-only metadata history, never copies of private notes or drafts."""

    __tablename__ = "lead_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "lead_id"],
            ["axiom.leads.workspace_id", "axiom.leads.id"],
            ondelete="RESTRICT",
            name="fk_lead_events_workspace_lead",
        ),
        CheckConstraint(
            "event_type IN ('created', 'updated', 'archived')",
            name="ck_lead_events_type",
        ),
        CheckConstraint(
            "jsonb_typeof(changed_fields) = 'array'",
            name="ck_lead_events_changes",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    lead_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("axiom.app_users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_fields: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


Index(
    "ix_lead_events_workspace_lead_created",
    LeadEvent.workspace_id,
    LeadEvent.lead_id,
    LeadEvent.created_at.desc(),
)


class ScenarioComparison(Base):
    """Append-only comparison and exact evidence snapshot for one owned lead."""

    __tablename__ = "scenario_comparisons"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "lead_id"],
            ["axiom.leads.workspace_id", "axiom.leads.id"],
            ondelete="RESTRICT",
            name="fk_scenario_comparison_lead",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "profile_revision"],
            ["axiom.profile_versions.workspace_id", "axiom.profile_versions.revision"],
            ondelete="RESTRICT",
            name="fk_scenario_comparison_profile",
        ),
        UniqueConstraint("workspace_id", "create_key", name="uq_scenario_comparison_workspace_key"),
        CheckConstraint("lead_version >= 1", name="ck_scenario_comparison_lead_version"),
        CheckConstraint("profile_revision >= 1", name="ck_scenario_comparison_profile_revision"),
        CheckConstraint(
            "char_length(create_key) BETWEEN 8 AND 128 "
            "AND create_key ~ '^[A-Za-z0-9][A-Za-z0-9_-]*$'",
            name="ck_scenario_comparison_key",
        ),
        CheckConstraint(
            "char_length(create_fingerprint) = 64 AND create_fingerprint ~ '^[0-9a-f]+$'",
            name="ck_scenario_comparison_fingerprint",
        ),
        CheckConstraint(
            "jsonb_typeof(snapshot) = 'object' AND octet_length(snapshot::text) <= 65536",
            name="ck_scenario_comparison_snapshot",
        ),
        CheckConstraint(
            "jsonb_typeof(result) = 'object' AND octet_length(result::text) <= 262144",
            name="ck_scenario_comparison_result",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    lead_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), nullable=False)
    lead_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    profile_revision: Mapped[int] = mapped_column(BigInteger, nullable=False)
    create_key: Mapped[str] = mapped_column(String(128), nullable=False)
    create_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


Index(
    "ix_scenario_comparison_workspace_lead_created",
    ScenarioComparison.workspace_id,
    ScenarioComparison.lead_id,
    ScenarioComparison.created_at.desc(),
)


class McpClientGrant(Base):
    """Durable read-only consent; a revoked grant cannot be reactivated."""

    __tablename__ = "mcp_client_grants"
    __table_args__ = (
        CheckConstraint(
            "jsonb_typeof(scopes) = 'array' AND jsonb_array_length(scopes) BETWEEN 1 AND 3 "
            'AND scopes <@ \'["research:run","evidence:read","crm:read"]\'::jsonb',
            name="ck_mcp_grant_scopes",
        ),
        CheckConstraint(
            "char_length(resource) BETWEEN 1 AND 256 AND resource LIKE 'https://%/mcp'",
            name="ck_mcp_grant_resource",
        ),
        CheckConstraint("expires_at > created_at", name="ck_mcp_grant_expiry"),
        CheckConstraint(
            "revoked_at IS NULL OR revoked_at >= created_at",
            name="ck_mcp_grant_revocation",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("axiom.app_users.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    client_id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("axiom.workspaces.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    resource: Mapped[str] = mapped_column(String(256), primary_key=True)
    scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
