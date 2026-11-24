"""Actual isolated PostgreSQL RLS and consent revocation checks."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.auth import DelegatedPrincipal, VerifiedPrincipal
from app.database import Database
from app.leads_store import LeadStore
from app.mcp_access import McpAccess, McpAccessDenied, list_saved_leads
from app.mcp_grants import McpGrantStore
from app.settings import RuntimeSettings
from app.workspace_store import WorkspaceStore

pytestmark = pytest.mark.postgres
RESOURCE = "https://api.example.org/mcp"


@pytest.fixture(scope="module")
def database():
    raw = os.environ.get("AXIOM_TEST_RUNTIME_DATABASE_URL")
    if not raw:
        pytest.skip("Only isolated PostgreSQL runtime credentials are accepted")
    instance = Database(RuntimeSettings(database_url=raw, database_required=True))
    yield instance
    instance.close()


def test_durable_consent_resolves_only_current_owner_and_cannot_reactivate(database: Database):
    owner = VerifiedPrincipal(uuid4(), uuid4())
    outsider = VerifiedPrincipal(uuid4(), uuid4())
    workspaces = WorkspaceStore(database)
    workspaces.bootstrap(owner)
    workspaces.bootstrap(outsider)
    workspace = UUID(
        str(
            workspaces.create_workspace(owner, name="MCP consent", key=uuid4().hex).response_body[
                "id"
            ]
        )
    )
    client_id = uuid4()
    grants = McpGrantStore(database, RESOURCE)
    actor = DelegatedPrincipal(owner, client_id, RESOURCE, frozenset({"crm:read"}))
    access = McpAccess(grants.resolve)
    with pytest.raises(McpAccessDenied):
        access.require(actor, workspace, "list_saved_leads")
    expiry = datetime.now(UTC) + timedelta(minutes=5)
    grants.record_reviewed_consent(
        owner, workspace, client_id=client_id, scopes=frozenset({"crm:read"}), expires_at=expiry
    )
    fresh = McpGrantStore(database, RESOURCE)
    assert list_saved_leads(
        actor, workspace, access=McpAccess(fresh.resolve), leads=LeadStore(database)
    ) == {"items": []}
    with pytest.raises(McpAccessDenied):
        access.require(actor, workspace, "save_lead")
    foreign = DelegatedPrincipal(outsider, client_id, RESOURCE, frozenset({"crm:read"}))
    with pytest.raises(McpAccessDenied):
        access.require(foreign, workspace, "list_saved_leads")
    with database.transaction(outsider) as session:
        assert session.scalar(text("SELECT count(*) FROM axiom.mcp_client_grants")) == 0
    assert grants.revoke(owner, workspace, client_id=client_id)
    assert not fresh.revoke(owner, workspace, client_id=client_id)
    with pytest.raises(McpAccessDenied):
        access.require(actor, workspace, "list_saved_leads")
    with pytest.raises(McpAccessDenied):
        grants.record_reviewed_consent(
            owner, workspace, client_id=client_id, scopes=frozenset({"crm:read"}), expires_at=expiry
        )
    with database.transaction(owner) as session:
        result = session.execute(
            text("UPDATE axiom.mcp_client_grants SET revoked_at = NULL WHERE client_id = :client"),
            {"client": client_id},
        )
        assert result.rowcount == 0
    with pytest.raises(DBAPIError):
        with database.transaction(owner) as session:
            session.execute(text("UPDATE axiom.mcp_client_grants SET scopes = '[]'::jsonb"))
