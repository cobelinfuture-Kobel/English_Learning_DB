#!/usr/bin/env python3
"""Validate Unit01 canonical chunk alias reconciliation and workbook-readback invariants."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_u01data02_unit01_existing_u01e_projection_and_cumulative_linkage as builder
from ulga.validators import validate_a1fs_v1_u01data02_unit01_existing_u01e_projection_and_cumulative_linkage as base_validator

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Validates exact metadata-only reconciliation of three Unit01 canonical chunk aliases into existing registry bindings and confirms the remaining project phrase gaps and Pattern-to-Frame evidence boundary; it creates no learner content, answer, scoring, state, audio, A2 target, or parallel bank."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01DATA04A_Unit01CanonicalChunkAliasReconciliationAndOperatorWorkbookReadbackFullFix"
PASS_STATUS = "PASS_A1FS_V1_U01DATA04A_UNIT01_CANONICAL_CHUNK_ALIAS_RECONCILIATION"
DEFAULT_REPORT = builder.DEFAULT_OUTPUT
EXPECTED_ALIAS_TO_BINDING = {
    "chunk:cd_player": "U01-BIND-CHUNK-EVP-CHUNK-000003",
    "chunk:ice_cream": "U01-BIND-CHUNK-EVP-CHUNK-000054",
    "chunk:living_room": "U01-BIND-CHUNK-EVP-CHUNK-000075",
}
EXPECTED_EXTERNAL_SUPPORT = {
    "phrase:u01e:in_a_box",
    "phrase:u01e:in_the_park",
    "phrase:u01e:near_the_bed",
}
EXPECTED_STATUS_COUNTS = {
    "LINKED_TO_CUMULATIVE_REGISTRY": 17,
    "LINKED_WITH_EXTERNAL_SUPPORT": 7,
}
EXPECTED_ACTIVITY_ASSET_LINK_COUNT = 60
EXPECTED_UNIQUE_ACTIVITY_BINDING_COUNT = 20


class AliasReconciliationValidationError(ValueError):
    pass


def validate_report(report: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    def check(condition: bool, code: str) -> None:
        if not condition:
            errors.append(code)

    try:
        base_validator.validate_report(report)
    except base_validator.ProjectionValidationError as exc:
        errors.append(f"base_projection_invalid:{exc}")

    summary = report.get("linkage_summary") or {}
    check(
        summary.get("canonical_chunk_alias_reconciliation_status")
        == "PASS_EXACT_NORMALIZED_LABEL_TO_SINGLE_CANONICAL_CHUNK_BINDING",
        "alias_reconciliation_status_invalid",
    )
    check(
        summary.get("canonical_chunk_alias_reconciled_target_count") == 3,
        "alias_reconciliation_count_invalid",
    )
    rows = summary.get("canonical_chunk_alias_reconciliations") or []
    by_alias = {
        str(row.get("source_alias_id")): row
        for row in rows
        if isinstance(row, Mapping) and row.get("source_alias_id")
    }
    check(set(by_alias) == set(EXPECTED_ALIAS_TO_BINDING), "alias_identity_set_invalid")
    for alias_id, expected_binding in EXPECTED_ALIAS_TO_BINDING.items():
        row = by_alias.get(alias_id) or {}
        check(row.get("registry_binding_id") == expected_binding, f"alias_binding_invalid:{alias_id}")
        check(
            row.get("reconciliation_method")
            == "EXACT_NORMALIZED_LABEL_UNIQUE_CANONICAL_CHUNK",
            f"alias_method_invalid:{alias_id}",
        )

    check(
        set(summary.get("unlinked_external_support_target_ids") or []) == EXPECTED_EXTERNAL_SUPPORT,
        "remaining_external_support_set_invalid",
    )
    check(
        not (set(EXPECTED_ALIAS_TO_BINDING) & set(summary.get("unlinked_external_support_target_ids") or [])),
        "reconciled_alias_remains_external_support",
    )
    check(
        summary.get("activity_linkage_status_counts") == EXPECTED_STATUS_COUNTS,
        "activity_linkage_status_counts_invalid",
    )
    check(
        summary.get("activity_asset_link_count") == EXPECTED_ACTIVITY_ASSET_LINK_COUNT,
        "activity_asset_link_count_invalid",
    )
    check(
        summary.get("unique_activity_linked_registry_binding_count")
        == EXPECTED_UNIQUE_ACTIVITY_BINDING_COUNT,
        "unique_activity_binding_count_invalid",
    )
    check(
        summary.get("canonical_pattern_to_unit_frame_bridge_status")
        == "UNRESOLVED_RECORDED_NOT_INFERRED",
        "pattern_frame_boundary_invalid",
    )

    activities = [
        *(report.get("activity_projections") or {}).get("existing_response_contract_activities", []),
        *(report.get("activity_projections") or {}).get("fixed_admitted_items", []),
    ]
    observed_aliases = {
        str(row.get("source_alias_id"))
        for activity in activities
        for row in activity.get("canonical_chunk_alias_reconciliations", []) or []
        if isinstance(row, Mapping) and row.get("source_alias_id")
    }
    check(observed_aliases == set(EXPECTED_ALIAS_TO_BINDING), "activity_alias_evidence_invalid")
    check(
        sum(len(activity.get("linked_registry_binding_ids") or []) for activity in activities)
        == EXPECTED_ACTIVITY_ASSET_LINK_COUNT,
        "activity_link_sum_invalid",
    )
    check(all(value is False for value in (report.get("boundaries") or {}).values()), "boundary_drift")

    if errors:
        raise AliasReconciliationValidationError(";".join(errors))
    return {
        "validation_status": PASS_STATUS,
        "unit_id": builder.UNIT_ID,
        "projection_sha256": report["projection_sha256"],
        "reconciled_alias_count": 3,
        "remaining_external_support_count": 3,
        "activity_asset_link_count": EXPECTED_ACTIVITY_ASSET_LINK_COUNT,
        "unique_activity_binding_count": EXPECTED_UNIQUE_ACTIVITY_BINDING_COUNT,
        "pattern_frame_bridge_status": summary["canonical_pattern_to_unit_frame_bridge_status"],
        "next_short_step": "A1FS-V1-U01DATA03_Unit01CumulativeDataWorkbookAndJsonExport",
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report.resolve().read_text(encoding="utf-8"))
        result = validate_report(report)
    except (
        OSError,
        json.JSONDecodeError,
        AliasReconciliationValidationError,
        ValueError,
        KeyError,
        TypeError,
    ) as exc:
        print("STATUS=FAIL_A1FS_V1_U01DATA04A_UNIT01_CANONICAL_CHUNK_ALIAS_RECONCILIATION")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={result['validation_status']}")
    print(f"UNIT={result['unit_id']}")
    print(f"RECONCILED_ALIASES={result['reconciled_alias_count']}")
    print(f"REMAINING_EXTERNAL_SUPPORT={result['remaining_external_support_count']}")
    print(f"ACTIVITY_ASSET_LINKS={result['activity_asset_link_count']}")
    print(f"UNIQUE_ACTIVITY_BINDINGS={result['unique_activity_binding_count']}")
    print(f"PATTERN_FRAME_BRIDGE={result['pattern_frame_bridge_status']}")
    print(f"PROJECTION_SHA256={result['projection_sha256']}")
    print(f"NEXT_SHORT_STEP={result['next_short_step']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
