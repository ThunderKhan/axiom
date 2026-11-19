"""Run both required Ruff quality checks, failing on either violation."""
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    for args in (("ruff", "check", "."), ("ruff", "format", "--check", ".")):
        result = subprocess.run(args, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
