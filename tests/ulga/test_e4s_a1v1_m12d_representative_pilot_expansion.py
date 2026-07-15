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
from ulga.builders import build_e4s_a1v1_m12d_representative_pilot_expansion as builder
from ulga.validators import validate_e4s_a1v1_m12d_representative_pilot_expansion as validator


def _response_for(item: dict) -> object:
    contract = item["private_scoring_contract"]
    mode = contract["scoring_mode"]
    if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"}:
        return contract["accepted_texts"][0]
    if mode == "EXACT_SEQUENCE":
        return contract["accepted_sequence"]
    return "This is a test fixture response."


def _build_fixture_root(base: Path) -> tuple[Path, Path]:
    input_root = base / "m12"
    qa_root = base / "m12c"
    prepared = m12.prepare_capture(input_root)
    manifest = prepared["manifest"]
    bank = json.loads((input_root / "runtime/source_m08/text_mode_session_bank.private.json").read_text(encoding="utf-8"))
    allowed = set(manifest["selection"]["selectable_item_ids"])
    item = next(
        row
        for row in bank["items"]
        if row["item_id"] in allowed
        and row["private_scoring_contract"]["scoring_mode"] != "FEATURE_RUBRIC"
    )
    registry = m12.m08.empty_attempt_registry(bank)
    registry["session_id"] = "m12d-prior-fixture"
    registry["learner_ref"] = "fixture-learner"
    registry["attempts"] = [{
        "item_id": item["item_id"],
        "attempt_sequence": 1,
        "response": _response_for(item),
        "submitted_at": "2026-07-15T13:16:05.516Z",
        "operator_review": m12.m08._empty_review(),
    }]
    registry_path = input_root / "prior_fixture_registry.private.json"
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    m12.import_evidence(input_root, registry_path, evidence_origin="TEST_FIXTURE")
    m12c.build_qa(input_root, qa_root, expected_origin="TEST_FIXTURE")
    return input_root, qa_root


def _batch_registry(input_root: Path, manifest: dict, item_ids: list[str], *, suffix: str) -> dict:
    bank = json.loads((input_root / "runtime/source_m08/text_mode_session_bank.private.json").read_text(encoding="utf-8"))
    prior = json.loads((input_root / "pilot_attempt_registry.private.json").read_text(encoding="utf-8"))
    by_id = {row["item_id"]: row for row in bank["items"]}
    registry = m12.m08.empty_attempt_registry(bank)
    registry["session_id"] = f"m12d-{suffix}"
    registry["learner_ref"] = prior["learner_ref"]
    registry["attempts"] = [
        {
            "item_id": item_id,
            "attempt_sequence": index,
            "response": _response_for(by_id[item_id]),
            "submitted_at": f"2026-07-15T13:{20 + index:02d}:05.516Z",
            "operator_review": m12.m08._empty_review(),
        }
        for index, item_id in enumerate(item_ids, start=1)
    ]
    return registry


def _write_registry(path: Path, registry: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def fixture_data() -> dict:
    root = builder.REPO_ROOT / ".local" / f"m12d-fullfix-test-{uuid.uuid4().hex}"
    input_root, qa_root = _build_fixture_root(root)
    prepare_root = root / "prepare"
    prepared = builder.prepare_batch(
        input_root,
        qa_root,
        prepare_root,
        expected_origin="TEST_FIXTURE",
    )
    item_ids = list(prepared["manifest"]["batch_selection"]["item_ids"])
    first_ids = item_ids[:4]
    remaining_ids = item_ids[4:]
    first_registry = _batch_registry(input_root, prepared["manifest"], first_ids, suffix="first-four")
    remaining_registry = _batch_registry(input_root, prepared["manifest"], remaining_ids, suffix="remaining-four")
    full_registry = _batch_registry(input_root, prepared["manifest"], item_ids, suffix="full-eight")
    first_path = _write_registry(root / "first_four.private.json", first_registry)
    remaining_path = _write_registry(root / "remaining_four.private.json", remaining_registry)
    full_path = _write_registry(root / "full_eight.private.json", full_registry)

    partial_root = root / "partial"
    partial = builder.import_batch(
        input_root,
        qa_root,
        partial_root,
        first_path,
        expected_origin="TEST_FIXTURE",
    )
    resumed = builder.prepare_batch(
        input_root,
        qa_root,
        partial_root,
        expected_origin="TEST_FIXTURE",
    )

    incremental_root = root / "incremental"
    builder.import_batch(
        input_root,
        qa_root,
        incremental_root,
        first_path,
        expected_origin="TEST_FIXTURE",
    )
    complete = builder.import_batch(
        input_root,
        qa_root,
        incremental_root,
        remaining_path,
        expected_origin="TEST_FIXTURE",
    )

    full_root = root / "full"
    full = builder.import_batch(
        input_root,
        qa_root,
        full_root,
        full_path,
        expected_origin="TEST_FIXTURE",
    )
    yield {
        "root": root,
        "input_root": input_root,
        "qa_root": qa_root,
        "prepare_root": prepare_root,
        "prepared": prepared,
        "item_ids": item_ids,
        "first_ids": first_ids,
        "remaining_ids": remaining_ids,
        "first_registry": first_registry,
        "remaining_registry": remaining_registry,
        "first_path": first_path,
        "remaining_path": remaining_path,
        "partial_root": partial_root,
        "partial": partial,
        "resumed": resumed,
        "incremental_root": incremental_root,
        "complete": complete,
        "full_root": full_root,
        "full": full,
    }
    shutil.rmtree(root, ignore_errors=True)


def test_prepare_builds_balanced_4x2_batch(fixture_data: dict) -> None:
    manifest = fixture_data["prepared"]["manifest"]
    selection = manifest["batch_selection"]
    assert selection["batch_size"] == 8
    assert selection["grammar_unit_count"] == 4
    assert selection["skill_counts"] == {"reading": 4, "writing": 4}
    assert selection["role_counts"] == {"practice": 4, "assessment": 4}
    assert manifest["attempt_registry_contract"]["completion_attempt_count"] == 8
    assert fixture_data["prepared"]["resume_state"] == {
        "task_id": builder.TASK_ID,
        "captured_item_ids": [],
        "remaining_item_ids": fixture_data["item_ids"],
        "captured_attempt_count": 0,
        "remaining_attempt_count": 8,
    }


def test_batch_preserves_all_available_m12c_priority_units(fixture_data: dict) -> None:
    qa_report = json.loads((fixture_data["qa_root"] / "real_evidence_qa_safe_report.json").read_text(encoding="utf-8"))
    priority: list[str] = []
    for row in qa_report["iteration_queue"]["items"]:
        grammar_id = row["grammar_unit_id"]
        if grammar_id not in priority:
            priority.append(grammar_id)
    chosen = fixture_data["prepared"]["manifest"]["batch_selection"]["grammar_unit_ids"]
    assert set(priority).issubset(set(chosen))
    assert len(chosen) == 4


def test_partial_four_of_eight_is_preserved_but_does_not_advance(fixture_data: dict) -> None:
    report = fixture_data["partial"]["safe_report"]
    assert report["batch_attempt_count"] == 4
    assert report["remaining_batch_attempt_count"] == 4
    assert report["cumulative_attempt_count"] == 5
    assert report["validation_status"] == builder.PARTIAL_STATUS
    assert report["stop_reason"] == "REAL_LEARNER_REPRESENTATIVE_BATCH_INCOMPLETE"
    assert report["next_short_step"] == builder.NEXT_IMPORT
    assert report["next_short_step"] != builder.NEXT_QA


def test_partial_validator_passes_without_overclaim(fixture_data: dict) -> None:
    result = validator.validate(
        "import-batch",
        fixture_data["input_root"],
        fixture_data["qa_root"],
        fixture_data["partial_root"],
        expected_origin="TEST_FIXTURE",
    )
    assert result["error_count"] == 0, result["errors"]
    assert result["validation_status"] == builder.PARTIAL_STATUS
    assert result["batch_attempt_count"] == 4
    assert result["remaining_batch_attempt_count"] == 4
    assert result["next_short_step"] == builder.NEXT_IMPORT


def test_prepare_after_partial_exposes_only_remaining_metadata(fixture_data: dict) -> None:
    resumed = fixture_data["resumed"]
    assert resumed["safe_report"]["batch_attempt_count"] == 4
    assert resumed["safe_report"]["remaining_batch_attempt_count"] == 4
    assert set(resumed["resume_state"]["captured_item_ids"]) == set(fixture_data["first_ids"])
    assert set(resumed["resume_state"]["remaining_item_ids"]) == set(fixture_data["remaining_ids"])
    html = (fixture_data["partial_root"] / "session/index.html").read_text(encoding="utf-8").casefold()
    assert "resume_state.json" in html
    assert "previously captured items are hidden" in html
    assert "e4s-a1v1-m12d-current-attempts" in html


def test_second_four_merge_to_exact_complete_eight(fixture_data: dict) -> None:
    report = fixture_data["complete"]["safe_report"]
    assert report["batch_attempt_count"] == 8
    assert report["remaining_batch_attempt_count"] == 0
    assert report["cumulative_attempt_count"] == 9
    assert report["validation_status"] == builder.TEST_STATUS
    assert report["stop_reason"] == "REAL_LEARNER_REPRESENTATIVE_BATCH_REQUIRED"
    merged_ids = [row["item_id"] for row in fixture_data["complete"]["batch_registry"]["attempts"]]
    assert merged_ids == fixture_data["item_ids"]
    assert len(merged_ids) == len(set(merged_ids)) == 8


def test_incremental_complete_validator_passes(fixture_data: dict) -> None:
    result = validator.validate(
        "import-batch",
        fixture_data["input_root"],
        fixture_data["qa_root"],
        fixture_data["incremental_root"],
        expected_origin="TEST_FIXTURE",
    )
    assert result["error_count"] == 0, result["errors"]
    assert result["validation_status"] == builder.TEST_STATUS
    assert result["batch_attempt_count"] == 8
    assert result["remaining_batch_attempt_count"] == 0
    assert result["cumulative_attempt_count"] == 9


def test_direct_full_eight_still_passes(fixture_data: dict) -> None:
    report = fixture_data["full"]["safe_report"]
    assert report["batch_attempt_count"] == 8
    assert report["remaining_batch_attempt_count"] == 0
    assert report["validation_status"] == builder.TEST_STATUS
    assert report["cumulative_attempt_count"] == 9


def test_idempotent_partial_replay_does_not_duplicate(fixture_data: dict) -> None:
    root = fixture_data["root"] / "idempotent"
    first = builder.import_batch(
        fixture_data["input_root"],
        fixture_data["qa_root"],
        root,
        fixture_data["first_path"],
        expected_origin="TEST_FIXTURE",
    )
    second = builder.import_batch(
        fixture_data["input_root"],
        fixture_data["qa_root"],
        root,
        fixture_data["first_path"],
        expected_origin="TEST_FIXTURE",
    )
    assert first["safe_report"] == second["safe_report"]
    assert len(second["batch_registry"]["attempts"]) == 4
    assert second["ledger"]["attempt_count"] == 5


def test_conflicting_replay_is_rejected(fixture_data: dict) -> None:
    root = fixture_data["root"] / "conflict"
    builder.import_batch(
        fixture_data["input_root"],
        fixture_data["qa_root"],
        root,
        fixture_data["first_path"],
        expected_origin="TEST_FIXTURE",
    )
    conflict = copy.deepcopy(fixture_data["first_registry"])
    conflict["attempts"][0]["response"] = "different replay value"
    path = _write_registry(fixture_data["root"] / "conflict.private.json", conflict)
    with pytest.raises(builder.RepresentativePilotError, match="conflicting_replay"):
        builder.import_batch(
            fixture_data["input_root"],
            fixture_data["qa_root"],
            root,
            path,
            expected_origin="TEST_FIXTURE",
        )


def test_nonbatch_item_and_learner_mismatch_are_rejected(fixture_data: dict) -> None:
    manifest = fixture_data["prepared"]["manifest"]
    prior = json.loads((fixture_data["input_root"] / "pilot_attempt_registry.private.json").read_text(encoding="utf-8"))
    query = json.loads((fixture_data["input_root"] / "pilot_progress_query_index.json").read_text(encoding="utf-8"))
    allowed = set(manifest["batch_selection"]["item_ids"])
    nonbatch = next(row["item_id"] for row in query["items"] if row["item_id"] not in allowed and not row["attempted"])
    registry = copy.deepcopy(fixture_data["first_registry"])
    registry["attempts"][0]["item_id"] = nonbatch
    with pytest.raises(builder.RepresentativePilotError, match="nonbatch"):
        builder._validate_batch_registry(manifest, prior, registry)
    mismatch = copy.deepcopy(fixture_data["first_registry"])
    mismatch["learner_ref"] = "different-learner"
    with pytest.raises(builder.RepresentativePilotError, match="learner_ref_mismatch"):
        builder._validate_batch_registry(manifest, prior, mismatch)


def test_payload_is_learner_safe_and_will_free(fixture_data: dict) -> None:
    payload = fixture_data["prepared"]["batch_payload"]
    assert payload["item_count"] == 8
    assert not any(row["grammar_unit_id"] == builder.DEFERRED_GRAMMAR_ID for row in payload["items"])
    encoded = json.dumps(payload, ensure_ascii=False).casefold()
    for forbidden in ('"answer_key"', '"accepted_texts"', '"accepted_sequence"', '"private_scoring_contract"', '"model_texts"'):
        assert forbidden not in encoded


def test_non_localhost_serve_is_rejected_and_dry_run_reports_remaining(fixture_data: dict, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(builder.RepresentativePilotError, match="non_localhost_bind_forbidden"):
        builder.serve_batch(fixture_data["partial_root"], host="0.0.0.0", port=8772, dry_run=True)
    assert builder.serve_batch(fixture_data["partial_root"], host="127.0.0.1", port=8772, dry_run=True) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["remaining_attempt_count"] == 4


def test_direct_cli_prepare_and_partial_validate() -> None:
    root = builder.REPO_ROOT / ".local" / f"m12d-cli-fullfix-{uuid.uuid4().hex}"
    try:
        input_root, qa_root = _build_fixture_root(root)
        output_root = root / "output"
        prepare = subprocess.run(
            [
                sys.executable,
                str(Path(builder.__file__).resolve()),
                "prepare",
                "--input-root", str(input_root),
                "--qa-root", str(qa_root),
                "--output-root", str(output_root),
                "--expected-origin", "TEST_FIXTURE",
            ],
            cwd=builder.REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert prepare.returncode == 0, prepare.stderr
        value = json.loads(prepare.stdout)
        assert value["remaining_batch_attempt_count"] == 8
        validate = subprocess.run(
            [
                sys.executable,
                str(Path(validator.__file__).resolve()),
                "prepare",
                "--input-root", str(input_root),
                "--qa-root", str(qa_root),
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
