#!/usr/bin/env python3
"""Validate the reusable Unit production contract and Unit03 acceptance manifest."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only validator for reusable Unit production contracts and Unit03 acceptance evidence; "
    "no grammar, vocabulary, chunk, sentence asset, QuestionBank, scene, learner content, runtime/state, or A2 authority is created or mutated."
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_reusable_unit_production_contract.json"
MANIFEST_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_unit03_production_acceptance_manifest.json"

CONTRACT_SCHEMA = "a1fs.v1.reusable_unit_production_contract.v1"
MANIFEST_SCHEMA = "a1fs.v1.unit03.production_acceptance_manifest.v1"
PASS_STATUS = "PASS_A1FS_V1_REUSABLE_UNIT_PRODUCTION_CONTRACT"

Q_SEQUENCE = [f"Q{i:02d}" for i in range(1, 11)]
PROGRESSION_ROLES = ["GUIDED", "REDUCED_SUPPORT", "INDEPENDENT", "TRANSFER", "RETENTION"]
CONNECTED_FAMILIES = [
    "C_SENTENCE_CHAINING",
    "D_SCENE_DESCRIPTION",
    "E_SHOW_AND_TELL",
    "F_PERSONAL_SPEAKING",
    "G_COMPARE_GROUP_REFERENCE",
    "H_INTERACTION_ROLEPLAY",
    "I_RETELL_MEMORY",
]
UNIT03_TASK_FAMILIES = [
    "RECOGNITION",
    "MEANING_DISCRIMINATION",
    "FORM_SELECTION",
    "MORPHOLOGY_CONSTRUCTION",
    "ERROR_DETECTION",
    "ERROR_CORRECTION",
    "CONTEXT_GAP",
    "U01_U02_INTEGRATION",
    "PRODUCTIVE_RESPONSE",
    "TRANSFER",
]


class ReusableUnitProductionContractError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ReusableUnitProductionContractError(f"JSON_ROOT_NOT_OBJECT:{path}")
    return payload


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise ReusableUnitProductionContractError(code)


def _validate_contract(contract: Mapping[str, Any]) -> None:
    _require(contract.get("schema_version") == CONTRACT_SCHEMA, "CONTRACT_SCHEMA_INVALID")
    _require(
        contract.get("status") == "APPROVED_FOR_UNIT04_PLUS_INSTANTIATION_AFTER_CURRENT_UNIT_Q01_Q10_ACCEPTANCE",
        "CONTRACT_STATUS_INVALID",
    )
    evidence = contract.get("evidence_units", {})
    _require(list(evidence) == ["Unit01", "Unit02", "Unit03"], "EVIDENCE_UNIT_SEQUENCE_INVALID")
    slots = contract.get("authority_pipeline", {}).get("required_slots", [])
    _require([row.get("q") for row in slots] == Q_SEQUENCE, "Q01_Q10_SEQUENCE_INVALID")
    _require(contract.get("authority_pipeline", {}).get("precondition") == "CURRENT_UNIT_Q01_Q10_ACCEPTED", "Q01_Q10_PRECONDITION_INVALID")
    common = contract.get("common_contract", {})
    _require(set(common) == {"speaking", "reading_writing"}, "COMMON_PIPELINE_KEYS_INVALID")
    layer1 = common["speaking"].get("layer1_atomic", {})
    _require(layer1.get("source_authority") == "Q06_ADMITTED_SENTENCE_ASSETS", "LAYER1_SOURCE_AUTHORITY_INVALID")
    _require("exact_duplicate_occurrences" in layer1.get("required_metrics", []), "LAYER1_DEDUP_METRIC_MISSING")
    layer2 = common["speaking"].get("layer2_connected", {})
    _require(layer2.get("capability_families") == [
        "SENTENCE_CHAINING", "SCENE_OR_PICTURE_DESCRIPTION", "SHOW_AND_TELL", "PERSONAL_SPEAKING",
        "COMPARE_OR_GROUP_REFERENCE", "INTERACTION_OR_ROLEPLAY", "RETELL_OR_MEMORY",
    ], "LAYER2_CAPABILITY_FAMILIES_INVALID")
    _require(layer2.get("threshold_policy") == "UNIT_PARAMETERS_DEFINE_NUMERIC_THRESHOLDS; COMMON_CONTRACT_DEFINES_REQUIRED_METRICS", "LAYER2_THRESHOLD_PARAMETERIZATION_INVALID")
    rw = common["reading_writing"]
    params = rw.get("form_architecture", {}).get("parameterized_fields", [])
    _require("form_count" in params and "questions_per_section" in params, "RW_PARAMETERIZATION_INCOMPLETE")
    _require(rw.get("form_architecture", {}).get("required_progression_roles") == PROGRESSION_ROLES, "RW_PROGRESSION_ROLES_INVALID")
    required = set(contract.get("unit_parameter_contract", {}).get("required", []))
    _require({"grammar_target", "q_authority_artifacts", "speaking_parameters", "reading_writing_parameters", "acceptance_thresholds"} <= required, "UNIT_PARAMETER_REQUIRED_FIELDS_INCOMPLETE")
    instantiation = contract.get("unit04_plus_instantiation", {})
    _require(instantiation.get("current_unit_content_materialization") is False, "UNIT04_CONTENT_MATERIALIZATION_MUST_BE_FALSE")
    _require(instantiation.get("implementation_precondition") == "UNIT04_Q01_Q10_CURRENT_UNIT_AUTHORITY_ACCEPTED", "UNIT04_IMPLEMENTATION_PRECONDITION_INVALID")
    governance = contract.get("governance", {})
    for key in ("canonical_content_mutated_by_this_contract", "learner_content_created_by_this_contract", "unit04_content_created", "a2_unlocked"):
        _require(governance.get(key) is False, f"GOVERNANCE_BOUNDARY_INVALID:{key}")


def _expanded_forms(ranges: list[Mapping[str, Any]]) -> tuple[list[int], list[str]]:
    forms: list[int] = []
    roles: list[str] = []
    for row in ranges:
        start, end = row["forms"]
        forms.extend(range(int(start), int(end) + 1))
        roles.append(str(row["role"]))
    return forms, roles


def _validate_manifest(manifest: Mapping[str, Any], contract: Mapping[str, Any]) -> None:
    _require(manifest.get("schema_version") == MANIFEST_SCHEMA, "MANIFEST_SCHEMA_INVALID")
    _require(manifest.get("contract_ref") == "ulga/contracts/a1fs_v1_reusable_unit_production_contract.json", "CONTRACT_REF_INVALID")
    p = manifest.get("unit_parameters", {})
    _require(p.get("unit_number") == 3, "UNIT03_NUMBER_INVALID")
    _require(p.get("grammar_unit_id") == "GRAMMAR_SUBJECT_PRONOUNS", "UNIT03_GRAMMAR_ID_INVALID")
    _require(p.get("q01_q10_acceptance_status") == "FINAL_ACCEPTED", "UNIT03_Q01_Q10_NOT_ACCEPTED")
    rw = p["reading_writing_parameters"]
    _require(sum(int(v) for v in rw["sections"].values()) == rw["questions_per_form"], "RW_SECTION_SUM_INVALID")
    _require(rw["form_count"] * rw["questions_per_form"] == rw["total_items"], "RW_TOTAL_ARITHMETIC_INVALID")
    forms, roles = _expanded_forms(rw["progression_ranges"])
    _require(forms == list(range(1, rw["form_count"] + 1)), "RW_PROGRESSION_FORM_COVERAGE_INVALID")
    _require(roles == PROGRESSION_ROLES, "RW_PROGRESSION_ROLE_ORDER_INVALID")
    _require(rw["task_families"] == UNIT03_TASK_FAMILIES, "UNIT03_TASK_FAMILIES_INVALID")
    speaking_p = p["speaking_parameters"]
    layer2_counts = speaking_p["layer2"]["required_families"]
    _require(list(layer2_counts) == CONNECTED_FAMILIES, "UNIT03_CONNECTED_FAMILY_ORDER_INVALID")
    _require(sum(layer2_counts.values()) == speaking_p["layer2"]["connected_set_count"] == 200, "UNIT03_CONNECTED_SET_COUNT_INVALID")
    acceptance = manifest["acceptance"]
    l1 = acceptance["speaking"]["layer1"]
    _require(l1["status"] == "PASS", "LAYER1_STATUS_INVALID")
    _require(l1["atomic_sentence_count"] == l1["exact_unique_sentence_count"] == 2077, "LAYER1_COUNT_INVALID")
    _require(l1["exact_duplicate_occurrences"] == 0, "LAYER1_EXACT_DUPLICATE_INVALID")
    _require(l1["direct_count"] + l1["reference_bound_count"] == l1["atomic_sentence_count"], "LAYER1_REFERENCE_ARITHMETIC_INVALID")
    _require(set(l1["subject_pronoun_counts"]) == {"i", "you", "he", "she", "it", "we", "they"}, "LAYER1_PRONOUN_COVERAGE_INVALID")
    l2 = acceptance["speaking"]["layer2"]
    _require(l2["status"] == "PASS_MACHINE_SEMANTIC_STATIC_VISUAL_PENDING", "LAYER2_STATUS_INVALID")
    _require(l2["connected_set_count"] == 200 and l2["utterance_count"] == 1270, "LAYER2_CAPACITY_INVALID")
    _require(l2["scene_family_count"] == 17, "LAYER2_SCENE_COUNT_INVALID")
    thresholds = p["acceptance_thresholds"]
    _require(l2["exact_duplicate_rate"] < thresholds["speaking_layer2_exact_sentence_repeat_rate_max"], "LAYER2_EXACT_REPEAT_THRESHOLD_FAILED")
    _require(l2["top1_lexical_payload_share"] < thresholds["speaking_layer2_top1_lexical_payload_share_max"], "LAYER2_TOP1_THRESHOLD_FAILED")
    _require(l2["top10_lexical_payload_concentration"] < thresholds["speaking_layer2_top10_lexical_payload_concentration_max"], "LAYER2_TOP10_THRESHOLD_FAILED")
    _require(l2["top20_lexical_payload_concentration"] < thresholds["speaking_layer2_top20_lexical_payload_concentration_max"], "LAYER2_TOP20_THRESHOLD_FAILED")
    _require(l2["distinct_lexical_payload_word_forms"] >= thresholds["speaking_layer2_distinct_lexical_payload_words_min"], "LAYER2_LEXICAL_WORD_COUNT_FAILED")
    _require(l2["selected_distinct_np_surfaces"] >= thresholds["speaking_layer2_selected_np_surfaces_min"], "LAYER2_NP_SURFACE_COUNT_FAILED")
    _require(l2["be_share"] < thresholds["speaking_layer2_be_share_max"], "LAYER2_BE_SHARE_FAILED")
    _require(l2["can_see_share"] < thresholds["speaking_layer2_can_see_share_max"], "LAYER2_CAN_SEE_SHARE_FAILED")
    _require(all(v == 0 for v in l2["semantic_zero_count_checks"].values()), "LAYER2_SEMANTIC_ZERO_GATE_FAILED")
    _require(l2["html_static_structure"]["pass"] is True, "LAYER2_STATIC_RENDER_FAILED")
    _require(l2["browser_dom_visual_evidence"] == "NOT_AVAILABLE_RUNTIME_CHROMIUM_TIMEOUT", "LAYER2_VISUAL_PENDING_REASON_INVALID")
    reading = acceptance["reading_writing"]
    _require(reading["status"] == "FINAL_ACCEPTED", "RW_STATUS_INVALID")
    counts = reading["hard_counts"]
    _require((counts["forms"], counts["questions_per_form"], counts["total_items"], counts["distinct_item_ids"]) == (20, 40, 800, 800), "RW_HARD_COUNTS_INVALID")
    _require(sum(counts["section_totals"].values()) == 800, "RW_SECTION_TOTAL_INVALID")
    _require(reading["answerability"]["unique_answerable"] == 800, "RW_ANSWERABILITY_INVALID")
    _require(reading["answerability"]["mcq_multiple_valid"] == 0, "RW_MULTIPLE_VALID_INVALID")
    _require(all(v == 0 for v in reading["leakage"].values()), "RW_LEAKAGE_INVALID")
    _require(all(v == 0 for v in reading["reference_and_morphology"].values()), "RW_REFERENCE_MORPHOLOGY_INVALID")
    _require(reading["scenes"]["covered_scene_families"] == reading["scenes"]["required_scene_families"] == 17, "RW_SCENE_COVERAGE_INVALID")
    _require(reading["diversity"]["learner_visible_exact_repeat_rate"] < thresholds["reading_writing_learner_visible_exact_repeat_rate_max"], "RW_REPEAT_THRESHOLD_FAILED")
    _require(reading["diversity"]["cross_form_exact_assessment_duplicate"] == 0, "RW_CROSS_FORM_DUPLICATE_INVALID")
    _require(reading["semantic"]["semantic_pass_items"] == 800, "RW_SEMANTIC_COUNT_INVALID")
    _require(reading["render"]["questionbook_answerkey_alignment"] == "800/800", "RW_ALIGNMENT_INVALID")
    _require(reading["render"]["full_visual_review"] == "PASS", "RW_VISUAL_ACCEPTANCE_INVALID")
    reuse = manifest["unit04_plus_reuse_readiness"]
    _require(reuse["reusable_contract_ready"] is True, "REUSE_CONTRACT_NOT_READY")
    _require(reuse["unit03_parameters_are_not_global_defaults"] is True, "UNIT03_PARAMETER_BOUNDARY_INVALID")
    _require(reuse["unit04_content_materialized"] is False, "UNIT04_CONTENT_MUST_NOT_BE_MATERIALIZED")


def validate_payloads(contract: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    _validate_contract(contract)
    _validate_manifest(manifest, contract)
    return {
        "status": PASS_STATUS,
        "contract_schema": CONTRACT_SCHEMA,
        "manifest_schema": MANIFEST_SCHEMA,
        "evidence_units": ["Unit01", "Unit02", "Unit03"],
        "unit04_content_materialized": False,
        "reading_writing_status": manifest["acceptance"]["reading_writing"]["status"],
        "speaking_layer1_status": manifest["acceptance"]["speaking"]["layer1"]["status"],
        "speaking_layer2_status": manifest["acceptance"]["speaking"]["layer2"]["status"],
    }


def validate_files(contract_path: Path = CONTRACT_PATH, manifest_path: Path = MANIFEST_PATH) -> dict[str, Any]:
    return validate_payloads(_load(contract_path), _load(manifest_path))


def main() -> int:
    print(json.dumps(validate_files(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
