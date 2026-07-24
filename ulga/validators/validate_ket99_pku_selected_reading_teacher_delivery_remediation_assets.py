#!/usr/bin/env python3
"""Validate selected KET99 Reading teacher-delivery/remediation assets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_ket99_pku_selected_reading_teacher_delivery_remediation_assets as builder

FAIL_STATUS = "FAIL_KET99_PK_M4C_SELECTED_READING_TEACHER_DELIVERY_REMEDIATION_ASSETS"
DEFAULT_REPORT = builder.ROOT / ".local/a1fs_v1/ket99_pku_m4c/selected_reading_teacher_delivery_remediation_assets.validation.json"


def _walk(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in builder.FORBIDDEN_KEYS:
                errors.append(f"private_content_key_forbidden:{path}.{key}")
            errors.extend(_walk(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            errors.extend(_walk(child, f"{path}[{index}]"))
    return errors


def validate_paths(*, artifact_path: Path, m4a_path: Path, m4b_path: Path) -> dict[str, Any]:
    artifact = builder.read_json(artifact_path)
    expected = builder.build_artifact(builder.read_json(m4a_path), builder.read_json(m4b_path))
    errors: list[str] = []
    if artifact != expected:
        errors.append("artifact_deterministic_rebuild_mismatch")
    errors.extend(_walk(artifact))
    if artifact.get("task_id") != builder.TASK_ID:
        errors.append("task_id_invalid")
    if artifact.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    expected_counts = {
        "authored_asset_bundle_count": 4,
        "authored_placement_count": 11,
        "referenced_lesson_count": 3,
        "teacher_delivery_bundle_count": 3,
        "remediation_bundle_count": 3,
        "teacher_delivery_activated_count": 0,
        "remediation_activated_count": 0,
        "learner_facing_asset_count": 0,
        "composition_item_delta": 0,
        "lesson_selection_delta": 0,
        "mastery_evidence_delta": 0,
        "canonical_coverage_delta": 0,
        "private_text_exposure_count": 0,
    }
    counts = artifact.get("counts", {})
    for key, value in expected_counts.items():
        if counts.get(key) != value:
            errors.append(f"count_invalid:{key}:{counts.get(key)}")
    if {row.get("pku_id") for row in artifact.get("asset_bundles", [])} != set(builder.ASSET_DEFINITIONS):
        errors.append("selected_pku_set_invalid")
    placement_pairs = {(bundle.get("pku_id"), placement.get("lesson_id")) for bundle in artifact.get("asset_bundles", []) for placement in bundle.get("placements", [])}
    expected_pairs = {(pku_id, lesson_id) for pku_id, lessons in builder.PLACEMENT_POLICY.items() for lesson_id in lessons}
    if placement_pairs != expected_pairs:
        errors.append("placement_set_invalid")
    for bundle in artifact.get("asset_bundles", []):
        policy = bundle.get("consumer_policy", {})
        if (policy.get("required_for_delivery"), policy.get("composition_item"), policy.get("learner_facing_allowed"), policy.get("mastery_evidence_allowed"), policy.get("production_activation_allowed"), policy.get("a2_mapping_allowed"), policy.get("private_canary_required_before_activation")) != (False, False, False, False, False, False, True):
            errors.append(f"bundle_boundary_invalid:{bundle.get('asset_id')}")
        if bundle.get("source_evidence", {}).get("verbatim_source_content_included") is not False:
            errors.append(f"verbatim_source_boundary_invalid:{bundle.get('asset_id')}")
        unsigned = {key: value for key, value in bundle.items() if key != "content_sha256"}
        if bundle.get("content_sha256") != builder.digest(unsigned):
            errors.append(f"bundle_content_sha256_invalid:{bundle.get('asset_id')}")
    if artifact.get("claim_boundaries", {}).get("pedagogical_effectiveness_proven") is not False:
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
    parser.add_argument("--m4a-intake", type=Path, default=builder.DEFAULT_M4A)
    parser.add_argument("--m4b-evaluation", type=Path, default=builder.DEFAULT_M4B)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        report = validate_paths(artifact_path=args.artifact, m4a_path=args.m4a_intake, m4b_path=args.m4b_evaluation)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {"task_id": builder.TASK_ID, "validation_status": FAIL_STATUS, "error_count": 1, "errors": [str(exc)], "stop_reason": "VALIDATION_FAILURE", "next_short_step": builder.TASK_ID}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
