from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m12_real_learner_pilot_evidence_capture as m12
from ulga.builders import build_e4s_a1v1_m12c_real_learner_pilot_evidence_qa as m12c
from ulga.builders import build_e4s_a1v1_m12d_representative_pilot_expansion as m12d
from ulga.builders import build_e4s_a1v1_m12e_representative_pilot_evidence_qa as builder
from ulga.validators import validate_e4s_a1v1_m12e_representative_pilot_evidence_qa as validator


def _response_for(item: dict) -> object:
    contract = item["private_scoring_contract"]
    mode = contract["scoring_mode"]
    if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"}:
        return contract["accepted_texts"][0]
    if mode == "EXACT_SEQUENCE":
        return contract["accepted_sequence"]
    return "Representative QA fixture response."


def _build_chain(base: Path) -> tuple[Path, Path, Path]:
    input_root = base / "m12"
    qa_root = base / "m12c"
    representative_root = base / "m12d"
    prepared = m12.prepare_capture(input_root)
    manifest = prepared["manifest"]
    bank = json.loads((input_root / "runtime/source_m08/text_mode_session_bank.private.json").read_text(encoding="utf-8"))
    allowed = set(manifest["selection"]["selectable_item_ids"])
    prior_item = next(
        row for row in bank["items"]
        if row["item_id"] in allowed
        and row["private_scoring_contract"]["scoring_mode"] != "FEATURE_RUBRIC"
    )
    prior = m12.m08.empty_attempt_registry(bank)
    prior["session_id"] = "m12e-prior-fixture"
    prior["learner_ref"] = "fixture-learner"
    prior["attempts"] = [{
        "item_id": prior_item["item_id"],
        "attempt_sequence": 1,
        "response": _response_for(prior_item),
        "submitted_at": "2026-07-16T00:01:00.000Z",
        "operator_review": m12.m08._empty_review(),
    }]
    prior_path = base / "prior.private.json"
    prior_path.write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    m12.import_evidence(input_root, prior_path, evidence_origin="TEST_FIXTURE")
    m12c.build_qa(input_root, qa_root, expected_origin="TEST_FIXTURE")

    m12d_prepared = m12d.prepare_batch(
        input_root,
        qa_root,
        representative_root,
        expected_origin="TEST_FIXTURE",
    )
    item_ids = list(m12d_prepared["manifest"]["batch_selection"]["item_ids"])
    by_id = {row["item_id"]: row for row in bank["items"]}
    batch = m12.m08.empty_attempt_registry(bank)
    batch["session_id"] = "m12e-representative-fixture"
    batch["learner_ref"] = prior["learner_ref"]
    batch["attempts"] = [
        {
            "item_id": item_id,
            "attempt_sequence": index,
            "response": _response_for(by_id[item_id]),
            "submitted_at": f"2026-07-16T00:{10 + index:02d}:00.000Z",
            "operator_review": m12.m08._empty_review(),
        }
        for index, item_id in enumerate(item_ids, start=1)
    ]
    batch_path = base / "batch.private.json"
    batch_path.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    m12d.import_batch(
        input_root,
        qa_root,
        representative_root,
        batch_path,
        expected_origin="TEST_FIXTURE",
    )
    return input_root, qa_root, representative_root


@pytest.fixture(scope="module")
def built() -> dict:
    root = builder.REPO_ROOT / ".local" / f"m12e-test-{uuid.uuid4().hex}"
    input_root, qa_root, representative_root = _build_chain(root)
    output_root = root / "m12e"
    report = builder.build_qa(
        input_root,
        qa_root,
        representative_root,
        output_root,
        expected_origin="TEST_FIXTURE",
    )
    yield {
        "root": root,
        "input_root": input_root,
        "qa_root": qa_root,
        "representative_root": representative_root,
        "output_root": output_root,
        "report": report,
    }
    shutil.rmtree(root, ignore_errors=True)


def test_representative_batch_and_coverage_delta(built: dict) -> None:
    report = built["report"]
    assert report["representative_batch"]["batch_attempt_count"] == 8
    assert report["representative_batch"]["complete"] is True
    assert report["representative_batch"]["skill_counts"] == {"reading": 4, "writing": 4}
    assert report["representative_batch"]["role_counts"] == {"practice": 4, "assessment": 4}
    assert report["evidence_summary"]["attempt_count"] == 9
    assert report["coverage_progress"]["delta"]["items"] == 8
    assert report["coverage_progress"]["representative_pilot_completed"] is True


def test_coverage_partition_is_consistent(built: dict) -> None:
    coverage = built["report"]["coverage_progress"]
    assert coverage["current"]["items"] + coverage["remaining"]["items"] == 184
    assert coverage["current"]["units"] + coverage["remaining"]["units"] == 23
    assert coverage["current"]["rows"] + coverage["remaining"]["rows"] == 107
    assert coverage["current"]["items"] == 9
    assert coverage["coverage_complete"] is False


def test_expansion_queue_is_unique_unattempted_and_will_free(built: dict) -> None:
    report = built["report"]
    ledger = json.loads((built["representative_root"] / "cumulative_progress_ledger.private.json").read_text(encoding="utf-8"))
    attempted = {row["item_id"] for row in ledger["entries"]}
    queue = report["coverage_expansion_queue"]
    ids = [row["item_id"] for row in queue["items"]]
    assert queue["candidate_count"] == 8
    assert len(ids) == len(set(ids)) == 8
    assert not set(ids) & attempted
    assert not any(row["grammar_unit_id"] == builder.DEFERRED_GRAMMAR_ID for row in queue["items"])
    assert {row["reason_code"] for row in queue["items"]}.issubset({
        "FAILED_UNIT_REMEDIATION",
        "UNATTEMPTED_UNIT_COVERAGE",
        "SKILL_ROLE_BALANCE",
    })


def test_quality_gate_and_next_step_are_consistent(built: dict) -> None:
    report = built["report"]
    summary = report["evidence_summary"]
    quality = report["quality_gate"]
    pending = summary["pending_human_review_count"]
    rejected = summary["outcome_counts"]["HUMAN_REJECT"]
    assert quality["human_review_required"] is (pending > 0)
    assert quality["remediation_required"] is (summary["auto_fail_count"] + rejected > 0)
    if pending:
        assert report["stop_reason"] == "HUMAN_REVIEW_DECISIONS_REQUIRED"
        assert report["next_short_step"] == "E4S-A1V1-M12E1_HumanReviewDecisionMaterialization"
    else:
        assert report["stop_reason"] == "NONE"


def test_safe_report_contains_no_private_content(built: dict) -> None:
    report = built["report"]
    encoded = json.dumps(report, ensure_ascii=False).casefold()
    for forbidden in (
        '"response"', '"prompt"', '"answer_key"', '"accepted_texts"',
        '"private_scoring_contract"', '"learner_ref"', '"session_id"',
    ):
        assert forbidden not in encoded
    for key in (
        "private_responses_included", "learner_identity_included",
        "test_fixture_counted_as_real_evidence", "canonical_authority_write",
        "canonical_egp_mapping_changed", "public_delivery", "production_runtime_enabled",
        "a2_content_promoted", "audio_or_recording_processed", "learner_mastery_claimed",
        "retention_confirmed",
    ):
        assert report["claim_boundaries"][key] is False


def test_independent_validator_passes(built: dict) -> None:
    result = validator.validate(
        built["input_root"],
        built["qa_root"],
        built["representative_root"],
        built["output_root"],
        expected_origin="TEST_FIXTURE",
    )
    assert result["error_count"] == 0, result["errors"]
    assert result["validation_status"] == builder.TEST_STATUS
    assert result["attempt_count"] == 9
    assert result["iteration_candidate_count"] == 8
    assert result["representative_pilot_completed"] is True


def test_legacy_exact_complete_m12d_report_is_accepted(built: dict) -> None:
    legacy_root = built["root"] / "legacy-exact-complete"
    shutil.copytree(built["representative_root"], legacy_root)
    report_path = legacy_root / "representative_pilot_expansion_safe_report.json"
    legacy_report = json.loads(report_path.read_text(encoding="utf-8"))
    legacy_report.pop("remaining_batch_attempt_count", None)
    report_path.write_text(json.dumps(legacy_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    output_root = built["root"] / "legacy-exact-complete-output"
    report = builder.build_qa(
        built["input_root"],
        built["qa_root"],
        legacy_root,
        output_root,
        expected_origin="TEST_FIXTURE",
    )
    assert report["evidence_summary"]["attempt_count"] == 9
    assert report["representative_batch"]["complete"] is True
    result = validator.validate(
        built["input_root"],
        built["qa_root"],
        legacy_root,
        output_root,
        expected_origin="TEST_FIXTURE",
    )
    assert result["error_count"] == 0, result["errors"]


def test_missing_remaining_count_does_not_hide_incomplete_report(built: dict) -> None:
    legacy_root = built["root"] / "legacy-incomplete"
    shutil.copytree(built["representative_root"], legacy_root)
    report_path = legacy_root / "representative_pilot_expansion_safe_report.json"
    legacy_report = json.loads(report_path.read_text(encoding="utf-8"))
    legacy_report.pop("remaining_batch_attempt_count", None)
    legacy_report["batch_attempt_count"] = 7
    legacy_report["cumulative_attempt_count"] = legacy_report["prior_attempt_count"] + 7
    report_path.write_text(json.dumps(legacy_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(builder.RepresentativeEvidenceQAError, match="m12d_batch_attempts"):
        builder.build_qa(
            built["input_root"],
            built["qa_root"],
            legacy_root,
            built["root"] / "legacy-incomplete-output",
            expected_origin="TEST_FIXTURE",
        )


def test_report_tampering_fails_validator(built: dict) -> None:
    path = built["output_root"] / "representative_evidence_qa_safe_report.json"
    original = path.read_text(encoding="utf-8")
    try:
        mutated = copy.deepcopy(built["report"])
        mutated["coverage_progress"]["delta"]["items"] = 7
        builder.write_json_atomic(path, mutated)
        result = validator.validate(
            built["input_root"],
            built["qa_root"],
            built["representative_root"],
            built["output_root"],
            expected_origin="TEST_FIXTURE",
        )
        assert result["validation_status"] == "FAIL"
        assert result["error_count"] > 0
    finally:
        path.write_text(original, encoding="utf-8")


def test_build_is_deterministic(built: dict) -> None:
    root = built["root"] / "deterministic"
    rebuilt = builder.build_qa(
        built["input_root"],
        built["qa_root"],
        built["representative_root"],
        root,
        expected_origin="TEST_FIXTURE",
    )
    assert rebuilt == built["report"]
    assert json.loads((root / "coverage_expansion_queue.json").read_text(encoding="utf-8")) == built["report"]["coverage_expansion_queue"]


def test_direct_cli_build_and_validate() -> None:
    root = builder.REPO_ROOT / ".local" / f"m12e-cli-{uuid.uuid4().hex}"
    try:
        input_root, qa_root, representative_root = _build_chain(root)
        output_root = root / "m12e"
        build = subprocess.run(
            [
                sys.executable,
                str(Path(builder.__file__).resolve()),
                "--input-root", str(input_root),
                "--qa-root", str(qa_root),
                "--representative-root", str(representative_root),
                "--output-root", str(output_root),
                "--expected-origin", "TEST_FIXTURE",
            ],
            cwd=builder.REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert build.returncode == 0, build.stderr
        assert json.loads(build.stdout)["attempt_count"] == 9
        validate = subprocess.run(
            [
                sys.executable,
                str(Path(validator.__file__).resolve()),
                "--input-root", str(input_root),
                "--qa-root", str(qa_root),
                "--representative-root", str(representative_root),
                "--output-root", str(output_root),
                "--expected-origin", "TEST_FIXTURE",
                "--validation-report", str(output_root / "validation.json"),
            ],
            cwd=builder.REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert validate.returncode == 0, validate.stderr
        assert json.loads(validate.stdout)["error_count"] == 0
    finally:
        shutil.rmtree(root, ignore_errors=True)
