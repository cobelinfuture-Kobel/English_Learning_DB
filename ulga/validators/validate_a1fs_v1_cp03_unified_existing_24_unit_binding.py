#!/usr/bin/env python3
"""Independently validate the CP03 single-curriculum dual-source binding."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_cp03_unified_existing_24_unit_binding as builder  # noqa: E402


def _m11b_ids(unit: Mapping[str, Any]) -> dict[str, list[str]]:
    return {
        skill: list(unit.get("skill_lanes", {}).get(skill, {}).get("admitted_item_ids", []))
        for skill in builder.SKILLS
    }


def _raz_expected(
    package: Mapping[str, Any], allowed: set[str], errors: list[str]
) -> dict[str, list[str]]:
    result: defaultdict[str, list[str]] = defaultdict(list)
    for row in package.get("promoted_material_registry", []):
        if not isinstance(row, Mapping):
            errors.append("raz_promoted_row_invalid")
            continue
        material_id = str(row.get("material_id") or "")
        if row.get("registry_status") != "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY":
            errors.append(f"raz_unpromoted_material_present:{material_id}")
        grammar_refs = {
            str(link.get("authority_ref") or "")
            for link in row.get("authority_links", [])
            if isinstance(link, Mapping)
            and link.get("authority_type") == "GRAMMAR"
            and link.get("link_status") == "VERIFIED_EXISTING_AUTHORITY_MATCH"
        }
        if not grammar_refs or not grammar_refs <= allowed:
            errors.append(f"raz_grammar_ref_outside_existing_24:{material_id}")
        for grammar_id in sorted(grammar_refs & allowed):
            result[grammar_id].append(material_id)
    return {key: sorted(value) for key, value in result.items()}


def validate_artifact(
    artifact: Mapping[str, Any],
    cp01_artifact: Mapping[str, Any],
    cp02_artifact: Mapping[str, Any],
    raz_registry_package: Mapping[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    if artifact.get("task_id") != builder.TASK_ID:
        errors.append("task_id_mismatch")
    if artifact.get("schema_version") != builder.SCHEMA_VERSION:
        errors.append("schema_version_mismatch")
    if artifact.get("scope") != "A1_A1_PLUS_ONLY":
        errors.append("scope_mismatch")

    contract = artifact.get("binding_contract", {})
    expected_contract = {
        "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
        "unit_identity_source": builder.cp02.TASK_ID,
        "content_sources": [
            "M11B_REVIEWED_CONTENT",
            "RAZ_AI_ACL_S05_PROMOTED_MATERIAL_REGISTRY",
        ],
        "raz_join_key": "VERIFIED_GRAMMAR_AUTHORITY_REF_EQUALS_EXISTING_GRAMMAR_UNIT_ID",
        "new_unit_creation_allowed": False,
        "raz_specific_parallel_curriculum_allowed": False,
        "unpromoted_raz_asset_binding_allowed": False,
    }
    if contract != expected_contract:
        errors.append("single_curriculum_binding_contract_mismatch")

    source_units = cp01_artifact.get("learning_units", [])
    cp02_units = cp02_artifact.get("learning_units", [])
    if not isinstance(source_units, list) or len(source_units) != 24:
        errors.append("cp01_source_unit_count_not_24")
        source_units = []
    source_by_grammar = {
        str(row.get("grammar_unit_id") or ""): row
        for row in source_units
        if isinstance(row, Mapping)
    }
    cp02_by_grammar = {
        str(row.get("grammar_unit_id") or ""): row
        for row in cp02_units
        if isinstance(row, Mapping)
    }
    allowed = set(source_by_grammar)
    if len(allowed) != 24 or set(cp02_by_grammar) != allowed:
        errors.append("source_curriculum_identity_mismatch")
    expected_raz = _raz_expected(raz_registry_package, allowed, errors)

    rows = artifact.get("learning_units", [])
    if not isinstance(rows, list) or len(rows) != 24:
        errors.append("output_learning_unit_count_not_24")
        rows = []
    output_ids = [str(row.get("grammar_unit_id") or "") for row in rows]
    if set(output_ids) != allowed or len(output_ids) != len(set(output_ids)):
        errors.append("second_or_missing_unit_identity_detected")
    if [row.get("sequence_index") for row in rows] != list(range(1, 25)):
        errors.append("unit_sequence_mismatch")

    seen_raz_materials: Counter[str] = Counter()
    m11b_item_count = 0
    m11b_unit_count = 0
    raz_assignment_count = 0
    raz_covered_unit_count = 0
    for row in rows:
        grammar_id = str(row.get("grammar_unit_id") or "")
        source = source_by_grammar.get(grammar_id)
        cp02_source = cp02_by_grammar.get(grammar_id)
        if source is None or cp02_source is None:
            continue
        identity = (
            row.get("learning_unit_id"),
            row.get("sequence_index"),
            row.get("internal_stage"),
            row.get("canonical_egp_row_ids"),
        )
        expected_identity = (
            source.get("learning_unit_id"),
            source.get("sequence_index"),
            source.get("internal_stage"),
            source.get("canonical_egp_row_ids"),
        )
        if identity != expected_identity:
            errors.append(f"unit_identity_drift:{grammar_id}")
        if row.get("cp02_authority_bindings") != cp02_source.get("authority_bindings"):
            errors.append(f"cp02_authority_binding_drift:{grammar_id}")

        m11b = row.get("m11b_reviewed_content_binding", {})
        expected_m11b = _m11b_ids(source)
        if m11b.get("source_task_id") != cp01_artifact.get("source_identity", {}).get("admission_task_id"):
            errors.append(f"m11b_source_task_id_mismatch:{grammar_id}")
        expected_basis = source.get("skill_lanes", {}).get("reading", {}).get("admission_basis")
        if m11b.get("admission_basis") != expected_basis:
            errors.append(f"m11b_admission_basis_mismatch:{grammar_id}")
        actual_m11b = m11b.get("admitted_item_ids_by_skill")
        if actual_m11b != expected_m11b:
            errors.append(f"m11b_item_identity_drift:{grammar_id}")
            actual_m11b = {}
        count = sum(len(ids) for ids in actual_m11b.values()) if isinstance(actual_m11b, Mapping) else 0
        if m11b.get("admitted_item_count") != count:
            errors.append(f"m11b_item_count_mismatch:{grammar_id}")
        expected_status = "BOUND_EXISTING_M11B_REVIEWED_CONTENT" if count else "DEFERRED_NO_M11B_ADMISSION"
        if m11b.get("binding_status") != expected_status:
            errors.append(f"m11b_binding_status_mismatch:{grammar_id}")
        m11b_item_count += count
        m11b_unit_count += count > 0

        raz = row.get("raz_admitted_asset_binding", {})
        materials = raz.get("materials", [])
        actual_material_ids = [
            str(item.get("material_id") or "")
            for item in materials
            if isinstance(item, Mapping)
        ]
        if actual_material_ids != expected_raz.get(grammar_id, []):
            errors.append(f"raz_material_binding_drift:{grammar_id}")
        if raz.get("material_count") != len(materials):
            errors.append(f"raz_material_count_mismatch:{grammar_id}")
        expected_status = "BOUND_EXISTING_RAZ_ADMITTED_ASSETS" if materials else "NO_RAZ_ADMITTED_ASSET_FOR_EXISTING_UNIT"
        if raz.get("binding_status") != expected_status:
            errors.append(f"raz_binding_status_mismatch:{grammar_id}")
        for material in materials:
            material_id = str(material.get("material_id") or "")
            seen_raz_materials[material_id] += 1
            if (
                material.get("grammar_authority_ref") != grammar_id
                or material.get("registry_status") != "PROMOTED_TO_A1_A1PLUS_MATERIAL_REGISTRY"
            ):
                errors.append(f"raz_binding_lineage_invalid:{grammar_id}:{material_id}")
        raz_assignment_count += len(materials)
        raz_covered_unit_count += bool(materials)

    expected_promoted_ids = {
        str(row.get("material_id") or "")
        for row in raz_registry_package.get("promoted_material_registry", [])
        if isinstance(row, Mapping)
    }
    if set(seen_raz_materials) != expected_promoted_ids:
        errors.append("not_every_promoted_raz_material_bound")

    expected_summary = {
        "existing_learning_unit_count": 24,
        "new_learning_unit_count": 0,
        "parallel_curriculum_count": 0,
        "m11b_reviewed_content_unit_count": m11b_unit_count,
        "m11b_reviewed_content_item_count": m11b_item_count,
        "raz_promoted_material_input_count": len(expected_promoted_ids),
        "raz_distinct_bound_material_count": len(seen_raz_materials),
        "raz_material_unit_binding_count": raz_assignment_count,
        "raz_covered_existing_unit_count": raz_covered_unit_count,
    }
    if artifact.get("coverage_summary") != expected_summary:
        errors.append("coverage_summary_not_reconciled")
    if m11b_unit_count != 23 or m11b_item_count != 184:
        errors.append("m11b_reviewed_content_baseline_drift")

    source_identity = artifact.get("source_identity", {})
    expected_source_identity = {
        "cp01_task_id": cp01_artifact.get("task_id"),
        "cp01_sha256": builder._sha256_value(cp01_artifact),
        "cp02_task_id": cp02_artifact.get("task_id"),
        "cp02_sha256": builder._sha256_value(cp02_artifact),
        "m11b_admission_task_id": cp01_artifact.get("source_identity", {}).get("admission_task_id"),
        "m11b_admission_bank_sha256": cp01_artifact.get("source_identity", {}).get("admission_bank_sha256"),
        "raz_registry_task_id": raz_registry_package.get("task_id"),
        "raz_registry_package_sha256": raz_registry_package.get("package_sha256"),
    }
    if source_identity != expected_source_identity:
        errors.append("source_identity_mismatch")

    for key, value in artifact.get("claim_boundaries", {}).items():
        if value is not False:
            errors.append(f"false_claim_boundary:{key}")
    if artifact.get("next_short_step") != builder.NEXT_SHORT_STEP:
        errors.append("next_short_step_mismatch")

    return {
        "task_id": builder.TASK_ID,
        "validation_status": builder.PASS_STATUS if not errors else "FAIL",
        "errors": errors,
        "validation_counts": expected_summary,
        "single_existing_24_unit_curriculum_enforced": not errors,
        "stop_reason": "NONE" if not errors else "VALIDATION_FAILURE",
        "next_short_step": builder.NEXT_SHORT_STEP if not errors else None,
    }


def main() -> int:
    try:
        cp01_artifact = builder._read(builder.CP01_PATH)
        cp02_artifact = builder._read(builder.CP02_PATH)
        registry_package = builder._read(builder.RAZ_REGISTRY_PATH)
        artifact = builder._read(builder.OUTPUT_PATH)
        report = validate_artifact(
            artifact, cp01_artifact, cp02_artifact, registry_package
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["validation_status"] == builder.PASS_STATUS else 1
    except (OSError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
