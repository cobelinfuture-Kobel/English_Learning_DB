#!/usr/bin/env python3
"""Backward-compatible R01 entrypoint after SQLite lifecycle merged into builder.

The authoritative close-before-replace implementation now lives in the R01
builder itself. This module remains only so previously generated operator paths
or imports continue to delegate to the same authority without monkeypatching.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Preserves backward compatibility for the former Windows-safe R01 entrypoint while "
    "delegating to the authoritative builder-level SQLite lifecycle. It creates no curriculum, "
    "learner content, scoring, mastery, dashboard, audio, A2, Cloudflare route, external "
    "binding, monkeypatch authority, or parallel runtime."
)
MODULE = r01.MODULE


def copy_sqlite_closed(source: Path, target: Path) -> None:
    """Delegate to the authoritative builder-level SQLite copy operation."""
    r01._copy_sqlite(source, target)


def activate_windows_safe_runtime() -> None:
    """Compatibility no-op: the builder is already Windows-safe."""
    return None


def main(argv: Sequence[str] | None = None) -> int:
    return r01.main(list(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
