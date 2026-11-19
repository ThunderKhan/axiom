"""Validated, server-only process configuration."""

from __future__ import annotations

from ipaddress import ip_address
from typing import Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    """Settings for both runtime roles; no external provider is required at WP-01."""

    model_config = SettingsConfigDict(env_prefix="AXIOM_", extra="ignore")

    bind_host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    cors_origins: str = "http://127.0.0.1:3000"
    database_url: SecretStr | None = None
    database_required: bool = False
    worker_run_seconds: float = Field(default=30.0, ge=0.1, le=300.0)
    worker_idle_seconds: float = Field(default=0.25, ge=0.05, le=5.0)

    @field_validator("bind_host")
    @classmethod
    def require_ip_bind_address(cls, value: str) -> str:
        # Only literal interface addresses; never silently resolve a hostname.
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
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username is not None
                or url.password is not None
                or url.query
                or url.fragment
                or url.path
                or origin != f"{url.scheme}://{url.netloc}"
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


def load_settings() -> RuntimeSettings:
    """Read and validate the environment at process startup."""
    return RuntimeSettings()
