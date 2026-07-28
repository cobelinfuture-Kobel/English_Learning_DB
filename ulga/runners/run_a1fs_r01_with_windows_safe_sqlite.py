#!/usr/bin/env python3
"""Run R01 with explicit SQLite connection closure before atomic replacement.

Python's sqlite3 connection context manager commits or rolls back but does not
close the connection. Windows therefore keeps the temporary SQLite file locked
when R01 immediately calls os.replace. This governed runner installs a corrected
copy helper for initial materialization, shared-state backup, update, and rollback
operations, and makes itself the packaged product entrypoint.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from typing import Sequence

from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Closes existing R01 SQLite backup connections before Windows atomic file replacement "
    "and delegates to the accepted R01 product-root runtime. It creates no curriculum, learner "
    "content, scoring, mastery, dashboard, audio, A2, Cloudflare route, external binding, or "
    "parallel authority."
)
MODULE = "ulga.runners.run_a1fs_r01_with_windows_safe_sqlite"


def copy_sqlite_closed(source: Path, target: Path) -> None:
    """Copy one live SQLite database and close both handles before os.replace."""
    source, target = Path(source), Path(target)
    if not source.is_file():
        raise r01.ProductRootError(f"sqlite_source_missing:{source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.unlink(missing_ok=True)
    try:
        with closing(sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True)) as src:
            with closing(sqlite3.connect(temporary)) as dst:
                src.backup(dst)
                dst.commit()
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def activate_windows_safe_runtime() -> None:
    """Install the corrected helper and package this module as the V1 entrypoint."""
    r01._copy_sqlite = copy_sqlite_closed
    r01.MODULE = MODULE


def main(argv: Sequence[str] | None = None) -> int:
    activate_windows_safe_runtime()
    return r01.main(list(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
