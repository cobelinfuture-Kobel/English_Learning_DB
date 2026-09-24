from __future__ import annotations

from copy import deepcopy

from ulga.validators import validate_a1fs_v1_shared_speaking_structured_practice_contract as validator


def payload() -> dict:
    return validator._load()


def test_shared_structured_speaking_contract_validates() -> None:
    report = validator.validate_payload(payload())
    assert report == {
        "status": validator.PASS_STATUS,
        "unit03_status": "FINAL_ACCEPTED",
        "unique_sentence_count": 724,
        "template_family_count": 24,
        "rapid_drill_prompt_count": 273,
        "forms": 20,
        "groups_per_form": 3,
        "print_visual_acceptance": "PASS",
        "unit04_content_materialized": False,
    }


def test_abc_semantics_and_progression_are_frozen_but_counts_parameterized() -> None:
    contract = payload()
    abc = contract["learner_products"]["speaking_forms_abc"]
    assert [(row["group"], row["role"]) for row in abc["groups"]] == validator.GROUPS
    assert abc["required_progression_roles"] == validator.PROGRESSION
    assert contract["unit_parameter_rule"]["numeric_values_are_global_defaults"] is False


def test_unit03_evidence_pins_724_24_273_and_20x3() -> None:
    evidence = payload()["unit03_evidence"]
    assert evidence["unique_sentence_fluency"]["exact_unique_sentence_count"] == 724
    assert evidence["template_chunk_drill_book"]["template_family_count"] == 24
    assert evidence["template_chunk_drill_book"]["rapid_drill_prompt_count"] == 273
    assert evidence["speaking_forms_abc"]["form_count"] == 20
    assert evidence["speaking_forms_abc"]["groups_per_form"] == 3


def test_unit03_final_print_gate_is_closed() -> None:
    visual = payload()["unit03_evidence"]["print_visual_acceptance"]
    assert visual["status"] == "PASS"
    assert visual["template_pages"] == 17
    assert visual["forms_pages"] == 20
    assert visual["total_reviewed_pages"] == 37
    assert visual["blank_pages"] == 0
    assert visual["text_blocks_outside_page"] == 0
    assert visual["clipping_or_overlap_after_repair"] == 0
    assert visual["learner_visible_text_preserved_sha256"]


def test_validator_rejects_fourth_group() -> None:
    drifted = deepcopy(payload())
    drifted["learner_products"]["speaking_forms_abc"]["group_count"] = 4
    try:
        validator.validate_payload(drifted)
    except validator.StructuredSpeakingContractError as exc:
        assert "ABC_GROUP_COUNT_INVALID" in str(exc)
    else:
        raise AssertionError("validator accepted a fourth speaking group")


def test_validator_rejects_visual_overlap_regression() -> None:
    drifted = deepcopy(payload())
    drifted["unit03_evidence"]["print_visual_acceptance"]["clipping_or_overlap_after_repair"] = 1
    try:
        validator.validate_payload(drifted)
    except validator.StructuredSpeakingContractError as exc:
        assert "UNIT03_PRINT_ZERO_GATE_FAILED:clipping_or_overlap_after_repair" in str(exc)
    else:
        raise AssertionError("validator accepted print overlap regression")


def test_validator_rejects_globalizing_unit03_numeric_defaults() -> None:
    drifted = deepcopy(payload())
    drifted["unit_parameter_rule"]["numeric_values_are_global_defaults"] = True
    try:
        validator.validate_payload(drifted)
    except validator.StructuredSpeakingContractError as exc:
        assert "UNIT03_NUMBERS_MUST_NOT_BE_GLOBAL_DEFAULTS" in str(exc)
    else:
        raise AssertionError("validator accepted Unit03 numeric values as global defaults")


def test_validator_rejects_premature_unit04_content_materialization() -> None:
    drifted = deepcopy(payload())
    drifted["unit04_plus_instantiation"]["current_unit_content_materialization"] = True
    try:
        validator.validate_payload(drifted)
    except validator.StructuredSpeakingContractError as exc:
        assert "UNIT04_CONTENT_MATERIALIZATION_FORBIDDEN" in str(exc)
    else:
        raise AssertionError("validator accepted Unit04 learner content before Unit04 Q01-Q10 authority")
