#!/usr/bin/env python3
"""Promote only S04-eligible representatives to a safe material registry.

The registry is a text-free index into private RAZ source units. It records
Authority links and candidate CEFR scope, while keeping remediation, support,
and rejected lanes outside the promoted registry. It is not learner-facing
content and does not alter canonical Authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_raz_af_deep_semantic_material_alignment as deep
from ulga.builders import build_raz_aw_theme_authority_candidate_matching as matching
from ulga.builders import build_raz_ai_acl_v1_s04_admission_resolution as resolution

REPO_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "RAZ-AI-ACL-V1-S05_A1A1PlusMaterialRegistryPromotion"
SCHEMA_VERSION = "raz.ai.acl.v1.s05.a1_a1plus_material_registry_promotion.v1"
PASS_STATUS = "PASS_RAZ_AI_ACL_V1_S05_A1_A1PLUS_MATERIAL_REGISTRY_PROMOTION"

EXPECTED_TOTAL_PAGE_UNIT_COUNT = 22632
EXPECTED_SCOPE_PAGE_UNIT_COUNT = 7957
EXPECTED_SEMANTIC_IDENTITY_COUNT = 7849
EXPECTED_DUPLICATE_BINDING_COUNT = 108
EXPECTED_DEFERRED_PAGE_UNIT_COUNT = 14675

DEFAULT_RESOLUTION = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s04_admission_resolution/"
    "rewrite_admission_resolution.safe.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / ".local/raz_ai/acl_v1_s05_material_registry/"
    "a1_a1plus_material_registry.safe.json"
)

LANES = {
    "PROMOTION_ELIGIBLE",
    "REMEDIATION_REQUIRED",
    "SUPPORT_ADMITTED",
    "REJECTED_CLOSED",
}

CLAIM_BOUNDARIES = {
    "source_text_read_performed": False,
    "source_text_included_in_output": False,
    "source_title_included_in_output": False,
    "canonical_authority_write_performed": False,
    "eligible_material_registry_promotion_performed": True,
    "rewrite_required_rows_promoted": False,
    "support_only_rows_promoted": False,
    "rejected_rows_promoted": False,
    "learner_facing_content_created": False,
    "a2_a2plus_rows_remain_deferred": True,
}


class MaterialRegistryError(ValueError):
    """Fail-closed S04 lineage, accounting, or promotion eligibility error."""


def _verify_hash(package: Mapping[str, Any]) -> None:
    claimed = package.get("package_sha256")
    if not isinstance(claimed, str) or len(claimed) != 64:
        raise MaterialRegistryError("resolution_package_sha256_invalid")
    core = dict(package)
    core.pop("package_sha256", None)
    if deep.sha256_value(core) != claimed:
        raise MaterialRegistryError("resolution_package_sha256_mismatch")


def _material_id(group: str, source_ref: str) -> str:
    digest = hashlib.sha256(f"{group}\0{source_ref}".encode("utf-8")).hexdigest()[:24]
    return f"RAZ_A1A1PLUS_MATERIAL_{digest}"


def _verify_resolution(
    package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int,
    expected_scope_page_unit_count: int,
    expected_semantic_identity_count: int,
    expected_duplicate_binding_count: int,
    expected_deferred_page_unit_count: int,
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if package.get("task_id") != resolution.TASK_ID:
        raise MaterialRegistryError("resolution_task_id_mismatch")
    if package.get("validation_status") != resolution.PASS_STATUS:
        raise MaterialRegistryError("resolution_validation_status_not_pass")
    if package.get("errors") != []:
        raise MaterialRegistryError("resolution_errors_not_empty")
    _verify_hash(package)
    gate = package.get("admission_resolution_gate")
    if (
        not isinstance(gate, Mapping)
        or gate.get("decision") != "ADMISSION_RESOLUTION_READY"
        or gate.get("ready_for_material_registry_promotion") is not True
        or gate.get("remediation_queue_is_nonpromotable") is not True
    ):
        raise MaterialRegistryError("resolution_gate_not_ready_for_registry")
    summary = package.get("aggregate_summary")
    if not isinstance(summary, Mapping):
        raise MaterialRegistryError("resolution_summary_missing")
    expected = {
        "source_candidate_count": expected_total_page_unit_count,
        "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
        "semantic_identity_count": expected_semantic_identity_count,
        "duplicate_binding_count": expected_duplicate_binding_count,
        "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
        "final_promoted_material_count": 0,
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise MaterialRegistryError(
                f"resolution_summary_mismatch:{key}:{summary.get(key)}:{value}"
            )
    rows = package.get("resolved_admission_rows")
    bindings = package.get("duplicate_bindings")
    if not isinstance(rows, list) or not all(isinstance(row, Mapping) for row in rows):
        raise MaterialRegistryError("resolved_admission_rows_invalid")
    if not isinstance(bindings, list) or not all(
        isinstance(row, Mapping) for row in bindings
    ):
        raise MaterialRegistryError("duplicate_bindings_invalid")
    if len(rows) != expected_semantic_identity_count:
        raise MaterialRegistryError("resolved_admission_row_count_mismatch")
    if len(bindings) != expected_duplicate_binding_count:
        raise MaterialRegistryError("duplicate_binding_count_mismatch")
    return rows, bindings


def build_package(
    resolution_package: Mapping[str, Any],
    *,
    expected_total_page_unit_count: int = EXPECTED_TOTAL_PAGE_UNIT_COUNT,
    expected_scope_page_unit_count: int = EXPECTED_SCOPE_PAGE_UNIT_COUNT,
    expected_semantic_identity_count: int = EXPECTED_SEMANTIC_IDENTITY_COUNT,
    expected_duplicate_binding_count: int = EXPECTED_DUPLICATE_BINDING_COUNT,
    expected_deferred_page_unit_count: int = EXPECTED_DEFERRED_PAGE_UNIT_COUNT,
) -> dict[str, Any]:
    rows, bindings = _verify_resolution(
        resolution_package,
        expected_total_page_unit_count=expected_total_page_unit_count,
        expected_scope_page_unit_count=expected_scope_page_unit_count,
        expected_semantic_identity_count=expected_semantic_identity_count,
        expected_duplicate_binding_count=expected_duplicate_binding_count,
        expected_deferred_page_unit_count=expected_deferred_page_unit_count,
    )
    promoted: list[dict[str, Any]] = []
    remediation: list[dict[str, Any]] = []
    support: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    lane_counts: Counter[str] = Counter()
    cefr_counts: Counter[str] = Counter()
    seen_groups: set[str] = set()
    seen_sources: set[str] = set()
    material_ids: set[str] = set()

    for row in sorted(rows, key=lambda item: str(item.get("semantic_duplicate_group_id"))):
        group = str(row.get("semantic_duplicate_group_id") or "")
        source_ref = str(row.get("selected_source_unit_ref") or "")
        lane = str(row.get("admission_resolution") or "")
        scope = str(row.get("candidate_cefr_scope") or "")
        links = row.get("authority_links")
        if not group or group in seen_groups:
            raise MaterialRegistryError("semantic_group_missing_or_duplicate")
        if not source_ref or source_ref in seen_sources:
            raise MaterialRegistryError("source_ref_missing_or_duplicate")
        if lane not in LANES:
            raise MaterialRegistryError(f"admission_resolution_invalid:{source_ref}:{lane}")
        if not isinstance(links, list) or not all(isinstance(link, Mapping) for link in links):
            raise MaterialRegistryError(f"authority_links_invalid:{source_ref}")
        seen_groups.add(group)
        seen_sources.add(source_ref)
        lane_counts[lane] += 1
        base = {
            "semantic_duplicate_group_id": group,
            "selected_source_unit_ref": source_ref,
            "source_level": str(row.get("source_level") or ""),
            "source_book_id": str(row.get("source_book_id") or ""),
            "authority_links": [dict(link) for link in links],
        }
        if lane == "PROMOTION_ELIGIBLE":
            if scope not in {"A1", "A1_PLUS"}:
                raise MaterialRegistryError(f"promoted_scope_invalid:{source_ref}:{scope}")
            material_id = _material_id(group, source_ref)
            if material_id in material_ids:
                raise MaterialRegistryError("material_id_collision")
            material_ids.add(material_id)
            cefr_counts[scope] += 1
            promoted.append(
                {
                    "material_id": material_id,
                    **base,
                    "candidate_cefr_scope": scope,
                    "registry_status": "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY",
                    "source_payload_access": "PRIVATE_SOURCE_REF_REQUIRED",
                }
            )
        elif lane == "REMEDIATION_REQUIRED":
            remediation.append(
                {
                    **base,
                    "remediation_status": "PENDING_CONTENT_REWRITE_EVIDENCE",
                    "promotion_status": "NOT_PROMOTED",
                }
            )
        elif lane == "SUPPORT_ADMITTED":
            support.append({**base, "support_status": "ADMITTED_SUPPORT_ONLY"})
        else:
            rejected.append({**base, "rejection_status": "CLOSED_UNUSABLE"})

    checks = {
        "all_semantic_identities_reconciled_once": (
            len(promoted) + len(remediation) + len(support) + len(rejected)
            == expected_semantic_identity_count
            and len(seen_groups) == expected_semantic_identity_count
            and len(seen_sources) == expected_semantic_identity_count
        ),
        "promotion_count_matches_eligible_count": (
            len(promoted) == lane_counts["PROMOTION_ELIGIBLE"]
        ),
        "promoted_material_ids_unique": len(material_ids) == len(promoted),
        "promoted_rows_are_a1_or_a1plus": all(
            row["candidate_cefr_scope"] in {"A1", "A1_PLUS"} for row in promoted
        ),
        "noneligible_lanes_not_promoted": all(
            "material_id" not in row for row in remediation + support + rejected
        ),
        "a2_a2plus_not_opened": all(
            row["candidate_cefr_scope"] not in {"A2", "A2_PLUS"} for row in promoted
        ),
        "duplicate_bindings_preserved": len(bindings) == expected_duplicate_binding_count,
    }
    ready = all(checks.values()) and bool(promoted)
    package: dict[str, Any] = {
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS if ready else "FAIL",
        "input_identity": {
            "admission_resolution_task_id": resolution_package["task_id"],
            "admission_resolution_package_sha256": resolution_package["package_sha256"],
        },
        "scope_contract": dict(resolution_package["scope_contract"]),
        "promoted_material_registry": promoted,
        "remediation_queue": remediation,
        "support_registry": support,
        "rejected_registry": rejected,
        "duplicate_bindings": [dict(row) for row in bindings],
        "aggregate_summary": {
            "source_candidate_count": expected_total_page_unit_count,
            "a1_a1plus_scope_candidate_count": expected_scope_page_unit_count,
            "semantic_identity_count": expected_semantic_identity_count,
            "duplicate_binding_count": len(bindings),
            "deferred_a2_a2plus_count": expected_deferred_page_unit_count,
            "lane_counts": dict(sorted(lane_counts.items())),
            "promoted_cefr_scope_counts": dict(sorted(cefr_counts.items())),
            "final_promoted_material_count": len(promoted),
            "remediation_queue_count": len(remediation),
            "support_registry_count": len(support),
            "rejected_registry_count": len(rejected),
        },
        "material_registry_gate": {
            "source_checks": checks,
            "decision": "A1_A1PLUS_MATERIAL_REGISTRY_READY" if ready else "BLOCKED_MATERIAL_REGISTRY",
            "distance_before": "D2",
            "distance_after": "D1" if ready else "D2",
            "ready_for_final_coverage_reconciliation": ready,
            "ready_for_learner_facing_content": False,
        },
        "claim_boundaries": dict(CLAIM_BOUNDARIES),
        "errors": [],
    }
    leakage = matching.scan_forbidden_safe_keys(package)
    if leakage:
        raise MaterialRegistryError("safe_output_leakage:" + ";".join(leakage[:20]))
    package["package_sha256"] = deep.sha256_value(package)
    return package


def _readback(package: Mapping[str, Any]) -> dict[str, Any]:
    return {"task_id": TASK_ID, "decision": package["material_registry_gate"]["decision"], "distance_after": package["material_registry_gate"]["distance_after"], **package["aggregate_summary"], "package_sha256": package["package_sha256"]}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission-resolution-package", type=Path, default=DEFAULT_RESOLUTION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        package = deep.read_json(args.admission_resolution_package)
        if not isinstance(package, Mapping):
            raise MaterialRegistryError("admission_resolution_package_not_object")
        output = build_package(package)
        deep.write_json_atomic(args.output, output)
        print(json.dumps(_readback(output), sort_keys=True))
        return 0
    except (MaterialRegistryError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
