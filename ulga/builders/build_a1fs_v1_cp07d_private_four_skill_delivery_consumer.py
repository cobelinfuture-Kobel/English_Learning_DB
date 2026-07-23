#!/usr/bin/env python3
"""Public CP07D builder with selected-lesson level binding.

The large, already-reviewed implementation remains in
``cp07d_private_four_skill_delivery_consumer_impl``.  This public entry point
adds the production invariant that every projected activity mounted on a KET
lesson has the exact level selected by M4, rather than inheriting the broader
A1/A1+ scope of the CP05 approved source artifact.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ulga.builders import cp07d_private_four_skill_delivery_consumer_impl as _impl

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "SELECTED_LESSON_LEVEL_BINDING_ONLY; POLICY-BOUND FOUR-SKILL PROJECTION "
    "REMAINS DELEGATED TO CP07D_IMPL"
)

_ORIGINAL_BUILD = _impl.build_private_delivery_consumer


def build_private_delivery_consumer(
    m2_consumer: Mapping[str, Any],
    cp05_approved: Mapping[str, Any],
    cp07c_plan: Mapping[str, Any],
) -> dict[str, Any]:
    result = _ORIGINAL_BUILD(m2_consumer, cp05_approved, cp07c_plan)
    contract = result.get("cp07d_delivery_contract")
    if not isinstance(contract, Mapping):
        raise _impl.CP07DBuildError("cp07d_delivery_contract_required")
    selected_level = str(contract.get("selected_level") or "")
    if selected_level not in {"A1", "A1+"}:
        raise _impl.CP07DBuildError("selected_lesson_level_invalid")
    projected_keys = contract.get("projected_asset_keys")
    if not isinstance(projected_keys, list) or not projected_keys:
        raise _impl.CP07DBuildError("projected_asset_key_list_required")
    projected_key_set = set(projected_keys)
    rebound_count = 0
    for asset in result.get("asset_records", []):
        if isinstance(asset, dict) and asset.get("asset_key") in projected_key_set:
            asset["level"] = selected_level
            rebound_count += 1
    if rebound_count != len(projected_key_set):
        raise _impl.CP07DBuildError("projected_asset_level_binding_incomplete")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    original = _impl.build_private_delivery_consumer
    _impl.build_private_delivery_consumer = build_private_delivery_consumer
    try:
        return _impl.main(argv)
    finally:
        _impl.build_private_delivery_consumer = original


def __getattr__(name: str) -> Any:
    return getattr(_impl, name)


if __name__ == "__main__":
    raise SystemExit(main())
