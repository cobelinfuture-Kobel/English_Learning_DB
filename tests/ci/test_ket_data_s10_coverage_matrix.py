from __future__ import annotations

from builders.build_ket_data_s10_coverage_matrix import (
    EXPECTED_ROW_IDS,
    EXPECTED_STATUS_COUNTS,
    materialize,
)
from validators.validate_ket_data_s10_coverage_matrix import validate


def _rows():
    return {row["coverage_id"]: row for row in materialize()["coverage_rows"]}


def test_s10_source_matrix_rows_and_status_counts_are_exact():
    payload = materialize()
    assert [row["coverage_id"] for row in payload["coverage_rows"]] == EXPECTED_ROW_IDS
    assert payload["summary"]["coverage_row_count"] == 7
    assert payload["summary"]["status_counts"] == EXPECTED_STATUS_COUNTS
    assert [row["capability_or_task_family"] for row in payload["coverage_rows"]] == [
        "short-text meaning",
        "multi-text matching",
        "location extraction",
        "connected open cloze",
        "guided message",
        "image description",
        "visual speaking",
    ]


def test_s10_binds_ket_reference_to_s9_and_current_u04_evidence():
    rows = _rows()

    assert rows["KET_S10_COV_001"]["ket_reference"][0]["task_family"] == "SHORT_MESSAGE_MEANING"
    assert rows["KET_S10_COV_001"]["u04_evidence"]["supports_status"] == "missing"

    assert rows["KET_S10_COV_002"]["ket_reference"][0]["task_family"] == "MULTI_TEXT_MATCHING"
    assert rows["KET_S10_COV_002"]["u04_evidence"]["supports_status"] == "partial"

    location = rows["KET_S10_COV_003"]
    assert location["s3_reference_value"] == "LOCATE_EXPLICIT_DETAIL"
    assert len(location["ket_reference"]) == 4
    assert location["u04_evidence"]["supports_status"] == "strong"
    assert "SHORT_READING_LOCATION_EXTRACTION" in location["u04_evidence"]["positive_signals"]
    assert "LISTENING_LOCATION_EXTRACTION" in location["u04_evidence"]["positive_signals"]

    assert rows["KET_S10_COV_004"]["ket_reference"][0]["task_family"] == "OPEN_CLOZE"
    assert rows["KET_S10_COV_005"]["ket_reference"][0]["task_family"] == "GUIDED_MESSAGE"

    image = rows["KET_S10_COV_006"]
    assert image["s3_reference_value"] == "DESCRIBE_VISUAL_RELATION"
    assert image["u04_evidence"]["supports_status"] == "partial"

    visual = rows["KET_S10_COV_007"]
    assert visual["ket_reference"][0]["task_family"] == "SPEAK_VISUAL_DISCUSSION"
    assert visual["u04_evidence"]["supports_status"] == "weak"


def test_s10_preserves_level_adaptation_and_does_not_materialize_content():
    payload = materialize()
    for row in payload["coverage_rows"]:
        for ref in row["ket_reference"]:
            assert ref["NATIVE_LEVEL"] == "A2_KET"
            assert ref["ADAPTABLE_DOWN"] is True
            assert ref["MIN_ADAPTED_LEVEL"] == "A1"
            assert ref["ADAPTATION_RULE"] == "PRESERVE_S3_MECHANIC_REDUCE_RESPONSE_DEMAND"

    summary = payload["summary"]
    assert summary["learner_facing_task_count"] == 0
    assert summary["question_bank_item_count"] == 0
    assert summary["new_content_count"] == 0
    assert summary["a2_or_a2_plus_unlock_count"] == 0
    assert summary["live_model_call_count"] == 0


def test_s10_is_deterministic_and_validator_passes():
    first = materialize()
    second = materialize()
    assert first == second
    result = validate()
    assert result["validation_status"] == "PASS_KET_DATA_S10_A1FS_CURRENT_VS_KET_REFERENCE_COVERAGE_MATRIX"
    assert result["error_count"] == 0
    assert result["coverage_row_count"] == 7
