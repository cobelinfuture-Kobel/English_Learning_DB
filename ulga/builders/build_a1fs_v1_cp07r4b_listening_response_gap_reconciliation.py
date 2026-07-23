#!/usr/bin/env python3
"""Reconcile the remaining selected-listening response capability gap.

A CHK adapter is materialized only when a non-AUD selected private asset already
contains both an explicit scoring contract and an exact prompt. The adapter
copies those source fields without rewriting the source asset. Prompt-only,
implicit-answer, explicitly disabled, AUD-bound, ambiguous, or incomplete
candidates remain classified and fail closed for response-capability claims.
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

from ulga.builders import build_a1fs_v1_cp07r4a_ket_asset_response_media_capability_admission as r4a  # noqa: E402
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6  # noqa: E402
from ulga.builders import cp07d_private_four_skill_delivery_consumer_impl as cp07d  # noqa: E402

A1FS_CONTENT_POLICY_MODE = "POLICY_BOUND"

TASK_ID = "A1FS-V1-CP07F-R4B_ListeningResponseGapReconciliation"
SCHEMA_VERSION = "a1fs.v1.cp07f.r4b.listening_response_gap_reconciliation.v1"
PASS_STATUS = "PASS_CP07F_R4B_LISTENING_RESPONSE_GAP_RECONCILIATION_READY"
NEXT_RESOLVED_STEP = "A1FS-V1-CP07F-R4C_RealFourSkillAttemptAndMediaEvidenceCanary"
NEXT_EVIDENCE_STEP = "A1FS-V1-CP07F-R4C_ListeningExplicitResponseEvidenceAdmission"

DEFAULT_R4A = r4a.DEFAULT_OUTPUT
DEFAULT_OUTPUT = REPO_ROOT / ".local/a1fs_v1/cp07r4b/listening_response_gap_reconciliation.private.json"
DEFAULT_REPORT = REPO_ROOT / ".local/a1fs_v1/cp07r4b/listening_response_gap_reconciliation.validation.json"

EXPLICIT_CONTRACT_KEYS = ("private_scoring_contract", "scoring_contract", "answer_contract")
PROMPT_KEYS = {"question", "prompt", "launch_cue", "instruction"}


class R4BReconciliationError(ValueError):
    """Fail-closed R4A source or adapter reconciliation error."""


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise R4BReconciliationError(f"json_object_required:{path}")
    return value


def _verify_source(source: Mapping[str, Any]) -> tuple[Mapping[str, Any], dict[str, Mapping[str, Any]], list[str]]:
    if source.get("cp07r4a_task_id") != r4a.TASK_ID or source.get("cp07r4a_schema_version") != r4a.SCHEMA_VERSION:
        raise R4BReconciliationError("r4a_contract_invalid")
    if source.get("cp07r4a_validation_status") != r4a.PASS_STATUS:
        raise R4BReconciliationError("r4a_not_passed")
    if source.get("cp07d_stop_reason") != "NONE" or source.get("cp07d_errors") != []:
        raise R4BReconciliationError("r4a_cp07d_boundary_invalid")
    delivery = source.get("cp07d_delivery_contract")
    if not isinstance(delivery, Mapping):
        raise R4BReconciliationError("r4a_delivery_contract_missing")
    if delivery.get("selected_level") not in {"A1", "A1+"} or delivery.get("a2_payload_included") is not False:
        raise R4BReconciliationError("r4a_scope_invalid")
    rows = source.get("asset_records")
    if not isinstance(rows, list):
        raise R4BReconciliationError("r4a_asset_records_missing")
    index = {
        str(row.get("asset_key") or ""): row
        for row in rows
        if isinstance(row, Mapping) and str(row.get("asset_key") or "")
    }
    if len(index) != len(rows):
        raise R4BReconciliationError("r4a_asset_identity_missing_or_duplicate")
    mounted = delivery.get("mounted_ket_asset_keys")
    projected = delivery.get("projected_asset_keys")
    if not isinstance(mounted, list) or not isinstance(projected, list) or not mounted:
        raise R4BReconciliationError("r4a_selected_asset_lists_invalid")
    selected = sorted(str(value) for value in list(mounted) + list(projected))
    if len(selected) != len(set(selected)) or any(key not in index for key in selected):
        raise R4BReconciliationError("r4a_selected_asset_identity_invalid")
    return delivery, index, selected


def _explicit_contract(payload: Mapping[str, Any]) -> tuple[str | None, Mapping[str, Any] | None]:
    for key in EXPLICIT_CONTRACT_KEYS:
        value = payload.get(key)
        if isinstance(value, Mapping):
            return key, value
    return None, None


def _prompts(payload: Mapping[str, Any]) -> list[str]:
    result = []
    for value in m6.walk(payload, PROMPT_KEYS):
        if isinstance(value, str) and value.strip():
            result.append(value.strip())
    return list(dict.fromkeys(result))


def _candidate_adapter(source_asset: Mapping[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    key = str(source_asset["asset_key"])
    role = str(source_asset["role"])
    payload = source_asset.get("payload")
    if not isinstance(payload, Mapping):
        raise R4BReconciliationError(f"asset_payload_invalid:{key}")
    contract_key, explicit = _explicit_contract(payload)
    prompts = _prompts(payload)
    original = m6.derive_contract(source_asset)
    explicit_disabled = payload.get("response_capture_enabled") is False

    reason = "NOT_ELIGIBLE"
    adapter = None
    if original["capture_enabled"]:
        reason = "ALREADY_CAPTURE_ENABLED"
    elif role == "AUD":
        reason = "AUD_ASSET_NOT_RESPONSE_ADAPTER_SOURCE"
    elif explicit_disabled:
        reason = "SOURCE_EXPLICITLY_DISABLES_RESPONSE_CAPTURE"
    elif explicit is None:
        reason = "EXPLICIT_SCORING_CONTRACT_MISSING"
    elif not prompts:
        reason = "EXACT_PROMPT_MISSING"
    else:
        adapter_payload = {
            "learner_instruction": prompts[0],
            "private_scoring_contract": copy.deepcopy(dict(explicit)),
            "response_capture_enabled": True,
            "source_lineage": {
                "source_asset_key": key,
                "source_content_digest": str(source_asset.get("content_digest") or ""),
                "source_contract_field": str(contract_key),
                "derivation": "EXACT_PROMPT_AND_EXPLICIT_SCORING_CONTRACT_COPY",
            },
        }
        adapter_key = f"CP07R4B:{cp07d._digest({'source': key, 'payload': adapter_payload})[:24]}"
        adapter = {
            "asset_id": adapter_key,
            "asset_key": adapter_key,
            "lesson_id": str(source_asset["lesson_id"]),
            "skill": "LISTENING",
            "level": str(source_asset["level"]),
            "role": "CHK",
            "payload": adapter_payload,
            "content_digest": cp07d._digest(adapter_payload),
            "release_scope": "PRIVATE_INTERNAL_D0",
        }
        derived_adapter = m6.derive_contract(adapter)
        if not derived_adapter["capture_enabled"]:
            adapter = None
            reason = "EXPLICIT_CONTRACT_NOT_M6_CAPTUREABLE"
        else:
            reason = "AUTO_ADAPTER_ELIGIBLE"

    classification = {
        "asset_key": key,
        "role": role,
        "existing_capture_enabled": bool(original["capture_enabled"]),
        "existing_scoring_mode": str(original["scoring_mode"]),
        "explicit_contract_present": explicit is not None,
        "explicit_contract_field": contract_key,
        "prompt_count": len(prompts),
        "response_capture_explicitly_disabled": explicit_disabled,
        "auto_adapter_eligible": adapter is not None,
        "reason_code": reason,
    }
    return adapter, classification


def _response_summary(asset: Mapping[str, Any], source_kind: str) -> dict[str, Any]:
    contract = m6.derive_contract(asset)
    return {
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


def build_reconciliation(r4a_consumer: Mapping[str, Any]) -> dict[str, Any]:
    delivery, index, selected_keys = _verify_source(r4a_consumer)
    skill = str(delivery["selected_skill"])
    result = copy.deepcopy(dict(r4a_consumer))
    classifications: list[dict[str, Any]] = []
    adapters: list[dict[str, Any]] = []

    if skill == "LISTENING" and not delivery.get("response_capture_asset_keys"):
        for key in selected_keys:
            adapter, classification = _candidate_adapter(index[key])
            classifications.append(classification)
            if adapter is not None:
                adapters.append(adapter)

    if adapters:
        existing = {str(row["asset_key"]) for row in result["asset_records"]}
        if any(str(row["asset_key"]) in existing for row in adapters):
            raise R4BReconciliationError("adapter_asset_key_collision")
        result["asset_records"].extend(copy.deepcopy(adapters))
        lesson_id = str(delivery["selected_lesson_id"])
        catalog = next(
            (row for row in result["lesson_catalog"] if row.get("lesson_id") == lesson_id),
            None,
        )
        if catalog is None:
            raise R4BReconciliationError("selected_lesson_catalog_missing")
        adapter_keys = sorted(str(row["asset_key"]) for row in adapters)
        catalog["asset_keys"] = list(catalog["asset_keys"]) + adapter_keys
        catalog["roles"] = list(dict.fromkeys(list(catalog["roles"]) + ["CHK"]))
        result["counts"]["asset_record_count"] = len(result["asset_records"])

        response_keys = sorted(
            str(row["asset_key"])
            for row in result["asset_records"]
            if row.get("lesson_id") == lesson_id and m6.derive_contract(row)["capture_enabled"]
        )
        result["cp07d_delivery_contract"]["response_capture_asset_keys"] = response_keys
        result["cp07d_delivery_contract"]["m6_feature_rubric_compatible"] = bool(response_keys)
        admission = result["cp07r4a_capability_admission"]
        admission["response_contracts"].extend(
            _response_summary(row, "R4B_EXACT_SOURCE_ADAPTER") for row in adapters
        )
        admission["response_contracts"].sort(key=lambda row: str(row["asset_key"]))
        result["counts"]["cp07r4a_response_contract_count"] = len(admission["response_contracts"])
        result["counts"]["cp07r4a_response_capture_asset_count"] = len(response_keys)
        result["cp07r4_capability_gaps"]["response_capture_contract_missing"] = not bool(response_keys)
        remediation_status = "AUTO_REMEDIATED_FROM_EXPLICIT_SOURCE_CONTRACT"
    elif skill != "LISTENING" or delivery.get("response_capture_asset_keys"):
        remediation_status = "NO_REMEDIATION_NEEDED"
    else:
        remediation_status = "BLOCKED_EXPLICIT_SCORING_EVIDENCE_REQUIRED"

    result["cp07r4b_task_id"] = TASK_ID
    result["cp07r4b_schema_version"] = SCHEMA_VERSION
    result["cp07r4b_validation_status"] = PASS_STATUS
    result["cp07r4b_source_identity"] = {
        "r4a_consumer_sha256": cp07d._digest(r4a_consumer),
    }
    result["cp07r4b_reconciliation"] = {
        "selected_skill": skill,
        "remediation_status": remediation_status,
        "safe_gap_classifications": sorted(classifications, key=lambda row: str(row["asset_key"])),
        "adapter_asset_keys": sorted(str(row["asset_key"]) for row in adapters),
        "adapter_count": len(adapters),
        "source_asset_payloads_mutated": False,
        "prompt_or_scoring_content_invented": False,
        "operator_evidence_required": remediation_status == "BLOCKED_EXPLICIT_SCORING_EVIDENCE_REQUIRED",
    }
    result["cp07r4b_claim_boundaries"] = {
        "source_asset_payload_mutated": False,
        "new_prompt_invented": False,
        "new_answer_invented": False,
        "new_rubric_invented": False,
        "real_learner_attempt_claimed": False,
        "real_media_claimed": False,
        "mastery_or_retention_claimed": False,
        "a2_a2plus_in_scope": False,
    }
    result["cp07d_next_short_step"] = (
        NEXT_EVIDENCE_STEP
        if remediation_status == "BLOCKED_EXPLICIT_SCORING_EVIDENCE_REQUIRED"
        else NEXT_RESOLVED_STEP
    )
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r4a-consumer", type=Path, default=DEFAULT_R4A)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        source = _read(args.r4a_consumer)
        artifact = build_reconciliation(source)
        from ulga.validators import validate_a1fs_v1_cp07r4b_listening_response_gap_reconciliation as validator
        report = validator.validate_artifact(artifact, r4a_consumer=source)
        cp07d._write_atomic(args.output, artifact, private=True)
        cp07d._write_atomic(args.report, report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if report["validation_status"] == PASS_STATUS else 1
    except (R4BReconciliationError, m6.ResponseEvidenceError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
