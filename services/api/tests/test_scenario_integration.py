"""Real PostgreSQL persistence, idempotency and tenant isolation for scenario sets."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.auth import VerifiedPrincipal, get_verified_principal
from app.database import Database
from app.leads_contract import CreateLead, PatchLead
from app.leads_store import LeadStore
from app.main import create_app
from app.profile_contract import ProfileAnswers
from app.profile_store import ProfileStore
from app.settings import RuntimeSettings
from app.workspace_store import WorkspaceStore

pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def database():
    raw = os.environ.get("AXIOM_TEST_RUNTIME_DATABASE_URL")
    if not raw:
        pytest.skip("Only isolated PostgreSQL runtime credentials are accepted")
    instance = Database(RuntimeSettings(database_url=raw, database_required=True))
    yield instance
    instance.close()


def workspace(database: Database, actor: VerifiedPrincipal) -> UUID:
    store = WorkspaceStore(database)
    store.bootstrap(actor)
    result = store.create_workspace(actor, name="Scenario test", key="key-" + uuid4().hex)
    return UUID(str(result.response_body["id"]))


def test_saved_comparison_reopens_and_preserves_frozen_baseline(database: Database) -> None:
    assert database.ready()
    owner, outsider = VerifiedPrincipal(uuid4(), None), VerifiedPrincipal(uuid4(), None)
    wid = workspace(database, owner)
    other = workspace(database, outsider)
    profiles = ProfileStore(database)
    answers = ProfileAnswers(
        stage="live",
        name="Notes",
        problem="Offline notes",
        audience="Students",
        capabilities="offline sync",
    )
    profiles.save(owner, wid, answers=answers, expected_revision=0)
    profiles.confirm(owner, wid, expected_revision=1)
    leads = LeadStore(database)
    lead = leads.create(
        owner,
        wid,
        payload=CreateLead(
            title="Notes research",
            source_url="https://example.org/scenario",
            source_excerpt="A student needs offline sync for notes",
        ),
        key="lead-" + uuid4().hex,
    )
    lid = UUID(str(lead["id"]))
    body = {
        "needs": [{"requirement": "offline sync", "locator": "offline sync", "intent": "buying"}],
        "expected_lead_version": 1,
        "expected_profile_revision": 1,
        "scenarios": [
            {
                "name": "Remove sync",
                "features": [{"name": "offline sync", "action": "remove"}],
                "pricing": "Lower price",
            },
            {
                "name": "Explore export",
                "features": [{"name": "export", "action": "add"}],
                "positioning": "Students",
            },
        ],
    }
    key = "scenario-" + uuid4().hex
    route = f"/api/v1/workspaces/{wid}/leads/{lid}/scenario-comparisons"
    app = create_app(RuntimeSettings())
    app.state.database = database
    app.dependency_overrides[get_verified_principal] = lambda: owner
    with TestClient(app) as client:
        response = client.post(route, json=body, headers={"Idempotency-Key": key})
        assert response.status_code == 201
        saved = response.json()
        assert saved["persisted_comparison"] is True
        assert saved["live_source_verified"] is False
        assert saved["comparison"]["baseline_verdict"] == "research_further"
        assert len(saved["comparison"]["scenarios"]) == 2
        replay = client.post(route, json=body, headers={"Idempotency-Key": key})
        assert replay.status_code == 200
        assert replay.json() == saved
        conflict = client.post(route, json={**body, "needs": []}, headers={"Idempotency-Key": key})
        assert conflict.status_code == 409
        leads.patch(owner, wid, lid, payload=PatchLead(expected_version=1, note="New note"))
        stale = client.post(route, json=body, headers={"Idempotency-Key": "new-" + uuid4().hex})
        assert stale.status_code == 409
        assert client.get(route).json()["items"] == [saved]
        app.dependency_overrides[get_verified_principal] = lambda: outsider
        assert client.get(route).status_code == 404
        assert client.post(route, json=body, headers={"Idempotency-Key": key}).status_code == 404
        foreign = f"/api/v1/workspaces/{other}/leads/{lid}/scenario-comparisons"
        assert client.get(foreign).status_code == 404
    # Fresh app and verified principal: database state, not process-local memory.
    reopened = create_app(RuntimeSettings())
    reopened.state.database = database
    reopened.dependency_overrides[get_verified_principal] = lambda: owner
    with TestClient(reopened) as client:
        assert client.get(route).json()["items"] == [saved]
    with database.transaction(outsider) as session:
        assert session.scalar(text("SELECT count(*) FROM axiom.scenario_comparisons")) == 0
    with pytest.raises(DBAPIError):
        with database.transaction(owner) as session:
            session.execute(
                text("UPDATE axiom.scenario_comparisons SET result = '{}'::jsonb WHERE id = :id"),
                {"id": UUID(saved["id"])},
            )
