from __future__ import annotations

import copy

from ulga.builders.build_a1_grammar_derived_pedagogy_fullfix import (
    build_and_validate_from_repo as build_fullfix_source,
)
from ulga.builders.build_a1_grammar_text_mode_rereview_gate import (
    RECOMMEND_APPROVE,
    RECOMMEND_MANUAL,
    RECOMMEND_REVISION,
    audit_unit,
    build_artifact,
    validate_artifact,
)


def built():
    fullfix, fullfix_report = build_fullfix_source()
    assert fullfix_report["validation_status"] == "PASS"
    artifact = build_artifact(fullfix)
    report = validate_artifact(artifact, fullfix)
    return artifact, report, fullfix


def recommendations_by_id(artifact):
    return {
        item["grammar_unit_id"]: item
        for item in artifact["recommendations"]
    }


def test_rereview_covers_24_units_and_109_rows():
    artifact, report, _ = built()
    summary = artifact["coverage_summary"]

    assert report["validation_status"] == "PASS"
    assert len(artifact["recommendations"]) == 24
    assert summary["canonical_unit_count"] == 24
    assert summary["canonical_row_count"] == 109
    assert summary["recommend_approve_unit_count"] == 23
    assert summary["recommend_manual_review_unit_count"] == 1
    assert summary["recommend_revision_unit_count"] == 0


def test_articles_route_to_manual_review_for_declared_validator_gap():
    artifact, _, _ = built()
    articles = recommendations_by_id(artifact)["GRAMMAR_ARTICLES_BASIC"]

    assert articles["recommendation"] == RECOMMEND_MANUAL
    assert articles["manual_review_reasons"] == [
        "ARTICLE_NUMBER_AGREEMENT_GATE_NOT_IMPLEMENTED"
    ]
    assert articles["remediation_blockers"] == []


def test_other_23_units_are_recommended_for_text_mode_approval():
    artifact, _, _ = built()
    recommendations = recommendations_by_id(artifact)

    approved = [
        grammar_id for grammar_id, item in recommendations.items()
        if item["recommendation"] == RECOMMEND_APPROVE
    ]
    assert len(approved) == 23
    assert "GRAMMAR_ARTICLES_BASIC" not in approved
    assert not any(
        item["recommendation"] == RECOMMEND_REVISION
        for item in recommendations.values()
    )


def test_no_operator_decision_or_evidence_is_fabricated():
    artifact, _, _ = built()

    for item in artifact["recommendations"]:
        assert item["operator_confirmation_required"] is True
        assert item["operator_decision"] is None
        assert item["operator_reviewer_ref"] is None
        assert item["operator_evidence_ref"] is None
    assert artifact["coverage_summary"]["operator_confirmed_unit_count"] == 0
    assert artifact["coverage_summary"]["operator_approved_unit_count"] == 0
    assert artifact["claim_boundaries"]["operator_approval_fabricated"] is False


def test_release_gates_remain_blocked_until_operator_confirmation():
    artifact, _, _ = built()
    gates = artifact["release_gates"]

    assert gates["fullfix_remediation_gate"]["status"] == "PASS"
    assert gates["delegated_rereview_gate"]["status"] == "PASS"
    assert gates["operator_confirmation_gate"]["status"] == (
        "BLOCKED_PENDING_OPERATOR_DECISIONS"
    )
    assert gates["text_mode_private_pilot_gate"]["status"] == (
        "BLOCKED_PENDING_OPERATOR_CONFIRMATION"
    )
    assert artifact["claim_boundaries"]["text_mode_private_pilot_eligible"] is False


def test_audio_remains_deferred_and_non_blocking_for_text_mode():
    artifact, _, _ = built()
    audio = artifact["release_gates"]["audio_scope_gate"]

    assert audio["status"] == "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE"
    assert audio["blocks_text_mode"] is False
    assert audio["blocks_full_four_skill_release"] is True
    assert artifact["claim_boundaries"]["audio_scope_deferred"] is True
    assert artifact["claim_boundaries"]["audio_scope_complete"] is False


def test_generic_objective_tamper_returns_revision_recommendation():
    _, _, fullfix = built()
    unit = copy.deepcopy(fullfix["learning_units"][0])
    unit["learning_objectives"][0] = (
        "Recognize the form and meaning of a generic grammar unit."
    )

    result = audit_unit(unit, fullfix["known_validator_gaps"])

    assert result["recommendation"] == RECOMMEND_REVISION
    assert "GENERIC_LEARNING_OBJECTIVE_REMAINS" in result["remediation_blockers"]


def test_missing_writing_rubric_returns_revision_recommendation():
    _, _, fullfix = built()
    unit = copy.deepcopy(fullfix["learning_units"][0])
    item = next(
        item for item in unit["practice_items"]
        if item["task_type"] == "guided_contextual_writing"
    )
    del item["scoring_rubric"]

    result = audit_unit(unit, fullfix["known_validator_gaps"])

    assert result["recommendation"] == RECOMMEND_REVISION
    assert any(
        blocker.startswith("SCORING_RUBRIC_MISSING")
        for blocker in result["remediation_blockers"]
    )


def test_builder_is_deterministic_and_does_not_mutate_source():
    _, _, fullfix = built()
    before = copy.deepcopy(fullfix)

    first = build_artifact(fullfix)
    second = build_artifact(fullfix)

    assert first == second
    assert fullfix == before


def test_forged_text_mode_gate_fails_closed():
    artifact, _, fullfix = built()
    artifact["release_gates"]["text_mode_private_pilot_gate"]["status"] = "PASS"
    artifact["claim_boundaries"]["text_mode_private_pilot_eligible"] = True

    report = validate_artifact(artifact, fullfix)

    assert report["validation_status"] == "FAIL"
    assert "text_mode_pilot_gate_forged_open" in report["errors"]
    assert "false_text_mode_pilot_eligibility" in report["errors"]


def test_stop_reason_requires_human_review_evidence():
    _, report, _ = built()

    assert report["stop_reason"] == "OPERATOR_REVIEW_CONFIRMATION_REQUIRED"
    assert report["blocker_type"] == "HUMAN_REVIEW_EVIDENCE_REQUIRED"
    assert report["next_resume_task"] == (
        "R7-M105N_A1A1PlusOperatorConfirmationAndTextModePrivatePilotIntegration"
    )
