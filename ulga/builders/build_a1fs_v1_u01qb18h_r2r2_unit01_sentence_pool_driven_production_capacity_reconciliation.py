#!/usr/bin/env python3
"""Policy-bound facade for Unit01 blueprint-authoritative R2R2 reconciliation.

Implementation lives outside the canonical builder discovery namespace so the
public producer can expose the governance policy binding literally while keeping
all runtime behavior in one implementation module.
"""
from __future__ import annotations

from ulga import u01qb18h_r2r2_blueprint_dynamic_impl as _impl

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"


def __getattr__(name: str):
    return getattr(_impl, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_impl)))
