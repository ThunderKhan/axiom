"""Server-owned permission records and bounded, nonpersistent source retrieval."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from threading import BoundedSemaphore, Lock
from time import monotonic
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.feed_source import FeedItem, parse_feed
from app.public_source import (
    FetchedDocument,
    SourceAccessBlocked,
    SourceAcquisitionFailed,
    SourceRecord,
    fetch_reviewed_public_document,
    normalize_fetched_document,
)

Purpose = Literal["research_preview", "competitor_preview", "feed_preview"]
Fetcher = Callable[[str], FetchedDocument]
_PREVIEW_CONTENT_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})


class ReviewedSource(BaseModel):
    """Trusted deployment configuration, never a client-supplied permission claim."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    url: str = Field(min_length=10, max_length=2048)
    publisher: str = Field(min_length=1, max_length=120)
    terms_url: str = Field(min_length=10, max_length=2048)
    review_id: str = Field(min_length=1, max_length=120)
    reviewer: str = Field(min_length=1, max_length=120)
    reviewed_on: date
    permissions: tuple[Purpose, ...] = Field(min_length=1, max_length=3)
    access_permitted: Literal[True]
    excerpt_redisplay_permitted: Literal[True]
    robots_reviewed: Literal[True]
    minimum_interval_seconds: int = Field(default=60, ge=10, le=3600)

    @field_validator("url", "terms_url")
    @classmethod
    def exact_https_url(cls, value: str) -> str:
        if (
            not value.isascii()
            or value.strip() != value
            or any(ord(ch) <= 32 or ord(ch) == 127 for ch in value)
            or "\\" in value
            or "*" in value
        ):
            raise ValueError("Review records require exact HTTPS URLs")
        try:
            parsed = urlsplit(value)
            valid = (
                parsed.scheme == "https"
                and bool(parsed.hostname)
                and parsed.username is None
                and parsed.password is None
                and parsed.port in (None, 443)
                and not parsed.fragment
                and not parsed.query
            )
        except ValueError as exc:
            raise ValueError("Invalid reviewed URL") from exc
        if not valid:
            raise ValueError("Review records require exact HTTPS URLs")
        return value

    @field_validator("publisher", "review_id", "reviewer")
    @classmethod
    def clean_label(cls, value: str) -> str:
        if not value.strip() or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
            raise ValueError("Review metadata must be a nonempty single line")
        return value.strip()

    @model_validator(mode="after")
    def validate_review(self) -> ReviewedSource:
        if self.reviewed_on > datetime.now(UTC).date():
            raise ValueError("Source review date cannot be in the future")
        if len(set(self.permissions)) != len(self.permissions):
            raise ValueError("Duplicate permissions")
        return self


class SourceRateLimited(Exception):
    """The process-local concurrency or request interval limit was reached."""


def _fetch_approved(url: str) -> FetchedDocument:
    return fetch_reviewed_public_document(url, access_reviewed=True)


class ReviewedSourceRegistry:
    """An immutable exact-URL registry with per-process, non-bursting network limits."""

    def __init__(
        self,
        entries: tuple[ReviewedSource, ...] = (),
        *,
        fetcher: Fetcher = _fetch_approved,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if len(entries) > 32 or len({entry.url for entry in entries}) != len(entries):
            raise ValueError("Source registry requires at most 32 unique reviewed URLs")
        self._entries = {entry.url: entry for entry in entries}
        self._fetcher = fetcher
        self._clock = clock
        self._lock = Lock()
        self._in_flight = BoundedSemaphore(1)
        self._last_request: dict[str, float] = {}
        self._last_global: float | None = None

    @contextmanager
    def _reviewed_document(
        self, url: str, purpose: Purpose
    ) -> Iterator[tuple[ReviewedSource, FetchedDocument]]:
        # Never let a founder's POST body decide what may be fetched.
        review = self._entries.get(url)
        if review is None or purpose not in review.permissions:
            raise SourceAccessBlocked()
        if not self._in_flight.acquire(blocking=False):
            raise SourceRateLimited()
        try:
            with self._lock:
                now = self._clock()
                last = self._last_request.get(url)
                if self._last_global is not None and now - self._last_global < 5:
                    raise SourceRateLimited()
                if last is not None and now - last < review.minimum_interval_seconds:
                    raise SourceRateLimited()
                # Failures count against the quota; there are no automatic retries.
                self._last_request[url] = now
                self._last_global = now
            document = self._fetcher(url)
            if document.url != url:
                raise SourceAcquisitionFailed()
            yield review, document
        finally:
            self._in_flight.release()

    def preview(self, url: str, purpose: Purpose) -> tuple[ReviewedSource, SourceRecord]:
        if purpose not in ("research_preview", "competitor_preview"):
            raise SourceAccessBlocked()
        with self._reviewed_document(url, purpose) as (review, document):
            # The bounded normalizer treats source contents as inert text.
            # Do not expose XML/HTML markup or assume XML is an actual parsed feed.
            if document.content_type not in _PREVIEW_CONTENT_TYPES:
                raise SourceAccessBlocked()
            try:
                record = normalize_fetched_document(document)
            except (ValueError, UnicodeError, AssertionError) as exc:
                raise SourceAcquisitionFailed() from exc
            if not record.excerpt.strip():
                raise SourceAcquisitionFailed()
            return review, record

    def preview_feed(
        self, url: str, *, query: str, limit: int
    ) -> tuple[ReviewedSource, FetchedDocument, tuple[FeedItem, ...]]:
        with self._reviewed_document(url, "feed_preview") as (review, document):
            return review, document, parse_feed(document, query=query, limit=limit)
