#!/usr/bin/env python3
"""Validate KET99 M4D selected Reading asset private consumer canary."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_ket99_pku_selected_reading_asset_consumer_activation_canary as builder

FAIL_STATUS = "FAIL_KET99_PK_M4D_SELECTED_READING_ASSET_CONSUMER_PRIVATE_CANARY"


def validate_paths(*, artifact: Mapping[str, Any], m4c_value: Mapping[str, Any], cp07d_value: Mapping[str, Any]) -> dict[str, Any]:
    expected = builder.build_artifact(m4c_value, cp07d_value)
    errors: list[str] = []
    if artifact != expected:
        errors.append("artifact_deterministic_rebuild_mismatch")
    if artifact.get("m4d_task_id") != builder.TASK_ID or artifact.get("m4d_schema_version") != builder.SCHEMA_VERSION:
        errors.append("m4d_identity_invalid")
    canary = artifact.get("m4d_private_canary", {})
    counts = artifact.get("m4d_counts", {})
    if canary.get("asset_records_digest_before") != canary.get("asset_records_digest_after"):
        errors.append("asset_records_mutated")
    if canary.get("counts_digest_before") != canary.get("counts_digest_after"):
        errors.append("cp07d_counts_mutated")
    if canary.get("projected_asset_keys_before") != canary.get("projected_asset_keys_after"):
        errors.append("projected_asset_keys_mutated")
    if canary.get("response_capture_asset_keys_before") != canary.get("response_capture_asset_keys_after"):
        errors.append("response_capture_contract_mutated")
    for key in (
        "composition_item_delta", "required_delivery_asset_delta", "asset_record_delta",
        "response_capture_contract_delta", "mastery_evidence_delta", "canonical_coverage_delta", "a2_unlock_count",
    ):
        if counts.get(key) != 0:
            errors.append(f"boundary_count_invalid:{key}")
    contract = artifact.get("cp07d_delivery_contract", {})
    teacher_assets = contract.get("optional_teacher_delivery_assets", [])
    remediation_assets = artifact.get("m7_optional_remediation_asset_registry", [])
    if canary.get("selected_lesson_has_authored_assets"):
        if not teacher_assets or not remediation_assets:
            errors.append("referenced_canary_assets_missing")
        if canary.get("canary_status") != "PASS_REFERENCED_READING_ASSET_PRIVATE_CANARY":
            errors.append("referenced_canary_status_invalid")
    else:
        if teacher_assets or remediation_assets:
            errors.append("nonreferenced_canary_assets_present")
        if canary.get("canary_status") != "PASS_NON_BLOCKING_NO_SELECTED_READING_ASSET":
            errors.append("nonreferenced_canary_status_invalid")
    for row in teacher_assets:
        if row.get("required_for_delivery") is not False or row.get("composition_item") is not False or row.get("learner_facing_allowed") is not False:
            errors.append(f"teacher_asset_boundary_invalid:{row.get('asset_id')}")
    for row in remediation_assets:
        if row.get("mastery_evidence_allowed") is not False or not row.get("trigger_signatures"):
            errors.append(f"remediation_asset_boundary_invalid:{row.get('support_asset_id')}")
    if artifact.get("m4d_claim_boundaries", {}).get("pedagogical_effectiveness_proven") is not False:
        errors.append("effectiveness_claim_invalid")
    return {
        "task_id": builder.TASK_ID,
        "validation_status": builder.PASS_STATUS if not errors else FAIL_STATUS,
        "error_count": len(errors),
        "errors": errors,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else builder.TASK_ID,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--m4c-assets", type=Path, default=builder.DEFAULT_M4C)
    parser.add_argument("--cp07d-consumer", type=Path, default=builder.DEFAULT_CP07D)
    parser.add_argument("--report", type=Path, default=builder.DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        artifact = builder.read_json(args.artifact)
        report = validate_paths(artifact=artifact, m4c_value=builder.read_json(args.m4c_assets), cp07d_value=builder.read_json(args.cp07d_consumer))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {"task_id": builder.TASK_ID, "validation_status": FAIL_STATUS, "error_count": 1, "errors": [str(exc)], "stop_reason": "VALIDATION_FAILURE", "next_short_step": builder.TASK_ID}
    builder.write(args.report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
