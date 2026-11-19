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


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "",
        "https://safe.example/",
        "http://unsafe.example",
        "***safe.example",
        "https://safe.example/path",
        "https://safe.example?token=secret",
        "http://127.0.0.1:0",
        "http://127.0.0.1:99999",
        "http://127.0.0.1:3000,http://127.0.0.1:3000",
        "https://web.example:443",
        "http://127.0.0.1:80",
        "https://WEB.example",
        "https://tést.example",
    ],
)
def test_invalid_cors_origin_configuration_fails_closed(origin: str) -> None:
    with pytest.raises(ValidationError):
        RuntimeSettings(cors_origins=origin)


def test_explicit_cors_origin_list_is_accepted() -> None:
    settings = RuntimeSettings(cors_origins="http://127.0.0.1:3000,https://axiom.example")
    assert settings.cors_origins == "http://127.0.0.1:3000,https://axiom.example"


def test_browser_canonical_cors_origins_are_accepted() -> None:
    settings = RuntimeSettings(
        cors_origins="https://web.example,http://127.0.0.1:3200,https://web.example:8443"
    )
    assert settings.cors_origins == (
        "https://web.example,http://127.0.0.1:3200,https://web.example:8443"
    )
