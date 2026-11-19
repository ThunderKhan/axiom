"""M1.5 HTTP + real isolated PostgreSQL acceptance: actual signatures, ownership and RLS."""

from __future__ import annotations

import base64
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm
from pydantic import SecretStr
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.exc import DBAPIError

from app.auth import JwtVerifier, VerifiedPrincipal
from app.database import Database, _pg_url
from app.main import create_app
from app.models import Workspace, WorkspaceCreateIdempotency
from app.settings import RuntimeSettings
from app.workspace_store import WorkspaceNotFound, WorkspaceStore

pytestmark = pytest.mark.postgres
ISSUER = "https://axiomtest.supabase.co/auth/v1"


@pytest.fixture(scope="module")
def api():
    url = os.environ.get("AXIOM_TEST_RUNTIME_DATABASE_URL")
    if not url:
        pytest.skip("Use isolated local PostgreSQL runner for HTTP/real DB acceptance")
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = {
        **json.loads(RSAAlgorithm.to_jwk(private.public_key())),
        "kid": "m1-workspace-tests",
        "alg": "RS256",
        "use": "sig",
    }
    settings = RuntimeSettings(
        database_url=url,
        database_required=True,
        auth_issuer=ISSUER,
        auth_audience="authenticated",
        auth_jwks_url=ISSUER + "/.well-known/jwks.json",
    )
    app = create_app(settings)
    app.state.jwt_verifier = JwtVerifier(settings, fetcher=lambda _: {"keys": [jwk]})
    with TestClient(app) as client:
        yield client, private, settings


@pytest.fixture(scope="module")
def privileged_engine():
    url = os.environ.get("AXIOM_MIGRATION_DATABASE_URL")
    if not url:
        pytest.skip("The isolated migration-only role is required")
    engine = create_engine(_pg_url(url))
    yield engine
    engine.dispose()


def headers(private, user: UUID | None = None, **changes: object) -> dict[str, str]:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": ISSUER,
        "aud": "authenticated",
        "iat": now,
        "exp": now + 3600,
        "role": "authenticated",
        "sub": str(user if user is not None else uuid4()),
    }
    claims.update(changes)
    token = jwt.encode(claims, private, algorithm="RS256", headers={"kid": "m1-workspace-tests"})
    return {"Authorization": "Bearer " + token}


def create(client: TestClient, auth: dict[str, str], name: str, key: str):
    return client.post(
        "/api/v1/workspaces",
        json={"name": name},
        headers={**auth, "Idempotency-Key": key},
    )


def bootstrap(client: TestClient, auth: dict[str, str]) -> None:
    assert client.post("/api/v1/me/bootstrap", headers=auth).status_code == 201


def assert_error(result, status: int, code: str) -> dict[str, object]:
    assert result.status_code == status, result.text
    document = result.json()
    assert set(document) == {"error", "request_id"}
    assert set(document["error"]) == {"code", "message", "retryable", "details"}
    assert document["error"]["code"] == code
    assert document["error"]["details"] == {}
    assert document["request_id"].startswith("req_")
    assert "Traceback" not in result.text
    return document["error"]


def test_bootstrap_read_only_me_multiowner_crud_and_foreign_idor(api, privileged_engine) -> None:
    client, private, _settings = api
    a, b = uuid4(), uuid4()
    aa, bb = headers(private, a), headers(private, b)

    assert_error(client.get("/api/v1/me", headers=aa), 409, "PROVISIONING_REQUIRED")
    assert_error(client.get("/api/v1/workspaces", headers=aa), 409, "PROVISIONING_REQUIRED")
    created = client.post("/api/v1/me/bootstrap", headers=aa)
    assert created.status_code == 201
    assert created.json()["created"] is True
    assert created.json()["user"]["id"] == str(a)
    assert created.json()["user"]["status"] == "active"
    assert len(created.json()["user"]) == 3
    repeated = client.post("/api/v1/me/bootstrap", headers=aa)
    assert repeated.status_code == 200
    assert repeated.json()["created"] is False
    assert repeated.json()["user"] == created.json()["user"]
    assert client.get("/api/v1/me", headers=aa).json() == created.json()["user"]
    assert_error(
        client.post("/api/v1/me/bootstrap", json={"id": str(b)}, headers=aa),
        422,
        "VALIDATION_FAILED",
    )
    bootstrap(client, bb)

    a1 = create(client, aa, "  First product ", "ownerA-first-189").json()
    a2 = create(client, aa, "Second product", "ownerA-second-189").json()
    b1 = create(client, bb, "Private B", "ownerB-first-189").json()
    assert a1["name"] == "First product"
    assert len({a1["id"], a2["id"], b1["id"]}) == 3
    assert a1["version"] == a2["version"] == 1
    listed_a = client.get("/api/v1/workspaces", headers=aa).json()
    listed_b = client.get("/api/v1/workspaces", headers=bb).json()
    assert set(item["id"] for item in listed_a["items"]) == {a1["id"], a2["id"]}
    assert [item["id"] for item in listed_b["items"]] == [b1["id"]]
    assert listed_a["next_cursor"] is None
    assert client.get("/api/v1/workspaces/" + a1["id"], headers=aa).json() == a1

    foreign = assert_error(
        client.get("/api/v1/workspaces/" + b1["id"], headers=aa), 404, "NOT_FOUND"
    )
    missing = assert_error(
        client.get("/api/v1/workspaces/" + str(uuid4()), headers=aa), 404, "NOT_FOUND"
    )
    assert foreign == missing
    assert_error(
        client.patch(
            "/api/v1/workspaces/" + a1["id"],
            headers=bb,
            json={"name": "Stolen", "expected_version": 1},
        ),
        404,
        "NOT_FOUND",
    )
    assert_error(
        client.patch(
            "/api/v1/workspaces/" + str(uuid4()),
            headers=bb,
            json={"name": "Stolen", "expected_version": 1},
        ),
        404,
        "NOT_FOUND",
    )
    assert_error(
        client.post(
            "/api/v1/workspaces",
            json={"name": "Forgery", "owner_user_id": str(b)},
            headers={**aa, "Idempotency-Key": "ownerSpoofKey88"},
        ),
        422,
        "VALIDATION_FAILED",
    )
    assert client.get("/api/v1/workspaces/" + a1["id"], headers=aa).json() == a1

    with privileged_engine.begin() as conn:
        conn.execute(text("UPDATE axiom.app_users SET status='suspended' WHERE id=:id"), {"id": b})
    try:
        for method, url in (
            ("get", "/api/v1/me"),
            ("get", "/api/v1/workspaces"),
            ("post", "/api/v1/me/bootstrap"),
        ):
            assert_error(getattr(client, method)(url, headers=bb), 403, "ACCOUNT_DISABLED")
        assert_error(
            client.get("/api/v1/workspaces/" + b1["id"], headers=bb), 403, "ACCOUNT_DISABLED"
        )
        with privileged_engine.begin() as conn:
            conn.execute(
                text("UPDATE axiom.app_users SET status='deprovisioned' WHERE id=:id"),
                {"id": b},
            )
        assert_error(client.post("/api/v1/me/bootstrap", headers=bb), 403, "ACCOUNT_DISABLED")
    finally:
        with privileged_engine.begin() as conn:
            conn.execute(text("UPDATE axiom.app_users SET status='active' WHERE id=:id"), {"id": b})


def test_create_idempotency_concurrency_replay_restart_and_expiry(api, privileged_engine) -> None:
    client, private, settings = api
    actor = uuid4()
    auth = headers(private, actor)
    bootstrap(client, auth)
    first = create(client, auth, "  The product  ", "idempotencyKey189")
    assert first.status_code == 201
    replay = create(client, auth, "The product", "idempotencyKey189")
    assert replay.status_code == 201 and replay.json() == first.json()
    assert_error(
        create(client, auth, "Different", "idempotencyKey189"), 409, "IDEMPOTENCY_CONFLICT"
    )
    other = create(client, auth, "The product", "secondKey1888")
    assert other.status_code == 201 and other.json()["id"] != first.json()["id"]

    with ThreadPoolExecutor(max_workers=4) as pool:
        parallel = list(
            pool.map(lambda _: create(client, auth, "Parallel", "parallelUniqueKey189"), range(4))
        )
    assert {result.status_code for result in parallel} == {201}
    assert len({result.json()["id"] for result in parallel}) == 1

    with TestClient(create_app(settings)) as fresh:
        # Supply the same real RSA public key (fixture JWKS fetch, no auth bypass).
        public = json.loads(RSAAlgorithm.to_jwk(private.public_key()))
        fresh.app.state.jwt_verifier = JwtVerifier(
            settings,
            fetcher=lambda _: {
                "keys": [{**public, "kid": "m1-workspace-tests", "alg": "RS256", "use": "sig"}]
            },
        )
        after_restart = create(fresh, auth, "The product", "idempotencyKey189")
        assert after_restart.status_code == 201
        assert after_restart.json() == first.json()

    with privileged_engine.connect() as conn:
        record = conn.execute(
            text("""SELECT created_at, expires_at FROM axiom.workspace_create_idempotency
                     WHERE owner_user_id=:owner AND key=:key"""),
            {"owner": actor, "key": "idempotencyKey189"},
        ).one()
        assert record.expires_at - record.created_at >= timedelta(hours=25)

    # The approved residual behavior: after an *explicit operator purge* of
    # an expired record, a very late replay can create a second workspace.
    with privileged_engine.begin() as conn:
        conn.execute(
            text("""UPDATE axiom.workspace_create_idempotency
                     SET created_at=now()-interval '50 hours',
                         expires_at=now()-interval '25 hours'
                     WHERE owner_user_id=:owner AND key=:key"""),
            {"owner": actor, "key": "idempotencyKey189"},
        )
        assert (
            conn.execute(
                text("""DELETE FROM axiom.workspace_create_idempotency
                     WHERE owner_user_id=:owner AND key=:key AND expires_at < now()"""),
                {"owner": actor, "key": "idempotencyKey189"},
            ).rowcount
            == 1
        )
    late_retry = create(client, auth, "The product", "idempotencyKey189")
    assert late_retry.status_code == 201
    assert late_retry.json()["id"] != first.json()["id"]


def test_keyset_pagination_with_equal_timestamps_and_foreign_cursor(api, privileged_engine) -> None:
    client, private, _settings = api
    a, b = uuid4(), uuid4()
    aa, bb = headers(private, a), headers(private, b)
    bootstrap(client, aa)
    bootstrap(client, bb)
    ids = set()
    for i in range(5):
        result = create(client, aa, f"Page {i}", f"pageRequest189-{i:02d}")
        assert result.status_code == 201
        ids.add(result.json()["id"])
    b_resource = create(client, bb, "B only", "pageRequestB1888").json()
    # Tie created_at intentionally to exercise id DESC as a deterministic tie-break.
    with privileged_engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE axiom.workspaces SET created_at=date_trunc('second',now()) "
                "WHERE owner_user_id=:owner"
            ),
            {"owner": a},
        )
    first = client.get("/api/v1/workspaces?limit=2", headers=aa)
    assert first.status_code == 200
    assert len(first.json()["items"]) == 2
    cursor = first.json()["next_cursor"]
    assert isinstance(cursor, str) and cursor
    assert_error(
        client.get("/api/v1/workspaces?limit=2&cursor=" + cursor, headers=bb),
        422,
        "VALIDATION_FAILED",
    )
    for bad in ("not-a-cursor", "x" * 513):
        assert_error(
            client.get("/api/v1/workspaces", params={"limit": 2, "cursor": bad}, headers=aa),
            422,
            "VALIDATION_FAILED",
        )
    for bad_limit in ("0", "101", "-1", "garbage"):
        assert_error(
            client.get("/api/v1/workspaces", params={"limit": bad_limit}, headers=aa),
            422,
            "VALIDATION_FAILED",
        )
    # Newer insert after page 1 must not be repeated on later pages.
    inserted = create(client, aa, "A new one", "pageNewInsert189").json()
    collected = first.json()["items"][:]
    while cursor:
        page = client.get("/api/v1/workspaces", params={"limit": 2, "cursor": cursor}, headers=aa)
        assert page.status_code == 200
        collected.extend(page.json()["items"])
        cursor = page.json()["next_cursor"]
    assert {x["id"] for x in collected} == ids
    assert len(collected) == len(ids)
    assert inserted["id"] not in ids
    assert b_resource["id"] not in ids
    assert [x["id"] for x in collected] == sorted(ids, reverse=True)

    # A cursor with a forged owner but a foreign anchor cannot become a data path.
    b_page = client.get("/api/v1/workspaces?limit=1", headers=bb).json()
    assert b_page["next_cursor"] is None
    payload = json.loads(
        base64.urlsafe_b64decode(
            first.json()["next_cursor"] + "=" * (-len(first.json()["next_cursor"]) % 4)
        )
    )
    payload["id"] = b_resource["id"]
    forged = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    assert_error(
        client.get("/api/v1/workspaces", params={"limit": 2, "cursor": forged}, headers=aa),
        422,
        "VALIDATION_FAILED",
    )


def test_pagination_anchor_survives_non_utc_dst_fold(api, privileged_engine) -> None:
    client, private, settings = api
    owner = uuid4()
    auth = headers(private, owner)
    bootstrap(client, auth)
    for index in range(2):
        result = create(client, auth, f"Fold {index}", f"foldKey189-{index}")
        assert result.status_code == 201

    # 01:30 occurs twice in New York on this date: this is the second occurrence.
    folded_instant = datetime(2026, 11, 1, 6, 30, tzinfo=UTC)
    with privileged_engine.begin() as conn:
        conn.execute(
            text("UPDATE axiom.workspaces SET created_at=:at WHERE owner_user_id=:owner"),
            {"at": folded_instant, "owner": owner},
        )
    first = client.get("/api/v1/workspaces", params={"limit": 1}, headers=auth)
    assert first.status_code == 200
    cursor = first.json()["next_cursor"]
    assert cursor is not None

    runtime = Database(settings)

    def non_utc_session(connection) -> None:
        connection.exec_driver_sql("SET LOCAL TIME ZONE 'America/New_York'")

    event.listen(runtime.engine, "begin", non_utc_session)
    try:
        page = WorkspaceStore(runtime).page_workspaces(
            VerifiedPrincipal(owner, None), limit=1, cursor=cursor
        )
        assert len(page["items"]) == 1
    finally:
        runtime.close()


def test_optimistic_patch_atomic_and_owner_immutable(api, privileged_engine) -> None:
    client, private, _settings = api
    a, b = uuid4(), uuid4()
    aa, bb = headers(private, a), headers(private, b)
    bootstrap(client, aa)
    bootstrap(client, bb)
    first = create(client, aa, "Original", "optimisticKey189").json()
    path = "/api/v1/workspaces/" + first["id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(
                lambda name: client.patch(
                    path, headers=aa, json={"name": name, "expected_version": 1}
                ),
                ["First update", "Second update"],
            )
        )
    assert sorted(result.status_code for result in outcomes) == [200, 409]
    assert_error(next(x for x in outcomes if x.status_code == 409), 409, "VERSION_CONFLICT")
    current = client.get(path, headers=aa).json()
    assert current["version"] == 2
    assert current["name"] in {"First update", "Second update"}
    assert current["updated_at"] >= first["updated_at"]
    assert_error(
        client.patch(path, headers=aa, json={"name": current["name"], "expected_version": 1}),
        409,
        "VERSION_CONFLICT",
    )
    assert_error(
        client.patch(path, headers=bb, json={"name": "Lost", "expected_version": 2}),
        404,
        "NOT_FOUND",
    )
    for bad in (
        {"name": "x", "expected_version": 0},
        {"name": "x", "expected_version": True},
        {"name": "x", "expected_version": 2, "owner_user_id": str(b)},
        {"name": "x"},
        {"name": ""},
        {"name": " "},
        {"name": "x" * 121, "expected_version": 2},
    ):
        assert_error(client.patch(path, headers=aa, json=bad), 422, "VALIDATION_FAILED")
    assert_error(client.get("/api/v1/workspaces/not-a-uuid", headers=aa), 422, "VALIDATION_FAILED")
    assert client.get(path, headers=aa).json() == current
    # No-change success still checks expected version, and increments only once.
    no_change = client.patch(
        path, headers=aa, json={"name": current["name"], "expected_version": 2}
    )
    assert no_change.status_code == 200 and no_change.json()["version"] == 3


def test_privileged_rls_bypass_is_not_app_authorization(api, privileged_engine) -> None:
    client, private, settings = api
    a, b = uuid4(), uuid4()
    aa, bb = headers(private, a), headers(private, b)
    bootstrap(client, aa)
    bootstrap(client, bb)
    private_b = create(client, bb, "Do not leak", "privilegedBkey1888").json()
    with privileged_engine.connect() as conn:
        assert conn.scalar(text("SELECT current_user")) == "axiom_migrator"
        assert conn.scalar(text("SELECT count(*) FROM axiom.workspaces")) >= 1
    privileged = Database(
        settings.model_copy(
            update={"database_url": SecretStr(os.environ["AXIOM_MIGRATION_DATABASE_URL"])}
        )
    )
    try:
        store = WorkspaceStore(privileged)
        with pytest.raises(WorkspaceNotFound):
            store.get_workspace(VerifiedPrincipal(a, None), UUID(private_b["id"]))
        with pytest.raises(WorkspaceNotFound):
            store.update_workspace(
                VerifiedPrincipal(a, None),
                UUID(private_b["id"]),
                name="Hijacked",
                expected_version=1,
            )
        # HTTP must independently forbid IDOR even if DB role bypasses RLS.
        privileged_app = create_app(
            settings.model_copy(
                update={"database_url": SecretStr(os.environ["AXIOM_MIGRATION_DATABASE_URL"])}
            )
        )
        privileged_app.state.database.close()  # dispose the unused engine created by create_app
        privileged_app.state.database = privileged
        privileged_app.state.jwt_verifier = client.app.state.jwt_verifier
        with TestClient(privileged_app) as privileged_client:
            assert_error(
                privileged_client.get("/api/v1/workspaces/" + private_b["id"], headers=aa),
                404,
                "NOT_FOUND",
            )
    finally:
        privileged.close()


def test_safe_database_outage_and_rollbacks(api, privileged_engine) -> None:
    client, private, settings = api
    a = uuid4()
    aa = headers(private, a)
    bootstrap(client, aa)
    workspace_id = uuid4()
    runtime = Database(settings)
    try:
        with pytest.raises(DBAPIError):
            with runtime.transaction(VerifiedPrincipal(a, None)) as session:
                session.add(Workspace(id=workspace_id, owner_user_id=a, name="Will rollback"))
                session.flush()
                session.add(
                    WorkspaceCreateIdempotency(
                        owner_user_id=a,
                        operation="workspace.create",
                        key="rollbackKey189",
                        fingerprint="not-a-digest",
                        response_status=201,
                        response_body={"id": str(workspace_id)},
                        expires_at=session.scalar(select(text("now() + interval '25 hours'"))),
                    )
                )
                session.flush()
        with runtime.transaction(VerifiedPrincipal(a, None)) as session:
            assert session.scalar(select(Workspace.id).where(Workspace.id == workspace_id)) is None
            assert (
                session.scalar(
                    select(WorkspaceCreateIdempotency).where(
                        WorkspaceCreateIdempotency.owner_user_id == a,
                        WorkspaceCreateIdempotency.key == "rollbackKey189",
                    )
                )
                is None
            )
    finally:
        runtime.close()
    bad_settings = settings.model_copy(
        update={
            "database_url": SecretStr(
                "postgresql://test_user:doNotRevealMe@127.0.0.1:55433/axiom_test"
            )
        }
    )
    fail_app = create_app(bad_settings)
    fail_app.state.jwt_verifier = client.app.state.jwt_verifier
    with TestClient(fail_app) as failing:
        response = failing.get("/api/v1/me", headers=aa)
        assert_error(response, 503, "DATABASE_UNAVAILABLE")
        assert "doNotRevealMe" not in response.text
        assert failing.get("/api/v1/health/live").status_code == 200
