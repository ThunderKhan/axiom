"""Fail-closed, project-bound Supabase user JWT verification (M1 D1âD3, I3)."""

from __future__ import annotations

import json
import re
from http.client import HTTPException
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

import jwt
from fastapi import Request as FastAPIRequest
from jwt import InvalidTokenError, PyJWTError
from jwt.algorithms import ECAlgorithm, RSAAlgorithm

from app.settings import RuntimeSettings

# Project signing-mode selection is verified separately against a real Supabase test project.
_ALLOWED_ALGORITHMS: Mapping[str, str] = {"RS256": "RSA", "ES256": "EC"}
_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$")
_JWKS_MAX_BYTES = 65536
_UNKNOWN_KID_REFRESH_SECONDS = 30.0
_JWKS_FAILURE_BACKOFF_SECONDS = 5.0
_NETWORK_TIMEOUT_SECONDS = 3.0
_CLOCK_SKEW_SECONDS = 30


class AuthFailure(Exception):
    """Sanitized failure at the JWT trust boundary, never including raw credentials."""

    def __init__(self, *, unavailable: bool = False) -> None:
        super().__init__(
            "Authentication dependency unavailable" if unavailable else "Invalid authentication"
        )
        self.unavailable = unavailable


@dataclass(frozen=True, slots=True)
class VerifiedPrincipal:
    """Crypto-verified provider subject only, NOT an active app user or workspace owner."""

    user_id: UUID
    session_id: UUID | None


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


def fetch_jwks(url: str) -> Mapping[str, object]:
    """Bounded HTTPS fetch from a *server-validated*, fixed project JWKS URL."""
    opener = build_opener(_NoRedirects())
    # A fixed, server-validated Supabase project HTTPS URL; never trust a JWT-supplied URL.
    request = Request(  # noqa: S310
        url, headers={"Accept": "application/json", "User-Agent": "Axiom-Auth/1"}
    )
    try:
        with opener.open(request, timeout=_NETWORK_TIMEOUT_SECONDS) as response:
            length = response.headers.get("Content-Length")
            if length is not None and int(length) > _JWKS_MAX_BYTES:
                raise AuthFailure(unavailable=True)
            data = response.read(_JWKS_MAX_BYTES + 1)
    except (OSError, HTTPException, HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise AuthFailure(unavailable=True) from exc
    if len(data) > _JWKS_MAX_BYTES:
        raise AuthFailure(unavailable=True)
    try:
        document = json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise AuthFailure(unavailable=True) from exc
    if not isinstance(document, dict):
        raise AuthFailure(unavailable=True)
    return document


class JwtVerifier:
    """Thread-safe bounded JWKS cache, refresh throttling and signature verification."""

    def __init__(
        self,
        settings: RuntimeSettings,
        *,
        fetcher: Callable[[str], Mapping[str, object]] = fetch_jwks,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if not settings.auth_configured:
            raise ValueError("Trusted Supabase Auth configuration is required")
        assert settings.auth_jwks_url is not None
        assert settings.auth_issuer is not None
        assert settings.auth_audience is not None
        self._jwks_url = settings.auth_jwks_url
        self._issuer = settings.auth_issuer
        self._audience = settings.auth_audience
        self._cache_seconds = settings.jwks_cache_max_seconds
        self._fetcher = fetcher
        self._clock = clock
        self._lock = threading.Lock()
        self._keys: dict[tuple[str, str], Any] = {}
        self._retrieved_at: float | None = None
        self._next_unknown_refresh = 0.0
        self._retry_failed_refresh_after = 0.0

    def invalidate(self) -> None:
        """Operator-triggerable local purge; reset only through trusted server control."""
        with self._lock:
            self._keys.clear()
            self._retrieved_at = None
            self._next_unknown_refresh = 0.0
            self._retry_failed_refresh_after = 0.0

    def _refresh(self, now: float) -> None:
        # Caller holds lock, so a single flight updates keys atomically.
        try:
            response = self._fetcher(self._jwks_url)
            raw = response.get("keys")
            if not isinstance(raw, list) or len(raw) > 32:
                raise ValueError("invalid JWKS")
            parsed: dict[tuple[str, str], Any] = {}
            for entry in raw:
                if not isinstance(entry, dict):
                    raise ValueError("invalid JWK")
                kid = entry.get("kid")
                alg = entry.get("alg")
                kty = entry.get("kty")
                if not isinstance(kid, str) or not 1 <= len(kid) <= 256:
                    raise ValueError("invalid JWK identifier")
                if not isinstance(alg, str) or alg not in _ALLOWED_ALGORITHMS:
                    # A project may publish an unrelated algorithm; it never becomes trusted.
                    continue
                if kty != _ALLOWED_ALGORITHMS[alg] or entry.get("use", "sig") != "sig":
                    raise ValueError("incoherent signing key")
                if alg == "ES256" and entry.get("crv") != "P-256":
                    raise ValueError("unsupported curve")
                # The public-key parsers reject malformed coordinates/moduli and private JWKs.
                if any(x in entry for x in ("d", "p", "q", "dp", "dq", "qi", "oth")):
                    raise ValueError("private signing material in JWKS")
                key_id = (kid, alg)
                if key_id in parsed:
                    raise ValueError("ambiguous duplicate JWK")
                parser = RSAAlgorithm if alg == "RS256" else ECAlgorithm
                parsed[key_id] = parser.from_jwk(json.dumps(entry))
        except AuthFailure:
            self._retry_failed_refresh_after = self._clock() + _JWKS_FAILURE_BACKOFF_SECONDS
            raise
        except (
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
            PyJWTError,
            OSError,
            HTTPException,
        ) as exc:
            self._retry_failed_refresh_after = self._clock() + _JWKS_FAILURE_BACKOFF_SECONDS
            raise AuthFailure(unavailable=True) from exc
        self._keys = parsed
        self._retrieved_at = now
        self._retry_failed_refresh_after = 0.0

    def _key(self, kid: str, alg: str) -> Any:
        with self._lock:
            now = self._clock()
            fresh = (
                self._retrieved_at is not None
                and 0 <= now - self._retrieved_at < self._cache_seconds
            )
            if not fresh:
                # Expired keys cannot be used, even when the provider is unavailable.
                self._keys.clear()
                self._retrieved_at = None
                if now < self._retry_failed_refresh_after:
                    raise AuthFailure(unavailable=True)
                # A cold or expired-cache fetch also counts toward unknown-kid throttling.
                self._next_unknown_refresh = now + _UNKNOWN_KID_REFRESH_SECONDS
                self._refresh(now)
            key = self._keys.get((kid, alg))
            if key is None and fresh:
                if now < self._retry_failed_refresh_after:
                    raise AuthFailure(unavailable=True)
                if now >= self._next_unknown_refresh:
                    # Move the deadline only when starting a real refresh, never on misses.
                    self._next_unknown_refresh = now + _UNKNOWN_KID_REFRESH_SECONDS
                    self._refresh(now)
                    key = self._keys.get((kid, alg))
            if key is None:
                raise AuthFailure()
            return key

    def verify(self, token: str) -> VerifiedPrincipal:
        if len(token) > 16384 or not _TOKEN_PATTERN.fullmatch(token):
            raise AuthFailure()
        try:
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            alg = header.get("alg")
            if (
                not isinstance(kid, str)
                or not 1 <= len(kid) <= 256
                or not isinstance(alg, str)
                or alg not in _ALLOWED_ALGORITHMS
                or header.get("crit") is not None
                or any(k in header for k in ("jwk", "jku", "x5u", "x5c"))
            ):
                raise AuthFailure()
            key = self._key(kid, alg)
            claims = jwt.decode(
                token,
                key,
                algorithms=[alg],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["iss", "aud", "exp", "iat", "sub", "role"]},
                leeway=_CLOCK_SKEW_SECONDS,
            )
        except AuthFailure:
            raise
        except (InvalidTokenError, TypeError, ValueError, OverflowError) as exc:
            raise AuthFailure() from exc
        # Exact string audience excludes ambiguous multi-audience tokens.
        if claims.get("aud") != self._audience or claims.get("role") != "authenticated":
            raise AuthFailure()
        if claims.get("is_anonymous") is True or claims.get("type") not in (None, "access_token"):
            raise AuthFailure()
        if claims.get("token_use") not in (None, "access"):
            raise AuthFailure()
        try:
            subject = UUID(claims["sub"])
            session = claims.get("session_id")
            session_id = UUID(session) if session is not None else None
        except (ValueError, TypeError, AttributeError) as exc:
            raise AuthFailure() from exc
        if subject.int == 0:
            raise AuthFailure()
        return VerifiedPrincipal(user_id=subject, session_id=session_id)


def extract_bearer(request: FastAPIRequest) -> str:
    values = request.headers.getlist("authorization")
    if len(values) != 1:
        raise AuthFailure()
    scheme, sep, token = values[0].partition(" ")
    if not sep or scheme.lower() != "bearer" or not token or token != token.strip():
        raise AuthFailure()
    return token


def get_verified_principal(request: FastAPIRequest) -> VerifiedPrincipal:
    """Reusable dependency; cryptography does not grant app_user/workspace permissions."""
    verifier: JwtVerifier | None = getattr(request.app.state, "jwt_verifier", None)
    if verifier is None:
        raise AuthFailure(unavailable=True)
    return verifier.verify(extract_bearer(request))
