"""Fail-closed nonproduction-only hosted M1 runtime/pooler parity probe.

The test performs one *rollback-only* A/B isolation transaction against the
genuine least-privileged database login. No administrator credentials, DDL,
mocked database, privileged role or production project are accepted.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from app.database import Database
from app.settings import RuntimeSettings

PROJECT_REF = "zmlgecokvbjdpuclvlqe"
CONFIRMATION = "I_CONFIRM_AXIOM_M1_NONPRODUCTION"
URL_ENV = "AXIOM_HOSTED_TEST_DATABASE_URL"
MODE_ENV = "AXIOM_HOSTED_TEST_POOLER_MODE"


class HostedParityBlocked(Exception):
    """No hosted verification claim may be made if any gate fails."""


def validate_target(env: Mapping[str, str]) -> tuple[str, str]:
    if env.get("AXIOM_HOSTED_TEST_CONFIRMATION") != CONFIRMATION:
        raise HostedParityBlocked("explicit nonproduction authorization missing")
    if any(key.upper().startswith("PG") for key in env):
        raise HostedParityBlocked("libpq routing overrides are not allowed")
    raw = env.get(URL_ENV, "")
    mode = env.get(MODE_ENV, "")
    if mode not in {"session", "transaction"}:
        raise HostedParityBlocked("explicit Supavisor pooler mode required")
    try:
        url = make_url(raw)
    except (ValueError, TypeError):
        raise HostedParityBlocked("invalid runtime connection configuration") from None
    if (
        url.drivername not in {"postgresql", "postgresql+psycopg"}
        or not url.password
        or url.database != "postgres"
        or url.username != f"axiom_runtime.{PROJECT_REF}"
        or url.port != (5432 if mode == "session" else 6543)
        or not isinstance(url.host, str)
        or not url.host.endswith(".pooler.supabase.com")
        or url.host == ".pooler.supabase.com"
        or url.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}
        or any(key not in {"sslmode"} for key in url.query)
    ):
        raise HostedParityBlocked("refused non-allowlisted pooler runtime URL")
    return raw, mode


def check_isolation(db: Database) -> None:
    """Exercise two subjects and wrong-owner writes, then discard every row."""
    alice, bob, workspace = uuid4(), uuid4(), uuid4()
    with db.engine.connect() as conn:
        transaction = conn.begin()
        try:
            conn.execute(
                text("SELECT set_config('app.current_user_id', :subject, true)"),
                {"subject": str(alice)},
            )
            conn.execute(text("INSERT INTO axiom.app_users(id) VALUES (:id)"), {"id": alice})
            conn.execute(
                text("INSERT INTO axiom.workspaces(id, owner_user_id, name) "
                     "VALUES (:id, :owner, 'M1 ephemeral verification')"),
                {"id": workspace, "owner": alice},
            )
            if conn.scalar(
                text("SELECT count(*) FROM axiom.workspaces WHERE id=:id"),
                {"id": workspace},
            ) != 1:
                raise HostedParityBlocked("owner cannot see its row")
            conn.execute(
                text("SELECT set_config('app.current_user_id', :subject, true)"),
                {"subject": str(bob)},
            )
            conn.execute(text("INSERT INTO axiom.app_users(id) VALUES (:id)"), {"id": bob})
            if conn.scalar(
                text("SELECT count(*) FROM axiom.workspaces WHERE id=:id"),
                {"id": workspace},
            ) != 0:
                raise HostedParityBlocked("foreign workspace visible to second subject")
            savepoint = conn.begin_nested()
            try:
                conn.execute(
                    text("INSERT INTO axiom.workspaces(id, owner_user_id, name) "
                         "VALUES (:id, :owner, 'Forbidden')"),
                    {"id": uuid4(), "owner": alice},
                )
            except SQLAlchemyError as exc:
                savepoint.rollback()
                if getattr(getattr(exc, "orig", None), "sqlstate", None) != "42501":
                    raise HostedParityBlocked("foreign write failed for an unexpected reason") from None
            else:
                savepoint.rollback()
                raise HostedParityBlocked("foreign-owner write unexpectedly succeeded")
            if conn.execute(
                text("UPDATE axiom.workspaces SET name='Forbidden' WHERE id=:id"),
                {"id": workspace},
            ).rowcount != 0:
                raise HostedParityBlocked("foreign-owner update unexpectedly succeeded")
        finally:
            # Even on failed checks, ephemeral users/workspaces are never committed.
            transaction.rollback()
        if conn.scalar(text("SELECT axiom.current_subject()")) is not None:
            raise HostedParityBlocked("transaction-local subject leaked across rollback")


def main(env: Mapping[str, str]) -> int:
    db: Database | None = None
    try:
        raw, mode = validate_target(env)
        db = Database(RuntimeSettings(database_url=raw, database_required=True))
        if not db.ready():
            raise HostedParityBlocked("managed migration, role or RLS readiness mismatch")
        with db.engine.connect() as conn:
            role = conn.scalar(text("SELECT current_user"))
            attrs = conn.execute(
                text("SELECT rolsuper, rolbypassrls, rolcreatedb, rolcreaterole "
                     "FROM pg_roles WHERE rolname=current_user"),
            ).one_or_none()
            if role != "axiom_runtime" or attrs is None or any(attrs):
                raise HostedParityBlocked("runtime login is privileged or incorrect")
        check_isolation(db)
        print(f"PASS: hosted Axiom M1 {mode} pooler runtime/RLS rollback-only probe")
        return 0
    except (HostedParityBlocked, SQLAlchemyError, ValueError, TypeError) as exc:
        # Never expose DBAPI error text, URLs or driver-supplied connection details.
        label = str(exc) if isinstance(exc, HostedParityBlocked) else type(exc).__name__
        print(f"BLOCKED: hosted M1 parity not verified ({label})", file=sys.stderr)
        return 1
    finally:
        if db is not None:
            db.close()


if __name__ == "__main__":
    raise SystemExit(main(os.environ))
