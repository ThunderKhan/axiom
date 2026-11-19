"""Unit regression checks: disposable PostgreSQL runner validates before SQL."""

from __future__ import annotations

import pytest

from scripts.run_db_integration import validate_test_environment

URLS = {
    "AXIOM_TEST_ADMIN_DATABASE_URL": "postgresql://postgres@127.0.0.1:55432/axiom_test",
    "AXIOM_MIGRATION_DATABASE_URL": "postgresql://axiom_migrator@127.0.0.1:55432/axiom_test",
    "AXIOM_TEST_RUNTIME_DATABASE_URL": "postgresql://axiom_runtime@127.0.0.1:55432/axiom_test",
}


def test_exact_isolated_urls_are_accepted() -> None:
    validate_test_environment(URLS)


@pytest.mark.parametrize(
    "query",
    (
        "?hostaddr=192.0.2.10",
        "?host=remote.example",
        "?port=5432",
        "?service=unsafe",
        "?sslmode=disable",
        "?options=-csearch_path%3Dpublic",
    ),
)
def test_query_overrides_rejected_before_database_access(query: str) -> None:
    urls = {**URLS, "AXIOM_MIGRATION_DATABASE_URL": URLS["AXIOM_MIGRATION_DATABASE_URL"] + query}
    with pytest.raises(RuntimeError, match="fixed local DB roles"):
        validate_test_environment(urls)


@pytest.mark.parametrize(
    "variable",
    (
        "PGHOST",
        "PGHOSTADDR",
        "PGPORT",
        "PGUSER",
        "PGDATABASE",
        "PGSERVICE",
        "PGSERVICEFILE",
        "PGPASSFILE",
        "PGOPTIONS",
        "PGSSLMODE",
        "PGPASSWORD",
    ),
)
def test_libpq_environment_overrides_rejected(variable: str) -> None:
    with pytest.raises(RuntimeError, match="environment overrides"):
        validate_test_environment({**URLS, variable: "remote.example"})


@pytest.mark.parametrize(
    ("name", "replacement"),
    (
        ("AXIOM_TEST_ADMIN_DATABASE_URL", "postgresql://postgres@192.0.2.10:55432/axiom_test"),
        ("AXIOM_TEST_ADMIN_DATABASE_URL", "postgresql://postgres@127.0.0.1:5432/axiom_test"),
        ("AXIOM_TEST_ADMIN_DATABASE_URL", "postgresql://postgres@127.0.0.1:55432/other_db"),
        ("AXIOM_TEST_ADMIN_DATABASE_URL", "postgresql://axiom_runtime@127.0.0.1:55432/axiom_test"),
        ("AXIOM_TEST_RUNTIME_DATABASE_URL", "postgresql://postgres@127.0.0.1:55432/axiom_test"),
    ),
)
def test_nonisolated_and_wrong_role_urls_rejected(name: str, replacement: str) -> None:
    with pytest.raises(RuntimeError, match="fixed local DB roles"):
        validate_test_environment({**URLS, name: replacement})


def test_missing_connection_configuration_rejected() -> None:
    urls = dict(URLS)
    urls.pop("AXIOM_MIGRATION_DATABASE_URL")
    with pytest.raises(RuntimeError, match="Missing AXIOM_MIGRATION_DATABASE_URL"):
        validate_test_environment(urls)
