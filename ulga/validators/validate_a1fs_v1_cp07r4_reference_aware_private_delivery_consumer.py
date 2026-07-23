#!/usr/bin/env python3
"""Validate the R4 reference-aware private delivery consumer."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_cp07r4_reference_aware_private_delivery_consumer as builder
from ulga.builders import cp07d_private_four_skill_delivery_consumer_impl as cp07d

FAIL_STATUS = "FAIL_CP07F_R4_REFERENCE_AWARE_PRIVATE_DELIVERY_CONSUMER"


def _append(errors: list[str], condition: bool, message: str) -> None:
    if not condition and message not in errors:
        errors.append(message)


def validate_artifact(
    artifact: Mapping[str, Any],
    *,
    m2_consumer: Mapping[str, Any],
    cp05_approved: Mapping[str, Any],
    r3f_plan: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        rebuilt = builder.build_private_delivery_consumer(m2_consumer, cp05_approved, r3f_plan)
    except Exception as exc:  # fail-closed report boundary
        rebuilt = None
        errors.append(f"deterministic_rebuild_failed:{type(exc).__name__}:{exc}")

    _append(errors, artifact.get("cp07r4_task_id") == builder.TASK_ID, "task_id_invalid")
    _append(errors, artifact.get("cp07r4_schema_version") == builder.SCHEMA_VERSION, "schema_version_invalid")
    _append(errors, artifact.get("cp07r4_validation_status") == builder.PASS_STATUS, "validation_status_invalid")
    _append(errors, artifact.get("cp07d_task_id") == cp07d.TASK_ID, "cp07d_compatibility_task_invalid")
    _append(errors, artifact.get("cp07d_schema_version") == cp07d.SCHEMA_VERSION, "cp07d_compatibility_schema_invalid")
    _append(errors, artifact.get("cp07d_validation_status") == cp07d.PASS_STATUS, "cp07d_compatibility_status_invalid")
    _append(errors, artifact.get("cp07d_errors") == [], "cp07d_errors_not_empty")
    _append(errors, artifact.get("cp07d_stop_reason") == "NONE", "cp07d_stop_reason_invalid")

    source_identity = artifact.get("cp07r4_source_identity")
    _append(errors, isinstance(source_identity, Mapping), "source_identity_missing")
    if isinstance(source_identity, Mapping):
        _append(errors, source_identity.get("m2_consumer_sha256") == cp07d._digest(m2_consumer), "m2_source_binding_invalid")
        _append(errors, source_identity.get("r3f_plan_sha256") == cp07d._digest(r3f_plan), "r3f_source_binding_invalid")

    lesson = r3f_plan.get("selected_lesson")
    composition = r3f_plan.get("unified_lesson_composition")
    contract = artifact.get("cp07d_delivery_contract")
    gaps = artifact.get("cp07r4_capability_gaps")
    _append(errors, isinstance(lesson, Mapping), "selected_lesson_missing")
    _append(errors, isinstance(composition, Mapping), "r3f_composition_missing")
    _append(errors, isinstance(contract, Mapping), "delivery_contract_missing")
    _append(errors, isinstance(gaps, Mapping), "capability_gaps_missing")

    projected_keys: list[str] = []
    mounted_keys: list[str] = []
    response_keys: list[str] = []
    audio_keys: list[str] = []
    recording_keys: list[str] = []
    if isinstance(contract, Mapping) and isinstance(lesson, Mapping) and isinstance(composition, Mapping):
        _append(errors, contract.get("selected_lesson_id") == lesson.get("lesson_id"), "selected_lesson_id_drift")
        _append(errors, contract.get("selected_skill") == lesson.get("skill"), "selected_skill_drift")
        _append(errors, contract.get("selected_level") == lesson.get("level"), "selected_level_drift")
        _append(errors, contract.get("composition_mode") == composition.get("composition_mode"), "composition_mode_drift")
        _append(errors, contract.get("missing_reference_blocks_delivery") is False, "missing_reference_blocks_delivery")
        _append(errors, contract.get("optional_context_projection_required") is False, "optional_context_projection_became_required")
        _append(errors, contract.get("m3_session_compatible") is True, "m3_compatibility_invalid")
        _append(errors, contract.get("m5_private_renderer_compatible") is True, "m5_compatibility_invalid")
        _append(errors, contract.get("a2_payload_included") is False, "a2_payload_included")
        mounted_keys = list(contract.get("mounted_ket_asset_keys", [])) if isinstance(contract.get("mounted_ket_asset_keys"), list) else []
        projected_keys = list(contract.get("projected_asset_keys", [])) if isinstance(contract.get("projected_asset_keys"), list) else []
        response_keys = list(contract.get("response_capture_asset_keys", [])) if isinstance(contract.get("response_capture_asset_keys"), list) else []
        audio_keys = list(contract.get("listening_audio_asset_keys", [])) if isinstance(contract.get("listening_audio_asset_keys"), list) else []
        recording_keys = list(contract.get("speaking_recording_asset_keys", [])) if isinstance(contract.get("speaking_recording_asset_keys"), list) else []
        expected_mode = "KET_ASSET_BODY_WITH_OPTIONAL_CONTEXT_PROJECTIONS" if projected_keys else "KET_ASSET_BODY_ONLY"
        _append(errors, contract.get("delivery_mode") == expected_mode, "delivery_mode_invalid")
        _append(errors, contract.get("m6_feature_rubric_compatible") is bool(response_keys), "m6_capability_claim_invalid")
        _append(errors, contract.get("m10_private_media_registration_compatible") is bool(audio_keys or recording_keys), "m10_capability_claim_invalid")

    base_assets = {
        str(row.get("asset_key") or ""): row
        for row in m2_consumer.get("asset_records", [])
        if isinstance(row, Mapping)
    }
    result_assets = {
        str(row.get("asset_key") or ""): row
        for row in artifact.get("asset_records", [])
        if isinstance(row, Mapping)
    }
    _append(errors, len(result_assets) == len(artifact.get("asset_records", [])), "asset_identity_missing_or_duplicate")
    for key, row in base_assets.items():
        _append(errors, result_assets.get(key) == row, f"base_m2_asset_drift:{key}")

    if isinstance(lesson, Mapping):
        catalog_matches = [
            row for row in m2_consumer.get("lesson_catalog", [])
            if isinstance(row, Mapping) and row.get("lesson_id") == lesson.get("lesson_id")
        ]
        _append(errors, len(catalog_matches) == 1, "selected_m2_catalog_not_unique")
        if len(catalog_matches) == 1:
            expected_mounted = sorted(str(value) for value in catalog_matches[0].get("asset_keys", []))
            _append(errors, sorted(mounted_keys) == expected_mounted and bool(expected_mounted), "mounted_ket_asset_set_invalid")
        for key in mounted_keys + projected_keys:
            row = result_assets.get(key)
            _append(errors, row is not None, f"mounted_asset_missing:{key}")
            if isinstance(row, Mapping):
                _append(errors, row.get("lesson_id") == lesson.get("lesson_id"), f"mounted_asset_lesson_drift:{key}")
                _append(errors, row.get("skill") == lesson.get("skill"), f"mounted_asset_skill_drift:{key}")
                _append(errors, row.get("level") == lesson.get("level"), f"mounted_asset_level_drift:{key}")

    raz_items = []
    if isinstance(composition, Mapping):
        raz_items = [
            row for row in composition.get("composition_items", [])
            if isinstance(row, Mapping) and row.get("source_kind") == "RAZ_ACTIVITY_BINDING"
        ]
    if raz_items:
        _append(errors, bool(projected_keys), "r3f_context_not_projected")
        if isinstance(source_identity, Mapping):
            _append(errors, source_identity.get("cp05_approved_artifact_sha256") == cp05_approved.get("artifact_sha256"), "cp05_source_binding_invalid")
    else:
        _append(errors, projected_keys == [], "unexpected_context_projection")
        if isinstance(source_identity, Mapping):
            _append(errors, source_identity.get("cp05_approved_artifact_sha256") is None, "unused_cp05_binding_must_be_null")

    counts = artifact.get("counts")
    _append(errors, isinstance(counts, Mapping), "counts_missing")
    if isinstance(counts, Mapping):
        _append(errors, counts.get("cp07r4_mounted_ket_asset_count") == len(mounted_keys), "mounted_ket_count_invalid")
        _append(errors, counts.get("cp07d_projected_asset_count") == len(projected_keys), "projected_asset_count_invalid")
        _append(errors, counts.get("cp07d_projection_artifact_count") == len(artifact.get("cp07d_projection_artifacts", [])), "projection_artifact_count_invalid")
        _append(errors, counts.get("asset_record_count") == len(artifact.get("asset_records", [])), "asset_record_count_invalid")

    if isinstance(gaps, Mapping):
        _append(errors, gaps.get("response_capture_contract_missing") is (not bool(response_keys)), "response_gap_invalid")
        expected_audio_gap = bool(isinstance(lesson, Mapping) and lesson.get("skill") == "LISTENING" and not audio_keys)
        expected_recording_gap = bool(isinstance(lesson, Mapping) and lesson.get("skill") == "SPEAKING" and not recording_keys)
        _append(errors, gaps.get("listening_audio_registration_contract_missing") is expected_audio_gap, "listening_audio_gap_invalid")
        _append(errors, gaps.get("speaking_recording_contract_missing") is expected_recording_gap, "speaking_recording_gap_invalid")
        _append(errors, gaps.get("optional_context_not_projected") is (not bool(projected_keys)), "optional_context_gap_invalid")

    boundaries = artifact.get("cp07d_claim_boundaries")
    _append(errors, isinstance(boundaries, Mapping), "claim_boundaries_missing")
    if isinstance(boundaries, Mapping):
        for key in (
            "real_learner_attempt_claimed",
            "real_listening_audio_claimed",
            "real_speaking_recording_claimed",
            "automatic_speaking_score_claimed",
            "mastery_or_retention_claimed",
            "public_delivery_claimed",
            "a2_a2plus_in_scope",
        ):
            _append(errors, boundaries.get(key) is False, f"claim_boundary_invalid:{key}")

    deterministic = rebuilt == artifact if rebuilt is not None else False
    _append(errors, deterministic, "deterministic_rebuild_mismatch")

    status = builder.PASS_STATUS if not errors else FAIL_STATUS
    return {
        "task_id": builder.TASK_ID,
        "schema_version": builder.SCHEMA_VERSION,
        "validation_status": status,
        "error_count": len(errors),
        "errors": errors,
        "deterministic_rebuild_matches": deterministic,
        "selected_lesson_id": contract.get("selected_lesson_id") if isinstance(contract, Mapping) else None,
        "selected_skill": contract.get("selected_skill") if isinstance(contract, Mapping) else None,
        "delivery_mode": contract.get("delivery_mode") if isinstance(contract, Mapping) else None,
        "mounted_ket_asset_count": len(mounted_keys),
        "projected_context_asset_count": len(projected_keys),
        "response_capture_asset_count": len(response_keys),
        "listening_audio_asset_count": len(audio_keys),
        "speaking_recording_asset_count": len(recording_keys),
        "m3_m5_contracts_compatible": not any(value in errors for value in ("m3_compatibility_invalid", "m5_compatibility_invalid")),
        "m6_feature_rubric_compatible": bool(response_keys),
        "m10_private_media_registration_compatible": bool(audio_keys or recording_keys),
        "missing_reference_blocks_delivery": False,
        "a2_status": "LOCKED",
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": builder.NEXT_SHORT_STEP,
    }


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--m2-consumer", type=Path, required=True)
    parser.add_argument("--cp05-approved", type=Path, required=True)
    parser.add_argument("--r3f-plan", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    report = validate_artifact(
        _read(args.artifact),
        m2_consumer=_read(args.m2_consumer),
        cp05_approved=_read(args.cp05_approved),
        r3f_plan=_read(args.r3f_plan),
    )
    if args.report:
        cp07d._write_atomic(args.report, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == builder.PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
