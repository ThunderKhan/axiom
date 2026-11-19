"""M0 harness negative regressions (Docker-free: behavioral helper contracts)."""
from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ci.integrated_smoke import (  # noqa: E402
    require_api_live,
    require_api_unavailable,
    require_invalid_worker_rejected,
    require_local_inputs,
    require_port_free,
    stop_web,
    wait_for_web,
)


class IntegrationSmokeContracts(unittest.TestCase):
    def test_missing_frontend_dependencies_fail_before_spawning(self) -> None:
        # A clean checkout without npm ci must not masquerade as installed.
        with patch("ci.integrated_smoke.WEB", Path(__file__).resolve().parents[2] / "missing-axiom-web"):
            with self.assertRaisesRegex(RuntimeError, "Missing integration input"):
                require_local_inputs()

    def test_wrong_api_reply_is_not_considered_live(self) -> None:
        with patch(
            "ci.integrated_smoke.get_json",
            return_value=(200, {}, {"status": "not_real", "service": "axiom-api"}),
        ):
            with self.assertRaisesRegex(AssertionError, "liveness"):
                require_api_live("http://127.0.0.1:1")

    def test_unavailable_api_passes_negative_probe_only(self) -> None:
        with patch("ci.integrated_smoke.require_api_live", side_effect=URLError("refused")):
            require_api_unavailable("http://127.0.0.1:1")

    def test_available_api_fails_unavailable_assertion(self) -> None:
        with patch("ci.integrated_smoke.require_api_live", return_value=None):
            with self.assertRaisesRegex(AssertionError, "unexpectedly passed"):
                require_api_unavailable("http://127.0.0.1:8000")

    def test_web_port_collision_is_reported(self) -> None:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            port = listener.getsockname()[1]
            with self.assertRaisesRegex(RuntimeError, "occupied"):
                require_port_free(port)

    def test_dead_web_process_rejected_without_success(self) -> None:
        class DeadProcess:
            returncode = 7
            def poll(self) -> int:
                return 7
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "exited 7"):
                wait_for_web(DeadProcess(), Path(tmp) / "next.log", timeout=0.1)  # type: ignore[arg-type]

    def test_invalid_worker_requires_specific_validation_failure(self) -> None:
        expected = subprocess.CompletedProcess(
            ["docker", "compose", "run"], 2, "",
            "Invalid AXIOM_ configuration; worker startup aborted.",
        )
        require_invalid_worker_rejected(expected)
        for bad in (
            subprocess.CompletedProcess(["docker"], 1, "", "Docker daemon unavailable"),
            subprocess.CompletedProcess(["docker"], 125, "", "container creation failed"),
            subprocess.CompletedProcess(["docker"], 2, "", "some unrelated failure"),
            subprocess.CompletedProcess(
                ["docker"], 2, "axiom_worker_ready mode=idle_only",
                "Invalid AXIOM_ configuration; worker startup aborted.",
            ),
        ):
            with self.assertRaisesRegex(AssertionError, "not rejected by the worker"):
                require_invalid_worker_rejected(bad)

    @unittest.skipUnless(os.name == "posix", "POSIX process groups are unavailable on Windows")
    def test_cleanup_stops_owned_child_when_launcher_exits_before_listening(self) -> None:
        # npm can exit while Next.js remains alive inside the new POSIX session.
        with tempfile.TemporaryDirectory(prefix="axiom-owned-web-test-") as tmp:
            started = Path(tmp) / "child-started"
            listening = Path(tmp) / "child-listening"
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]

            child_script = (
                "from pathlib import Path\n"
                "import socket, sys, time\n"
                "Path(sys.argv[2]).write_text('started', encoding='utf-8')\n"
                "time.sleep(0.8)\n"
                "with socket.socket() as server:\n"
                "    server.bind(('127.0.0.1', int(sys.argv[1])))\n"
                "    server.listen(1)\n"
                "    Path(sys.argv[3]).write_text('listening', encoding='utf-8')\n"
                "    time.sleep(5)\n"
            )
            parent_script = (
                "import subprocess, sys\n"
                "subprocess.Popen([sys.executable, '-c', sys.argv[1], *sys.argv[2:]], "
                "stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
            )
            parent = subprocess.Popen(
                [
                    sys.executable, "-c", parent_script, child_script,
                    str(port), str(started), str(listening),
                ],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                parent.wait(timeout=5)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline and not started.exists():
                    time.sleep(0.05)
                self.assertTrue(started.exists(), "Child did not begin before cleanup")
                self.assertFalse(listening.exists(), "Child unexpectedly began listening already")
                stop_web(parent)
                # The child would have begun listening without process-group cleanup.
                time.sleep(1)
                self.assertFalse(listening.exists(), "Orphaned child opened its listener")
                require_port_free(port)
            finally:
                # Clean up even when a regression test fails.
                try:
                    os.killpg(parent.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


if __name__ == "__main__":
    unittest.main()
