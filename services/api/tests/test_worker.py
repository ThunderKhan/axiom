from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path
from threading import Event

import pytest

from app.settings import RuntimeSettings
from app.worker import run_idle_worker

ROOT = Path(__file__).resolve().parents[1]


def test_worker_has_bounded_idle_lifecycle(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_idle_worker(RuntimeSettings(worker_run_seconds=0.1)) == 0
    captured = capsys.readouterr()
    assert "mode=idle_only queue=not_implemented" in captured.out
    assert "axiom_worker_stopped" in captured.out


def test_worker_stops_when_event_signaled() -> None:
    stop = Event()
    stop.set()
    assert run_idle_worker(RuntimeSettings(worker_run_seconds=30), stop) == 0


def test_worker_runs_as_separate_python_process() -> None:
    env = {**os.environ, "AXIOM_WORKER_RUN_SECONDS": "0.1"}
    result = subprocess.run(
        [sys.executable, "-m", "app.worker"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "axiom_worker_ready" in result.stdout
    assert "axiom_worker_stopped" in result.stdout


def test_invalid_runtime_configuration_fails_without_leaking_secret() -> None:
    env = {
        **os.environ,
        "AXIOM_PORT": "invalid",
        "AXIOM_DATABASE_URL": "postgresql://owner:hiddenpassword@127.0.0.1/db",
    }
    for module in ("app.api", "app.worker"):
        result = subprocess.run(
            [sys.executable, "-m", module],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        assert result.returncode == 2
        assert "hiddenpassword" not in (result.stdout + result.stderr)


@pytest.mark.skipif(os.name == "nt", reason="POSIX signal delivery differs on Windows")
def test_worker_handles_sigterm_gracefully() -> None:
    env = {**os.environ, "AXIOM_WORKER_RUN_SECONDS": "30"}
    process = subprocess.Popen(
        [sys.executable, "-m", "app.worker"],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None
        assert "axiom_worker_ready" in process.stdout.readline()
        process.send_signal(signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=8)
        assert process.returncode == 0, stderr
        assert "axiom_worker_stopped" in stdout
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
