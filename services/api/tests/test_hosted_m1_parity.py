"""Offline negative controls for the hosted Axiom M1 parity probe.

These deliberately never open a socket, create a role or touch hosted state.
"""

from __future__ import annotations

import pytest

from scripts.verify_hosted_m1_parity import (
    CONFIRMATION,
    EXPECTED_HOST_ENV,
    HostedParityBlocked,
    MODE_ENV,
    PROJECT_REF,
    URL_ENV,
    validate_target,
)


RUNTIME_NAME = f"axiom_runtime.{PROJECT_REF}"
POOLER_HOST = "aws-0-ap-south-1.pooler.supabase.com"


def safe_env(mode: str = "transaction") -> dict[str, str]:
    return {
        "AXIOM_HOSTED_TEST_CONFIRMATION": CONFIRMATION,
        MODE_ENV: mode,
        EXPECTED_HOST_ENV: POOLER_HOST,
        URL_ENV: (
            f"postgresql://{RUNTIME_NAME}:dummy-test-pass"
            "@aws-0-ap-south-1.pooler.supabase.com:"
            f"{6543 if mode == 'transaction' else 5432}/postgres?sslmode=verify-full"
        ),
    }


@pytest.mark.parametrize("mode", ["transaction", "session"])
def test_matching_nonproduction_pooler_and_runtime_role(mode: str) -> None:
    url, confirmed_mode = validate_target(safe_env(mode))
    assert "dummy-test-pass" in url
    assert confirmed_mode == mode


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("AXIOM_HOSTED_TEST_CONFIRMATION", "no"),
        (MODE_ENV, "direct"),
        (EXPECTED_HOST_ENV, "attacker.example"),
        (EXPECTED_HOST_ENV, "aws-1-ap-south-1.pooler.supabase.com"),
        (
            URL_ENV,
            f"postgresql://{RUNTIME_NAME}:pass@attacker.example,{POOLER_HOST}:6543/"
            "postgres?sslmode=verify-full",
        ),
        (
            URL_ENV,
            f"postgresql://{RUNTIME_NAME}:pass@{POOLER_HOST}:6543/"
            "postgres?sslmode=require",
        ),
        (URL_ENV, "postgresql://axiom_runtime:pass@db.fake.supabase.co:5432/postgres"),
        (URL_ENV, "postgresql://postgres.project:pass@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"),
        (URL_ENV, "postgresql://axiom_runtime.wrong:pass@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"),
        (URL_ENV, f"postgresql://{RUNTIME_NAME}:pass@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"),
        (URL_ENV, f"postgresql://{RUNTIME_NAME}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"),
        (URL_ENV, f"postgresql://{RUNTIME_NAME}:pass@host.invalid:6543/postgres"),
        (
            URL_ENV,
            f"postgresql://{RUNTIME_NAME}:pass@aws-0-ap-south-1.pooler.supabase.com:6543/"
            "other?sslmode=verify-full",
        ),
        (
            URL_ENV,
            f"postgresql://{RUNTIME_NAME}:pass@aws-0-ap-south-1.pooler.supabase.com:6543/"
            "postgres?sslmode=disable",
        ),
        (
            URL_ENV,
            f"postgresql://{RUNTIME_NAME}:pass@aws-0-ap-south-1.pooler.supabase.com:6543/"
            "postgres?sslmode=verify-full&options=-csearch_path=public",
        ),
    ],
)
def test_refuse_unapproved_credential_routing(name: str, value: str) -> None:
    env = safe_env()
    env[name] = value
    with pytest.raises(HostedParityBlocked):
        validate_target(env)


def test_refuse_libpq_override_and_missing_confirmation() -> None:
    env = safe_env()
    env["PGHOST"] = "malicious"
    with pytest.raises(HostedParityBlocked):
        validate_target(env)
    del env["PGHOST"]
    del env["AXIOM_HOSTED_TEST_CONFIRMATION"]
    with pytest.raises(HostedParityBlocked):
        validate_target(env)
