#!/usr/bin/env python3
"""Canonical RAZQ01E entry with projection-authority-safe family fallback."""
from __future__ import annotations

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import _razq01e_existing_qb_runtime_core as _core
from ulga.builders import (
    build_a1fs_ops_v1_unit01_identity_scoped_fair_question_selection as identity_fair,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"

# The FullFix patches the existing U01QB02 class before RAZQ01E materialization.
# _core.qb02 and identity_fair.qb02 reference the same runtime authority.
identity_fair.install_fullfix()

for _name in dir(_core):
    if _name not in {"__name__", "__loader__", "__package__", "__spec__"}:
        globals()[_name] = getattr(_core, _name)

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"
policy_artifact = policy_artifact
identity_fair = identity_fair
_ORIGINAL_STRUCTURE = _core._structure
_ORIGINAL_MATERIALIZE_ITEM = _core._materialize_item
_ACTIVE_SKILL: str | None = None
_ACTIVE_PROJECTED_FAMILIES: frozenset[str] = frozenset()


def build_candidate(approved_content):
    return _core.build_candidate(approved_content)


def admit_candidate(candidate):
    return _core.admit_candidate(candidate)


def _projection_safe_structure(asset):
    structure, noun, adjective = _ORIGINAL_STRUCTURE(asset)
    if _ACTIVE_SKILL != "SPEAKING" or not _ACTIVE_PROJECTED_FAMILIES:
        return structure, noun, adjective
    candidates = [structure]
    if adjective is not None and "ADJECTIVE" not in candidates:
        candidates.append("ADJECTIVE")
    if "NOUN" not in candidates:
        candidates.append("NOUN")
    for candidate in candidates:
        if _core._family_for("SPEAKING", candidate) in _ACTIVE_PROJECTED_FAMILIES:
            return (
                candidate,
                noun,
                adjective if candidate in {"VERY", "ADJECTIVE"} else None,
            )
    return structure, noun, adjective


def _projection_safe_materialize_item(
    asset,
    *,
    skill: str,
    approved_content_sha256: str,
):
    global _ACTIVE_SKILL, _ACTIVE_PROJECTED_FAMILIES
    projection = _core._projection(asset, skill)
    previous_skill = _ACTIVE_SKILL
    previous_families = _ACTIVE_PROJECTED_FAMILIES
    _ACTIVE_SKILL = skill
    _ACTIVE_PROJECTED_FAMILIES = frozenset(
        str(value) for value in projection.get("existing_family_ids") or []
    )
    try:
        return _ORIGINAL_MATERIALIZE_ITEM(
            asset,
            skill=skill,
            approved_content_sha256=approved_content_sha256,
        )
    finally:
        _ACTIVE_SKILL = previous_skill
        _ACTIVE_PROJECTED_FAMILIES = previous_families


_core._structure = _projection_safe_structure
_core._materialize_item = _projection_safe_materialize_item
_structure = _projection_safe_structure
_materialize_item = _projection_safe_materialize_item


if __name__ == "__main__":
    raise SystemExit(_core.main())
