"""Fail-closed Docker input validation regression tests (Docker-free)."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

# quality_gate.py is run as a script; unittest discovery does not add the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ci.docker_smoke import cleanup_runtime, require_inputs, wait_for_worker_ready  # noqa: E402


class TestDockerContract(unittest.TestCase):
    def test_missing_dockerfile_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(FileNotFoundError, "Dockerfile"):
                require_inputs(Path(directory))

    def test_missing_compose_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename in (
                "services/api/Dockerfile",
                "services/api/.dockerignore",
                "services/api/pyproject.toml",
                "services/api/uv.lock",
                "services/api/app/api.py",
                "services/api/app/worker.py",
            ):
                target = root / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.touch()
            with self.assertRaisesRegex(FileNotFoundError, "compose.dev.yml"):
                require_inputs(root)

    def test_worker_stop_waits_for_readiness_marker(self) -> None:
        pending = subprocess.CompletedProcess(["docker", "logs"], 0, "", "")
        ready = subprocess.CompletedProcess(
            ["docker", "logs"], 0,
            "axiom_worker_ready mode=idle_only queue=not_implemented", "",
        )
        running = subprocess.CompletedProcess(["docker", "inspect"], 0, "true\n", "")
        with (
            patch("ci.docker_smoke.execute", side_effect=[pending, ready, running]) as run,
            patch("ci.docker_smoke.time.sleep") as sleep,
        ):
            wait_for_worker_ready("worker-123")
        self.assertEqual(run.call_count, 3)
        sleep.assert_called_once_with(0.2)
        self.assertEqual(run.call_args.args[:3], ("docker", "inspect", "--format"))

    def test_worker_never_ready_fails_closed(self) -> None:
        empty = subprocess.CompletedProcess(["docker", "logs"], 0, "", "")
        with (
            patch("ci.docker_smoke.execute", return_value=empty),
            patch("ci.docker_smoke.time.monotonic", side_effect=[1.0, 1.1]),
        ):
            with self.assertRaisesRegex(AssertionError, "never emitted readiness"):
                wait_for_worker_ready("worker-123", timeout=0.1)

    def test_cleanup_attempts_both_and_reports_compose_failure(self) -> None:
        fail = subprocess.CompletedProcess(
            ["docker", "compose"], 1, "", "daemon unavailable"
        )
        missing = subprocess.CompletedProcess(
            ["docker", "rm"], 1, "",
            "Error response from daemon: No such container: worker-123",
        )
        with patch("ci.docker_smoke.execute", side_effect=[fail, missing]) as run:
            with self.assertRaisesRegex(RuntimeError, "daemon unavailable"):
                cleanup_runtime(("docker", "compose", "-p", "fixture"), "worker-123")
        self.assertEqual(run.call_count, 2)

    def test_cleanup_ignores_only_confirmed_worker_absence(self) -> None:
        ok = subprocess.CompletedProcess(["docker", "compose"], 0, "", "")
        absent = subprocess.CompletedProcess(
            ["docker", "rm"], 1, "",
            "Error response from daemon: No such container: worker-123",
        )
        with patch("ci.docker_smoke.execute", side_effect=[ok, absent]) as run:
            cleanup_runtime(("docker", "compose", "-p", "fixture"), "worker-123")
        self.assertEqual(run.call_count, 2)

    def test_cleanup_fails_for_unrelated_docker_rm_errors(self) -> None:
        ok = subprocess.CompletedProcess(["docker", "compose"], 0, "", "")
        permission = subprocess.CompletedProcess(["docker", "rm"], 1, "", "permission denied")
        with patch("ci.docker_smoke.execute", side_effect=[ok, permission]) as run:
            with self.assertRaisesRegex(RuntimeError, "permission denied"):
                cleanup_runtime(("docker", "compose", "-p", "fixture"), "worker-123")
        self.assertEqual(run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
