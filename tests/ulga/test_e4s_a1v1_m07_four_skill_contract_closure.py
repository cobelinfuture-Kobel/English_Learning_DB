from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m07_four_skill_contract_closure as builder
from ulga.query import e4s_a1v1_four_skill_contract_consumer as consumer
from ulga.validators import validate_e4s_a1v1_m07_four_skill_contract_closure as validator


@pytest.fixture(scope="module")
def artifact() -> dict:
    return builder.build_artifact()


@pytest.fixture(scope="module")
def report(artifact: dict) -> dict:
    return builder.build_report(artifact)


def test_exact_four_skill_closure_counts(artifact: dict) -> None:
    summary = artifact["closure_summary"]
    assert summary["shared_item_count"] == 384
    assert summary["learning_unit_count"] == 24
    assert summary["canonical_egp_row_count"] == 109
    assert summary["items_per_unit"] == 16
    assert summary["skill_item_counts"] == {
        "reading": 96,
        "writing": 96,
        "listening": 96,
        "speaking": 96,
    }
    assert summary["skill_practice_counts"] == {
        "reading": 72,
        "writing": 72,
        "listening": 72,
        "speaking": 72,
    }
    assert summary["skill_assessment_counts"] == {
        "reading": 24,
        "writing": 24,
        "listening": 24,
        "speaking": 24,
    }


def test_each_unit_has_balanced_four_skill_matrix(artifact: dict) -> None:
    assert len(artifact["by_grammar_unit_id"]) == 24
    for row in artifact["by_grammar_unit_id"]:
        assert row["shared_item_count"] == 16
        assert row["skill_item_counts"] == {
            skill: 4 for skill in builder.SKILLS
        }
        assert row["skill_practice_counts"] == {
            skill: 3 for skill in builder.SKILLS
        }
        assert row["skill_assessment_counts"] == {
            skill: 1 for skill in builder.SKILLS
        }


def test_each_canonical_row_has_all_four_skills(artifact: dict) -> None:
    rows = artifact["by_canonical_egp_row_id"]
    assert len(rows) == 109
    for row in rows:
        counts = row["skill_item_counts"]
        assert set(counts) == set(builder.SKILLS)
        assert all(counts[skill] > 0 for skill in builder.SKILLS)
        assert len(set(counts.values())) == 1


def test_reading_writing_listening_speaking_states_are_explicit(artifact: dict) -> None:
    states = artifact["skill_states"]
    assert states["reading"]["reviewed_item_count"] == 81
    assert states["reading"]["pending_decision_count"] == 0
    assert states["writing"]["content_state"] == "TEXT_MODE_CONTRACT_READY"
    assert states["listening"]["rendered_audio_asset_count"] == 96
    assert states["speaking"]["capture_review_engine_state"] == "COMPLETE"


def test_speaking_audio_is_operator_deferred_not_a_failure(artifact: dict) -> None:
    speaking = artifact["skill_states"]["speaking"]
    gate = artifact["system_gate"]
    assert speaking["real_audio_evidence_state"] == "DEFERRED_BY_OPERATOR"
    assert speaking["real_audio_evidence_blocks_m07"] is False
    assert speaking["captured_audio_count"] == 0
    assert gate["speaking_real_audio_evidence_required_for_m07"] is False
    assert gate["m08_progression_allowed"] is True
    assert artifact["stop_reason"] == "NONE"


def test_no_false_evidence_or_mastery_claims(artifact: dict) -> None:
    assert all(
        state["actual_learner_evidence_count"] == 0
        for state in artifact["skill_states"].values()
    )
    boundaries = artifact["claim_boundaries"]
    assert boundaries["actual_learner_evidence_complete"] is False
    assert boundaries["learner_mastery_claimed"] is False
    assert boundaries["retention_confirmed"] is False
    assert boundaries["persistent_learner_state_writes"] == 0
    assert boundaries["canonical_authority_writes"] == 0


def test_artifact_and_report_are_metadata_only(artifact: dict, report: dict) -> None:
    encoded = json.dumps([artifact, report], ensure_ascii=False).casefold()
    for forbidden in (
        '"prompt"',
        '"prompt_text"',
        '"answer_key"',
        '"answer_contract"',
        '"accepted_texts"',
        '"transcript_text"',
        '"manual_transcript"',
        '"source_payload"',
        '"operator_notes"',
    ):
        assert forbidden not in encoded
    assert ":\\" not in encoded


def test_build_is_deterministic(artifact: dict) -> None:
    rebuilt = builder.build_artifact()
    assert builder.sha256_value(rebuilt) == builder.sha256_value(artifact)
    assert rebuilt == artifact


def test_independent_validator_passes(artifact: dict, report: dict) -> None:
    result = validator.validate(artifact, report, rebuild=False)
    assert result["validation_status"] == builder.PASS_STATUS, result["errors"]
    assert result["error_count"] == 0
    assert result["skills_closed"] == 4
    assert result["m08_progression_allowed"] is True


@pytest.mark.parametrize(
    ("mutator", "expected_error"),
    [
        (
            lambda value: value["closure_summary"].__setitem__(
                "shared_item_count", 383
            ),
            "summary_shared_item_count",
        ),
        (
            lambda value: value["skill_states"]["speaking"].__setitem__(
                "real_audio_evidence_state", "REQUIRED"
            ),
            "speaking_audio_not_operator_deferred",
        ),
        (
            lambda value: value["system_gate"].__setitem__(
                "learner_mastery_claimed", True
            ),
            "system_gate_mismatch",
        ),
    ],
)
def test_tampering_fails_closed(
    artifact: dict,
    report: dict,
    mutator,
    expected_error: str,
) -> None:
    tampered = copy.deepcopy(artifact)
    mutator(tampered)
    result = validator.validate(
        tampered,
        builder.build_report(tampered),
        rebuild=False,
    )
    assert result["validation_status"] == "FAIL"
    assert any(expected_error in error for error in result["errors"])


def test_row_skill_removal_fails_closed(artifact: dict) -> None:
    tampered = copy.deepcopy(artifact)
    tampered["by_canonical_egp_row_id"][0]["skill_item_counts"].pop("speaking")
    result = validator.validate(
        tampered,
        builder.build_report(tampered),
        rebuild=False,
    )
    assert result["validation_status"] == "FAIL"
    assert any("row_skill_names" in error for error in result["errors"])


def test_report_hash_tampering_fails_closed(artifact: dict, report: dict) -> None:
    tampered = copy.deepcopy(report)
    tampered["closure_artifact_sha256"] = "0" * 64
    result = validator.validate(artifact, tampered, rebuild=False)
    assert result["validation_status"] == "FAIL"
    assert "m07_report_not_reproducible" in result["errors"]


def test_query_surfaces(artifact: dict) -> None:
    summary = consumer.query(artifact, "summary")
    assert summary["closure_summary"]["shared_item_count"] == 384

    skill = consumer.query(artifact, "skill", "writing")
    assert skill["state"]["contract_item_count"] == 96

    first_unit = artifact["by_grammar_unit_id"][0]
    unit = consumer.query(
        artifact,
        "unit",
        first_unit["grammar_unit_id"],
    )
    assert unit["grammar_unit"]["shared_item_count"] == 16

    first_row = artifact["by_canonical_egp_row_id"][0]
    row = consumer.query(
        artifact,
        "row",
        first_row["canonical_egp_row_id"],
    )
    assert set(row["canonical_egp_row"]["skill_item_counts"]) == set(
        builder.SKILLS
    )

    first_stage = first_unit["internal_stage"]
    stage = consumer.query(artifact, "stage", first_stage)
    assert stage["grammar_unit_count"] > 0

    gate = consumer.query(artifact, "gate")
    assert gate["system_gate"]["m08_progression_allowed"] is True


@pytest.mark.parametrize(
    ("command", "value"),
    [
        ("skill", "unknown"),
        ("unit", "UNKNOWN_UNIT"),
        ("row", "UNKNOWN_ROW"),
        ("stage", "UNKNOWN_STAGE"),
    ],
)
def test_unknown_queries_fail_closed(
    artifact: dict,
    command: str,
    value: str,
) -> None:
    with pytest.raises(consumer.FourSkillQueryError):
        consumer.query(artifact, command, value)


def test_direct_cli_build_validate_and_query(tmp_path: Path) -> None:
    artifact_path = tmp_path / "closure.json"
    report_path = tmp_path / "report.json"
    validation_path = tmp_path / "validation.json"

    build = subprocess.run(
        [
            sys.executable,
            str(Path(builder.__file__).resolve()),
            "--output",
            str(artifact_path),
            "--report",
            str(report_path),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr
    assert artifact_path.exists()
    assert report_path.exists()

    validate = subprocess.run(
        [
            sys.executable,
            str(Path(validator.__file__).resolve()),
            "--artifact",
            str(artifact_path),
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
            "--artifact",
            str(artifact_path),
            "summary",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert query.returncode == 0, query.stderr
    assert json.loads(query.stdout)["closure_summary"]["shared_item_count"] == 384
