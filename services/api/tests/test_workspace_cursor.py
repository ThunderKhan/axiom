"""Deterministic M1 owner/query cursor validation without database access."""

from __future__ import annotations

import base64
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.workspace_cursor import InvalidCursor, decode_cursor, encode_cursor


def test_keyset_cursor_roundtrip_is_versioned_and_owner_bound() -> None:
    a, b, workspace = uuid4(), uuid4(), uuid4()
    at = datetime(2026, 11, 19, 12, 30, 9, 12345, tzinfo=UTC)
    cursor = encode_cursor(a, limit=2, created_at=at, workspace_id=workspace)
    assert cursor.isascii() and "/" not in cursor and "=" not in cursor
    decoded = decode_cursor(cursor, owner_id=a, limit=2)
    assert decoded.workspace_id == workspace
    assert decoded.created_at == at
    with pytest.raises(InvalidCursor):
        decode_cursor(cursor, owner_id=b, limit=2)
    with pytest.raises(InvalidCursor):
        decode_cursor(cursor, owner_id=a, limit=10)


@pytest.mark.parametrize(
    "value",
    ["", "!", "//evil", "x" * 513, "abc=", "e30", "not_base64", "%2f", "😇"],
)
def test_cursor_rejects_malformed_data(value: str) -> None:
    with pytest.raises(InvalidCursor):
        decode_cursor(value, owner_id=uuid4(), limit=20)


def test_malformed_and_modified_cursors_are_rejected() -> None:
    a, ws = uuid4(), uuid4()
    at = datetime.now(UTC)
    value = encode_cursor(a, limit=20, created_at=at, workspace_id=ws)
    body = json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))
    for change in (
        {"v": 99},
        {"owner": str(uuid4())},
        {"owner": 1},
        {"owner": True},
        {"owner": None},
        {"owner": []},
        {"owner": {}},
        {"at": (at + timedelta(seconds=1)).replace(tzinfo=None).isoformat()},
        {"at": "2026-01-01T12:00:00+03:00"},
        {"id": "bad-id"},
        {"limit": True},
        {"extra": "unapproved"},
    ):
        modified = {**body, **change}
        data = (
            base64.urlsafe_b64encode(json.dumps(modified, separators=(",", ":")).encode())
            .decode()
            .rstrip("=")
        )
        with pytest.raises(InvalidCursor):
            decode_cursor(data, owner_id=a, limit=20)
    with pytest.raises(ValueError):
        encode_cursor(a, limit=20, created_at=datetime.now(), workspace_id=ws)
