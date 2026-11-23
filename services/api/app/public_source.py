"""Fail-closed bounded public document acquisition and explicit source provenance.

WP-04 foundation only. No route or worker enables outbound fetching before an
individual provider/website access and retention review. The connection is pinned
to a fully validated numeric address, avoiding DNS-rebinding between resolution
and the socket connection. Redirects are not followed.
"""

from __future__ import annotations

import hashlib
import html
import io
import ipaddress
import socket
import ssl
from collections.abc import Buffer, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from http.client import HTTPConnection, HTTPException, HTTPResponse, HTTPSConnection
from time import monotonic
from typing import Literal, cast
from urllib.parse import SplitResult, urlsplit

MAX_URL_BYTES = 2048
MAX_BODY_BYTES = 65536
MAX_EXCERPT_CHARS = 500
MAX_TITLE_CHARS = 180
TIMEOUT_SECONDS = 4.0
MAX_FETCH_SECONDS = 8.0

_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "text/html",
        "text/plain",
        "application/xhtml+xml",
        "application/rss+xml",
        "application/atom+xml",
        "application/xml",
        "text/xml",
    }
)
_BLOCKED_HOST_SUFFIXES = (".local", ".localhost", ".internal", ".test", ".invalid")
Resolver = Callable[..., object]


class SourceAccessBlocked(Exception):
    """URL, website permission or destination did not meet the reviewed policy."""


class SourceAcquisitionFailed(Exception):
    """The upstream response was not a bounded, supported public document."""


@dataclass(frozen=True, slots=True)
class PinnedDestination:
    url: str
    scheme: Literal["http", "https"]
    hostname: str
    port: int
    path: str
    addresses: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class FetchedDocument:
    url: str
    content_type: str
    body: bytes
    retrieved_at: datetime
    charset: str = "utf-8"


@dataclass(frozen=True, slots=True)
class SourceRecord:
    """Source text is untrusted evidence, never an instruction or verified demand."""

    source_family: Literal["manual_url"]
    source_record_id: str
    provider_record_id: None
    canonical_url: str
    title: str
    excerpt: str
    published_at: None
    retrieved_at: datetime
    origin: Literal["live"]
    content_digest: str
    access_status: Literal["retrieved"]


def _public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
        if isinstance(address, ipaddress.IPv6Address) and (
            address.ipv4_mapped
            or address.sixtofour
            or address.teredo
            or address.scope_id is not None
            or address.is_site_local
        ):
            return False
        return (
            address.is_global
            and not address.is_multicast
            and not address.is_reserved
            and not address.is_unspecified
            and not address.is_loopback
            and not address.is_link_local
            and not address.is_private
        )
    except ValueError:
        return False


def resolve_public_url(
    raw_url: str,
    *,
    resolver: Resolver = socket.getaddrinfo,
) -> PinnedDestination:
    """Validate every resolved address, not just the first favorable answer."""
    if (
        not isinstance(raw_url, str)
        or not 1 <= len(raw_url.encode("utf-8")) <= MAX_URL_BYTES
        or raw_url.strip() != raw_url
        or any(ord(char) < 32 or ord(char) == 127 for char in raw_url)
        or "\\" in raw_url
    ):
        raise SourceAccessBlocked()
    try:
        parsed: SplitResult = urlsplit(raw_url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise SourceAccessBlocked() from exc
    if (
        parsed.scheme not in {"http", "https"}
        or not hostname
        or not hostname.isascii()
        or hostname.endswith(".")
        or hostname.startswith("-")
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or parsed.query
        or any(hostname.endswith(suffix) for suffix in _BLOCKED_HOST_SUFFIXES)
        or (hostname.count(".") == 0 and ":" not in hostname)
    ):
        raise SourceAccessBlocked()
    # Obvious literal private/loopback destinations must be denied before
    # any resolver call; DNS answers receive the same full policy below.
    literal: ipaddress.IPv4Address | ipaddress.IPv6Address | None
    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None
    if literal is not None and not _public_address(hostname):
        raise SourceAccessBlocked()
    default_port = 443 if parsed.scheme == "https" else 80
    if port is not None and port != default_port:
        raise SourceAccessBlocked()
    selected_port = port or default_port
    # Reject ambiguous URL encodings before sending any request bytes.
    if not parsed.path.isascii() or len(parsed.path) > 1800:
        raise SourceAccessBlocked()
    try:
        answers = cast(
            list[tuple[int, int, int, str, tuple[object, ...]]],
            resolver(hostname, selected_port, type=socket.SOCK_STREAM),
        )
    except (OSError, ValueError) as exc:
        raise SourceAcquisitionFailed() from exc
    if not answers:
        raise SourceAcquisitionFailed()
    addresses: list[str] = []
    for family, _, _, _, address in answers:
        if family not in (socket.AF_INET, socket.AF_INET6) or not address:
            raise SourceAccessBlocked()
        numeric = str(address[0])
        if not _public_address(numeric):
            raise SourceAccessBlocked()
        if numeric not in addresses:
            addresses.append(numeric)
    if not addresses:
        raise SourceAccessBlocked()
    return PinnedDestination(
        url=raw_url,
        scheme="https" if parsed.scheme == "https" else "http",
        hostname=hostname.lower(),
        port=selected_port,
        path=parsed.path or "/",
        addresses=tuple(addresses),
    )


class _DeadlineRaw(io.RawIOBase):
    """Make all http.client header/chunk framing reads honor one absolute deadline."""

    def __init__(self, owner: _DeadlineSocket) -> None:
        super().__init__()
        self.owner = owner

    def readable(self) -> bool:
        return True

    def readinto(self, buffer: Buffer) -> int:
        return self.owner.recv_into(buffer)

    def close(self) -> None:
        if not self.closed:
            self.owner.release_reader()
        super().close()


class _DeadlineSocket:
    """Bounded socket adapter with makefile-compatible deferred-close semantics.

    HTTPConnection may close its socket after reading response headers when
    Connection: close is negotiated; HTTPResponse still owns the reader until
    the body has been consumed. Always preserve the reader's ownership until
    response.close(), then hard-close on request completion.
    """

    def __init__(self, raw: socket.socket | ssl.SSLSocket, deadline: float) -> None:
        self.raw = raw
        self.deadline = deadline
        self.readers = 0
        self.closing = False

    def _enforce_deadline(self) -> None:
        remaining = self.deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError("Source fetch deadline expired")
        self.raw.settimeout(min(TIMEOUT_SECONDS, remaining))

    def recv_into(self, buffer: Buffer) -> int:
        self._enforce_deadline()
        return self.raw.recv_into(buffer)

    def sendall(self, data: bytes) -> None:
        self._enforce_deadline()
        self.raw.sendall(data)

    def makefile(self, mode: str, buffering: int | None = None) -> io.BufferedReader:
        if mode != "rb":
            raise ValueError("Only binary response readers are allowed")
        self.readers += 1
        return io.BufferedReader(_DeadlineRaw(self))

    def settimeout(self, _value: float) -> None:
        # Do not let http.client or a caller loosen the absolute deadline.
        self._enforce_deadline()

    def release_reader(self) -> None:
        self.readers -= 1
        if self.closing and self.readers == 0:
            self.raw.close()

    def close(self) -> None:
        self.closing = True
        if self.readers == 0:
            self.raw.close()

    def force_close(self) -> None:
        # Also close if header parsing failed before returning an HTTPResponse.
        self.closing = True
        self.raw.close()


class _PinnedHTTP(HTTPConnection):
    def __init__(self, target: PinnedDestination) -> None:
        super().__init__(target.hostname, target.port, timeout=TIMEOUT_SECONDS)
        self._address = target.addresses[0]
        self._deadline = monotonic() + MAX_FETCH_SECONDS
        self._bound_socket: _DeadlineSocket | None = None

    def set_deadline(self, deadline: float) -> None:
        self._deadline = deadline

    def connect(self) -> None:
        # Numeric address is selected only after all DNS answers pass validation.
        remaining = self._deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError("Source fetch deadline expired")
        raw = socket.create_connection((self._address, self.port), min(TIMEOUT_SECONDS, remaining))
        self._bound_socket = _DeadlineSocket(raw, self._deadline)
        # http.client needs only sendall/makefile/close/settimeout. Our adapter
        # intentionally preserves the same socket protocol but not its class.
        self.sock = cast(socket.socket, self._bound_socket)

    def abort(self) -> None:
        if self._bound_socket is not None:
            self._bound_socket.force_close()


class _PinnedHTTPS(HTTPSConnection):
    def __init__(self, target: PinnedDestination) -> None:
        self._ssl_context = ssl.create_default_context()
        super().__init__(
            target.hostname,
            target.port,
            timeout=TIMEOUT_SECONDS,
            context=self._ssl_context,
        )
        self._address = target.addresses[0]
        self._deadline = monotonic() + MAX_FETCH_SECONDS
        self._bound_socket: _DeadlineSocket | None = None

    def set_deadline(self, deadline: float) -> None:
        self._deadline = deadline

    def connect(self) -> None:
        remaining = self._deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError("Source fetch deadline expired")
        raw = socket.create_connection((self._address, self.port), min(TIMEOUT_SECONDS, remaining))
        try:
            remaining = self._deadline - monotonic()
            if remaining <= 0:
                raise TimeoutError("Source fetch deadline expired")
            raw.settimeout(min(TIMEOUT_SECONDS, remaining))
            # Verify the actual original hostname while connecting to the pinned IP.
            secured = self._ssl_context.wrap_socket(raw, server_hostname=self.host)
            self._bound_socket = _DeadlineSocket(secured, self._deadline)
            self.sock = cast(socket.socket, self._bound_socket)
        except Exception:
            raw.close()
            raise

    def abort(self) -> None:
        if self._bound_socket is not None:
            self._bound_socket.force_close()


def fetch_reviewed_public_document(
    raw_url: str,
    *,
    access_reviewed: bool = False,
    resolver: Resolver = socket.getaddrinfo,
    connection_factory: Callable[[PinnedDestination], HTTPConnection] | None = None,
) -> FetchedDocument:
    """No outbound request without explicit source-specific permission review.

    A reviewed document fetch rejects all redirects. Each new URL requires an
    independent policy decision, DNS resolution and address validation.
    """
    if not access_reviewed:
        raise SourceAccessBlocked()
    # Cover the TCP connect, request write, HTTP headers, body and chunk
    # framing. DNS is separately validated but uses the OS resolver timeout.
    deadline = monotonic() + MAX_FETCH_SECONDS
    target = resolve_public_url(raw_url, resolver=resolver)
    factory = connection_factory or (_PinnedHTTPS if target.scheme == "https" else _PinnedHTTP)
    connection = factory(target)
    if isinstance(connection, (_PinnedHTTP, _PinnedHTTPS)):
        connection.set_deadline(deadline)
    response: HTTPResponse | None = None
    try:
        connection.request(
            "GET",
            target.path,
            headers={
                "Accept": "text/html, text/plain, application/xml",
                "Accept-Encoding": "identity",
                "User-Agent": "AxiomResearch/0.1",
            },
        )
        response = connection.getresponse()
        if response.status in (301, 302, 303, 307, 308):
            raise SourceAccessBlocked()
        if response.status != 200:
            raise SourceAcquisitionFailed()
        content_header = response.getheader("Content-Type") or ""
        content_parts = content_header.split(";")
        content_type = content_parts[0].lower().strip()
        if content_type not in _ALLOWED_CONTENT_TYPES:
            raise SourceAccessBlocked()
        charset = "utf-8"
        for part in content_parts[1:]:
            key, separator, value = part.strip().partition("=")
            if key.lower() == "charset":
                if not separator:
                    raise SourceAccessBlocked()
                charset = value.strip().strip('"').lower()
                break
        if charset not in {"utf-8", "us-ascii", "iso-8859-1"}:
            raise SourceAccessBlocked()
        content_encoding = (response.getheader("Content-Encoding") or "identity").lower()
        if content_encoding != "identity":
            raise SourceAccessBlocked()
        raw_length = response.getheader("Content-Length")
        expected_length: int | None = None
        if raw_length is not None:
            try:
                expected_length = int(raw_length)
            except ValueError as exc:
                raise SourceAcquisitionFailed() from exc
            if expected_length < 0 or expected_length > MAX_BODY_BYTES:
                raise SourceAccessBlocked()
        # A per-socket timeout alone does not stop a slow-trickling server.
        # read1() performs one bounded network read per iteration so a global
        # monotonic deadline can be rechecked between arrivals.
        chunks: list[bytes] = []
        size = 0
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise SourceAcquisitionFailed()
            sock = getattr(connection, "sock", None)
            if sock is not None:
                sock.settimeout(min(TIMEOUT_SECONDS, remaining))
            chunk = response.read1(min(8192, MAX_BODY_BYTES + 1 - size))
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BODY_BYTES:
                raise SourceAccessBlocked()
            chunks.append(chunk)
        body = b"".join(chunks)
        if not body or (expected_length is not None and len(body) != expected_length):
            raise SourceAcquisitionFailed()
        try:
            body.decode(charset, errors="strict")
        except UnicodeError as exc:
            raise SourceAcquisitionFailed() from exc
        return FetchedDocument(raw_url, content_type, body, datetime.now(UTC), charset)
    except (OSError, TimeoutError, ssl.SSLError, HTTPException) as exc:
        # Never surface raw socket/network messages containing private URL input.
        raise SourceAcquisitionFailed() from exc
    finally:
        try:
            if response is not None:
                response.close()
        finally:
            connection.close()
            if isinstance(connection, (_PinnedHTTP, _PinnedHTTPS)):
                connection.abort()


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden = 0
        self._title = False
        self.title: list[str] = []
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "svg", "noscript"}:
            self._hidden += 1
        elif tag == "title":
            self._title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "svg", "noscript"}:
            self._hidden = max(0, self._hidden - 1)
        elif tag == "title":
            self._title = False

    def handle_data(self, data: str) -> None:
        if self._hidden:
            return
        if self._title:
            self.title.append(data)
        else:
            self.parts.append(data)


def normalize_fetched_document(document: FetchedDocument) -> SourceRecord:
    """Preserve actual retrieval provenance; no guessed publication timestamp."""
    if document.retrieved_at.tzinfo is None or not document.body:
        raise ValueError("A real timestamp and nonempty response body are required")
    if len(document.body) > MAX_BODY_BYTES or document.content_type not in _ALLOWED_CONTENT_TYPES:
        raise ValueError("Unexpected public document representation")
    if document.charset not in {"utf-8", "us-ascii", "iso-8859-1"}:
        raise ValueError("Unsupported public document charset")
    try:
        decoded = document.body.decode(document.charset, errors="strict")
    except UnicodeError as exc:
        raise ValueError("Invalid declared public document encoding") from exc
    if document.content_type in {"text/html", "application/xhtml+xml"}:
        parser = _VisibleText()
        parser.feed(decoded)
        title = " ".join(" ".join(parser.title).split())
        excerpt = " ".join(" ".join(parser.parts).split())
    else:
        title = ""
        excerpt = " ".join(html.unescape(decoded).split())
    digest = hashlib.sha256(document.body).hexdigest()
    identifier = hashlib.sha256(document.url.encode("utf-8")).hexdigest()[:32]
    return SourceRecord(
        source_family="manual_url",
        source_record_id=identifier,
        provider_record_id=None,
        canonical_url=document.url,
        title=title[:MAX_TITLE_CHARS],
        excerpt=excerpt[:MAX_EXCERPT_CHARS],
        published_at=None,
        retrieved_at=document.retrieved_at.astimezone(UTC),
        origin="live",
        content_digest=digest,
        access_status="retrieved",
    )


def unique_sources(records: list[SourceRecord]) -> list[SourceRecord]:
    """Stable dedupe, never merge distinct URLs on similar or imagined text."""
    seen: set[tuple[str, str]] = set()
    out: list[SourceRecord] = []
    for record in records:
        key = (record.source_family, record.source_record_id)
        if key not in seen:
            out.append(record)
            seen.add(key)
    return out
