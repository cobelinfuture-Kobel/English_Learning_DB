from copy import deepcopy

import pytest

from ulga.builders import build_e4s_a1v1_reading_v1_integration_gate as builder
from ulga.validators import validate_e4s_a1v1_reading_v1_integration_gate as validator


@pytest.fixture(scope="module")
def report():
    return builder.build_report()


def test_m04a_integrates_96_reading_items_across_24_units(report):
    reading = report["reading_grammar_integration"]
    assert reading == {
        "status": "PASS",
        "shared_reading_item_count": 96,
        "learning_unit_count": 24,
        "items_per_unit": 4,
        "practice_item_count": 72,
        "assessment_item_count": 24,
        "task_type_counts": {
            "context_choice": 48,
            "form_choice": 48,
        },
        "source_kind_counts": {"READING_WRITING_TEXT_MODE": 96},
        "semantic_role": "GRAMMAR_ALIGNED_READING_RECOGNITION",
        "not_claimed_as": "SOURCE_GROUNDED_PASSAGE_COMPREHENSION",
    }


def test_m04a_keeps_six_type_reading_v1_contract_healthy_but_synthetic(report):
    fixture = report["reading_v1_contract_fixture"]
    assert fixture["status"] == "PASS"
    assert fixture["validator_status"] == "PASS"
    assert fixture["item_count"] == 6
    assert set(fixture["question_types"]) == builder.V1_QUESTION_TYPES
    assert fixture["synthetic_fixture_only"] is True
    assert fixture["real_source_coverage_claimed"] is False


def test_m04a_fails_closed_on_missing_ci_readable_reading_sources(report):
    source = report["reading_source_availability"]
    assert source["status"] == "BLOCKED"
    assert source["github_ci_readable_intake_item_count"] == 0
    assert source["github_ci_readable_levels"] == []
    assert source["drive_source_folder_discovered"] is True
    assert source["drive_source_folder_id"] == builder.DRIVE_RAZ_OUTPUT_FOLDER_ID
    assert source["drive_connector_visible_normalized_file_count"] == 0
    assert source["raw_source_text_persisted"] is False
    assert source["full_passage_text_persisted"] is False
    assert source["source_payload_copied_to_repo"] is False

    assert report["m04_gate"] == {
        "grammar_reading_bank_integrated": True,
        "reading_v1_six_type_contract_healthy": True,
        "source_grounded_comprehension_content_available": False,
        "reading_v1_complete": False,
        "m05_progression_allowed": False,
    }
    assert report["stop_reason"] == "SOURCE_EVIDENCE_REQUIRED"
    assert report["blocker_type"] == "CI_READABLE_READING_SOURCE_ARTIFACT_MISSING"
    assert report["next_short_step"] is None
    assert report["next_resume_task"] == builder.RESUME_TASK
    assert report["required_operator_action"]


def test_m04a_validator_accepts_the_blocked_gate_as_correct_current_state(report):
    validation = validator.validate_report(report)
    assert validation["validation_status"] == validator.VALIDATION_PASS_STATUS
    assert validation["errors"] == []
    assert validation["validation_counts"] == {
        "shared_reading_item_count": 96,
        "reading_learning_unit_count": 24,
        "reading_v1_fixture_item_count": 6,
        "github_ci_readable_source_item_count": 0,
    }
    assert validation["gate_state"] == {
        "m04a_complete": True,
        "m04_complete": False,
        "m05_progression_allowed": False,
    }
    assert validation["stop_reason"] == "SOURCE_EVIDENCE_REQUIRED"
    assert validation["next_resume_task"] == builder.RESUME_TASK


def test_m04a_validator_rejects_false_reading_completion(report):
    tampered = deepcopy(report)
    tampered["m04_gate"]["reading_v1_complete"] = True
    tampered["m04_gate"]["m05_progression_allowed"] = True
    tampered["claim_boundaries"]["m04_reading_v1_complete"] = True
    validation = validator.validate_report(tampered)
    assert validation["validation_status"] == "FAIL"
    assert "false_m04_completion" in validation["errors"]
    assert "m05_progression_not_blocked" in validation["errors"]
    assert "false_claim:m04_reading_v1_complete" in validation["errors"]
    assert validation["stop_reason"] == "VALIDATION_FAILURE"
