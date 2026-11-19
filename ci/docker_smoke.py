"""Required real Docker/Compose smoke gate for the Python API and worker."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "axiom-api:dev"
COMPOSE_FILE = ROOT / "infra" / "compose.dev.yml"
DOCKERFILE = ROOT / "services" / "api" / "Dockerfile"
BUILD_CONTEXT = ROOT / "services" / "api"


def require_inputs(root: Path = ROOT) -> None:
    for relative in (
        "services/api/Dockerfile",
        "services/api/.dockerignore",
        "services/api/pyproject.toml",
        "services/api/uv.lock",
        "services/api/app/api.py",
        "services/api/app/worker.py",
        "infra/compose.dev.yml",
    ):
        if not (root / relative).is_file():
            raise FileNotFoundError(f"Required container input missing: {relative}")


def execute(*command: str, timeout: int = 180, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(command), flush=True)
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if check and result.returncode:
        raise RuntimeError(
            f"Command failed (exit {result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result


def expected_failure(*command: str) -> None:
    result = execute(*command, check=False)
    if result.returncode == 0:
        raise AssertionError(f"Broken-input command incorrectly succeeded: {' '.join(command)}")


def verify_negative_build_and_compose_cases() -> None:
    with tempfile.TemporaryDirectory(prefix="axiom-negative-") as tmp:
        compose = Path(tmp) / "broken-compose.yml"
        compose.write_text("services: [invalid yaml", encoding="utf-8")
        expected_failure("docker", "compose", "-f", str(compose), "config", "--quiet")
        dockerfile = Path(tmp) / "broken.Dockerfile"
        dockerfile.write_text("FROM scratch\nCOPY nonexistent-axiom-build-input /tmp/\n", encoding="utf-8")
        expected_failure(
            "docker", "build", "--file", str(dockerfile), str(BUILD_CONTEXT)
        )


def wait_for_api() -> None:
    deadline = time.monotonic() + 45
    endpoints = (
        ("/api/v1/health/live", {"status": "alive", "service": "axiom-api"}),
        (
            "/api/v1/health/ready",
            {"status": "ready", "scope": "foundation_only", "dependencies": "none_configured"},
        ),
    )
    while time.monotonic() < deadline:
        try:
            for endpoint, expected in endpoints:
                with urlopen("http://127.0.0.1:8000" + endpoint, timeout=2) as response:
                    if response.status != 200 or json.load(response) != expected:
                        raise AssertionError(f"Unexpected API {endpoint} health response")
            return
        except (URLError, TimeoutError, ConnectionError):
            time.sleep(0.5)
    raise AssertionError("Containerized API did not become ready on 127.0.0.1:8000")


def main() -> int:
    require_inputs()
    project = f"axiom-ci-{os.getpid()}"
    compose = ("docker", "compose", "-f", str(COMPOSE_FILE), "-p", project)
    worker_name = f"axiom-worker-smoke-{os.getpid()}"

    execute("docker", "build", "--file", str(DOCKERFILE), "--tag", IMAGE, str(BUILD_CONTEXT), timeout=420)
    image_user = execute("docker", "image", "inspect", "--format", "{{.Config.User}}", IMAGE).stdout.strip()
    if image_user in ("", "root", "0", "0:0"):
        raise AssertionError(f"Docker image does not declare a non-root user: {image_user!r}")
    actual_uid = execute(
        "docker", "run", "--rm", IMAGE, "python", "-c", "import os; print(os.getuid())"
    ).stdout.strip()
    if actual_uid != "10001":
        raise AssertionError(f"Container actually runs as unexpected UID {actual_uid!r}")

    execute(*compose, "config", "--quiet")
    configuration = json.loads(execute(*compose, "config", "--format", "json").stdout)
    if configuration["services"]["worker"].get("ports"):
        raise AssertionError("Worker Compose service must have no published ports")
    api_ports = configuration["services"]["api"].get("ports") or []
    if len(api_ports) != 1 or api_ports[0].get("host_ip") != "127.0.0.1":
        raise AssertionError("API Compose ingress must be restricted to loopback")

    verify_negative_build_and_compose_cases()
    expected_failure("docker", "run", "--rm", "-e", "AXIOM_PORT=0", IMAGE, "python", "-m", "app.worker")
    expected_failure("docker", "run", "--rm", "-e", "AXIOM_PORT=0", IMAGE, "python", "-m", "app.api")

    try:
        execute(*compose, "up", "-d", "--no-build", "api", timeout=90)
        wait_for_api()
        worker = execute(
            *compose, "run", "--rm", "--no-deps", "-e", "AXIOM_WORKER_RUN_SECONDS=0.2", "worker",
            timeout=35,
        )
        if "axiom_worker_ready mode=idle_only" not in worker.stdout or "axiom_worker_stopped" not in worker.stdout:
            raise AssertionError(f"Worker did not execute and exit honestly:\n{worker.stdout}")

        execute(
            "docker", "run", "-d", "--name", worker_name,
            "-e", "AXIOM_WORKER_RUN_SECONDS=30", IMAGE, "python", "-m", "app.worker",
        )
        time.sleep(1)
        execute("docker", "stop", "--time", "5", worker_name, timeout=15)
        stopped = execute("docker", "logs", worker_name).stdout
        if "axiom_worker_ready" not in stopped or "axiom_worker_stopped" not in stopped:
            raise AssertionError("Worker did not stop gracefully on SIGTERM")
        print("PASS: Docker API/worker startup, health, non-root, termination, isolation and negative cases")
        return 0
    finally:
        execute(*compose, "down", "--remove-orphans", timeout=60, check=False)
        execute("docker", "rm", "-f", worker_name, check=False)


if __name__ == "__main__":
    raise SystemExit(main())
