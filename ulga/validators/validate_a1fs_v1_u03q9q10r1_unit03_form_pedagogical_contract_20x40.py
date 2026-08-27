#!/usr/bin/env python3
"""Validate Unit03 Q9/Q10 successor 20x40 A/B/C/D/E contract."""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Mapping

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy_artifact
from ulga.builders import (
    build_a1fs_v1_u03q9q10r1_unit03_form_pedagogical_contract_20x40_6_10_10_8_6
    as builder,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U03Q9Q10R1_FORM_PEDAGOGICAL_CONTRACT_20X40_VALIDATOR"


class U03Q9Q10R1ValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise U03Q9Q10R1ValidationError(code)


def validation_receipt(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "validator_id": VALIDATOR_ID,
        "status": "PASS",
        "validated_payload_sha256": policy_artifact.digest(payload),
    }
    return {**core, "receipt_sha256": policy_artifact.digest(core)}


def _validate_scope(payload: Mapping[str, Any]) -> None:
    expected = {
        "q1_q4": "KEEP", "q5": "VERIFY_ONLY", "q6": "KEEP_NO_REGENERATION",
        "q7": "KEEP", "q8": "KEEP", "q9": "AMEND",
        "q10": "SUCCESSOR_REVISION_REMATERIALIZE", "pdf_pagination": "OUT_OF_SCOPE",
        "pdf_renderer": "OUT_OF_SCOPE", "q11": "OUT_OF_SCOPE",
        "unit04": "OUT_OF_SCOPE", "a2": "LOCKED",
    }
    require(dict(payload.get("scope_lock") or {}) == expected, "SCOPE_LOCK_DRIFT")


def _validate_history(payload: Mapping[str, Any]) -> None:
    h = dict(payload.get("historical_provenance") or {})
    require(h.get("unit03_q9_sha256") == builder.HISTORICAL_Q9_SHA256, "Q9_PROVENANCE_SHA_DRIFT")
    require(h.get("unit03_q10_16x40_sha256") == builder.HISTORICAL_Q10_SHA256, "Q10_PROVENANCE_SHA_DRIFT")
    require(h.get("unit03_q10_historical_runtime_count") == 640, "HISTORICAL_Q10_RUNTIME_DRIFT")
    require(h.get("unit03_q10_historical_identity_mutated") is False, "HISTORICAL_Q10_MUTATED")
    require(h.get("u03scfv2_historical_runtime_count") == 800, "HISTORICAL_SCFV2_RUNTIME_DRIFT")
    require(h.get("u03scfv2_historical_identity_mutated") is False, "HISTORICAL_SCFV2_MUTATED")
    require(h.get("successor_runtime_identity_is_new") is True, "SUCCESSOR_IDENTITY_NOT_NEW")


def _validate_q9(payload: Mapping[str, Any]) -> None:
    q9 = dict(payload.get("q9_amendment") or {})
    require(q9.get("task_family_count") == 10, "Q9_FAMILY_COUNT_INVALID")
    require(tuple(q9.get("task_families") or []) == builder.Q9_FAMILIES, "Q9_FAMILY_SET_OR_ORDER_DRIFT")
    require(q9.get("family_11_created") is False, "Q9_FAMILY_11_CREATED")
    require(dict(q9.get("section_mapping") or {}) == builder.FAMILY_SECTION_MAPPING, "Q9_SECTION_MAPPING_DRIFT")
    expected = [{"question_type": q, "task_family": f} for q, f in builder.CONNECTED_PASSAGE_TYPES]
    connected = list(q9.get("connected_passage_question_types") or [])
    require(connected == expected, "Q9_CONNECTED_PASSAGE_TYPE_MAPPING_DRIFT")
    require(all(row["task_family"] in builder.Q9_FAMILIES for row in connected), "CONNECTED_TYPE_CREATED_FAMILY_11")


def _validate_form_contract(payload: Mapping[str, Any], items: list[Mapping[str, Any]], runtime: list[Mapping[str, Any]]) -> None:
    c = dict(payload.get("q10_successor_form_contract") or {})
    require(c.get("materialization_identity") == "U03Q10R1_SUCCESSOR_20X40_6_10_10_8_6", "SUCCESSOR_IDENTITY_INVALID")
    require(c.get("form_count") == 20 and c.get("activities_per_form") == 40, "FORM_DENOMINATOR_INVALID")
    require(c.get("runtime_occurrence_count") == 800, "RUNTIME_DENOMINATOR_INVALID")
    require(c.get("candidate_count_per_slot") == 3, "CANDIDATE_COUNT_INVALID")
    require(c.get("section_counts_per_form") == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}, "SECTION_PER_FORM_CONTRACT_INVALID")
    require(c.get("selected_item_identity_count") == 800, "SELECTED_ITEM_IDENTITY_COUNT_INVALID")
    require(c.get("global_800_distinct_selected_item_proof") is True, "GLOBAL_800_DISTINCT_NOT_PROVEN")
    require(len(items) == 800 and len(runtime) == 800, "SUCCESSOR_800_ROWS_INVALID")
    require(len({row["item_id"] for row in items}) == 800, "QUESTIONBANK_ITEM_ID_COLLISION")
    require(len({row["runtime_occurrence_id"] for row in runtime}) == 800, "RUNTIME_OCCURRENCE_ID_COLLISION")
    require(len({row["selected_item_id"] for row in runtime}) == 800, "RUNTIME_SELECTED_ID_COLLISION")
    item_by_id = {str(row["item_id"]): row for row in items}
    item_ids = set(item_by_id)
    for row in runtime:
        candidates = list(row.get("candidate_ids") or [])
        require(len(candidates) == 3 and len(set(candidates)) == 3, f"THREE_CANDIDATE_CONTRACT_INVALID:{row.get('slot_id')}")
        require(all(candidate in item_ids for candidate in candidates), f"CANDIDATE_NOT_MATERIALIZED:{row.get('slot_id')}")
        require(str(row.get("selected_item_id")) == candidates[0], f"FIRST_CANDIDATE_SELECTION_INVALID:{row.get('slot_id')}")
        selected = item_by_id[str(row["selected_item_id"])]
        require(str(row.get("task_family")) == str(selected.get("task_family")), f"RUNTIME_FAMILY_SELECTED_ITEM_DRIFT:{row.get('slot_id')}")
        require(all(str(item_by_id[c]["task_family"]) == str(row["task_family"]) for c in candidates), f"CROSS_FAMILY_CANDIDATE_INVALID:{row.get('slot_id')}")
    for form_number in range(1, 21):
        rows = [row for row in items if int(row["form_number"]) == form_number]
        rrows = [row for row in runtime if int(row["form_number"]) == form_number]
        require(len(rows) == 40 and len(rrows) == 40, f"FORM_40_DENOMINATOR_INVALID:{form_number}")
        counts = Counter(str(row["section"]) for row in rows)
        expected = Counter({"A": 6, "B": 10, "C": 10, "D": 8, "E": 6})
        require(counts == expected, f"FORM_SECTION_DISTRIBUTION_INVALID:{form_number}:{counts}")
        require(Counter(str(row["section"]) for row in rrows) == expected, f"FORM_RUNTIME_SECTION_DISTRIBUTION_INVALID:{form_number}")
    family_counts = Counter(str(row["task_family"]) for row in items)
    require(set(family_counts) == set(builder.Q9_FAMILIES), f"RUNTIME_Q9_FAMILY_COVERAGE_INVALID:{sorted(family_counts)}")


def _validate_progression(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    p = dict(payload.get("progression_contract") or {})
    require(p.get("forms_by_stage") == builder.STAGE_BY_FORMS, "STAGE_FORM_MAPPING_DRIFT")
    require(p.get("passage_sentence_count_by_stage") == builder.PASSAGE_SENTENCE_COUNT_BY_STAGE, "PASSAGE_SENTENCE_COUNT_CONTRACT_DRIFT")
    expected = Counter({stage: 160 for stage in builder.STAGE_BY_FORMS})
    require(Counter(str(row["progression_stage"]) for row in items) == expected, "STAGE_RUNTIME_COUNTS_INVALID")


def _validate_section_b(items: list[Mapping[str, Any]]) -> None:
    all_b = [row for row in items if row.get("section") == "B"]
    require(len(all_b) == 200, "SECTION_B_TOTAL_INVALID")
    for form_number in range(1, 21):
        rows = [row for row in all_b if int(row["form_number"]) == form_number]
        require(len(rows) == 10, f"SECTION_B_FORM_COUNT_INVALID:{form_number}")
        evidence = {str(value) for row in rows for value in (row.get("pedagogical_evidence") or [])}
        require(builder.B_REQUIRED_EVIDENCE.issubset(evidence), f"SECTION_B_REQUIRED_PEDAGOGY_MISSING:{form_number}")
        qtypes = {str(row["question_type"]) for row in rows}
        require(any("rewrite" in q or "structured_morphology_build" in q for q in qtypes), f"SECTION_B_MANIPULATION_NOT_REAL:{form_number}")
        require(any("correction" in q for q in qtypes), f"SECTION_B_CORRECTION_NOT_REAL:{form_number}")
        require(any("production" in q for q in qtypes), f"SECTION_B_PRODUCTION_NOT_REAL:{form_number}")


def _validate_section_c(items: list[Mapping[str, Any]]) -> None:
    all_c = [row for row in items if row.get("section") == "C"]
    require(len(all_c) == 200, "SECTION_C_TOTAL_INVALID")
    for row in all_c:
        require(str(row.get("task_family")) == "U01_U02_INTEGRATION", f"SECTION_C_FAMILY_INVALID:{row.get('item_id')}")
        require(set(row.get("grammar_targets") or []) == builder.C_TARGETS, f"SECTION_C_TARGETS_INVALID:{row.get('item_id')}")
        require(str(row.get("primary_target")) == "SUBJECT_PRONOUN", f"SECTION_C_PRIMARY_TARGET_INVALID:{row.get('item_id')}")
        require(set(row.get("secondary_targets") or []) == {"ARTICLE", "PLURALITY"}, f"SECTION_C_SECONDARY_TARGETS_INVALID:{row.get('item_id')}")
        require(dict(row.get("integration_proof") or {}) == {
            "same_question_contains_u01_article": True,
            "same_question_contains_u02_number_plural": True,
            "same_question_contains_u03_subject_pronoun": True,
            "alternating_separate_questions_only": False,
        }, f"SECTION_C_INTEGRATION_PROOF_INVALID:{row.get('item_id')}")
        text = " ".join([str(row.get("stimulus") or ""), str(row.get("prompt") or ""),
                         str(row.get("correct_answer") or ""),
                         " ".join(str(v) for v in (row.get("options") or []))]).casefold()
        require("two " in text, f"SECTION_C_NUMBER_PLURAL_SURFACE_MISSING:{row.get('item_id')}")
        require(any(token in text.split() for token in ("i", "you", "he", "she", "it", "we", "they")), f"SECTION_C_PRONOUN_SURFACE_MISSING:{row.get('item_id')}")
        require(" a " in f" {text} " or " an " in f" {text} ", f"SECTION_C_ARTICLE_SURFACE_MISSING:{row.get('item_id')}")


def _validate_section_e(items: list[Mapping[str, Any]]) -> None:
    all_e = [row for row in items if row.get("section") == "E"]
    require(len(all_e) == 120, "SECTION_E_TOTAL_INVALID")
    expected_types = {q for q, _ in builder.CONNECTED_PASSAGE_TYPES}
    by_form: dict[int, list[Mapping[str, Any]]] = defaultdict(list)
    for row in all_e:
        by_form[int(row["form_number"])].append(row)
    require(set(by_form) == set(range(1, 21)), "SECTION_E_FORM_COVERAGE_INVALID")
    for form_number, rows in by_form.items():
        require(len(rows) == 6, f"SECTION_E_FORM_COUNT_INVALID:{form_number}")
        require(all(row.get("connected_passage") is True for row in rows), f"SECTION_E_NOT_CONNECTED_PASSAGE:{form_number}")
        require(len({str(row.get("passage_id")) for row in rows}) == 1, f"SECTION_E_PASSAGE_ID_NOT_SHARED:{form_number}")
        require({str(row["question_type"]) for row in rows} == expected_types, f"SECTION_E_QUESTION_TYPES_INVALID:{form_number}")
        stage = builder._stage(form_number)
        count = builder.PASSAGE_SENTENCE_COUNT_BY_STAGE[stage]
        require(all(int(row.get("passage_sentence_count", -1)) == count for row in rows), f"SECTION_E_PASSAGE_LENGTH_INVALID:{form_number}")
        require(all(len(row.get("passage_sentences") or []) == count for row in rows), f"SECTION_E_PASSAGE_SENTENCES_INVALID:{form_number}")
        if stage in {"TRANSFER", "RETENTION"}:
            require(all(row.get("passage_unseen") is True for row in rows), f"SECTION_E_UNSEEN_FLAG_MISSING:{form_number}")
        else:
            require(all(row.get("passage_unseen") is False for row in rows), f"SECTION_E_UNSEEN_FLAG_EARLY:{form_number}")


def _validate_q6(payload: Mapping[str, Any], items: list[Mapping[str, Any]]) -> None:
    q6 = dict(payload.get("q6_preservation") or {})
    require(q6.get("historical_unit03_admitted_sentence_asset_count") == 18983, "Q6_HISTORICAL_COUNT_DRIFT")
    require(q6.get("successor_sentence_assets_created") == 0, "Q6_NEW_SENTENCE_ASSET_CREATED")
    require(q6.get("q6_regenerated") is False and q6.get("q6_mutated") is False, "Q6_CHANGED")
    require(all(row.get("q6_sentence_asset_created") is False for row in items), "ITEM_CREATED_Q6_SENTENCE_ASSET")


def _validate_boundaries(payload: Mapping[str, Any]) -> None:
    b = dict(payload.get("claim_boundaries") or {})
    keys = (
        "q1_q4_mutated", "q5_mutated", "q6_regenerated", "q6_mutated",
        "q7_mutated", "q8_mutated", "historical_q10_runtime_mutated",
        "historical_u03scfv2_runtime_mutated", "family_11_created",
        "pdf_pagination_modified", "pdf_renderer_modified", "q11_opened",
        "unit04_opened", "a2_unlocked",
    )
    require(all(b.get(key) is False for key in keys), "CLAIM_BOUNDARY_DRIFT")


def validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    require(payload.get("schema_version") == builder.SCHEMA_VERSION, "SCHEMA_INVALID")
    require(payload.get("task_id") == builder.TASK_ID, "TASK_INVALID")
    require(payload.get("status") == builder.PASS_STATUS, "STATUS_INVALID")
    require(payload.get("unit_id") == builder.UNIT_ID, "UNIT_INVALID")
    _validate_scope(payload)
    _validate_history(payload)
    _validate_q9(payload)
    items = list(payload.get("successor_questionbank_items") or [])
    runtime = list(payload.get("runtime_bindings") or [])
    _validate_form_contract(payload, items, runtime)
    _validate_progression(payload, items)
    _validate_section_b(items)
    _validate_section_c(items)
    _validate_section_e(items)
    _validate_q6(payload, items)
    _validate_boundaries(payload)
    proofs = dict(payload.get("pedagogical_proofs") or {})
    require(proofs.get("section_e_connected_passage_questions_per_form") == 6, "E_PER_FORM_PROOF_INVALID")
    require(proofs.get("section_e_connected_passage_question_count") == 120, "E_120_PROOF_INVALID")
    require(proofs.get("section_c_not_alternating_separate_question_claim") is True, "C_INTEGRATION_CLAIM_INVALID")
    return {
        "validation_status": "PASS", "error_count": 0, "q9_task_family_count": 10,
        "forms": 20, "activities_per_form": 40, "runtime_occurrences": 800,
        "section_b_real_sentence_operation": True,
        "section_c_same_item_u01_u02_u03_integration": True,
        "section_e_connected_passage_questions": 120, "q6_regenerated": False,
        "historical_runtime_identities_preserved": True,
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
    print(f"Q9_TASK_FAMILIES={report['q9_task_family_count']}")
    print(f"FORMS={report['forms']}")
    print(f"ACTIVITIES_PER_FORM={report['activities_per_form']}")
    print(f"RUNTIME_OCCURRENCES={report['runtime_occurrences']}")
    print(f"SECTION_B_REAL_SENTENCE_OPERATION={report['section_b_real_sentence_operation']}")
    print(f"SECTION_C_SAME_ITEM_INTEGRATION={report['section_c_same_item_u01_u02_u03_integration']}")
    print(f"SECTION_E_CONNECTED_PASSAGE_QUESTIONS={report['section_e_connected_passage_questions']}")
    print(f"Q6_REGENERATED={report['q6_regenerated']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
