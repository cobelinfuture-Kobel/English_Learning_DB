#!/usr/bin/env python3
"""Rebuild A1FS beside the active root, validate it, then atomically activate it."""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Must be set before importing any A1FS release/runtime module. Child localhost
# acceptance processes inherit this setting as well.
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from ulga.builders import (  # noqa: E402
    build_a1fs_ops_v1_upg02_side_by_side_rebuild_atomic_activation as runner,
)


if __name__ == "__main__":
    raise SystemExit(runner.main(["--code-root", str(REPOSITORY_ROOT), *sys.argv[1:]]))
