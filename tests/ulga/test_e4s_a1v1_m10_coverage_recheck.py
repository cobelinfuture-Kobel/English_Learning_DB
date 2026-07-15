from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m10_coverage_recheck as builder
from ulga.query import e4s_a1v1_coverage_recheck_consumer as consumer
from ulga.validators import validate_e4s_a1v1_m10_coverage_recheck as validator


@pytest.fixture(scope="module")
def report() -> dict:
    return builder.build_report()


def test_structural_coverage_is_109_of_109(report: dict) -> None:
    summary = report["coverage_summary"]
    assert summary["canonical_grammar_unit_count"] == 24
    assert summary["canonical_egp_row_count"] == 109
    assert summary["covered_row_count"] == 109
    assert summary["draft_only_row_count"] == 0
    assert summary["missing_row_count"] == 0
    assert summary["structural_coverage_percent"] == 100.0


def test_every_row_has_all_required_layers(report: dict) -> None:
    assert len(report["rows"]) == 109
    for row in report["rows"]:
        assert row["classification"] == "COVERED"
        assert set(row["coverage_layers"]) == set(builder.COVERAGE_LAYERS)
        assert all(row["coverage_layers"].values())
        assert set(row["four_skill_item_counts"]) == set(builder.SKILLS)
        assert all(value > 0 for value in row["four_skill_item_counts"].values())
        assert row["text_runtime_item_counts"]["reading"] > 0
        assert row["text_runtime_item_counts"]["writing"] > 0


def test_classification_lists_are_exact(report: dict) -> None:
    lists = report["classification_lists"]
    assert len(lists["covered_row_ids"]) == 109
    assert lists["covered_row_ids"] == sorted(lists["covered_row_ids"])
    assert lists["draft_only_row_ids"] == []
    assert lists["missing_row_ids"] == []
    assert len(set(lists["covered_row_ids"])) == 109


def test_structural_coverage_is_separate_from_evidence_and_mastery(report: dict) -> None:
    summary = report["coverage_summary"]
    assert summary["actual_learner_evidence_row_coverage_percent"] == 0.0
    assert summary["learner_mastery_row_coverage_percent"] == 0.0
    assert all(row["learner_evidence_state"] == "NOT_COLLECTED" for row in report["rows"])
    assert all(row["learner_mastery_state"] == "NOT_CLAIMED" for row in report["rows"])


def test_speaking_audio_deferral_does_not_reduce_structural_coverage(report: dict) -> None:
    assert report["coverage_summary"]["speaking_captured_audio_count"] == 0
    assert all(
        row["speaking_real_audio_evidence_state"] == "DEFERRED_BY_OPERATOR"
        for row in report["rows"]
    )
    assert report["coverage_layer_counts"]["speaking_contract_engine"] == 109
    assert report["coverage_summary"]["covered_row_count"] == 109


def test_operator_review_backlog_is_24_units(report: dict) -> None:
    summary = report["coverage_summary"]
    backlog = report["backlog"]
    assert summary["operator_reviewed_candidate_unit_count"] == 0
    assert summary["operator_review_pending_candidate_unit_count"] == 24
    assert len(backlog["operator_content_review_pending_unit_ids"]) == 24
    assert len(set(backlog["operator_content_review_pending_unit_ids"])) == 24


def test_evidence_backlogs_cover_all_109_rows(report: dict) -> None:
    all_rows = report["classification_lists"]["covered_row_ids"]
    backlog = report["backlog"]
    assert backlog["actual_learner_evidence_pending_row_ids"] == all_rows
    assert backlog["learner_mastery_unclaimed_row_ids"] == all_rows
    assert backlog["speaking_real_audio_deferred_row_ids"] == all_rows


def test_reading_row_audit_is_not_misclassified_as_missing(report: dict) -> None:
    audit = report["backlog"]["source_grounded_reading_row_audit"]
    assert audit["status"] == "NOT_AUDITABLE_FROM_COMMITTED_METADATA"
    assert audit["structural_coverage_impact"] == "NONE"
    assert report["coverage_summary"]["missing_row_count"] == 0


def test_report_is_metadata_only(report: dict) -> None:
    encoded = json.dumps(report, ensure_ascii=False).casefold()
    for forbidden in (
        '"prompt"',
        '"answer_key"',
        '"answer_contract"',
        '"accepted_texts"',
        '"model_text"',
        '"transcript_text"',
        '"manual_transcript"',
        '"source_payload"',
        '"learner_response"',
    ):
        assert forbidden not in encoded
    assert ":\\" not in encoded
    boundaries = report["claim_boundaries"]
    assert boundaries["new_design_docs_created"] is False
    assert boundaries["canonical_graph_written"] is False
    assert boundaries["a2_a2plus_in_scope"] is False
    assert boundaries["recording_files_processed"] is False


def test_build_is_deterministic(report: dict) -> None:
    rebuilt = builder.build_report()
    assert rebuilt == report
    assert builder.sha256_value(rebuilt) == builder.sha256_value(report)


def test_independent_validator_passes(report: dict) -> None:
    result = validator.validate(report, rebuild=False)
    assert result["validation_status"] == builder.PASS_STATUS, result["errors"]
    assert result["error_count"] == 0
    assert result["covered_row_count"] == 109
    assert result["draft_only_row_count"] == 0
    assert result["missing_row_count"] == 0


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        ("classification", "covered_row_has_failed_layer"),
        ("summary", "summary_count_drift:covered_row_count"),
        ("mastery", "false_mastery_state"),
        ("backlog", "evidence_backlog_drift"),
        ("boundary", "claim_boundaries_drift"),
    ],
)
def test_tampering_fails_closed(report: dict, mutation: str, expected: str) -> None:
    value = copy.deepcopy(report)
    if mutation == "classification":
        value["rows"][0]["coverage_layers"]["rule_validator"] = False
    elif mutation == "summary":
        value["coverage_summary"]["covered_row_count"] = 108
    elif mutation == "mastery":
        value["rows"][0]["learner_mastery_state"] = "MASTERED"
    elif mutation == "backlog":
        value["backlog"]["learner_mastery_unclaimed_row_ids"].pop()
    elif mutation == "boundary":
        value["claim_boundaries"]["a2_a2plus_in_scope"] = True
    result = validator.validate(value, rebuild=False)
    assert result["validation_status"] == "FAIL"
    assert any(expected in error for error in result["errors"])


def test_query_surfaces(report: dict) -> None:
    summary = consumer.query(report, "summary")
    assert summary["coverage_summary"]["covered_row_count"] == 109
    backlog = consumer.query(report, "backlog")
    assert len(backlog["backlog"]["operator_content_review_pending_unit_ids"]) == 24

    row = report["rows"][0]
    assert consumer.query(
        report, "row", row["canonical_egp_row_id"]
    )["match_count"] == 1
    assert consumer.query(
        report, "unit", row["grammar_unit_ids"][0]
    )["match_count"] > 0
    assert consumer.query(report, "classification", "COVERED")["match_count"] == 109
    assert consumer.query(
        report, "stage", row["internal_stages"][0]
    )["match_count"] > 0
    assert consumer.query(
        report, "layer", "private_text_runtime"
    )["match_count"] == 109


@pytest.mark.parametrize(
    ("command", "value"),
    [
        ("row", "UNKNOWN_ROW"),
        ("unit", "UNKNOWN_UNIT"),
        ("classification", "UNKNOWN"),
        ("stage", "UNKNOWN_STAGE"),
        ("layer", "UNKNOWN_LAYER"),
    ],
)
def test_unknown_queries_fail_closed(report: dict, command: str, value: str) -> None:
    with pytest.raises(consumer.CoverageQueryError):
        consumer.query(report, command, value)


def test_direct_cli_build_validate_and_query(tmp_path: Path) -> None:
    report_path = tmp_path / "coverage.json"
    validation_path = tmp_path / "validation.json"
    build = subprocess.run(
        [sys.executable, str(Path(builder.__file__).resolve()), "--output", str(report_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    assert json.loads(build.stdout)["covered"] == 109

    validate = subprocess.run(
        [
            sys.executable,
            str(Path(validator.__file__).resolve()),
            "--report",
            str(report_path),
            "--validation-report",
            str(validation_path),
            "--no-rebuild",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert validate.returncode == 0, validate.stderr
    assert json.loads(validate.stdout)["error_count"] == 0

    query = subprocess.run(
        [
            sys.executable,
            str(Path(consumer.__file__).resolve()),
            "--report",
            str(report_path),
            "summary",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert query.returncode == 0, query.stderr
    assert json.loads(query.stdout)["coverage_summary"]["covered_row_count"] == 109
