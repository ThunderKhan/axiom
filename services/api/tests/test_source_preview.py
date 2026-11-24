"""Permission-gated actual transport composition; deterministic test fetch only."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.auth import VerifiedPrincipal, get_verified_principal
from app.feed_source import parse_feed
from app.main import create_app
from app.public_source import FetchedDocument, SourceAccessBlocked, SourceAcquisitionFailed
from app.settings import RuntimeSettings
from app.source_registry import ReviewedSource, ReviewedSourceRegistry, SourceRateLimited
from app.workspace_http import get_workspace_store
from app.workspace_store import WorkspaceNotFound

URL = "https://example.org/product"
NOW = datetime(2026, 11, 24, 6, tzinfo=UTC)


def permission(**overrides: object) -> ReviewedSource:
    data: dict[str, object] = {
        "url": URL,
        "publisher": "Fixture publisher",
        "terms_url": "https://example.org/terms",
        "review_id": "fixture-only-review",
        "reviewer": "Fixture reviewer",
        "reviewed_on": date(2026, 11, 24),
        "permissions": ["research_preview", "competitor_preview"],
        "access_permitted": True,
        "excerpt_redisplay_permitted": True,
        "robots_reviewed": True,
        "minimum_interval_seconds": 60,
    }
    data.update(overrides)
    return ReviewedSource.model_validate(data)


def document(url: str) -> FetchedDocument:
    return FetchedDocument(
        url,
        "text/html",
        (
            b"<title>Example</title><script>Invented price</script>"
            b"<template><p>Invented price</p></template><p>Offline export.</p>"
        ),
        NOW,
    )


def test_registry_denies_unreviewed_url_and_wrong_purpose_before_fetch() -> None:
    calls: list[str] = []

    def fetch(url: str) -> FetchedDocument:
        calls.append(url)
        return document(url)

    registry = ReviewedSourceRegistry(
        (permission(permissions=["research_preview"]),), fetcher=fetch
    )
    for url in (URL + "?key=secret", URL + "/other", "https://other.example.org"):
        with pytest.raises(SourceAccessBlocked):
            registry.preview(url, "research_preview")
    with pytest.raises(SourceAccessBlocked):
        registry.preview(URL, "competitor_preview")
    assert calls == []
    review, result = registry.preview(URL, "research_preview")
    assert calls == [URL]
    assert review.review_id == "fixture-only-review"
    assert result.origin == "live"
    assert result.excerpt == "Offline export."
    assert result.retrieved_at == NOW
    assert "Invented price" not in result.excerpt


def test_process_limits_and_failed_requests_do_not_auto_retry() -> None:
    now = 100.0
    calls: list[str] = []

    def clock() -> float:
        return now

    def fetch(url: str) -> FetchedDocument:
        calls.append(url)
        return document(url)

    registry = ReviewedSourceRegistry((permission(),), fetcher=fetch, clock=clock)
    registry.preview(URL, "research_preview")
    now += 59
    with pytest.raises(SourceRateLimited):
        registry.preview(URL, "competitor_preview")
    now += 1
    registry.preview(URL, "competitor_preview")
    assert calls == [URL, URL]


@pytest.mark.parametrize(
    "overrides",
    [
        {"url": "https://*.example.org/product"},
        {"url": "https://example.org/product?credential=secret"},
        {"url": "http://example.org/product"},
        {"access_permitted": False},
        {"excerpt_redisplay_permitted": False},
        {"robots_reviewed": False},
        {"permissions": ["research_preview", "research_preview"]},
    ],
)
def test_invalid_review_configuration_is_refused(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        permission(**overrides)


def test_http_authorization_and_real_source_boundaries() -> None:
    owner = VerifiedPrincipal(uuid4(), None)
    outsider = VerifiedPrincipal(uuid4(), None)
    workspace = uuid4()
    calls: list[str] = []

    class Workspaces:
        def get_workspace(self, principal: VerifiedPrincipal, wid: UUID) -> dict[str, object]:
            if principal != owner or wid != workspace:
                raise WorkspaceNotFound()
            return {"id": workspace}

    def fetch(url: str) -> FetchedDocument:
        calls.append(url)
        return document(url)

    app = create_app(RuntimeSettings())
    app.state.source_registry = ReviewedSourceRegistry((permission(),), fetcher=fetch)
    app.dependency_overrides[get_workspace_store] = lambda: Workspaces()
    app.dependency_overrides[get_verified_principal] = lambda: outsider
    prefix = f"/api/v1/workspaces/{workspace}"
    with TestClient(app) as client:
        denied = client.post(prefix + "/research/public-url/preview", json={"url": URL})
        assert denied.status_code == 404
        assert calls == []
        app.dependency_overrides[get_verified_principal] = lambda: owner
        denied = client.post(
            prefix + "/research/public-url/preview",
            json={"url": "https://example.org/unreviewed"},
        )
        assert denied.status_code == 403
        assert calls == []
        invalid = client.post(
            prefix + "/research/public-url/preview",
            json={"url": URL, "access_reviewed": True},
        )
        assert invalid.status_code == 422
        assert calls == []
        response = client.post(
            prefix + "/competitors/preview",
            json={
                "name": "Fixture competitor",
                "url": URL,
                "confirmed": True,
                "candidates": [
                    {"kind": "features", "locator": "Offline export"},
                    {"kind": "pricing", "locator": "Invented price"},
                ],
            },
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        result = response.json()
        assert result["source"]["workspace_id"] == str(workspace)
        assert result["source"]["persisted"] is False
        assert result["source"]["independent_fact_verification"] is False
        assert len(result["claims"]) == 1
        assert result["claims"][0]["status"] == "publisher_claim_observed"
        assert result["claims"][0]["text"] == "Offline export"
        assert result["unknowns"] == ["pricing", "positioning"]
        assert calls == [URL]
        rate_limited = client.post(prefix + "/research/public-url/preview", json={"url": URL})
        assert rate_limited.status_code == 429
        assert calls == [URL]


def test_html_parser_assertion_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.public_source import SourceRecord

    def broken_parser(_document: FetchedDocument) -> SourceRecord:
        raise AssertionError("Invalid HTML parser state")

    monkeypatch.setattr("app.source_registry.normalize_fetched_document", broken_parser)
    registry = ReviewedSourceRegistry((permission(),), fetcher=document)
    with pytest.raises(SourceAcquisitionFailed):
        registry.preview(URL, "research_preview")


def test_default_runtime_registry_is_disabled() -> None:
    app = create_app(RuntimeSettings(reviewed_sources=()))
    registry = app.state.source_registry
    with pytest.raises(SourceAccessBlocked):
        registry.preview(URL, "research_preview")


def feed_document(url: str) -> FetchedDocument:
    return FetchedDocument(
        url,
        "application/rss+xml",
        b"""<rss version="2.0"><channel>
          <item><title>Offline sync</title><link>https://example.org/first</link>
          <description><![CDATA[<p>Need offline sync.</p><script>hidden</script>]]></description>
          <pubDate>Tue, 24 Nov 2026 06:00:00 GMT</pubDate></item>
          <item><title>Duplicate</title><link>https://example.org/first</link>
          <description>offline sync</description></item>
          <item><title>Unsafe</title><link>https://127.0.0.1/secret</link>
          <description>offline sync</description></item>
          <item><title>Other</title><link>https://example.org/second</link>
          <description>Another topic.</description></item>
        </channel></rss>""",
        NOW,
    )


def test_rss_and_atom_preserve_publication_and_filter_without_following_links() -> None:
    items = parse_feed(feed_document(URL), query="offline sync", limit=10)
    assert len(items) == 1
    assert items[0].source_url == "https://example.org/first"
    assert items[0].excerpt == "Need offline sync."
    assert items[0].published_at == NOW
    assert parse_feed(feed_document(URL), query="not present", limit=10) == ()
    atom = FetchedDocument(
        URL,
        "application/atom+xml",
        b"""<feed xmlns="http://www.w3.org/2005/Atom">
        <entry><title>Offline export</title><link href="https://example.org/atom"/>
        <summary>Export requested</summary><published>2026-11-24T06:00:00Z</published>
        </entry></feed>""",
        NOW,
    )
    assert parse_feed(atom, query="export", limit=1)[0].published_at == NOW


@pytest.mark.parametrize(
    "body",
    [
        b'<!DOCTYPE rss [<!ENTITY x "secret">]><rss version="2.0">&x;</rss>',
        b"<not-a-feed/>",
        b"<rss",
        b"x" * 65537,
    ],
)
def test_malformed_or_unsafe_xml_is_rejected(body: bytes) -> None:
    with pytest.raises(SourceAcquisitionFailed):
        parse_feed(FetchedDocument(URL, "application/xml", body, NOW), query="", limit=10)


def test_feed_preview_permission_and_http_owner_guard() -> None:
    owner, outsider = VerifiedPrincipal(uuid4(), None), VerifiedPrincipal(uuid4(), None)
    workspace = uuid4()
    calls: list[str] = []

    class Workspaces:
        def get_workspace(self, principal: VerifiedPrincipal, wid: UUID) -> dict[str, object]:
            if principal != owner or wid != workspace:
                raise WorkspaceNotFound()
            return {"id": workspace}

    def fetch(url: str) -> FetchedDocument:
        calls.append(url)
        return feed_document(url)

    registry = ReviewedSourceRegistry((permission(),), fetcher=fetch)
    with pytest.raises(SourceAccessBlocked):
        registry.preview_feed(URL, query="", limit=10)
    assert calls == []
    app = create_app(RuntimeSettings())
    app.state.source_registry = ReviewedSourceRegistry(
        (permission(permissions=["feed_preview"]),), fetcher=fetch
    )
    app.dependency_overrides[get_workspace_store] = lambda: Workspaces()
    app.dependency_overrides[get_verified_principal] = lambda: outsider
    route = f"/api/v1/workspaces/{workspace}/research/feed/preview"
    with TestClient(app) as client:
        body = {"url": URL, "query": "offline", "limit": 5}
        assert client.post(route, json=body).status_code == 404
        assert calls == []
        app.dependency_overrides[get_verified_principal] = lambda: owner
        response = client.post(route, json=body)
        assert response.status_code == 200
        result = response.json()
        assert result["source_family"] == "rss_atom"
        assert result["persisted"] is False
        assert result["independent_fact_verification"] is False
        assert len(result["items"]) == 1
        assert calls == [URL]
        assert client.post(route, json=body).status_code == 429
        assert calls == [URL]
