from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import RuntimeSettings


def test_fastapi_import_and_versioned_openapi() -> None:
    app = create_app(RuntimeSettings())
    with TestClient(app) as client:
        schema = client.get("/openapi.json")
        assert schema.status_code == 200
        assert schema.json()["info"]["version"] == "0.2.0"
        assert set(schema.json()["paths"]) == {
            "/api/v1/health/live",
            "/api/v1/health/ready",
        }


def test_liveness_is_genuine_http_response() -> None:
    with TestClient(create_app(RuntimeSettings())) as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive", "service": "axiom-api"}


def test_readiness_without_external_dependencies_is_scoped() -> None:
    with TestClient(create_app(RuntimeSettings())) as client:
        response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "scope": "foundation_only",
        "dependencies": "none_configured",
    }


def test_configured_but_unverified_database_is_not_ready_and_secret_is_hidden() -> None:
    config = RuntimeSettings(database_url="postgresql://owner:private@127.0.0.1/db")
    with TestClient(create_app(config)) as client:
        live = client.get("/api/v1/health/live")
        ready = client.get("/api/v1/health/ready")
    assert live.status_code == 200
    assert ready.status_code == 503
    assert ready.json() == {
        "status": "not_ready",
        "scope": "foundation_only",
        "dependencies": "database_not_verified",
    }
    assert "private" not in ready.text


def test_unknown_product_paths_do_not_fake_success() -> None:
    with TestClient(create_app(RuntimeSettings())) as client:
        assert client.get("/api/v1/opportunities").status_code == 404

def test_allowed_origin_get_and_preflight_are_exact() -> None:
    app = create_app(RuntimeSettings(cors_origins="http://127.0.0.1:3200"))
    with TestClient(app) as client:
        preflight = client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "http://127.0.0.1:3200",
                "Access-Control-Request-Method": "GET",
            },
        )
        actual = client.get(
            "/api/v1/health/live", headers={"Origin": "http://127.0.0.1:3200"}
        )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://127.0.0.1:3200"
    assert actual.status_code == 200
    assert actual.headers["access-control-allow-origin"] == "http://127.0.0.1:3200"
    assert "access-control-allow-credentials" not in actual.headers


def test_unapproved_origin_never_receives_permission() -> None:
    app = create_app(RuntimeSettings(cors_origins="http://127.0.0.1:3200"))
    with TestClient(app) as client:
        preflight = client.options(
            "/api/v1/health/live",
            headers={
                "Origin": "https://unapproved.example",
                "Access-Control-Request-Method": "GET",
            },
        )
        actual = client.get(
            "/api/v1/health/live", headers={"Origin": "https://unapproved.example"}
        )
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers
    assert actual.status_code == 200
    assert "access-control-allow-origin" not in actual.headers
