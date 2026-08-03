#!/usr/bin/env python3
"""Independently validate policy-bound Unit01 cumulative micro-scene expansion."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy
from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as r1
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as builder
from ulga.validators import validate_a1fs_v1_policy_bound_content_artifact as policy_validator

PASS_STATUS = "PASS_A1FS_V1_U01QB07_UNIT01_MICRO_SCENE_SEED_ENRICHMENT_VALIDATION"


class SceneEnrichmentValidationError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SceneEnrichmentValidationError(f"UNREADABLE_JSON:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise SceneEnrichmentValidationError("OBJECT_REQUIRED")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def validate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    policy_report = policy_validator.validate_artifact(
        candidate,
        expected_role=content_policy.CANDIDATE_ROLE,
    )
    if policy_report.get("validation_status") != policy_validator.PASS_STATUS:
        errors.append("policy_bound_candidate_invalid")

    payload = candidate.get("payload") if isinstance(candidate.get("payload"), Mapping) else {}
    if payload.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if (
        payload.get("task_id") != builder.TASK_ID
        or payload.get("status") != builder.PASS_STATUS
        or payload.get("unit_id") != builder.UNIT_ID
    ):
        errors.append("identity_invalid")
    if payload.get("scene_growth_policy") != r1.SCENE_GROWTH_POLICY:
        errors.append("scene_growth_policy_invalid")

    model = payload.get("model_authored_scenes") if isinstance(payload.get("model_authored_scenes"), list) else []
    combined = payload.get("cumulative_unique_scenes") if isinstance(payload.get("cumulative_unique_scenes"), list) else []
    if len(model) != builder.EXPECTED_SUPPLEMENT_COUNT:
        errors.append("model_authored_count_invalid")

    signatures: list[str] = []
    for row in model:
        if not isinstance(row, Mapping):
            errors.append("model_scene_not_object")
            continue
        core = row.get("semantic_scene_core") or {}
        signatures.append(str(row.get("semantic_scene_signature_v2")))
        if row.get("semantic_scene_signature_v2") != r1.digest(core):
            errors.append("semantic_signature_invalid")
        if r1.genuine_scene_reason_codes(core):
            errors.append("model_scene_fails_genuine_gate")
        if row.get("scene_taxonomy") != r1.scene_taxonomy(core):
            errors.append("taxonomy_invalid")
        if row.get("lineage_mode") != "MODEL_AUTHORED_FROM_APPROVED_SEEDS":
            errors.append("lineage_mode_invalid")
        provenance = row.get("provenance") or {}
        if (
            not provenance.get("resolved_seed_scene_ref_ids")
            or provenance.get("source_equivalence_claimed") is not False
        ):
            errors.append("seed_provenance_invalid")
        if row.get("counts_toward_scene_rotation") is not True:
            errors.append("model_scene_not_rotation_ready")
    if len(signatures) != len(set(signatures)):
        errors.append("model_semantic_duplicate")

    combined_signatures = [
        str(row.get("semantic_scene_signature_v2"))
        for row in combined
        if isinstance(row, Mapping)
    ]
    if len(combined_signatures) != len(set(combined_signatures)):
        errors.append("combined_semantic_duplicate")

    total = len(combined)
    families = {
        str(row.get("situation_family"))
        for row in combined
        if isinstance(row, Mapping) and row.get("situation_family") != "UNCLASSIFIED_OBJECT"
    }
    expected_capacity = {
        "genuine_distinct_micro_scene_count": total,
        "target_range": [builder.TARGET_MIN, builder.TARGET_MAX],
        "target_range_pass": builder.TARGET_MIN <= total <= builder.TARGET_MAX,
        "hard_min_24_pass": total >= 24,
        "situation_family_count": len(families),
        "situation_family_min_5_pass": len(families) >= 5,
        "maximum_scene_slots_at_two_uses_each": total * 2,
        "required_scene_slots": 48,
        "twelve_form_rotation_ready": total >= 24 and len(families) >= 5,
    }
    if payload.get("rotation_capacity") != expected_capacity:
        errors.append("rotation_capacity_invalid")
    if not expected_capacity["target_range_pass"]:
        errors.append("target_range_not_met")
    if not expected_capacity["twelve_form_rotation_ready"]:
        errors.append("twelve_form_capacity_not_met")

    boundaries = payload.get("boundaries") or {}
    if boundaries != {
        "source_equivalence_claimed": False,
        "question_items_mutated": False,
        "scoring_mutated": False,
        "learner_state_mutated": False,
        "mastery_claimed": False,
    }:
        errors.append("boundaries_invalid")

    unsigned_payload = deepcopy(dict(payload))
    declared_pool_sha = unsigned_payload.pop("pool_sha256", None)
    if declared_pool_sha != r1.digest(unsigned_payload):
        errors.append("pool_sha256_invalid")

    report: dict[str, Any] = {
        "status": PASS_STATUS if not errors else "FAIL_A1FS_V1_U01QB07_VALIDATION",
        "validator_id": builder.VALIDATOR_ID,
        "candidate_artifact_sha256": candidate.get("artifact_sha256"),
        "error_count": len(errors),
        "errors": errors,
        "cumulative_distinct_scene_count": total,
        "situation_family_count": len(families),
        "twelve_form_rotation_ready": expected_capacity["twelve_form_rotation_ready"],
    }
    report["report_sha256"] = content_policy.digest(report)
    if errors:
        raise SceneEnrichmentValidationError("|".join(errors))
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = validate(read_json(args.candidate))
        if args.output is not None:
            write_json(args.output, report)
    except (SceneEnrichmentValidationError, KeyError, TypeError, ValueError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB07_UNIT01_MICRO_SCENE_SEED_ENRICHMENT_VALIDATION")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={report['status']}")
    print(f"CANDIDATE_ARTIFACT_SHA256={report['candidate_artifact_sha256']}")
    print(f"CUMULATIVE_DISTINCT_SCENES={report['cumulative_distinct_scene_count']}")
    print(f"SITUATION_FAMILIES={report['situation_family_count']}")
    print(f"TWELVE_FORM_ROTATION_READY={report['twelve_form_rotation_ready']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
