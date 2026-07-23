#!/usr/bin/env python3
"""Validate explicit R4A response and media capability admission."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_cp07r4a_ket_asset_response_media_capability_admission as builder
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import cp07d_private_four_skill_delivery_consumer_impl as cp07d

FAIL_STATUS = "FAIL_CP07F_R4A_KET_ASSET_RESPONSE_MEDIA_CAPABILITY_ADMISSION"
FORBIDDEN_ADMISSION_KEYS = {
    "prompt",
    "accepted_texts",
    "accepted_sequence",
    "rubric",
    "answer",
    "correct_answer",
    "source_text",
    "transcript",
}


def _append(errors: list[str], condition: bool, message: str) -> None:
    if not condition and message not in errors:
        errors.append(message)


def _walk_keys(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            found.add(str(key).casefold())
            found.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_walk_keys(child))
    return found


def validate_artifact(
    artifact: Mapping[str, Any],
    *,
    r4_consumer: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        rebuilt = builder.build_capability_admission(r4_consumer)
    except Exception as exc:  # fail-closed report boundary
        rebuilt = None
        errors.append(f"deterministic_rebuild_failed:{type(exc).__name__}:{exc}")

    _append(errors, artifact.get("cp07r4a_task_id") == builder.TASK_ID, "task_id_invalid")
    _append(errors, artifact.get("cp07r4a_schema_version") == builder.SCHEMA_VERSION, "schema_version_invalid")
    _append(errors, artifact.get("cp07r4a_validation_status") == builder.PASS_STATUS, "validation_status_invalid")
    _append(errors, artifact.get("asset_records") == r4_consumer.get("asset_records"), "asset_records_mutated")
    _append(errors, artifact.get("lesson_catalog") == r4_consumer.get("lesson_catalog"), "lesson_catalog_mutated")

    source_identity = artifact.get("cp07r4a_source_identity")
    _append(errors, isinstance(source_identity, Mapping), "source_identity_missing")
    if isinstance(source_identity, Mapping):
        _append(
            errors,
            source_identity.get("r4_consumer_sha256") == cp07d._digest(r4_consumer),
            "r4_source_binding_invalid",
        )

    source_contract = r4_consumer.get("cp07d_delivery_contract")
    contract = artifact.get("cp07d_delivery_contract")
    admission = artifact.get("cp07r4a_capability_admission")
    gaps = artifact.get("cp07r4_capability_gaps")
    _append(errors, isinstance(source_contract, Mapping), "source_delivery_contract_missing")
    _append(errors, isinstance(contract, Mapping), "delivery_contract_missing")
    _append(errors, isinstance(admission, Mapping), "admission_contract_missing")
    _append(errors, isinstance(gaps, Mapping), "capability_gaps_missing")

    expected_response_keys: list[str] = []
    expected_audio_keys: list[str] = []
    expected_recording_keys: list[str] = []
    expected_summaries: list[dict[str, Any]] = []
    expected_media: list[dict[str, Any]] = []

    asset_index = {
        str(row.get("asset_key") or ""): row
        for row in r4_consumer.get("asset_records", [])
        if isinstance(row, Mapping)
    }
    if isinstance(source_contract, Mapping):
        mounted = list(source_contract.get("mounted_ket_asset_keys", []))
        projected = list(source_contract.get("projected_asset_keys", []))
        selected_skill = str(source_contract.get("selected_skill") or "")
        source_kind_by_key = {
            **{str(key): "KET_ASSET_BODY" for key in mounted},
            **{str(key): "OPTIONAL_CONTEXT_PROJECTION" for key in projected},
        }
        for key in sorted(source_kind_by_key):
            asset = asset_index.get(key)
            if asset is None:
                errors.append(f"source_selected_asset_missing:{key}")
                continue
            try:
                derived = m6.derive_contract(asset)
            except Exception as exc:
                errors.append(f"source_contract_derivation_failed:{key}:{type(exc).__name__}:{exc}")
                continue
            expected_summaries.append({
                "asset_key": key,
                "source_kind": source_kind_by_key[key],
                "skill": str(derived["skill"]),
                "role": str(derived["role"]),
                "capture_enabled": bool(derived["capture_enabled"]),
                "response_type": str(derived["response_type"]),
                "scoring_mode": str(derived["scoring_mode"]),
                "human_review_fallback": bool(derived["human_review_fallback"]),
                "accepted_text_count": len(derived.get("accepted_texts", [])),
                "accepted_sequence_count": len(derived.get("accepted_sequence", [])),
                "rubric_criterion_count": len(derived.get("rubric", {})),
                "actual_attempt_completed": False,
            })
            if derived["capture_enabled"]:
                expected_response_keys.append(key)
            if selected_skill == "LISTENING" and asset.get("role") == "AUD":
                expected_audio_keys.append(key)
                expected_media.append({
                    "asset_key": key,
                    "source_kind": source_kind_by_key[key],
                    "media_kind": "LISTENING_AUDIO",
                    "registration_contract_admitted": True,
                    "consent_required": False,
                    "actual_media_registered": False,
                })
            if (
                selected_skill == "SPEAKING"
                and asset.get("role") in builder.PRODUCTIVE_SPEAKING_ROLES
                and derived["capture_enabled"]
                and derived["scoring_mode"] == "FEATURE_RUBRIC"
            ):
                expected_recording_keys.append(key)
                expected_media.append({
                    "asset_key": key,
                    "source_kind": source_kind_by_key[key],
                    "media_kind": "SPEAKING_RECORDING",
                    "registration_contract_admitted": True,
                    "consent_required": True,
                    "actual_media_registered": False,
                })

    expected_response_keys.sort()
    expected_audio_keys.sort()
    expected_recording_keys.sort()
    expected_summaries.sort(key=lambda row: str(row["asset_key"]))
    expected_media.sort(key=lambda row: (str(row["media_kind"]), str(row["asset_key"])))

    response_keys: list[str] = []
    audio_keys: list[str] = []
    recording_keys: list[str] = []
    if isinstance(contract, Mapping):
        response_keys = sorted(str(value) for value in contract.get("response_capture_asset_keys", []))
        audio_keys = sorted(str(value) for value in contract.get("listening_audio_asset_keys", []))
        recording_keys = sorted(str(value) for value in contract.get("speaking_recording_asset_keys", []))
        _append(errors, response_keys == expected_response_keys, "response_capture_admission_invalid")
        _append(errors, audio_keys == expected_audio_keys, "listening_audio_admission_invalid")
        _append(errors, recording_keys == expected_recording_keys, "speaking_recording_admission_invalid")
        _append(errors, contract.get("m6_feature_rubric_compatible") is bool(response_keys), "m6_capability_flag_invalid")
        _append(
            errors,
            contract.get("m10_private_media_registration_compatible") is bool(audio_keys or recording_keys),
            "m10_capability_flag_invalid",
        )
        for key, value in source_contract.items() if isinstance(source_contract, Mapping) else []:
            if key not in {
                "response_capture_asset_keys",
                "listening_audio_asset_keys",
                "speaking_recording_asset_keys",
                "m6_feature_rubric_compatible",
                "m10_private_media_registration_compatible",
            }:
                _append(errors, contract.get(key) == value, f"r4_delivery_contract_drift:{key}")

    if isinstance(admission, Mapping):
        _append(errors, admission.get("response_contracts") == expected_summaries, "response_contract_summary_invalid")
        _append(errors, admission.get("media_admissions") == expected_media, "media_admission_summary_invalid")
        _append(errors, admission.get("actual_attempt_count") == 0, "actual_attempt_claimed")
        _append(errors, admission.get("actual_media_registration_count") == 0, "actual_media_claimed")
        _append(errors, admission.get("automatic_speaking_score_enabled") is False, "automatic_speaking_score_claimed")
        found_keys = _walk_keys(admission)
        for forbidden in FORBIDDEN_ADMISSION_KEYS:
            _append(errors, forbidden not in found_keys, f"forbidden_admission_content_key:{forbidden}")

    if isinstance(gaps, Mapping) and isinstance(contract, Mapping):
        selected_skill = str(contract.get("selected_skill") or "")
        _append(errors, gaps.get("response_capture_contract_missing") is (not bool(response_keys)), "response_gap_invalid")
        _append(
            errors,
            gaps.get("listening_audio_registration_contract_missing")
            is (selected_skill == "LISTENING" and not bool(audio_keys)),
            "listening_audio_gap_invalid",
        )
        _append(
            errors,
            gaps.get("speaking_recording_contract_missing")
            is (selected_skill == "SPEAKING" and not bool(recording_keys)),
            "speaking_recording_gap_invalid",
        )

    counts = artifact.get("counts")
    _append(errors, isinstance(counts, Mapping), "counts_missing")
    if isinstance(counts, Mapping):
        _append(errors, counts.get("cp07r4a_response_contract_count") == len(expected_summaries), "response_contract_count_invalid")
        _append(errors, counts.get("cp07r4a_response_capture_asset_count") == len(response_keys), "response_capture_count_invalid")
        _append(errors, counts.get("cp07r4a_listening_audio_admission_count") == len(audio_keys), "listening_audio_count_invalid")
        _append(errors, counts.get("cp07r4a_speaking_recording_admission_count") == len(recording_keys), "speaking_recording_count_invalid")

    boundaries = artifact.get("cp07r4a_claim_boundaries")
    _append(errors, isinstance(boundaries, Mapping), "claim_boundaries_missing")
    if isinstance(boundaries, Mapping):
        for key in (
            "asset_payload_mutated",
            "prompt_or_answer_created",
            "real_learner_attempt_claimed",
            "real_listening_audio_claimed",
            "real_speaking_recording_claimed",
            "automatic_speaking_score_claimed",
            "mastery_or_retention_claimed",
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
        "response_contract_count": len(expected_summaries),
        "response_capture_asset_count": len(response_keys),
        "listening_audio_admission_count": len(audio_keys),
        "speaking_recording_admission_count": len(recording_keys),
        "asset_payloads_unchanged": artifact.get("asset_records") == r4_consumer.get("asset_records"),
        "actual_attempt_count": 0,
        "actual_media_registration_count": 0,
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
    parser.add_argument("--r4-consumer", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    report = validate_artifact(_read(args.artifact), r4_consumer=_read(args.r4_consumer))
    if args.report:
        cp07d._write_atomic(args.report, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == builder.PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
