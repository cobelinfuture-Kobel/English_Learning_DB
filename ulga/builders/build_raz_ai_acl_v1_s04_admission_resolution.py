#!/usr/bin/env python3
"""Resolve S03 linkage rows into closed admission and remediation lanes.

S04 makes no content edits. It preserves ready representatives as promotion
eligible, routes rewrite-required representatives to remediation, admits
support-only rows only as support, and closes rejected rows. This prevents an
unresolved rewrite from being silently promoted.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s03_authority_linkage as linkage

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI-ACL-V1-S04_RewriteAndAdmissionResolution"
SCHEMA_VERSION = "raz.ai.acl.v1.s04.rewrite_admission_resolution.v2"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S04_REWRITE_ADMISSION_RESOLUTION"

EXPECTED_TOTAL_PAGE_UNIT_COUNT = 22632
EXPECTED_SCOPE_PAGE_UNIT_COUNT = 7957
EXPECTED_SEMANTIC_IDENTITY_COUNT = 7849
EXPECTED_DUPLICATE_BINDING_COUNT = 108
EXPECTED_DEFERRED_PAGE_UNIT_COUNT = 14675

DEFAULT_LINKAGE = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s03_authority_linkage/"
    "authority_linkage_conflict_gate.safe.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s04_admission_resolution/"
    "rewrite_admission_resolution.safe.json"
)

RESOLUTION_BY_ADMISSION = {
    "A1_READY_CANDIDATE": "PROMOTION_ELIGIBLE",
    "A1PLUS_READY_CANDIDATE": "PROMOTION_ELIGIBLE",
    "REWRITE_REQUIRED": "REMEDIATION_REQUIRED",
    "SUPPORT_ONLY": "SUPPORT_ADMITTED",
    "REJECTED_UNUSABLE": "REJECTED_CLOSED",
}
EXPECTED_LINKAGE_STATUS = {
    "A1_READY_CANDIDATE": "AUTHORITY_LINKED_A1_READY",
    "A1PLUS_READY_CANDIDATE": "AUTHORITY_LINKED_A1PLUS_READY",
    "REWRITE_REQUIRED": "AUTHORITY_LINKED_REWRITE_REQUIRED",
    "SUPPORT_ONLY": "AUTHORITY_LINKED_SUPPORT_ONLY",
    "REJECTED_UNUSABLE": "REJECTED_NOT_PROMOTABLE",
}
EXPECTED_SCOPE_BY_ADMISSION = {
    "A1_READY_CANDIDATE": "A1",
    "A1PLUS_READY_CANDIDATE": "A1_PLUS",
    "REWRITE_REQUIRED": "A1_A1PLUS_UNRESOLVED",
    "SUPPORT_ONLY": "NONE",
    "REJECTED_UNUSABLE": "NONE",
}

CLAIM_BOUNDARIES = {
    "source_text_read_performed": False,
    "source_text_included_in_output": False,
    "source_title_included_in_output": False,
    "automatic_rewrite_performed": False,
    "rewrite_required_rows_promoted": False,
    "canonical_authority_write_performed": False,
    "material_promotion_performed": False,
    "learner_facing_content_created": False,
    "a2_a2plus_rows_remain_deferred": True,
}


class AdmissionResolutionError(ValueError):
    """Fail-closed S03 lineage, accounting, or lane resolution error."""


def _verify_hash(package: Mapping[str, Any]) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise AdmissionResolutionError("linkage_package_sha256_invalid")
    core = dict(package)
    core.pop("package_sha256", None)
    if deep.sha256_value(core) != claimed:
        raise AdmissionResolutionError("linkage_package_sha256_mismatch")


def _verify_linkage(
    package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int,
    expected_scope_page_unit_count: int,
    expected_semantic_identity_count: int,
    expected_duplicate_binding_count: int,
    expected_deferred_page_unit_count: int,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if package.get("task_id") != linkage.TASK_ID:
        raise AdmissionResolutionError("linkage_task_id_mismatch")
    if package.get("validation_status") != linkage.PASS_STATUS:
        raise AdmissionResolutionError("linkage_validation_status_not_pass")
    if package.get("errors") != []:
        raise AdmissionResolutionError("linkage_errors_not_empty")
    _verify_hash(package)
    gate = package.get("authority_linkage_gate")
    if (
        not isinstance(gate, Mapping)
        or gate.get("decision") != "AUTHORITY_LINKAGE_READY"
        or gate.get("ready_for_rewrite_and_admission_resolution") is not True
    ):
        raise AdmissionResolutionError("linkage_gate_not_ready_for_resolution")
    summary = package.get("aggregate_summary")
    if not isinstance(summary, Mapping):
        raise AdmissionResolutionError("linkage_summary_missing")
    expected = {
        "source_candidate_count": expected_total_page_unit_count,
        "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
        "semantic_identity_count": expected_semantic_identity_count,
        "representative_count": expected_semantic_identity_count,
        "duplicate_binding_count": expected_duplicate_binding_count,
        "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
        "authority_reference_type_conflict_count": 0,
        "final_promoted_material_count": 0,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise AdmissionResolutionError(
                f"linkage_summary_mismatch:{key}:{summary.get(key)}:{value}"
            )
    rows = package.get("authority_linkage_rows")
    bindings = package.get("duplicate_bindings")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise AdmissionResolutionError("authority_linkage_rows_invalid")
    if not isinstance(bindings, list) or not all(
        isinstance(row, Mapping) for row in bindings
    ):
        raise AdmissionResolutionError("duplicate_bindings_invalid")
    if len(rows) != expected_semantic_identity_count:
        raise AdmissionResolutionError("authority_linkage_row_count_mismatch")
    if len(bindings) != expected_duplicate_binding_count:
        raise AdmissionResolutionError("duplicate_binding_count_mismatch")
    return rows, bindings


def build_package(
    linkage_package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int = EXPECTED_TOTAL_PAGE_UNIT_COUNT,
    expected_scope_page_unit_count: int = EXPECTED_SCOPE_PAGE_UNIT_COUNT,
    expected_semantic_identity_count: int = EXPECTED_SEMANTIC_IDENTITY_COUNT,
    expected_duplicate_binding_count: int = EXPECTED_DUPLICATE_BINDING_COUNT,
    expected_deferred_page_unit_count: int = EXPECTED_DEFERRED_PAGE_UNIT_COUNT,
) -> dict[str, Any]:
    rows, bindings = _verify_linkage(
        linkage_package,
        expected_total_page_unit_count=expected_total_page_unit_count,
        expected_scope_page_unit_count=expected_scope_page_unit_count,
        expected_semantic_identity_count=expected_semantic_identity_count,
        expected_duplicate_binding_count=expected_duplicate_binding_count,
        expected_deferred_page_unit_count=expected_deferred_page_unit_count,
    )
    resolved_rows: list[dict[str, Any]] = []
    resolution_counts: Counter[str] = Counter()
    cefr_counts: Counter[str] = Counter()
    seen_groups: set[str] = set()
    seen_refs: set[str] = set()

    for row in sorted(rows, key=lambda item: str(item.get("semantic_duplicate_group_id"))):
        group = str(row.get("semantic_duplicate_group_id") or "")
        source_ref = str(row.get("selected_source_unit_ref") or "")
        admission = str(row.get("representative_admission_status") or "")
        linkage_status = str(row.get("authority_linkage_status") or "")
        scope = str(row.get("candidate_cefr_scope") or "")
        links = row.get("authority_links")
        if not group or group in seen_groups:
            raise AdmissionResolutionError("semantic_group_missing_or_duplicate")
        if not source_ref or source_ref in seen_refs:
            raise AdmissionResolutionError("source_ref_missing_or_duplicate")
        if admission not in RESOLUTION_BY_ADMISSION:
            raise AdmissionResolutionError(f"admission_status_invalid:{source_ref}:{admission}")
        if linkage_status != EXPECTED_LINKAGE_STATUS[admission]:
            raise AdmissionResolutionError(
                f"linkage_status_mismatch:{source_ref}:{linkage_status}"
            )
        if not isinstance(links, list) or not all(isinstance(link, Mapping) for link in links):
            raise AdmissionResolutionError(f"authority_links_invalid:{source_ref}")
        resolution = RESOLUTION_BY_ADMISSION[admission]
        expected_scope = EXPECTED_SCOPE_BY_ADMISSION[admission]
        if scope != expected_scope:
            raise AdmissionResolutionError(
                "candidate_cefr_scope_mismatch:"
                f"{source_ref}:{admission}:{scope}:{expected_scope}"
            )
        seen_groups.add(group)
        seen_refs.add(source_ref)
        resolution_counts[resolution] += 1
        cefr_counts[scope] += 1
        resolved_rows.append(
            {
                "semantic_duplicate_group_id": group,
                "selected_source_unit_ref": source_ref,
                "source_level": str(row.get("source_level") or ""),
                "source_book_id": str(row.get("source_book_id") or ""),
                "candidate_cefr_scope": scope,
                "authority_links": [dict(link) for link in links],
                "authority_link_count": int(row.get("authority_link_count") or 0),
                "admission_resolution": resolution,
                "remediation_reason_codes": (
                    ["SOURCE_CONTENT_REWRITE_REQUIRED_BEFORE_PROMOTION"]
                    if resolution == "REMEDIATION_REQUIRED"
                    else []
                ),
                "promotion_status": "ELIGIBLE_NOT_PROMOTED"
                if resolution == "PROMOTION_ELIGIBLE"
                else "NOT_PROMOTABLE",
            }
        )

    checks = {
        "all_semantic_identities_resolved_once": (
            len(resolved_rows) == expected_semantic_identity_count
            and len(seen_groups) == expected_semantic_identity_count
            and len(seen_refs) == expected_semantic_identity_count
        ),
        "resolution_counts_reconcile": (
            sum(resolution_counts.values()) == expected_semantic_identity_count
        ),
        "promotion_eligible_rows_are_a1_or_a1plus": all(
            row["candidate_cefr_scope"] in {"A1", "A1_PLUS"}
            for row in resolved_rows
            if row["admission_resolution"] == "PROMOTION_ELIGIBLE"
        ),
        "rewrite_rows_remain_unpromoted": all(
            row["promotion_status"] == "NOT_PROMOTABLE"
            for row in resolved_rows
            if row["admission_resolution"] == "REMEDIATION_REQUIRED"
        ),
        "support_and_rejected_rows_not_promotable": all(
            row["promotion_status"] == "NOT_PROMOTABLE"
            for row in resolved_rows
            if row["admission_resolution"] in {"SUPPORT_ADMITTED", "REJECTED_CLOSED"}
        ),
        "a2_a2plus_not_opened": all(
            row["candidate_cefr_scope"] not in {"A2", "A2_PLUS"}
            for row in resolved_rows
        ),
        "no_material_promoted": all(
            row["promotion_status"] != "PROMOTED" for row in resolved_rows
        ),
    }
    ready = all(checks.values())
    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "input_identity": {
            "authority_linkage_task_id": linkage_package["task_id"],
            "authority_linkage_package_sha256": linkage_package["package_sha256"],
        },
        "scope_contract": dict(linkage_package["scope_contract"]),
        "resolved_admission_rows": resolved_rows,
        "duplicate_bindings": [dict(row) for row in bindings],
        "aggregate_summary": {
            "source_candidate_count": expected_total_page_unit_count,
            "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
            "semantic_identity_count": len(resolved_rows),
            "duplicate_binding_count": len(bindings),
            "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
            "admission_resolution_counts": dict(sorted(resolution_counts.items())),
            "candidate_cefr_scope_counts": dict(sorted(cefr_counts.items())),
            "promotion_eligible_count": resolution_counts["PROMOTION_ELIGIBLE"],
            "remediation_required_count": resolution_counts["REMEDIATION_REQUIRED"],
            "support_admitted_count": resolution_counts["SUPPORT_ADMITTED"],
            "rejected_closed_count": resolution_counts["REJECTED_CLOSED"],
            "final_promoted_material_count": 0,
        },
        "admission_resolution_gate": {
            "source_checks": checks,
            "decision": "ADMISSION_RESOLUTION_READY" if ready else "BLOCKED_ADMISSION_RESOLUTION",
            "distance_before": "D3",
            "distance_after": "D2" if ready else "D3",
            "ready_for_material_registry_promotion": ready,
            "remediation_queue_is_nonpromotable": True,
            "ready_for_learner_facing_content": False,
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    leakage = matching.scan_forbidden_safe_keys(package)
    if leakage:
        raise AdmissionResolutionError("safe_output_leakage:" + ";".join(leakage[:20]))
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _readback(package: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "task_id": TASK_ID,
        "decision": package["admission_resolution_gate"]["decision"],
        "distance_after": package["admission_resolution_gate"]["distance_after"],
        **package["aggregate_summary"],
        "package_sha256": package["package_sha256"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority-linkage-package", type=Path, default=DEFAULT_LINKAGE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        package = deep.read_json(args.authority_linkage_package)
        if not isinstance(package, Mapping):
            raise AdmissionResolutionError("authority_linkage_package_not_object")
        output = build_package(package)
        deep.write_json_atomic(args.output, output)
        print(json.dumps(_readback(output), sort_keys=True))
        return 0
    except (AdmissionResolutionError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
