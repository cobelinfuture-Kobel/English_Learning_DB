#!/usr/bin/env python3
"""Canonical RAZQ01E entry with projection-authority-safe family fallback."""
from __future__ import annotations

from ulga.builders import _razq01e_existing_qb_runtime_core as _core

for _name in dir(_core):
    if _name not in {"__name__", "__loader__", "__package__", "__spec__"}:
        globals()[_name] = getattr(_core, _name)

_ORIGINAL_STRUCTURE = _core._structure
_ORIGINAL_MATERIALIZE_ITEM = _core._materialize_item
_ACTIVE_SKILL: str | None = None
_ACTIVE_PROJECTED_FAMILIES: frozenset[str] = frozenset()


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
