#!/usr/bin/env python3
"""Validate shared structured-speaking production contract and Unit03 evidence."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Read-only validator for the shared structured-speaking contract and Unit03 acceptance evidence; "
    "no grammar, vocabulary, chunk, sentence asset, QuestionBank, scene, learner content, runtime/state, Unit04 content, or A2 authority is created or mutated."
)

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_shared_speaking_structured_practice_contract.json"
SCHEMA = "a1fs.v1.shared_speaking_structured_practice_contract.v1"
PASS_STATUS = "PASS_A1FS_V1_SHARED_SPEAKING_STRUCTURED_PRACTICE_CONTRACT"
PROGRESSION = ["GUIDED", "REDUCED_SUPPORT", "INDEPENDENT", "TRANSFER", "RETENTION"]
GROUPS = [("A", "FSI_PATTERN_DRILL"), ("B", "SHOW_AND_TELL_DESCRIPTION"), ("C", "DIALOGUE_COMMUNICATIVE_TRANSFER")]


class StructuredSpeakingContractError(ValueError):
    pass


def _load(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise StructuredSpeakingContractError("CONTRACT_ROOT_NOT_OBJECT")
    return payload


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise StructuredSpeakingContractError(code)


def validate_payload(contract: Mapping[str, Any]) -> dict[str, Any]:
    _require(contract.get("schema_version") == SCHEMA, "SCHEMA_INVALID")
    _require(
        contract.get("status") == "UNIT03_FINAL_ACCEPTED_APPROVED_FOR_UNIT04_PLUS_INSTANTIATION_AFTER_Q01_Q10",
        "STATUS_INVALID",
    )
    relationship = contract.get("relationship_to_base_speaking", {})
    _require(relationship.get("replaces_layer1_atomic_pool") is False, "LAYER1_REPLACEMENT_FORBIDDEN")
    _require(relationship.get("replaces_layer2_connected_pool") is False, "LAYER2_REPLACEMENT_FORBIDDEN")

    source = contract.get("source_authority", {})
    _require(source.get("required") == [
        "Q05_EXACT_FRAME_OR_PATTERN_BINDING",
        "Q06_ADMITTED_SENTENCE_ASSETS",
        "Q07_ACCEPTED_SCENES_OR_CONTEXTS",
        "Q08_ACCEPTED_COMMUNICATIVE_FUNCTIONS",
        "Q10_ACCEPTED_QUESTIONBANK_AND_SCENE_EVIDENCE",
    ], "SOURCE_AUTHORITY_SEQUENCE_INVALID")

    products = contract.get("learner_products", {})
    _require(set(products) == {"unique_sentence_fluency", "template_chunk_drill_book", "speaking_forms_abc"}, "LEARNER_PRODUCT_SET_INVALID")
    abc = products["speaking_forms_abc"]
    _require(abc.get("group_count") == 3, "ABC_GROUP_COUNT_INVALID")
    actual_groups = [(row.get("group"), row.get("role")) for row in abc.get("groups", [])]
    _require(actual_groups == GROUPS, "ABC_GROUP_ROLE_ORDER_INVALID")
    _require(abc.get("required_progression_roles") == PROGRESSION, "ABC_PROGRESSION_INVALID")
    _require(set(abc.get("parameterized_fields", [])) >= {
        "form_count", "group_a_prompts_per_form", "group_b_connected_sentences_by_stage", "group_c_turns_by_stage"
    }, "ABC_PARAMETERIZATION_INCOMPLETE")

    visual = contract.get("acceptance_contract", {}).get("visual", {})
    _require(visual.get("gate") == "PRINT_OR_BROWSER_VISUAL_ACCEPTANCE", "VISUAL_GATE_INVALID")
    _require(visual.get("layout_only_repair_allowed") is True, "LAYOUT_REPAIR_POLICY_INVALID")
    unit_rule = contract.get("unit_parameter_rule", {})
    _require(unit_rule.get("numeric_values_are_global_defaults") is False, "UNIT03_NUMBERS_MUST_NOT_BE_GLOBAL_DEFAULTS")

    u03 = contract.get("unit03_evidence", {})
    _require(u03.get("status") == "FINAL_ACCEPTED", "UNIT03_EVIDENCE_NOT_FINAL")
    unique = u03.get("unique_sentence_fluency", {})
    _require(unique.get("exact_unique_sentence_count") == 724, "UNIT03_UNIQUE_SENTENCE_COUNT_INVALID")
    template = u03.get("template_chunk_drill_book", {})
    _require((template.get("template_family_count"), template.get("rapid_drill_prompt_count"), template.get("repetition_count_per_prompt"), template.get("print_page_count")) == (24, 273, 3, 17), "UNIT03_TEMPLATE_DRILL_COUNTS_INVALID")
    forms = u03.get("speaking_forms_abc", {})
    _require((forms.get("form_count"), forms.get("groups_per_form"), forms.get("group_a_prompts_per_form"), forms.get("print_page_count")) == (20, 3, 10, 20), "UNIT03_ABC_COUNTS_INVALID")
    _require(list(forms.get("group_b_connected_sentences_by_stage", {})) == PROGRESSION, "UNIT03_GROUP_B_STAGE_ORDER_INVALID")
    _require(list(forms.get("group_c_turns_by_stage", {})) == PROGRESSION, "UNIT03_GROUP_C_STAGE_ORDER_INVALID")
    _require(forms["group_b_connected_sentences_by_stage"] == {"GUIDED": 3, "REDUCED_SUPPORT": 4, "INDEPENDENT": 5, "TRANSFER": 6, "RETENTION": 6}, "UNIT03_GROUP_B_COUNTS_INVALID")
    _require(forms["group_c_turns_by_stage"] == {"GUIDED": 4, "REDUCED_SUPPORT": 5, "INDEPENDENT": 6, "TRANSFER": 6, "RETENTION": 6}, "UNIT03_GROUP_C_COUNTS_INVALID")

    machine = u03.get("machine_qa", {})
    _require(machine.get("status") == "PASS_FINAL_MACHINE_AND_PRINT_VISUAL", "UNIT03_MACHINE_QA_STATUS_INVALID")
    print_qa = u03.get("print_visual_acceptance", {})
    _require(print_qa.get("status") == "PASS", "UNIT03_PRINT_VISUAL_STATUS_INVALID")
    _require(print_qa.get("renderer") == "WeasyPrint", "UNIT03_PRINT_RENDERER_INVALID")
    _require((print_qa.get("template_pages"), print_qa.get("forms_pages"), print_qa.get("total_reviewed_pages")) == (17, 20, 37), "UNIT03_PRINT_PAGE_COUNTS_INVALID")
    for key in ("blank_pages", "text_blocks_outside_page", "clipping_or_overlap_after_repair"):
        _require(print_qa.get(key) == 0, f"UNIT03_PRINT_ZERO_GATE_FAILED:{key}")
    _require(bool(print_qa.get("learner_visible_text_preserved_sha256")), "LAYOUT_REPAIR_TEXT_PRESERVATION_HASH_MISSING")

    _require(bool(unique.get("html_sha256")), "UNIT03_UNIQUE_HASH_MISSING:html_sha256")
    for key in ("template_bank_sha256", "html_sha256"):
        _require(bool(template.get(key)), f"UNIT03_TEMPLATE_HASH_MISSING:{key}")
    for key in ("data_sha256", "html_sha256"):
        _require(bool(forms.get(key)), f"UNIT03_FORMS_HASH_MISSING:{key}")
    _require(bool(print_qa.get("visual_qa_sha256")), "UNIT03_VISUAL_QA_HASH_MISSING")
    _require(bool(u03.get("final_package_sha256")), "UNIT03_PACKAGE_HASH_MISSING")

    inst = contract.get("unit04_plus_instantiation", {})
    _require(inst.get("allowed_now") == "SHARED_CONTRACT_REUSE_ONLY", "UNIT04_ALLOWED_NOW_INVALID")
    _require(inst.get("current_unit_content_materialization") is False, "UNIT04_CONTENT_MATERIALIZATION_FORBIDDEN")
    _require(inst.get("implementation_precondition") == "UNIT04_Q01_Q10_CURRENT_UNIT_AUTHORITY_ACCEPTED", "UNIT04_PRECONDITION_INVALID")

    governance = contract.get("governance", {})
    for key in ("canonical_content_mutated", "second_sentence_authority_created", "unit04_learner_content_created", "q11_created", "a2_unlocked"):
        _require(governance.get(key) is False, f"GOVERNANCE_BOUNDARY_INVALID:{key}")

    return {
        "status": PASS_STATUS,
        "unit03_status": u03["status"],
        "unique_sentence_count": unique["exact_unique_sentence_count"],
        "template_family_count": template["template_family_count"],
        "rapid_drill_prompt_count": template["rapid_drill_prompt_count"],
        "forms": forms["form_count"],
        "groups_per_form": forms["groups_per_form"],
        "print_visual_acceptance": print_qa["status"],
        "unit04_content_materialized": False,
    }


def validate_file(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return validate_payload(_load(path))


def main() -> int:
    print(json.dumps(validate_file(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
