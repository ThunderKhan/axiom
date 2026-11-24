"""Run both required Ruff quality checks, failing on either violation."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    for args in (("ruff", "check", "."), ("ruff", "format", "--check", ".")):
        # Fixed, trusted executable/args; never a shell or user-controlled command.
        result = subprocess.run(args, check=False)  # noqa: S603
        if result.returncode != 0:
            if args[1] == "format":
                # Show exact formatter suggestions without changing tracked files.
                subprocess.run(("ruff", "format", "--diff", "."), check=False)  # noqa: S603
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
