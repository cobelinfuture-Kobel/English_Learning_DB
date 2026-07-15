from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m11b_authority_exception_resolution as builder
from ulga.validators import validate_e4s_a1v1_m11b_authority_exception_resolution as validator


@pytest.fixture(scope="module")
def built() -> tuple[Path, dict]:
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m11b-test-{uuid.uuid4().hex}"
    result = builder.build_to_root(root)
    yield root, result
    shutil.rmtree(root, ignore_errors=True)


def test_policy_has_exact_four_authority_exceptions() -> None:
    policy = builder._load_policy()
    assert len(policy["resolution_records"]) == 4
    assert {row["grammar_unit_id"] for row in policy["resolution_records"]} == builder.EXPECTED_EXCEPTION_IDS
    assert policy["expected_resolution_distribution"] == {
        "RESOLVED_AUTO_PASS": 3,
        "DEFERRED_CAMBRIDGE_CEILING": 1,
        "UNRESOLVED": 0,
    }


def test_three_revisions_one_ceiling_defer(built: tuple[Path, dict]) -> None:
    _, result = built
    records = result["matrix"]["records"]
    assert {row["grammar_unit_id"] for row in records if row["resolution_status"] == "RESOLVED_AUTO_PASS"} == {
        "GRAMMAR_COORDINATION_A1",
        "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1",
        "GRAMMAR_ADVERB_PHRASES_A1",
    }
    deferred = [row for row in records if row["resolution_status"] == "DEFERRED_CAMBRIDGE_CEILING"]
    assert len(deferred) == 1
    assert deferred[0]["grammar_unit_id"] == "GRAMMAR_WILL_FUTURE_A1"


def test_revisions_change_all_and_only_private_content_fields(built: tuple[Path, dict]) -> None:
    _, result = built
    for record in result["matrix"]["records"]:
        if record["resolution_status"] != "RESOLVED_AUTO_PASS":
            continue
        assert set(record["changed_fields"]) == set(builder.REVISION_FIELDS)
        assert record["before_payload_sha256"] != record["after_payload_sha256"]
        assert record["private_learning_ready"] is True


def test_all_exception_revalidations_pass(built: tuple[Path, dict]) -> None:
    _, result = built
    for record in result["matrix"]["records"]:
        assert builder._metrics_pass(record["revalidation"]), record
        value = dict(record)
        digest = value.pop("record_sha256")
        assert digest == builder.sha256_value(value)


def test_will_payload_is_unchanged_and_not_private_ready(built: tuple[Path, dict]) -> None:
    _, result = built
    record = next(row for row in result["matrix"]["records"] if row["grammar_unit_id"] == "GRAMMAR_WILL_FUTURE_A1")
    assert record["before_payload_sha256"] == record["after_payload_sha256"]
    assert record["changed_fields"] == []
    assert record["private_learning_ready"] is False
    assert record["cambridge_stage"] == "FLYERS"


def test_private_bank_has_23_units_and_excludes_will(built: tuple[Path, dict]) -> None:
    _, result = built
    bank = result["bank"]
    ids = {row["grammar_unit_id"] for row in bank["reviewed_units"]}
    assert bank["reviewed_unit_count"] == 23
    assert len(ids) == 23
    assert "GRAMMAR_WILL_FUTURE_A1" not in ids
    assert bank["deferred_unit_count"] == 1
    assert bank["deferred_units"][0]["grammar_unit_id"] == "GRAMMAR_WILL_FUTURE_A1"
    assert bank["deferred_units"][0]["canonical_egp_mapping_preserved"] is True
    assert bank["deferred_units"][0]["a2_content_promoted"] is False


def test_three_revised_units_are_in_private_bank(built: tuple[Path, dict]) -> None:
    _, result = built
    by_id = {row["grammar_unit_id"]: row for row in result["bank"]["reviewed_units"]}
    for grammar_id in (
        "GRAMMAR_COORDINATION_A1",
        "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1",
        "GRAMMAR_ADVERB_PHRASES_A1",
    ):
        assert by_id[grammar_id]["status"] == "EVIDENCE_REVISED_PRIVATE_LEARNING_UNIT"
        assert by_id[grammar_id]["authority_resolution"] == "M11B_REVISED_AND_REVALIDATED"
        payload = by_id[grammar_id]["final_private_unit_payload"]
        assert payload["content_review_status"] == "AUTHORITY_EVIDENCE_REVISED_PRIVATE"
        assert payload["source_trace"]["canonical_authority_payload_mutated"] is False


def test_safe_report_has_zero_unresolved_and_no_false_claims(built: tuple[Path, dict]) -> None:
    _, result = built
    report = result["safe_report"]
    assert report["resolution_counts"] == {
        "RESOLVED_AUTO_PASS": 3,
        "DEFERRED_CAMBRIDGE_CEILING": 1,
        "UNRESOLVED": 0,
    }
    assert report["private_ready_unit_count"] == 23
    assert report["unresolved_exception_count"] == 0
    assert report["validation_status"] == "PASS_M11B_AUTHORITY_EXCEPTIONS_RESOLVED"
    assert report["stop_reason"] == "NONE"
    assert report["next_short_step"] == builder.NEXT_SHORT_STEP
    for key in (
        "private_candidate_content_included",
        "raw_cambridge_source_included",
        "canonical_egp_mapping_changed",
        "canonical_authority_promotion",
        "public_delivery",
        "learner_mastery_claimed",
        "a2_content_promoted",
        "manual_checkbox_approval_required",
    ):
        assert report["claim_boundaries"][key] is False


def test_safe_report_has_no_private_content(built: tuple[Path, dict]) -> None:
    _, result = built
    encoded = json.dumps(result["safe_report"], ensure_ascii=False).casefold()
    for forbidden in (
        '"final_private_unit_payload"',
        '"prompt"',
        '"answer_key"',
        '"positive_examples"',
        '"negative_examples"',
        '"raw_pdf_text"',
    ):
        assert forbidden not in encoded
    assert ":\\" not in encoded


def test_build_is_deterministic(built: tuple[Path, dict]) -> None:
    _, result = built
    matrix, bank, report = builder.build_artifacts()
    assert matrix == result["matrix"]
    assert bank == result["bank"]
    assert report == result["safe_report"]


def test_independent_validator_passes(built: tuple[Path, dict]) -> None:
    root, _ = built
    result = validator.validate(root)
    assert result["error_count"] == 0, result["errors"]
    assert result["validation_status"] == validator.PASS_STATUS
    assert result["private_ready_unit_count"] == 23
    assert result["deferred_unit_count"] == 1


def test_matrix_tampering_fails_validator(built: tuple[Path, dict]) -> None:
    root, result = built
    path = root / "authority_exception_resolution_matrix.private.json"
    original = path.read_text(encoding="utf-8")
    try:
        mutated = copy.deepcopy(result["matrix"])
        mutated["records"][0]["private_learning_ready"] = False
        builder.write_json_atomic(path, mutated)
        check = validator.validate(root)
        assert check["validation_status"] == "FAIL"
        assert check["error_count"] > 0
    finally:
        path.write_text(original, encoding="utf-8")


def test_direct_cli_build_and_validate() -> None:
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m11b-cli-{uuid.uuid4().hex}"
    try:
        build = subprocess.run(
            [sys.executable, str(Path(builder.__file__).resolve()), "--output-root", str(root)],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert build.returncode == 0, build.stderr
        payload = json.loads(build.stdout)
        assert payload["private_ready_units"] == 23
        assert payload["deferred_units"] == 1
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
    finally:
        shutil.rmtree(root, ignore_errors=True)
