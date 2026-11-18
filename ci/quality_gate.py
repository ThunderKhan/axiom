"""Axiom CI gates: always audit repo, fail closed once application code appears."""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys
import tomllib
import unittest
from urllib.parse import unquote, urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED = ("AGENTS.md", "ENGINEERING.md", "docs/01-INDEX.md")
CHECKS = ("install", "lint", "typecheck", "test", "build", "security")
CODE_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs"}
MANIFESTS = {"package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "go.mod"}
IGNORED = {".git", "node_modules", ".next", ".venv", "dist", "build", "__pycache__"}
SECRETS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\bsk_live_[A-Za-z0-9]{16,}\b"),
)


class QualityError(Exception):
    """Required verification failed."""


def fail(message: str) -> None:
    raise QualityError(message)


def tracked(root: pathlib.Path) -> list[pathlib.Path]:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=root,
                            capture_output=True, check=True)
    return [root / b.decode("utf-8") for b in result.stdout.split(b"\0") if b]


def check_document_links(root: pathlib.Path, files: list[pathlib.Path]) -> int:
    for name in REQUIRED:
        if not (root / name).is_file():
            fail(f"Missing governing document: {name}")
    count = 0
    for file in files:
        if file.suffix.lower() != ".md" or not file.is_file():
            continue
        body = file.read_text(encoding="utf-8")
        if body.count(chr(96) * 3) % 2:
            fail(f"Unbalanced Markdown code fences: {file.relative_to(root)}")
        for match in re.finditer(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", body):
            url = match.group(1).strip().split()[0].strip("<>")
            if url.startswith(("http:", "https:", "mailto:", "#", "data:")):
                continue
            path = unquote(urlsplit(url).path)
            if not path or path.startswith("/"):
                continue
            target = (file.parent / path).resolve()
            if not target.is_relative_to(root.resolve()) or not target.exists():
                fail(f"Broken Markdown link in {file.relative_to(root)}: {url}")
        count += 1
    if count == 0:
        fail("No Markdown files discovered")
    return count


def check_obvious_secrets(root: pathlib.Path, files: list[pathlib.Path]) -> None:
    for file in files:
        if not file.is_file() or file.stat().st_size > 2_000_000:
            continue
        try:
            data = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if any(pattern.search(data) for pattern in SECRETS):
            fail(f"Potential committed secret in {file.relative_to(root)}")


def check_workflow(root: pathlib.Path) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise QualityError("Install pinned PyYAML to validate workflow") from exc
    path = root / ".github/workflows/quality.yml"
    if not path.is_file():
        fail("Missing .github/workflows/quality.yml")
    content = path.read_text(encoding="utf-8")
    # BaseLoader preserves GitHub's 'on' key as a string (not YAML 1.1 bool).
    workflow = yaml.load(content, Loader=yaml.BaseLoader)
    if not isinstance(workflow, dict):
        fail("Workflow YAML is not a mapping")
    if workflow.get("permissions") != {"contents": "read"}:
        fail("CI token permissions must be contents: read only")
    events = workflow.get("on")
    if not isinstance(events, dict) or "pull_request" not in events or "push" not in events:
        fail("Quality workflow must run on PRs and pushes")
    if "pull_request_target" in events:
        fail("Untrusted PR code must not run in pull_request_target context")
    if set(events["push"].get("branches", [])) != {"main"}:
        fail("Quality workflow must cover pushes to main")
    if not {"repository", "application"}.issubset(workflow.get("jobs", {})):
        fail("Required repository and application jobs are missing")
    if "secrets:" in content:
        fail("No production secrets in ordinary quality PR workflow")


def sources(root: pathlib.Path, files: list[pathlib.Path]) -> list[pathlib.Path]:
    found = []
    for file in files:
        parts = file.relative_to(root).parts
        if not parts or any(p in IGNORED for p in parts):
            continue
        if parts[0] in {"ci", ".github"} or parts[:2] == ("tests", "ci"):
            continue
        if file.suffix.lower() in CODE_EXTS or file.name in MANIFESTS:
            found.append(file)
    return found


def validate_command(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not value or any(
        not isinstance(arg, str) or not arg.strip() for arg in value
    ):
        fail(f"{label}: expected nonempty command argument array")
    cmd = list(value)
    if cmd[0] in {"echo", "true", "false", "exit", ":", "printf", "bash", "sh", "cmd", "powershell"}:
        fail(f"{label}: placeholder or shell wrapper is not a real quality command")
    if any("passWithNoTests" in arg or "pass-with-no-tests" in arg for arg in cmd):
        fail(f"{label}: no-tests bypass is forbidden")
    return cmd


def check_application_config(root: pathlib.Path, files: list[pathlib.Path]) -> list[tuple[str, pathlib.Path, dict]]:
    code = sources(root, files)
    config_file = root / "ci/quality.toml"
    if not code:
        if config_file.is_file():
            fail("Application quality config exists but no application source is tracked")
        return []
    if not config_file.is_file():
        fail("Application code exists, but ci/quality.toml is missing. Define actual build/lint/type/test/security commands.")
    with config_file.open("rb") as stream:
        config = tomllib.load(stream)
    packages = config.get("packages")
    if config.get("version") != 1 or not isinstance(packages, dict) or not packages:
        fail("ci/quality.toml requires version = 1 and nonempty [packages.<name>] sections")
    declared = []
    for name, spec in packages.items():
        if not isinstance(spec, dict):
            fail(f"Bad package entry: {name}")
        rel = spec.get("directory")
        if not isinstance(rel, str) or not rel or pathlib.Path(rel).is_absolute() or ".." in pathlib.Path(rel).parts:
            fail(f"Bad directory for package {name}")
        directory = (root / rel).resolve()
        if not directory.is_relative_to(root.resolve()) or not directory.is_dir():
            fail(f"Missing directory for package {name}: {rel}")
        for key in ("manifest", "lockfile"):
            value = spec.get(key)
            if (not isinstance(value, str) or not value or pathlib.Path(value).is_absolute()
                or ".." in pathlib.Path(value).parts or not (directory / value).is_file()):
                fail(f"Missing or invalid package {name} {key}: {value}")
        patterns = spec.get("test_files")
        if not isinstance(patterns, list) or not patterns or any(not isinstance(x, str) or not x for x in patterns):
            fail(f"Package {name} must declare actual test_files globs")
        if not any(file.is_file() for pattern in patterns for file in directory.glob(pattern)):
            fail(f"Package {name}: no tests match {patterns}")
        for key in CHECKS:
            validate_command(spec.get(key), f"{name}.{key}")
        declared.append((name, directory, spec))
    uncovered = [file for file in code if not any(file.is_relative_to(d) for _, d, _ in declared)]
    if uncovered:
        fail("Application code outside configured CI packages: " +
             ", ".join(str(file.relative_to(root)) for file in uncovered[:10]))
    return declared


def run_application(root: pathlib.Path, files: list[pathlib.Path]) -> None:
    packages = check_application_config(root, files)
    if not packages:
        notice = ("Documentation-only: no application code or executable app tests/build exist. "
                  "Application readiness NOT verified. Adding app code without quality configuration will fail.")
        print("::notice::" + notice)
        print(notice)
        return
    for name, directory, spec in packages:
        for key in CHECKS:
            cmd = validate_command(spec[key], f"{name}.{key}")
            print(f"Executing {name}/{key}: {cmd!r}", flush=True)
            subprocess.run(cmd, cwd=directory, check=True)


def run_ci_tests(root: pathlib.Path) -> None:
    directory = root / "tests/ci"
    if not directory.is_dir():
        fail("Required CI test suite tests/ci does not exist")
    suite = unittest.TestLoader().discover(str(directory), pattern="test_*.py", top_level_dir=str(directory))
    if suite.countTestCases() < 1:
        fail("CI test discovery returned zero tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        fail(f"CI helper tests failed: {len(result.failures)} failures; {len(result.errors)} errors")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("self-test", "repository", "application"))
    mode = parser.parse_args().mode
    try:
        if mode == "self-test":
            run_ci_tests(ROOT)
        elif mode == "repository":
            files = tracked(ROOT)
            count = check_document_links(ROOT, files)
            check_obvious_secrets(ROOT, files)
            check_workflow(ROOT)
            print(f"Verified {count} Markdown files, workflow policy, and obvious credential patterns")
        else:
            run_application(ROOT, tracked(ROOT))
        return 0
    except (QualityError, subprocess.CalledProcessError, OSError, ValueError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
