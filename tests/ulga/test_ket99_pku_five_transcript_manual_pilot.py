from __future__ import annotations

import copy
from pathlib import Path

from ulga.validators import validate_ket99_pku_five_transcript_manual_pilot as validator

ROOT = Path(__file__).resolve().parents[2]
JSON_PATH = ROOT / "ulga/reports/ket99_pku_pilot/ket99_pedagogical_knowledge_units.pilot.json"
CSV_PATH = ROOT / "ulga/reports/ket99_pku_pilot/ket99_pku_pilot_review.csv"


def test_committed_manual_pilot_passes() -> None:
    artifact = validator.load_json(JSON_PATH)
    rows = validator.load_csv(CSV_PATH)
    report = validator.validate_artifact(artifact, rows)
    assert report["validation_status"] == validator.PASS_STATUS, report["errors"]
    assert report["source_transcript_count"] == 5
    assert report["pku_count"] == 35
    assert report["exact_authority_join_ready_count"] == 10
    assert report["pending_teaching_need_identity_count"] == 22
    assert report["rejected_exam_procedure_count"] == 3
    assert report["production_lesson_mapping_count"] == 0
    assert report["operator_confirmation_required"] is True
    assert report["a2_status"] == "LOCKED"


def test_keyword_or_production_promotion_tamper_fails_closed() -> None:
    artifact = validator.load_json(JSON_PATH)
    rows = validator.load_csv(CSV_PATH)
    tampered = copy.deepcopy(artifact)
    tampered["authority_contract"]["keyword_only_mapping_allowed"] = True
    tampered["counts"]["production_lesson_mapping_count"] = 1
    report = validator.validate_artifact(tampered, rows)
    assert report["validation_status"] == "FAIL_KET99_PK_M1_MANUAL_PILOT_VALIDATION"
    assert any("authority_lock_invalid:keyword_only_mapping_allowed" == value for value in report["errors"])
    assert any("count_invalid:production_lesson_mapping_count" == value for value in report["errors"])


def test_csv_must_remain_operator_review_surface() -> None:
    artifact = validator.load_json(JSON_PATH)
    rows = validator.load_csv(CSV_PATH)
    tampered = copy.deepcopy(rows)
    tampered[0]["operator_decision"] = "APPROVE"
    report = validator.validate_artifact(artifact, tampered)
    assert report["validation_status"] == "FAIL_KET99_PK_M1_MANUAL_PILOT_VALIDATION"
    assert any("csv_operator_decision_not_blank" in value for value in report["errors"])
