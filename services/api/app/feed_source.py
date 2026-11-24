"""Bounded RSS 2.0 and Atom 1.0 parsing of already reviewed fetched documents."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

from app.public_source import (
    MAX_BODY_BYTES,
    MAX_EXCERPT_CHARS,
    MAX_TITLE_CHARS,
    FetchedDocument,
    SourceAcquisitionFailed,
    _VisibleText,
)

FEED_CONTENT_TYPES = frozenset(
    {"application/rss+xml", "application/atom+xml", "application/xml", "text/xml"}
)
_ATOM = "{http://www.w3.org/2005/Atom}"


@dataclass(frozen=True, slots=True)
class FeedItem:
    source_id: str
    source_url: str
    title: str
    excerpt: str
    published_at: datetime | None


def _plain(element: ET.Element | None, maximum: int) -> str:
    if element is None or len(element):
        return ""  # Nested XML/XHTML content is not supported in this bounded slice.
    parser = _VisibleText()
    parser.feed(element.text or "")
    return " ".join(" ".join(parser.parts).split())[:maximum]


def _citation(raw: str) -> str | None:
    value = raw.strip()
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        if (
            not value.isascii()
            or len(value) > 2048
            or any(ord(ch) <= 32 or ord(ch) == 127 for ch in value)
            or "\\" in value
            or parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
            or parsed.query
            or parsed.fragment
            or not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,63}", host)
            or host.endswith((".local", ".localhost", ".internal", ".test", ".invalid"))
        ):
            return None
        return value
    except (ValueError, UnicodeError):
        return None


def _published(raw: str | None, *, atom: bool) -> datetime | None:
    if not raw or len(raw) > 100:
        return None
    try:
        value = (
            datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if atom
            else parsedate_to_datetime(raw)
        )
        return value.astimezone(UTC) if value.tzinfo is not None else None
    except (ValueError, TypeError, OverflowError):
        return None


def parse_feed(document: FetchedDocument, *, query: str, limit: int) -> tuple[FeedItem, ...]:
    """Parse one bounded feed; never resolve entry links or treat a match as buying intent."""
    if (
        document.content_type not in FEED_CONTENT_TYPES
        or document.charset not in {"utf-8", "us-ascii"}
        or not 1 <= len(document.body) <= MAX_BODY_BYTES
        or document.retrieved_at.tzinfo is None
        or type(limit) is not int
        or not 1 <= limit <= 20
        or len(query) > 120
    ):
        raise SourceAcquisitionFailed()
    try:
        decoded = document.body.decode(document.charset, errors="strict")
        # Reject DTD/entity declarations before parsing. Pass decoded Unicode so
        # an XML encoding declaration cannot hide a byte-level declaration.
        if "<!DOCTYPE" in decoded or "<!ENTITY" in decoded or "\x00" in decoded:
            raise ValueError("DTD and entity declarations are not supported")
        root = ET.fromstring(decoded)  # noqa: S314 - bounded input, DTD/entity declarations denied
        if sum(1 for _ in root.iter()) > 2048:
            raise ValueError("Feed structure is oversized")
        atom = root.tag == _ATOM + "feed"
        if atom:
            entries = root.findall(_ATOM + "entry")
        elif root.tag == "rss" and root.get("version") == "2.0":
            entries = root.findall("channel/item")
        else:
            raise ValueError("Unsupported feed format")

        words = query.casefold().split()
        output: list[FeedItem] = []
        seen: set[str] = set()
        for entry in entries[:128]:
            prefix = _ATOM if atom else ""
            if atom:
                link = next(
                    (
                        item.get("href", "")
                        for item in entry.findall(_ATOM + "link")
                        if item.get("rel", "alternate") == "alternate"
                    ),
                    "",
                )
                summary = entry.find(_ATOM + "summary")
                if summary is None:
                    summary = entry.find(_ATOM + "content")
                timestamp = entry.findtext(_ATOM + "published")
            else:
                link = entry.findtext("link", "")
                summary = entry.find("description")
                timestamp = entry.findtext("pubDate")
            url = _citation(link)
            if url is None or url in seen:
                continue
            title = _plain(entry.find(prefix + "title"), MAX_TITLE_CHARS)
            excerpt = _plain(summary, MAX_EXCERPT_CHARS)
            if not title or not excerpt:
                continue
            searchable = (title + " " + excerpt).casefold()
            if not all(word in searchable for word in words):
                continue
            seen.add(url)
            output.append(
                FeedItem(
                    source_id=hashlib.sha256(url.encode("utf-8")).hexdigest()[:32],
                    source_url=url,
                    title=title,
                    excerpt=excerpt,
                    published_at=_published(timestamp, atom=atom),
                )
            )
            if len(output) == limit:
                break
        return tuple(output)
    except (ET.ParseError, ValueError, UnicodeError, AssertionError) as exc:
        raise SourceAcquisitionFailed() from exc
