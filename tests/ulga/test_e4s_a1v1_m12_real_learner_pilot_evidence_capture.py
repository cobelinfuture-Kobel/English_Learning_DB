from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m12_real_learner_pilot_evidence_capture as builder
from ulga.validators import validate_e4s_a1v1_m12_real_learner_pilot_evidence_capture as validator


@pytest.fixture(scope="module")
def prepared() -> tuple[Path, dict]:
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m12-prepare-test-{uuid.uuid4().hex}"
    result = builder.prepare_capture(root)
    yield root, result
    shutil.rmtree(root, ignore_errors=True)


def _response_for_item(item: dict) -> object:
    contract = item["private_scoring_contract"]
    mode = contract["scoring_mode"]
    if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"}:
        values = list(contract.get("accepted_texts", []))
        assert values
        return values[0]
    if mode == "EXACT_SEQUENCE":
        values = list(contract.get("accepted_sequence", []))
        assert values
        return values
    if mode == "FEATURE_RUBRIC":
        return "This is a fixture response."
    raise AssertionError(f"unsupported scoring mode: {mode}")


def _fixture_registry(root: Path, *, item_ids: list[str] | None = None) -> dict:
    source_bank = builder.read_json(root / "runtime/source_m08/text_mode_session_bank.private.json")
    manifest = builder.read_json(root / "pilot_capture_manifest.private.json")
    allowed = set(manifest["selection"]["selectable_item_ids"])
    selectable = [row for row in source_bank["items"] if row["item_id"] in allowed]
    selected = selectable[:1] if item_ids is None else [
        next(row for row in source_bank["items"] if row["item_id"] == item_id)
        for item_id in item_ids
    ]
    registry = builder.m08.empty_attempt_registry(source_bank)
    registry["session_id"] = "fixture-session-001"
    registry["learner_ref"] = "fixture-learner-not-real"
    registry["attempts"] = [
        {
            "item_id": row["item_id"],
            "attempt_sequence": 1,
            "response": _response_for_item(row),
            "submitted_at": f"2026-07-15T12:30:{index:02d}+08:00",
            "operator_review": builder.m08._empty_review(),
        }
        for index, row in enumerate(selected)
    ]
    return registry


def test_prepare_manifest_has_exact_authority_selection(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    manifest = result["manifest"]
    assert manifest["selection"]["selectable_item_count"] == 184
    assert manifest["selection"]["private_ready_unit_count"] == 23
    assert manifest["selection"]["private_ready_row_count"] == 107
    assert manifest["selection"]["reading_item_count"] == 92
    assert manifest["selection"]["writing_item_count"] == 92
    assert manifest["selection"]["practice_item_count"] == 138
    assert manifest["selection"]["assessment_item_count"] == 46
    assert len(manifest["selection"]["selectable_item_ids"]) == 184
    assert len(set(manifest["selection"]["selectable_item_ids"])) == 184


def test_prepare_report_requires_real_learner_session(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    report = result["safe_report"]
    assert report["mode"] == "PREPARE"
    assert report["evidence_origin"] == "NONE"
    assert report["actual_attempt_count"] == 0
    assert report["real_learner_evidence_captured"] is False
    assert report["real_learner_pilot_completed"] is False
    assert report["learner_mastery_claimed"] is False
    assert report["retention_confirmed"] is False
    assert report["validation_status"] == builder.PREPARE_STATUS
    assert report["stop_reason"] == "REAL_LEARNER_SESSION_EVIDENCE_REQUIRED"
    assert report["next_short_step"] == builder.NEXT_IMPORT


def test_prepare_template_is_m08_hash_compatible_and_empty(prepared: tuple[Path, dict]) -> None:
    root, result = prepared
    source_bank = builder.read_json(root / "runtime/source_m08/text_mode_session_bank.private.json")
    template = result["template"]
    assert template["task_id"] == builder.m08.TASK_ID
    assert template["schema_version"] == "e4s.a1v1.text_mode_attempt_registry.v1"
    assert template["session_bank_sha256"] == builder.m08.sha256_value(source_bank)
    assert template["attempts"] == []


def test_prepare_excludes_all_will_items(prepared: tuple[Path, dict]) -> None:
    root, result = prepared
    allowed = set(result["manifest"]["selection"]["selectable_item_ids"])
    source_bank = builder.read_json(root / "runtime/source_m08/text_mode_session_bank.private.json")
    will_items = [row for row in source_bank["items"] if row["grammar_unit_id"] == builder.DEFERRED_GRAMMAR_ID]
    assert len(will_items) == 8
    assert not ({row["item_id"] for row in will_items} & allowed)
    assert result["manifest"]["deferred_unit"]["canonical_egp_row_count"] == 2


def test_prepare_validator_passes(prepared: tuple[Path, dict]) -> None:
    root, _ = prepared
    result = validator.validate_prepare(root)
    assert result["validation_status"] == builder.PREPARE_STATUS
    assert result["error_count"] == 0, result["errors"]
    assert result["real_learner_evidence_captured"] is False


def test_test_fixture_import_is_valid_but_never_real_evidence() -> None:
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m12-fixture-import-{uuid.uuid4().hex}"
    registry_path = root / "fixture_registry.private.json"
    try:
        builder.prepare_capture(root)
        registry = _fixture_registry(root)
        builder.write_json_atomic(registry_path, registry)
        result = builder.import_evidence(
            root,
            registry_path,
            evidence_origin="TEST_FIXTURE",
        )
        report = result["safe_report"]
        assert report["mode"] == "IMPORT"
        assert report["evidence_origin"] == "TEST_FIXTURE"
        assert report["actual_attempt_count"] == 1
        assert report["attempted_unit_count"] == 1
        assert report["attempted_row_count"] >= 1
        assert report["real_learner_evidence_captured"] is False
        assert report["real_learner_pilot_completed"] is False
        assert report["learner_mastery_claimed"] is False
        assert report["validation_status"] == builder.TEST_STATUS
        assert report["stop_reason"] == "REAL_LEARNER_SESSION_EVIDENCE_REQUIRED"
        assert report["next_short_step"] == builder.NEXT_IMPORT
        validation = validator.validate_import(root, expected_origin="TEST_FIXTURE")
        assert validation["validation_status"] == builder.TEST_STATUS
        assert validation["error_count"] == 0, validation["errors"]
        assert validation["real_learner_evidence_captured"] is False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_empty_registry_is_rejected(prepared: tuple[Path, dict]) -> None:
    root, result = prepared
    empty_path = root / "empty_registry.private.json"
    builder.write_json_atomic(empty_path, result["template"])
    with pytest.raises(builder.PilotCaptureError, match="attempt_count_out_of_range"):
        builder.import_evidence(root, empty_path, evidence_origin="TEST_FIXTURE")


def test_registry_hash_drift_is_rejected(prepared: tuple[Path, dict]) -> None:
    root, _ = prepared
    path = root / "hash_drift_registry.private.json"
    registry = _fixture_registry(root)
    registry["session_bank_sha256"] = "0" * 64
    builder.write_json_atomic(path, registry)
    with pytest.raises(builder.PilotCaptureError, match="registry_session_bank_hash"):
        builder.import_evidence(root, path, evidence_origin="TEST_FIXTURE")


def test_deferred_will_attempt_is_rejected(prepared: tuple[Path, dict]) -> None:
    root, _ = prepared
    source_bank = builder.read_json(root / "runtime/source_m08/text_mode_session_bank.private.json")
    will_id = next(row["item_id"] for row in source_bank["items"] if row["grammar_unit_id"] == builder.DEFERRED_GRAMMAR_ID)
    path = root / "will_registry.private.json"
    registry = _fixture_registry(root, item_ids=[will_id])
    builder.write_json_atomic(path, registry)
    with pytest.raises(builder.PilotCaptureError, match="registry_nonselectable_items"):
        builder.import_evidence(root, path, evidence_origin="TEST_FIXTURE")


def test_duplicate_attempt_item_is_rejected(prepared: tuple[Path, dict]) -> None:
    root, _ = prepared
    path = root / "duplicate_registry.private.json"
    registry = _fixture_registry(root)
    duplicate = copy.deepcopy(registry["attempts"][0])
    duplicate["attempt_sequence"] = 2
    duplicate["submitted_at"] = "2026-07-15T12:31:00+08:00"
    registry["attempts"].append(duplicate)
    builder.write_json_atomic(path, registry)
    with pytest.raises(builder.PilotCaptureError, match="registry_duplicate_attempt_item"):
        builder.import_evidence(root, path, evidence_origin="TEST_FIXTURE")


def test_unknown_evidence_origin_is_rejected(prepared: tuple[Path, dict]) -> None:
    root, _ = prepared
    manifest = builder.read_json(root / "pilot_capture_manifest.private.json")
    registry = _fixture_registry(root)
    with pytest.raises(builder.PilotCaptureError, match="evidence_origin_invalid"):
        builder._validate_import_registry(manifest, registry, evidence_origin="SYNTHETIC")


def test_safe_reports_contain_no_private_response(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    encoded = json.dumps(result["safe_report"], ensure_ascii=False).casefold()
    for forbidden in (
        '"response"',
        '"prompt"',
        '"answer_key"',
        '"accepted_texts"',
        '"private_scoring_contract"',
    ):
        assert forbidden not in encoded
    assert ":\\" not in encoded


def test_prepare_is_deterministic(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m12-deterministic-{uuid.uuid4().hex}"
    try:
        rebuilt = builder.prepare_capture(root)
        assert rebuilt["manifest"] == result["manifest"]
        assert rebuilt["template"] == result["template"]
        assert rebuilt["safe_report"] == result["safe_report"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_direct_cli_prepare_import_fixture_and_validate() -> None:
    root = builder.SOURCE_REPO_ROOT / ".local" / f"m12-cli-{uuid.uuid4().hex}"
    registry_path = root / "fixture_registry.private.json"
    try:
        prepare = subprocess.run(
            [
                sys.executable,
                str(Path(builder.__file__).resolve()),
                "prepare",
                "--output-root",
                str(root),
            ],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert prepare.returncode == 0, prepare.stderr
        prepared_payload = json.loads(prepare.stdout)
        assert prepared_payload["validation_status"] == builder.PREPARE_STATUS
        assert prepared_payload["actual_attempts"] == 0
        registry = _fixture_registry(root)
        builder.write_json_atomic(registry_path, registry)
        imported = subprocess.run(
            [
                sys.executable,
                str(Path(builder.__file__).resolve()),
                "import-evidence",
                "--output-root",
                str(root),
                "--attempt-registry",
                str(registry_path),
                "--evidence-origin",
                "TEST_FIXTURE",
            ],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert imported.returncode == 0, imported.stderr
        imported_payload = json.loads(imported.stdout)
        assert imported_payload["validation_status"] == builder.TEST_STATUS
        assert imported_payload["real_learner_evidence_captured"] is False
        validation = subprocess.run(
            [
                sys.executable,
                str(Path(validator.__file__).resolve()),
                "import-evidence",
                "--output-root",
                str(root),
                "--expected-origin",
                "TEST_FIXTURE",
                "--validation-report",
                str(root / "pilot_capture_validation.json"),
            ],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert validation.returncode == 0, validation.stderr
        validation_payload = json.loads(validation.stdout)
        assert validation_payload["error_count"] == 0
        assert validation_payload["real_learner_evidence_captured"] is False
    finally:
        shutil.rmtree(root, ignore_errors=True)
