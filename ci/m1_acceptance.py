"""Fail-closed, trace-free M1 real-provider acceptance runner.

Only the opt-in nonproduction provider suite can satisfy this technical gate.
Credential-bearing Playwright output is captured in memory and NEVER printed.
Passing this runner does not replace managed-DB parity or human security review.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"
SHA_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
PROJECT_HOST = re.compile(r"[a-z0-9][a-z0-9-]{1,62}\.supabase\.co\Z")
REQUIRED_TEST_TITLES = frozenset(
    {
        "real authorized user signs in, survives refresh, then loses private access",
        "two authorized users create and isolate workspaces",
        "M1 genuine JWT and two-user cross-tenant API acceptance",
    }
)
REQUIRED = (
    "M1_ACCEPTANCE_HEAD_SHA",
    "M1_ACCEPTANCE_ISSUER",
    "NEXT_PUBLIC_SUPABASE_URL",
    "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY",
    "NEXT_PUBLIC_API_BASE_URL",
    "E2E_SUPABASE_EMAIL",
    "E2E_SUPABASE_PASSWORD",
    "E2E_SUPABASE_SECOND_EMAIL",
    "E2E_SUPABASE_SECOND_PASSWORD",
)


class AcceptanceBlocked(Exception):
    """An acceptance prerequisite or actual mandatory test is not satisfied."""


def verified_head() -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True,
            text=True, timeout=10,
        )
        value = completed.stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        raise AcceptanceBlocked("Cannot verify the checked-out commit") from exc
    if not SHA_PATTERN.fullmatch(value):
        raise AcceptanceBlocked("Checked-out commit must be a full SHA")
    return value


def require_clean_checkout(root: Path = ROOT) -> None:
    """Do not attribute provider execution to a commit with modified or untracked source."""
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all",
             "--ignore-submodules=none"],
            cwd=root, check=True, capture_output=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise AcceptanceBlocked("Cannot verify that the checkout is clean") from exc
    if completed.stdout:
        # Git status may contain private local paths. Never print its output.
        raise AcceptanceBlocked("Checkout has tracked changes or untracked files")


def preflight(env: Mapping[str, str], head: str) -> None:
    """Validate nonproduction intent, the exact SHA and public origins, not secrets."""
    if env.get("M1_ACCEPTANCE_NONPRODUCTION") != "I_CONFIRM_NONPRODUCTION":
        raise AcceptanceBlocked("Explicit authorized nonproduction opt-in is missing")
    if env.get("E2E_M1_ACCEPTANCE") != "1" or env.get("E2E_WORKSPACE_API_READY") != "1":
        raise AcceptanceBlocked("The full M1 provider suite is not enabled")
    missing = [name for name in REQUIRED if not env.get(name)]
    if missing:
        raise AcceptanceBlocked("Missing required environment variable names: " + ", ".join(missing))
    expected = env["M1_ACCEPTANCE_HEAD_SHA"]
    if not SHA_PATTERN.fullmatch(expected) or head != expected:
        raise AcceptanceBlocked("Tested commit does not equal the requested full PR head SHA")
    url = urlsplit(env["NEXT_PUBLIC_SUPABASE_URL"])
    if (
        url.scheme != "https"
        or not url.hostname
        or not PROJECT_HOST.fullmatch(url.hostname)
        or url.port is not None
        or url.username is not None
        or url.password is not None
        or url.query
        or url.fragment
        or url.path not in ("", "/")
        or env["NEXT_PUBLIC_SUPABASE_URL"] != "https://" + url.hostname
    ):
        raise AcceptanceBlocked("Supabase test URL must be an exact canonical HTTPS project origin")
    if env["M1_ACCEPTANCE_ISSUER"] != env["NEXT_PUBLIC_SUPABASE_URL"] + "/auth/v1":
        raise AcceptanceBlocked("M1 issuer must match the selected public Auth project")
    if env.get("AXIOM_AUTH_ISSUER") != env["M1_ACCEPTANCE_ISSUER"]:
        raise AcceptanceBlocked("FastAPI issuer must match the browser provider issuer")
    if env.get("AXIOM_AUTH_AUDIENCE") != "authenticated":
        raise AcceptanceBlocked("FastAPI must verify the ordinary authenticated audience")
    if env.get("AXIOM_AUTH_JWKS_URL") != env["M1_ACCEPTANCE_ISSUER"] + "/.well-known/jwks.json":
        raise AcceptanceBlocked("FastAPI JWKS must match the same trusted Auth issuer")
    if not env["NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"].startswith("sb_publishable_"):
        raise AcceptanceBlocked("Public browser key must be a Supabase publishable key")
    if env["NEXT_PUBLIC_API_BASE_URL"] != "http://127.0.0.1:8000":
        raise AcceptanceBlocked("Only the isolated loopback FastAPI test origin is permitted")
    if env["E2E_SUPABASE_EMAIL"].strip().casefold() == env["E2E_SUPABASE_SECOND_EMAIL"].strip().casefold():
        raise AcceptanceBlocked("Two distinct ordinary Supabase test accounts are required")
    if env.get("E2E_SUPABASE_EVALUATOR_EMAIL") or env.get("E2E_SUPABASE_EVALUATOR_PASSWORD"):
        if not (env.get("E2E_SUPABASE_EVALUATOR_EMAIL") and env.get("E2E_SUPABASE_EVALUATOR_PASSWORD")):
            raise AcceptanceBlocked("The optional evaluator account must provide both fields")
    if env.get("AXIOM_DATABASE_REQUIRED", "").lower() != "true":
        raise AcceptanceBlocked("FastAPI must require its verified PostgreSQL database")


def require_real_database_readiness() -> None:
    # This is a real HTTP request to the configured loopback API. M0-only health
    # cannot claim DB/RLS readiness. The actual DB migration/RLS suite runs
    # separately as a mandatory step in the trusted acceptance workflow.
    try:
        with urlopen("http://127.0.0.1:8000/api/v1/health/ready", timeout=5) as response:
            if response.status != 200:
                raise AcceptanceBlocked("The real API/database readiness check did not pass")
            payload = json.load(response)
    except (OSError, HTTPError, URLError, ValueError) as exc:
        raise AcceptanceBlocked("Real FastAPI/database readiness unavailable") from exc
    if not isinstance(payload, dict) or payload.get("status") != "ready" or payload.get("dependencies") != "database_verified":
        raise AcceptanceBlocked("API did not verify database role, schema and RLS readiness")


def validated_report(document: Any) -> int:
    """Only the required named tests executed and passed, with no skipped tests."""
    if not isinstance(document, dict) or not isinstance(document.get("stats"), dict):
        raise AcceptanceBlocked("Playwright JSON evidence is missing")
    stats = document["stats"]
    if (
        type(stats.get("expected")) is not int
        or stats["expected"] < len(REQUIRED_TEST_TITLES)
        or stats.get("unexpected") != 0
        or stats.get("skipped") != 0
        or stats.get("flaky") != 0
    ):
        raise AcceptanceBlocked("Required provider test execution was failed, skipped or incomplete")
    titles: list[str] = []

    def walk(suites: Any) -> None:
        if not isinstance(suites, list):
            raise AcceptanceBlocked("Malformed Playwright report suites")
        for suite in suites:
            if not isinstance(suite, dict):
                raise AcceptanceBlocked("Malformed Playwright suite record")
            for spec in suite.get("specs", []):
                if not isinstance(spec, dict) or not isinstance(spec.get("title"), str):
                    raise AcceptanceBlocked("Malformed Playwright test record")
                tests = spec.get("tests")
                if not isinstance(tests, list) or len(tests) != 1:
                    raise AcceptanceBlocked("Ambiguous or unexecuted Playwright test")
                result = tests[0]
                if (
                    not isinstance(result, dict)
                    or result.get("status") != "expected"
                    or not isinstance(result.get("results"), list)
                    or len(result["results"]) != 1
                    or result["results"][0].get("status") != "passed"
                ):
                    raise AcceptanceBlocked("Playwright provider test did not pass exactly once")
                titles.append(spec["title"])
            walk(suite.get("suites", []))

    walk(document.get("suites"))
    if len(titles) != stats["expected"] or len(set(titles)) != len(titles):
        raise AcceptanceBlocked("Playwright test counts or identities do not agree")
    if set(titles) != REQUIRED_TEST_TITLES:
        raise AcceptanceBlocked("Required real-provider test is missing or replaced")
    return len(titles)


def run_provider(env: Mapping[str, str], *, head: str) -> None:
    preflight(env, head)
    require_clean_checkout()
    require_real_database_readiness()
    command = [
        "node", "node_modules/playwright/cli.js", "test",
        "--config=playwright.provider.config.ts", "--reporter=json", "--workers=1",
    ]
    try:
        result = subprocess.run(
            command, cwd=WEB, env=dict(env), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=600, check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise AcceptanceBlocked("Real-provider suite did not complete") from exc
    # Check after execution too: the provider tests may have altered tracked or
    # untracked executable inputs without changing HEAD.
    require_clean_checkout()
    if result.returncode != 0:
        # NEVER print Playwright stdout/stderr: these can contain passwords,
        # credentials, cookies, tokens, URLs or private browser state.
        raise AcceptanceBlocked("Real-provider suite failed; private diagnostics withheld")
    try:
        report = json.loads(result.stdout)
    except (UnicodeError, ValueError) as exc:
        raise AcceptanceBlocked("No parseable real-provider test execution report") from exc
    count = validated_report(report)
    if verified_head() != head:
        raise AcceptanceBlocked("Repository SHA changed during real-provider verification")
    print(f"PASS: {count} real-provider Playwright tests at SHA {head}.")
    print("Evidence class: authorized nonproduction Supabase Auth + isolated FastAPI/PostgreSQL/RLS.")
    print("NOT VERIFIED: managed Supabase database parity, provider revocation SLA, deployed HTTPS, human signoff.")


def self_test() -> None:
    """Negative proof that missing evidence, skipped tests and stale heads block."""
    env: dict[str, str] = {}
    for name in REQUIRED:
        env[name] = "fixture"
    env.update(
        {
            "M1_ACCEPTANCE_HEAD_SHA": "a" * 40,
            "M1_ACCEPTANCE_NONPRODUCTION": "I_CONFIRM_NONPRODUCTION",
            "E2E_M1_ACCEPTANCE": "1",
            "E2E_WORKSPACE_API_READY": "1",
            "NEXT_PUBLIC_SUPABASE_URL": "https://example-test.supabase.co",
            "M1_ACCEPTANCE_ISSUER": "https://example-test.supabase.co/auth/v1",
            "AXIOM_AUTH_ISSUER": "https://example-test.supabase.co/auth/v1",
            "AXIOM_AUTH_AUDIENCE": "authenticated",
            "AXIOM_AUTH_JWKS_URL": "https://example-test.supabase.co/auth/v1/.well-known/jwks.json",
            "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY": "sb_publishable_fixture_not_a_real_key",
            "NEXT_PUBLIC_API_BASE_URL": "http://127.0.0.1:8000",
            "E2E_SUPABASE_EMAIL": "a@example.test",
            "E2E_SUPABASE_SECOND_EMAIL": "b@example.test",
            "AXIOM_DATABASE_REQUIRED": "true",
        }
    )
    preflight(env, "a" * 40)
    cases = [
        ({k: v for k, v in env.items() if k != "E2E_SUPABASE_PASSWORD"}, "a" * 40),
        (env, "b" * 40),
        ({**env, "M1_ACCEPTANCE_NONPRODUCTION": "no"}, "a" * 40),
        ({**env, "E2E_SUPABASE_SECOND_EMAIL": env["E2E_SUPABASE_EMAIL"]}, "a" * 40),
        ({**env, "NEXT_PUBLIC_API_BASE_URL": "https://api.example.test"}, "a" * 40),
        ({**env, "AXIOM_AUTH_ISSUER": "https://other.supabase.co/auth/v1"}, "a" * 40),
    ]
    for scenario, sha in cases:
        try:
            preflight(scenario, sha)
        except AcceptanceBlocked:
            pass
        else:
            raise AssertionError("Fail-closed preflight accepted an unsafe fixture")

    def test_report(titles: list[str]) -> dict[str, Any]:
        return {
            "stats": {"expected": len(titles), "unexpected": 0, "skipped": 0, "flaky": 0},
            "suites": [{
                "specs": [
                    {"title": title, "tests": [{"status": "expected", "results": [{"status": "passed"}]}]}
                    for title in titles
                ],
                "suites": [],
            }],
        }

    valid = test_report(sorted(REQUIRED_TEST_TITLES))
    assert validated_report(valid) == len(REQUIRED_TEST_TITLES)
    bad = [
        {},
        test_report([]),
        test_report(sorted(REQUIRED_TEST_TITLES)[:2]),
        {**valid, "stats": {**valid["stats"], "skipped": 1}},
        {**valid, "stats": {**valid["stats"], "unexpected": 1}},
        {**valid, "stats": {**valid["stats"], "expected": 999}},
    ]
    for item in bad:
        try:
            validated_report(item)
        except AcceptanceBlocked:
            pass
        else:
            raise AssertionError("Fail-closed gate accepted incomplete or failed evidence")
    altered = test_report(sorted(REQUIRED_TEST_TITLES))
    altered["suites"][0]["specs"][0]["tests"][0]["status"] = "skipped"
    try:
        validated_report(altered)
    except AcceptanceBlocked:
        pass
    else:
        raise AssertionError("Skipped mandatory test was accepted")
    # Use a disposable repository so this guard itself is exercised by offline CI.
    with TemporaryDirectory(prefix="axiom-m1-checkout-") as directory:
        checkout = Path(directory)
        fixture = checkout / "provider.spec.ts"
        fixture.write_text("original test\\n", encoding="utf-8")

        def git(*args: str) -> None:
            subprocess.run(
                ["git", *args], cwd=checkout, check=True,
                capture_output=True, timeout=10,
            )

        git("init", "--quiet")
        git("add", "provider.spec.ts")
        git("-c", "user.name=Acceptance Fixture",
            "-c", "user.email=fixture@example.test", "commit", "--quiet",
            "-m", "test clean checkout")
        require_clean_checkout(checkout)

        fixture.write_text("modified test\\n", encoding="utf-8")
        try:
            require_clean_checkout(checkout)
        except AcceptanceBlocked:
            pass
        else:
            raise AssertionError("Changed tracked provider test was accepted")
        fixture.write_text("original test\\n", encoding="utf-8")

        untracked = checkout / "injected-provider-test.ts"
        untracked.write_text("untracked code\\n", encoding="utf-8")
        try:
            require_clean_checkout(checkout)
        except AcceptanceBlocked:
            pass
        else:
            raise AssertionError("Untracked executable input was accepted")
        untracked.unlink()
        require_clean_checkout(checkout)
    print("PASS: M1 acceptance gate negative controls (no provider connection).")


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) == 2 else ""
    try:
        if mode == "self-test":
            self_test()
        elif mode == "preflight":
            preflight(os.environ, verified_head())
            require_clean_checkout()
            print("PASS: nonproduction provider settings and exact SHA prerequisites.")
            print("NOT VERIFIED: provider/DB execution; preflight alone is not acceptance.")
        elif mode == "run":
            run_provider(os.environ, head=verified_head())
        else:
            print("Usage: python ci/m1_acceptance.py self-test|preflight|run", file=sys.stderr)
            return 2
        return 0
    except AcceptanceBlocked as exc:
        print("M1 ACCEPTANCE BLOCKED: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
