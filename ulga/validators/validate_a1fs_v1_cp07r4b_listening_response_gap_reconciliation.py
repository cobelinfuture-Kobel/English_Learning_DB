#!/usr/bin/env python3
"""Validate R4B listening response gap reconciliation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_cp07r4b_listening_response_gap_reconciliation as builder
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import cp07d_private_four_skill_delivery_consumer_impl as cp07d

FAIL_STATUS = "FAIL_CP07F_R4B_LISTENING_RESPONSE_GAP_RECONCILIATION"


def _append(errors: list[str], condition: bool, message: str) -> None:
    if not condition and message not in errors:
        errors.append(message)


def validate_artifact(
    artifact: Mapping[str, Any],
    *,
    r4a_consumer: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    try:
        rebuilt = builder.build_reconciliation(r4a_consumer)
    except Exception as exc:
        rebuilt = None
        errors.append(f"deterministic_rebuild_failed:{type(exc).__name__}:{exc}")

    _append(errors, artifact.get("cp07r4b_task_id") == builder.TASK_ID, "task_id_invalid")
    _append(errors, artifact.get("cp07r4b_schema_version") == builder.SCHEMA_VERSION, "schema_version_invalid")
    _append(errors, artifact.get("cp07r4b_validation_status") == builder.PASS_STATUS, "validation_status_invalid")
    source_identity = artifact.get("cp07r4b_source_identity")
    _append(errors, isinstance(source_identity, Mapping), "source_identity_missing")
    if isinstance(source_identity, Mapping):
        _append(errors, source_identity.get("r4a_consumer_sha256") == cp07d._digest(r4a_consumer), "source_binding_invalid")

    source_assets = {
        str(row.get("asset_key") or ""): row
        for row in r4a_consumer.get("asset_records", [])
        if isinstance(row, Mapping)
    }
    result_assets = {
        str(row.get("asset_key") or ""): row
        for row in artifact.get("asset_records", [])
        if isinstance(row, Mapping)
    }
    _append(errors, len(result_assets) == len(artifact.get("asset_records", [])), "result_asset_identity_invalid")
    for key, row in source_assets.items():
        _append(errors, result_assets.get(key) == row, f"source_asset_drift:{key}")

    reconciliation = artifact.get("cp07r4b_reconciliation")
    _append(errors, isinstance(reconciliation, Mapping), "reconciliation_missing")
    adapter_keys: list[str] = []
    remediation_status = None
    if isinstance(reconciliation, Mapping):
        remediation_status = reconciliation.get("remediation_status")
        _append(
            errors,
            remediation_status in {
                "AUTO_REMEDIATED_FROM_EXPLICIT_SOURCE_CONTRACT",
                "NO_REMEDIATION_NEEDED",
                "BLOCKED_EXPLICIT_SCORING_EVIDENCE_REQUIRED",
            },
            "remediation_status_invalid",
        )
        _append(errors, reconciliation.get("source_asset_payloads_mutated") is False, "source_mutation_claim_invalid")
        _append(errors, reconciliation.get("prompt_or_scoring_content_invented") is False, "content_invention_claim_invalid")
        adapter_keys = list(reconciliation.get("adapter_asset_keys", [])) if isinstance(reconciliation.get("adapter_asset_keys"), list) else []
        _append(errors, reconciliation.get("adapter_count") == len(adapter_keys), "adapter_count_invalid")
        _append(
            errors,
            reconciliation.get("operator_evidence_required") is (remediation_status == "BLOCKED_EXPLICIT_SCORING_EVIDENCE_REQUIRED"),
            "operator_evidence_flag_invalid",
        )

    delivery = artifact.get("cp07d_delivery_contract")
    _append(errors, isinstance(delivery, Mapping), "delivery_contract_missing")
    response_keys: list[str] = []
    if isinstance(delivery, Mapping):
        response_keys = list(delivery.get("response_capture_asset_keys", [])) if isinstance(delivery.get("response_capture_asset_keys"), list) else []
        _append(errors, delivery.get("a2_payload_included") is False, "a2_payload_included")
        _append(errors, delivery.get("real_attempt_completed") is False, "real_attempt_claimed")
        _append(errors, delivery.get("real_media_registered") is False, "real_media_claimed")

    for key in adapter_keys:
        row = result_assets.get(key)
        _append(errors, row is not None, f"adapter_missing:{key}")
        if isinstance(row, Mapping):
            _append(errors, row.get("skill") == "LISTENING", f"adapter_skill_invalid:{key}")
            _append(errors, row.get("role") == "CHK", f"adapter_role_invalid:{key}")
            payload = row.get("payload")
            _append(errors, isinstance(payload, Mapping), f"adapter_payload_invalid:{key}")
            if isinstance(payload, Mapping):
                lineage = payload.get("source_lineage")
                _append(errors, isinstance(lineage, Mapping), f"adapter_lineage_missing:{key}")
                if isinstance(lineage, Mapping):
                    source_key = str(lineage.get("source_asset_key") or "")
                    source = source_assets.get(source_key)
                    _append(errors, source is not None, f"adapter_source_missing:{key}")
                    if isinstance(source, Mapping):
                        source_payload = source.get("payload")
                        field = str(lineage.get("source_contract_field") or "")
                        _append(errors, isinstance(source_payload, Mapping), f"adapter_source_payload_invalid:{key}")
                        if isinstance(source_payload, Mapping):
                            _append(errors, payload.get("private_scoring_contract") == source_payload.get(field), f"adapter_contract_not_exact_copy:{key}")
                            prompts = builder._prompts(source_payload)
                            _append(errors, bool(prompts) and payload.get("learner_instruction") == prompts[0], f"adapter_prompt_not_exact_copy:{key}")
            try:
                derived = m6.derive_contract(row)
                _append(errors, derived["capture_enabled"] is True, f"adapter_not_capture_enabled:{key}")
            except Exception as exc:
                errors.append(f"adapter_contract_invalid:{key}:{type(exc).__name__}:{exc}")
        _append(errors, key in response_keys, f"adapter_not_in_response_keys:{key}")

    if remediation_status == "AUTO_REMEDIATED_FROM_EXPLICIT_SOURCE_CONTRACT":
        _append(errors, bool(adapter_keys) and bool(response_keys), "auto_remediation_did_not_resolve_gap")
    if remediation_status == "BLOCKED_EXPLICIT_SCORING_EVIDENCE_REQUIRED":
        _append(errors, not adapter_keys and not response_keys, "blocked_status_has_adapter_or_capture")
    if remediation_status == "NO_REMEDIATION_NEEDED":
        _append(errors, not adapter_keys, "unnecessary_adapter_created")

    boundaries = artifact.get("cp07r4b_claim_boundaries")
    _append(errors, isinstance(boundaries, Mapping), "claim_boundaries_missing")
    if isinstance(boundaries, Mapping):
        for key in (
            "source_asset_payload_mutated",
            "new_prompt_invented",
            "new_answer_invented",
            "new_rubric_invented",
            "real_learner_attempt_claimed",
            "real_media_claimed",
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
        "remediation_status": remediation_status,
        "adapter_count": len(adapter_keys),
        "listening_response_capture_count": len(response_keys),
        "operator_evidence_required": remediation_status == "BLOCKED_EXPLICIT_SCORING_EVIDENCE_REQUIRED",
        "source_asset_payloads_unchanged": not any(error.startswith("source_asset_drift:") for error in errors),
        "a2_status": "LOCKED",
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILED",
        "next_short_step": artifact.get("cp07d_next_short_step"),
    }


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"json_object_required:{path}")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--r4a-consumer", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    report = validate_artifact(_read(args.artifact), r4a_consumer=_read(args.r4a_consumer))
    if args.report:
        cp07d._write_atomic(args.report, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["validation_status"] == builder.PASS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main())
