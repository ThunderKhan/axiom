"""Fail-closed domain authorization boundary for future remote MCP transport.

Not an OAuth server or a deployed endpoint. The grant resolver must read current,
server-owned, founder-consented grants on every invocation.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from app.auth import DelegatedPrincipal, VerifiedPrincipal
from app.leads_contract import LeadStage
from app.leads_store import LeadStore

Scope = Literal["research:run", "evidence:read", "crm:read", "crm:write"]
Tool = Literal[
    "discover_opportunities",
    "research_competitor",
    "assess_opportunity",
    "list_saved_leads",
    "save_lead",
]

_REQUIRED: dict[Tool, frozenset[Scope]] = {
    "discover_opportunities": frozenset({"research:run"}),
    "research_competitor": frozenset({"research:run"}),
    "assess_opportunity": frozenset({"research:run", "evidence:read"}),
    "list_saved_leads": frozenset({"crm:read"}),
    "save_lead": frozenset({"crm:write"}),
}


class McpAccessDenied(Exception):
    """No authorized tool grant; never disclose another client's grant."""


@dataclass(frozen=True, slots=True)
class ClientGrant:
    user_id: UUID
    client_id: UUID
    workspace_id: UUID
    resource: str
    scopes: frozenset[Scope]
    expires_at: datetime
    revoked: bool


GrantResolver = Callable[[UUID, UUID, UUID], ClientGrant | None]


class McpAccess:
    def __init__(self, resolve: GrantResolver) -> None:
        self._resolve = resolve

    def require(
        self, actor: DelegatedPrincipal, workspace_id: UUID, tool: Tool
    ) -> VerifiedPrincipal:
        required = _REQUIRED.get(tool)
        if required is None or not required.issubset(actor.scopes):
            raise McpAccessDenied()
        user_id = actor.principal.user_id
        grant = self._resolve(user_id, actor.client_id, workspace_id)
        if (
            grant is None
            or grant.user_id != user_id
            or grant.client_id != actor.client_id
            or grant.workspace_id != workspace_id
            or grant.resource != actor.resource
            or grant.revoked
            or grant.expires_at.tzinfo is None
            or grant.expires_at <= datetime.now(UTC)
            or not required.issubset(grant.scopes)
        ):
            raise McpAccessDenied()
        # Write tools remain disabled until durable consent and audit are implemented.
        if tool == "save_lead":
            raise McpAccessDenied()
        return actor.principal


def list_saved_leads(
    actor: DelegatedPrincipal,
    workspace_id: UUID,
    *,
    access: McpAccess,
    leads: LeadStore,
    stage: LeadStage | None = None,
    limit: int = 20,
) -> dict[str, object]:
    """Reuse the real CRM domain read; no separate or privileged data access."""
    principal = access.require(actor, workspace_id, "list_saved_leads")
    return leads.list(principal, workspace_id, stage=stage, limit=limit)
