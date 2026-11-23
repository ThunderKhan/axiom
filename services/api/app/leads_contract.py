"""Bounded user-declared lead inputs; no claim of verified live source retrieval."""

from __future__ import annotations

import ipaddress
import re
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator, model_validator

from app.workspace_http import StrictBody

LeadStage = Literal["spotted", "qualified", "contacted", "closed_lost"]
_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$")


def validate_idempotency_key(value: str) -> str:
    if not _KEY.fullmatch(value):
        raise ValueError("Invalid idempotency key")
    return value


def _validate_url(value: str) -> str:
    if len(value.encode("utf-8")) > 2048 or value.strip() != value or "\\" in value:
        raise ValueError("Invalid source URL")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Invalid source URL") from exc
    if (
        parsed.scheme != "https"
        or not hostname
        or not hostname.isascii()
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or (port is not None and port != 443)
        or any(ord(character) < 33 or ord(character) == 127 for character in value)
    ):
        raise ValueError("A valid public HTTPS citation is required")
    normalized_host = hostname.rstrip(".").lower()
    if normalized_host == "localhost" or normalized_host.endswith(
        (".localhost", ".local", ".internal", ".test", ".invalid")
    ):
        raise ValueError("Private source authorities are not valid citations")
    try:
        literal = ipaddress.ip_address(normalized_host)
    except ValueError as exc:
        if re.fullmatch(r"[0-9.]+", normalized_host):
            raise ValueError("Noncanonical numeric source addresses are not valid") from exc
        literal = None
    if literal is not None and not literal.is_global:
        raise ValueError("Private addresses are not valid citations")
    return value


def _parse_timestamp(value: object) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("A timezone-aware ISO 8601 timestamp is required")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid timestamp format") from exc


def _safe_text(value: str) -> str:
    if "\x00" in value or any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValueError("Invalid text characters")
    return value


class CreateLead(StrictBody):
    """Only user-supplied source URLs can be saved until lawful adapters are integrated."""

    title: str = Field(min_length=1, max_length=180)
    source_url: str = Field(min_length=10, max_length=2048)
    source_excerpt: str = Field(min_length=1, max_length=500)
    stage: LeadStage = "spotted"
    note: str = Field(default="", max_length=2000)
    follow_up_at: datetime | None = None
    follow_up_done: bool = False
    unsent_draft: str = Field(default="", max_length=4000)

    @field_validator("title")
    @classmethod
    def nonempty_title(cls, value: str) -> str:
        title = _safe_text(value).strip()
        if not title or any(ord(char) < 32 or ord(char) == 127 for char in title):
            raise ValueError("A single-line title is required")
        return title

    @field_validator("source_url")
    @classmethod
    def validated_source(cls, value: str) -> str:
        return _validate_url(value)

    @field_validator("source_excerpt", "note", "unsent_draft")
    @classmethod
    def bounded_text(cls, value: str) -> str:
        return _safe_text(value)

    @field_validator("follow_up_at", mode="before")
    @classmethod
    def parse_timestamp(cls, value: object) -> datetime | None:
        return _parse_timestamp(value)

    @field_validator("follow_up_at")
    @classmethod
    def aware_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Follow-up timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def consistent_followup(self) -> CreateLead:
        if self.follow_up_done and self.follow_up_at is None:
            raise ValueError("Cannot complete a follow-up without a due date")
        return self


class PatchLead(StrictBody):
    expected_version: int = Field(ge=1, lt=9223372036854775807)
    stage: LeadStage | None = None
    note: str | None = Field(default=None, max_length=2000)
    follow_up_at: datetime | None = None
    follow_up_done: bool | None = None
    unsent_draft: str | None = Field(default=None, max_length=4000)

    @field_validator("note", "unsent_draft")
    @classmethod
    def bounded_text(cls, value: str | None) -> str | None:
        return _safe_text(value) if value is not None else None

    @field_validator("follow_up_at", mode="before")
    @classmethod
    def parse_timestamp(cls, value: object) -> datetime | None:
        return _parse_timestamp(value)

    @field_validator("follow_up_at")
    @classmethod
    def aware_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("Follow-up timestamps must include a timezone")
        return value

    @model_validator(mode="after")
    def require_edit(self) -> PatchLead:
        edited = self.model_fields_set - {"expected_version"}
        if not edited:
            raise ValueError("At least one changed field is required")
        if any(getattr(self, name) is None for name in edited if name != "follow_up_at"):
            raise ValueError("Only the follow-up due date can be cleared")
        return self
