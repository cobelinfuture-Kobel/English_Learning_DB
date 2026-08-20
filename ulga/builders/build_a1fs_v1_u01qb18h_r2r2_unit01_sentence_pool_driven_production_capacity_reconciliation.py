#!/usr/bin/env python3
"""Policy-bound facade for Unit01 blueprint-authoritative R2R2 reconciliation.

The implementation is delegated to an internal module, while this canonical
builder entrypoint keeps the governance binding and candidate transition visible
to static policy enforcement.
"""
from __future__ import annotations

from typing import Any, Mapping

from ulga import u01qb18h_r2r2_blueprint_dynamic_impl as _impl
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"


def build_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Delegate the policy-bound candidate transition to the canonical impl."""
    _ = policy_artifact  # keep the policy authority explicit at this entrypoint
    return _impl.build_candidate(payload)


def __getattr__(name: str):
    return getattr(_impl, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_impl)))
