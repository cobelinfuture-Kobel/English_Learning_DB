#!/usr/bin/env python3
"""Reconcile S05 coverage and close RAZ-AI-ACL-V1 at D0.

S06 verifies that every A-I semantic identity is represented in exactly one
closed registry lane, duplicate bindings reconcile to the original A-I count,
J-W remain deferred, and every promoted A1/A1+ material has the Authority links
required by downstream private consumers.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s05_material_registry as registry

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI-ACL-V1-S06_FinalCoverageReconciliationAndD0Closeout"
SCHEMA_VERSION = "raz.ai.acl.v1.s06.final_coverage_reconciliation_closeout.v1"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S06_FINAL_COVERAGE_RECONCILIATION_D0_CLOSEOUT"

EXPECTED_TOTAL_PAGE_UNIT_COUNT = 22632
EXPECTED_SCOPE_PAGE_UNIT_COUNT = 7957
EXPECTED_SEMANTIC_IDENTITY_COUNT = 7849
EXPECTED_DUPLICATE_BINDING_COUNT = 108
EXPECTED_DEFERRED_PAGE_UNIT_COUNT = 14675

DEFAULT_REGISTRY = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s05_material_registry/"
    "a1_a1plus_material_registry.safe.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s06_final_closeout/"
    "final_coverage_reconciliation_d0.safe.json"
)

CLAIM_BOUNDARIES = {
    "source_text_read_performed": False,
    "source_text_included_in_output": False,
    "source_title_included_in_output": False,
    "canonical_authority_write_performed": False,
    "learner_facing_content_created": False,
    "mastery_claimed": False,
    "retention_claimed": False,
    "a2_a2plus_rows_remain_deferred": True,
    "program_closeout_is_registry_capability_closeout": True,
}


class FinalCloseoutError(ValueError):
    """Fail-closed S05 lineage, coverage, or closeout invariant error."""


def _verify_hash(package: Mapping[str, Any]) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise FinalCloseoutError("registry_package_sha256_invalid")
    core = dict(package)
    core.pop("package_sha256", None)
    if deep.sha256_value(core) != claimed:
        raise FinalCloseoutError("registry_package_sha256_mismatch")


def _rows(package: Mapping[str, Any], key: str) -> list[Mapping[str, Any]]:
    value = package.get(key)
    if not isinstance(value, list) or not all(isinstance(row, Mapping) for row in value):
        raise FinalCloseoutError(f"registry_lane_invalid:{key}")
    return value


def build_package(
    registry_package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int = EXPECTED_TOTAL_PAGE_UNIT_COUNT,
    expected_scope_page_unit_count: int = EXPECTED_SCOPE_PAGE_UNIT_COUNT,
    expected_semantic_identity_count: int = EXPECTED_SEMANTIC_IDENTITY_COUNT,
    expected_duplicate_binding_count: int = EXPECTED_DUPLICATE_BINDING_COUNT,
    expected_deferred_page_unit_count: int = EXPECTED_DEFERRED_PAGE_UNIT_COUNT,
) -> dict[str, Any]:
    if registry_package.get("task_id") != registry.TASK_ID:
        raise FinalCloseoutError("registry_task_id_mismatch")
    if registry_package.get("validation_status") != registry.PASS_STATUS:
        raise FinalCloseoutError("registry_validation_status_not_pass")
    if registry_package.get("errors") != []:
        raise FinalCloseoutError("registry_errors_not_empty")
    _verify_hash(registry_package)
    gate = registry_package.get("material_registry_gate")
    if (
        not isinstance(gate, Mapping)
        or gate.get("decision") != "A1_A1PLUS_MATERIAL_REGISTRY_READY"
        or gate.get("ready_for_final_coverage_reconciliation") is not True
    ):
        raise FinalCloseoutError("registry_gate_not_ready_for_closeout")
    summary = registry_package.get("aggregate_summary")
    if not isinstance(summary, Mapping):
        raise FinalCloseoutError("registry_summary_missing")
    expected = {
        "source_candidate_count": expected_total_page_unit_count,
        "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
        "semantic_identity_count": expected_semantic_identity_count,
        "duplicate_binding_count": expected_duplicate_binding_count,
        "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise FinalCloseoutError(
                f"registry_summary_mismatch:{key}:{summary.get(key)}:{value}"
            )

    promoted = _rows(registry_package, "promoted_material_registry")
    remediation = _rows(registry_package, "remediation_queue")
    support = _rows(registry_package, "support_registry")
    rejected = _rows(registry_package, "rejected_registry")
    bindings = _rows(registry_package, "duplicate_bindings")
    lanes = promoted + remediation + support + rejected
    group_counts = Counter(str(row.get("semantic_duplicate_group_id") or "") for row in lanes)
    source_counts = Counter(str(row.get("selected_source_unit_ref") or "") for row in lanes)
    material_ids = [str(row.get("material_id") or "") for row in promoted]
    promoted_scope_counts = Counter(
        str(row.get("candidate_cefr_scope") or "") for row in promoted
    )

    promoted_authority_complete = True
    for row in promoted:
        links = row.get("authority_links")
        if not isinstance(links, list) or not all(isinstance(link, Mapping) for link in links):
            raise FinalCloseoutError("promoted_authority_links_invalid")
        authority_types = {str(link.get("authority_type") or "") for link in links}
        if not {"VOCABULARY", "GRAMMAR"} <= authority_types:
            promoted_authority_complete = False

    checks = {
        "source_total_reconciles": (
            expected_scope_page_unit_count + expected_deferred_page_unit_count
            == expected_total_page_unit_count
        ),
        "scope_count_reconciles_from_identity_and_duplicates": (
            expected_semantic_identity_count + expected_duplicate_binding_count
            == expected_scope_page_unit_count
        ),
        "all_semantic_identities_in_exactly_one_lane": (
            len(lanes) == expected_semantic_identity_count
            and bool(group_counts)
            and all(group and count == 1 for group, count in group_counts.items())
            and all(source and count == 1 for source, count in source_counts.items())
        ),
        "duplicate_bindings_exact": len(bindings) == expected_duplicate_binding_count,
        "promoted_registry_nonempty": bool(promoted),
        "promoted_material_ids_complete_unique": (
            all(material_ids) and len(material_ids) == len(set(material_ids))
        ),
        "promoted_scope_closed_to_a1_a1plus": (
            set(promoted_scope_counts) <= {"A1", "A1_PLUS"}
            and sum(promoted_scope_counts.values()) == len(promoted)
        ),
        "promoted_authority_complete": promoted_authority_complete,
        "nonpromoted_lanes_have_no_material_id": all(
            "material_id" not in row for row in remediation + support + rejected
        ),
        "registry_summary_counts_match_lanes": (
            summary.get("final_promoted_material_count") == len(promoted)
            and summary.get("remediation_queue_count") == len(remediation)
            and summary.get("support_registry_count") == len(support)
            and summary.get("rejected_registry_count") == len(rejected)
        ),
        "a2_a2plus_not_opened": all(
            row.get("candidate_cefr_scope") not in {"A2", "A2_PLUS"} for row in promoted
        ),
    }
    ready = all(checks.values())
    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "input_identity": {
            "material_registry_task_id": registry_package["task_id"],
            "material_registry_package_sha256": registry_package["package_sha256"],
        },
        "scope_contract": dict(registry_package["scope_contract"]),
        "coverage_reconciliation": {
            "source_candidate_count": expected_total_page_unit_count,
            "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
            "semantic_identity_count": expected_semantic_identity_count,
            "duplicate_binding_count": expected_duplicate_binding_count,
            "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
            "promoted_material_count": len(promoted),
            "remediation_queue_count": len(remediation),
            "support_registry_count": len(support),
            "rejected_registry_count": len(rejected),
            "promoted_cefr_scope_counts": dict(sorted(promoted_scope_counts.items())),
        },
        "consumer_contract": {
            "registry_consumer_input": "promoted_material_registry",
            "source_payload_resolution": "PRIVATE_SOURCE_REF_REQUIRED",
            "authority_linkage_required": ["VOCABULARY", "GRAMMAR"],
            "learner_facing_content_status": "NOT_CREATED_BY_THIS_PROGRAM",
        },
        "final_closeout_gate": {
            "source_checks": checks,
            "decision": "RAZ_AI_ACL_V1_D0_CLOSED" if ready else "BLOCKED_FINAL_CLOSEOUT",
            "program_status": "PASS_ACCEPTED_AND_CLOSED" if ready else "BLOCKED",
            "distance_before": "D1",
            "distance_after": "D0" if ready else "D1",
            "remaining_in_scope_blocker_count": 0 if ready else sum(
                1 for passed in checks.values() if not passed
            ),
            "a2_a2plus_status": "DEFERRED_A2_A2PLUS",
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    leakage = matching.scan_forbidden_safe_keys(package)
    if leakage:
        raise FinalCloseoutError("safe_output_leakage:" + ";".join(leakage[:20]))
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _readback(package: Mapping[str, Any]) -> dict[str, Any]:
    return {"task_id": TASK_ID, "decision": package["final_closeout_gate"]["decision"], "program_status": package["final_closeout_gate"]["program_status"], "distance_after": package["final_closeout_gate"]["distance_after"], **package["coverage_reconciliation"], "package_sha256": package["package_sha256"]}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--material-registry-package", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        package = deep.read_json(args.material_registry_package)
        if not isinstance(package, Mapping):
            raise FinalCloseoutError("material_registry_package_not_object")
        output = build_package(package)
        deep.write_json_atomic(args.output, output)
        print(json.dumps(_readback(output), sort_keys=True))
        return 0
    except (FinalCloseoutError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
