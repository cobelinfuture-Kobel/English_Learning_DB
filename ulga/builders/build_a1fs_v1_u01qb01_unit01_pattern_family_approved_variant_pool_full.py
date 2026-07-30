#!/usr/bin/env python3
"""Deprecated compatibility shim for the canonical Unit01 variant-pool builder.

All implementation and authority now live in
build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool.
This module exists only so historical imports fail safely without preserving a
second builder or a second question-bank authority.
"""
from __future__ import annotations

from typing import Any

from ulga.builders import (
    build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as _canonical,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Deprecated compatibility import shim only; all Unit01 candidate generation, validation admission, task identities, and runtime boundaries are delegated to the single canonical U01QB01 builder."
DEPRECATED_COMPATIBILITY_SHIM = True
CANONICAL_MODULE = _canonical.__name__


def __getattr__(name: str) -> Any:
    return getattr(_canonical, name)


def main(argv: list[str] | None = None) -> int:
    return _canonical.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
