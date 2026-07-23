#!/usr/bin/env python3
"""Validate the CP07D policy-bound private delivery consumer."""
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

from ulga.builders import build_a1fs_v1_cp07d_private_four_skill_delivery_consumer as builder  # noqa: E402
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6  # noqa: E402
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy  # noqa: E402

VALIDATOR_ID = "validate_a1fs_v1_cp07d_private_four_skill_delivery_consumer"
SCHEMA_VERSION = "a1fs.v1.cp07d.private_four_skill_delivery_consumer_validation.v1"


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def validate_artifact(
    artifact: Mapping[str, Any],
    *,
    m2_consumer: Mapping[str, Any],
    cp05_approved: Mapping[str, Any],
    cp07c_plan: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if artifact.get("task_id") != m2_consumer.get("task_id"):
        errors.append("m2_task_identity_changed")
    if artifact.get("schema_version") != m2_consumer.get("schema_version"):
        errors.append("m2_schema_identity_changed")
    if artifact.get("validation_status") != m2_consumer.get("validation_status"):
        errors.append("m2_validation_status_changed")
    if artifact.get("cp07d_task_id") != builder.TASK_ID:
        errors.append("cp07d_task_id_invalid")
    if artifact.get("cp07d_schema_version") != builder.SCHEMA_VERSION:
        errors.append("cp07d_schema_version_invalid")
    if artifact.get("cp07d_validation_status") != builder.PASS_STATUS:
        errors.append("cp07d_validation_status_invalid")
    if artifact.get("cp07d_stop_reason") != "NONE" or artifact.get("cp07d_errors") != []:
        errors.append("cp07d_artifact_not_passed")
    if artifact.get("cp07d_next_short_step") != builder.NEXT_SHORT_STEP:
        errors.append("cp07d_next_short_step_invalid")

    expected_source_identity = {
        "m2_consumer_sha256": builder._digest(m2_consumer),
        "cp05_approved_artifact_sha256": str(cp05_approved.get("artifact_sha256") or ""),
        "cp07c_plan_sha256": builder._digest(cp07c_plan),
    }
    if artifact.get("cp07d_source_identity") != expected_source_identity:
        errors.append("cp07d_source_identity_mismatch")

    original_lessons = {str(row.get("lesson_id") or ""): row for row in m2_consumer.get("lesson_catalog", []) if isinstance(row, Mapping)}
    derived_lessons = {str(row.get("lesson_id") or ""): row for row in artifact.get("lesson_catalog", []) if isinstance(row, Mapping)}
    if set(original_lessons) != set(derived_lessons):
        errors.append("lesson_catalog_identity_set_changed")
    original_assets = {str(row.get("asset_key") or ""): row for row in m2_consumer.get("asset_records", []) if isinstance(row, Mapping)}
    derived_assets = {str(row.get("asset_key") or ""): row for row in artifact.get("asset_records", []) if isinstance(row, Mapping)}
    if len(derived_assets) != len(artifact.get("asset_records", [])):
        errors.append("derived_asset_identity_missing_or_duplicate")
    for asset_key, row in original_assets.items():
        if derived_assets.get(asset_key) != row:
            errors.append(f"original_ket_asset_changed:{asset_key}")

    contract = artifact.get("cp07d_delivery_contract")
    if not isinstance(contract, Mapping):
        errors.append("cp07d_delivery_contract_required")
        contract = {}
    selected_lesson = cp07c_plan.get("selected_lesson") or {}
    if contract.get("selected_lesson_id") != selected_lesson.get("lesson_id"):
        errors.append("selected_lesson_binding_mismatch")
    if contract.get("selected_skill") != selected_lesson.get("skill"):
        errors.append("selected_skill_binding_mismatch")
    if contract.get("selected_level") != selected_lesson.get("level"):
        errors.append("selected_level_binding_mismatch")
    if contract.get("a2_payload_included") is not False:
        errors.append("a2_payload_detected")
    for flag in ("m3_session_compatible", "m5_private_renderer_compatible", "m6_feature_rubric_compatible"):
        if contract.get(flag) is not True:
            errors.append(f"runtime_compatibility_flag_invalid:{flag}")
    if contract.get("real_attempt_completed") is not False or contract.get("real_media_registered") is not False:
        errors.append("premature_real_runtime_claim")

    projection_artifacts = artifact.get("cp07d_projection_artifacts")
    if not isinstance(projection_artifacts, list) or not projection_artifacts:
        errors.append("projection_artifact_list_required")
        projection_artifacts = []
    projection_by_sha: dict[str, Mapping[str, Any]] = {}
    for index, projection in enumerate(projection_artifacts):
        if not isinstance(projection, Mapping):
            errors.append(f"projection_artifact_invalid:{index}")
            continue
        try:
            artifact_sha = policy.verify_artifact_digest(projection)
        except policy.ContentPolicyBuildError as exc:
            errors.append(f"projection_digest_invalid:{index}:{exc}")
            continue
        if projection.get("artifact_role") != policy.PROJECTION_ROLE:
            errors.append(f"projection_role_invalid:{index}")
        if projection.get("learner_facing") is not True:
            errors.append(f"projection_learner_facing_invalid:{index}")
        if projection.get("source_bindings", {}).get("approved_canonical_artifact_sha256") != cp05_approved.get("artifact_sha256"):
            errors.append(f"projection_cp05_binding_invalid:{index}")
        payload = projection.get("payload")
        if not isinstance(payload, Mapping) or payload.get("skill") != selected_lesson.get("skill"):
            errors.append(f"projection_skill_invalid:{index}")
        projection_by_sha[artifact_sha] = projection
    if len(projection_by_sha) != len(projection_artifacts):
        errors.append("projection_artifact_sha_duplicate")

    projected_keys = contract.get("projected_asset_keys")
    if not isinstance(projected_keys, list) or not projected_keys:
        errors.append("projected_asset_key_list_required")
        projected_keys = []
    if len(projected_keys) != len(set(projected_keys)):
        errors.append("projected_asset_key_duplicate")
    projected_assets = [derived_assets[key] for key in projected_keys if key in derived_assets]
    if len(projected_assets) != len(projected_keys):
        errors.append("projected_asset_missing_from_consumer")

    role_counts: Counter[str] = Counter()
    capture_keys: list[str] = []
    listening_audio_keys: list[str] = []
    speaking_recording_keys: list[str] = []
    for asset in projected_assets:
        key = str(asset.get("asset_key") or "")
        if asset.get("lesson_id") != selected_lesson.get("lesson_id") or asset.get("skill") != selected_lesson.get("skill"):
            errors.append(f"projected_asset_lesson_or_skill_drift:{key}")
        if asset.get("level") not in {"A1", "A1+"}:
            errors.append(f"projected_asset_a2_or_level_invalid:{key}")
        projection = projection_by_sha.get(str(asset.get("content_digest") or ""))
        if projection is None:
            errors.append(f"projected_asset_projection_binding_missing:{key}")
            continue
        payload = asset.get("payload")
        if not isinstance(payload, Mapping):
            errors.append(f"projected_asset_payload_invalid:{key}")
            continue
        governance = payload.get("content_governance_ref")
        if not isinstance(governance, Mapping) or governance.get("projection_artifact_sha256") != asset.get("content_digest"):
            errors.append(f"projected_asset_governance_ref_invalid:{key}")
        role = str(asset.get("role") or "")
        role_counts[role] += 1
        try:
            response_contract = m6.derive_contract(asset)
        except (m6.ResponseEvidenceError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"m6_contract_derivation_failed:{key}:{exc}")
            continue
        if role == "AUD":
            listening_audio_keys.append(key)
            if response_contract["capture_enabled"] is not False:
                errors.append(f"listening_aud_capture_must_be_disabled:{key}")
            if payload.get("media_registration_required") is not True:
                errors.append(f"listening_media_registration_flag_missing:{key}")
        else:
            if role not in builder.CAPTURE_ROLES:
                errors.append(f"projected_response_role_not_captureable:{key}:{role}")
            if response_contract["capture_enabled"] is not True or response_contract["scoring_mode"] != "FEATURE_RUBRIC":
                errors.append(f"m6_feature_rubric_contract_invalid:{key}")
            capture_keys.append(key)
        if selected_lesson.get("skill") == "SPEAKING":
            if role not in builder.SPEAKING_RECORDING_ROLES:
                errors.append(f"speaking_recording_role_invalid:{key}:{role}")
            if payload.get("recording_capture_required") is not True or payload.get("recording_consent_required") is not True:
                errors.append(f"speaking_recording_contract_missing:{key}")
            speaking_recording_keys.append(key)

    if contract.get("response_capture_asset_keys") != capture_keys:
        errors.append("response_capture_asset_keys_mismatch")
    if contract.get("listening_audio_asset_keys") != listening_audio_keys:
        errors.append("listening_audio_asset_keys_mismatch")
    if contract.get("speaking_recording_asset_keys") != speaking_recording_keys:
        errors.append("speaking_recording_asset_keys_mismatch")
    if contract.get("projected_role_counts") != dict(sorted(role_counts.items())):
        errors.append("projected_role_counts_mismatch")

    expected_asset_count = len(m2_consumer.get("asset_records", [])) + len(projected_assets)
    if artifact.get("counts", {}).get("asset_record_count") != expected_asset_count:
        errors.append("derived_asset_count_mismatch")
    if artifact.get("counts", {}).get("cp07d_projected_asset_count") != len(projected_assets):
        errors.append("projected_asset_summary_mismatch")
    if artifact.get("counts", {}).get("cp07d_projection_artifact_count") != len(projection_artifacts):
        errors.append("projection_artifact_summary_mismatch")

    catalog = derived_lessons.get(str(selected_lesson.get("lesson_id") or ""), {})
    if not set(projected_keys) <= set(catalog.get("asset_keys", [])):
        errors.append("projected_assets_not_mounted_on_selected_lesson")
    if any(row.get("level") == "A2" and row.get("asset_key") in projected_keys for row in artifact.get("asset_records", [])):
        errors.append("a2_projected_asset_detected")

    boundaries = artifact.get("cp07d_claim_boundaries")
    if not isinstance(boundaries, Mapping) or any(value is not False for value in boundaries.values()):
        errors.append("cp07d_claim_boundaries_invalid")

    deterministic_rebuild_matches = False
    try:
        rebuilt = builder.build_private_delivery_consumer(m2_consumer, cp05_approved, cp07c_plan)
        deterministic_rebuild_matches = builder._digest(rebuilt) == builder._digest(artifact)
        if not deterministic_rebuild_matches:
            errors.append("deterministic_rebuild_mismatch")
    except (
        builder.CP07DBuildError,
        policy.ContentPolicyBuildError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(f"deterministic_rebuild_failed:{exc}")

    return {
        "task_id": builder.TASK_ID,
        "validator_id": VALIDATOR_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL_CP07D_PRIVATE_FOUR_SKILL_DELIVERY_CONSUMER",
        "error_count": len(errors),
        "errors": errors,
        "deterministic_rebuild_matches": deterministic_rebuild_matches,
        "selected_skill": selected_lesson.get("skill"),
        "projection_artifact_count": len(projection_artifacts),
        "projected_asset_count": len(projected_assets),
        "response_capture_asset_count": len(capture_keys),
        "listening_audio_asset_count": len(listening_audio_keys),
        "speaking_recording_asset_count": len(speaking_recording_keys),
        "m3_m5_m6_contracts_compatible": not any(
            error.startswith(("m6_", "projected_asset_", "runtime_compatibility")) for error in errors
        ),
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--m2-consumer", type=Path, required=True)
    parser.add_argument("--cp05-approved", type=Path, required=True)
    parser.add_argument("--cp07c-plan", type=Path, required=True)
    args = parser.parse_args(argv)
    report = validate_artifact(
        _read(args.artifact),
        m2_consumer=_read(args.m2_consumer),
        cp05_approved=_read(args.cp05_approved),
        cp07c_plan=_read(args.cp07c_plan),
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == builder.PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
