"""Link saved CRM opportunities to immutable reviewed feed runs.

Revision ID: m7_0001_lead_provenance
Revises: m6_0001_research_runs
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m7_0001_lead_provenance"
down_revision: str | None = "m6_0001_research_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_research_run_workspace_id", "research_runs", ["workspace_id", "id"], schema="axiom"
    )
    op.add_column(
        "leads", sa.Column("research_run_id", postgresql.UUID(as_uuid=True)), schema="axiom"
    )
    op.add_column(
        "leads", sa.Column("research_signal_id", postgresql.UUID(as_uuid=True)), schema="axiom"
    )
    op.drop_constraint("ck_leads_origin", "leads", schema="axiom", type_="check")
    op.create_check_constraint(
        "ck_leads_origin",
        "leads",
        "(source_origin = 'user_provided' AND research_run_id IS NULL "
        "AND research_signal_id IS NULL) OR (source_origin = 'live' "
        "AND research_run_id IS NOT NULL AND research_signal_id IS NOT NULL)",
        schema="axiom",
    )
    op.create_foreign_key(
        "fk_leads_research_run",
        "leads",
        "research_runs",
        ["workspace_id", "research_run_id"],
        ["workspace_id", "id"],
        source_schema="axiom",
        referent_schema="axiom",
        ondelete="RESTRICT",
    )
    op.execute(
        "GRANT INSERT (source_origin, research_run_id, research_signal_id) "
        "ON axiom.leads TO axiom_runtime"
    )


def downgrade() -> None:
    raise RuntimeError("Research-linked lead provenance requires reviewed forward recovery")
