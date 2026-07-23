#!/usr/bin/env python3
"""Validate the CP07A unified runtime activity lineage index."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp07a_unified_runtime_activity_contract_and_lineage_adapter as builder  # noqa: E402

VALIDATOR_ID = "validate_a1fs_v1_cp07a_unified_runtime_activity_contract_and_lineage_adapter"
SCHEMA_VERSION = "a1fs.v1.cp07a.unified_runtime_activity_validation.v1"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def _walk_forbidden(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in builder.FORBIDDEN_CONTENT_KEYS:
                errors.append(f"private_content_key_forbidden:{path}.{key}")
            _walk_forbidden(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _walk_forbidden(child, f"{path}[{index}]", errors)


def validate_artifact(
    artifact: Mapping[str, Any],
    *,
    m2_index: Mapping[str, Any],
    cp05_approved: Mapping[str, Any],
    cp06_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if artifact.get("task_id") != builder.TASK_ID:
        errors.append("task_id_invalid")
    if artifact.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_invalid")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY":
        errors.append("scope_invalid")
    if artifact.get("stop_reason") != "NONE" or artifact.get("errors") != []:
        errors.append("artifact_not_passed")
    if artifact.get("next_short_step") != builder.NEXT_SHORT_STEP:
        errors.append("next_short_step_invalid")

    expected_sources = {
        "m2_consumer_sha256": builder._digest(m2_index),
        "cp05_approved_artifact_sha256": str(cp05_approved.get("artifact_sha256") or ""),
        "cp06_artifact_sha256": builder._digest(cp06_artifact),
    }
    if artifact.get("source_identity") != expected_sources:
        errors.append("source_identity_mismatch")

    contract = artifact.get("runtime_activity_contract")
    if not isinstance(contract, Mapping):
        errors.append("runtime_activity_contract_required")
    else:
        if contract.get("source_kinds") != list(builder.SOURCE_KINDS):
            errors.append("runtime_source_kinds_invalid")
        if contract.get("skills") != list(builder.SKILLS):
            errors.append("runtime_skills_invalid")
        if contract.get("levels") != list(builder.LEVELS):
            errors.append("runtime_levels_invalid")
        if contract.get("learner_facing_content_included") is not False:
            errors.append("learner_facing_content_must_be_absent")
        if contract.get("a2_payload_allowed") is not False:
            errors.append("a2_payload_must_be_locked")

    rows = artifact.get("runtime_activities")
    if not isinstance(rows, list) or not rows:
        errors.append("runtime_activity_rows_required")
        rows = []
    seen: set[str] = set()
    source_counts: Counter[str] = Counter()
    skill_counts: Counter[str] = Counter()
    readiness_counts: Counter[str] = Counter()
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            errors.append(f"runtime_activity_row_invalid:{index}")
            continue
        identity = str(row.get("runtime_activity_id") or "")
        source_kind = str(row.get("source_kind") or "")
        skill = str(row.get("skill") or "")
        level = str(row.get("level") or "")
        readiness = str(row.get("runtime_readiness") or "")
        if not identity or identity in seen:
            errors.append(f"runtime_activity_id_missing_or_duplicate:{index}")
        seen.add(identity)
        if source_kind not in builder.SOURCE_KINDS:
            errors.append(f"runtime_source_kind_invalid:{identity}")
        if skill not in builder.SKILLS:
            errors.append(f"runtime_skill_invalid:{identity}")
        if level not in builder.LEVELS:
            errors.append(f"runtime_level_invalid:{identity}")
        if row.get("learner_facing") is not False or row.get("a2_payload_included") is not False:
            errors.append(f"runtime_claim_boundary_invalid:{identity}")
        binding = row.get("curriculum_binding")
        lineage = row.get("source_lineage")
        response_ref = row.get("response_contract_ref")
        roles = row.get("instructional_roles")
        if not isinstance(binding, Mapping) or not isinstance(lineage, Mapping) or not isinstance(response_ref, Mapping):
            errors.append(f"runtime_binding_or_lineage_missing:{identity}")
        if not isinstance(roles, list) or "FOCUS" not in roles:
            errors.append(f"runtime_focus_role_missing:{identity}")
        if source_kind == "RAZ_ACTIVITY_BINDING":
            if any(role not in builder.CONTENT_ROLES for role in roles):
                errors.append(f"raz_content_role_invalid:{identity}")
            expected = {
                "READING": "QUERYABLE_TEXT_RUNTIME_CONTRACT",
                "WRITING": "QUERYABLE_TEXT_RUNTIME_CONTRACT",
                "LISTENING": "BLOCKED_AUDIO_GENERATION",
                "SPEAKING": "BLOCKED_RECORDING_CAPTURE",
            }.get(skill)
            if readiness != expected:
                errors.append(f"raz_runtime_readiness_invalid:{identity}")
            if response_ref.get("authority") != "CP05_APPROVED_SKILL_CONTRACT":
                errors.append(f"raz_response_contract_ref_invalid:{identity}")
        elif source_kind == "KET_ASSET_BODY":
            if readiness != "QUERYABLE_PRIVATE_KET_ASSET":
                errors.append(f"ket_runtime_readiness_invalid:{identity}")
            if binding.get("ket_lesson_id") in {None, ""}:
                errors.append(f"ket_lesson_binding_missing:{identity}")
        elif source_kind == "M11B_REVIEWED_ACTIVITY":
            if readiness != "PENDING_REVIEWED_PAYLOAD_RESOLUTION":
                errors.append(f"m11b_runtime_readiness_invalid:{identity}")
        source_counts[source_kind] += 1
        skill_counts[skill] += 1
        readiness_counts[readiness] += 1

    summary = artifact.get("coverage_summary")
    if not isinstance(summary, Mapping):
        errors.append("coverage_summary_required")
        summary = {}
    expected_summary = {
        "runtime_activity_count": len(rows),
        "source_kind_counts": {kind: source_counts[kind] for kind in builder.SOURCE_KINDS},
        "skill_counts": {skill: skill_counts[skill] for skill in builder.SKILLS},
        "runtime_readiness_counts": dict(sorted(readiness_counts.items())),
    }
    for key, value in expected_summary.items():
        if summary.get(key) != value:
            errors.append(f"coverage_summary_mismatch:{key}")
    if summary.get("existing_learning_unit_count") != 24 or summary.get("new_learning_unit_count") != 0:
        errors.append("coverage_unit_count_invalid")
    if summary.get("a2_activity_count") != 0:
        errors.append("a2_activity_detected")

    boundaries = artifact.get("claim_boundaries")
    if not isinstance(boundaries, Mapping) or any(value is not False for value in boundaries.values()):
        errors.append("claim_boundaries_invalid")
    _walk_forbidden(artifact, "$", errors)

    deterministic_rebuild_matches = False
    try:
        rebuilt = builder.build_artifact(m2_index, cp05_approved, cp06_artifact)
        deterministic_rebuild_matches = builder._digest(rebuilt) == builder._digest(artifact)
        if not deterministic_rebuild_matches:
            errors.append("deterministic_rebuild_mismatch")
    except (builder.CP07ABuildError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"deterministic_rebuild_failed:{exc}")

    ket_queryable = raz_text_queryable = a2_fail_closed = False
    try:
        ket_result = builder.query_runtime_activity_index(
            artifact, source_kind="KET_ASSET_BODY", limit=1
        )
        ket_queryable = ket_result["returned_count"] == 1
        if not ket_queryable:
            errors.append("ket_consumer_smoke_failed")
        raz_result = builder.query_runtime_activity_index(
            artifact,
            source_kind="RAZ_ACTIVITY_BINDING",
            runtime_readiness="QUERYABLE_TEXT_RUNTIME_CONTRACT",
            limit=1,
        )
        raz_text_queryable = raz_result["returned_count"] == 1
        if not raz_text_queryable:
            errors.append("raz_text_consumer_smoke_failed")
    except (builder.CP07ABuildError, KeyError, TypeError, ValueError) as exc:
        errors.append(f"consumer_smoke_failed:{exc}")
    try:
        builder.query_runtime_activity_index(artifact, level="A2")
        errors.append("a2_query_not_rejected")
    except builder.CP07ABuildError as exc:
        a2_fail_closed = str(exc) == "A2_PAYLOAD_LOCKED"
        if not a2_fail_closed:
            errors.append(f"a2_query_wrong_failure:{exc}")

    return {
        "task_id": builder.TASK_ID,
        "validator_id": VALIDATOR_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL_CP07A_UNIFIED_RUNTIME_ACTIVITY_INDEX",
        "error_count": len(errors),
        "errors": errors,
        "deterministic_rebuild_matches": deterministic_rebuild_matches,
        "ket_queryable": ket_queryable,
        "raz_text_queryable": raz_text_queryable,
        "a2_fail_closed": a2_fail_closed,
        "coverage_summary": dict(summary),
        "private_or_learner_content_absent": not any(error.startswith("private_content_key_forbidden") for error in errors),
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--m2-consumer", type=Path, required=True)
    parser.add_argument("--cp05-approved", type=Path, required=True)
    parser.add_argument("--cp06", type=Path, required=True)
    args = parser.parse_args(argv)
    report = validate_artifact(
        _read(args.artifact),
        m2_index=_read(args.m2_consumer),
        cp05_approved=_read(args.cp05_approved),
        cp06_artifact=_read(args.cp06),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == builder.PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
