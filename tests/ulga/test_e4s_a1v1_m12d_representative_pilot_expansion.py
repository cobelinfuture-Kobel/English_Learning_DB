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
    if mode == "EXACT_MORPHOLOGY":
        parts = contract.get("correct_morphology_parts", [])
        if isinstance(parts, list):
            return " ".join(str(value) for value in parts)
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
        if row["item_id"] in allowed and row["private_scoring_contract"]["scoring_mode"] != "HUMAN_REVIEW"
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


def _build_batch_registry(input_root: Path, manifest: dict) -> dict:
    bank = json.loads((input_root / "runtime/source_m08/text_mode_session_bank.private.json").read_text(encoding="utf-8"))
    by_id = {row["item_id"]: row for row in bank["items"]}
    prior = json.loads((input_root / "pilot_attempt_registry.private.json").read_text(encoding="utf-8"))
    registry = m12.m08.empty_attempt_registry(bank)
    registry["session_id"] = "m12d-batch-fixture"
    registry["learner_ref"] = prior["learner_ref"]
    registry["attempts"] = [
        {
            "item_id": item_id,
            "attempt_sequence": index,
            "response": _response_for(by_id[item_id]),
            "submitted_at": f"2026-07-15T13:{20 + index:02d}:05.516Z",
            "operator_review": m12.m08._empty_review(),
        }
        for index, item_id in enumerate(manifest["batch_selection"]["item_ids"], start=1)
    ]
    return registry


@pytest.fixture(scope="module")
def fixture_data() -> dict:
    root = builder.REPO_ROOT / ".local" / f"m12d-test-{uuid.uuid4().hex}"
    input_root, qa_root = _build_fixture_root(root)
    prepare_root = root / "prepare"
    prepared = builder.prepare_batch(
        input_root,
        qa_root,
        prepare_root,
        expected_origin="TEST_FIXTURE",
    )
    batch_registry = _build_batch_registry(input_root, prepared["manifest"])
    registry_path = root / "batch_registry.private.json"
    registry_path.write_text(json.dumps(batch_registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    import_root = root / "import"
    imported = builder.import_batch(
        input_root,
        qa_root,
        import_root,
        registry_path,
        expected_origin="TEST_FIXTURE",
    )
    yield {
        "root": root,
        "input_root": input_root,
        "qa_root": qa_root,
        "prepare_root": prepare_root,
        "prepared": prepared,
        "registry_path": registry_path,
        "batch_registry": batch_registry,
        "import_root": import_root,
        "imported": imported,
    }
    shutil.rmtree(root, ignore_errors=True)


def test_prepare_builds_balanced_4x2_batch(fixture_data: dict) -> None:
    manifest = fixture_data["prepared"]["manifest"]
    selection = manifest["batch_selection"]
    assert selection["batch_size"] == 8
    assert selection["grammar_unit_count"] == 4
    assert selection["skill_counts"] == {"reading": 4, "writing": 4}
    assert selection["role_counts"] == {"practice": 4, "assessment": 4}
    assert len(selection["item_ids"]) == len(set(selection["item_ids"])) == 8
    assert len(selection["grammar_unit_ids"]) == 4


def test_batch_uses_m12c_priority_units(fixture_data: dict) -> None:
    qa_report = json.loads((fixture_data["qa_root"] / "real_evidence_qa_safe_report.json").read_text(encoding="utf-8"))
    priority: list[str] = []
    for row in qa_report["iteration_queue"]["items"]:
        grammar_id = row["grammar_unit_id"]
        if grammar_id not in priority:
            priority.append(grammar_id)
    chosen = fixture_data["prepared"]["manifest"]["batch_selection"]["grammar_unit_ids"]
    required_priority = set(priority[: min(4, len(priority))])
    assert required_priority.issubset(set(chosen))
    assert len(chosen) == 4


def test_batch_excludes_prior_attempt_and_deferred_will(fixture_data: dict) -> None:
    prior = json.loads((fixture_data["input_root"] / "pilot_attempt_registry.private.json").read_text(encoding="utf-8"))
    prior_ids = {row["item_id"] for row in prior["attempts"]}
    selected = set(fixture_data["prepared"]["manifest"]["batch_selection"]["item_ids"])
    assert not (prior_ids & selected)
    assert not any(item_id.startswith(builder.DEFERRED_GRAMMAR_ID) for item_id in selected)


def test_batch_payload_is_learner_safe(fixture_data: dict) -> None:
    payload = fixture_data["prepared"]["batch_payload"]
    assert payload["item_count"] == 8
    encoded = json.dumps(payload, ensure_ascii=False).casefold()
    for forbidden in (
        '"answer_key"',
        '"accepted_texts"',
        '"accepted_sequence"',
        '"private_scoring_contract"',
        '"model_texts"',
    ):
        assert forbidden not in encoded


def test_prepare_validator_passes(fixture_data: dict) -> None:
    result = validator.validate(
        "prepare",
        fixture_data["input_root"],
        fixture_data["qa_root"],
        fixture_data["prepare_root"],
        expected_origin="TEST_FIXTURE",
    )
    assert result["error_count"] == 0, result["errors"]
    assert result["validation_status"] == builder.PREPARE_STATUS
    assert result["batch_size"] == 8
    assert result["batch_unit_count"] == 4


def test_import_merges_prior_and_batch_evidence(fixture_data: dict) -> None:
    imported = fixture_data["imported"]
    report = imported["safe_report"]
    assert report["prior_attempt_count"] == 1
    assert report["batch_attempt_count"] == 8
    assert report["cumulative_attempt_count"] == 9
    assert imported["ledger"]["attempt_count"] == 9
    ids = [row["item_id"] for row in imported["cumulative_registry"]["attempts"]]
    assert len(ids) == len(set(ids)) == 9
    assert report["validation_status"] == builder.TEST_STATUS
    assert report["stop_reason"] == "REAL_LEARNER_REPRESENTATIVE_BATCH_REQUIRED"
    assert report["claim_boundaries"]["test_fixture_counted_as_real_evidence"] is False


def test_import_validator_passes(fixture_data: dict) -> None:
    result = validator.validate(
        "import-batch",
        fixture_data["input_root"],
        fixture_data["qa_root"],
        fixture_data["import_root"],
        expected_origin="TEST_FIXTURE",
    )
    assert result["error_count"] == 0, result["errors"]
    assert result["validation_status"] == builder.TEST_STATUS
    assert result["cumulative_attempt_count"] == 9


def test_duplicate_prior_item_is_rejected(fixture_data: dict) -> None:
    manifest = fixture_data["prepared"]["manifest"]
    registry = copy.deepcopy(fixture_data["batch_registry"])
    prior = json.loads((fixture_data["input_root"] / "pilot_attempt_registry.private.json").read_text(encoding="utf-8"))
    registry["attempts"][0]["item_id"] = prior["attempts"][0]["item_id"]
    with pytest.raises(builder.RepresentativePilotError, match="nonbatch|duplicates_prior"):
        builder._validate_batch_registry(manifest, prior, registry)


def test_nonbatch_item_is_rejected(fixture_data: dict) -> None:
    manifest = fixture_data["prepared"]["manifest"]
    registry = copy.deepcopy(fixture_data["batch_registry"])
    prior = json.loads((fixture_data["input_root"] / "pilot_attempt_registry.private.json").read_text(encoding="utf-8"))
    query = json.loads((fixture_data["input_root"] / "pilot_progress_query_index.json").read_text(encoding="utf-8"))
    allowed = set(manifest["batch_selection"]["item_ids"])
    nonbatch = next(row["item_id"] for row in query["items"] if row["item_id"] not in allowed and not row["attempted"])
    registry["attempts"][0]["item_id"] = nonbatch
    with pytest.raises(builder.RepresentativePilotError, match="nonbatch"):
        builder._validate_batch_registry(manifest, prior, registry)


def test_learner_ref_mismatch_is_rejected(fixture_data: dict) -> None:
    manifest = fixture_data["prepared"]["manifest"]
    registry = copy.deepcopy(fixture_data["batch_registry"])
    prior = json.loads((fixture_data["input_root"] / "pilot_attempt_registry.private.json").read_text(encoding="utf-8"))
    registry["learner_ref"] = "different-learner"
    with pytest.raises(builder.RepresentativePilotError, match="learner_ref_mismatch"):
        builder._validate_batch_registry(manifest, prior, registry)


def test_prepare_is_deterministic(fixture_data: dict) -> None:
    rebuild = fixture_data["root"] / "deterministic"
    try:
        result = builder.prepare_batch(
            fixture_data["input_root"],
            fixture_data["qa_root"],
            rebuild,
            expected_origin="TEST_FIXTURE",
        )
        assert result["manifest"] == fixture_data["prepared"]["manifest"]
        assert result["batch_payload"] == fixture_data["prepared"]["batch_payload"]
        assert result["safe_report"] == fixture_data["prepared"]["safe_report"]
    finally:
        shutil.rmtree(rebuild, ignore_errors=True)


def test_non_localhost_serve_is_rejected(fixture_data: dict) -> None:
    with pytest.raises(builder.RepresentativePilotError, match="non_localhost_bind_forbidden"):
        builder.serve_batch(fixture_data["prepare_root"], host="0.0.0.0", port=8772, dry_run=True)


def test_direct_cli_prepare_validate_and_serve() -> None:
    root = builder.REPO_ROOT / ".local" / f"m12d-cli-{uuid.uuid4().hex}"
    try:
        input_root, qa_root = _build_fixture_root(root)
        output_root = root / "output"
        prepare = subprocess.run(
            [
                sys.executable,
                str(Path(builder.__file__).resolve()),
                "prepare",
                "--input-root",
                str(input_root),
                "--qa-root",
                str(qa_root),
                "--output-root",
                str(output_root),
                "--expected-origin",
                "TEST_FIXTURE",
            ],
            cwd=builder.REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert prepare.returncode == 0, prepare.stderr
        assert json.loads(prepare.stdout)["validation_status"] == builder.PREPARE_STATUS
        validate = subprocess.run(
            [
                sys.executable,
                str(Path(validator.__file__).resolve()),
                "prepare",
                "--input-root",
                str(input_root),
                "--qa-root",
                str(qa_root),
                "--output-root",
                str(output_root),
                "--expected-origin",
                "TEST_FIXTURE",
                "--validation-report",
                str(output_root / "validation.json"),
            ],
            cwd=builder.REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert validate.returncode == 0, validate.stderr
        assert json.loads(validate.stdout)["error_count"] == 0
        serve = subprocess.run(
            [
                sys.executable,
                str(Path(builder.__file__).resolve()),
                "serve",
                "--output-root",
                str(output_root),
                "--dry-run",
            ],
            cwd=builder.REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert serve.returncode == 0, serve.stderr
        assert json.loads(serve.stdout)["batch_status"] == "READY_FOR_REPRESENTATIVE_PILOT_BATCH"
    finally:
        shutil.rmtree(root, ignore_errors=True)
