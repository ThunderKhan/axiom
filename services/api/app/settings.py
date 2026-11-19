"""Validated, server-only process configuration."""

from __future__ import annotations

import re
from ipaddress import ip_address
from typing import Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_HOST = re.compile(r"[a-z0-9][a-z0-9-]{0,62}\.supabase\.co\Z")


class RuntimeSettings(BaseSettings):
    """Shared process settings; auth must be explicitly configured for protected APIs."""

    model_config = SettingsConfigDict(env_prefix="AXIOM_", extra="ignore")

    bind_host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: str = "http://127.0.0.1:3000"
    database_url: SecretStr | None = None
    database_required: bool = False
    worker_run_seconds: float = Field(default=30.0, ge=0.1, le=300.0)
    worker_idle_seconds: float = Field(default=0.25, ge=0.05, le=5.0)
    auth_issuer: str | None = None
    auth_audience: str | None = None
    auth_jwks_url: str | None = None
    jwks_cache_max_seconds: int = Field(default=300, ge=1, le=300)

    @property
    def auth_configured(self) -> bool:
        return all((self.auth_issuer, self.auth_audience, self.auth_jwks_url))

    @field_validator("bind_host")
    @classmethod
    def require_ip_bind_address(cls, value: str) -> str:
        ip_address(value)
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_exact_cors_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",")]
        if not origins or any(not origin for origin in origins):
            raise ValueError("AXIOM_CORS_ORIGINS requires explicit nonempty origins")
        if len(set(origins)) != len(origins):
            raise ValueError("Duplicate CORS origins are not allowed")
        for origin in origins:
            try:
                url = urlsplit(origin)
                port = url.port
            except ValueError as exc:
                raise ValueError("Invalid CORS origin or port") from exc
            host = url.hostname or ""
            if not host.isascii():
                raise ValueError("CORS origins must use ASCII/punycode hosts")
            canonical_host = f"[{ip_address(host).compressed}]" if ":" in host else host
            default_port = 80 if url.scheme == "http" else 443
            canonical_port = f":{port}" if port is not None and port != default_port else ""
            canonical_origin = f"{url.scheme}://{canonical_host}{canonical_port}"
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username is not None
                or url.password is not None
                or url.query
                or url.fragment
                or url.path
                or origin != canonical_origin
                or (port is not None and not 1 <= port <= 65535)
            ):
                raise ValueError("CORS origins must be exact HTTP(S) origins without credentials")
            if url.scheme == "http" and url.hostname not in {"127.0.0.1", "localhost", "::1"}:
                raise ValueError("Plain HTTP CORS origins require a loopback host")
        return ",".join(origins)

    @field_validator("database_url")
    @classmethod
    def require_postgresql_scheme(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and not value.get_secret_value().startswith(
            ("postgresql://", "postgresql+psycopg://")
        ):
            raise ValueError("AXIOM_DATABASE_URL must be a PostgreSQL connection URL")
        return value

    @model_validator(mode="after")
    def require_database_url_if_requested(self) -> Self:
        if self.database_required and self.database_url is None:
            raise ValueError("AXIOM_DATABASE_URL is required when database_required is true")
        return self

    @model_validator(mode="after")
    def validate_auth_project_origin(self) -> Self:
        provided = (self.auth_issuer, self.auth_audience, self.auth_jwks_url)
        if not any(value is not None for value in provided):
            return self  # M0 health-only deployment remains functional.
        if not all(isinstance(value, str) and value for value in provided):
            raise ValueError("All AXIOM_AUTH_* values are required together")
        assert self.auth_issuer is not None
        assert self.auth_jwks_url is not None
        assert self.auth_audience is not None
        url = urlsplit(self.auth_issuer)
        if (
            url.scheme != "https"
            or not url.hostname
            or not _PROJECT_HOST.fullmatch(url.hostname)
            or url.port is not None
            or url.username is not None
            or url.password is not None
            or url.path != "/auth/v1"
            or url.query
            or url.fragment
            or self.auth_issuer != f"https://{url.hostname}/auth/v1"
            or self.auth_jwks_url != f"{self.auth_issuer}/.well-known/jwks.json"
            or self.auth_audience.strip() != self.auth_audience
            or not 1 <= len(self.auth_audience) <= 128
        ):
            raise ValueError(
                "Auth issuer, audience and JWKS must match one trusted Supabase project"
            )
        return self


def load_settings() -> RuntimeSettings:
    """Read and validate the environment at process startup."""
    return RuntimeSettings()
