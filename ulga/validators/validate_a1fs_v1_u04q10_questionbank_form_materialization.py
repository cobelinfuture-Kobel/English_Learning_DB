#!/usr/bin/env python3
"""Validate Unit04 Q10 20x40 QuestionBank and Form materialization."""
from __future__ import annotations

from collections import Counter
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u04q10_questionbank_form_materialization as builder

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U04Q10_QUESTIONBANK_FORM_MATERIALIZATION_VALIDATOR"


class U04Q10ValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise U04Q10ValidationError(code)


def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def _source_evidence_sets():
    src = builder._sources()
    repair = src["repair"]
    reuse_pairs = {
        (str(row["sentence_id"]), str(row["relation_surface"]), str(scene_ref))
        for row in repair["resolved_existing_sentence_scene_evidence"]
        for scene_ref in row["source_scene_refs"]
    }
    at_ids = {str(row["sentence_id"]) for row in repair["at_text_bound_admitted_sentence_evidence"]}
    q07 = {
        (str(row["bound_sentence_id"]), str(row["relation_surface"]), str(row["scene_ref_id"])): row
        for row in src["q07"]["micro_scenes"]
        if str(row["relation_surface"]) in builder.NEW_RELATIONS
    }
    return reuse_pairs, at_ids, q07


def _validate_identity_and_denominators(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_INVALID")
    contract = dict(payload.get("materialization_contract") or {})
    require(contract.get("form_count") == 20, "FORM_COUNT_INVALID")
    require(contract.get("questions_per_form") == 40, "QUESTIONS_PER_FORM_INVALID")
    require(contract.get("questionbank_item_count") == 800, "QUESTIONBANK_COUNT_INVALID")
    require(contract.get("runtime_occurrence_count") == 800, "RUNTIME_COUNT_INVALID")
    require(contract.get("candidate_count_per_slot") == 3, "CANDIDATE_COUNT_INVALID")
    require(contract.get("section_counts_per_form") == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}, "SECTION_CONTRACT_INVALID")
    require(contract.get("task_family_count") == 10, "TASK_FAMILY_DENOMINATOR_INVALID")
    require(contract.get("target_relation_count") == 8, "TARGET_RELATION_DENOMINATOR_INVALID")
    require(contract.get("communicative_function_count") == 6, "FUNCTION_DENOMINATOR_INVALID")
    require(len(items) == 800, "ITEM_ROWS_INVALID")
    require(len({str(row["item_id"]) for row in items}) == 800, "ITEM_ID_COLLISION")
    require(len({str(row["semantic_signature"]) for row in items}) == 800, "SEMANTIC_SIGNATURE_COLLISION")


def _validate_forms(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    forms = list(payload.get("forms") or [])
    require(len(forms) == 20, "FORM_ROWS_INVALID")
    require(len({str(row["form_id"]) for row in forms}) == 20, "FORM_ID_COLLISION")
    item_ids = {str(row["item_id"]) for row in items}
    for form_number in range(1, 21):
        rows = [row for row in items if int(row["form_number"]) == form_number]
        require(len(rows) == 40, f"FORM_40_INVALID:{form_number}")
        require(Counter(str(row["section"]) for row in rows) == Counter({"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}), f"FORM_SECTION_INVALID:{form_number}")
        require({str(row["progression_role"]) for row in rows} == {builder._stage(form_number)}, f"FORM_STAGE_INVALID:{form_number}")
        form = next(row for row in forms if int(row["form_number"]) == form_number)
        require(form["question_count"] == 40, f"FORM_REPORT_COUNT_INVALID:{form_number}")
        require(form["section_counts"] == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}, f"FORM_REPORT_SECTION_INVALID:{form_number}")
        require(str(form["progression_role"]) == builder._stage(form_number), f"FORM_REPORT_STAGE_INVALID:{form_number}")
        require(len(form["item_ids"]) == 40 and set(form["item_ids"]).issubset(item_ids), f"FORM_ITEM_BINDING_INVALID:{form_number}")


def _validate_authority_coverage(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    families = {str(row["task_family_id"]) for row in items}
    relations = {str(row["relation_surface"]) for row in items}
    functions = {str(row["communicative_function_id"]) for row in items}
    require(families == set(builder._families()), f"TASK_FAMILY_COVERAGE_INVALID:{sorted(families)}")
    require(relations == set(builder.TARGET_RELATIONS), f"TARGET_RELATION_COVERAGE_INVALID:{sorted(relations)}")
    q08_functions = {str(row["function_id"]) for row in builder._sources()["q08"]["communicative_functions"]}
    require(len(q08_functions) == 6, "Q08_FUNCTION_AUTHORITY_DRIFT")
    require(functions == q08_functions, f"FUNCTION_COVERAGE_INVALID:{sorted(functions)}")
    coverage = dict(payload.get("coverage") or {})
    require(coverage.get("task_family_coverage") == "10/10", "TASK_FAMILY_COVERAGE_REPORT_INVALID")
    require(coverage.get("target_relation_coverage") == "8/8", "TARGET_RELATION_COVERAGE_REPORT_INVALID")
    require(coverage.get("communicative_function_coverage") == "6/6", "FUNCTION_COVERAGE_REPORT_INVALID")
    require(coverage.get("questionbank_item_count") == 800, "ITEM_COVERAGE_REPORT_INVALID")
    require(coverage.get("unique_item_id_count") == 800, "UNIQUE_ITEM_REPORT_INVALID")
    require(coverage.get("unique_semantic_signature_count") == 800, "UNIQUE_SEMANTIC_REPORT_INVALID")
    require(coverage.get("exact_semantic_duplicate_count") == 0, "SEMANTIC_DUPLICATE_REPORT_INVALID")
    require(coverage.get("support_relation_item_count") == 0, "SUPPORT_RELATION_PROMOTED")


def _validate_evidence_and_at_repair(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    reuse_pairs, at_ids, q07 = _source_evidence_sets()
    at_rows = [row for row in items if row["relation_surface"] == "at"]
    require(at_rows, "AT_COVERAGE_MISSING")
    for row in items:
        relation = str(row["relation_surface"])
        require(row.get("target_relation_evidence") is True, f"TARGET_EVIDENCE_FALSE:{row['item_id']}")
        require(row.get("support_relation") is False, f"SUPPORT_RELATION_PROMOTION:{row['item_id']}")
        require(row.get("creates_new_grammar_authority") is False, f"NEW_GRAMMAR_AUTHORITY:{row['item_id']}")
        require(row.get("creates_new_sentence_identity") is False, f"NEW_SENTENCE_IDENTITY:{row['item_id']}")
        require(row.get("creates_new_scene_identity") is False, f"NEW_SCENE_IDENTITY:{row['item_id']}")
        require(row.get("directional_from_into_to_activated") is False, f"DIRECTIONAL_SCOPE_OPENED:{row['item_id']}")
        require(row.get("a2_unlocked") is False, f"A2_UNLOCKED:{row['item_id']}")
        if relation == "at":
            require(str(row["task_family_id"]) in builder.AT_ALLOWED_FAMILIES, f"AT_FAMILY_FORBIDDEN:{row['item_id']}")
            require(str(row["communicative_function_id"]) == builder.AT_CF, f"AT_FUNCTION_FORBIDDEN:{row['item_id']}")
            require(row.get("evidence_mode") == "PRIOR_ADMITTED_TEXT_BOUND_POINT_PLACE_EVIDENCE", f"AT_EVIDENCE_MODE_INVALID:{row['item_id']}")
            require(row.get("scene_ref_id") is None and row.get("source_scene_ref") is None, f"AT_SCENE_REF_FORBIDDEN:{row['item_id']}")
            require(str(row["source_sentence_id"]) in at_ids, f"AT_SOURCE_SENTENCE_INVALID:{row['item_id']}")
            require(not row.get("options"), f"AT_SELECTED_RESPONSE_FORBIDDEN:{row['item_id']}")
            require(str(row["evidence_role"]) in {"FORM_CONSTRUCTION_WITH_GIVEN_RELATION", "OPEN_PRODUCTIVE_RESPONSE_WITH_POINT_PLACE_CUE"}, f"AT_EVIDENCE_ROLE_INVALID:{row['item_id']}")
        elif relation in builder.REUSE_RELATIONS:
            key = (str(row["source_sentence_id"]), relation, str(row["scene_ref_id"]))
            require(key in reuse_pairs, f"REUSE_PAIR_NOT_AUTHORIZED:{row['item_id']}:{key}")
            require(row.get("evidence_mode") == "EXISTING_SENTENCE_SCENE_PAIR", f"REUSE_MODE_INVALID:{row['item_id']}")
        elif relation in builder.NEW_RELATIONS:
            key = (str(row["source_sentence_id"]), relation, str(row["scene_ref_id"]))
            require(key in q07, f"Q07_SCENE_BINDING_INVALID:{row['item_id']}:{key}")
            require(row.get("evidence_mode") == "Q07_UNIT04_SCENE_BOUND", f"Q07_MODE_INVALID:{row['item_id']}")
            if relation == "between":
                landmarks = list(row.get("reference_landmarks") or [])
                require(len(landmarks) == 2 and len(set(landmarks)) == 2, f"BETWEEN_LANDMARK_INVALID:{row['item_id']}")
        else:
            raise U04Q10ValidationError(f"UNKNOWN_TARGET_RELATION:{relation}")
    coverage = dict(payload.get("coverage") or {})
    require(coverage.get("at_scene_ref_count") == 0, "AT_SCENE_REF_REPORT_NONZERO")
    require(coverage.get("fabricated_scene_ref_count") == 0, "FABRICATED_SCENE_REF_NONZERO")
    repair = dict(payload.get("repair_enforcement") or {})
    require(repair.get("at_evidence_mode") == "PRIOR_ADMITTED_TEXT_BOUND_POINT_PLACE_EVIDENCE", "AT_REPAIR_MODE_DRIFT")
    require(set(repair.get("at_allowed_task_family_ids") or []) == builder.AT_ALLOWED_FAMILIES, "AT_REPAIR_FAMILY_DRIFT")
    require(repair.get("at_allowed_communicative_function_ids") == [builder.AT_CF], "AT_REPAIR_FUNCTION_DRIFT")
    require(repair.get("at_scene_bound_item_allowed") is False, "AT_SCENE_BOUND_REOPENED")
    require(repair.get("at_picture_relation_selection_allowed") is False, "AT_PICTURE_SELECTION_REOPENED")
    require(repair.get("at_in_forced_single_answer_contrast_allowed") is False, "AT_IN_FORCED_CONTRAST_REOPENED")
    require(repair.get("fabricated_scene_ref_count") == 0, "REPAIR_FABRICATED_SCENE_REF_NONZERO")


def _validate_answerability(items: list[Mapping[str, Any]]) -> None:
    for row in items:
        options = list(row.get("options") or [])
        if options:
            require(len(options) == len(set(options)), f"OPTION_DUPLICATION:{row['item_id']}")
            require(row.get("correct_answer") in options, f"CORRECT_ANSWER_NOT_OPTION:{row['item_id']}")
            stimulus = row.get("stimulus") or {}
            require(bool(stimulus.get("unique_meaning_cue")), f"SELECTED_RESPONSE_UNIQUE_CUE_MISSING:{row['item_id']}")
            require(row.get("single_answer_unique_cue_required") is True, f"UNIQUE_CUE_FLAG_FALSE:{row['item_id']}")
            require(str(row["relation_surface"]) != "at", f"AT_SELECTED_RESPONSE:{row['item_id']}")
        response = dict(row.get("response_contract") or {})
        family = str(row["task_family_id"])
        cf = str(row["communicative_function_id"])
        if family == "U04-TF09_PRODUCTIVE_RESPONSE" or (family == "U04-TF10_TRANSFER" and cf in {"U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION", "U04-CF05_DESCRIBE_SPATIAL_SCENE"}):
            require(response.get("scoring_mode") == "HUMAN_REVIEW", f"OPEN_RESPONSE_NOT_HUMAN_REVIEW:{row['item_id']}")
            require(response.get("single_answer_required") is False, f"OPEN_RESPONSE_FORCED_SINGLE:{row['item_id']}")
        require(row.get("q03_overlap_guards_preserved") is True, f"OVERLAP_GUARD_MISSING:{row['item_id']}")


def _validate_runtime(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    runtime = list(payload.get("runtime_bindings") or [])
    require(len(runtime) == 800, "RUNTIME_ROWS_INVALID")
    require(len({str(row["slot_id"]) for row in runtime}) == 800, "RUNTIME_SLOT_COLLISION")
    require(len({str(row["selected_item_id"]) for row in runtime}) == 800, "RUNTIME_SELECTED_COLLISION")
    by_id = {str(row["item_id"]): row for row in items}
    for row in runtime:
        candidates = list(row.get("candidate_ids") or [])
        require(len(candidates) == 3 and len(set(candidates)) == 3, f"THREE_CANDIDATE_CONTRACT_INVALID:{row['slot_id']}")
        require(all(candidate in by_id for candidate in candidates), f"CANDIDATE_NOT_IN_BANK:{row['slot_id']}")
        require(str(row["selected_item_id"]) == candidates[0], f"SELECTED_NOT_FIRST_CANDIDATE:{row['slot_id']}")
        require(all(str(by_id[candidate]["task_family_id"]) == str(row["task_family_id"]) for candidate in candidates), f"CROSS_FAMILY_CANDIDATE:{row['slot_id']}")


def _validate_boundaries(payload: Mapping[str, Any]) -> None:
    boundaries = dict(payload.get("boundaries") or {})
    expected_false = {
        "q03_q09_authority_mutated",
        "q07_micro_scene_rows_modified",
        "q08_communicative_function_inventory_modified",
        "q09_task_family_inventory_modified",
        "new_grammar_authority_created",
        "new_sentence_identity_created",
        "new_scene_identity_created",
        "support_relations_promoted_to_target",
        "directional_from_into_to_activated",
        "a2_unlocked",
    }
    require(set(boundaries) == expected_false, "BOUNDARY_KEY_DRIFT")
    require(all(boundaries[key] is False for key in expected_false), "BOUNDARY_FALSE_CONTRACT_DRIFT")
    require(payload.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_SHORT_STEP_DRIFT")


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    items = list(payload.get("questionbank_items") or [])
    _validate_identity_and_denominators(payload, items)
    _validate_forms(payload, items)
    _validate_authority_coverage(payload, items)
    _validate_evidence_and_at_repair(payload, items)
    _validate_answerability(items)
    _validate_runtime(payload, items)
    _validate_boundaries(payload)
    return {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "questionbank_items": 800,
        "forms": 20,
        "task_families": "10/10",
        "target_relations": "8/8",
        "communicative_functions": "6/6",
        "at_scene_ref_count": 0,
        "fabricated_scene_ref_count": 0,
    }


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "CANDIDATE_ROLE_INVALID")
    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "CANDIDATE_PAYLOAD_INVALID")
    validate_payload(payload)
    return validation_receipt(payload)


def main() -> int:
    report = validate_payload(builder.build_export_payload())
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
