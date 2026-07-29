#!/usr/bin/env python3
"""Validate Unit01 operator approval and contract-aware replay outputs."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_razq01b_unit01_contract_aware_replay as replay

VALIDATOR_ID = "A1FS_V1_RAZQ01B_UNIT01_CONTRACT_AWARE_REPLAY_VALIDATOR"
PASS_STATUS = "PASS_A1FS_V1_RAZQ01B_UNIT01_CONTRACT_AWARE_REPLAY_VALIDATION"


class ReplayValidationError(ValueError):
    pass


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ReplayValidationError(code)


def validate_approval(contract: Mapping[str, Any], approval: Mapping[str, Any]) -> dict[str, Any]:
    summary = replay.verify_operator_approval(contract, approval)
    _require(summary["operator_approval_verified"] is True, "operator_approval_not_verified")
    _require(summary["approved_dimension_count"] == 6, "approved_dimension_count_invalid")
    _require(
        approval.get("decision_source_text")
        == "Unit01ContentContractOperatorReviewAndContractAwareReplay",
        "decision_source_text_invalid",
    )
    _require(
        approval.get("boundaries", {}).get("a2_unlocked") is False,
        "a2_boundary_invalid",
    )
    return summary


def validate_report(
    report: Mapping[str, Any],
    contract: Mapping[str, Any],
    approval: Mapping[str, Any],
) -> dict[str, Any]:
    approval_summary = validate_approval(contract, approval)
    _require(report.get("schema_version") == replay.SCHEMA_VERSION, "report_schema_invalid")
    _require(report.get("task_id") == replay.TASK_ID, "report_task_id_invalid")
    _require(report.get("status") == replay.PASS_STATUS, "report_status_invalid")
    scope = report.get("scope", {})
    _require(scope.get("allowed_units") == ["GRAMMAR_ARTICLES_BASIC"], "report_unit_scope_invalid")
    _require(scope.get("blocked_units") == "UNIT_02_TO_UNIT_24", "report_blocked_unit_scope_invalid")
    _require(scope.get("canonical_promotion") is False, "canonical_promotion_forbidden")
    _require(scope.get("learner_facing_content_write") is False, "learner_content_write_forbidden")
    inputs = report.get("inputs", {})
    _require(
        inputs.get("approved_contract_sha256") == replay.APPROVED_CONTRACT_SHA256,
        "report_contract_digest_invalid",
    )
    validation = report.get("validation", {})
    _require(validation.get("operator_approval_verified") is True, "report_operator_approval_missing")
    _require(validation.get("contract_profile_overlay_applied") is True, "contract_profile_overlay_missing")
    _require(validation.get("contract_material_gate_applied") is True, "contract_material_gate_missing")
    _require(validation.get("unit01_only") is True, "unit01_only_gate_missing")
    _require(validation.get("canonical_content_modified") is False, "canonical_content_modified")
    _require(validation.get("unit02_to_unit24_modified") is False, "other_units_modified")
    _require(validation.get("a2_unlocked") is False, "a2_unlocked")
    unit = report.get("unit", {})
    _require(
        unit.get("unit_profile", {}).get("unit_id") == "GRAMMAR_ARTICLES_BASIC",
        "unit_profile_invalid",
    )
    _require(
        "UNIT01_OPERATOR_APPROVED_CONTENT_CONTRACT"
        in unit.get("unit_profile", {}).get("authority_sources", []),
        "approved_contract_authority_missing",
    )
    _require(isinstance(unit.get("filter_funnel"), Mapping), "filter_funnel_missing")
    _require(report.get("next_short_step") == replay.NEXT_SHORT_STEP, "next_short_step_invalid")
    return {
        "validator_id": VALIDATOR_ID,
        "validation_status": PASS_STATUS,
        "error_count": 0,
        "records_scanned": int(report.get("records_scanned") or 0),
        "approved_contract_sha256": approval_summary["approved_contract_sha256"],
        "unit_id": "GRAMMAR_ARTICLES_BASIC",
        "next_short_step": replay.NEXT_SHORT_STEP,
    }


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReplayValidationError(f"unreadable:{path}:{exc}") from exc
    _require(isinstance(value, dict), f"object_required:{path}")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=replay.DEFAULT_CONTRACT)
    parser.add_argument("--approval", type=Path, default=replay.DEFAULT_APPROVAL)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    try:
        contract, approval = _load(args.contract), _load(args.approval)
        if args.report is None:
            summary = validate_approval(contract, approval)
            result = {"validation_status": PASS_STATUS, **summary}
        else:
            result = validate_report(_load(args.report), contract, approval)
    except (ReplayValidationError, replay.ReplayError, ValueError, KeyError, TypeError) as exc:
        print("STATUS=FAIL_A1FS_V1_RAZQ01B_UNIT01_CONTRACT_AWARE_REPLAY_VALIDATION")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={result['validation_status']}")
    print(f"APPROVED_CONTRACT_SHA256={result['approved_contract_sha256']}")
    print(f"NEXT_SHORT_STEP={replay.NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
