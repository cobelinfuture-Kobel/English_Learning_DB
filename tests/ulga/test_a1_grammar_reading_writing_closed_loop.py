from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_grammar_full_teachable_candidate_coverage import (  # noqa: E402
    build_and_validate_from_repo as build_candidate_source,
)
from ulga.builders.build_a1_grammar_reading_writing_closed_loop import (  # noqa: E402
    build_artifact,
    validate_artifact,
)


def built():
    candidate, candidate_report = build_candidate_source()
    assert candidate_report["validation_status"] == "PASS"
    artifact = build_artifact(candidate)
    report = validate_artifact(artifact, candidate)
    return artifact, report, candidate


def test_reading_writing_closure_passes_for_24_units_and_109_rows():
    artifact, report, _ = built()
    summary = artifact["coverage_summary"]

    assert report["validation_status"] == "PASS"
    assert len(artifact["by_grammar_unit_id"]) == 24
    assert len(artifact["by_egp_row_id"]) == 109
    assert summary["reading_activity_count"] == 96
    assert summary["writing_activity_count"] == 96
    assert summary["candidate_cross_skill_closed_row_count"] == 109
    assert summary["candidate_cross_skill_row_coverage_percent"] == 100.0


def test_each_unit_has_balanced_reading_writing_and_assessment_paths():
    artifact, _, _ = built()

    for unit in artifact["by_grammar_unit_id"].values():
        assert len(unit["reading_activity_ids"]) == 4
        assert len(unit["writing_activity_ids"]) == 4
        assert len(unit["reading_assessment_ids"]) == 1
        assert len(unit["writing_assessment_ids"]) == 1
        assert unit["cross_skill_closure_status"] == "CANDIDATE_READING_WRITING_CLOSED"


def test_each_row_has_receptive_productive_and_assessment_paths():
    artifact, _, _ = built()

    for row in artifact["by_egp_row_id"].values():
        assert row["reading_activity_ids"]
        assert row["writing_activity_ids"]
        assert row["reading_assessment_ids"]
        assert row["writing_assessment_ids"]
        assert row["reading_evidence_dimensions"]
        assert row["writing_evidence_dimensions"]
        assert row["learner_mastery_status"] == "NOT_MEASURED"


def test_all_192_source_activities_are_preserved_and_gated():
    artifact, report, candidate = built()
    source_ids = {
        item["item_id"]
        for unit in candidate["learning_units"]
        for item in unit["practice_items"] + unit["assessment_items"]
    }
    output_ids = {
        item["activity_id"]
        for item in artifact["reading_activity_bank"] + artifact["writing_activity_bank"]
    }

    assert output_ids == source_ids
    assert len(output_ids) == 192
    assert report["gate_checks"]["all_activity_grammar_gates_pass"] is True


def test_builder_does_not_mutate_candidate_source():
    _, _, candidate = built()
    before = copy.deepcopy(candidate)

    build_artifact(candidate)

    assert candidate == before


def test_missing_writing_activity_fails_closed():
    artifact, _, candidate = built()
    removed = artifact["writing_activity_bank"].pop()
    unit = artifact["by_grammar_unit_id"][removed["grammar_unit_id"]]
    unit["writing_activity_ids"].remove(removed["activity_id"])

    report = validate_artifact(artifact, candidate)

    assert report["validation_status"] == "FAIL"
    assert "reading_writing_activity_count_mismatch" in report["errors"]
    assert "activity_identity_partition_mismatch" in report["errors"]


def test_activity_grammar_tamper_fails_closed():
    artifact, _, candidate = built()
    item = artifact["reading_activity_bank"][0]
    item["grammar_gate"]["validation_targets"][0]["text"] = "Not a matching target."

    report = validate_artifact(artifact, candidate)

    assert report["validation_status"] == "FAIL"
    assert any(error.startswith("activity_grammar_gate_fail") for error in report["errors"])


def test_false_promotion_or_mastery_claim_fails_closed():
    artifact, _, candidate = built()
    artifact["claim_boundaries"]["private_learning_promotion_complete"] = True
    artifact["claim_boundaries"]["learner_mastery_runtime_complete"] = True

    report = validate_artifact(artifact, candidate)

    assert report["validation_status"] == "FAIL"
    assert "false_review_or_promotion_claim" in report["errors"]
    assert "false_mastery_runtime_claim" in report["errors"]


def test_scope_remains_a1_only_and_no_learner_writes():
    artifact, _, _ = built()
    boundaries = artifact["claim_boundaries"]

    assert boundaries["candidate_reading_writing_closure_complete"] is True
    assert boundaries["listening_integration_complete"] is False
    assert boundaries["speaking_integration_complete"] is False
    assert boundaries["learner_attempt_collection_complete"] is False
    assert boundaries["learner_mastery_runtime_complete"] is False
    assert boundaries["no_a2_a2plus_expansion"] is True
    assert boundaries["no_learner_state_write"] is True
