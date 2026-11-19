"""Persistence primitives for later authorized /me and /workspaces HTTP handlers."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert

from app.auth import VerifiedPrincipal
from app.database import Database
from app.models import AppUser, Workspace, WorkspaceCreateIdempotency
from app.workspace_cursor import InvalidCursor, decode_cursor, encode_cursor

_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$")
_OPERATION = "workspace.create"


class AccountDisabled(Exception):
    """The cryptographically verified identity has been explicitly disabled."""


class ProvisioningRequired(Exception):
    """The account must be explicitly bootstrapped before domain operations."""


class IdempotencyConflict(Exception):
    """A previously committed key was used with a different canonical request."""


class InvalidWorkspaceInput(ValueError):
    """A malformed name or key must never enter the database."""


class WorkspaceNotFound(Exception):
    """Both foreign and absent IDs must use the identical public 404."""


class VersionConflict(Exception):
    """The caller owns a workspace but supplied a stale version."""


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    created: bool
    status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CreateResult:
    response_status: int
    response_body: dict[str, object]
    replayed: bool


def canonical_name(value: str) -> str:
    if not isinstance(value, str):
        raise InvalidWorkspaceInput("A workspace name is required")
    name = value.strip()
    if not 1 <= len(name) <= 120 or any(
        unicodedata.category(char) in {"Cc", "Cs"} for char in name
    ):
        raise InvalidWorkspaceInput("Workspace name must be 1–120 safe characters")
    return name


def _response(workspace: Workspace) -> dict[str, object]:
    return {
        "id": str(workspace.id),
        "name": workspace.name,
        "created_at": workspace.created_at.isoformat(),
        "updated_at": workspace.updated_at.isoformat(),
        "version": workspace.version,
    }


class WorkspaceStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _active(session: Any, principal: VerifiedPrincipal) -> None:
        status = session.scalar(select(AppUser.status).where(AppUser.id == principal.user_id))
        if status is None:
            raise ProvisioningRequired()
        if status != "active":
            raise AccountDisabled()

    def bootstrap(self, principal: VerifiedPrincipal) -> BootstrapResult:
        with self.database.transaction(principal) as session:
            inserted = session.execute(
                insert(AppUser)
                .values(id=principal.user_id)
                .on_conflict_do_nothing(index_elements=[AppUser.id])
                .returning(AppUser.id)
            ).scalar_one_or_none()
            status = session.scalar(select(AppUser.status).where(AppUser.id == principal.user_id))
            if status != "active":
                raise AccountDisabled()
            created_at = session.scalar(
                select(AppUser.created_at).where(AppUser.id == principal.user_id)
            )
            assert created_at is not None
            return BootstrapResult(
                created=inserted is not None, status=status, created_at=created_at
            )

    def get_user(self, principal: VerifiedPrincipal) -> dict[str, object]:
        """Strictly read-only identity lookup; never auto-bootstrap a missing row."""
        with self.database.transaction(principal) as session:
            user = session.scalar(select(AppUser).where(AppUser.id == principal.user_id))
            if user is None:
                raise ProvisioningRequired()
            if user.status != "active":
                raise AccountDisabled()
            return {
                "id": str(user.id),
                "status": user.status,
                "created_at": user.created_at.isoformat(),
            }

    def get_workspace(self, principal: VerifiedPrincipal, workspace_id: UUID) -> dict[str, object]:
        """Explicit owner predicate even if a privileged DB login could bypass RLS."""
        with self.database.transaction(principal) as session:
            self._active(session, principal)
            workspace = session.scalar(
                select(Workspace).where(
                    Workspace.id == workspace_id, Workspace.owner_user_id == principal.user_id
                )
            )
            if workspace is None:
                raise WorkspaceNotFound()
            return _response(workspace)

    def page_workspaces(
        self, principal: VerifiedPrincipal, *, limit: int = 20, cursor: str | None = None
    ) -> dict[str, object]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise InvalidWorkspaceInput("Invalid workspace limit")
        bookmark = (
            decode_cursor(cursor, owner_id=principal.user_id, limit=limit)
            if cursor is not None
            else None
        )
        with self.database.transaction(principal) as session:
            self._active(session, principal)
            if bookmark is not None:
                # An encoded value is only a hint. Validate its *real* anchor
                # belongs to the verified user and matches the issued ordering key.
                anchor_at = session.scalar(
                    select(Workspace.created_at).where(
                        Workspace.id == bookmark.workspace_id,
                        Workspace.owner_user_id == principal.user_id,
                    )
                )
                if anchor_at is None or anchor_at.astimezone(UTC) != bookmark.created_at:
                    raise InvalidCursor()
            query = select(Workspace).where(Workspace.owner_user_id == principal.user_id)
            if bookmark is not None:
                query = query.where(
                    or_(
                        Workspace.created_at < bookmark.created_at,
                        and_(
                            Workspace.created_at == bookmark.created_at,
                            Workspace.id < bookmark.workspace_id,
                        ),
                    )
                )
            rows = session.scalars(
                query.order_by(Workspace.created_at.desc(), Workspace.id.desc()).limit(limit + 1)
            ).all()
            items = rows[:limit]
            next_cursor = (
                encode_cursor(
                    principal.user_id,
                    limit=limit,
                    created_at=items[-1].created_at,
                    workspace_id=items[-1].id,
                )
                if len(rows) > limit
                else None
            )
            return {"items": [_response(item) for item in items], "next_cursor": next_cursor}

    def update_workspace(
        self, principal: VerifiedPrincipal, workspace_id: UUID, *, name: str, expected_version: int
    ) -> dict[str, object]:
        normalized = canonical_name(name)
        if type(expected_version) is not int or not 1 <= expected_version <= 9223372036854775807:
            raise InvalidWorkspaceInput("Invalid expected workspace version")
        with self.database.transaction(principal) as session:
            self._active(session, principal)
            # Foreign and nonexistent objects must be indistinguishable, even
            # if the connection is unexpectedly privileged and bypasses RLS.
            owned = session.scalar(
                select(Workspace.id).where(
                    Workspace.id == workspace_id, Workspace.owner_user_id == principal.user_id
                )
            )
            if owned is None:
                raise WorkspaceNotFound()
            updated = session.scalars(
                update(Workspace)
                .where(
                    Workspace.id == workspace_id,
                    Workspace.owner_user_id == principal.user_id,
                    Workspace.version == expected_version,
                )
                .values(
                    name=normalized,
                    version=Workspace.version + 1,
                    updated_at=func.clock_timestamp(),
                )
                .returning(Workspace)
            ).one_or_none()
            if updated is None:
                # The atomic UPDATE precondition failed: no last-write-wins.
                # The existence check has already confirmed verified ownership.
                raise VersionConflict()
            return _response(updated)

    def list_workspaces(
        self, principal: VerifiedPrincipal, *, limit: int = 20
    ) -> list[dict[str, object]]:
        if not 1 <= limit <= 100:
            raise InvalidWorkspaceInput("Invalid workspace limit")
        with self.database.transaction(principal) as session:
            self._active(session, principal)
            workspaces = session.scalars(
                select(Workspace)
                .where(Workspace.owner_user_id == principal.user_id)
                .order_by(Workspace.created_at.desc(), Workspace.id.desc())
                .limit(limit)
            ).all()
            return [_response(item) for item in workspaces]

    def create_workspace(
        self, principal: VerifiedPrincipal, *, name: str, key: str
    ) -> CreateResult:
        normalized = canonical_name(name)
        if not isinstance(key, str) or _KEY_PATTERN.fullmatch(key) is None:
            raise InvalidWorkspaceInput("Invalid idempotency key")
        fingerprint = hashlib.sha256(
            json.dumps({"name": normalized}, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        # A deterministic, owner-scoped transaction advisory lock serializes competing
        # requests for the same key across process replicas and protects replay atomicity.
        digest = hashlib.sha256(f"{principal.user_id}:{_OPERATION}:{key}".encode("ascii")).digest()
        advisory_key = int.from_bytes(digest[:8], "big", signed=True)
        with self.database.transaction(principal) as session:
            self._active(session, principal)
            session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": advisory_key})
            existing = session.scalar(
                select(WorkspaceCreateIdempotency).where(
                    WorkspaceCreateIdempotency.owner_user_id == principal.user_id,
                    WorkspaceCreateIdempotency.operation == _OPERATION,
                    WorkspaceCreateIdempotency.key == key,
                )
            )
            if existing is not None:
                if existing.fingerprint != fingerprint:
                    raise IdempotencyConflict()
                return CreateResult(
                    response_status=existing.response_status,
                    response_body=existing.response_body,
                    replayed=True,
                )
            workspace = Workspace(id=uuid4(), owner_user_id=principal.user_id, name=normalized)
            session.add(workspace)
            session.flush()
            body = _response(workspace)
            session.add(
                WorkspaceCreateIdempotency(
                    owner_user_id=principal.user_id,
                    operation=_OPERATION,
                    key=key,
                    fingerprint=fingerprint,
                    response_status=201,
                    response_body=body,
                    expires_at=session.scalar(
                        select(func.clock_timestamp() + text("interval '25 hours'"))
                    ),
                )
            )
            session.flush()
            return CreateResult(response_status=201, response_body=body, replayed=False)
