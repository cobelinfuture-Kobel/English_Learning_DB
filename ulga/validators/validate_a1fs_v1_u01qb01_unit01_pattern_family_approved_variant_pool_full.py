#!/usr/bin/env python3
"""Deprecated compatibility shim for the canonical Unit01 variant-pool validator."""
from __future__ import annotations

from typing import Any

from ulga.validators import (
    validate_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as _canonical,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
DEPRECATED_COMPATIBILITY_SHIM = True
CANONICAL_MODULE = _canonical.__name__


def __getattr__(name: str) -> Any:
    return getattr(_canonical, name)
