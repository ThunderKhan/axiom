"""Bounded, owner-bound, versioned keyset cursor; never an authorization credential."""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,512}$")
_FIELDS = frozenset({"v", "owner", "limit", "at", "id"})


class InvalidCursor(ValueError):
    """Malformed, unrelated or expired cursor: fail with the same safe validation error."""


@dataclass(frozen=True, slots=True)
class WorkspaceCursor:
    created_at: datetime
    workspace_id: UUID


def encode_cursor(
    owner_id: UUID, *, limit: int, created_at: datetime, workspace_id: UUID
) -> str:
    if created_at.tzinfo is None:
        raise ValueError("UTC timestamp required for pagination")
    value = {
        "v": 1,
        "owner": str(owner_id),
        "limit": limit,
        "at": created_at.astimezone(timezone.utc).isoformat(),
        "id": str(workspace_id),
    }
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(value: str, *, owner_id: UUID, limit: int) -> WorkspaceCursor:
    """Parse an opaque hint, then require a real owned anchor in the DB query.

    Owner/query matching here is defense in depth. No client cursor is allowed
    to choose the repository's owner scope, even when modified or forged.
    """
    if not isinstance(value, str) or _PATTERN.fullmatch(value) is None:
        raise InvalidCursor()
    try:
        raw = base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)
        if base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=") != value:
            raise InvalidCursor()
        data = json.loads(raw)
        if not isinstance(data, dict) or frozenset(data) != _FIELDS:
            raise InvalidCursor()
        if type(data["v"]) is not int or data["v"] != 1:
            raise InvalidCursor()
        if type(data["limit"]) is not int or data["limit"] != limit:
            raise InvalidCursor()
        if str(UUID(data["owner"])) != str(owner_id):
            raise InvalidCursor()
        if not isinstance(data["id"], str) or str(UUID(data["id"])) != data["id"]:
            raise InvalidCursor()
        if not isinstance(data["at"], str) or len(data["at"]) > 48:
            raise InvalidCursor()
        at = datetime.fromisoformat(data["at"])
        if at.tzinfo is None or at.utcoffset() != timezone.utc.utcoffset(None):
            raise InvalidCursor()
        if at.astimezone(timezone.utc).isoformat() != data["at"]:
            raise InvalidCursor()
        return WorkspaceCursor(created_at=at, workspace_id=UUID(data["id"]))
    except (ValueError, TypeError, KeyError, UnicodeError, binascii.Error, OverflowError) as exc:
        raise InvalidCursor() from exc
