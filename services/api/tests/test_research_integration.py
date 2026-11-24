"""Real isolated PostgreSQL with an explicitly injected feed fixture, not live evidence."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.auth import VerifiedPrincipal, get_verified_principal
from app.database import Database
from app.main import create_app
from app.profile_contract import ProfileAnswers
from app.profile_store import ProfileStore
from app.public_source import FetchedDocument
from app.settings import RuntimeSettings
from app.source_registry import ReviewedSource, ReviewedSourceRegistry
from app.workspace_store import WorkspaceStore

pytestmark = pytest.mark.postgres
URL = "https://example.org/feed.xml"


@pytest.fixture(scope="module")
def database():
    raw = os.environ.get("AXIOM_TEST_RUNTIME_DATABASE_URL")
    if not raw:
        pytest.skip("Only isolated PostgreSQL runtime credentials are accepted")
    instance = Database(RuntimeSettings(database_url=raw, database_required=True))
    yield instance
    instance.close()


def test_persist_replay_reopen_and_deny_foreign_feed_runs(database: Database) -> None:
    owner, outsider = VerifiedPrincipal(uuid4(), None), VerifiedPrincipal(uuid4(), None)
    workspaces = WorkspaceStore(database)
    workspaces.bootstrap(owner)
    workspaces.bootstrap(outsider)
    created = workspaces.create_workspace(owner, name="Research", key=uuid4().hex)
    workspace = UUID(str(created.response_body["id"]))
    profiles = ProfileStore(database)
    profiles.save(
        owner,
        workspace,
        answers=ProfileAnswers(
            stage="live",
            name="Notes",
            problem="Offline notes",
            audience="Students",
            capabilities="offline sync",
        ),
        expected_revision=0,
    )
    profiles.confirm(owner, workspace, expected_revision=1)
    state = profiles.read(owner, workspace)
    confirmed = state["confirmed"]
    assert isinstance(confirmed, dict)
    calls: list[str] = []

    def fetch(url: str) -> FetchedDocument:
        calls.append(url)
        return FetchedDocument(
            url,
            "application/rss+xml",
            b'<rss version="2.0"><channel><item><title>Notes</title>'
            b"<link>https://example.org/article</link>"
            b"<description>Offline sync requested.</description></item></channel></rss>",
            datetime.now(UTC),
        )

    review = ReviewedSource(
        url=URL,
        publisher="Fixture publisher",
        terms_url="https://example.org/terms",
        review_id="test-fixture",
        reviewer="integration test fixture",
        reviewed_on=datetime.now(UTC).date(),
        permissions=("feed_persist",),
        access_permitted=True,
        excerpt_redisplay_permitted=True,
        robots_reviewed=True,
        retention_reviewed=True,
    )
    app = create_app(RuntimeSettings())
    app.state.database = database
    app.state.source_registry = ReviewedSourceRegistry((review,), fetcher=fetch)
    app.dependency_overrides[get_verified_principal] = lambda: outsider
    route = f"/api/v1/workspaces/{workspace}/research/runs"
    payload = {"profile_version_id": str(confirmed["id"]), "url": URL, "query": "offline"}
    headers = {"Idempotency-Key": uuid4().hex}
    with TestClient(app) as client:
        assert client.post(route, json=payload, headers=headers).status_code == 404
        assert calls == []
        app.dependency_overrides[get_verified_principal] = lambda: owner
        invalid = client.post(route, json={**payload, "query": "\x00"}, headers=headers)
        assert invalid.status_code == 422
        assert calls == []
        blocked = client.post(
            route, json={**payload, "url": "https://example.org/other"}, headers=headers
        )
        assert blocked.status_code == 403
        assert calls == []
        response = client.post(route, json=payload, headers=headers)
        assert response.status_code == 201
        saved = response.json()
        assert saved["status"] == "completed"
        assert saved["result"]["items"][0]["intent"] == "unknown"
        assert saved["result"]["policy_review_id"] == "test-fixture"
        assert calls == [URL]
        replay = client.post(route, json=payload, headers=headers)
        assert replay.status_code == 200
        assert replay.json() == saved
        assert calls == [URL]
        assert (
            client.post(route, json={**payload, "query": "other"}, headers=headers).status_code
            == 409
        )
        detail = route + "/" + saved["run_id"]
        assert client.get(detail).json() == saved
        signal = saved["result"]["items"][0]["signal_id"]
        assessment_route = detail + "/signals/" + signal + "/assessment"
        need = {"requirement": "offline sync", "locator": "Offline sync", "intent": "buying"}
        assessment = client.post(assessment_route, json={"needs": [need]})
        assert assessment.status_code == 200
        report = assessment.json()
        assert report["assessment"]["verdict"] == "research_further"
        assert report["assessment"]["intent"] == "unknown"
        assert report["assessment"]["compatibility"] == "supported"
        assert report["profile_revision"] == 1
        assert report["persisted_assessment"] is False
        assert report["article_independently_verified"] is False
        fabricated = {**need, "locator": "invented offline sync phrase"}
        assert client.post(assessment_route, json={"needs": [fabricated]}).status_code == 422
        missing = detail + "/signals/" + str(uuid4()) + "/assessment"
        assert client.post(missing, json={"needs": [need]}).status_code == 404
        profiles.save(
            owner,
            workspace,
            answers=ProfileAnswers(
                stage="live",
                name="Updated",
                problem="Different",
                audience="Students",
                capabilities="export",
                missing_capabilities="offline sync",
            ),
            expected_revision=2,
        )
        profiles.confirm(owner, workspace, expected_revision=3)
        assert client.post(assessment_route, json={"needs": [need]}).json() == report
        app.dependency_overrides[get_verified_principal] = lambda: outsider
        assert client.get(detail).status_code == 404
        assert client.post(assessment_route, json={"needs": [need]}).status_code == 404
    with database.transaction(outsider) as session:
        assert session.scalar(text("SELECT count(*) FROM axiom.research_runs")) == 0
    with pytest.raises(DBAPIError):
        with database.transaction(owner) as session:
            session.execute(text("UPDATE axiom.research_runs SET result = '{}'::jsonb"))
