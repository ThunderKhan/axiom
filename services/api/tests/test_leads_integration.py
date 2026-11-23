"""Real PostgreSQL tenant isolation, replay safety, revision races and audit history."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.auth import VerifiedPrincipal
from app.database import Database
from app.leads_contract import CreateLead, PatchLead
from app.leads_store import InvalidLeadInput, LeadAlreadySaved, LeadStore
from app.settings import RuntimeSettings
from app.workspace_store import (
    IdempotencyConflict,
    VersionConflict,
    WorkspaceNotFound,
    WorkspaceStore,
)

pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def database():
    url = os.environ.get("AXIOM_TEST_RUNTIME_DATABASE_URL")
    if not url:
        pytest.skip("Only isolated real PostgreSQL with runtime role is accepted")
    database = Database(RuntimeSettings(database_url=url, database_required=True))
    yield database
    database.close()


def actor() -> VerifiedPrincipal:
    return VerifiedPrincipal(user_id=uuid4(), session_id=None)


def workspace(store: WorkspaceStore, owner: VerifiedPrincipal) -> UUID:
    store.bootstrap(owner)
    result = store.create_workspace(owner, name="Lead acceptance", key="key-" + uuid4().hex)
    return UUID(str(result.response_body["id"]))


def sample(*, note: str = "", source_url: str = "https://example.org/manual") -> CreateLead:
    return CreateLead(
        title="Customer needs offline data",
        source_url=source_url,
        source_excerpt="A customer explicitly requested offline data",
        note=note,
    )


def test_manual_lead_survives_update_dedupe_and_foreign_workspace_denial(
    database: Database,
) -> None:
    assert database.ready()
    owner, outsider = actor(), actor()
    workspaces, leads = WorkspaceStore(database), LeadStore(database)
    own_id, other_id = workspace(workspaces, owner), workspace(workspaces, outsider)
    key = "create-" + uuid4().hex
    new = leads.create(owner, own_id, payload=sample(), key=key)
    assert not new["already_exists"]
    assert new["source_origin"] == "user_provided"
    assert new["stage"] == "spotted"
    lead_id = UUID(str(new["id"]))
    replay = leads.create(owner, own_id, payload=sample(), key=key)
    assert replay["id"] == lead_id
    assert replay["already_exists"] is True
    duplicate_key = "next-" + uuid4().hex
    with pytest.raises(LeadAlreadySaved):
        leads.create(owner, own_id, payload=sample(), key=duplicate_key)
    with pytest.raises(IdempotencyConflict):
        leads.create(owner, own_id, payload=sample(note="different"), key=key)

    assert [row["id"] for row in leads.list(owner, own_id)["items"]] == [lead_id]
    assert leads.read(owner, own_id, lead_id)["version"] == 1
    with pytest.raises(WorkspaceNotFound):
        leads.read(outsider, own_id, lead_id)
    with pytest.raises(WorkspaceNotFound):
        leads.patch(
            outsider, own_id, lead_id, payload=PatchLead(expected_version=1, stage="contacted")
        )
    with pytest.raises(WorkspaceNotFound):
        leads.read(owner, other_id, lead_id)
    assert leads.list(outsider, other_id)["items"] == []

    changed = leads.patch(
        owner,
        own_id,
        lead_id,
        payload=PatchLead(
            expected_version=1,
            stage="qualified",
            note="Manual outreach considered, not contacted",
            follow_up_at=datetime(2026, 11, 26, tzinfo=UTC),
            follow_up_done=True,
            unsent_draft="Draft only. Nothing has been delivered.",
        ),
    )
    assert changed["version"] == 2
    assert changed["follow_up_done"] is True
    assert "Nothing has been delivered" in str(leads.read(owner, own_id, lead_id)["unsent_draft"])
    assert len(leads.list(owner, own_id, stage="qualified", query="offline")["items"]) == 1
    assert leads.list(owner, own_id, stage="spotted")["items"] == []
    with pytest.raises(VersionConflict):
        leads.patch(owner, own_id, lead_id, payload=PatchLead(expected_version=1, note="stale"))
    with pytest.raises(InvalidLeadInput):
        leads.patch(
            owner,
            own_id,
            lead_id,
            payload=PatchLead(expected_version=2, follow_up_at=None),
        )

    history = leads.history(owner, own_id, lead_id)
    assert [row["event_type"] for row in history] == ["updated", "created"]
    assert "note" in history[0]["changed_fields"]
    assert "Draft only" not in str(history)
    with pytest.raises(WorkspaceNotFound):
        leads.history(outsider, own_id, lead_id)

    leads.archive(owner, own_id, lead_id, expected_version=2)
    assert leads.list(owner, own_id)["items"] == []
    with pytest.raises(WorkspaceNotFound):
        leads.read(owner, own_id, lead_id)
    with pytest.raises(IdempotencyConflict):
        leads.create(owner, own_id, payload=sample(), key=key)
    with pytest.raises(WorkspaceNotFound):
        leads.archive(owner, own_id, lead_id, expected_version=2)
    with database.transaction(owner) as session:
        retained = session.scalar(
            text("SELECT count(*) FROM axiom.lead_events WHERE lead_id = :lead"),
            {"lead": lead_id},
        )
    assert retained == 3
    # The rejected duplicate key was never accepted; it remains safe for a new URL.
    distinct = leads.create(
        owner,
        own_id,
        payload=sample(source_url="https://example.org/different"),
        key=duplicate_key,
    )
    assert distinct["already_exists"] is False


def test_composite_fk_and_runtime_columns_resist_cross_workspace_mutation(
    database: Database,
) -> None:
    workspaces, leads = WorkspaceStore(database), LeadStore(database)
    owner, outsider = actor(), actor()
    own_id, other_id = workspace(workspaces, owner), workspace(workspaces, outsider)
    lead = leads.create(
        owner,
        own_id,
        payload=sample(source_url="https://example.org/more"),
        key="key-" + uuid4().hex,
    )
    lead_id = lead["id"]
    with database.transaction(outsider) as session:
        assert (
            session.execute(
                text("SELECT count(*) FROM axiom.leads WHERE id=:lead"),
                {"lead": lead_id},
            ).scalar_one()
            == 0
        )
    with pytest.raises(DBAPIError) as exc:
        with database.transaction(outsider) as session:
            session.execute(
                text(
                    "INSERT INTO axiom.lead_events "
                    "(id, workspace_id, lead_id, actor_id, event_type, changed_fields) "
                    "VALUES (:id, :ws, :lead, :actor, 'created', '[]'::jsonb)"
                ),
                {"id": uuid4(), "ws": other_id, "lead": lead_id, "actor": outsider.user_id},
            )
    assert getattr(exc.value.orig, "sqlstate", None) in {"23503", "42501"}
    with pytest.raises(DBAPIError) as exc:
        with database.transaction(owner) as session:
            session.execute(
                text(
                    "UPDATE axiom.leads SET source_url='https://example.org/altered' WHERE id=:id"
                ),
                {"id": lead_id},
            )
    assert getattr(exc.value.orig, "sqlstate", None) == "42501"
    with pytest.raises(DBAPIError) as exc:
        with database.transaction(owner) as session:
            session.execute(
                text("DELETE FROM axiom.lead_events WHERE lead_id=:id"), {"id": lead_id}
            )
    assert getattr(exc.value.orig, "sqlstate", None) == "42501"
