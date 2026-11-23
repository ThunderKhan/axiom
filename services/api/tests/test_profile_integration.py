"""Genuine PostgreSQL runtime-role profile isolation and append-only version tests."""

from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.auth import VerifiedPrincipal
from app.database import Database
from app.profile_contract import ProfileAnswers
from app.profile_store import ProfileIncomplete, ProfileStore
from app.settings import RuntimeSettings
from app.workspace_store import VersionConflict, WorkspaceNotFound, WorkspaceStore

pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def database():
    raw = os.environ.get("AXIOM_TEST_RUNTIME_DATABASE_URL")
    if not raw:
        pytest.skip("Only the guarded isolated PostgreSQL runner may provide runtime credentials")
    instance = Database(RuntimeSettings(database_url=raw, database_required=True))
    yield instance
    instance.close()


def _actor() -> VerifiedPrincipal:
    return VerifiedPrincipal(user_id=uuid4(), session_id=None)


def _workspace(store: WorkspaceStore, actor: VerifiedPrincipal) -> UUID:
    store.bootstrap(actor)
    value = store.create_workspace(actor, name="Profile test", key="key-" + uuid4().hex)
    return UUID(str(value.response_body["id"]))


def _answers(name: str, *, stage: str = "idea") -> ProfileAnswers:
    return ProfileAnswers.model_validate(
        {
            "name": name,
            "stage": stage,
            "problem": "Researchers cannot find enough evidence",
            "audience": "Founders",
            "capabilities": "Proposed sourced comparisons"
            if stage == "idea"
            else "Existing customer research reports",
            "website_url": "https://example.org",
        }
    )


def test_resumable_profile_is_owner_scoped_and_versions_are_immutable(database: Database) -> None:
    assert database.ready()
    workspaces = WorkspaceStore(database)
    profiles = ProfileStore(database)
    alice, bob = _actor(), _actor()
    alice_id = _workspace(workspaces, alice)
    _workspace(workspaces, bob)

    assert profiles.read(alice, alice_id) == {
        "draft_revision": 0,
        "draft_step": 0,
        "answers": None,
        "confirmed_revision": 0,
        "confirmed": None,
    }
    with pytest.raises(WorkspaceNotFound):
        profiles.read(bob, alice_id)
    with pytest.raises(WorkspaceNotFound):
        profiles.save(bob, alice_id, answers=_answers("Bad"), expected_revision=0)

    first = profiles.save(
        alice, alice_id, answers=ProfileAnswers(name="Incomplete"), expected_revision=0
    )
    assert first["draft_revision"] == 1
    with pytest.raises(ProfileIncomplete):
        profiles.confirm(alice, alice_id, expected_revision=1)
    with pytest.raises(VersionConflict):
        profiles.save(alice, alice_id, answers=_answers("Stale"), expected_revision=0)

    saved = profiles.save(
        alice, alice_id, answers=_answers("Idea"), expected_revision=1, draft_step=7
    )
    assert saved["draft_revision"] == 2
    assert saved["draft_step"] == 7
    assert profiles.read(alice, alice_id)["draft_step"] == 7
    confirmed = profiles.confirm(alice, alice_id, expected_revision=2)
    assert confirmed["confirmed_revision"] == 1
    assert confirmed["draft_revision"] == 3  # Replayed POST cannot mint a second version.
    assert confirmed["confirmed"]["answers"]["name"] == "Idea"
    immutable_id = confirmed["confirmed"]["id"]
    with pytest.raises(VersionConflict):
        profiles.confirm(alice, alice_id, expected_revision=2)

    next_draft = profiles.save(
        alice, alice_id, answers=_answers("Live", stage="live"), expected_revision=3
    )
    assert next_draft["confirmed"]["id"] == immutable_id
    assert next_draft["confirmed"]["answers"]["name"] == "Idea"
    newer = profiles.confirm(alice, alice_id, expected_revision=4)
    assert newer["confirmed_revision"] == 2
    assert newer["confirmed"]["id"] != immutable_id
    assert profiles.read(alice, alice_id)["confirmed"]["answers"]["name"] == "Live"
    with database.transaction(alice) as session:
        oldest = session.execute(
            text("SELECT revision, answers FROM axiom.profile_versions WHERE id=:id"),
            {"id": immutable_id},
        ).one()
        assert oldest.revision == 1 and oldest.answers["name"] == "Idea"
    with database.transaction(bob) as session:
        assert (
            session.execute(
                text("SELECT count(*) FROM axiom.profile_versions WHERE workspace_id=:wid"),
                {"wid": alice_id},
            ).scalar_one()
            == 0
        )


def test_runtime_refuses_direct_foreign_insert_and_mutation_of_confirmed_versions(
    database: Database,
) -> None:
    workspaces, profiles = WorkspaceStore(database), ProfileStore(database)
    owner, outsider = _actor(), _actor()
    owned_id = _workspace(workspaces, owner)
    _workspace(workspaces, outsider)
    profile = profiles.save(owner, owned_id, answers=_answers("Immutable"), expected_revision=0)
    result = profiles.confirm(owner, owned_id, expected_revision=int(profile["draft_revision"]))
    version_id = result["confirmed"]["id"]

    with pytest.raises(DBAPIError) as exc:
        with database.transaction(outsider) as session:
            session.execute(
                text(
                    "INSERT INTO axiom.profile_versions "
                    "(id, workspace_id, revision, answers) "
                    "VALUES (:id, :workspace_id, 900, '{}'::jsonb)"
                ),
                {"id": uuid4(), "workspace_id": owned_id},
            )
    assert getattr(exc.value.orig, "sqlstate", None) == "42501"

    with pytest.raises(DBAPIError) as exc:
        with database.transaction(owner) as session:
            session.execute(
                text("UPDATE axiom.profile_versions SET revision=999 WHERE id=:id"),
                {"id": version_id},
            )
    assert getattr(exc.value.orig, "sqlstate", None) == "42501"
    assert profiles.read(owner, owned_id)["confirmed_revision"] == 1
