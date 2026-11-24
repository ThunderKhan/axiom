"""Durable consent persistence; no public consent or token issuance endpoint."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth import DelegatedPrincipal, VerifiedPrincipal
from app.database import Database
from app.mcp_access import ClientGrant, McpAccessDenied, Scope
from app.models import McpClientGrant, Workspace
from app.workspace_store import WorkspaceStore

_READ_SCOPES: frozenset[Scope] = frozenset({"research:run", "evidence:read", "crm:read"})


class McpGrantStore:
    def __init__(self, database: Database, resource: str) -> None:
        self.database = database
        self.resource = resource

    @staticmethod
    def _owned(session: Session, principal: VerifiedPrincipal, workspace_id: UUID) -> None:
        WorkspaceStore._active(session, principal)
        if (
            session.scalar(
                select(Workspace.id).where(
                    Workspace.id == workspace_id, Workspace.owner_user_id == principal.user_id
                )
            )
            is None
        ):
            raise McpAccessDenied()

    def record_reviewed_consent(
        self,
        principal: VerifiedPrincipal,
        workspace_id: UUID,
        *,
        client_id: UUID,
        scopes: frozenset[Scope],
        expires_at: datetime,
    ) -> None:
        """Internal broker handoff ONLY after verified client registration and consent.

        Not callable by a delegated client or exposed as an HTTP operation.
        A revoked or expired identity cannot be silently re-granted by this slice.
        """
        now = datetime.now(UTC)
        if (
            principal.session_id is None
            or client_id.int == 0
            or not scopes
            or not scopes.issubset(_READ_SCOPES)
            or expires_at.tzinfo is None
            or not now < expires_at <= now + timedelta(days=30)
        ):
            raise McpAccessDenied()
        with self.database.transaction(principal) as session:
            self._owned(session, principal, workspace_id)
            result = session.execute(
                insert(McpClientGrant)
                .values(
                    user_id=principal.user_id,
                    workspace_id=workspace_id,
                    client_id=client_id,
                    resource=self.resource,
                    scopes=sorted(scopes),
                    expires_at=expires_at,
                )
                .on_conflict_do_nothing()
                .returning(McpClientGrant.client_id)
            ).scalar_one_or_none()
            if result is None:
                raise McpAccessDenied()

    def resolve(self, actor: DelegatedPrincipal, workspace_id: UUID) -> ClientGrant | None:
        if actor.resource != self.resource:
            return None
        with self.database.transaction(actor.principal) as session:
            self._owned(session, actor.principal, workspace_id)
            row = session.get(
                McpClientGrant,
                (actor.principal.user_id, actor.client_id, workspace_id, self.resource),
            )
            if row is None:
                return None
            scopes = frozenset(scope for scope in _READ_SCOPES if scope in row.scopes)
            if len(scopes) != len(row.scopes):
                return None
            return ClientGrant(
                row.user_id,
                row.client_id,
                row.workspace_id,
                row.resource,
                scopes,
                row.expires_at,
                row.revoked_at is not None,
            )

    def revoke(self, principal: VerifiedPrincipal, workspace_id: UUID, *, client_id: UUID) -> bool:
        """One-way, owner-scoped revocation; no scope or identity mutation."""
        with self.database.transaction(principal) as session:
            self._owned(session, principal, workspace_id)
            changed = session.execute(
                update(McpClientGrant)
                .where(
                    McpClientGrant.user_id == principal.user_id,
                    McpClientGrant.client_id == client_id,
                    McpClientGrant.workspace_id == workspace_id,
                    McpClientGrant.resource == self.resource,
                    McpClientGrant.revoked_at.is_(None),
                )
                .values(revoked_at=datetime.now(UTC))
                .returning(McpClientGrant.client_id)
            ).scalar_one_or_none()
            return changed is not None
