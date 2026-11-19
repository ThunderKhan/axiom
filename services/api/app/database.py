"""Bounded SQLAlchemy lifecycle and verified transaction-local PostgreSQL subject."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import VerifiedPrincipal
from app.models import HEAD_REVISION
from app.settings import RuntimeSettings


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
        """Fail closed on schema, runtime role, grants and exact RLS policy presence."""
        try:
            with self.engine.connect() as conn:
                revision = conn.scalar(text("SELECT version_num FROM public.alembic_version"))
                if revision != HEAD_REVISION:
                    return False
                role_safe = conn.scalar(
                    text(
                        """SELECT count(*) = 3 AND bool_and(
                            NOT r.rolsuper AND NOT r.rolbypassrls
                            AND NOT r.rolcreatedb AND NOT r.rolcreaterole
                            AND NOT has_schema_privilege(current_user, 'axiom', 'CREATE')
                            AND NOT has_database_privilege(
                                current_user, current_database(), 'CREATE'
                            )
                            AND c.relrowsecurity
                            AND NOT pg_has_role(current_user, c.relowner, 'MEMBER')
                         )
                         FROM pg_class c
                         JOIN pg_namespace n ON n.oid = c.relnamespace
                         CROSS JOIN pg_roles r
                         WHERE r.rolname = current_user AND n.nspname = 'axiom'
                           AND c.relname IN (
                               'app_users', 'workspaces', 'workspace_create_idempotency'
                           )
                           AND c.relkind = 'r'"""
                    )
                )
                if role_safe is not True:
                    return False
                policies_safe = conn.scalar(
                    text(
                        """SELECT
                            (SELECT count(*) FROM pg_policies
                             WHERE schemaname = 'axiom') = 7
                            AND NOT EXISTS (
                                SELECT 1 FROM (
                                    VALUES
                                    ('app_users', 'app_user_own_read', 'SELECT'),
                                    ('app_users', 'app_user_own_bootstrap', 'INSERT'),
                                    ('workspaces', 'workspaces_own_read', 'SELECT'),
                                    ('workspaces', 'workspaces_own_insert', 'INSERT'),
                                    ('workspaces', 'workspace_own_update', 'UPDATE'),
                                    ('workspace_create_idempotency',
                                     'workspace_create_idempotency_own_read', 'SELECT'),
                                    ('workspace_create_idempotency',
                                     'workspace_create_idempotency_own_insert', 'INSERT')
                                ) AS required(table_name, policy_name, command)
                                LEFT JOIN pg_policies p
                                  ON p.schemaname = 'axiom'
                                 AND p.tablename = required.table_name
                                 AND p.policyname = required.policy_name
                                 AND p.cmd = required.command
                                 AND p.permissive = 'PERMISSIVE'
                                 AND 'axiom_runtime' = ANY(p.roles)
                                WHERE p.policyname IS NULL
                                   OR (required.command IN ('SELECT', 'UPDATE')
                                       AND p.qual IS NULL)
                                   OR (required.command IN ('INSERT', 'UPDATE')
                                       AND p.with_check IS NULL)
                            )"""
                    )
                )
                if policies_safe is not True:
                    return False
                grants_safe = conn.scalar(
                    text(
                        """SELECT
                            has_schema_privilege(current_user, 'axiom', 'USAGE')
                            AND has_function_privilege(
                                current_user, 'axiom.current_subject()', 'EXECUTE'
                            )
                            AND has_table_privilege(
                                current_user, 'axiom.app_users', 'SELECT'
                            )
                            AND has_table_privilege(
                                current_user, 'axiom.workspaces', 'SELECT'
                            )
                            AND has_table_privilege(
                                current_user, 'axiom.workspace_create_idempotency', 'SELECT'
                            )
                            AND (
                                SELECT bool_and(
                                    has_column_privilege(
                                        current_user,
                                        format('axiom.%I', required.table_name),
                                        required.column_name,
                                        required.action
                                    )
                                )
                                FROM (VALUES
                                    ('app_users', 'id', 'INSERT'),
                                    ('workspaces', 'id', 'INSERT'),
                                    ('workspaces', 'owner_user_id', 'INSERT'),
                                    ('workspaces', 'name', 'INSERT'),
                                    ('workspaces', 'name', 'UPDATE'),
                                    ('workspaces', 'updated_at', 'UPDATE'),
                                    ('workspaces', 'version', 'UPDATE'),
                                    ('workspace_create_idempotency', 'owner_user_id', 'INSERT'),
                                    ('workspace_create_idempotency', 'operation', 'INSERT'),
                                    ('workspace_create_idempotency', 'key', 'INSERT'),
                                    ('workspace_create_idempotency', 'fingerprint', 'INSERT'),
                                    ('workspace_create_idempotency', 'response_status', 'INSERT'),
                                    ('workspace_create_idempotency', 'response_body', 'INSERT'),
                                    ('workspace_create_idempotency', 'expires_at', 'INSERT')
                                ) AS required(table_name, column_name, action)
                            )
                            AND NOT has_table_privilege(
                                current_user, 'axiom.workspaces', 'DELETE'
                            )
                            AND NOT has_column_privilege(
                                current_user, 'axiom.workspaces', 'owner_user_id', 'UPDATE'
                            )"""
                    )
                )
                return grants_safe is True
        except (SQLAlchemyError, ValueError, TypeError):
            return False

    def close(self) -> None:
        self.engine.dispose()
