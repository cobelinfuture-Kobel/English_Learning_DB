from __future__ import annotations

import copy
import json
from pathlib import Path

from ulga.builders.build_a1_grammar_operator_confirmation_text_mode_pilot import (
    ARTICLE_GATE_CASES,
    build_and_validate_from_repo,
    build_resolved_pedagogy_source,
    validate_artifact,
)
from ulga.query.a1_canonical_validator_dispatcher import (
    ARTICLES_GRAMMAR_ID,
    VALIDATOR_REGISTRY,
    validate,
)
from ulga.validators.validate_a1_articles_number_agreement_fullfix import (
    classify_articles_number_agreement,
)


def test_direct_article_validator_accepts_singular_and_definite_plural_forms():
    for text in (
        "a cat",
        "an apple",
        "the book",
        "the books",
        "a bus",
        "a class",
        "an address",
        "a red book",
    ):
        decision = classify_articles_number_agreement(text)
        assert decision.match is True, (text, decision)


def test_direct_article_validator_rejects_regular_and_irregular_plural_after_indefinite_article():
    for text in (
        "a books",
        "an apples",
        "a children",
        "a red books",
        "a boxes",
        "an oranges",
    ):
        decision = classify_articles_number_agreement(text)
        assert decision.match is False, (text, decision)
        assert decision.reason in {
            "article_number_agreement_gate",
            "a_an_phonology_gate",
        }


def test_direct_article_validator_preserves_legacy_negative_cases():
    for text in ("apple", "two cats", "John"):
        assert classify_articles_number_agreement(text).match is False


def test_dispatcher_uses_the_fullfix_route():
    assert VALIDATOR_REGISTRY[ARTICLES_GRAMMAR_ID] is classify_articles_number_agreement
    result = validate(ARTICLES_GRAMMAR_ID, "a books")
    assert result["dispatch_status"] == "VALIDATOR_EXECUTED"
    assert result["match"] is False
    assert result["reason"] == "article_number_agreement_gate"


def test_all_declared_article_gate_cases_pass():
    for text, expected in ARTICLE_GATE_CASES:
        result = validate(ARTICLES_GRAMMAR_ID, text)
        assert result["match"] is expected, (text, result)


def test_resolved_pedagogy_rebuild_clears_historical_gap_and_keeps_full_identity():
    pedagogy, report = build_resolved_pedagogy_source()
    assert report["validation_status"] == "PASS"
    assert len(pedagogy["learning_units"]) == 24
    assert len(pedagogy["by_egp_row_id"]) == 109
    assert report["coverage_summary"]["text_mode_item_count"] == 192
    assert pedagogy["coverage_summary"]["known_validator_gap_count"] == 0
    assert pedagogy["known_validator_gaps"] == []
    assert (
        pedagogy["claim_boundaries"]["all_negative_examples_automatically_certified"]
        is True
    )
    assert pedagogy["validator_gap_resolution"]["remaining_gap_count"] == 0


def test_resolved_articles_negative_example_has_no_stale_validator_limit():
    pedagogy, _ = build_resolved_pedagogy_source()
    articles = next(
        unit
        for unit in pedagogy["learning_units"]
        if unit["grammar_unit_id"] == ARTICLES_GRAMMAR_ID
    )
    example = next(
        item for item in articles["negative_examples"] if item["text"] == "a books"
    )
    assert "validator_limit" not in example
    assert validate(ARTICLES_GRAMMAR_ID, example["text"])["match"] is False


def test_operator_confirmation_opens_only_text_mode_pilot_gate():
    artifact, report = build_and_validate_from_repo()
    assert report["validation_status"] == "PASS"
    assert artifact["coverage_summary"]["operator_approved_unit_count"] == 24
    assert artifact["coverage_summary"]["text_mode_pilot_eligible_row_count"] == 109
    assert artifact["release_gates"]["operator_confirmation_gate"] == "PASS"
    assert artifact["release_gates"]["text_mode_private_pilot_gate"] == (
        "PASS_READY_FOR_OPERATOR_CONTROLLED_PILOT"
    )
    assert artifact["release_gates"]["audio_scope_gate"] == (
        "DEFERRED_NON_BLOCKING_FOR_TEXT_MODE"
    )
    assert artifact["claim_boundaries"]["text_mode_private_pilot_started"] is False
    assert artifact["claim_boundaries"]["actual_learner_evidence_complete"] is False


def test_all_24_approvals_have_real_operator_evidence_refs():
    artifact, _ = build_and_validate_from_repo()
    assert len(artifact["approvals"]) == 24
    for approval in artifact["approvals"]:
        assert approval["operator_decision"] == "APPROVE_TEXT_MODE"
        assert approval["operator_reviewer_ref"] == "operator:cobelinfuture-Kobel"
        assert approval["operator_evidence_ref"].startswith(
            "operator_chat_decision://2026-07-10/"
        )
        assert approval["text_mode_private_pilot_eligible"] is True


def test_articles_approval_traces_the_resolved_gap():
    artifact, _ = build_and_validate_from_repo()
    articles = next(
        item
        for item in artifact["approvals"]
        if item["grammar_unit_id"] == ARTICLES_GRAMMAR_ID
    )
    assert articles["resolved_validator_gap"] == (
        "ARTICLE_NUMBER_AGREEMENT_GATE_NOT_IMPLEMENTED"
    )
    assert articles["resolution_status"] == (
        "RESOLVED_BY_CANONICAL_DISPATCHER_FULLFIX"
    )
    assert artifact["article_validator_fullfix"]["remaining_gap_count"] == 0


def test_promotion_builder_is_deterministic_and_non_mutating():
    artifact, report = build_and_validate_from_repo()
    assert report["validation_status"] == "PASS"
    before = copy.deepcopy(artifact)
    assert artifact == before


def test_forged_audio_or_started_pilot_claim_fails_closed():
    artifact, _ = build_and_validate_from_repo()
    artifact["claim_boundaries"]["audio_scope_complete"] = True
    artifact["claim_boundaries"]["text_mode_private_pilot_started"] = True
    pedagogy, pedagogy_report = build_resolved_pedagogy_source()
    assert pedagogy_report["validation_status"] == "PASS"
    validation = validate_artifact(artifact, pedagogy)
    assert validation["validation_status"] == "FAIL"
    assert "false_completion_claim:audio_scope_complete" in validation["errors"]
    assert (
        "false_completion_claim:text_mode_private_pilot_started"
        in validation["errors"]
    )


def test_operator_confirmation_artifact_has_exact_24_unit_scope():
    path = Path("ulga/reviews/a1_grammar_text_mode_operator_confirmations.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["decision"] == (
        "APPROVE_TEXT_MODE_AFTER_ARTICLES_VALIDATOR_FULLFIX"
    )
    assert len(payload["approved_unit_ids"]) == 24
    assert len(set(payload["approved_unit_ids"])) == 24
    assert payload["approval_scope"]["reading"] is True
    assert payload["approval_scope"]["writing"] is True
    assert payload["approval_scope"]["listening_audio"] is False
    assert payload["approval_scope"]["speaking_audio"] is False
    assert payload["approval_scope"]["persistent_learner_state"] is False
