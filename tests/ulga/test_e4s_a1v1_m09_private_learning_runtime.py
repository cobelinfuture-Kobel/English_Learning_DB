from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08
from ulga.builders import build_e4s_a1v1_m09_private_learning_runtime as builder
from ulga.validators import validate_e4s_a1v1_m09_private_learning_runtime as validator


@pytest.fixture()
def prepared(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, dict]:
    monkeypatch.setattr(builder, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(m08, "REPO_ROOT", tmp_path)
    root = tmp_path / ".local/e4s_a1v1/runtime/m09"
    result = builder.prepare_runtime(
        root,
        m07_receipt_path=builder.M07_RECEIPT_PATH,
        m08_receipt_path=builder.M08_RECEIPT_PATH,
    )
    return root, result


def test_private_runtime_prepares_and_validates(
    prepared: tuple[Path, dict],
) -> None:
    root, result = prepared
    assert result["manifest"]["runtime_status"] == builder.RUNTIME_STATUS
    assert result["health"]["health_status"] == builder.RUNTIME_STATUS
    assert result["acceptance"]["acceptance_status"] == builder.ACCEPTANCE_STATUS
    validation = validator.validate(root)
    assert validation["error_count"] == 0, validation["errors"]
    assert validation["validation_status"] == builder.ACCEPTANCE_STATUS


def test_runtime_has_exact_text_mode_accounting(
    prepared: tuple[Path, dict],
) -> None:
    _, result = prepared
    runtime = result["manifest"]["text_mode_runtime"]
    assert runtime == {
        "available_items": 192,
        "reading_items": 96,
        "writing_items": 96,
        "practice_items": 144,
        "assessment_items": 48,
        "grammar_units": 24,
        "canonical_egp_rows": 109,
        "zero_evidence_state": m08.ZERO_STATUS,
        "session_entrypoint": "text_mode/local_session/index.html",
    }


def test_skill_states_preserve_audio_deferral(prepared: tuple[Path, dict]) -> None:
    _, result = prepared
    states = result["manifest"]["skill_runtime_states"]
    assert states["reading"]["runtime_state"] == "INTERACTIVE_TEXT_SESSION_READY"
    assert states["writing"]["runtime_state"] == "INTERACTIVE_TEXT_SESSION_READY"
    assert states["listening"]["new_audio_asset_processing"] is False
    assert states["speaking"]["recording_controls_enabled"] is False
    assert states["speaking"]["real_audio_evidence_state"] == "DEFERRED_BY_OPERATOR"


def test_runtime_is_localhost_only(prepared: tuple[Path, dict]) -> None:
    root, result = prepared
    policy = result["manifest"]["bind_policy"]
    assert policy["allowed_host"] == "127.0.0.1"
    assert policy["network_submission_enabled"] is False
    assert policy["external_network_dependency"] is False
    assert builder.serve_runtime(
        root,
        host="127.0.0.1",
        port=8765,
        dry_run=True,
    ) == 0
    with pytest.raises(builder.PrivateRuntimeError, match="non_localhost_bind_forbidden"):
        builder.serve_runtime(
            root,
            host="0.0.0.0",
            port=8765,
            dry_run=True,
        )


def test_invalid_port_fails_closed(prepared: tuple[Path, dict]) -> None:
    root, _ = prepared
    with pytest.raises(builder.PrivateRuntimeError, match="port_out_of_range"):
        builder.serve_runtime(
            root,
            host="127.0.0.1",
            port=80,
            dry_run=True,
        )
    m07 = builder.read_json(builder.M07_RECEIPT_PATH)
    m08_receipt = builder.read_json(builder.M08_RECEIPT_PATH)
    text_report = builder.read_json(root / "text_mode/text_mode_progress_safe_report.json")
    text_validation = builder.read_json(root / "text_mode/text_mode_session_validation.json")
    with pytest.raises(builder.PrivateRuntimeError, match="port_out_of_range"):
        builder.build_manifest(
            m07, m08_receipt, text_report, text_validation, port=70000
        )


def test_dashboard_has_no_recording_or_external_network(
    prepared: tuple[Path, dict],
) -> None:
    root, _ = prepared
    html = (root / "dashboard/index.html").read_text(encoding="utf-8")
    lowered = html.casefold()
    assert "open reading / writing session" in lowered
    assert "recording controls are not exposed" in lowered
    assert "deferred by operator" in lowered
    for forbidden in (
        "getusermedia",
        "mediarecorder",
        "<audio",
        "websocket",
        "xmlhttprequest",
        "fetch('http",
        'fetch("http',
        "answer_key",
        "accepted_texts",
    ):
        assert forbidden not in lowered


def test_no_audio_or_recording_files_are_created(
    prepared: tuple[Path, dict],
) -> None:
    root, _ = prepared
    forbidden_suffixes = {".wav", ".webm", ".ogg", ".m4a", ".mp3"}
    assert not [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.casefold() in forbidden_suffixes
    ]


def test_m08_artifact_hashes_match_closeout_receipt(
    prepared: tuple[Path, dict],
) -> None:
    root, _ = prepared
    receipt = builder.read_json(builder.M08_RECEIPT_PATH)
    assert receipt["artifact_hashes"] == {
        "session_bank_sha256": builder.sha256_file(
            root / "text_mode/text_mode_session_bank.private.json"
        ),
        "learner_safe_payload_sha256": builder.sha256_file(
            root / "text_mode/text_mode_learner_safe_payload.json"
        ),
        "progress_safe_report_sha256": builder.sha256_file(
            root / "text_mode/text_mode_progress_safe_report.json"
        ),
        "validation_sha256": builder.sha256_file(
            root / "text_mode/text_mode_session_validation.json"
        ),
    }


def test_required_file_removal_fails_health(prepared: tuple[Path, dict]) -> None:
    root, _ = prepared
    (root / "dashboard/index.html").unlink()
    health = builder.run_health(root)
    assert health["health_status"] == "FAIL"
    assert any("required_file_missing" in error for error in health["errors"])


def test_dashboard_tampering_fails_health(prepared: tuple[Path, dict]) -> None:
    root, _ = prepared
    (root / "dashboard/index.html").write_text(
        "<html><script>navigator.mediaDevices.getUserMedia({audio:true})</script></html>",
        encoding="utf-8",
    )
    health = builder.run_health(root)
    assert health["health_status"] == "FAIL"
    assert any("dashboard_" in error for error in health["errors"])


def test_manifest_tampering_fails_validator(prepared: tuple[Path, dict]) -> None:
    root, _ = prepared
    path = root / "runtime_manifest.json"
    manifest = builder.read_json(path)
    manifest["claim_boundaries"]["recording_enabled"] = True
    builder.write_json_atomic(path, manifest)
    result = validator.validate(root)
    assert result["validation_status"] == "FAIL"
    assert result["error_count"] > 0


def test_dashboard_manifest_drift_fails_health(prepared: tuple[Path, dict]) -> None:
    root, _ = prepared
    path = root / "dashboard/runtime_manifest.json"
    value = builder.read_json(path)
    value["runtime_status"] = "FAIL"
    builder.write_json_atomic(path, value)
    health = builder.run_health(root)
    assert health["health_status"] == "FAIL"
    assert "dashboard_manifest_drift" in health["errors"]


def test_receipt_tampering_fails_manifest_build(prepared: tuple[Path, dict]) -> None:
    root, _ = prepared
    m07 = builder.read_json(builder.M07_RECEIPT_PATH)
    m08_receipt = builder.read_json(builder.M08_RECEIPT_PATH)
    m08_receipt["actual_learner_evidence_count"] = 1
    text_report = builder.read_json(root / "text_mode/text_mode_progress_safe_report.json")
    text_validation = builder.read_json(root / "text_mode/text_mode_session_validation.json")
    with pytest.raises(builder.PrivateRuntimeError, match="m08_evidence"):
        builder.build_manifest(m07, m08_receipt, text_report, text_validation)


def test_output_root_escape_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(builder.PrivateRuntimeError, match="output_root_outside_local"):
        builder._safe_output_root(tmp_path / "outside")


def test_runtime_outputs_are_deterministic(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(builder, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(m08, "REPO_ROOT", tmp_path)
    first_root = tmp_path / ".local/first"
    second_root = tmp_path / ".local/second"
    first = builder.prepare_runtime(
        first_root,
        m07_receipt_path=builder.M07_RECEIPT_PATH,
        m08_receipt_path=builder.M08_RECEIPT_PATH,
    )
    second = builder.prepare_runtime(
        second_root,
        m07_receipt_path=builder.M07_RECEIPT_PATH,
        m08_receipt_path=builder.M08_RECEIPT_PATH,
    )
    assert first == second
    for relative in (
        "runtime_manifest.json",
        "runtime_health.json",
        "runtime_acceptance.json",
        "dashboard/index.html",
        "dashboard/runtime_manifest.json",
    ):
        assert (first_root / relative).read_bytes() == (second_root / relative).read_bytes()


def test_acceptance_has_no_false_mastery_or_production_claims(
    prepared: tuple[Path, dict],
) -> None:
    _, result = prepared
    boundaries = result["acceptance"]["claim_boundaries"]
    assert boundaries["private_local_only"] is True
    for key in (
        "production_runtime_enabled",
        "public_delivery_enabled",
        "canonical_authority_write",
        "persistent_learner_state_service_enabled",
        "actual_learner_evidence_complete",
        "learner_mastery_claimed",
        "retention_confirmed",
        "new_audio_processing_performed",
        "recording_enabled",
        "a2_a2plus_in_scope",
    ):
        assert boundaries[key] is False
    assert result["acceptance"]["stop_reason"] == "NONE"
    assert result["acceptance"]["next_short_step"] == builder.NEXT_SHORT_STEP


def test_direct_cli_prepare_health_and_serve_dry_run() -> None:
    for module in (builder, validator):
        result = subprocess.run(
            [sys.executable, str(Path(module.__file__).resolve()), "--help"],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    root = builder.SOURCE_REPO_ROOT / ".local" / f"m09-ci-{uuid.uuid4().hex}"
    try:
        prepare = subprocess.run(
            [
                sys.executable,
                str(Path(builder.__file__).resolve()),
                "prepare",
                "--output-root",
                str(root),
                "--m07-receipt",
                str(builder.M07_RECEIPT_PATH),
                "--m08-receipt",
                str(builder.M08_RECEIPT_PATH),
            ],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert prepare.returncode == 0, prepare.stderr
        assert json.loads(prepare.stdout)["acceptance_status"] == builder.ACCEPTANCE_STATUS

        health = subprocess.run(
            [
                sys.executable,
                str(Path(builder.__file__).resolve()),
                "health",
                "--output-root",
                str(root),
            ],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert health.returncode == 0, health.stderr
        assert json.loads(health.stdout)["health_status"] == builder.RUNTIME_STATUS

        validate = subprocess.run(
            [
                sys.executable,
                str(Path(validator.__file__).resolve()),
                "--output-root",
                str(root),
                "--validation-report",
                str(root / "runtime_validation.json"),
            ],
            cwd=builder.SOURCE_REPO_ROOT,
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
                str(root),
                "--dry-run",
            ],
            cwd=builder.SOURCE_REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert serve.returncode == 0, serve.stderr
        assert json.loads(serve.stdout)["url"].startswith("http://127.0.0.1:")
    finally:
        shutil.rmtree(root, ignore_errors=True)
