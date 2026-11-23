"""Pure input contracts: no live-source claims, invalid time or unsafe draft inputs."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.leads_contract import CreateLead, PatchLead, validate_idempotency_key


def example(**changes: object) -> dict[str, object]:
    return {
        "title": "Founder seeks evidence",
        "source_url": "https://example.org/research/123",
        "source_excerpt": "Customers request a verifiable source",
        **changes,
    }


def test_create_accepts_declared_public_source_and_never_assigns_verified_origin() -> None:
    value = CreateLead.model_validate(
        example(follow_up_at=datetime(2026, 11, 26, tzinfo=UTC), follow_up_done=True)
    )
    assert value.stage == "spotted"
    assert value.unsent_draft == ""
    assert value.follow_up_done is True
    assert "source_origin" not in value.model_fields_set
    assert value.source_url.startswith("https://")


@pytest.mark.parametrize(
    "source_url",
    [
        "https://",
        "https://user:secret@example.org/",
        "https://example.org:9999/",
        "https://example.org/#fragment",
        "https://not a host.org/path",
        "https://example.org/\x00",
        "http://example.org/path",
        "https://example.org\\@internal/",
        "https://localhost/private",
        "https://localhost./private",
        "https://127.1/private",
        "https://2130706433/private",
        "https://127.0.0.1/private",
        "https://192.168.1.1/admin",
        "https://metadata.google.internal/path",
    ],
)
def test_rejects_invalid_or_secret_bearing_source_authorities(source_url: str) -> None:
    with pytest.raises(ValidationError):
        CreateLead.model_validate(example(source_url=source_url))


@pytest.mark.parametrize(
    "changes",
    [
        {"title": " \t "},
        {"title": "Line\nbreak"},
        {"note": "binary\x00content"},
        {"unsent_draft": "X" * 4001},
        {"source_excerpt": ""},
        {"source_excerpt": "a" * 501},
        {"follow_up_at": datetime(2026, 11, 26)},
        {"follow_up_done": True},
        {"stage": "delivered"},
    ],
)
def test_create_rejects_bad_fields_and_fake_actions(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        CreateLead.model_validate(example(**changes))


def test_http_json_timezone_strings_are_parsed_without_weakening_strict_body() -> None:
    raw = example(
        follow_up_at="2026-11-26T12:00:00Z",
        follow_up_done=True,
    )
    created = CreateLead.model_validate(raw)
    assert created.follow_up_at is not None
    assert created.follow_up_at.utcoffset().total_seconds() == 0
    patch = PatchLead.model_validate(
        {"expected_version": 1, "follow_up_at": "2026-11-26T17:30:00+05:30"}
    )
    assert patch.follow_up_at is not None
    assert patch.follow_up_at.utcoffset().total_seconds() == 19800
    with pytest.raises(ValidationError):
        CreateLead.model_validate(example(follow_up_at="2026-11-26T12:00:00"))


def test_patch_needs_real_edit_and_version() -> None:
    with pytest.raises(ValidationError):
        PatchLead.model_validate({"expected_version": 1})
    with pytest.raises(ValidationError):
        PatchLead.model_validate({"expected_version": 1, "stage": None})
    with pytest.raises(ValidationError):
        PatchLead.model_validate({"expected_version": 1, "note": "bad\x00value"})
    with pytest.raises(ValidationError):
        PatchLead.model_validate({"expected_version": 1, "follow_up_at": "2026-11-26"})
    assert PatchLead(expected_version=1, follow_up_at=None).model_fields_set == {
        "expected_version",
        "follow_up_at",
    }


def test_header_idempotency_token_is_explicitly_bounded() -> None:
    assert validate_idempotency_key("safeKey_123") == "safeKey_123"
    for invalid in ("", "short", "bad key___", "." * 12, "s" * 129):
        with pytest.raises(ValueError):
            validate_idempotency_key(invalid)
