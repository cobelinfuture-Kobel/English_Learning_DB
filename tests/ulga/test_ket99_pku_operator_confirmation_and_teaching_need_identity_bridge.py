from __future__ import annotations

import copy

from ulga.builders import build_ket99_pku_operator_confirmation_and_teaching_need_identity_bridge as builder
from ulga.validators import validate_ket99_pku_operator_confirmation_and_teaching_need_identity_bridge as validator


def _build() -> dict:
    return builder.build_from_paths(
        m1_json=builder.DEFAULT_M1_JSON,
        m1_csv=builder.DEFAULT_M1_CSV,
        decision_path=builder.DEFAULT_DECISION,
    )


def test_operator_confirmation_bridge_builds_and_validates() -> None:
    artifact = _build()
    report = validator.validate_artifact(artifact)
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert artifact["counts"] == {
        "source_transcript_count": 5,
        "source_pku_count": 35,
        "confirmed_pilot_admission_count": 32,
        "confirmed_exam_procedure_rejection_count": 3,
        "existing_authority_join_count": 10,
        "soft_teaching_need_identity_count": 22,
        "teaching_need_identity_count": 32,
        "production_lesson_mapping_count": 0,
        "hard_graph_mutation_count": 0,
    }
    assert artifact["stop_reason"] == "NONE"
    assert artifact["next_short_step"] == builder.NEXT_SHORT_STEP


def test_bridge_build_is_deterministic() -> None:
    assert _build() == _build()


def test_hard_graph_or_production_mapping_tamper_fails_closed() -> None:
    artifact = _build()
    tampered = copy.deepcopy(artifact)
    tampered["authority_contract"]["hard_graph_mutation_allowed"] = True
    tampered["counts"]["production_lesson_mapping_count"] = 1
    report = validator.validate_artifact(tampered)
    assert report["validation_status"] == validator.FAIL_STATUS
    assert "authority_boundary_invalid:hard_graph_mutation_allowed" in report["errors"]
    assert "count_invalid:production_lesson_mapping_count" in report["errors"]


def test_exam_procedure_rows_remain_rejected_without_identity() -> None:
    artifact = _build()
    assert len(artifact["rejected_records"]) == 3
    assert all(row["teaching_need_identity_id"] is None for row in artifact["rejected_records"])
    assert all(row["lesson_mapping_allowed"] is False for row in artifact["rejected_records"])
