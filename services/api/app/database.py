"""Bounded SQLAlchemy lifecycle and verified transaction-local PostgreSQL subject."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import VerifiedPrincipal
from app.models import HEAD_REVISION
from app.settings import RuntimeSettings

if TYPE_CHECKING:
    from uuid import UUID


def _pg_url(raw: str) -> str:
    parsed = make_url(raw)
    if parsed.drivername not in {"postgresql", "postgresql+psycopg"}:
        raise ValueError("A PostgreSQL connection URL is required")
    return parsed.set(drivername="postgresql+psycopg").render_as_string(hide_password=False)


class Database:
    """One engine per API process, one short transaction per operation, never a global session."""

    def __init__(self, settings: RuntimeSettings) -> None:
        if settings.database_url is None:
            raise ValueError("A runtime database connection is required")
        self.engine: Engine = create_engine(
            _pg_url(settings.database_url.get_secret_value()),
            pool_size=4,
            max_overflow=0,
            pool_timeout=2,
            pool_pre_ping=True,
            pool_reset_on_return="rollback",
            connect_args={"connect_timeout": 3},
        )

    @contextmanager
    def transaction(self, principal: VerifiedPrincipal) -> Iterator[Session]:
        """Use ONLY after successful JWT verification; never accept a caller-supplied UUID."""
        if not isinstance(principal, VerifiedPrincipal):
            raise TypeError("A cryptographically verified principal is required")
        with Session(self.engine, autoflush=False, expire_on_commit=False) as session:
            with session.begin():
                session.execute(
                    text("SELECT set_config('app.current_user_id', :subject, true)"),
                    {"subject": str(principal.user_id)},
                )
                yield session

    def ready(self) -> bool:
        """Fail closed on schema, connection, role, grant, or RLS mismatches; no secrets returned."""
        try:
            with self.engine.connect() as conn:
                revision = conn.execute(text("SELECT version_num FROM public.alembic_version")).scalar_one()
                if revision != HEAD_REVISION:
                    return False
                verdict = conn.execute(
                    text(
                        """SELECT bool_and(
                            NOT r.rolsuper AND NOT r.rolbypassrls
                            AND NOT r.rolcreatedb AND NOT r.rolcreaterole
                            AND NOT has_schema_privilege(current_user, 'axiom', 'CREATE')
                            AND NOT has_database_privilege(current_user, current_database(), 'CREATE')
                            AND c.relrowsecurity AND NOT pg_has_role(current_user, c.relowner, 'MEMBER')
                         )
                         FROM pg_class c
                         JOIN pg_namespace n ON n.oid = c.relnamespace
                         CROSS JOIN pg_roles r
                         WHERE r.rolname = current_user AND n.nspname = 'axiom'
                           AND c.relname IN ('app_users', 'workspaces', 'workspace_create_idempotency')
                           AND c.relkind = 'r'"""
                    )
                ).scalar_one_or_none()
                count = conn.execute(
                    text(
                        """SELECT count(*) FROM pg_class c JOIN pg_namespace n
                           ON n.oid = c.relnamespace WHERE n.nspname = 'axiom'
                           AND c.relkind = 'r'
                           AND c.relname IN ('app_users', 'workspaces', 'workspace_create_idempotency')"""
                    )
                ).scalar_one()
                return bool(verdict) and count == 3
        except (SQLAlchemyError, ValueError, TypeError):
            return False

    def close(self) -> None:
        self.engine.dispose()
