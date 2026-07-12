from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_full_teachable_candidate_coverage import (  # noqa: E402
    AUTHORITY_PATH,
    BATCH_01_PATH,
    BATCH_02_PATH,
    CAN_RULE_PATH,
    QUERY_PATH,
    RULE_INDEX_PATH,
    build_artifact,
    load_json,
    validate_artifact,
)
from ulga.builders.build_a1_grammar_representative_vertical_slice import UNIT_SPECS  # noqa: E402


def sources():
    return (
        load_json(QUERY_PATH),
        load_json(RULE_INDEX_PATH),
        load_json(AUTHORITY_PATH),
        load_json(CAN_RULE_PATH),
        load_json(BATCH_01_PATH),
        load_json(BATCH_02_PATH),
    )


def built():
    payloads = sources()
    artifact = build_artifact(*payloads)
    report = validate_artifact(artifact, *payloads)
    return artifact, report, payloads


def test_full_candidate_coverage_reaches_24_units_and_109_rows():
    artifact, report, _ = built()
    summary = artifact["coverage_summary"]

    assert report["validation_status"] == "PASS"
    assert len(artifact["learning_units"]) == 24
    assert len(artifact["by_egp_row_id"]) == 109
    assert summary["candidate_teaching_ready_unit_count"] == 24
    assert summary["candidate_practice_ready_unit_count"] == 24
    assert summary["candidate_assessment_ready_unit_count"] == 24
    assert summary["candidate_teachable_unique_egp_row_count"] == 109
    assert summary["candidate_teachable_unit_coverage_percent"] == 100.0
    assert summary["candidate_teachable_row_coverage_percent"] == 100.0
    assert summary["practice_item_count"] == 144
    assert summary["assessment_item_count"] == 48


def test_all_units_have_complete_candidate_learning_sections():
    artifact, _, _ = built()

    for unit in artifact["learning_units"]:
        assert len(unit["learning_objectives"]) >= 2
        assert len(unit["form_rules"]) >= 1
        assert len(unit["meaning_functions"]) >= 1
        assert len(unit["usage_conditions"]) >= 2
        assert len(unit["positive_examples"]) >= 2
        assert len(unit["negative_examples"]) >= 3
        assert len(unit["common_error_tags"]) >= 3
        assert len(unit["contrast_unit_ids"]) >= 1
        assert len(unit["practice_items"]) == 6
        assert len(unit["assessment_items"]) == 2
        assert unit["readiness"]["candidate_teachable"] is True
        assert unit["readiness"]["candidate_practice_ready"] is True
        assert unit["readiness"]["candidate_assessment_ready"] is True
        assert unit["readiness"]["promoted_for_private_learning"] is False
        assert unit["readiness"]["mastery_trackable"] is False


def test_all_192_activity_grammar_gates_pass():
    _, report, _ = built()

    assert report["validation_counts"]["practice_and_assessment_grammar_gate_target_count"] == 192
    assert report["validation_counts"]["unique_item_id_count"] == 192
    assert report["gate_checks"]["practice_item_grammar_gates_pass"] is True


def test_every_canonical_row_is_candidate_teachable_but_not_promoted():
    artifact, _, _ = built()

    for row_id, binding in artifact["by_egp_row_id"].items():
        assert binding["egp_row_id"] == row_id
        assert binding["grammar_unit_ids"]
        assert binding["candidate_teachable_status"] == "PROJECT_AUTHORED_CANDIDATE_READY"
        assert binding["promoted_private_learning_status"] == "NOT_PROMOTED"


def test_builder_does_not_mutate_sources():
    payloads = sources()
    before = copy.deepcopy(payloads)

    build_artifact(*payloads)

    assert payloads == before


def test_missing_row_fails_closed():
    artifact, _, payloads = built()
    unit = next(unit for unit in artifact["learning_units"] if unit["canonical_egp_row_ids"])
    row_id = unit["canonical_egp_row_ids"].pop()
    unit["canonical_egp_row_count"] -= 1
    artifact["by_egp_row_id"].pop(row_id, None)

    report = validate_artifact(artifact, *payloads)

    assert report["validation_status"] == "FAIL"
    assert any(error.startswith("canonical_row_mismatch") for error in report["errors"])


def test_false_private_learning_promotion_fails_closed():
    artifact, _, payloads = built()
    artifact["claim_boundaries"]["private_learning_promotion_complete"] = True
    artifact["learning_units"][0]["readiness"]["promoted_for_private_learning"] = True

    report = validate_artifact(artifact, *payloads)

    assert report["validation_status"] == "FAIL"
    assert "false_review_or_promotion_claim" in report["errors"]
    assert any(error.startswith("false_promotion_or_mastery_claim") for error in report["errors"])


def test_positive_and_activity_tampering_fail_closed():
    artifact, _, payloads = built()
    artifact["learning_units"][0]["positive_examples"][0]["text"] = "Not a matching target."
    artifact["learning_units"][1]["practice_items"][0]["grammar_gate"]["validation_targets"][0]["text"] = "Not a matching target."

    report = validate_artifact(artifact, *payloads)

    assert report["validation_status"] == "FAIL"
    assert any(error.startswith("positive_example_gate_fail") for error in report["errors"])
    assert any(error.startswith("practice_item_grammar_gate_fail") for error in report["errors"])


def test_scope_remains_a1_only_without_mastery_runtime():
    artifact, _, _ = built()
    boundaries = artifact["claim_boundaries"]

    assert boundaries["full_24_unit_candidate_teachable_coverage_complete"] is True
    assert boundaries["full_109_row_candidate_teachable_coverage_complete"] is True
    assert boundaries["operator_review_complete"] is False
    assert boundaries["private_learning_promotion_complete"] is False
    assert boundaries["learner_mastery_runtime_complete"] is False
    assert boundaries["no_a2_a2plus_expansion"] is True
    assert boundaries["no_learner_state_write"] is True



def test_tamper_validation_does_not_mutate_global_unit_specs():
    before = copy.deepcopy(UNIT_SPECS)
    artifact, _, payloads = built()

    artifact["learning_units"][0]["positive_examples"][0]["text"] = (
        "Not a matching target."
    )
    artifact["learning_units"][1]["practice_items"][0]["grammar_gate"][
        "validation_targets"
    ][0]["text"] = "Not a matching target."

    report = validate_artifact(artifact, *payloads)

    assert report["validation_status"] == "FAIL"
    assert UNIT_SPECS == before

    _, rebuilt_report, _ = built()
    assert rebuilt_report["validation_status"] == "PASS"
