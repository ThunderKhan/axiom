"""Run both required Ruff quality checks, failing on either violation."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    for args in (("ruff", "check", "."), ("ruff", "format", "--diff", ".")):
        # Fixed, trusted executable/args; never a shell or user-controlled command.
        result = subprocess.run(args, check=False)  # noqa: S603
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
