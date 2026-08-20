#!/usr/bin/env python3
"""Policy-bound facade for Unit01 blueprint-authoritative R2R2 reconciliation.

The canonical producer delegates to the exact-scene R2R2 implementation.  A
production-only compatibility path is retained for historical focused tests whose
synthetic 240-row blueprint intentionally contains no PF09 contextual-reference
activities; real blueprints with PF09 always use the extended exact-scene path.
"""
from __future__ import annotations

from typing import Any, Mapping

from ulga import u01qb18h_r2r2_pf09_exact_scene_impl as _impl
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"


def _has_contextual_reference_demand(blueprint: Any) -> bool:
    return any(
        str(row.get("skill") or "") == "WRITING"
        and str(row.get("task_angle") or "") == _impl.PF09_TASK_ANGLE
        for row in (blueprint or [])
        if isinstance(row, Mapping)
    )


def build_reconciliation_payload(**kwargs: Any) -> dict[str, Any]:
    """Use extended PF09 materialization only when the supplied blueprint asks for it."""
    if _has_contextual_reference_demand(kwargs.get("blueprint")):
        return _impl.build_reconciliation_payload(**kwargs)
    return _impl.base.build_reconciliation_payload(**kwargs)


def build_candidate(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Delegate the policy-bound candidate transition to the canonical impl."""
    _ = policy_artifact
    return _impl.build_candidate(payload)


def __getattr__(name: str):
    return getattr(_impl, name)


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(dir(_impl)))
