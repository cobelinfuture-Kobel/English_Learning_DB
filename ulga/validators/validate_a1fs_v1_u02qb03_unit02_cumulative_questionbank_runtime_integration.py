from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_v1_u02qb03_unit02_cumulative_questionbank_runtime_integration as builder,
)


def validate_report(report: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    def req(condition: bool, code: str) -> None:
        if not condition:
            errors.append(code)

    req(report.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_VERSION_INVALID")
    req(report.get("task_id") == builder.TASK_ID, "TASK_ID_INVALID")
    req(report.get("status") == builder.PASS_STATUS, "STATUS_INVALID")

    catalog = report.get("cumulative_questionbank_catalog", {})
    req(catalog.get("unit01_reference_only_item_count") == builder.EXPECTED_UNIT01_CATALOG, "UNIT01_CATALOG_COUNT_INVALID")
    req(catalog.get("unit02_approved_item_count") == builder.EXPECTED_UNIT02_APPROVED, "UNIT02_APPROVED_COUNT_INVALID")
    req(catalog.get("cumulative_catalog_item_count") == builder.EXPECTED_CUMULATIVE_CATALOG, "CUMULATIVE_CATALOG_COUNT_INVALID")
    req(catalog.get("unit01_catalog_mutated") is False, "UNIT01_CATALOG_MUTATED")
    req(catalog.get("unit02_approved_item_identity_mutated") is False, "UNIT02_ITEM_IDENTITY_MUTATED")
    req(catalog.get("parallel_questionbank_created") is False, "PARALLEL_QUESTIONBANK_CREATED")

    eligibility = report.get("runtime_eligibility", {})
    req(eligibility.get("restricted_target_surfaces") == ["beer"], "RUNTIME_RESTRICTED_SURFACE_INVALID")
    req(eligibility.get("approved_assets_deleted") is False, "APPROVED_ASSETS_DELETED")
    req(int(eligibility.get("minimum_runtime_family_pool_depth", 0)) >= builder.MIN_RUNTIME_POOL_DEPTH, "RUNTIME_POOL_DEPTH_INSUFFICIENT")
    family_counts = eligibility.get("runtime_family_pool_counts", {})
    req(set(family_counts) == set(builder.qbc02.TASK_FAMILIES), "RUNTIME_FAMILY_SET_INVALID")

    pattern = report.get("pattern_reconciliation", {})
    req(pattern.get("legacy_raw_pattern_id") == builder.sp02.LEGACY_INVALID_PATTERN_ID, "LEGACY_PATTERN_ID_INVALID")
    req(pattern.get("legacy_raw_binding_count") == builder.sp02.EXPECTED_LEGACY_INVALID_BINDINGS, "LEGACY_BINDING_COUNT_INVALID")
    req(pattern.get("raw_pattern_ids_runtime_authoritative") is False, "RAW_PATTERN_IDS_LEFT_RUNTIME_AUTHORITATIVE")

    runtime = report.get("runtime_form_contract", {})
    req(runtime.get("form_count") == builder.EXPECTED_FORMS, "FORM_COUNT_INVALID")
    req(runtime.get("scene_slots_per_form") == builder.EXPECTED_SCENE_SLOTS, "SCENE_SLOT_COUNT_INVALID")
    req(runtime.get("task_family_count") == builder.EXPECTED_TASK_FAMILIES, "TASK_FAMILY_COUNT_INVALID")
    req(runtime.get("activities_per_form") == builder.EXPECTED_ACTIVITIES_PER_FORM, "ACTIVITIES_PER_FORM_INVALID")
    req(runtime.get("runtime_occurrence_count") == builder.EXPECTED_RUNTIME_OCCURRENCES, "RUNTIME_OCCURRENCE_COUNT_INVALID")
    req(runtime.get("all_slots_retain_three_legal_candidates") is True, "THREE_CANDIDATES_PER_SLOT_NOT_PRESERVED")
    req(runtime.get("within_form_same_task_family_selected_item_reuse") is False, "WITHIN_FORM_FAMILY_REUSE_CLAIM_INVALID")
    req(runtime.get("runtime_connected") is True, "RUNTIME_NOT_CONNECTED")
    req(runtime.get("final_forms_materialized") is True, "FINAL_FORMS_NOT_MATERIALIZED")

    rows = report.get("runtime_occurrences", [])
    req(len(rows) == builder.EXPECTED_RUNTIME_OCCURRENCES, "RUNTIME_ROWS_INVALID")
    occurrence_ids = [str(row.get("runtime_occurrence_id") or "") for row in rows]
    req(all(occurrence_ids) and len(set(occurrence_ids)) == len(occurrence_ids), "RUNTIME_OCCURRENCE_IDENTITY_INVALID")
    req(all(len(row.get("candidate_ids") or []) == builder.MIN_CANDIDATES_PER_SLOT for row in rows), "RUNTIME_SLOT_CANDIDATE_COUNT_INVALID")
    req(all(row.get("selected_item_id") in (row.get("candidate_ids") or []) for row in rows), "SELECTED_ITEM_OUTSIDE_SLOT_CANDIDATES")
    req(all(str(row.get("target_singular") or "") not in builder.RUNTIME_RESTRICTED_SURFACES for row in rows), "RESTRICTED_SURFACE_RUNTIME_LEAK")
    req(all(row.get("runtime_pattern_lineage", {}).get("runtime_may_consume_raw_pattern_ids") is False for row in rows), "RAW_PATTERN_RUNTIME_CONSUMPTION_DETECTED")

    for form_number in range(1, builder.EXPECTED_FORMS + 1):
        form_rows = [row for row in rows if row.get("form_number") == form_number]
        req(len(form_rows) == builder.EXPECTED_ACTIVITIES_PER_FORM, f"FORM_ACTIVITY_COUNT_INVALID:{form_number}")
        counts = Counter(str(row.get("task_family")) for row in form_rows)
        req(set(counts) == set(builder.qbc02.TASK_FAMILIES) and all(counts[family] == builder.EXPECTED_SCENE_SLOTS for family in counts), f"FORM_TASK_FAMILY_DISTRIBUTION_INVALID:{form_number}")
        for family in builder.qbc02.TASK_FAMILIES:
            ids = [str(row.get("selected_item_id")) for row in form_rows if row.get("task_family") == family]
            req(len(ids) == builder.EXPECTED_SCENE_SLOTS and len(set(ids)) == builder.EXPECTED_SCENE_SLOTS, f"WITHIN_FORM_SELECTED_REUSE:{form_number}:{family}")

    sentence = report.get("sentence_asset_integration", {})
    req(set(sentence.get("binding_required_task_families", [])) == builder.SENTENCE_BINDING_REQUIRED_FAMILIES, "SENTENCE_BINDING_REQUIRED_FAMILIES_INVALID")
    expected_bound = builder.EXPECTED_FORMS * builder.EXPECTED_SCENE_SLOTS * len(builder.SENTENCE_BINDING_REQUIRED_FAMILIES)
    req(sentence.get("bound_runtime_occurrence_count") == expected_bound, "BOUND_SENTENCE_OCCURRENCE_COUNT_INVALID")
    bound = [row for row in rows if row.get("task_family") in builder.SENTENCE_BINDING_REQUIRED_FAMILIES]
    req(all(row.get("sentence_asset_binding", {}).get("status") == "BOUND_CANONICAL_Q6_SENTENCE_ASSET" and row.get("sentence_asset_binding", {}).get("sentence_asset_id") for row in bound), "REQUIRED_Q6_SENTENCE_BINDING_MISSING")
    nonbound = [row for row in rows if row.get("task_family") not in builder.SENTENCE_BINDING_REQUIRED_FAMILIES]
    req(all(row.get("sentence_asset_binding", {}).get("status") == "NOT_REQUIRED_FOR_TASK_FAMILY" for row in nonbound), "UNEXPECTED_SENTENCE_BINDING_POLICY")
    req(sentence.get("q6_assets_mutated") is False, "Q6_ASSETS_MUTATED")

    boundaries = report.get("claim_boundaries", {})
    for key in (
        "questionbank_items_created",
        "unit01_runtime_or_catalog_mutated",
        "unit02_qbc02_raw_payload_mutated",
        "unit02_sp02_authority_mutated",
        "unit02_sentence_assets_mutated",
        "new_selector_engine_created",
        "learner_session_state_materialized",
        "learner_state_mutated",
        "canonical_scene_authority_mutated",
        "a2_unlocked",
    ):
        req(boundaries.get(key) is False, f"CLAIM_BOUNDARY_INVALID:{key}")

    req(report.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_SHORT_STEP_INVALID")
    return {
        "validator_id": "validate_a1fs_v1_u02qb03_unit02_cumulative_questionbank_runtime_integration_v1",
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
    }
