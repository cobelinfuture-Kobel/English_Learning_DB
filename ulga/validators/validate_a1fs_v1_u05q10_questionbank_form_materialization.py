from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import build_a1fs_v1_u05q10_questionbank_form_materialization as builder

VALIDATOR_ID = "validate_a1fs_v1_u05q10_questionbank_form_materialization_v1"


class U05Q10ValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise U05Q10ValidationError(message)


def _validate_identity_and_counts(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
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
    require(contract.get("section_counts_per_form") == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}, "SECTION_COUNTS_INVALID")
    require(contract.get("task_family_count") == 10, "TASK_FAMILY_COUNT_INVALID")
    require(contract.get("communicative_function_count") == 7, "FUNCTION_COUNT_INVALID")
    require(contract.get("frame_count") == 6, "FRAME_COUNT_INVALID")
    require(contract.get("subject_class_count") == 9, "SUBJECT_CLASS_COUNT_INVALID")
    require(len(items) == 800, "ITEM_ROW_COUNT_INVALID")
    require(len({str(row["item_id"]) for row in items}) == 800, "ITEM_ID_COLLISION")
    require(len({str(row["item_semantic_signature"]) for row in items}) == 800, "ITEM_SIGNATURE_COLLISION")
    require(
        contract.get("q06_source_identity_policy")
        == "DISTINCT_WITHIN_TASK_FAMILY_CROSS_FAMILY_REUSE_ALLOWED",
        "Q06_SOURCE_IDENTITY_POLICY_INVALID",
    )
    by_family: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in items:
        by_family[str(row["task_family_id"])].append(row)
    for family_id, family_rows in by_family.items():
        require(
            len(family_rows) == len({str(row["q06_identity"]) for row in family_rows}),
            f"SAME_FAMILY_Q06_SOURCE_REUSE:{family_id}",
        )


def _validate_forms(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    forms = list(payload.get("forms") or [])
    require(len(forms) == 20, "FORM_ROW_COUNT_INVALID")
    require(len({str(row["form_id"]) for row in forms}) == 20, "FORM_ID_COLLISION")
    item_ids = {str(row["item_id"]) for row in items}
    for form_number in range(1, 21):
        rows = [row for row in items if int(row["form_number"]) == form_number]
        require(len(rows) == 40, f"FORM_ITEM_COUNT_INVALID:{form_number}")
        require(
            Counter(str(row["section"]) for row in rows) == Counter({"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}),
            f"FORM_SECTION_COUNT_INVALID:{form_number}",
        )
        require({str(row["progression_role"]) for row in rows} == {builder._stage(form_number)}, f"FORM_STAGE_INVALID:{form_number}")
        form = next(row for row in forms if int(row["form_number"]) == form_number)
        require(form["question_count"] == 40, f"FORM_REPORT_COUNT_INVALID:{form_number}")
        require(form["section_counts"] == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}, f"FORM_REPORT_SECTION_INVALID:{form_number}")
        require(str(form["progression_role"]) == builder._stage(form_number), f"FORM_REPORT_STAGE_INVALID:{form_number}")
        require(len(form["item_ids"]) == 40 and set(form["item_ids"]).issubset(item_ids), f"FORM_ITEM_BINDING_INVALID:{form_number}")


def _validate_authority_coverage(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    src = builder._sources()
    families = builder._families(src)
    expected_functions = {str(row["function_id"]) for row in src["q08"]["communicative_functions"]}
    expected_frames = set(src["q08"]["frame_function_compatibility"])
    expected_subjects = set(src["q06"]["coverage"]["subject_class_counts"])

    actual_families = {str(row["task_family_id"]) for row in items}
    actual_functions = {str(row["communicative_function_id"]) for row in items}
    actual_frames = {str(row["frame_id"]) for row in items}
    actual_subjects = {str(row["subject_class"]) for row in items}
    actual_polarities = {str(row["polarity"]) for row in items}
    actual_complements = {builder._frame_base(str(row["frame_id"])) for row in items}

    require(actual_families == set(families), "TASK_FAMILY_COVERAGE_INVALID")
    require(actual_functions == expected_functions, "FUNCTION_COVERAGE_INVALID")
    require(actual_frames == expected_frames, "FRAME_COVERAGE_INVALID")
    require(actual_subjects == expected_subjects, "SUBJECT_CLASS_COVERAGE_INVALID")
    require(actual_polarities == {"AFFIRMATIVE", "NEGATIVE"}, "POLARITY_COVERAGE_INVALID")
    require(actual_complements == {"NP", "ADJ", "PLACE"}, "COMPLEMENT_COVERAGE_INVALID")

    coverage = dict(payload.get("coverage") or {})
    require(coverage.get("task_family_coverage") == "10/10", "TASK_FAMILY_REPORT_INVALID")
    require(coverage.get("communicative_function_coverage") == "7/7", "FUNCTION_REPORT_INVALID")
    require(coverage.get("frame_coverage") == "6/6", "FRAME_REPORT_INVALID")
    require(coverage.get("subject_class_coverage") == "9/9", "SUBJECT_REPORT_INVALID")
    require(coverage.get("polarity_coverage") == "2/2", "POLARITY_REPORT_INVALID")
    require(coverage.get("complement_class_coverage") == "3/3", "COMPLEMENT_REPORT_INVALID")
    variants = dict(coverage.get("surface_variant_coverage") or {})
    require(variants.get("full_count", 0) > 0, "FULL_VARIANT_COVERAGE_MISSING")
    require(variants.get("contracted_count", 0) + variants.get("contracted_alt_count", 0) > 0, "CONTRACTED_VARIANT_COVERAGE_MISSING")
    require(variants.get("surface_variant_is_new_semantics") is False, "SURFACE_VARIANT_PROMOTED_TO_NEW_SEMANTICS")
    require(
        coverage.get("q06_source_reuse_policy")
        == "DISTINCT_WITHIN_TASK_FAMILY_CROSS_FAMILY_REUSE_ALLOWED",
        "Q06_SOURCE_REUSE_POLICY_REPORT_INVALID",
    )
    require(coverage.get("same_family_duplicate_q06_source_count") == 0, "SAME_FAMILY_Q06_SOURCE_DUPLICATE_REPORT_INVALID")
    require(
        0 < int(coverage.get("unique_q06_source_identity_count", 0)) <= 800,
        "UNIQUE_Q06_SOURCE_IDENTITY_REPORT_INVALID",
    )
    require(
        int(coverage.get("cross_family_reused_q06_source_identity_count", 0)) >= 0,
        "CROSS_FAMILY_REUSE_REPORT_INVALID",
    )
    require(
        1 <= int(coverage.get("max_task_families_per_q06_source", 0)) <= 10,
        "MAX_TASK_FAMILIES_PER_Q06_SOURCE_INVALID",
    )

    for row in items:
        family = families[str(row["task_family_id"])]
        function_id = str(row["communicative_function_id"])
        frame = str(row["frame_id"])
        require(function_id in family["allowed_function_ids"], f"FUNCTION_NOT_ALLOWED_BY_FAMILY:{row['item_id']}")
        require(function_id in src["q08"]["frame_function_compatibility"][frame], f"FUNCTION_NOT_ALLOWED_BY_FRAME:{row['item_id']}")


def _validate_q06_q07_binding_rules(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    src = builder._sources()
    bindings = builder._binding_map(src)
    scenes = builder._scene_map(src)
    q06_by_id = {_q06_id(row): row for row in builder._q06_rows(src)}
    for row in items:
        qid = str(row["q06_identity"])
        require(qid in q06_by_id, f"Q06_SOURCE_NOT_FOUND:{row['item_id']}")
        source = q06_by_id[qid]
        require(row["frame_id"] == source["frame_id"], f"Q06_FRAME_DRIFT:{row['item_id']}")
        require(row["polarity"] == source["polarity"], f"Q06_POLARITY_DRIFT:{row['item_id']}")
        require(row["subject_class"] == source["subject_class"], f"Q06_SUBJECT_DRIFT:{row['item_id']}")
        require(row["surface_variant"] == source["surface_variant"], f"Q06_VARIANT_DRIFT:{row['item_id']}")
        if source["requires_context_binding"]:
            require(qid in bindings, f"Q07_BINDING_MISSING:{row['item_id']}")
            scene_ref = str(bindings[qid]["scene_ref_id"])
            require(row["scene_ref_id"] == scene_ref, f"Q07_SCENE_REF_DRIFT:{row['item_id']}")
            require(scene_ref in scenes, f"Q07_SCENE_NOT_FOUND:{row['item_id']}")
            if source["polarity"] == "NEGATIVE":
                truth = scenes[scene_ref]["truth_evidence_spec"]
                require(truth["explicit_positive_alternative_required_for_negative"] is True, f"NEGATIVE_CONTRAST_GUARD_MISSING:{row['item_id']}")
                require(truth["negation_proof_by_absence_allowed"] is False, f"NEGATION_BY_ABSENCE_REOPENED:{row['item_id']}")
            if source["subject_class"] in {"he", "she", "it", "they"}:
                require(scenes[scene_ref]["referent_binding_spec"]["required"] is True, f"PRONOUN_REFERENT_GUARD_MISSING:{row['item_id']}")
        else:
            require(row["scene_ref_id"] is None, f"STANDALONE_FORCED_SCENE:{row['item_id']}")

    coverage = dict(payload.get("coverage") or {})
    require(coverage.get("context_required_unbound_item_count") == 0, "CONTEXT_REQUIRED_UNBOUND_NONZERO")
    require(coverage.get("standalone_item_forced_scene_count") == 0, "STANDALONE_FORCED_SCENE_NONZERO")


def _q06_id(row: Mapping[str, Any]) -> str:
    return str(row.get("sentence_id") or row.get("binding_id") or "")


def _validate_answerability(items: list[Mapping[str, Any]]) -> None:
    for row in items:
        options = list(row.get("options") or [])
        response = dict(row.get("response_contract") or {})
        if options:
            require(len(options) == len(set(options)), f"OPTION_DUPLICATION:{row['item_id']}")
            require(row.get("correct_answer") in options, f"CORRECT_NOT_IN_OPTIONS:{row['item_id']}")
            require(row.get("single_answer_unique_cue_required") is True, f"UNIQUE_CUE_FLAG_MISSING:{row['item_id']}")
            require(response.get("single_answer_required") is True, f"SELECTED_RESPONSE_NOT_SINGLE:{row['item_id']}")
        if row["task_family_id"] in {
            "U05-TF05_SENTENCE_CONSTRUCTION",
            "U05-TF07_CONTEXT_GAP",
            "U05-TF09_PRODUCTIVE_RESPONSE",
            "U05-TF10_TRANSFER",
        }:
            require(response.get("scoring_mode") == "HUMAN_REVIEW", f"OPEN_OR_EQUIVALENT_RESPONSE_NOT_HUMAN_REVIEW:{row['item_id']}")
            require(response.get("single_answer_required") is False, f"OPEN_OR_EQUIVALENT_RESPONSE_FORCED_SINGLE:{row['item_id']}")
        if row["communicative_function_id"] == "U05-CF05_REQUEST_BASIC_BE_INFORMATION":
            stimulus = dict(row.get("stimulus") or {})
            require(stimulus.get("exact_question_form_materialized_by_unit05") is False, f"CF05_INTERROGATIVE_MATERIALIZED:{row['item_id']}")
            require(row["task_family_id"] in {"U05-TF09_PRODUCTIVE_RESPONSE", "U05-TF10_TRANSFER"}, f"CF05_FAMILY_INVALID:{row['item_id']}")


def _validate_runtime(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    runtime = list(payload.get("runtime_bindings") or [])
    require(len(runtime) == 800, "RUNTIME_ROW_COUNT_INVALID")
    require(len({str(row["slot_id"]) for row in runtime}) == 800, "RUNTIME_SLOT_COLLISION")
    require(len({str(row["selected_item_id"]) for row in runtime}) == 800, "RUNTIME_SELECTED_COLLISION")
    by_id = {str(row["item_id"]): row for row in items}
    for row in runtime:
        candidates = list(row.get("candidate_ids") or [])
        require(len(candidates) == 3 and len(set(candidates)) == 3, f"THREE_CANDIDATE_CONTRACT_INVALID:{row['slot_id']}")
        require(all(candidate in by_id for candidate in candidates), f"RUNTIME_CANDIDATE_NOT_IN_BANK:{row['slot_id']}")
        require(str(row["selected_item_id"]) == candidates[0], f"RUNTIME_SELECTED_NOT_FIRST:{row['slot_id']}")
        require(all(str(by_id[candidate]["task_family_id"]) == str(row["task_family_id"]) for candidate in candidates), f"RUNTIME_CROSS_FAMILY_CANDIDATE:{row['slot_id']}")


def _validate_boundaries(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    false_fields = {
        "q06_sentence_semantics_modified",
        "q07_scene_semantics_modified",
        "q08_communicative_function_semantics_modified",
        "q09_task_family_inventory_modified",
        "new_grammar_authority_created",
        "new_vocabulary_identity_created",
        "new_sentence_identity_created",
        "new_scene_identity_created",
        "new_communicative_function_identity_created",
        "unit05_current360_materialized",
        "unit05_spoken360_materialized",
        "unit05_pattern360_materialized",
        "be_interrogative_mastery_activated",
        "past_be_activated",
        "existential_there_be_activated",
        "present_continuous_mastery_activated",
        "a2_a2plus_unlocked",
    }
    boundaries = dict(payload.get("boundaries") or {})
    require(set(boundaries) == false_fields, "BOUNDARY_KEY_DRIFT")
    require(all(boundaries[key] is False for key in false_fields), "BOUNDARY_FALSE_CONTRACT_DRIFT")
    for row in items:
        for key in (
            "creates_new_grammar_authority",
            "creates_new_vocabulary_identity",
            "creates_new_sentence_identity",
            "creates_new_scene_identity",
            "creates_new_communicative_function_identity",
            "be_interrogative_mastery_activated",
            "past_be_activated",
            "existential_there_be_activated",
            "present_continuous_mastery_activated",
            "a2_a2plus_unlocked",
        ):
            require(row.get(key) is False, f"ITEM_BOUNDARY_REOPENED:{key}:{row['item_id']}")
    require(payload.get("next_short_step") == builder.NEXT_SHORT_STEP, "NEXT_SHORT_STEP_DRIFT")


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    items = list(payload.get("questionbank_items") or [])
    _validate_identity_and_counts(payload, items)
    _validate_forms(payload, items)
    _validate_authority_coverage(payload, items)
    _validate_q06_q07_binding_rules(payload, items)
    _validate_answerability(items)
    _validate_runtime(payload, items)
    _validate_boundaries(payload, items)
    return {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "error_count": 0,
        "questionbank_items": 800,
        "forms": 20,
        "task_families": "10/10",
        "communicative_functions": "7/7",
        "frames": "6/6",
        "subject_classes": "9/9",
    }


def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    report = validate_payload(payload)
    core = {
        "validator_id": VALIDATOR_ID,
        "status": report["status"],
        "questionbank_digest": payload["integrity"]["questionbank_digest"],
        "forms_digest": payload["integrity"]["forms_digest"],
        "runtime_digest": payload["integrity"]["runtime_digest"],
    }
    return {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "receipt_sha256": builder._digest(core),
    }


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(candidate)
    require(candidate.get("artifact_role") == policy_artifact.CANDIDATE_ROLE, "CANDIDATE_ROLE_INVALID")
    require(candidate.get("producer_id") == builder.TASK_ID, "PRODUCER_ID_INVALID")
    require(candidate.get("level_scope") == ["A1"], "LEVEL_SCOPE_INVALID")
    payload = candidate.get("payload")
    require(isinstance(payload, Mapping), "CANDIDATE_PAYLOAD_INVALID")
    return validation_receipt(payload)


def validate_approved(candidate: Mapping[str, Any], approved: Mapping[str, Any]) -> dict[str, Any]:
    policy_artifact.verify_artifact_digest(candidate)
    policy_artifact.verify_artifact_digest(approved)
    errors: list[str] = []
    if approved.get("artifact_role") != policy_artifact.APPROVED_ROLE:
        errors.append("APPROVED_ROLE_INVALID")
    if approved.get("producer_id") != builder.TASK_ID:
        errors.append("APPROVED_PRODUCER_ID_INVALID")
    if approved.get("admission", {}).get("decision_ref") != builder.DECISION_REF:
        errors.append("DECISION_REF_INVALID")
    if approved.get("payload") != candidate.get("payload"):
        errors.append("APPROVED_PAYLOAD_DRIFT")
    try:
        validate_payload(approved.get("payload", {}))
    except Exception as exc:
        errors.append(str(exc))
    return {
        "validator_id": VALIDATOR_ID,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
    }


def main() -> int:
    report = validate_payload(builder.build_export_payload())
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
