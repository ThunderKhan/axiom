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
M1_TENANT_TITLE = "M1 genuine JWT and two-user cross-tenant API acceptance"
P0_TENANT_TITLE = "P0 genuine founder browser and two-user tenant acceptance"


def required_titles(p0_enabled: bool = False) -> frozenset[str]:
    if not p0_enabled:
        return REQUIRED_TEST_TITLES
    return (REQUIRED_TEST_TITLES - {M1_TENANT_TITLE}) | {P0_TENANT_TITLE}


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


def require_expected_head(env: Mapping[str, str], head: str) -> None:
    """Reject a clean checkout at a different commit than the intended revision."""
    expected = env.get("M1_ACCEPTANCE_HEAD_SHA", "")
    if not SHA_PATTERN.fullmatch(expected) or head != expected:
        raise AcceptanceBlocked("Tested commit does not equal the requested full PR head SHA")


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
    if env.get("E2E_P0_ACCEPTANCE", "0") not in {"0", "1"}:
        raise AcceptanceBlocked("Invalid P0 acceptance mode")
    missing = [name for name in REQUIRED if not env.get(name)]
    if missing:
        raise AcceptanceBlocked("Missing required environment variable names: " + ", ".join(missing))
    require_expected_head(env, head)
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


def validated_report(document: Any, *, p0_enabled: bool = False) -> int:
    """Only the required named tests executed and passed, with no skipped tests."""
    required = required_titles(p0_enabled)
    if not isinstance(document, dict) or not isinstance(document.get("stats"), dict):
        raise AcceptanceBlocked("Playwright JSON evidence is missing")
    stats = document["stats"]
    if (
        type(stats.get("expected")) is not int
        or stats["expected"] < len(required)
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
    if set(titles) != required:
        raise AcceptanceBlocked("Required real-provider test is missing or replaced")
    return len(titles)


# Only hard-coded, public test names and enumerated outcome labels may reach CI.
# Never emit Playwright's error, stack, stdout/stderr, request, URL or test attachments.
SAFE_PROVIDER_LABELS = (
    ("real authorized user signs in, survives refresh, then loses private access", "AUTH_SESSION"),
    ("two authorized users create and isolate workspaces", "WORKSPACE_UI"),
    ("M1 genuine JWT and two-user cross-tenant API acceptance", "TENANT_API"),
)
SAFE_PROVIDER_TEST_FILES = {
    "AUTH_SESSION": "auth-provider.smoke.spec.ts",
    "WORKSPACE_UI": "workspace-provider.smoke.spec.ts",
    "TENANT_API": "m1-acceptance.provider.spec.ts",
}


def sanitized_provider_outcomes(output: bytes, *, p0_enabled: bool = False) -> str:
    """Summarize expected Playwright test outcomes without revealing private diagnostics."""
    try:
        report = json.loads(output)
    except (UnicodeError, ValueError):
        return "M1 provider outcomes: report unavailable (private diagnostics withheld)"
    if not isinstance(report, dict):
        return "M1 provider outcomes: report unavailable (private diagnostics withheld)"

    labels = (
        tuple((P0_TENANT_TITLE if title == M1_TENANT_TITLE else title, code)
              for title, code in SAFE_PROVIDER_LABELS)
        if p0_enabled else SAFE_PROVIDER_LABELS
    )
    observations: dict[str, list[str]] = {title: [] for title, _ in labels}

    def visit(suites: Any) -> None:
        if not isinstance(suites, list):
            return
        for suite in suites:
            if not isinstance(suite, dict):
                continue
            specs = suite.get("specs")
            if isinstance(specs, list):
                for spec in specs:
                    if not isinstance(spec, dict):
                        continue
                    title = spec.get("title")
                    if not isinstance(title, str) or title not in observations:
                        continue
                    tests = spec.get("tests")
                    if not isinstance(tests, list) or len(tests) != 1:
                        observations[title].append("incomplete")
                        continue
                    test = tests[0]
                    if not isinstance(test, dict):
                        observations[title].append("incomplete")
                        continue
                    results = test.get("results")
                    passed = (
                        test.get("status") == "expected"
                        and isinstance(results, list)
                        and len(results) == 1
                        and isinstance(results[0], dict)
                        and results[0].get("status") == "passed"
                    )
                    outcome = "passed" if passed else "not_passed"
                    # Only expose a numeric line in the known *public test file*.
                    # Playwright error messages, locations and stacks are never emitted.
                    if not passed and isinstance(results, list) and results:
                        first = results[0]
                        errors = first.get("errors") if isinstance(first, dict) else None
                        if isinstance(errors, list):
                            for error in errors:
                                if not isinstance(error, dict):
                                    continue
                                location = error.get("location")
                                if not isinstance(location, dict):
                                    continue
                                raw_file = location.get("file")
                                line = location.get("line")
                                label = next(
                                    (code for name, code in labels if name == title),
                                    None,
                                )
                                if (
                                    isinstance(raw_file, str)
                                    and isinstance(label, str)
                                    and raw_file.replace("\\", "/").rsplit("/", 1)[-1]
                                    == SAFE_PROVIDER_TEST_FILES[label]
                                    and type(line) is int
                                    and 1 <= line <= 800
                                ):
                                    outcome += f"@line{line}"
                                    break
                    observations[title].append(outcome)
            visit(suite.get("suites"))

    visit(report.get("suites"))
    parts = []
    for title, label in labels:
        seen = observations[title]
        outcome = seen[0] if len(seen) == 1 else ("not_run" if not seen else "incomplete")
        parts.append(f"{label}={outcome}")
    return "M1 provider outcomes (private diagnostics withheld): " + ", ".join(parts)


def run_provider(env: Mapping[str, str], *, head: str) -> None:
    preflight(env, head)
    p0_enabled = env.get("E2E_P0_ACCEPTANCE") == "1"
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
        # The report itself can contain secrets. Print only fixed test IDs and
        # enumerated statuses parsed from its in-memory JSON, never raw content.
        print(sanitized_provider_outcomes(result.stdout, p0_enabled=p0_enabled), file=sys.stderr)
        raise AcceptanceBlocked("Real-provider suite failed; private diagnostics withheld")
    try:
        report = json.loads(result.stdout)
    except (UnicodeError, ValueError) as exc:
        raise AcceptanceBlocked("No parseable real-provider test execution report") from exc
    count = validated_report(report, p0_enabled=p0_enabled)
    if verified_head() != head:
        raise AcceptanceBlocked("Repository SHA changed during real-provider verification")
    print(f"PASS: {count} real-provider Playwright tests at SHA {head}.")
    print("Evidence class: authorized nonproduction Supabase Auth + isolated FastAPI/PostgreSQL/RLS.")
    if p0_enabled:
        print("P0 extension: manual citation, evidence graph, saved scenarios, follow-up, reload and tenant denial.")
        print("NOT VERIFIED: live third-party source retrieval or external MCP client acceptance.")
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
    require_expected_head(env, "a" * 40)
    for wrong in ("", "bad-sha", "b" * 40):
        try:
            require_expected_head({**env, "M1_ACCEPTANCE_HEAD_SHA": wrong}, "a" * 40)
        except AcceptanceBlocked:
            pass
        else:
            raise AssertionError("Missing, malformed or mismatched checkpoint SHA was accepted")
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
    p0_report = test_report(sorted(required_titles(True)))
    assert validated_report(p0_report, p0_enabled=True) == len(REQUIRED_TEST_TITLES)
    for report, mode in ((valid, True), (p0_report, False)):
        try:
            validated_report(report, p0_enabled=mode)
        except AcceptanceBlocked:
            pass
        else:
            raise AssertionError("Mismatched acceptance mode was accepted")
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
        ignored_declaration = checkout / "next-env.d.ts"
        (checkout / ".gitignore").write_text("next-env.d.ts" + chr(10), encoding="utf-8")
        fixture.write_text("original test\\n", encoding="utf-8")

        def git(*args: str) -> None:
            subprocess.run(
                ["git", *args], cwd=checkout, check=True,
                capture_output=True, timeout=10,
            )

        git("init", "--quiet")
        git("add", "provider.spec.ts", ".gitignore")
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

        # The Next-generated, type-only stub may be rewritten without dirtying
        # executable source, while an untracked test file must still fail closed.
        ignored_declaration.write_text("generated Next types", encoding="utf-8")
        require_clean_checkout(checkout)

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
    # The failure summary may publish only predefined identifiers/status labels,
    # even if Playwright's raw JSON contains private provider response material.
    assert "report unavailable" in sanitized_provider_outcomes(b"not JSON: hidden-password")
    fail_report = test_report(sorted(REQUIRED_TEST_TITLES))
    failed_spec = next(
        spec for spec in fail_report["suites"][0]["specs"]
        if spec["title"] == SAFE_PROVIDER_LABELS[0][0]
    )
    failed_spec["tests"][0]["results"][0]["status"] = "failed"
    failed_spec["tests"][0]["results"][0]["errors"] = [{
        "message": "PRIVATE_PASSWORD_DO_NOT_PRINT",
        "stack": "SECRET_SESSION_TOKEN_DO_NOT_PRINT",
        "location": {
            "file": "/private/SENSITIVE_ROOT/auth-provider.smoke.spec.ts",
            "line": 42,
        },
    }]
    summary = sanitized_provider_outcomes(json.dumps(fail_report).encode("utf-8"))
    assert "AUTH_SESSION=not_passed@line42" in summary
    assert "WORKSPACE_UI=passed" in summary
    assert "SENSITIVE_ROOT" not in summary
    assert "TENANT_API=passed" in summary
    assert "PRIVATE_PASSWORD" not in summary and "SECRET_SESSION_TOKEN" not in summary
    for title, label in SAFE_PROVIDER_LABELS:
        assert title not in summary and label in summary

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
        elif mode == "verify-checkout":
            head = verified_head()
            require_expected_head(os.environ, head)
            require_clean_checkout()
            print(f"PASS: clean tracked and ordinarily untracked checkout at SHA {head}.")
        else:
            print(
                "Usage: python ci/m1_acceptance.py self-test|preflight|run|verify-checkout",
                file=sys.stderr,
            )
            return 2
        return 0
    except AcceptanceBlocked as exc:
        print("M1 ACCEPTANCE BLOCKED: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
