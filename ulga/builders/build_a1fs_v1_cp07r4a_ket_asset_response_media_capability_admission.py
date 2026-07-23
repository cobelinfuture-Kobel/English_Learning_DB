#!/usr/bin/env python3
"""Admit explicit M6/M10 capabilities from an R4 private delivery consumer.

The adapter does not invent prompts, answers, rubrics, audio, recordings, or
learner attempts. It reuses M6's authoritative contract derivation over the
already-governed private asset payloads and M10's exact role requirements.
All base and projected asset objects remain unchanged.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp07r4_reference_aware_private_delivery_consumer as r4  # noqa: E402
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6  # noqa: E402
from ulga.builders import cp07d_private_four_skill_delivery_consumer_impl as cp07d  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Metadata-only capability admission derived by existing M6 and M10 contracts over unchanged private assets; no prompt, answer, rubric content, media, learner response, score, mastery, retention, hard graph, lesson selection, or A2 payload is produced."

TASK_ID = "A1FS-V1-CP07F-R4A_KETAssetResponseAndMediaCapabilityAdmission"
SCHEMA_VERSION = "a1fs.v1.cp07f.r4a.ket_asset_response_media_capability_admission.v1"
PASS_STATUS = "PASS_CP07F_R4A_KET_ASSET_RESPONSE_MEDIA_CAPABILITY_ADMISSION_READY"
NEXT_SHORT_STEP = "A1FS-V1-CP07F-R4B_FourSkillResponseAndMediaRuntimeCanary"

DEFAULT_R4 = r4.DEFAULT_OUTPUT
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp07r4a/ket_asset_response_media_capability_admission.private.json"
DEFAULT_REPORT = REPO_ROOT / ".local/a1fs_v1/cp07r4a/ket_asset_response_media_capability_admission.validation.json"

PRODUCTIVE_SPEAKING_ROLES = {"PRD", "XFR", "EVD"}


class R4AAdmissionError(ValueError):
    """Fail-closed R4 source or capability-admission error."""


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise R4AAdmissionError(f"json_object_required:{path}")
    return value


def _verify_r4(consumer: Mapping[str, Any]) -> tuple[Mapping[str, Any], dict[str, Mapping[str, Any]], list[str], list[str]]:
    if consumer.get("cp07r4_task_id") != r4.TASK_ID or consumer.get("cp07r4_schema_version") != r4.SCHEMA_VERSION:
        raise R4AAdmissionError("r4_contract_invalid")
    if consumer.get("cp07r4_validation_status") != r4.PASS_STATUS:
        raise R4AAdmissionError("r4_not_passed")
    if consumer.get("cp07d_stop_reason") != "NONE" or consumer.get("cp07d_errors") != []:
        raise R4AAdmissionError("r4_cp07d_boundary_invalid")
    contract = consumer.get("cp07d_delivery_contract")
    if not isinstance(contract, Mapping):
        raise R4AAdmissionError("r4_delivery_contract_missing")
    if contract.get("selected_skill") not in r4.SKILLS or contract.get("selected_level") not in {"A1", "A1+"}:
        raise R4AAdmissionError("r4_selected_scope_invalid")
    if contract.get("missing_reference_blocks_delivery") is not False or contract.get("a2_payload_included") is not False:
        raise R4AAdmissionError("r4_delivery_boundary_invalid")
    asset_rows = consumer.get("asset_records")
    if not isinstance(asset_rows, list):
        raise R4AAdmissionError("r4_asset_records_missing")
    asset_index = {
        str(row.get("asset_key") or ""): row
        for row in asset_rows
        if isinstance(row, Mapping) and str(row.get("asset_key") or "")
    }
    if len(asset_index) != len(asset_rows):
        raise R4AAdmissionError("r4_asset_identity_missing_or_duplicate")
    mounted = contract.get("mounted_ket_asset_keys")
    projected = contract.get("projected_asset_keys")
    if not isinstance(mounted, list) or not mounted or not isinstance(projected, list):
        raise R4AAdmissionError("r4_selected_asset_lists_invalid")
    mounted_keys = sorted(str(value) for value in mounted)
    projected_keys = sorted(str(value) for value in projected)
    if set(mounted_keys) & set(projected_keys):
        raise R4AAdmissionError("r4_mounted_projected_asset_overlap")
    selected_lesson_id = str(contract.get("selected_lesson_id") or "")
    selected_skill = str(contract.get("selected_skill") or "")
    selected_level = str(contract.get("selected_level") or "")
    for key in mounted_keys + projected_keys:
        asset = asset_index.get(key)
        if asset is None:
            raise R4AAdmissionError(f"r4_selected_asset_missing:{key}")
        if (
            asset.get("lesson_id") != selected_lesson_id
            or asset.get("skill") != selected_skill
            or asset.get("level") != selected_level
        ):
            raise R4AAdmissionError(f"r4_selected_asset_partition_drift:{key}")
    return contract, asset_index, mounted_keys, projected_keys


def _response_summary(asset: Mapping[str, Any], *, source_kind: str) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = m6.derive_contract(asset)
    summary = {
        "asset_key": str(contract["asset_key"]),
        "source_kind": source_kind,
        "skill": str(contract["skill"]),
        "role": str(contract["role"]),
        "capture_enabled": bool(contract["capture_enabled"]),
        "response_type": str(contract["response_type"]),
        "scoring_mode": str(contract["scoring_mode"]),
        "human_review_fallback": bool(contract["human_review_fallback"]),
        "accepted_text_count": len(contract.get("accepted_texts", [])),
        "accepted_sequence_count": len(contract.get("accepted_sequence", [])),
        "rubric_criterion_count": len(contract.get("rubric", {})),
        "actual_attempt_completed": False,
    }
    return contract, summary


def build_capability_admission(r4_consumer: Mapping[str, Any]) -> dict[str, Any]:
    delivery, asset_index, mounted_keys, projected_keys = _verify_r4(r4_consumer)
    selected_skill = str(delivery["selected_skill"])
    source_kind_by_key = {
        **{key: "KET_ASSET_BODY" for key in mounted_keys},
        **{key: "OPTIONAL_CONTEXT_PROJECTION" for key in projected_keys},
    }

    response_contracts: list[dict[str, Any]] = []
    response_keys: list[str] = []
    listening_audio_keys: list[str] = []
    speaking_recording_keys: list[str] = []
    media_admissions: list[dict[str, Any]] = []

    for key in mounted_keys + projected_keys:
        asset = asset_index[key]
        derived, summary = _response_summary(asset, source_kind=source_kind_by_key[key])
        response_contracts.append(summary)
        if derived["capture_enabled"]:
            response_keys.append(key)
        if selected_skill == "LISTENING" and asset.get("role") == "AUD":
            listening_audio_keys.append(key)
            media_admissions.append({
                "asset_key": key,
                "source_kind": source_kind_by_key[key],
                "media_kind": "LISTENING_AUDIO",
                "registration_contract_admitted": True,
                "consent_required": False,
                "actual_media_registered": False,
            })
        if (
            selected_skill == "SPEAKING"
            and asset.get("role") in PRODUCTIVE_SPEAKING_ROLES
            and derived["capture_enabled"]
            and derived["scoring_mode"] == "FEATURE_RUBRIC"
        ):
            speaking_recording_keys.append(key)
            media_admissions.append({
                "asset_key": key,
                "source_kind": source_kind_by_key[key],
                "media_kind": "SPEAKING_RECORDING",
                "registration_contract_admitted": True,
                "consent_required": True,
                "actual_media_registered": False,
            })

    response_keys.sort()
    listening_audio_keys.sort()
    speaking_recording_keys.sort()
    response_contracts.sort(key=lambda row: str(row["asset_key"]))
    media_admissions.sort(key=lambda row: (str(row["media_kind"]), str(row["asset_key"])))

    result = copy.deepcopy(dict(r4_consumer))
    contract = result["cp07d_delivery_contract"]
    contract["response_capture_asset_keys"] = response_keys
    contract["listening_audio_asset_keys"] = listening_audio_keys
    contract["speaking_recording_asset_keys"] = speaking_recording_keys
    contract["m6_feature_rubric_compatible"] = bool(response_keys)
    contract["m10_private_media_registration_compatible"] = bool(
        listening_audio_keys or speaking_recording_keys
    )

    result["cp07r4a_task_id"] = TASK_ID
    result["cp07r4a_schema_version"] = SCHEMA_VERSION
    result["cp07r4a_validation_status"] = PASS_STATUS
    result["cp07r4a_source_identity"] = {
        "r4_consumer_sha256": cp07d._digest(r4_consumer),
    }
    result["cp07r4a_capability_admission"] = {
        "authority": {
            "response_contract_derivation": "A1FS_V1_M6_DERIVE_CONTRACT",
            "listening_media_admission": "M10_LISTENING_REQUIRES_AUD_ROLE",
            "speaking_media_admission": "M10_SPEAKING_REQUIRES_PRODUCTIVE_FEATURE_RUBRIC_ATTEMPT",
        },
        "response_contracts": response_contracts,
        "media_admissions": media_admissions,
        "actual_attempt_count": 0,
        "actual_media_registration_count": 0,
        "automatic_speaking_score_enabled": False,
    }
    result["counts"]["cp07r4a_response_contract_count"] = len(response_contracts)
    result["counts"]["cp07r4a_response_capture_asset_count"] = len(response_keys)
    result["counts"]["cp07r4a_listening_audio_admission_count"] = len(listening_audio_keys)
    result["counts"]["cp07r4a_speaking_recording_admission_count"] = len(speaking_recording_keys)
    result["cp07r4_capability_gaps"] = {
        "response_capture_contract_missing": not bool(response_keys),
        "listening_audio_registration_contract_missing": selected_skill == "LISTENING" and not bool(listening_audio_keys),
        "speaking_recording_contract_missing": selected_skill == "SPEAKING" and not bool(speaking_recording_keys),
        "optional_context_not_projected": not bool(projected_keys),
    }
    result["cp07r4a_claim_boundaries"] = {
        "asset_payload_mutated": False,
        "prompt_or_answer_created": False,
        "real_learner_attempt_claimed": False,
        "real_listening_audio_claimed": False,
        "real_speaking_recording_claimed": False,
        "automatic_speaking_score_claimed": False,
        "mastery_or_retention_claimed": False,
        "a2_a2plus_in_scope": False,
    }
    result["cp07d_next_short_step"] = NEXT_SHORT_STEP
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r4-consumer", type=Path, default=DEFAULT_R4)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        source = _read(args.r4_consumer)
        artifact = build_capability_admission(source)
        from ulga.validators import validate_a1fs_v1_cp07r4a_ket_asset_response_media_capability_admission as validator
        report = validator.validate_artifact(artifact, r4_consumer=source)
        cp07d._write_atomic(args.output, artifact, private=True)
        cp07d._write_atomic(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (R4AAdmissionError, m6.ResponseEvidenceError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
