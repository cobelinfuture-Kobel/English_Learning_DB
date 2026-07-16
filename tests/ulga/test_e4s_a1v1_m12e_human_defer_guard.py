from __future__ import annotations

import json
from pathlib import Path

from ulga.builders import build_e4s_a1v1_m12e_representative_pilot_evidence_qa as builder


def _base_report(deferred_count: int) -> dict:
    return {
        "evidence_summary": {
            "outcome_counts": {"HUMAN_DEFER": deferred_count},
        },
        "quality_gate": {
            "state": "PASS_COVERAGE_EXPANSION_REQUIRED",
            "human_review_required": False,
            "remediation_required": False,
            "representative_batch_valid": True,
            "deterministic_evidence_valid": True,
        },
        "stop_reason": "NONE",
        "next_short_step": "E4S-A1V1-M12F_CoverageExpansionBatch",
    }


def test_human_defer_stays_on_review_gate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        builder,
        "_original_build_qa",
        lambda *args, **kwargs: _base_report(1),
    )
    monkeypatch.setattr(builder._core, "_assert_schema", lambda value: None)

    result = builder.build_qa(
        tmp_path / "m12",
        tmp_path / "m12c",
        tmp_path / "m12d",
        tmp_path / "m12e",
        expected_origin="TEST_FIXTURE",
    )

    assert result["quality_gate"]["state"] == "PASS_HUMAN_REVIEW_REQUIRED"
    assert result["quality_gate"]["human_review_required"] is True
    assert result["stop_reason"] == "HUMAN_REVIEW_DECISIONS_REQUIRED"
    assert result["next_short_step"] == "E4S-A1V1-M12E1_HumanReviewDecisionMaterialization"
    persisted = json.loads(
        (tmp_path / "m12e/representative_evidence_qa_safe_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert persisted == result


def test_zero_human_defer_preserves_core_result(
    tmp_path: Path,
    monkeypatch,
) -> None:
    original = _base_report(0)
    monkeypatch.setattr(
        builder,
        "_original_build_qa",
        lambda *args, **kwargs: original,
    )

    result = builder.build_qa(
        tmp_path / "m12",
        tmp_path / "m12c",
        tmp_path / "m12d",
        tmp_path / "m12e",
        expected_origin="TEST_FIXTURE",
    )

    assert result is original
    assert result["stop_reason"] == "NONE"
    assert result["next_short_step"] == "E4S-A1V1-M12F_CoverageExpansionBatch"
