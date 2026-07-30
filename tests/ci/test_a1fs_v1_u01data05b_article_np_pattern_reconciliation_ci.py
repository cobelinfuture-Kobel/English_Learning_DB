from __future__ import annotations

from ulga.builders import build_a1fs_v1_u01data05b_unit01_article_noun_phrase_pattern_reconciliation as builder
from ulga.validators import validate_a1fs_v1_u01data05b_unit01_article_noun_phrase_pattern_reconciliation as validator


def _projection() -> dict:
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


def test_u01data05b_ci_gate() -> None:
    report = builder.build_report(_projection())
    result = validator.validate_report(report)
    summary = report["coverage_summary"]
    assert result["validation_status"] == validator.PASS_STATUS
    assert summary["activity_count"] == 24
    assert summary["coverage_eligible_activity_count"] == 23
    assert summary["pending_open_writing_activity_count"] == 1
    assert summary["legacy_demonstrative_broadcast_activity_count"] == 24
    assert summary["demonstrative_pattern_coverage_count"] == 0
    assert summary["covered_unit_local_pattern_ids"] == [
        "U01-NP-ARTICLE-NOUN"
    ]
    assert summary["uncovered_unit_local_pattern_ids"] == [
        "U01-NP-A-VERY-ADJECTIVE-NOUN",
        "U01-NP-ARTICLE-ADJECTIVE-NOUN",
    ]
    assert all(value is False for value in report["boundaries"].values())
