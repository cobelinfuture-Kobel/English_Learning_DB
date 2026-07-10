from __future__ import annotations

import copy

from ulga.builders.build_a1_grammar_text_mode_private_pilot_package import (
    build_and_validate_from_repo,
    validate_artifact,
)
from ulga.builders.build_a1_grammar_derived_pedagogy_fullfix import (
    build_artifact as build_pedagogy_artifact,
)
from ulga.builders.build_a1_grammar_operator_confirmation_text_mode_pilot import (
    build_and_validate_from_repo as build_promotion_source,
)
from ulga.builders.build_a1_grammar_text_mode_practice_item_fullfix import (
    build_and_validate_from_repo as build_practice_source,
)


def sources():
    practice, practice_report = build_practice_source()
    assert practice_report["validation_status"] == "PASS"
    pedagogy = build_pedagogy_artifact(practice)
    promotion, promotion_report = build_promotion_source()
    assert promotion_report["validation_status"] == "PASS"
    return pedagogy, promotion


def test_private_pilot_package_has_24_units_109_rows_and_192_items():
    artifact, report = build_and_validate_from_repo()
    assert report["validation_status"] == "PASS"
    assert len(artifact["learning_units"]) == 24
    assert len(artifact["by_egp_row_id"]) == 109
    assert len(artifact["item_bank"]) == 192
    assert artifact["package_manifest"]["practice_item_count"] == 144
    assert artifact["package_manifest"]["assessment_item_count"] == 48
    assert artifact["package_manifest"]["reading_item_count"] == 96
    assert artifact["package_manifest"]["writing_item_count"] == 96


def test_each_unit_has_approved_six_plus_two_delivery_plan():
    artifact, _ = build_and_validate_from_repo()
    for unit in artifact["learning_units"]:
        assert unit["operator_approval_status"] == "APPROVED_TEXT_MODE"
        assert unit["delivery_plan"]["practice_item_count"] == 6
        assert unit["delivery_plan"]["assessment_item_count"] == 2
        assert unit["delivery_plan"]["reading_item_count"] == 4
        assert unit["delivery_plan"]["writing_item_count"] == 4
        assert unit["text_mode_private_pilot_status"] == "READY_NOT_STARTED"
        assert unit["actual_learner_attempt_count"] == 0


def test_unit_sequence_respects_declared_prerequisites():
    artifact, _ = build_and_validate_from_repo()
    positions = {
        grammar_id: index
        for index, grammar_id in enumerate(
            artifact["package_manifest"]["unit_sequence"]
        )
    }
    for unit in artifact["learning_units"]:
        for prerequisite in unit["prerequisite_unit_ids"]:
            if prerequisite in positions:
                assert positions[prerequisite] < positions[unit["grammar_unit_id"]]


def test_all_items_are_text_mode_ready_and_have_no_attempts_or_writes():
    artifact, _ = build_and_validate_from_repo()
    item_ids = set()
    for item in artifact["item_bank"]:
        assert item["skill"] in {"reading", "writing"}
        assert item["pilot_delivery_status"] == "READY_NOT_DELIVERED"
        assert item["actual_attempt_count"] == 0
        assert item["learner_state_write"] is False
        assert item["item_id"] not in item_ids
        item_ids.add(item["item_id"])
    assert len(item_ids) == 192


def test_release_gates_open_package_but_not_execution_or_full_release():
    artifact, _ = build_and_validate_from_repo()
    gates = artifact["release_gates"]
    assert gates["operator_confirmation_gate"] == "PASS"
    assert gates["text_mode_private_pilot_package_gate"] == "PASS_READY"
    assert gates["pilot_execution_gate"] == "BLOCKED_NOT_STARTED"
    assert gates["actual_learner_evidence_gate"] == "BLOCKED_NOT_COLLECTED"
    assert gates["audio_scope_gate"] == "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE"
    assert gates["production_runtime_gate"] == "BLOCKED_NOT_APPROVED"


def test_package_does_not_claim_actual_pilot_or_mastery():
    artifact, _ = build_and_validate_from_repo()
    boundaries = artifact["claim_boundaries"]
    assert boundaries["text_mode_private_pilot_package_complete"] is True
    assert boundaries["text_mode_private_pilot_started"] is False
    assert boundaries["actual_learner_attempts_collected"] is False
    assert boundaries["actual_mastery_measured"] is False
    assert boundaries["audio_scope_deferred"] is True
    assert boundaries["audio_scope_complete"] is False
    assert boundaries["no_persistent_learner_state_write"] is True


def test_forged_started_pilot_or_persistent_write_fails_closed():
    artifact, _ = build_and_validate_from_repo()
    pedagogy, promotion = sources()
    artifact["claim_boundaries"]["text_mode_private_pilot_started"] = True
    artifact["item_bank"][0]["learner_state_write"] = True
    report = validate_artifact(artifact, pedagogy, promotion)
    assert report["validation_status"] == "FAIL"
    assert (
        "pilot_false_completion_claim:text_mode_private_pilot_started"
        in report["errors"]
    )
    assert any(
        error.startswith("pilot_item_learner_write_enabled")
        for error in report["errors"]
    )


def test_missing_item_or_row_fails_closed():
    artifact, _ = build_and_validate_from_repo()
    pedagogy, promotion = sources()
    artifact["item_bank"].pop()
    artifact["by_egp_row_id"].pop(next(iter(artifact["by_egp_row_id"])))
    report = validate_artifact(artifact, pedagogy, promotion)
    assert report["validation_status"] == "FAIL"
    assert "pilot_package_item_count_not_192" in report["errors"]
    assert "pilot_package_row_count_not_109" in report["errors"]


def test_builder_output_is_stable_for_repeated_reads():
    first, first_report = build_and_validate_from_repo()
    second, second_report = build_and_validate_from_repo()
    assert first_report["validation_status"] == "PASS"
    assert second_report["validation_status"] == "PASS"
    assert first == second
    snapshot = copy.deepcopy(first)
    assert first == snapshot
