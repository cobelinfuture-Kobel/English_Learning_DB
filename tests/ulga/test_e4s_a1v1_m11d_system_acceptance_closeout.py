from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m11d_system_acceptance_closeout as builder
from ulga.validators import validate_e4s_a1v1_m11d_system_acceptance_closeout as validator


@pytest.fixture(scope="module")
def built() -> tuple[Path, dict]:
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m11d-test-{uuid.uuid4().hex}"
    acceptance = builder.build_acceptance(root)
    yield root, acceptance
    shutil.rmtree(root, ignore_errors=True)


def test_canonical_structural_coverage_remains_24_units_109_rows(built: tuple[Path, dict]) -> None:
    _, acceptance = built
    assert acceptance["canonical_structural_coverage"] == {
        "grammar_units": 24,
        "canonical_egp_rows": 109,
        "covered_rows": 109,
        "draft_only_rows": 0,
        "missing_rows": 0,
        "structural_coverage_percent": 100.0,
        "status": "PASS_CANONICAL_A1_A1PLUS_STRUCTURAL_COVERAGE_COMPLETE",
    }


def test_authority_reviewed_child_path_is_23_units_107_rows_184_items(built: tuple[Path, dict]) -> None:
    _, acceptance = built
    assert acceptance["authority_reviewed_private_path"] == {
        "private_ready_units": 23,
        "private_ready_rows": 107,
        "selectable_items": 184,
        "reading_items": 92,
        "writing_items": 92,
        "practice_items": 138,
        "assessment_items": 46,
        "status": "PASS_CAMBRIDGE_ALIGNED_PRIVATE_CHILD_PATH_READY",
    }


def test_will_is_ceiling_deferred_not_missing(built: tuple[Path, dict]) -> None:
    _, acceptance = built
    deferred = acceptance["cambridge_ceiling_deferred"]
    assert deferred["grammar_unit_id"] == "GRAMMAR_WILL_FUTURE_A1"
    assert deferred["canonical_egp_row_count"] == 2
    assert deferred["excluded_item_count"] == 8
    assert deferred["cambridge_stage"] == "FLYERS"
    assert deferred["canonical_egp_mapping_preserved"] is True
    assert deferred["classified_as_missing"] is False
    assert acceptance["authority_reviewed_private_path"]["private_ready_rows"] + deferred["canonical_egp_row_count"] == 109


def test_runtime_acceptance_is_local_and_m08_compatible(built: tuple[Path, dict]) -> None:
    _, acceptance = built
    runtime = acceptance["runtime_acceptance"]
    assert runtime["runtime_status"] == builder.m11c.RUNTIME_STATUS
    assert runtime["runtime_validation_errors"] == 0
    assert runtime["required_health_checks"] == 13
    assert runtime["passed_health_checks"] == 13
    assert runtime["failed_health_checks"] == 0
    assert runtime["allowed_host"] == "127.0.0.1"
    assert runtime["m08_attempt_registry_compatible"] is True
    assert runtime["will_items_learner_exposed"] is False


def test_no_learner_evidence_mastery_or_retention_is_claimed(built: tuple[Path, dict]) -> None:
    _, acceptance = built
    assert acceptance["evidence_state"] == {
        "actual_learner_attempts": 0,
        "actual_learner_evidence_rows": 0,
        "learner_mastery_claimed": False,
        "retention_confirmed": False,
        "real_learner_pilot_completed": False,
        "speaking_real_audio_evidence": "DEFERRED_BY_OPERATOR",
    }
    assert acceptance["next_phase_entry_condition"] == "REAL_LEARNER_SESSION_EVIDENCE_REQUIRED"


def test_all_sixteen_acceptance_checks_are_present(built: tuple[Path, dict]) -> None:
    _, acceptance = built
    assert len(acceptance["acceptance_checks"]) == 16
    assert set(acceptance["acceptance_checks"]) == set(builder.ACCEPTANCE_CHECKS)
    assert all(value.endswith("_PASS") for value in acceptance["acceptance_checks"])


def test_closeout_status_and_next_step(built: tuple[Path, dict]) -> None:
    _, acceptance = built
    assert acceptance["acceptance_status"] == builder.PASS_STATUS
    assert acceptance["stop_reason"] == "NONE"
    assert acceptance["next_short_step"] == builder.NEXT_SHORT_STEP
    assert acceptance["next_phase_entry_condition"] == builder.NEXT_PHASE_ENTRY_CONDITION


def test_acceptance_is_metadata_only_and_has_no_private_payload(built: tuple[Path, dict]) -> None:
    _, acceptance = built
    encoded = json.dumps(acceptance, ensure_ascii=False).casefold()
    for forbidden in (
        '"prompt"',
        '"answer_key"',
        '"accepted_texts"',
        '"private_scoring_contract"',
        '"learner_response"',
        '"raw_pdf_text"',
        '"official_question_text"',
    ):
        assert forbidden not in encoded
    assert ":\\" not in encoded
    boundaries = acceptance["claim_boundaries"]
    assert boundaries["metadata_only_acceptance"] is True
    for key, value in boundaries.items():
        if key != "metadata_only_acceptance":
            assert value is False


def test_source_hash_chain_is_complete(built: tuple[Path, dict]) -> None:
    _, acceptance = built
    assert set(acceptance["source_hashes"]) == {
        "m10_coverage_recheck_sha256",
        "m11a_closeout_sha256",
        "m11b_closeout_sha256",
        "m11c_closeout_sha256",
        "m11c_runtime_manifest_sha256",
        "m11c_runtime_validation_sha256",
    }
    assert all(len(value) == 64 for value in acceptance["source_hashes"].values())


def test_independent_validator_passes(built: tuple[Path, dict]) -> None:
    root, _ = built
    result = validator.validate(root)
    assert result["validation_status"] == builder.PASS_STATUS
    assert result["error_count"] == 0, result["errors"]
    assert result["canonical_egp_row_count"] == 109
    assert result["private_ready_row_count"] == 107
    assert result["deferred_row_count"] == 2
    assert result["actual_learner_attempt_count"] == 0


def test_acceptance_tampering_fails_validator(built: tuple[Path, dict]) -> None:
    root, acceptance = built
    path = root / "system_acceptance.json"
    original = path.read_text(encoding="utf-8")
    try:
        mutated = copy.deepcopy(acceptance)
        mutated["cambridge_ceiling_deferred"]["classified_as_missing"] = True
        builder.write_json_atomic(path, mutated)
        result = validator.validate(root)
        assert result["validation_status"] == "FAIL"
        assert result["error_count"] > 0
    finally:
        path.write_text(original, encoding="utf-8")


def test_build_is_deterministic(built: tuple[Path, dict]) -> None:
    _, acceptance = built
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m11d-deterministic-{uuid.uuid4().hex}"
    try:
        rebuilt = builder.build_acceptance(root)
        assert rebuilt == acceptance
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_output_outside_local_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(builder.SystemAcceptanceError, match="output_root_outside_local"):
        builder.build_acceptance(tmp_path / "m11d")


def test_direct_cli_build_and_validate() -> None:
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m11d-cli-{uuid.uuid4().hex}"
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
        assert payload["acceptance_status"] == builder.PASS_STATUS
        assert payload["canonical_rows"] == 109
        assert payload["private_ready_rows"] == 107
        assert payload["actual_learner_attempts"] == 0
        validate = subprocess.run(
            [
                sys.executable,
                str(Path(validator.__file__).resolve()),
                "--output-root",
                str(root),
                "--validation-report",
                str(root / "system_acceptance_validation.json"),
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
