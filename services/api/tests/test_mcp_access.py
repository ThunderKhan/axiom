"""Domain scope policy tests; not an external OAuth/MCP transport test."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from app.auth import DelegatedPrincipal, VerifiedPrincipal
from app.leads_store import LeadStore
from app.mcp_access import ClientGrant, McpAccess, McpAccessDenied, list_saved_leads

RESOURCE = "https://api.example.org/mcp"


def test_read_scope_workspace_binding_and_revocation_are_checked_on_each_call() -> None:
    actor = DelegatedPrincipal(VerifiedPrincipal(uuid4(), uuid4()), uuid4(), RESOURCE)
    workspace = uuid4()
    valid = ClientGrant(
        actor.principal.user_id,
        actor.client_id,
        workspace,
        RESOURCE,
        frozenset({"crm:read"}),
        datetime.now(UTC) + timedelta(minutes=5),
        False,
    )
    current: list[ClientGrant | None] = [valid]
    access = McpAccess(lambda user, client, wid: current[0])
    leads = Mock(spec=LeadStore)
    leads.list.return_value = {"items": []}
    assert list_saved_leads(actor, workspace, access=access, leads=leads) == {"items": []}
    leads.list.assert_called_once_with(actor.principal, workspace, stage=None, limit=20)
    leads.reset_mock()
    for wrong_workspace in (uuid4(),):
        with pytest.raises(McpAccessDenied):
            list_saved_leads(actor, wrong_workspace, access=access, leads=leads)
    with pytest.raises(McpAccessDenied):
        access.require(actor, workspace, "research_competitor")
    with pytest.raises(McpAccessDenied):
        access.require(actor, workspace, "save_lead")
    current[0] = None
    with pytest.raises(McpAccessDenied):
        list_saved_leads(actor, workspace, access=access, leads=leads)
    leads.list.assert_not_called()


def test_even_explicit_write_scope_cannot_enable_unreviewed_write_tool() -> None:
    actor = DelegatedPrincipal(VerifiedPrincipal(uuid4(), uuid4()), uuid4(), RESOURCE)
    workspace = uuid4()
    grant = ClientGrant(
        actor.principal.user_id,
        actor.client_id,
        workspace,
        RESOURCE,
        frozenset({"crm:write"}),
        datetime.now(UTC) + timedelta(minutes=5),
        False,
    )
    with pytest.raises(McpAccessDenied):
        McpAccess(lambda user, client, wid: grant).require(actor, workspace, "save_lead")
