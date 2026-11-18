"""Axiom CI gates: always audit repo, fail closed once application code appears."""
from __future__ import annotations

import argparse
import json
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
CODE_EXTS = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts", ".go", ".rs"}
MANIFESTS = {"package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "go.mod"}
IGNORED = {".git", "node_modules", ".next", ".venv", "dist", "build", "__pycache__"}
# Only known, reproducible manifest/lockfile roles. Do not accept arbitrary files.
LOCKFILE_ROLES = {
    "package.json": {"package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml",
                     "yarn.lock", "bun.lock", "bun.lockb"},
    "pyproject.toml": {"uv.lock", "poetry.lock", "pdm.lock", "requirements.lock"},
    "requirements.txt": {"requirements.lock"},
    "Cargo.toml": {"Cargo.lock"},
    "go.mod": {"go.sum"},
}

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


def check_fence_boundaries(body: str, file: pathlib.Path, root: pathlib.Path) -> None:
    """Recognize CommonMark fenced code open/close boundaries, not raw backtick counts."""
    opened: tuple[str, int] | None = None
    for line in body.splitlines():
        match = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if not match:
            continue
        fence, info = match.groups()
        if opened is None:
            if fence[0] == "`" and "`" in info:
                continue  # Not a valid opening fence per CommonMark.
            opened = (fence[0], len(fence))
        elif fence[0] == opened[0] and len(fence) >= opened[1] and not info.strip():
            opened = None
    if opened is not None:
        fail(f"Unbalanced Markdown code fences: {file.relative_to(root)}")


def check_document_links(root: pathlib.Path, files: list[pathlib.Path]) -> int:
    # Parse actual CommonMark links, not regular-expression lookalikes in examples.
    try:
        from markdown_it import MarkdownIt
    except ImportError as exc:
        raise QualityError("Install pinned markdown-it-py for Markdown validation") from exc
    parser = MarkdownIt("commonmark")
    for name in REQUIRED:
        if not (root / name).is_file():
            fail(f"Missing governing document: {name}")
    count = 0
    for file in files:
        if file.suffix.lower() != ".md" or not file.is_file():
            continue
        body = file.read_text(encoding="utf-8")
        check_fence_boundaries(body, file, root)
        for token in parser.parse(body):
            if token.type != "inline":
                continue
            for child in token.children or []:
                if child.type != "link_open":
                    continue
                url = (child.attrGet("href") or "").strip()
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

    # SafeLoader, with strict duplicate-key rejection and literal string keys.
    # GitHub Actions 'on' would otherwise be coerced to boolean by YAML 1.1.
    class StrictWorkflowLoader(yaml.SafeLoader):
        def construct_mapping(self, node, deep=False):
            if not isinstance(node, yaml.MappingNode):
                raise QualityError("Workflow contains a non-mapping YAML node")
            mapping = {}
            for key_node, value_node in node.value:
                key = (self.construct_scalar(key_node) if isinstance(key_node, yaml.ScalarNode)
                       else self.construct_object(key_node, deep=deep))
                if key in mapping:
                    raise QualityError(f"Duplicate workflow YAML key: {key}")
                mapping[key] = self.construct_object(value_node, deep=deep)
            return mapping

    path = root / ".github/workflows/quality.yml"
    if not path.is_file():
        fail("Missing .github/workflows/quality.yml")
    content = path.read_text(encoding="utf-8")
    try:
        workflow = yaml.load(content, Loader=StrictWorkflowLoader)
    except yaml.YAMLError as exc:
        raise QualityError(f"Invalid workflow YAML: {exc}") from exc
    if not isinstance(workflow, dict):
        fail("Workflow YAML is not a mapping")
    if workflow.get("permissions") != {"contents": "read"}:
        fail("CI token permissions must be contents: read only")
    events = workflow.get("on")
    if not isinstance(events, dict) or not {"pull_request", "push", "workflow_dispatch"}.issubset(events):
        fail("Quality workflow must run on every PR, push to main, and manual dispatch")
    if "pull_request_target" in events:
        fail("Untrusted PR code must not run in pull_request_target context")
    # Empty event mappings are legal; branch/path filters can silently omit
    # required checks, so we disallow filters rather than guessing coverage.
    pr_event = events["pull_request"]
    if pr_event not in (None, {}):
        fail("pull_request must not filter branches, paths, or event types")
    push_event = events["push"]
    if not isinstance(push_event, dict) or push_event != {"branches": ["main"]}:
        fail("push must cover every change to main without path or tag filters")
    if events["workflow_dispatch"] not in (None, {}):
        fail("Manual dispatch must not contain unexpected filters")
    jobs = workflow.get("jobs")
    if not isinstance(jobs, dict) or not {"repository", "application"}.issubset(jobs):
        fail("Required repository and application jobs are missing")
    for name in ("repository", "application"):
        job = jobs[name]
        if not isinstance(job, dict):
            fail(f"Required job {name} must be a mapping")
        if "if" in job:
            fail(f"Required job {name} must not have a conditional that can skip it")
        if "permissions" in job and job["permissions"] != {"contents": "read"}:
            fail(f"Required job {name} must retain read-only contents access")
        if job.get("continue-on-error") not in (None, False):
            fail(f"Required job {name} cannot ignore failures")
        steps = job.get("steps")
        if not isinstance(steps, list) or not steps:
            fail(f"Required job {name} has no executable steps")
        if not any(isinstance(step, dict) and str(step.get("uses", "")).startswith("actions/checkout@")
                   for step in steps):
            fail(f"Required job {name} needs checkout access")
        for step in steps:
            if not isinstance(step, dict) or "if" in step or step.get("continue-on-error") not in (None, False):
                fail(f"Required job {name} may not conditionally skip or ignore errors in steps")

    def contains_secret_context(value: object) -> bool:
        if isinstance(value, dict):
            return any(str(key).lower() == "secrets" or contains_secret_context(val)
                       for key, val in value.items())
        if isinstance(value, list):
            return any(contains_secret_context(item) for item in value)
        return isinstance(value, str) and bool(
            re.search(r"\$\{\{[^}]*\bsecrets\s*(?:\.|\[)", value, re.IGNORECASE)
        )

    if contains_secret_context(workflow):
        fail("Production secret references are forbidden in ordinary quality PR workflows")


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
    executable = pathlib.PurePosixPath(cmd[0].replace("\\", "/")).name.lower()
    if executable in {"echo", "true", "false", "exit", ":", "printf", "bash", "sh", "cmd", "powershell"}:
        fail(f"{label}: placeholder or shell wrapper is not a real quality command")
    if executable in {"python", "python3", "node"} and any(
        arg in {"-c", "-e", "--eval"} for arg in cmd[1:2]
    ):
        fail(f"{label}: arbitrary inline command is not acceptable quality evidence")
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
        artifacts = {}
        for key in ("manifest", "lockfile"):
            value = spec.get(key)
            if (not isinstance(value, str) or not value or pathlib.Path(value).is_absolute()
                or ".." in pathlib.Path(value).parts):
                fail(f"Missing or invalid package {name} {key}: {value}")
            artifact = (directory / value).resolve()
            if not artifact.is_relative_to(directory) or not artifact.is_file():
                fail(f"Missing or invalid package {name} {key}: {value}")
            artifacts[key] = artifact
        if artifacts["manifest"] == artifacts["lockfile"]:
            fail(f"Package {name}: manifest and lockfile must be distinct files")
        manifest = artifacts["manifest"].name
        if manifest not in LOCKFILE_ROLES:
            fail(f"Package {name}: unsupported manifest type {manifest}")
        if artifacts["lockfile"].name not in LOCKFILE_ROLES[manifest]:
            fail(f"Package {name}: invalid {manifest} lockfile role: {artifacts['lockfile'].name}")
        patterns = spec.get("test_files")
        if not isinstance(patterns, list) or not patterns or any(
            not isinstance(pattern, str) or not pattern or pathlib.Path(pattern).is_absolute()
            or ".." in pathlib.Path(pattern).parts for pattern in patterns
        ):
            fail(f"Package {name} must declare actual test_files globs")
        matches = [file.resolve() for pattern in patterns for file in directory.glob(pattern)
                   if file.is_file() and file.resolve().is_relative_to(directory)]
        if not matches:
            fail(f"Package {name}: no tests match {patterns}")
        for file in matches:
            basename = file.name
            if manifest == "go.mod":
                valid = basename.endswith("_test.go")
            elif manifest == "Cargo.toml":
                valid = file.suffix == ".rs" and (
                    "tests" in file.relative_to(directory).parts or basename.endswith("_test.rs")
                )
            elif manifest in {"pyproject.toml", "requirements.txt"}:
                valid = file.suffix == ".py" and (
                    basename.startswith("test_") or basename.endswith("_test.py")
                )
            else:
                valid = bool(re.search(r"\.(?:test|spec)\.(?:[cm]?[jt]sx?)$", basename))
            if not valid:
                fail(f"Package {name}: not an ecosystem test file: {file.relative_to(directory)}")
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
        go_package = spec["manifest"] == "go.mod"
        for key in CHECKS:
            cmd = validate_command(spec[key], f"{name}.{key}")
            print(f"Executing {name}/{key}: {cmd!r}", flush=True)
            if go_package and key == "test":
                if (pathlib.PurePosixPath(cmd[0].replace("\\", "/")).name != "go"
                        or "test" not in cmd[1:] or "-json" not in cmd[1:]):
                    fail(f"Package {name}: go tests must use go test -json to prove tests ran")
                result = subprocess.run(cmd, cwd=directory, check=True,
                                        capture_output=True, text=True)
                print(result.stdout, end="", flush=True)
                print(result.stderr, end="", file=sys.stderr, flush=True)
                test_events = []
                for line in result.stdout.splitlines():
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if (isinstance(event, dict) and event.get("Test")
                            and event.get("Action") == "run"):
                        test_events.append(event["Test"])
                if not test_events:
                    fail(f"Package {name}: go test reported zero executed tests")
            else:
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
