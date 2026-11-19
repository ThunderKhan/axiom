"""Validated, server-only process configuration."""
from __future__ import annotations

from ipaddress import ip_address
from typing import Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RuntimeSettings(BaseSettings):
    """Settings for both runtime roles; no external provider is required at WP-01."""

    model_config = SettingsConfigDict(env_prefix="AXIOM_", extra="ignore")

    bind_host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
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
