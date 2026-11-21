"""Guard regression: pooled transaction mode must not use server-side prepared SQL."""

from __future__ import annotations

from app.database import _pg_connect_args


def test_supavisor_transaction_pooling_disables_autoprepare() -> None:
    url = (
        "postgresql://axiom_runtime.project:dummy@aws-0-ap-south-1."
        "pooler.supabase.com:6543/postgres?sslmode=require"
    )
    assert _pg_connect_args(url) == {"connect_timeout": 3, "prepare_threshold": None}


def test_direct_and_session_connections_keep_default_driver_behavior() -> None:
    urls = (
        "postgresql://axiom_runtime:dummy@localhost:5432/axiom_test",
        "postgresql://axiom_runtime.project:dummy@aws-0-ap-south-1."
        "pooler.supabase.com:5432/postgres",
        "postgresql://axiom_runtime:dummy@db.project.supabase.co:5432/postgres",
        "postgresql://axiom_runtime:dummy@localhost:6543/axiom_test",
    )
    assert all(_pg_connect_args(url) == {"connect_timeout": 3} for url in urls)
