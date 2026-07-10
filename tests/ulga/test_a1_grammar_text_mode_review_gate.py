from __future__ import annotations

import copy

import pytest

from ulga.builders.build_a1_grammar_text_mode_review_gate import (
    REVIEW_DIMENSIONS,
    apply_review_decisions,
    build_artifact,
    validate_artifact,
    validate_decisions,
)


def fixtures():
    unit_ids = [f"GRAMMAR_UNIT_{index:02d}" for index in range(24)]
    row_ids = [f"ROW_{index:03d}" for index in range(109)]
    assignments = {unit_id: [] for unit_id in unit_ids}
    for index, row_id in enumerate(row_ids):
        assignments[unit_ids[index % 24]].append(row_id)
    candidate = {
        "artifact_id": "candidate",
        "learning_units": [
            {
                "grammar_unit_id": unit_id,
                "internal_stage": "A1" if index < 15 else "A1+",
                "canonical_egp_row_ids": assignments[unit_id],
                "content_authority_status": "PROJECT_AUTHORED_CANDIDATE",
            }
            for index, unit_id in enumerate(unit_ids)
        ],
        "by_egp_row_id": {
            row_id: {"grammar_unit_ids": [unit_ids[index % 24]]}
            for index, row_id in enumerate(row_ids)
        },
    }
    cross_skill = {
        "artifact_id": "closure",
        "by_grammar_unit_id": {
            unit_id: {
                "skill_paths": {
                    "reading": {
                        "activity_ids": [f"{unit_id}:R:{i}" for i in range(4)],
                        "assessment_ids": [f"{unit_id}:R:A"],
                    },
                    "writing": {
                        "activity_ids": [f"{unit_id}:W:{i}" for i in range(4)],
                        "assessment_ids": [f"{unit_id}:W:A"],
                    },
                    "listening": {"activity_ids": [], "assessment_ids": []},
                    "speaking": {"activity_ids": [], "assessment_ids": []},
                }
            }
            for unit_id in unit_ids
        },
        "by_egp_row_id": {row_id: {} for row_id in row_ids},
    }
    return candidate, cross_skill


def approvals(artifact):
    return {
        item["grammar_unit_id"]: {
            "decision": "APPROVE_TEXT_MODE",
            "reviewer_ref": "operator:reviewer",
            "evidence_ref": f"review://{item['grammar_unit_id']}",
        }
        for item in artifact["review_queue"]
    }


def test_review_gate_covers_24_units_and_109_rows():
    candidate, closure = fixtures()
    artifact = build_artifact(candidate, closure)
    report = validate_artifact(artifact, candidate, closure)

    assert report["validation_status"] == "PASS"
    assert len(artifact["review_queue"]) == 24
    assert artifact["coverage_summary"]["text_mode_review_queue_row_count"] == 109
    assert artifact["coverage_summary"]["approved_text_mode_unit_count"] == 0


def test_audio_is_deferred_but_does_not_block_text_review():
    candidate, closure = fixtures()
    artifact = build_artifact(candidate, closure)
    gate = artifact["release_gates"]["audio_scope_gate"]

    assert gate["status"] == "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE"
    assert gate["blocks_text_mode"] is False
    assert gate["blocks_full_four_skill_release"] is True
    assert artifact["claim_boundaries"]["audio_scope_complete"] is False


def test_each_unit_has_all_review_dimensions_and_rw_evidence():
    candidate, closure = fixtures()
    artifact = build_artifact(candidate, closure)

    for item in artifact["review_queue"]:
        assert set(item["review_dimensions"]) == set(REVIEW_DIMENSIONS)
        assert len(item["text_mode_evidence"]["reading_activity_ids"]) == 4
        assert len(item["text_mode_evidence"]["writing_activity_ids"]) == 4
        assert item["deferred_skill_policy"]["audio_is_required_for_text_mode_review"] is False


def test_all_approved_decisions_open_text_mode_only():
    candidate, closure = fixtures()
    artifact = build_artifact(candidate, closure)
    reviewed = apply_review_decisions(artifact, approvals(artifact))

    assert reviewed["coverage_summary"]["approved_text_mode_unit_count"] == 24
    assert reviewed["coverage_summary"]["text_mode_pilot_eligible_row_count"] == 109
    assert reviewed["release_gates"]["text_mode_private_pilot_gate"]["status"] == (
        "PASS_READY_FOR_OPERATOR_CONTROLLED_PILOT"
    )
    assert reviewed["claim_boundaries"]["text_mode_private_pilot_eligible"] is True
    assert reviewed["claim_boundaries"]["full_four_skill_release_complete"] is False
    assert reviewed["decision_application"]["audio_scope_remains_deferred"] is True


def test_rejection_keeps_text_mode_gate_blocked():
    candidate, closure = fixtures()
    artifact = build_artifact(candidate, closure)
    decisions = approvals(artifact)
    first = next(iter(decisions))
    decisions[first]["decision"] = "REJECT"
    reviewed = apply_review_decisions(artifact, decisions)

    assert reviewed["coverage_summary"]["rejected_unit_count"] == 1
    assert reviewed["claim_boundaries"]["text_mode_private_pilot_eligible"] is False
    assert reviewed["release_gates"]["text_mode_private_pilot_gate"]["status"] == (
        "BLOCKED_PENDING_FULL_TEXT_REVIEW_APPROVAL"
    )


def test_missing_or_invalid_decisions_fail_closed():
    candidate, closure = fixtures()
    artifact = build_artifact(candidate, closure)
    decisions = approvals(artifact)
    decisions.pop(next(iter(decisions)))
    assert validate_decisions(
        decisions, {item["grammar_unit_id"] for item in artifact["review_queue"]}
    )

    decisions = approvals(artifact)
    first = next(iter(decisions))
    decisions[first]["decision"] = "MAYBE"
    with pytest.raises(ValueError, match="invalid_review_decision"):
        apply_review_decisions(artifact, decisions)


def test_builder_and_decision_application_do_not_mutate_inputs():
    candidate, closure = fixtures()
    before_sources = copy.deepcopy((candidate, closure))
    artifact = build_artifact(candidate, closure)
    before_artifact = copy.deepcopy(artifact)

    apply_review_decisions(artifact, approvals(artifact))

    assert (candidate, closure) == before_sources
    assert artifact == before_artifact


def test_false_audio_or_review_completion_claim_fails_closed():
    candidate, closure = fixtures()
    artifact = build_artifact(candidate, closure)
    artifact["claim_boundaries"]["audio_scope_complete"] = True
    artifact["claim_boundaries"]["operator_text_review_complete"] = True

    report = validate_artifact(artifact, candidate, closure)

    assert report["validation_status"] == "FAIL"
    assert "false_completion_claim:audio_scope_complete" in report["errors"]
    assert "false_completion_claim:operator_text_review_complete" in report["errors"]


def test_forged_text_mode_gate_fails_closed():
    candidate, closure = fixtures()
    artifact = build_artifact(candidate, closure)
    artifact["release_gates"]["text_mode_private_pilot_gate"]["status"] = "PASS"

    report = validate_artifact(artifact, candidate, closure)

    assert report["validation_status"] == "FAIL"
    assert "text_mode_gate_forged_open" in report["errors"]


def test_missing_canonical_row_fails_closed():
    candidate, closure = fixtures()
    artifact = build_artifact(candidate, closure)
    artifact["review_queue"][0]["canonical_egp_row_ids"].pop()

    report = validate_artifact(artifact, candidate, closure)

    assert report["validation_status"] == "FAIL"
    assert "review_queue_not_109_canonical_rows" in report["errors"]
