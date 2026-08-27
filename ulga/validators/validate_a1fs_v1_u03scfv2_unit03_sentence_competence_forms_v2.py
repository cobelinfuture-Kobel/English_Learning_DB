#!/usr/bin/env python3
"""Validate Unit03 Sentence-Competence Forms V2 20x40 materialization."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u03scfv2_unit03_sentence_competence_forms_v2_800_materialization
    as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U03SCFV2_800_MATERIALIZATION_VALIDATOR"


class U03SCFV2ValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise U03SCFV2ValidationError(code)


def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_INVALID")

    preservation = payload.get("unit02_preservation", {})
    require(preservation.get("form_count") == 16, "U02_FORM_COUNT_DRIFT")
    require(preservation.get("runtime_occurrence_count") == 640, "U02_RUNTIME_DRIFT")
    require(preservation.get("approved_item_count") == 1730, "U02_ITEM_COUNT_DRIFT")
    require(preservation.get("cumulative_catalog_item_count") == 2204, "U02_CUMULATIVE_DRIFT")
    require(preservation.get("unit02_16x40_mutated") is False, "U02_16X40_MUTATED")

    assets = payload.get("sentence_asset_delta", {})
    asset_rows = assets.get("assets")
    require(assets.get("asset_count") == 80, "U03_SENTENCE_ASSET_COUNT_INVALID")
    require(isinstance(asset_rows, list) and len(asset_rows) == 80, "U03_SENTENCE_ASSET_ROWS_INVALID")
    require(len({row["sentence_id"] for row in asset_rows}) == 80, "U03_SENTENCE_ASSET_ID_COLLISION")
    require(len({row["normalized_text"] for row in asset_rows}) == 80, "U03_SENTENCE_ASSET_TEXT_COLLISION")
    require(all(row.get("canonical_admission_status") == "ADMITTED" for row in asset_rows), "U03_SENTENCE_ASSET_NOT_ADMITTED")
    require(all(row.get("context_bound") is True for row in asset_rows), "U03_SENTENCE_ASSET_NOT_CONTEXT_BOUND")
    require(all(row.get("pattern_binding_status") == "NO_NEW_UNIT03_PATTERN_FAMILY_ADMITTED" for row in asset_rows), "U03_PATTERN_BOUNDARY_DRIFT")
    require(assets.get("parallel_sentence_asset_schema_created") is False, "PARALLEL_SENTENCE_SCHEMA_CREATED")

    qb = payload.get("questionbank_delta", {})
    new_items = qb.get("unit03_new_items")
    require(qb.get("unit03_new_item_count") == 400, "U03_QB_DELTA_COUNT_INVALID")
    require(isinstance(new_items, list) and len(new_items) == 400, "U03_QB_ROWS_INVALID")
    require(len({row["item_id"] for row in new_items}) == 400, "U03_QB_ID_COLLISION")
    require(len({row["semantic_signature"] for row in new_items}) == 400, "U03_QB_SEMANTIC_COLLISION")
    require(qb.get("inherited_cumulative_catalog_count") == 2204, "INHERITED_CATALOG_INVALID")
    require(qb.get("cumulative_catalog_count_after_unit03") == 2604, "U03_CUMULATIVE_CATALOG_INVALID")
    require(qb.get("parallel_questionbank_created") is False, "PARALLEL_QB_CREATED")
    require(Counter(row["task_family"] for row in new_items) == Counter({family: 80 for _, family in builder.SECTION_FAMILIES}), "U03_TASK_FAMILY_DISTRIBUTION_INVALID")
    require(all((row.get("sentence_asset_binding") or {}).get("status") == "BOUND_CANONICAL_UNIT03_SENTENCE_ASSET" for row in new_items), "U03_QB_SENTENCE_BINDING_INVALID")

    contract = payload.get("runtime_form_contract", {})
    require(contract.get("form_count") == 20, "FORM_COUNT_INVALID")
    require(contract.get("activities_per_form") == 40, "ACTIVITIES_PER_FORM_INVALID")
    require(contract.get("runtime_occurrence_count") == 800, "RUNTIME_COUNT_INVALID")
    require(contract.get("inherited_runtime_binding_count") == 400, "INHERITED_RUNTIME_COUNT_INVALID")
    require(contract.get("unit03_delta_runtime_binding_count") == 400, "U03_DELTA_RUNTIME_COUNT_INVALID")
    require(contract.get("sections_per_form") == 5, "SECTION_COUNT_INVALID")
    require(contract.get("activities_per_section") == 8, "SECTION_ACTIVITY_COUNT_INVALID")
    require(contract.get("candidate_count_per_slot") == 3, "CANDIDATE_COUNT_INVALID")
    require(contract.get("global_800_distinct_selected_item_proof") is True, "GLOBAL_800_DISTINCT_NOT_PROVEN")
    require(contract.get("parallel_selector_created") is False, "PARALLEL_SELECTOR_CREATED")
    require(contract.get("parallel_runtime_authority_created") is False, "PARALLEL_RUNTIME_CREATED")

    runtime = payload.get("runtime_bindings")
    require(isinstance(runtime, list) and len(runtime) == 800, "RUNTIME_ROWS_INVALID")
    require(len({row["runtime_occurrence_id"] for row in runtime}) == 800, "RUNTIME_ID_COLLISION")
    require(len({row["selected_item_id"] for row in runtime}) == 800, "SELECTED_ITEM_COLLISION")
    require(all(len(row["candidate_ids"]) == 3 and len(set(row["candidate_ids"])) == 3 for row in runtime), "THREE_CANDIDATE_CONTRACT_INVALID")
    require(all(row["selected_item_id"] == row["candidate_ids"][0] for row in runtime), "FIRST_CANDIDATE_SELECTION_INVALID")
    require(Counter(row["questionbank_source"] for row in runtime) == Counter({"INHERITED_CURRENT_U01_U02": 400, "UNIT03_DELTA": 400}), "RUNTIME_SOURCE_DISTRIBUTION_INVALID")
    require(Counter(row["progression_stage"] for row in runtime) == Counter({stage: 160 for stage in builder.STAGE_BY_FORMS}), "STAGE_DISTRIBUTION_INVALID")

    for form_number in range(1, 21):
        form_rows = [row for row in runtime if row["form_number"] == form_number]
        require(len(form_rows) == 40, f"FORM_RUNTIME_COUNT_INVALID:{form_number}")
        require(Counter(row["section"] for row in form_rows) == Counter({section: 8 for section, _ in builder.SECTION_FAMILIES}), f"FORM_SECTION_DISTRIBUTION_INVALID:{form_number}")
        require(Counter(row["questionbank_source"] for row in form_rows) == Counter({"INHERITED_CURRENT_U01_U02": 20, "UNIT03_DELTA": 20}), f"FORM_SOURCE_MIX_INVALID:{form_number}")

    forms = payload.get("student_forms")
    require(isinstance(forms, list) and len(forms) == 20, "STUDENT_FORM_COUNT_INVALID")
    require(sum(form["learner_visible_activity_count"] for form in forms) == 800, "LEARNER_VISIBLE_COUNT_INVALID")
    require(all(form["section_count"] == 5 for form in forms), "LEARNER_SECTION_COUNT_INVALID")
    for form in forms:
        builder.u01_learner._assert_no_answer_leak(form)

    boundaries = payload.get("claim_boundaries", {})
    for key in (
        "unit02_forms01_16_mutated",
        "unit01_unit02_questionbank_items_mutated",
        "second_questionbank_authority_created",
        "second_selector_created",
        "second_renderer_created",
        "parallel_sentence_asset_schema_created",
        "canonical_sentence_pattern_authority_mutated",
        "learner_state_mutated",
        "a2_unlocked",
    ):
        require(boundaries.get(key) is False, f"BOUNDARY_INVALID:{key}")

    return {
        "validation_status": "PASS",
        "error_count": 0,
        "unit03_sentence_assets": 80,
        "unit03_new_questionbank_items": 400,
        "runtime_bindings": 800,
        "forms": 20,
        "activities_per_form": 40,
        "global_800_distinct": True,
    }


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "CANDIDATE_ROLE_INVALID")
    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "CANDIDATE_PAYLOAD_INVALID")
    validate_payload(payload)
    return validation_receipt(payload)


def validate_approved(candidate: Mapping[str, Any], approved: Mapping[str, Any]) -> dict[str, Any]:
    require(approved.get("artifact_role") == policy_artifact.APPROVED_ROLE, "APPROVED_ROLE_INVALID")
    require(approved.get("payload") == candidate.get("payload"), "APPROVED_PAYLOAD_DRIFT")
    return validate_payload(approved["payload"])


def main() -> int:
    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    report = validate_approved(candidate, approved)
    print(f"STATUS={report['validation_status']}")
    print(f"ERROR_COUNT={report['error_count']}")
    print(f"UNIT03_SENTENCE_ASSETS={report['unit03_sentence_assets']}")
    print(f"UNIT03_NEW_QB_ITEMS={report['unit03_new_questionbank_items']}")
    print(f"RUNTIME_BINDINGS={report['runtime_bindings']}")
    print(f"FORMS={report['forms']}")
    print(f"ACTIVITIES_PER_FORM={report['activities_per_form']}")
    print(f"GLOBAL_800_DISTINCT={report['global_800_distinct']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
