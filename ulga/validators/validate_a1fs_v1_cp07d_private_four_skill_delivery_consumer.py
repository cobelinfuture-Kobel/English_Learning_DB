#!/usr/bin/env python3
"""Public CP07D validator enforcing selected-lesson level identity."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_cp07d_private_four_skill_delivery_consumer as builder
from ulga.validators import cp07d_private_four_skill_delivery_consumer_validation_impl as _impl

_ORIGINAL_VALIDATE = _impl.validate_artifact


def validate_artifact(
    artifact: Mapping[str, Any],
    *,
    m2_consumer: Mapping[str, Any],
    cp05_approved: Mapping[str, Any],
    cp07c_plan: Mapping[str, Any],
) -> dict[str, Any]:
    report = _ORIGINAL_VALIDATE(
        artifact,
        m2_consumer=m2_consumer,
        cp05_approved=cp05_approved,
        cp07c_plan=cp07c_plan,
    )
    selected_lesson = cp07c_plan.get("selected_lesson")
    selected_level = selected_lesson.get("level") if isinstance(selected_lesson, Mapping) else None
    contract = artifact.get("cp07d_delivery_contract")
    projected_keys = contract.get("projected_asset_keys", []) if isinstance(contract, Mapping) else []
    projected_key_set = set(projected_keys) if isinstance(projected_keys, list) else set()
    mismatches: list[str] = []
    for asset in artifact.get("asset_records", []):
        if not isinstance(asset, Mapping) or asset.get("asset_key") not in projected_key_set:
            continue
        if asset.get("level") != selected_level:
            mismatches.append(f"projected_asset_selected_lesson_level_drift:{asset.get('asset_key')}")
    if mismatches:
        errors = list(report.get("errors", []))
        for error in mismatches:
            if error not in errors:
                errors.append(error)
        report["errors"] = errors
        report["error_count"] = len(errors)
        report["validation_status"] = "FAIL_CP07D_PRIVATE_FOUR_SKILL_DELIVERY_CONSUMER"
        report["m3_m5_m6_contracts_compatible"] = False
        report["stop_reason"] = "VALIDATION_FAILED"
    return report


def main(argv: Sequence[str] | None = None) -> int:
    original = _impl.validate_artifact
    _impl.validate_artifact = validate_artifact
    try:
        return _impl.main(argv)
    finally:
        _impl.validate_artifact = original


def __getattr__(name: str) -> Any:
    return getattr(_impl, name)


if __name__ == "__main__":
    raise SystemExit(main())
