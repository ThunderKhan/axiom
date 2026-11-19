"""Independent bounded idle worker; no queue, leases or research jobs at WP-01."""

from __future__ import annotations

from collections.abc import Callable

import signal
import sys
from threading import Event, current_thread, main_thread
from time import monotonic
from types import FrameType

from pydantic import ValidationError

from app.settings import RuntimeSettings, load_settings


def run_idle_worker(settings: RuntimeSettings, stop: Event | None = None) -> int:
    stopped = stop if stop is not None else Event()
    previous: dict[signal.Signals, Callable[[int, FrameType | None], object] | int | None] = {}

    def request_stop(_number: int, _frame: FrameType | None) -> None:
        stopped.set()

    if current_thread() is main_thread():
        for sig in (signal.SIGINT, signal.SIGTERM):
            previous[sig] = signal.signal(sig, request_stop)

    try:
        print("axiom_worker_ready mode=idle_only queue=not_implemented", flush=True)
        deadline = monotonic() + settings.worker_run_seconds
        while not stopped.is_set():
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            stopped.wait(min(settings.worker_idle_seconds, remaining))
        print("axiom_worker_stopped", flush=True)
        return 0
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def main() -> int:
    try:
        settings = load_settings()
    except ValidationError:
        print("Invalid AXIOM_ configuration; worker startup aborted.", file=sys.stderr)
        return 2
    return run_idle_worker(settings)


if __name__ == "__main__":
    raise SystemExit(main())
