from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_u01data05b_unit01_article_noun_phrase_pattern_reconciliation as builder
from ulga.validators import validate_a1fs_v1_u01data05b_unit01_article_noun_phrase_pattern_reconciliation as validator


def projection() -> dict:
    existing_ids = [
        "U01-R-01", "U01-R-02", "U01-R-03", "U01-R-04",
        "U01-W-01", "U01-W-02", "U01-W-03", "U01-W-04",
        "U01-S-01", "U01-S-02", "U01-S-03",
    ]
    fixed_ids = sorted(
        set(builder.EXPECTED_ARTICLE_NP_ACTIVITY_IDS) - set(existing_ids)
    ) + [builder.OPEN_WRITING_ACTIVITY_ID]

    def row(activity_id: str, source: str) -> dict:
        skill = (
            "READING" if "-R" in activity_id
            else "WRITING" if "-W" in activity_id
            else "SPEAKING"
        )
        return {
            "activity_id": activity_id,
            "activity_source": source,
            "skill": skill,
            "question_type": "fixture",
            "target_pattern_ids": ["SP_000016", "SP_000017"],
        }

    core = {
        "task_id": "A1FS-V1-U01DATA02_Unit01ExistingU01ELanguageSentenceQuestionProjectionAndCumulativeLinkage",
        "unit": {"unit_id": builder.UNIT_ID},
        "activity_projections": {
            "existing_response_contract_activities": [
                row(value, "EXISTING_RESPONSE_CONTRACT") for value in existing_ids
            ],
            "fixed_admitted_items": [
                row(value, "U01E_S03_FIXED_ADMITTED_ITEM_BANK") for value in fixed_ids
            ],
        },
        "linkage_summary": {"total_activity_count": 24},
    }
    core["projection_sha256"] = builder.digest(core)
    return core


def test_build_and_validate_exact_reconciliation() -> None:
    report = builder.build_report(projection())
    result = validator.validate_report(report)
    assert result["validation_status"] == validator.PASS_STATUS
    assert report["coverage_summary"]["activity_count_by_unit_local_pattern"] == {
        "U01-NP-ARTICLE-NOUN": 23,
        "U01-NP-ARTICLE-ADJECTIVE-NOUN": 0,
        "U01-NP-A-VERY-ADJECTIVE-NOUN": 0,
    }
    assert report["coverage_summary"]["demonstrative_pattern_coverage_count"] == 0


def test_this_and_that_are_deferred_not_redefined() -> None:
    report = builder.build_report(projection())
    assert [row["pattern_id"] for row in report["deferred_global_patterns"]] == [
        "SP_000016", "SP_000017"
    ]
    assert all(
        row["coverage_claim_allowed"] is False
        for row in report["deferred_global_patterns"]
    )
    assert report["boundaries"]["existing_pattern_ids_redefined"] is False
    assert report["boundaries"]["new_that_is_frame_created"] is False


def test_np_structures_remain_separate_coverage_rows() -> None:
    report = builder.build_report(projection())
    patterns = report["unit_local_pattern_contract"]["patterns"]
    assert [row["structural_signature"] for row in patterns] == [
        "DET+N", "DET+ADJ+N", "DET+VERY+ADJ+N"
    ]
    assert report["coverage_summary"]["coverage_merge_across_np_structures_allowed"] is False


def test_open_writing_waits_for_real_response() -> None:
    report = builder.build_report(projection())
    row = next(
        row for row in report["activity_pattern_reconciliations"]
        if row["activity_id"] == builder.OPEN_WRITING_ACTIVITY_ID
    )
    assert row["activity_realized_pattern_ids"] == []
    assert row["pattern_coverage_eligible"] is False
    assert row["pattern_resolution_status"] == "PENDING_LEARNER_RESPONSE_AND_HUMAN_REVIEW"


def test_non_broadcast_input_fails_closed() -> None:
    source = projection()
    source["activity_projections"]["existing_response_contract_activities"][0][
        "target_pattern_ids"
    ] = ["SP_000016"]
    source["projection_sha256"] = builder.digest(
        {key: value for key, value in source.items() if key != "projection_sha256"}
    )
    with pytest.raises(
        builder.ReconciliationError,
        match="LEGACY_PATTERN_BROADCAST_SHAPE_INVALID",
    ):
        builder.build_report(source)


def test_tampered_output_digest_fails() -> None:
    report = builder.build_report(projection())
    tampered = deepcopy(report)
    tampered["coverage_summary"]["demonstrative_pattern_coverage_count"] = 1
    with pytest.raises(
        validator.ValidationError,
        match="RECONCILIATION_DIGEST_INVALID",
    ):
        validator.validate_report(tampered)
