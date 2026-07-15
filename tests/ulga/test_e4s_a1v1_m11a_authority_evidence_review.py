from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m11a_authority_evidence_review as builder
from ulga.query import e4s_a1v1_m11a_authority_evidence_consumer as consumer
from ulga.validators import validate_e4s_a1v1_m11a_authority_evidence_review as validator


@pytest.fixture(scope="module")
def built() -> tuple[Path, dict]:
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m11a-test-{uuid.uuid4().hex}"
    result = builder.build_to_root(root)
    yield root, result
    shutil.rmtree(root, ignore_errors=True)


def test_source_manifest_is_four_hash_pinned_pdfs() -> None:
    manifest, policy = builder.load_sources()
    assert manifest["source_package_status"] == "PASS_WITH_VERSION_WARNINGS"
    assert len(manifest["sources"]) == 4
    assert len({row["drive_file_id"] for row in manifest["sources"]}) == 4
    assert all(len(row["sha256"]) == 64 for row in manifest["sources"])
    assert all(row["learner_facing_copy_allowed"] is False for row in manifest["sources"])
    assert len(policy["unit_alignment"]) == 24


def test_exact_24_units_109_rows_and_expected_distribution(built: tuple[Path, dict]) -> None:
    _, result = built
    matrix = result["matrix"]
    report = result["safe_report"]
    assert matrix["unit_count"] == 24
    assert matrix["canonical_egp_row_count"] == 109
    assert report["decision_counts"] == {
        "AUTO_PASS": 20,
        "REVISION_REQUIRED": 3,
        "AUTHORITY_CONFLICT": 1,
        "SOURCE_EVIDENCE_MISSING": 0,
    }
    assert report["stop_reason"] == "NONE"
    assert report["next_short_step"] == builder.NEXT_SHORT_STEP


def test_manual_checkbox_approval_is_not_part_of_m11a(built: tuple[Path, dict]) -> None:
    _, result = built
    encoded = json.dumps(result["matrix"], ensure_ascii=False).casefold()
    assert '"reviewer_id"' not in encoded
    assert '"reviewed_at"' not in encoded
    assert '"decision": "pending"' not in encoded
    assert result["safe_report"]["claim_boundaries"]["manual_checkbox_approval_required"] is False


def test_will_future_is_a_cambridge_flyers_conflict(built: tuple[Path, dict]) -> None:
    _, result = built
    rows = {row["grammar_unit_id"]: row for row in result["matrix"]["entries"]}
    target = rows["GRAMMAR_WILL_FUTURE_A1"]
    assert target["cambridge_stage"] == "FLYERS"
    assert target["automated_decision"] == "AUTHORITY_CONFLICT"
    assert "CAMBRIDGE_FLYERS_A2_STRUCTURE_CONFLICT" in target["conflict_codes"]
    assert target["criteria"]["a1_a1plus_level_appropriate"]["status"] == "FAIL"
    assert target["criteria"]["no_a2_expansion"]["status"] == "FAIL"


def test_broad_units_are_revision_required(built: tuple[Path, dict]) -> None:
    _, result = built
    revision_ids = {
        row["grammar_unit_id"]
        for row in result["matrix"]["entries"]
        if row["automated_decision"] == "REVISION_REQUIRED"
    }
    assert revision_ids == {
        "GRAMMAR_COORDINATION_A1",
        "GRAMMAR_VERB_COMPLEMENT_PATTERNS_A1",
        "GRAMMAR_ADVERB_PHRASES_A1",
    }


def test_auto_pass_units_materialize_private_bank_only(built: tuple[Path, dict]) -> None:
    _, result = built
    bank = result["bank"]
    matrix = result["matrix"]
    auto_pass_ids = {
        row["grammar_unit_id"]
        for row in matrix["entries"]
        if row["automated_decision"] == "AUTO_PASS"
    }
    bank_ids = {row["grammar_unit_id"] for row in bank["reviewed_units"]}
    assert bank["reviewed_unit_count"] == 20
    assert bank_ids == auto_pass_ids
    assert "GRAMMAR_WILL_FUTURE_A1" not in bank_ids
    assert all(row["canonical_authority_promotion"] is False for row in bank["reviewed_units"])


def test_every_unit_has_twelve_traceable_criteria(built: tuple[Path, dict]) -> None:
    _, result = built
    for row in result["matrix"]["entries"]:
        assert set(row["criteria"]) == set(builder.CRITERIA)
        for criterion in row["criteria"].values():
            assert criterion["status"] in {"PASS", "WARNING", "FAIL"}
            assert criterion["evidence_refs"]
        record = dict(row)
        digest = record.pop("evidence_record_sha256")
        assert digest == builder.sha256_value(record)


def test_safe_report_has_no_candidate_or_cambridge_payload(built: tuple[Path, dict]) -> None:
    _, result = built
    encoded = json.dumps(result["safe_report"], ensure_ascii=False).casefold()
    for forbidden in (
        '"candidate_unit_payload"',
        '"final_private_unit_payload"',
        '"prompt"',
        '"answer_key"',
        '"positive_examples"',
        '"negative_examples"',
        '"raw_pdf_text"',
        '"official_question_text"',
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
    assert result["validation_status"] == "PASS_WITH_AUTHORITY_EXCEPTIONS"
    assert result["manual_checkbox_approval_required"] is False


def test_matrix_tampering_fails_validator(built: tuple[Path, dict]) -> None:
    root, result = built
    path = root / "authority_evidence_matrix.private.json"
    original = path.read_text(encoding="utf-8")
    try:
        mutated = copy.deepcopy(result["matrix"])
        mutated["entries"][0]["automated_decision"] = "AUTHORITY_CONFLICT"
        builder.write_json_atomic(path, mutated)
        check = validator.validate(root)
        assert check["validation_status"] == "FAIL"
        assert check["error_count"] > 0
    finally:
        path.write_text(original, encoding="utf-8")


def test_source_byte_verification_and_hash_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest, _ = builder.load_sources()
    fake = copy.deepcopy(manifest)
    for index, source in enumerate(fake["sources"]):
        payload = f"fixture-{index}".encode("utf-8")
        path = tmp_path / source["local_filename"]
        path.write_bytes(payload)
        source["byte_size"] = len(payload)
        source["sha256"] = __import__("hashlib").sha256(payload).hexdigest()
    fake_manifest = tmp_path / "manifest.json"
    fake_manifest.write_text(json.dumps(fake), encoding="utf-8")
    monkeypatch.setattr(builder, "MANIFEST_PATH", fake_manifest)
    loaded, _ = builder.load_sources()
    assert builder.verify_source_bytes(loaded, tmp_path) == "SOURCE_BYTES_VERIFIED"
    first = tmp_path / loaded["sources"][0]["local_filename"]
    first.write_bytes(b"tampered")
    with pytest.raises(builder.AuthorityEvidenceError, match="cambridge_source_(size|hash)_drift"):
        builder.verify_source_bytes(loaded, tmp_path)


def test_safe_and_private_queries(built: tuple[Path, dict]) -> None:
    _, result = built
    summary = consumer.query(result["matrix"], result["bank"], result["safe_report"], "summary")
    assert summary["decision_counts"]["AUTO_PASS"] == 20
    conflict = consumer.query(
        result["matrix"], result["bank"], result["safe_report"], "decision", "AUTHORITY_CONFLICT"
    )
    assert conflict["match_count"] == 1
    assert conflict["units"][0]["grammar_unit_id"] == "GRAMMAR_WILL_FUTURE_A1"
    private = consumer.query(
        result["matrix"], result["bank"], result["safe_report"], "unit", "GRAMMAR_BE_VERB_BASIC", private=True
    )
    assert len(private["private_unit_payloads"]) == 1
    unresolved_private = consumer.query(
        result["matrix"], result["bank"], result["safe_report"], "unit", "GRAMMAR_WILL_FUTURE_A1", private=True
    )
    assert unresolved_private["private_unit_payloads"] == []


def test_unknown_query_fails_closed(built: tuple[Path, dict]) -> None:
    _, result = built
    with pytest.raises(consumer.AuthorityEvidenceQueryError):
        consumer.query(result["matrix"], result["bank"], result["safe_report"], "unit", "UNKNOWN")


def test_m11_source_candidate_non_regression() -> None:
    candidate, validation = builder.m11._source_candidate()
    assert validation["validation_status"] == "PASS"
    assert candidate["coverage_summary"]["canonical_unit_count"] == 24
    assert candidate["coverage_summary"]["canonical_unique_egp_row_count"] == 109


def test_direct_cli_build_validate_and_summary() -> None:
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m11a-cli-{uuid.uuid4().hex}"
    try:
        build = subprocess.run(
            [sys.executable, str(Path(builder.__file__).resolve()), "--output-root", str(root)],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert build.returncode == 0, build.stderr
        assert json.loads(build.stdout)["decision_counts"]["AUTO_PASS"] == 20
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
            [
                sys.executable,
                str(Path(consumer.__file__).resolve()),
                "--output-root",
                str(root),
                "summary",
            ],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert summary.returncode == 0, summary.stderr
        assert json.loads(summary.stdout)["stop_reason"] == "NONE"
    finally:
        shutil.rmtree(root, ignore_errors=True)
