"""API process entrypoint. Use `python -m app.api`."""
from __future__ import annotations

import sys

import uvicorn
from pydantic import ValidationError

from app.settings import load_settings


def main() -> int:
    try:
        settings = load_settings()
    except ValidationError:
        # Pydantic's normal exception can contain secrets supplied as inputs.
        print("Invalid AXIOM_ configuration; startup aborted.", file=sys.stderr)
        return 2

    uvicorn.run(
        "app.main:app",
        host=settings.bind_host,
        port=settings.port,
        proxy_headers=False,
        access_log=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
