from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m11_candidate_content_review as builder
from ulga.query import e4s_a1v1_candidate_unit_review_consumer as consumer
from ulga.validators import validate_e4s_a1v1_m11_candidate_content_review as validator


@pytest.fixture()
def prepared(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict]:
    monkeypatch.setattr(builder, "REPO_ROOT", tmp_path)
    root = tmp_path / ".local/e4s_a1v1/content_review/m11"
    return root, builder.prepare_review(root)


def _approve(decision: dict, *, revision: dict | None = None) -> None:
    decision["decision"] = "APPROVE_WITH_REVISION" if revision else "APPROVE_AS_IS"
    decision["reviewer_id"] = "operator-local-01"
    decision["reviewed_at"] = "2026-07-15T12:00:00+08:00"
    decision["criteria"] = {key: True for key in builder.REVIEW_REQUIREMENTS}
    decision["revision"] = revision


def _reject(decision: dict, value: str = "REJECT") -> None:
    decision["decision"] = value
    decision["reviewer_id"] = "operator-local-01"
    decision["reviewed_at"] = "2026-07-15T12:00:00+08:00"
    decision["criteria"] = {key: False for key in builder.REVIEW_REQUIREMENTS}
    decision["reason_codes"] = ["CONTENT_REQUIRES_REWORK"]


def test_zero_decision_state_is_valid(prepared: tuple[Path, dict]) -> None:
    root, result = prepared
    assert result["queue"]["review_entry_count"] == 24
    assert result["safe_report"]["decision_counts"]["PENDING"] == 24
    assert result["safe_report"]["reviewed_unit_count"] == 0
    assert result["safe_report"]["validation_status"] == builder.PENDING_STATUS
    assert result["safe_report"]["stop_reason"] == "OPERATOR_CONTENT_REVIEW_DECISIONS_REQUIRED"
    validation = validator.validate(root)
    assert validation["error_count"] == 0, validation["errors"]
    assert validation["validation_status"] == builder.PENDING_STATUS


def test_queue_covers_24_units_and_109_rows(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    entries = result["queue"]["review_entries"]
    assert len({entry["grammar_unit_id"] for entry in entries}) == 24
    assert len({row for entry in entries for row in entry["canonical_egp_row_ids"]}) == 109
    assert all(entry["automated_prechecks"]["overall_status"] == "PASS" for entry in entries)
    assert all(set(entry["review_requirements"]) == set(builder.REVIEW_REQUIREMENTS) for entry in entries)


def test_one_approve_as_is_materializes_private_unit(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    decisions = copy.deepcopy(result["decisions"])
    _approve(decisions["decisions"][0])
    bank, report = builder.build_review_artifacts(
        result["queue"], decisions, builder._source_candidate()[0], report_mode="APPLY_DECISIONS"
    )
    assert bank["reviewed_unit_count"] == 1
    assert bank["reviewed_units"][0]["status"] == "REVIEWED_PRIVATE_LEARNING_UNIT"
    assert bank["reviewed_units"][0]["private_learning_ready"] is True
    assert bank["reviewed_units"][0]["mastery_trackable"] is False
    assert bank["reviewed_units"][0]["canonical_authority_promotion"] is False
    assert report["decision_counts"]["APPROVE_AS_IS"] == 1
    assert report["decision_counts"]["PENDING"] == 23
    assert report["validation_status"] == builder.PARTIAL_STATUS


def test_valid_revision_reruns_full_candidate_validator(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    decisions = copy.deepcopy(result["decisions"])
    payload = copy.deepcopy(result["queue"]["review_entries"][0]["candidate_unit_payload"])
    payload["learning_objectives"][0] = payload["learning_objectives"][0] + " (reviewed)"
    _approve(decisions["decisions"][0], revision={"replacement_unit_payload": payload})
    bank, _ = builder.build_review_artifacts(
        result["queue"], decisions, builder._source_candidate()[0], report_mode="APPLY_DECISIONS"
    )
    assert bank["reviewed_unit_count"] == 1
    assert bank["reviewed_units"][0]["final_private_unit_payload"]["learning_objectives"][0].endswith("(reviewed)")


def test_invalid_revision_fails_existing_candidate_validator(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    decisions = copy.deepcopy(result["decisions"])
    payload = copy.deepcopy(result["queue"]["review_entries"][0]["candidate_unit_payload"])
    payload["practice_items"] = []
    _approve(decisions["decisions"][0], revision={"replacement_unit_payload": payload})
    with pytest.raises(builder.CandidateReviewError, match="revised_candidate_validation_failed"):
        builder.build_review_artifacts(
            result["queue"], decisions, builder._source_candidate()[0], report_mode="APPLY_DECISIONS"
        )


def test_reject_and_defer_are_accounted(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    decisions = copy.deepcopy(result["decisions"])
    _reject(decisions["decisions"][0], "REJECT")
    _reject(decisions["decisions"][1], "DEFER")
    bank, report = builder.build_review_artifacts(
        result["queue"], decisions, builder._source_candidate()[0], report_mode="APPLY_DECISIONS"
    )
    assert bank["reviewed_unit_count"] == 0
    assert report["decision_counts"]["REJECT"] == 1
    assert report["decision_counts"]["DEFER"] == 1
    assert report["reason_code_counts"]["CONTENT_REQUIRES_REWORK"] == 2


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("queue_hash", "decision_registry_queue_hash_drift"),
        ("candidate_hash", "candidate_hash_drift"),
        ("duplicate", "duplicate_decision"),
        ("unknown", "unknown_decision"),
        ("missing", "missing_decisions"),
        ("reviewer", "reviewer_missing"),
        ("timestamp", "review_timestamp_invalid"),
        ("criteria", "approved_criteria_not_all_true"),
        ("reason", "approved_has_reason_codes"),
    ],
)
def test_decision_tampering_fails_closed(
    prepared: tuple[Path, dict], mutation: str, message: str
) -> None:
    _, result = prepared
    decisions = copy.deepcopy(result["decisions"])
    target = decisions["decisions"][0]
    _approve(target)
    if mutation == "queue_hash":
        decisions["review_queue_sha256"] = "0" * 64
    elif mutation == "candidate_hash":
        target["candidate_payload_sha256"] = "0" * 64
    elif mutation == "duplicate":
        decisions["decisions"][1] = copy.deepcopy(target)
    elif mutation == "unknown":
        target["review_entry_id"] = "M11_REVIEW_00000000000000000000"
    elif mutation == "missing":
        decisions["decisions"].pop()
        decisions["decision_count"] = 24
    elif mutation == "reviewer":
        target["reviewer_id"] = None
    elif mutation == "timestamp":
        target["reviewed_at"] = "2026-07-15T12:00:00"
    elif mutation == "criteria":
        target["criteria"][builder.REVIEW_REQUIREMENTS[0]] = False
    elif mutation == "reason":
        target["reason_codes"] = ["UNRESOLVED_ISSUE"]
    with pytest.raises(builder.CandidateReviewError, match=message):
        builder.build_review_artifacts(
            result["queue"], decisions, builder._source_candidate()[0], report_mode="APPLY_DECISIONS"
        )


def test_reason_code_cannot_create_safe_report_leak(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    decisions = copy.deepcopy(result["decisions"])
    _reject(decisions["decisions"][0])
    decisions["decisions"][0]["reason_codes"] = ["ANSWER_REVIEW_NEEDED"]
    with pytest.raises(builder.CandidateReviewError, match="reason_code_safe_report_forbidden"):
        builder.build_review_artifacts(
            result["queue"], decisions, builder._source_candidate()[0], report_mode="APPLY_DECISIONS"
        )


def test_safe_report_contains_no_candidate_content(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    encoded = json.dumps(result["safe_report"], ensure_ascii=False).casefold()
    for forbidden in (
        '"candidate_unit_payload"',
        '"final_private_unit_payload"',
        '"prompt"',
        '"answer_key"',
        '"accepted_texts"',
        '"positive_examples"',
        '"negative_examples"',
        '"review_notes"',
    ):
        assert forbidden not in encoded
    assert ":\\" not in encoded


def test_zero_state_is_deterministic(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    source = builder._source_candidate()[0]
    queue = builder.build_review_queue(source)
    decisions = builder.build_decision_template(queue)
    bank, report = builder.build_review_artifacts(queue, decisions, source, report_mode="PREPARE_REVIEW")
    assert queue == result["queue"]
    assert decisions == result["decisions"]
    assert bank == result["bank"]
    assert report == result["safe_report"]


def test_safe_and_private_query_modes(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    decisions = copy.deepcopy(result["decisions"])
    _approve(decisions["decisions"][0])
    bank, report = builder.build_review_artifacts(
        result["queue"], decisions, builder._source_candidate()[0], report_mode="APPLY_DECISIONS"
    )
    grammar_id = bank["reviewed_units"][0]["grammar_unit_id"]
    safe = consumer.query(report, bank, "unit", grammar_id)
    assert "private_unit_payloads" not in safe
    private = consumer.query(report, bank, "unit", grammar_id, private=True)
    assert private["private_unit_payloads"][0]["grammar_unit_id"] == grammar_id
    assert consumer.query(report, bank, "stage", bank["reviewed_units"][0]["internal_stage"])["match_count"] > 0
    assert consumer.query(report, bank, "row", bank["reviewed_units"][0]["canonical_egp_row_ids"][0])["match_count"] > 0


def test_unknown_reviewed_unit_query_fails_closed(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    with pytest.raises(consumer.CandidateReviewQueryError):
        consumer.query(result["safe_report"], result["bank"], "unit", "UNKNOWN")


def test_direct_cli_prepare_validate_and_summary() -> None:
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m11-ci-{uuid.uuid4().hex}"
    try:
        prepare = subprocess.run(
            [sys.executable, str(Path(builder.__file__).resolve()), "prepare-review", "--output-root", str(root)],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert prepare.returncode == 0, prepare.stderr
        assert json.loads(prepare.stdout)["pending_decisions"] == 24
        validate = subprocess.run(
            [
                sys.executable,
                str(Path(validator.__file__).resolve()),
                "--output-root",
                str(root),
                "--validation-report",
                str(root / "validation.json"),
            ],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert validate.returncode == 0, validate.stderr
        assert json.loads(validate.stdout)["error_count"] == 0
        summary = subprocess.run(
            [sys.executable, str(Path(consumer.__file__).resolve()), "--output-root", str(root), "summary"],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert summary.returncode == 0, summary.stderr
        assert json.loads(summary.stdout)["decision_counts"]["PENDING"] == 24
    finally:
        shutil.rmtree(root, ignore_errors=True)
