from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_representative_vertical_slice import (  # noqa: E402
    AUTHORITY_PATH,
    PILOT_UNIT_IDS,
    QUERY_PATH,
    RULE_INDEX_PATH,
    build_artifact,
    load_json,
    validate_artifact,
)


def sources():
    return load_json(QUERY_PATH), load_json(RULE_INDEX_PATH), load_json(AUTHORITY_PATH)


def built():
    query, rules, authority = sources()
    artifact = build_artifact(query, rules, authority)
    report = validate_artifact(artifact, query, rules, authority)
    return artifact, report, (query, rules, authority)


def test_vertical_slice_passes_with_six_pilot_units():
    artifact, report, _ = built()
    summary = artifact["coverage_summary"]

    assert report["validation_status"] == "PASS"
    assert artifact["pilot_unit_ids"] == list(PILOT_UNIT_IDS)
    assert len(artifact["learning_units"]) == 6
    assert summary == {
        "pilot_unit_count": 6,
        "pilot_unique_egp_row_count": 28,
        "teaching_ready_unit_count": 6,
        "practice_ready_unit_count": 6,
        "assessment_ready_unit_count": 6,
        "practice_item_count": 36,
        "assessment_item_count": 12,
        "mastery_trackable_unit_count": 0,
    }


def test_each_unit_has_teaching_reading_writing_and_assessment_content():
    artifact, _, _ = built()

    for unit in artifact["learning_units"]:
        assert len(unit["learning_objectives"]) >= 2
        assert len(unit["form_rules"]) >= 2
        assert len(unit["meaning_functions"]) >= 1
        assert len(unit["usage_conditions"]) >= 2
        assert len(unit["positive_examples"]) >= 2
        assert len(unit["negative_examples"]) >= 3
        assert len(unit["common_error_tags"]) >= 3
        assert len(unit["practice_items"]) == 6
        assert len(unit["assessment_items"]) == 2
        assert {item["skill"] for item in unit["practice_items"]} == {"reading", "writing"}
        assert {item["evidence_dimension"] for item in unit["assessment_items"]} == {
            "receptive_checkpoint",
            "productive_checkpoint",
        }
        assert unit["readiness"]["teachable"] is True
        assert unit["readiness"]["practice_ready"] is True
        assert unit["readiness"]["assessment_ready"] is True
        assert unit["readiness"]["mastery_trackable"] is False


def test_all_48_activity_grammar_gates_pass():
    _, report, _ = built()

    assert report["validation_counts"]["practice_and_assessment_grammar_gate_target_count"] == 48
    assert report["validation_counts"]["unique_item_id_count"] == 48
    assert report["gate_checks"]["practice_item_grammar_gates_pass"] is True


def test_builder_does_not_mutate_sources():
    query, rules, authority = sources()
    before = copy.deepcopy((query, rules, authority))

    build_artifact(query, rules, authority)

    assert (query, rules, authority) == before


def test_positive_example_tamper_fails_closed():
    artifact, _, source_values = built()
    query, rules, authority = source_values
    artifact["learning_units"][0]["positive_examples"][0]["text"] = "Not a matching target."

    report = validate_artifact(artifact, query, rules, authority)

    assert report["validation_status"] == "FAIL"
    assert any(error.startswith("positive_example_gate_fail") for error in report["errors"])


def test_practice_item_target_tamper_fails_closed():
    artifact, _, source_values = built()
    query, rules, authority = source_values
    item = artifact["learning_units"][0]["practice_items"][0]
    item["grammar_gate"]["validation_targets"][0]["text"] = "Not a matching target."

    report = validate_artifact(artifact, query, rules, authority)

    assert report["validation_status"] == "FAIL"
    assert any(error.startswith("practice_item_grammar_gate_fail") for error in report["errors"])


def test_false_full_coverage_claim_fails_closed():
    artifact, _, source_values = built()
    query, rules, authority = source_values
    artifact["claim_boundaries"]["full_24_unit_teachable_coverage_complete"] = True

    report = validate_artifact(artifact, query, rules, authority)

    assert report["validation_status"] == "FAIL"
    assert "false_full_coverage_claim" in report["errors"]


def test_rule_source_tamper_fails_closed():
    artifact, _, source_values = built()
    query, rules, authority = source_values
    artifact["learning_units"][0]["source_trace"]["rule_source_path"] = "ulga/rules/not_authority.json"

    report = validate_artifact(artifact, query, rules, authority)

    assert report["validation_status"] == "FAIL"
    assert any(error.startswith("rule_source_mismatch") for error in report["errors"])


def test_scope_boundaries_remain_a1_only_and_read_only():
    artifact, _, _ = built()
    boundaries = artifact["claim_boundaries"]

    assert boundaries["full_24_unit_teachable_coverage_complete"] is False
    assert boundaries["full_109_row_teachable_coverage_complete"] is False
    assert boundaries["learner_mastery_runtime_complete"] is False
    assert boundaries["no_a2_a2plus_expansion"] is True
    assert boundaries["no_learner_state_write"] is True
    assert boundaries["no_restricted_source_payload_copy"] is True
