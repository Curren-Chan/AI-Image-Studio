"""Run unittest discovery and surface failures as GitHub Actions annotations."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _workflow_escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def main() -> int:
    suite = unittest.defaultTestLoader.discover("tests")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        return 0

    for test, traceback in [*result.errors, *result.failures]:
        detail = " ".join(traceback.strip().splitlines()[-6:])
        print(
            f"::error title=CI test failed: {test.id()}::{_workflow_escape(detail)}",
            flush=True,
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
