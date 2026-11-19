"""Mandatory local M0 integration smoke: real Next.js, Compose API, browser, and worker."""
from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"
COMPOSE = ROOT / "infra" / "compose.dev.yml"
WEB_PORT = 3200
WEB_ORIGIN = f"http://127.0.0.1:{WEB_PORT}"
API_ORIGIN = "http://127.0.0.1:8000"
READY_MARKER = 'name="axiom-api-base-url"'


def require_local_inputs() -> None:
    required = [
        WEB / "node_modules" / "@playwright" / "test",
        WEB / "package-lock.json",
        WEB / "scripts" / "m0-browser-smoke.mjs",
        ROOT / "services" / "api" / "uv.lock",
        COMPOSE,
    ]
    for path in required:
        if not path.exists():
            raise RuntimeError(f"Missing integration input: {path.relative_to(ROOT)}")


def command(*args: str, env: dict[str, str] | None = None, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    print("$", " ".join(args), flush=True)
    proc = subprocess.run(
        args, cwd=ROOT, env=env, text=True, capture_output=True, timeout=timeout, check=False
    )
    if proc.returncode:
        raise RuntimeError(
            f"Command returned {proc.returncode}: {' '.join(args)}\n{proc.stdout}\n{proc.stderr}"
        )
    return proc


def require_port_free(port: int) -> None:
    """Reject an active listener, not harmless TCP TIME_WAIT after Compose cleanup."""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            raise RuntimeError(f"Port {port} is occupied; stop the existing service")
    except ConnectionRefusedError:
        # The previous container can leave TCP TIME_WAIT sockets behind.
        # No service is listening; the real startup remains the final authority.
        return


def get_json(url: str, *, origin: str | None = None) -> tuple[int, dict[str, str], dict[str, object]]:
    request = Request(url, headers={"Origin": origin} if origin else {})
    with urlopen(request, timeout=3) as response:
        return response.status, dict(response.headers.items()), json.load(response)


def require_api_live(api_origin: str) -> None:
    status, _, body = get_json(api_origin + "/api/v1/health/live")
    if status != 200 or body != {"status": "alive", "service": "axiom-api"}:
        raise AssertionError("Real API liveness response did not match the contract")


def require_api_unavailable(api_origin: str) -> None:
    try:
        require_api_live(api_origin)
    except (URLError, ConnectionError, TimeoutError, OSError):
        return
    raise AssertionError("Unavailable or incorrect API location unexpectedly passed")


def require_browser_cors(api_origin: str, web_origin: str) -> None:
    url = api_origin + "/api/v1/health/live"
    request = Request(
        url,
        method="OPTIONS",
        headers={"Origin": web_origin, "Access-Control-Request-Method": "GET"},
    )
    with urlopen(request, timeout=3) as response:
        if response.status != 200 or response.headers.get("Access-Control-Allow-Origin") != web_origin:
            raise AssertionError("Configured development origin was not allowed by real HTTP preflight")
        if response.headers.get("Access-Control-Allow-Credentials"):
            raise AssertionError("Foundation must not permit credentialed cross-origin requests")

    denied = Request(
        url, method="OPTIONS",
        headers={"Origin": "https://unauthorized.example", "Access-Control-Request-Method": "GET"},
    )
    try:
        with urlopen(denied, timeout=3) as response:
            raise AssertionError(f"Unapproved origin preflight unexpectedly returned {response.status}")
    except HTTPError as error:
        if error.code != 400 or error.headers.get("Access-Control-Allow-Origin"):
            raise AssertionError("Unapproved origin received unsafe CORS response") from error

    status, headers, _ = get_json(url, origin="https://unauthorized.example")
    if status != 200 or any(key.lower() == "access-control-allow-origin" for key in headers):
        raise AssertionError("Unapproved origin obtained a CORS allowance from actual GET")


def wait_for_web(process: subprocess.Popen[str], logs: Path, *, timeout: float = 100) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Next.js exited {process.returncode}; see {logs}")
        try:
            with urlopen(WEB_ORIGIN, timeout=3) as response:
                body = response.read().decode("utf-8", errors="replace")
                if response.status != 200:
                    raise AssertionError(f"Next.js returned HTTP {response.status}")
                if READY_MARKER not in body or API_ORIGIN not in body:
                    raise AssertionError("Next.js did not render the configured public API origin")
                if "axiom-private-test-sentinel" in body:
                    raise AssertionError("Server-only sentinel leaked into rendered HTML")
                return
        except (URLError, TimeoutError, ConnectionError):
            time.sleep(0.4)
    raise TimeoutError(f"Native Next.js never became ready; see {logs}")


def require_invalid_worker_rejected(result: subprocess.CompletedProcess[str]) -> None:
    """Distinguish a settings-validation exit from a Docker/Compose failure."""
    expected = "Invalid AXIOM_ configuration; worker startup aborted."
    if (
        result.returncode != 2
        or expected not in result.stderr
        or "axiom_worker_ready" in result.stdout
        or "axiom_worker_ready" in result.stderr
    ):
        raise AssertionError(
            "Invalid worker settings were not rejected by the worker itself "
            f"(exit {result.returncode}); Compose failures are not validation evidence"
        )

def owned_web_group_exists(group_id: int) -> bool:
    """Probe only the group created by the smoke's start_new_session process."""
    try:
        os.killpg(group_id, 0)
    except ProcessLookupError:
        return False
    return True


def stop_web(process: subprocess.Popen[str]) -> None:
    if os.name == "nt":
        # taskkill /T targets the owned Windows process tree, not just npm.cmd.
        if process.poll() is None:
            command("taskkill", "/PID", str(process.pid), "/T", "/F", timeout=15)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Native Next.js process failed to stop") from exc
        return

    # start_new_session=True gave this npm process its own POSIX process group.
    # The leader may have exited even while its Next.js child remains alive.
    group_id = process.pid
    if owned_web_group_exists(group_id):
        try:
            os.killpg(group_id, signal.SIGTERM)
        except ProcessLookupError:
            pass

        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and owned_web_group_exists(group_id):
            time.sleep(0.1)

        if owned_web_group_exists(group_id):
            try:
                os.killpg(group_id, signal.SIGKILL)
            except ProcessLookupError:
                pass
            kill_deadline = time.monotonic() + 5
            while time.monotonic() < kill_deadline and owned_web_group_exists(group_id):
                time.sleep(0.1)
            if owned_web_group_exists(group_id):
                raise RuntimeError("Owned Next.js process group did not stop after SIGKILL")

    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("Next.js launcher did not exit after group cleanup") from exc


def main() -> int:
    require_local_inputs()
    require_port_free(WEB_PORT)
    require_port_free(8000)
    npm = shutil.which("npm")
    node = shutil.which("node")
    if not npm or not node:
        raise RuntimeError("Node.js 22 and npm must be on PATH")
    project = f"axiom-m0-{os.getpid()}"
    compose = ("docker", "compose", "-f", str(COMPOSE), "-p", project)
    runtime_env = dict(os.environ)
    runtime_env["AXIOM_CORS_ORIGINS"] = WEB_ORIGIN
    web_env = dict(os.environ)
    web_env["NEXT_PUBLIC_API_BASE_URL"] = API_ORIGIN
    web_env["AXIOM_DATABASE_URL"] = "postgresql://axiom-private-test-sentinel@127.0.0.1/db"
    web_env.pop("CI", None)

    failure: BaseException | None = None
    cleanup_problems: list[str] = []
    with tempfile.TemporaryDirectory(prefix="axiom-m0-") as tmp:
        log_path = Path(tmp) / "next.log"
        web_process: subprocess.Popen[str] | None = None
        try:
            command(*compose, "config", "--quiet", env=runtime_env)
            command(*compose, "up", "-d", "--build", "--wait", "api", env=runtime_env, timeout=420)
            require_api_live(API_ORIGIN)
            require_browser_cors(API_ORIGIN, WEB_ORIGIN)
            worker = command(
                *compose, "run", "--rm", "--no-deps",
                "-e", "AXIOM_WORKER_RUN_SECONDS=0.2", "worker",
                env=runtime_env, timeout=45,
            )
            if (
                "axiom_worker_ready mode=idle_only queue=not_implemented" not in worker.stdout
                or "axiom_worker_stopped" not in worker.stdout
            ):
                raise AssertionError("Independent worker did not report honest startup/shutdown")
            # A worker failing settings validation must never be counted as ready.
            invalid_worker = subprocess.run(
                [
                    *compose, "run", "--rm", "--no-deps",
                    "-e", "AXIOM_PORT=0", "worker",
                ],
                cwd=ROOT, env=runtime_env, capture_output=True, text=True,
                timeout=45, check=False,
            )
            require_invalid_worker_rejected(invalid_worker)
            config = json.loads(command(*compose, "config", "--format", "json", env=runtime_env).stdout)
            if config["services"]["worker"].get("ports"):
                raise AssertionError("Worker must not publish a network port")
            with log_path.open("w", encoding="utf-8") as log:
                options = (
                    {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                    if os.name == "nt" else {"start_new_session": True}
                )
                web_process = subprocess.Popen(
                    [npm, "run", "dev", "--", "--port", str(WEB_PORT)],
                    cwd=WEB, env=web_env, stdout=log, stderr=subprocess.STDOUT,
                    **options,
                )
                wait_for_web(web_process, log_path)
                command(
                    node, str(WEB / "scripts" / "m0-browser-smoke.mjs"),
                    WEB_ORIGIN, API_ORIGIN, timeout=60,
                )
            require_api_unavailable("http://127.0.0.1:1")
            # Stopping the real API must be observed as a hard failure, not a stale fixture.
            command(*compose, "stop", "api", env=runtime_env)
            require_api_unavailable(API_ORIGIN)
            command(*compose, "start", "api", env=runtime_env)
            deadline = time.monotonic() + 30
            while True:
                try:
                    require_api_live(API_ORIGIN)
                    break
                except (URLError, TimeoutError, ConnectionError):
                    if time.monotonic() > deadline:
                        raise RuntimeError("API failed to recover after container restart")
                    time.sleep(0.3)
        except BaseException as error:
            failure = error
            if log_path.exists():
                print("Next.js diagnostic tail:\n" + log_path.read_text(encoding="utf-8")[-2500:])
        finally:
            if web_process is not None:
                try:
                    stop_web(web_process)
                except BaseException as error:
                    cleanup_problems.append(f"Next.js cleanup: {error}")
            try:
                command(*compose, "down", "--remove-orphans", env=runtime_env, timeout=90)
            except BaseException as error:
                cleanup_problems.append(f"Compose cleanup: {error}")

    if cleanup_problems:
        raise RuntimeError("M0 integration cleanup failed:\n" + "\n".join(cleanup_problems)) from failure
    if failure is not None:
        raise failure
    print("PASS: M0 real Chromium + native web + container API/worker + CORS + negative outage + cleanup")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, AssertionError, RuntimeError, TimeoutError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL: M0 integrated smoke: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
