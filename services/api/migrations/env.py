"""Migration-only entrypoint; never imports runtime database secrets."""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import create_engine, pool

from app.database import _pg_url
from app.models import Base

config = context.config
target_metadata = Base.metadata


def include_name(name: str | None, type_: str, parent_names: dict[str, str | None]) -> bool:
    """Do not inspect or mutate managed Supabase/public schemas outside M1."""
    if type_ == "schema":
        return name in {None, "axiom"}
    if type_ == "table":
        return parent_names.get("schema_name") == "axiom"
    return True


def run_migrations_online() -> None:
    raw = os.environ.get("AXIOM_MIGRATION_DATABASE_URL")
    if not raw:
        raise RuntimeError("A dedicated AXIOM_MIGRATION_DATABASE_URL is required")
    engine = create_engine(
        _pg_url(raw),
        poolclass=pool.NullPool,
        connect_args={"connect_timeout": 3},
    )
    try:
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                include_schemas=True,
                include_name=include_name,
                compare_type=True,
                transactional_ddl=True,
            )
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline SQL rendering is not authorized for this migration workflow")
run_migrations_online()
