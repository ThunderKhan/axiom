"""Reproducible isolated local/CI PostgreSQL migration and RLS gate.

Strictly restricted to the explicitly opted-in loopback axiom_test database.
Never repurpose this runner for hosted or existing user databases.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import psycopg
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
ENV_NAMES = (
    "AXIOM_TEST_ADMIN_DATABASE_URL",
    "AXIOM_MIGRATION_DATABASE_URL",
    "AXIOM_TEST_RUNTIME_DATABASE_URL",
)


def run(*args: str, expect_failure: bool = False) -> None:
    print(f"Running isolated database check: {' '.join(args)}", flush=True)
    result = subprocess.run(args, cwd=ROOT, check=False)  # noqa: S603
    if (result.returncode != 0) != expect_failure:
        raise RuntimeError(f"Database verification check failed (exit {result.returncode})")


def main() -> int:
    for name in ENV_NAMES:
        if not os.environ.get(name):
            raise RuntimeError(f"Missing {name} for isolated PostgreSQL verification")
        parsed = make_url(os.environ[name])
        if (
            parsed.drivername not in {"postgresql", "postgresql+psycopg"}
            or parsed.host != "127.0.0.1"
            or parsed.port != 55432
            or parsed.database != "axiom_test"
        ):
            raise RuntimeError("This test runner permits only loopback axiom_test:55432")
    with psycopg.connect(os.environ[ENV_NAMES[0]], autocommit=True) as admin:
        if admin.execute("SELECT current_user").fetchone()[0] != "postgres":
            raise RuntimeError("Expected the explicitly isolated PostgreSQL test administrator")
        roles = admin.execute(
            "SELECT rolname FROM pg_roles WHERE rolname IN ('axiom_runtime','axiom_migrator')"
        ).fetchall()
        if not roles:
            admin.execute((ROOT / "tests/postgres_roles.sql").read_text(encoding="utf-8"))
        elif len(roles) != 2:
            raise RuntimeError("Partially configured test roles; do not guess recovery")
    with psycopg.connect(os.environ[ENV_NAMES[0]]) as admin:
        version_exists = admin.execute(
            "SELECT to_regclass('public.alembic_version') IS NOT NULL"
        ).fetchone()[0]
        revision = (
            admin.execute("SELECT version_num FROM public.alembic_version").fetchone()[0]
            if version_exists
            else None
        )
    if revision is None:
        run("uv", "run", "--frozen", "alembic", "upgrade", "m1_0001_schema")
    elif revision not in ("m1_0001_schema", "m1_0002_rls"):
        raise RuntimeError("Unexpected migration state in isolated test database")
    run("uv", "run", "--frozen", "alembic", "upgrade", "head")
    run("uv", "run", "--frozen", "alembic", "upgrade", "head")
    run("uv", "run", "--frozen", "alembic", "check")
    # Both migrations deliberately prohibit destructive rollback. Verify that
    # attempted downgrade fails without changing the schema revision.
    run(
        "uv", "run", "--frozen", "alembic", "downgrade", "m1_0001_schema",
        expect_failure=True,
    )
    with psycopg.connect(os.environ[ENV_NAMES[0]]) as admin:
        unchanged = admin.execute(
            "SELECT version_num FROM public.alembic_version"
        ).fetchone()
        if unchanged != ("m1_0002_rls",):
            raise RuntimeError("A refused downgrade unexpectedly changed the schema revision")
    run("uv", "run", "--frozen", "alembic", "check")
    # Drift detection must reject an unexpected index; remove it only from this
    # explicitly isolated ephemeral database, even if the negative check fails.
    with psycopg.connect(os.environ["AXIOM_MIGRATION_DATABASE_URL"], autocommit=True) as migration:
        migration.execute("CREATE INDEX ix_m1_temporary_drift_probe ON axiom.workspaces (name)")
        try:
            run("uv", "run", "--frozen", "alembic", "check", expect_failure=True)
        finally:
            migration.execute("DROP INDEX IF EXISTS axiom.ix_m1_temporary_drift_probe")
    run("uv", "run", "--frozen", "alembic", "check")
    run(
        "uv",
        "run",
        "--frozen",
        "pytest",
        "-q",
        "-m",
        "postgres",
        "tests/test_database_integration.py",
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, psycopg.Error) as exc:
        # Never stringify connection errors: they can disclose secret connection URLs.
        print(f"Isolated DB verification aborted: {type(exc).__name__}", file=sys.stderr)
        raise SystemExit(1) from None
