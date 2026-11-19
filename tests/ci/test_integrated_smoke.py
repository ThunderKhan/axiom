"""M0 harness negative regressions (Docker-free: behavioral helper contracts)."""
from __future__ import annotations

import socket
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ci.integrated_smoke import (  # noqa: E402
    require_api_live,
    require_api_unavailable,
    require_local_inputs,
    require_port_free,
    wait_for_web,
)


class IntegrationSmokeContracts(unittest.TestCase):
    def test_missing_frontend_dependencies_fail_before_spawning(self) -> None:
        # A clean checkout without npm ci must not masquerade as installed.
        with patch("ci.integrated_smoke.WEB", Path("/nonexistent-axiom-web")):
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


if __name__ == "__main__":
    unittest.main()
