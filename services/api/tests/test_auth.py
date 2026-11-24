from __future__ import annotations

import json
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from typing import Annotated
from uuid import UUID, uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import Depends
from fastapi.testclient import TestClient
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

from app.auth import AuthFailure, JwtVerifier, VerifiedPrincipal, get_verified_principal
from app.main import create_app
from app.settings import RuntimeSettings

ISSUER = "https://axiomtest.supabase.co/auth/v1"
SUB = str(uuid4())
SESSION = str(uuid4())


def settings(**updates: object) -> RuntimeSettings:
    return RuntimeSettings(
        auth_issuer=ISSUER,
        auth_audience="authenticated",
        auth_jwks_url=f"{ISSUER}/.well-known/jwks.json",
        **updates,
    )


@pytest.fixture(scope="module")
def rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def other_rsa_key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def jwk(private_key, kid: str = "k1", algorithm: str = "RS256") -> dict[str, str]:
    parser = RSAAlgorithm if algorithm == "RS256" else ECAlgorithm
    result = json.loads(parser.to_jwk(private_key.public_key()))
    return {**result, "kid": kid, "alg": algorithm, "use": "sig"}


def token(private_key, **changes: object) -> str:
    claims = {
        "iss": ISSUER,
        "aud": "authenticated",
        "exp": 1893456000,
        "iat": 1763500000,
        "nbf": 1763500000,
        "sub": SUB,
        "role": "authenticated",
        "session_id": SESSION,
        "is_anonymous": False,
    }
    claims.update(changes)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "k1"})


def verifier(rsa_key, **opts: object) -> JwtVerifier:
    return JwtVerifier(settings(), fetcher=lambda url: {"keys": [jwk(rsa_key)]}, **opts)


def test_accepts_signed_supabase_shaped_claims(rsa_key) -> None:
    principal = verifier(rsa_key).verify(token(rsa_key))
    assert principal == VerifiedPrincipal(user_id=UUID(SUB), session_id=UUID(SESSION))


@pytest.mark.parametrize(
    "change",
    [
        {"iss": "https://foreign.supabase.co/auth/v1"},
        {"aud": "other"},
        {"aud": ["authenticated", "other"]},
        {"exp": 1},
        {"iat": 1893456001},
        {"nbf": 1893456001},
        {"sub": "not-a-uuid"},
        {"sub": "00000000-0000-0000-0000-000000000000"},
        {"role": "anon"},
        {"role": "service_role"},
        {"is_anonymous": True},
        {"session_id": "not-a-uuid"},
        {"type": "id_token"},
        {"token_use": "refresh"},
        {"client_id": "4b9cb24a-9073-41fc-892e-1255348cb067"},
        {"client_id": None},
    ],
)
def test_disallowed_user_claims(rsa_key, change: dict[str, object]) -> None:
    with pytest.raises(AuthFailure):
        verifier(rsa_key).verify(token(rsa_key, **change))


def test_wrong_signer_denied(rsa_key, other_rsa_key) -> None:
    with pytest.raises(AuthFailure):
        verifier(rsa_key).verify(token(other_rsa_key))


def test_unknown_key_denied_and_refresh_throttled(rsa_key, other_rsa_key) -> None:
    calls = []
    clock = [100.0]

    def fetch(_url: str) -> Mapping[str, object]:
        calls.append(clock[0])
        return {"keys": [jwk(rsa_key)]}

    service = JwtVerifier(settings(), fetcher=fetch, clock=lambda: clock[0])
    missing = jwt.encode(
        {
            "iss": ISSUER,
            "aud": "authenticated",
            "exp": 1893456000,
            "iat": 1763500000,
            "sub": SUB,
            "role": "authenticated",
        },
        other_rsa_key,
        algorithm="RS256",
        headers={"kid": "unknown"},
    )
    for _ in range(5):
        with pytest.raises(AuthFailure):
            service.verify(missing)
    assert len(calls) == 1
    clock[0] += 31
    with pytest.raises(AuthFailure):
        service.verify(missing)
    assert len(calls) == 2


def test_rotation_and_expiry(rsa_key, other_rsa_key) -> None:
    now = [100.0]
    current_keys = [[jwk(rsa_key)]]
    service = JwtVerifier(
        settings(jwks_cache_max_seconds=60),
        fetcher=lambda _: {"keys": current_keys[0]},
        clock=lambda: now[0],
    )
    assert service.verify(token(rsa_key)).user_id == UUID(SUB)
    current_keys[0] = [jwk(other_rsa_key)]
    assert service.verify(token(rsa_key)).user_id == UUID(SUB)
    now[0] = 161.0
    with pytest.raises(AuthFailure):
        service.verify(token(rsa_key))
    assert service.verify(token(other_rsa_key)).user_id == UUID(SUB)


def test_outage_accepts_only_fresh_cached_known_key(rsa_key) -> None:
    now = [100.0]
    failure = [False]

    def fetch(_url: str) -> Mapping[str, object]:
        if failure[0]:
            raise AuthFailure(unavailable=True)
        return {"keys": [jwk(rsa_key)]}

    service = JwtVerifier(settings(jwks_cache_max_seconds=60), fetcher=fetch, clock=lambda: now[0])
    assert service.verify(token(rsa_key)).user_id == UUID(SUB)
    failure[0] = True
    assert service.verify(token(rsa_key)).user_id == UUID(SUB)
    now[0] = 161
    with pytest.raises(AuthFailure) as error:
        service.verify(token(rsa_key))
    assert error.value.unavailable


def test_invalidation_forces_new_fetch(rsa_key) -> None:
    count = [0]

    def fetch(_url: str) -> Mapping[str, object]:
        count[0] += 1
        return {"keys": [jwk(rsa_key)]}

    service = JwtVerifier(settings(), fetcher=fetch)
    service.verify(token(rsa_key))
    service.invalidate()
    service.verify(token(rsa_key))
    assert count[0] == 2


def test_concurrent_first_refresh_is_single_flight(rsa_key) -> None:
    count = [0]

    def fetch(_url: str) -> Mapping[str, object]:
        count[0] += 1
        return {"keys": [jwk(rsa_key)]}

    service = JwtVerifier(settings(), fetcher=fetch)
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert all(
            pool.map(lambda _: service.verify(token(rsa_key)).user_id == UUID(SUB), range(32))
        )
    assert count[0] == 1


def test_es256_key_is_accepted_with_matching_algorithm() -> None:
    private = ec.generate_private_key(ec.SECP256R1())
    claims = {
        "iss": ISSUER,
        "aud": "authenticated",
        "exp": 1893456000,
        "iat": 1763500000,
        "sub": SUB,
        "role": "authenticated",
    }
    signed = jwt.encode(claims, private, algorithm="ES256", headers={"kid": "ecdsa"})
    service = JwtVerifier(settings(), fetcher=lambda _: {"keys": [jwk(private, "ecdsa", "ES256")]})
    assert service.verify(signed).user_id == UUID(SUB)


def test_header_algorithm_confusion_rejected(rsa_key) -> None:
    signed = jwt.encode(
        {
            "iss": ISSUER,
            "aud": "authenticated",
            "exp": 1893456000,
            "iat": 1763500000,
            "sub": SUB,
            "role": "authenticated",
        },
        "not-a-signing-key",
        algorithm="HS256",
        headers={"kid": "k1"},
    )
    with pytest.raises(AuthFailure):
        verifier(rsa_key).verify(signed)


def test_http_dependency_headers_errors_and_health(rsa_key) -> None:
    app = create_app(settings())
    app.state.jwt_verifier = verifier(rsa_key)

    @app.get("/__test_only__/protected")
    def protected(
        principal: Annotated[VerifiedPrincipal, Depends(get_verified_principal)],
    ) -> dict[str, str]:
        return {"user_id": str(principal.user_id)}

    with TestClient(app) as client:
        valid = client.get(
            "/__test_only__/protected", headers={"Authorization": f"Bearer {token(rsa_key)}"}
        )
        assert valid.status_code == 200
        assert valid.json() == {"user_id": SUB}
        assert client.get("/api/v1/health/live").status_code == 200
        for headers in (
            {},
            {"Authorization": "Basic abc"},
            {"Authorization": "Bearer junk"},
            {"Authorization": "Bearer  "},
            {"Authorization": "Bearer abc.def.ghi"},
        ):
            response = client.get("/__test_only__/protected", headers=headers)
            assert response.status_code == 401
            assert response.json()["error"]["code"] == "AUTH_REQUIRED"
            assert response.json()["error"]["details"] == {}
            assert response.json()["request_id"].startswith("req_")
            assert "Bearer" in response.headers["www-authenticate"]
        response = client.get(
            "/__test_only__/protected",
            headers=[
                ("Authorization", f"Bearer {token(rsa_key)}"),
                ("Authorization", "Bearer invalid"),
            ],
        )
        assert response.status_code == 401


def test_http_missing_configuration_fails_closed() -> None:
    app = create_app(RuntimeSettings())

    @app.get("/__test_only__/protected")
    def protected(
        principal: Annotated[VerifiedPrincipal, Depends(get_verified_principal)],
    ) -> dict[str, str]:
        return {"user_id": str(principal.user_id)}

    with TestClient(app) as client:
        response = client.get("/__test_only__/protected")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUTH_UNAVAILABLE"


def test_failed_cold_cache_fetch_is_single_flight_then_recovers(rsa_key) -> None:
    """Concurrent requests share an outage result instead of serializing timeouts."""
    from threading import Barrier

    clock = [100.0]
    calls = [0]
    provider_available = [False]

    def fetch(_url: str) -> Mapping[str, object]:
        calls[0] += 1
        if not provider_available[0]:
            raise AuthFailure(unavailable=True)
        return {"keys": [jwk(rsa_key)]}

    service = JwtVerifier(settings(), fetcher=fetch, clock=lambda: clock[0])
    signed = token(rsa_key)
    together = Barrier(9)

    def attempt() -> bool:
        together.wait(timeout=10)
        try:
            service.verify(signed)
        except AuthFailure as exc:
            return exc.unavailable
        return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        pending = [pool.submit(attempt) for _ in range(8)]
        together.wait(timeout=10)
        assert all(future.result(timeout=10) for future in pending)
    assert calls == [1]

    clock[0] = 104.9
    with pytest.raises(AuthFailure) as error:
        service.verify(signed)
    assert error.value.unavailable
    assert calls == [1]

    provider_available[0] = True
    clock[0] = 105.1
    assert service.verify(signed).user_id == UUID(SUB)
    assert calls == [2]


def test_failed_expired_cache_denies_stale_signatures_during_backoff(rsa_key) -> None:
    clock = [100.0]
    calls = [0]
    online = [True]

    def fetch(_url: str) -> Mapping[str, object]:
        calls[0] += 1
        if not online[0]:
            raise AuthFailure(unavailable=True)
        return {"keys": [jwk(rsa_key)]}

    service = JwtVerifier(
        settings(jwks_cache_max_seconds=60),
        fetcher=fetch,
        clock=lambda: clock[0],
    )
    signed = token(rsa_key)
    assert service.verify(signed).user_id == UUID(SUB)
    online[0] = False
    clock[0] = 160.0
    for now in (160.0, 161.0, 164.9):
        clock[0] = now
        with pytest.raises(AuthFailure) as error:
            service.verify(signed)
        assert error.value.unavailable
    assert calls == [2]
    online[0] = True
    clock[0] = 165.1
    assert service.verify(signed).user_id == UUID(SUB)
    assert calls == [3]


def test_unknown_kid_misses_do_not_postpone_key_rotation(rsa_key, other_rsa_key) -> None:
    clock = [100.0]
    available_keys = [[jwk(rsa_key)]]
    fetches = [0]

    def fetch(_url: str) -> Mapping[str, object]:
        fetches[0] += 1
        return {"keys": available_keys[0]}

    service = JwtVerifier(settings(), fetcher=fetch, clock=lambda: clock[0])
    assert service.verify(token(rsa_key)).user_id == UUID(SUB)
    claims = jwt.decode(token(other_rsa_key), options={"verify_signature": False})
    rotated = jwt.encode(claims, other_rsa_key, algorithm="RS256", headers={"kid": "k2"})
    clock[0] = 131.0  # First unknown-kid refresh after cold-cache fetch.
    with pytest.raises(AuthFailure):
        service.verify(rotated)
    assert fetches == [2]

    available_keys[0] = [jwk(rsa_key), jwk(other_rsa_key, kid="k2")]
    for now in (141.0, 151.0, 160.0):
        clock[0] = now
        with pytest.raises(AuthFailure):
            service.verify(rotated)
    assert fetches == [2]  # Rejected misses never reset the refresh deadline.

    clock[0] = 161.1
    assert service.verify(rotated).user_id == UUID(SUB)
    assert fetches == [3]


def test_truncated_chunked_jwks_response_is_safe_503(rsa_key, monkeypatch) -> None:
    from http.client import IncompleteRead

    from app.auth import fetch_jwks

    class BrokenResponse:
        headers: dict[str, str] = {}

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, _limit: int) -> bytes:
            raise IncompleteRead(b"{", 10)

    class BrokenOpener:
        def open(self, _request, *, timeout: float):
            assert timeout > 0
            return BrokenResponse()

    monkeypatch.setattr("app.auth.build_opener", lambda *_: BrokenOpener())
    with pytest.raises(AuthFailure) as error:
        fetch_jwks(f"{ISSUER}/.well-known/jwks.json")
    assert error.value.unavailable

    app = create_app(settings())
    app.state.jwt_verifier = JwtVerifier(settings())

    @app.get("/__test_only__/protected")
    def protected(
        principal: Annotated[VerifiedPrincipal, Depends(get_verified_principal)],
    ) -> dict[str, str]:
        return {"user_id": str(principal.user_id)}

    with TestClient(app) as client:
        response = client.get(
            "/__test_only__/protected",
            headers={"Authorization": f"Bearer {token(rsa_key)}"},
        )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUTH_UNAVAILABLE"
    assert response.json()["error"]["retryable"] is True
    assert response.json()["request_id"].startswith("req_")

def test_delegated_tokens_require_distinct_resource_and_client(rsa_key) -> None:
    service = verifier(rsa_key)
    resource = "https://api.example.org/mcp"
    client_id = str(uuid4())
    delegated = token(rsa_key, aud=resource, client_id=client_id)
    verified = service.verify_delegated(delegated, resource)
    assert verified.principal.user_id == UUID(SUB)
    assert verified.client_id == UUID(client_id)
    assert verified.resource == resource
    with pytest.raises(AuthFailure):
        service.verify(delegated)
    with pytest.raises(AuthFailure):
        service.verify(token(rsa_key, client_id=client_id))
    for invalid in (
        token(rsa_key),
        token(rsa_key, aud=resource),
        token(rsa_key, aud=resource, client_id="not-a-uuid"),
        token(rsa_key, aud=resource, client_id=client_id, session_id=None),
        token(rsa_key, aud=resource, client_id=client_id, exp=1),
        token(rsa_key, aud=[resource, "authenticated"], client_id=client_id),
    ):
        with pytest.raises(AuthFailure):
            service.verify_delegated(invalid, resource)
    with pytest.raises(AuthFailure):
        service.verify_delegated(token(rsa_key, client_id=client_id), "authenticated")
    with pytest.raises(AuthFailure):
        service.verify_delegated(delegated, "https://other.example.org/mcp")
