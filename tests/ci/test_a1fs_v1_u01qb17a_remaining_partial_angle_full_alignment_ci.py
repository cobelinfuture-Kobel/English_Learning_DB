from __future__ import annotations

from collections import Counter

from ulga.builders import (
    build_a1fs_v1_u01qb17a_unit01_remaining_partial_angle_full_alignment_candidate_reconciliation as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb17a_unit01_remaining_partial_angle_full_alignment_candidate_reconciliation as validator,
)


def test_u01qb17a_reconciles_remaining_partial_angles_without_count_growth() -> None:
    payload = builder.reconciled_payload()
    report = validator.validate_payload(payload)

    assert report["status"] == "PASS"
    assert payload["count_preservation"]["source_base_count"] == 288
    assert payload["count_preservation"]["removed_base_count"] == 24
    assert payload["count_preservation"]["full_alignment_items_added"] == 24
    assert payload["count_preservation"]["reconciled_base_count"] == 288
    assert payload["count_preservation"]["unchanged_real62_extension_count"] == 186
    assert payload["count_preservation"]["projected_runtime_total_count"] == 474
    assert payload["boundaries"]["question_bank_total_expanded"] is False
    assert payload["boundaries"]["runtime_migrated"] is False


def test_reference_evidence_is_a_real_evidence_task_not_an_article_retry() -> None:
    items = [
        row
        for row in builder.reconciled_payload()["reconciled_items"]
        if row["pattern_family_id"] == builder.PF16
    ]
    assert len(items) == 12
    assert Counter(row["support_level"] for row in items) == Counter(
        {"REDUCED_SUPPORT": 6, "INDEPENDENT": 6}
    )
    for row in items:
        assert row["skill"] == "READING"
        assert row["task_angle"] == "REFERENCE_EVIDENCE"
        assert row["question_type"] == "reference_evidence"
        assert "same item" in row["prompt"]
        assert ". The " in row["stimulus"]
        assert row["correct_answer"].startswith("The ")
        assert row["correct_answer"] in row["options"]
        assert row["response_contract"]["scoring_mode"] == "EXACT_TEXT"


def test_phrase_construction_becomes_free_phrase_output_before_sentence_production() -> None:
    items = [
        row
        for row in builder.reconciled_payload()["reconciled_items"]
        if row["pattern_family_id"] == builder.PF17
    ]
    assert len(items) == 12
    assert Counter(row["support_level"] for row in items) == Counter(
        {"GUIDED": 6, "REDUCED_SUPPORT": 6}
    )
    for row in items:
        assert row["skill"] == "WRITING"
        assert row["task_angle"] == "PHRASE_CONSTRUCTION"
        assert row["question_type"] == "phrase_construction"
        assert row["options"] == []
        assert row["response_contract"]["scoring_mode"] == "NORMALIZED_TEXT"
        assert row["correct_answer"] in row["response_contract"]["accepted_texts"]


def test_candidate_admission_is_policy_bound_and_runtime_claim_stays_pending() -> None:
    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    report = validator.validate_approved(candidate, approved)

    assert report["status"] == "PASS"
    assert report["error_count"] == 0
    assert report["reconciled_base_count"] == 288
    assert report["projected_runtime_total_count"] == 474
    assert report["remaining_partial_angle_count"] == 0
    assert report["runtime_migrated"] is False
    alignment = approved["payload"]["partial_angle_alignment"]
    assert alignment["content_contract_full_alignment_candidate_ready"] is True
    assert alignment["runtime_capacity_replay_pending"] is True
    assert alignment["runtime_full_alignment_claimed"] is False
    assert approved["payload"]["next_short_step"] == builder.NEXT_SHORT_STEP


def test_scope_boundaries_remain_frozen() -> None:
    payload = builder.reconciled_payload()
    boundaries = payload["boundaries"]
    assert builder.A1FS_CONTENT_POLICY_MODE == "POLICY_BOUND"
    assert boundaries == {
        "question_bank_total_expanded": False,
        "second_question_bank_created": False,
        "runtime_migrated": False,
        "real62_extension_modified": False,
        "learner_state_modified": False,
        "completed_attempts_modified": False,
        "speaking_scoring_enabled": False,
        "audio_enabled": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
    }
