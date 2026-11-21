"""Offline negative controls for the hosted Axiom M1 parity probe.

These deliberately never open a socket, create a role or touch hosted state.
"""

from __future__ import annotations

from importlib import import_module

import pytest

# The verifier is an operator script, not a shipped app package.
# Load it as a module so offline tests exercise its real public entrypoints.
parity = import_module("scripts.verify_hosted_m1_parity")
CONFIRMATION = parity.CONFIRMATION
EXPECTED_HOST_ENV = parity.EXPECTED_HOST_ENV
MODE_ENV = parity.MODE_ENV
PROJECT_REF = parity.PROJECT_REF
URL_ENV = parity.URL_ENV
HostedParityBlocked = parity.HostedParityBlocked
validate_target = parity.validate_target


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
    ("name", "before", "after"),
    [
        ("AXIOM_HOSTED_TEST_CONFIRMATION", CONFIRMATION, "no"),
        (MODE_ENV, "transaction", "direct"),
        (EXPECTED_HOST_ENV, POOLER_HOST, "attacker.example"),
        (EXPECTED_HOST_ENV, POOLER_HOST, "aws-1-ap-south-1.pooler.supabase.com"),
        (URL_ENV, POOLER_HOST, f"attacker.example,{POOLER_HOST}"),
        (URL_ENV, "sslmode=verify-full", "sslmode=require"),
        (URL_ENV, RUNTIME_NAME, "axiom_runtime"),
        (URL_ENV, RUNTIME_NAME, "postgres.project"),
        (URL_ENV, RUNTIME_NAME, "axiom_runtime.wrong"),
        (URL_ENV, ":6543/", ":5432/"),
        (URL_ENV, ":dummy-test-pass@", "@"),
        (URL_ENV, POOLER_HOST, "host.invalid"),
        (URL_ENV, "/postgres?", "/other?"),
        (URL_ENV, "sslmode=verify-full", "sslmode=disable"),
        (
            URL_ENV,
            "sslmode=verify-full",
            "sslmode=verify-full&options=-csearch_path=public",
        ),
    ],
)
def test_refuse_unapproved_credential_routing(name: str, before: str, after: str) -> None:
    env = safe_env()
    # A negative test must change exactly one guard on an otherwise valid URL.
    assert env[name].count(before) == 1
    env[name] = env[name].replace(before, after, 1)
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
