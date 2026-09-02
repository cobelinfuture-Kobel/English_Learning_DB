from __future__ import annotations

from copy import deepcopy

from ulga.validators import validate_a1fs_v1_reusable_unit_production_contract as validator


def payloads() -> tuple[dict, dict]:
    return validator._load(validator.CONTRACT_PATH), validator._load(validator.MANIFEST_PATH)


def test_reusable_contract_and_unit03_manifest_validate() -> None:
    contract, manifest = payloads()
    report = validator.validate_payloads(contract, manifest)
    assert report["status"] == validator.PASS_STATUS
    assert report["evidence_units"] == ["Unit01", "Unit02", "Unit03"]
    assert report["unit04_content_materialized"] is False


def test_common_contract_parameterizes_later_unit_counts_and_thresholds() -> None:
    contract, _ = payloads()
    common = contract["common_contract"]
    rw_fields = set(common["reading_writing"]["form_architecture"]["parameterized_fields"])
    assert {"form_count", "questions_per_form", "questions_per_section", "task_families"} <= rw_fields
    layer2 = common["speaking"]["layer2_connected"]
    assert layer2["threshold_policy"] == "UNIT_PARAMETERS_DEFINE_NUMERIC_THRESHOLDS; COMMON_CONTRACT_DEFINES_REQUIRED_METRICS"


def test_unit03_reading_writing_contract_is_arithmetically_closed() -> None:
    _, manifest = payloads()
    rw = manifest["unit_parameters"]["reading_writing_parameters"]
    assert sum(rw["sections"].values()) == 40
    assert rw["form_count"] * rw["questions_per_form"] == rw["total_items"] == 800
    forms, roles = validator._expanded_forms(rw["progression_ranges"])
    assert forms == list(range(1, 21))
    assert roles == validator.PROGRESSION_ROLES


def test_unit03_speaking_layer1_and_layer2_acceptance_is_pinned() -> None:
    _, manifest = payloads()
    speaking = manifest["acceptance"]["speaking"]
    assert speaking["layer1"]["atomic_sentence_count"] == 2077
    assert speaking["layer1"]["exact_duplicate_occurrences"] == 0
    assert speaking["layer2"]["connected_set_count"] == 200
    assert speaking["layer2"]["utterance_count"] == 1270
    assert speaking["layer2"]["scene_family_count"] == 17
    assert speaking["layer2"]["browser_dom_visual_evidence"] == "NOT_AVAILABLE_RUNTIME_CHROMIUM_TIMEOUT"


def test_validator_rejects_unit04_content_materialization_without_unit04_authority() -> None:
    contract, manifest = payloads()
    drifted = deepcopy(contract)
    drifted["unit04_plus_instantiation"]["current_unit_content_materialization"] = True
    try:
        validator.validate_payloads(drifted, manifest)
    except validator.ReusableUnitProductionContractError as exc:
        assert "UNIT04_CONTENT_MATERIALIZATION_MUST_BE_FALSE" in str(exc)
    else:
        raise AssertionError("validator accepted premature Unit04 content materialization")


def test_validator_rejects_layer2_lexical_concentration_regression() -> None:
    contract, manifest = payloads()
    drifted = deepcopy(manifest)
    drifted["acceptance"]["speaking"]["layer2"]["top10_lexical_payload_concentration"] = 0.31
    try:
        validator.validate_payloads(contract, drifted)
    except validator.ReusableUnitProductionContractError as exc:
        assert "LAYER2_TOP10_THRESHOLD_FAILED" in str(exc)
    else:
        raise AssertionError("validator accepted Layer2 lexical-concentration regression")
