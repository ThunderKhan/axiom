from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.settings import RuntimeSettings


def test_defaults_require_no_external_service() -> None:
    settings = RuntimeSettings()
    assert settings.database_url is None
    assert settings.database_required is False
    assert settings.port == 8000


@pytest.mark.parametrize("port", [0, 65536, "not-a-port"])
def test_invalid_ports_fail(port: object) -> None:
    with pytest.raises(ValidationError):
        RuntimeSettings(port=port)


@pytest.mark.parametrize("host", ["example.com", "not-a-host", ""])
def test_binding_requires_literal_ip(host: str) -> None:
    with pytest.raises(ValidationError):
        RuntimeSettings(bind_host=host)


def test_missing_required_database_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RuntimeSettings(database_required=True)


def test_wrong_database_scheme_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RuntimeSettings(database_url="https://invalid.example/database")


def test_secret_not_revealed_in_settings_representation() -> None:
    credentials = "postgresql://owner:sensitive-value@127.0.0.1:5432/db"
    settings = RuntimeSettings(database_url=credentials)
    assert "sensitive-value" not in repr(settings)


def test_invalid_worker_bounds_rejected() -> None:
    with pytest.raises(ValidationError):
        RuntimeSettings(worker_run_seconds=-1)
    with pytest.raises(ValidationError):
        RuntimeSettings(worker_idle_seconds=0)
