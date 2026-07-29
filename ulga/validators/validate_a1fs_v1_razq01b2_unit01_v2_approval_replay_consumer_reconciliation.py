#!/usr/bin/env python3
"""Validate Unit01 v2 approval, replay-consumer reconciliation, and capacity delta."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_razq01b2_unit01_v2_approval_replay_consumer_reconciliation as reconciliation

VALIDATOR_ID = "A1FS_V1_RAZQ01B2_UNIT01_V2_APPROVAL_REPLAY_CONSUMER_RECONCILIATION_VALIDATOR"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01B2_UNIT01_V2_APPROVAL_REPLAY_CONSUMER_RECONCILIATION_VALIDATION"


class ReconciliationValidationError(ValueError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ReconciliationValidationError(code)


def validate_approval(contract: Mapping[str, Any], approval: Mapping[str, Any]) -> dict[str, Any]:
    summary = reconciliation.verify_operator_approval(contract, approval)
    _require(summary["operator_approval_verified"] is True, "operator_approval_not_verified")
    _require(summary["approved_dimension_count"] == 7, "approved_dimension_count_invalid")
    _require(summary["legacy_contract_superseded"] is True, "legacy_contract_not_superseded")
    _require(
        approval.get("decision_source_text")
        == "Unit01V2ApprovalReplayConsumerReconciliation",
        "decision_source_text_invalid",
    )
    _require(
        approval.get("supersedes_contract_sha256")
        == reconciliation.LEGACY_APPROVED_CONTRACT_SHA256,
        "superseded_contract_digest_invalid",
    )
    _require(not any(approval.get("boundaries", {}).values()), "approval_boundary_invalid")
    return summary


def validate_report(
    report: Mapping[str, Any],
    contract: Mapping[str, Any],
    approval: Mapping[str, Any],
    *,
    require_baseline: bool = False,
) -> dict[str, Any]:
    approval_summary = validate_approval(contract, approval)
    _require(report.get("schema_version") == reconciliation.SCHEMA_VERSION, "report_schema_invalid")
    _require(report.get("task_id") == reconciliation.TASK_ID, "report_task_id_invalid")
    _require(report.get("status") == reconciliation.PASS_STATUS, "report_status_invalid")
    scope = report.get("scope", {})
    _require(scope.get("allowed_units") == ["GRAMMAR_ARTICLES_BASIC"], "report_unit_scope_invalid")
    _require(scope.get("blocked_units") == "UNIT_02_TO_UNIT_24", "report_blocked_unit_scope_invalid")
    _require(scope.get("canonical_promotion") is False, "canonical_promotion_forbidden")
    _require(scope.get("learner_facing_content_write") is False, "learner_content_write_forbidden")
    _require(
        report.get("inputs", {}).get("approved_contract_sha256")
        == reconciliation.APPROVED_CONTRACT_SHA256,
        "report_contract_digest_invalid",
    )
    profile = report.get("unit", {}).get("unit_profile", {})
    _require(profile.get("unit_id") == "GRAMMAR_ARTICLES_BASIC", "unit_profile_invalid")
    _require(
        "UNIT01_OPERATOR_APPROVED_CONTENT_CONTRACT_V2"
        in profile.get("authority_sources", []),
        "v2_contract_authority_missing",
    )
    adjective_ids = {
        "vocabulary:big:v_1389",
        "vocabulary:blue:v_1396",
        "vocabulary:new:v_6046",
        "vocabulary:old:v_6073",
        "vocabulary:red:v_7741",
        "vocabulary:small:v_9335",
    }
    _require(
        adjective_ids <= set(profile.get("target_evp_sense_ids", [])),
        "active_adjective_authority_missing",
    )
    _require(
        "EVP_CHUNK_000054" not in profile.get("target_chunk_ids", []),
        "ice_cream_direct_use_not_blocked",
    )
    validation = report.get("validation", {})
    for key in (
        "operator_approval_verified",
        "contract_profile_overlay_applied",
        "contract_material_gate_applied",
        "semantic_group_lineage_recovery_applied",
        "windowed_filter_applied",
        "unit01_v2_contract_applied",
        "article_sound_gate_applied",
        "countability_sensitive_chunk_gate_applied",
        "legacy_contract_superseded",
    ):
        _require(validation.get(key) is True, f"validation_gate_missing:{key}")
    _require(validation.get("active_noun_count") == 16, "active_noun_count_invalid")
    _require(validation.get("active_adjective_count") == 6, "active_adjective_count_invalid")
    _require(validation.get("active_memorization_count") == 22, "active_memorization_count_invalid")
    _require(validation.get("canonical_content_modified") is False, "canonical_content_modified")
    _require(validation.get("unit02_to_unit24_modified") is False, "other_units_modified")
    _require(validation.get("a2_unlocked") is False, "a2_unlocked")
    _require(
        validation.get("listening_product_boundary")
        == "DEFERRED_NO_LISTENING_LESSON_IN_UNIT01_RUNTIME",
        "listening_boundary_invalid",
    )
    delta = report.get("capacity_delta", {})
    _require(
        isinstance(delta.get("current_v2") or delta.get("v2"), Mapping),
        "v2_capacity_snapshot_missing",
    )
    if require_baseline:
        _require(delta.get("baseline_supplied") is True, "v1_baseline_required")
        _require(
            delta.get("baseline_contract_sha256")
            == reconciliation.LEGACY_APPROVED_CONTRACT_SHA256,
            "v1_baseline_digest_invalid",
        )
        _require(isinstance(delta.get("delta_v2_minus_v1"), Mapping), "capacity_delta_missing")
    _require(
        report.get("next_short_step") == reconciliation.POST_REPLAY_NEXT_SHORT_STEP,
        "next_short_step_invalid",
    )
    return {
        "validator_id": VALIDATOR_ID,
        "validation_status": PASS_STATUS,
        "error_count": 0,
        "records_scanned": int(report.get("records_scanned") or 0),
        "approved_contract_sha256": approval_summary["approved_contract_sha256"],
        "unit_id": "GRAMMAR_ARTICLES_BASIC",
        "baseline_supplied": bool(delta.get("baseline_supplied")),
        "next_short_step": reconciliation.POST_REPLAY_NEXT_SHORT_STEP,
    }


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReconciliationValidationError(f"unreadable:{path}:{exc}") from exc
    _require(isinstance(value, dict), f"object_required:{path}")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=reconciliation.DEFAULT_CONTRACT)
    parser.add_argument("--approval", type=Path, default=reconciliation.DEFAULT_APPROVAL)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--require-baseline", action="store_true")
    args = parser.parse_args(argv)
    try:
        contract, approval = _load(args.contract), _load(args.approval)
        if args.report is None:
            result = {
                "validation_status": PASS_STATUS,
                **validate_approval(contract, approval),
            }
        else:
            result = validate_report(
                _load(args.report),
                contract,
                approval,
                require_baseline=args.require_baseline,
            )
    except (
        ReconciliationValidationError,
        reconciliation.replay.ReplayError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        print(
            "STATUS=FAIL_A1FS_V1_RAZQ01B2_UNIT01_V2_APPROVAL_"
            "REPLAY_CONSUMER_RECONCILIATION_VALIDATION"
        )
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={result['validation_status']}")
    print(f"APPROVED_CONTRACT_SHA256={result['approved_contract_sha256']}")
    print(f"NEXT_SHORT_STEP={reconciliation.POST_REPLAY_NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
