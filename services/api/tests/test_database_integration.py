"""Real PostgreSQL M1 contract tests; never use SQLite/mocks for RLS evidence."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError

from app.auth import VerifiedPrincipal
from app.database import Database, _pg_url
from app.main import create_app
from app.models import AppUser, Workspace, WorkspaceCreateIdempotency
from app.settings import RuntimeSettings
from app.workspace_store import (
    AccountDisabled,
    IdempotencyConflict,
    InvalidWorkspaceInput,
    ProvisioningRequired,
    WorkspaceStore,
    canonical_name,
)

pytestmark = pytest.mark.postgres


@pytest.fixture(scope="module")
def database() -> Database:
    url = os.environ.get("AXIOM_TEST_RUNTIME_DATABASE_URL")
    if not url:
        pytest.skip("Set AXIOM_TEST_RUNTIME_DATABASE_URL to an isolated real PostgreSQL")
    instance = Database(RuntimeSettings(database_url=url, database_required=True))
    yield instance
    instance.close()


@pytest.fixture(scope="module")
def privileged_engine():
    url = os.environ.get("AXIOM_MIGRATION_DATABASE_URL")
    if not url:
        pytest.skip("A separate migration-only PostgreSQL role is required")
    engine = create_engine(_pg_url(url))
    yield engine
    engine.dispose()


def subject() -> VerifiedPrincipal:
    return VerifiedPrincipal(user_id=uuid4(), session_id=None)


def test_migration_schema_indexes_rls_and_role_separation(database: Database) -> None:
    assert database.ready()
    with database.engine.connect() as conn:
        rows = conn.execute(
            text(
                """SELECT c.relname, c.relrowsecurity
                   FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
                   WHERE n.nspname='axiom' AND c.relkind='r'"""
            )
        ).all()
        assert {row.relname for row in rows} == {
            "app_users",
            "workspaces",
            "workspace_create_idempotency",
            "product_profiles",
            "profile_versions",
            "leads",
            "lead_events",
            "scenario_comparisons",
        }
        assert all(row.relrowsecurity for row in rows)
        assert conn.scalar(text("SELECT current_user")) == "axiom_runtime"
        assert (
            conn.scalar(
                text(
                    """SELECT count(*) FROM pg_indexes WHERE schemaname='axiom'
                   AND indexname='ix_workspaces_owner_created_id'"""
                )
            )
            == 1
        )
        assert conn.scalar(text("SELECT count(*) FROM pg_policies WHERE schemaname='axiom'")) == 19
        assert not conn.scalar(text("SELECT has_schema_privilege(current_user,'axiom','CREATE')"))


def test_bootstrap_is_idempotent_concurrent_and_creates_no_workspaces(
    database: Database,
) -> None:
    store = WorkspaceStore(database)
    actor = subject()
    with ThreadPoolExecutor(max_workers=6) as pool:
        outcomes = list(pool.map(lambda _: store.bootstrap(actor), range(6)))
    assert sum(int(outcome.created) for outcome in outcomes) == 1
    assert all(outcome.status == "active" for outcome in outcomes)
    assert store.list_workspaces(actor) == []
    assert store.bootstrap(actor).created is False
    with database.transaction(actor) as session:
        assert (
            session.scalar(select(AppUser.created_at).where(AppUser.id == actor.user_id))
            is not None
        )


def test_unprovisioned_subject_denied_and_invalid_names(database: Database) -> None:
    store = WorkspaceStore(database)
    actor = subject()
    with pytest.raises(ProvisioningRequired):
        store.list_workspaces(actor)
    with pytest.raises(ProvisioningRequired):
        store.create_workspace(actor, name="Valid", key="safeKey888")
    for unsafe in ("", "  ", "\t", "hello\nworld", "a" * 121, "\ud800"):
        with pytest.raises(InvalidWorkspaceInput):
            canonical_name(unsafe)
    assert canonical_name("  Café 产品  ") == "Café 产品"
    assert len(canonical_name("a" * 120)) == 120


def test_disabled_states_survive_repeated_bootstrap(database: Database, privileged_engine) -> None:
    store = WorkspaceStore(database)
    for state in ("suspended", "deprovisioned"):
        actor = subject()
        assert store.bootstrap(actor).created
        with privileged_engine.begin() as conn:
            conn.execute(
                text("UPDATE axiom.app_users SET status=:status WHERE id=:id"),
                {"status": state, "id": actor.user_id},
            )
        with pytest.raises(AccountDisabled):
            store.bootstrap(actor)
        with pytest.raises(AccountDisabled):
            store.list_workspaces(actor)
        with database.transaction(actor) as session:
            assert (
                session.scalar(select(AppUser.status).where(AppUser.id == actor.user_id)) == state
            )


def test_two_workspaces_same_name_and_durable_idempotency(
    database: Database,
) -> None:
    store = WorkspaceStore(database)
    actor = subject()
    store.bootstrap(actor)
    initial = store.create_workspace(actor, name="  Same product  ", key="firstRequestKey8")
    assert not initial.replayed and initial.response_status == 201
    replay = store.create_workspace(actor, name="Same product", key="firstRequestKey8")
    assert replay.replayed and replay.response_body == initial.response_body
    with pytest.raises(IdempotencyConflict):
        store.create_workspace(actor, name="Changed product", key="firstRequestKey8")
    second = store.create_workspace(actor, name="Same product", key="secondRequestKey8")
    assert second.response_body["id"] != initial.response_body["id"]
    assert len(store.list_workspaces(actor)) == 2
    assert store.list_workspaces(actor)[0]["id"] == second.response_body["id"]
    with database.transaction(actor) as session:
        record = session.scalar(
            select(WorkspaceCreateIdempotency).where(
                WorkspaceCreateIdempotency.owner_user_id == actor.user_id,
                WorkspaceCreateIdempotency.key == "firstRequestKey8",
            )
        )
        assert record is not None
        assert record.expires_at >= record.created_at + __import__("datetime").timedelta(hours=24)
    fresh = Database(RuntimeSettings(database_url=os.environ["AXIOM_TEST_RUNTIME_DATABASE_URL"]))
    try:
        after_restart = WorkspaceStore(fresh).create_workspace(
            actor, name="Same product", key="firstRequestKey8"
        )
        assert after_restart.replayed and after_restart.response_body == initial.response_body
    finally:
        fresh.close()


def test_concurrent_same_key_creates_exactly_one(database: Database) -> None:
    store = WorkspaceStore(database)
    actor = subject()
    store.bootstrap(actor)
    with ThreadPoolExecutor(max_workers=6) as pool:
        responses = list(
            pool.map(
                lambda _: store.create_workspace(
                    actor, name="Concurrent product", key="concurrentRequest99"
                ),
                range(6),
            )
        )
    assert all(response.response_body == responses[0].response_body for response in responses)
    assert sum(not response.replayed for response in responses) == 1
    assert len(store.list_workspaces(actor)) == 1


def test_nonowner_rls_and_runtime_does_not_have_ddl(database: Database) -> None:
    store = WorkspaceStore(database)
    a, b = subject(), subject()
    store.bootstrap(a)
    store.bootstrap(b)
    b_workspace = store.create_workspace(b, name="Private B", key="privateKeyForB99")
    b_id = b_workspace.response_body["id"]
    assert store.list_workspaces(a) == []
    with database.transaction(a) as session:
        assert session.scalar(select(Workspace).where(Workspace.id == b_id)) is None
        assert (
            session.execute(
                text("UPDATE axiom.workspaces SET name='stolen' WHERE id=:id"),
                {"id": b_id},
            ).rowcount
            == 0
        )
    with pytest.raises(DBAPIError):
        with database.transaction(a) as session:
            session.execute(
                text(
                    """INSERT INTO axiom.workspaces (id,owner_user_id,name)
                       VALUES (:id,:owner,'Forbidden')"""
                ),
                {"id": uuid4(), "owner": b.user_id},
            )
    with pytest.raises(DBAPIError):
        with database.transaction(a) as session:
            session.execute(text("ALTER TABLE axiom.workspaces DISABLE ROW LEVEL SECURITY"))
    with pytest.raises(DBAPIError):
        with database.transaction(a) as session:
            session.execute(text("CREATE TABLE axiom.forbidden (id integer)"))
    assert store.list_workspaces(b)[0]["name"] == "Private B"


def test_owner_mutation_and_database_constraints(database: Database, privileged_engine) -> None:
    store = WorkspaceStore(database)
    actor, other = subject(), subject()
    store.bootstrap(actor)
    store.bootstrap(other)
    ws = store.create_workspace(actor, name="Valid", key="validWorkspaceKey88")
    with database.transaction(actor) as session:
        assert (
            session.execute(
                text("UPDATE axiom.workspaces SET name='Updated',version=version+1 WHERE id=:id"),
                {"id": ws.response_body["id"]},
            ).rowcount
            == 1
        )
    assert store.list_workspaces(actor)[0]["version"] == 2
    with pytest.raises(DBAPIError):
        with database.transaction(actor) as session:
            session.execute(
                text("UPDATE axiom.workspaces SET owner_user_id=:other WHERE id=:id"),
                {"other": other.user_id, "id": ws.response_body["id"]},
            )
    for invalid in ("", "   ", "a" * 121, "bad\nname", "\u00a0padded"):
        with pytest.raises(DBAPIError):
            with privileged_engine.begin() as conn:
                conn.execute(
                    text(
                        """INSERT INTO axiom.workspaces (id,owner_user_id,name)
                           VALUES (:id,:owner,:name)"""
                    ),
                    {"id": uuid4(), "owner": actor.user_id, "name": invalid},
                )
    with pytest.raises(DBAPIError):
        with privileged_engine.begin() as conn:
            conn.execute(
                text(
                    """INSERT INTO axiom.workspaces (id,owner_user_id,name,version)
                       VALUES (:id,:owner,'Broken',0)"""
                ),
                {"id": uuid4(), "owner": actor.user_id},
            )
    with pytest.raises(DBAPIError):
        with privileged_engine.begin() as conn:
            conn.execute(
                text(
                    """INSERT INTO axiom.workspaces (id,owner_user_id,name)
                       VALUES (:id,:owner,'Dangling')"""
                ),
                {"id": uuid4(), "owner": uuid4()},
            )
    with pytest.raises(DBAPIError):
        with privileged_engine.begin() as conn:
            conn.execute(text("DELETE FROM axiom.app_users WHERE id=:id"), {"id": actor.user_id})
    assert len(store.list_workspaces(actor)) == 1


def test_absent_invalid_identity_and_session_pool_reuse(database: Database) -> None:
    store = WorkspaceStore(database)
    a, b = subject(), subject()
    store.bootstrap(a)
    store.bootstrap(b)
    store.create_workspace(a, name="A only", key="ownPoolRequestA88")
    store.create_workspace(b, name="B only", key="ownPoolRequestB88")
    for actor in (a, b, a):
        with database.transaction(actor) as session:
            assert session.scalar(text("SELECT axiom.current_subject()")) == actor.user_id
            assert len(store.list_workspaces(actor)) == 1  # separate committed connection
        with database.engine.connect() as conn:
            assert conn.scalar(text("SELECT axiom.current_subject()")) is None
            assert conn.scalar(text("SELECT count(*) FROM axiom.workspaces")) == 0
    with database.engine.connect() as conn:
        conn.execute(text("SELECT set_config('app.current_user_id','not-a-uuid',true)"))
        assert conn.scalar(text("SELECT axiom.current_subject()")) is None
    try:
        with database.transaction(a) as session:
            assert session.scalar(text("SELECT axiom.current_subject()")) == a.user_id
            raise RuntimeError("test rollback")
    except RuntimeError:
        pass
    with database.engine.connect() as conn:
        assert conn.scalar(text("SELECT axiom.current_subject()")) is None
    with ThreadPoolExecutor(max_workers=4) as pool:
        users = (a, b) * 8
        result = list(pool.map(lambda actor: store.list_workspaces(actor), users))
    assert all(len(items) == 1 for items in result)
    assert {items[0]["name"] for items in result} == {"A only", "B only"}


def test_privileged_table_owner_bypasses_rls(database: Database, privileged_engine) -> None:
    store = WorkspaceStore(database)
    a, b = subject(), subject()
    store.bootstrap(a)
    store.bootstrap(b)
    store.create_workspace(a, name="Owner A", key="privilegedOwnerA88")
    store.create_workspace(b, name="Owner B", key="privilegedOwnerB88")
    with database.transaction(a) as session:
        assert len(session.scalars(select(Workspace)).all()) == 1
    with privileged_engine.connect() as conn:
        assert conn.scalar(text("SELECT current_user")) == "axiom_migrator"
        assert conn.scalar(text("SELECT count(*) FROM axiom.workspaces")) >= 2
        assert conn.scalar(text("SELECT axiom.current_subject()")) is None
    # This is NOT proof that the future FastAPI routes authorize privileged sessions.


def test_real_db_readiness_and_safe_unreachable_failure(database: Database) -> None:
    url = os.environ["AXIOM_TEST_RUNTIME_DATABASE_URL"]
    with TestClient(
        create_app(RuntimeSettings(database_url=url, database_required=True))
    ) as client:
        assert client.get("/api/v1/health/live").status_code == 200
        ready = client.get("/api/v1/health/ready")
        assert ready.status_code == 200
        assert ready.json()["dependencies"] == "database_verified"
    fake_password = "redaction" + "probe"
    unreachable_url = f"postgresql://test_user:{fake_password}@127.0.0.1:55433/axiom_test"
    with TestClient(create_app(RuntimeSettings(database_url=unreachable_url))) as client:
        ready = client.get("/api/v1/health/ready")
        assert ready.status_code == 503
        assert fake_password not in ready.text
        assert client.get("/api/v1/health/live").status_code == 200
    with TestClient(
        create_app(RuntimeSettings(database_url=os.environ["AXIOM_MIGRATION_DATABASE_URL"]))
    ) as client:
        assert client.get("/api/v1/health/ready").status_code == 503


def test_readiness_fails_on_revoked_runtime_schema_and_function_grants(
    database: Database, privileged_engine
) -> None:
    assert database.ready()
    scenarios = (
        (
            "REVOKE USAGE ON SCHEMA axiom FROM axiom_runtime",
            "GRANT USAGE ON SCHEMA axiom TO axiom_runtime",
        ),
        (
            "REVOKE EXECUTE ON FUNCTION axiom.current_subject() FROM axiom_runtime",
            "GRANT EXECUTE ON FUNCTION axiom.current_subject() TO axiom_runtime",
        ),
    )
    for revoke, restore in scenarios:
        with privileged_engine.begin() as conn:
            conn.execute(text(revoke))
        try:
            assert not database.ready()
            with TestClient(
                create_app(
                    RuntimeSettings(
                        database_url=os.environ["AXIOM_TEST_RUNTIME_DATABASE_URL"],
                        database_required=True,
                    )
                )
            ) as client:
                assert client.get("/api/v1/health/ready").status_code == 503
                assert client.get("/api/v1/health/live").status_code == 200
        finally:
            with privileged_engine.begin() as conn:
                conn.execute(text(restore))
        assert database.ready()


def test_runtime_pool_exhaustion_marks_readiness_unhealthy_then_recovers(
    database: Database,
) -> None:
    app = create_app(
        RuntimeSettings(
            database_url=os.environ["AXIOM_TEST_RUNTIME_DATABASE_URL"],
            database_required=True,
        )
    )
    with TestClient(app) as client:
        assert client.get("/api/v1/health/ready").status_code == 200
        assert app.state.database is not None
        with ExitStack() as held:
            for _ in range(4):
                held.enter_context(app.state.database.engine.connect())
            response = client.get("/api/v1/health/ready")
            assert response.status_code == 503
            assert response.json()["dependencies"] == "database_not_verified"
            assert client.get("/api/v1/health/live").status_code == 200
        assert client.get("/api/v1/health/ready").status_code == 200


def test_missing_required_rls_policies_fail_readiness(
    database: Database, privileged_engine
) -> None:
    # These policies are needed for bootstrap and owner-scoped workspace writes.
    scenarios = (
        (
            "app_user_own_read",
            "axiom.app_users",
            """CREATE POLICY app_user_own_read ON axiom.app_users
               FOR SELECT TO axiom_runtime
               USING (id = axiom.current_subject())""",
        ),
        (
            "workspace_create_idempotency_own_insert",
            "axiom.workspace_create_idempotency",
            """CREATE POLICY workspace_create_idempotency_own_insert
               ON axiom.workspace_create_idempotency
               FOR INSERT TO axiom_runtime
               WITH CHECK (
                   owner_user_id = axiom.current_subject()
                   AND EXISTS (
                       SELECT 1 FROM axiom.app_users a
                       WHERE a.id = axiom.current_subject() AND a.status = 'active'
                   )
               )""",
        ),
    )
    for policy, table, restore_sql in scenarios:
        assert database.ready()
        # Real DROP commits before readiness opens its own unprivileged session.
        with privileged_engine.begin() as conn:
            conn.execute(text(f"DROP POLICY {policy} ON {table}"))  # noqa: S608
        try:
            assert not database.ready()
        finally:
            with privileged_engine.begin() as conn:
                conn.execute(text(restore_sql))
        assert database.ready()


def test_missing_required_column_grants_fail_readiness(
    database: Database, privileged_engine
) -> None:
    scenarios = (
        ("axiom.app_users", "id", "INSERT"),
        ("axiom.workspaces", "id", "INSERT"),
        ("axiom.workspaces", "owner_user_id", "INSERT"),
        ("axiom.workspaces", "updated_at", "UPDATE"),
        ("axiom.workspaces", "version", "UPDATE"),
        ("axiom.workspace_create_idempotency", "operation", "INSERT"),
        ("axiom.workspace_create_idempotency", "key", "INSERT"),
        ("axiom.workspace_create_idempotency", "expires_at", "INSERT"),
    )
    for table, column, action in scenarios:
        assert database.ready()
        with privileged_engine.begin() as conn:
            revoke_sql = f"REVOKE {action} ({column}) ON {table} FROM axiom_runtime"
            conn.execute(text(revoke_sql))  # noqa: S608
        try:
            assert not database.ready()
        finally:
            with privileged_engine.begin() as conn:
                grant_sql = f"GRANT {action} ({column}) ON {table} TO axiom_runtime"
                conn.execute(text(grant_sql))  # noqa: S608
        assert database.ready()
