"""Transport/authorization negative tests with a real cryptographic JWT verifier."""

from __future__ import annotations

import json
import time
from uuid import uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from app.auth import JwtVerifier
from app.main import create_app
from app.settings import RuntimeSettings

ISSUER = "https://axiomtest.supabase.co/auth/v1"


def _client() -> tuple[TestClient, rsa.RSAPrivateKey]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    jwk = {**public, "kid": "local-test", "alg": "RS256", "use": "sig"}
    settings = RuntimeSettings(
        auth_issuer=ISSUER,
        auth_audience="authenticated",
        auth_jwks_url=ISSUER + "/.well-known/jwks.json",
    )
    app = create_app(settings)
    app.state.jwt_verifier = JwtVerifier(settings, fetcher=lambda _: {"keys": [jwk]})
    return TestClient(app), private_key


def _token(private: rsa.RSAPrivateKey, **changes: object) -> str:
    now = int(time.time())
    claims: dict[str, object] = {
        "iss": ISSUER,
        "aud": "authenticated",
        "iat": now,
        "exp": now + 300,
        "sub": str(uuid4()),
        "role": "authenticated",
    }
    claims.update(changes)
    return jwt.encode(claims, private, algorithm="RS256", headers={"kid": "local-test"})


def _assert_envelope(response, code: str, status: int) -> None:
    assert response.status_code == status
    body = response.json()
    assert body["error"] == {
        "code": code,
        "message": body["error"]["message"],
        "retryable": code.endswith("UNAVAILABLE"),
        "details": {},
    }
    assert body["request_id"].startswith("req_")
    assert len(body["request_id"]) == 36
    assert "Traceback" not in response.text


def test_missing_and_invalid_credentials_fail_before_missing_database() -> None:
    client, private = _client()
    with client:
        for method, path, kwargs in (
            ("post", "/api/v1/me/bootstrap", {}),
            ("get", "/api/v1/me", {}),
            ("get", "/api/v1/workspaces", {}),
            (
                "post",
                "/api/v1/workspaces",
                {
                    "json": {"name": "Valid"},
                    "headers": {
                        "Idempotency-Key": "requestKey88",
                    },
                },
            ),
            ("get", "/api/v1/workspaces/" + str(uuid4()), {}),
            (
                "patch",
                "/api/v1/workspaces/" + str(uuid4()),
                {
                    "json": {
                        "name": "Updated",
                        "expected_version": 1,
                    }
                },
            ),
        ):
            _assert_envelope(getattr(client, method)(path, **kwargs), "AUTH_REQUIRED", 401)
        for changes in (
            {"exp": 1},
            {"role": "service_role"},
            {"iss": "https://evil.example"},
            {"aud": "evil"},
            {"is_anonymous": True},
        ):
            response = client.get(
                "/api/v1/me", headers={"Authorization": "Bearer " + _token(private, **changes)}
            )
            _assert_envelope(response, "AUTH_REQUIRED", 401)
        valid = client.get("/api/v1/me", headers={"Authorization": "Bearer " + _token(private)})
        _assert_envelope(valid, "DATABASE_UNAVAILABLE", 503)
        assert valid.json()["error"]["retryable"] is True


def test_strict_transport_errors_do_not_reflect_input_data() -> None:
    client, private = _client()
    token = _token(private)
    with client:
        result = client.get(
            "/api/v1/workspaces?limit=0",
            headers={"Authorization": "Bearer " + token},
        )
        # Database is absent, so no operation may succeed; input is still untrusted.
        assert result.status_code in (422, 503)
        assert token not in result.text


def test_preflight_allows_only_approved_methods_and_origin() -> None:
    client, _ = _client()
    with client:
        for method in ("GET", "POST", "PATCH"):
            allowed = client.options(
                "/api/v1/workspaces",
                headers={
                    "Origin": "http://127.0.0.1:3000",
                    "Access-Control-Request-Method": method,
                    "Access-Control-Request-Headers": "authorization,content-type,idempotency-key",
                },
            )
            assert allowed.status_code == 200
            assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:3000"
            assert "authorization" in allowed.headers["access-control-allow-headers"].lower()
            assert "idempotency-key" in allowed.headers["access-control-allow-headers"].lower()
            assert "access-control-allow-credentials" not in allowed.headers
        denied = client.options(
            "/api/v1/workspaces",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "PATCH",
                "Access-Control-Request-Headers": "authorization,idempotency-key",
            },
        )
        assert denied.status_code == 400
        assert "access-control-allow-origin" not in denied.headers
