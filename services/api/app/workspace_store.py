"""Persistence primitives for later authorized /me and /workspaces HTTP handlers."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert

from app.auth import VerifiedPrincipal
from app.database import Database
from app.models import AppUser, Workspace, WorkspaceCreateIdempotency

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


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    created: bool
    status: str


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
            return BootstrapResult(created=inserted is not None, status=status)

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
                select(WorkspaceCreateIdempotency)
                .where(
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
                    expires_at=session.scalar(select(func.now() + timedelta(hours=24))),
                )
            )
            session.flush()
            return CreateResult(response_status=201, response_body=body, replayed=False)
