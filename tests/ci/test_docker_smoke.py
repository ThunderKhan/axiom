"""Fail-closed Docker input validation regression tests (Docker-free)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

# quality_gate.py is run as a script; unittest discovery does not add the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ci.docker_smoke import require_inputs  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
