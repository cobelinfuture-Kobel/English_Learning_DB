from __future__ import annotations

import copy
import json
import subprocess
import sys
import wave
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_speaking_v1 as builder
from ulga.query import e4s_a1v1_speaking_consumer as consumer
from ulga.validators import validate_e4s_a1v1_speaking_v1 as validator


def _receipt() -> dict:
    return {
        "task_id": "E4S-A1V1-M05_ListeningV1CompletionAndIntegration",
        "completion": {
            "listening_items": 96,
            "rendered_audio": 96,
            "grammar_units": 24,
            "canonical_egp_rows": 109,
        },
        "claim_boundaries": {
            "canonical_authority_writes": 0,
            "public_delivery_count": 0,
        },
        "next_short_step": builder.TASK_ID,
    }


def _write_wav(path: Path, *, frames: int = 16000, rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\0" * frames * 2)


@pytest.fixture()
def prepared(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(builder, "REPO_ROOT", tmp_path)
    root = tmp_path / ".local/e4s_a1v1/speaking/m06"
    receipt = tmp_path / "m05.json"
    receipt.write_text(json.dumps(_receipt()), encoding="utf-8")
    builder.prepare_artifacts(root, receipt)
    return root


def _approved_attempt(root: Path) -> dict:
    queue = builder.read_json(root / "speaking_capture_queue.private.json")
    item = queue["items"][0]
    relative = f"captures/{item['activity_id']}.wav"
    audio = root / relative
    _write_wav(audio)
    return {
        "evidence_id": f"M06_EVIDENCE:{item['activity_id']}:1",
        "shared_item_id": item["shared_item_id"],
        "activity_id": item["activity_id"],
        "learner_ref": "learner-local-01",
        "attempt_sequence": 1,
        "audio_relative_path": relative,
        "audio_sha256": builder.sha256_file(audio),
        "audio_size_bytes": audio.stat().st_size,
        "audio_mime_type": "audio/wav",
        "manual_transcript_status": "PROVIDED",
        "manual_transcript": "A private manually reviewed learner response.",
        "asr_status": "DISABLED",
        "asr_transcript": None,
        "review_decision": "APPROVE",
        "reviewer_id": "operator-local-01",
        "reviewed_at": "2026-07-15T12:00:00+08:00",
        "grammar_score": 0.9,
        "task_fulfillment_score": 0.9,
        "failure_domain": "none",
        "grammar_error_tags": [],
        "operator_notes": None,
    }


def test_zero_evidence_engine_materializes_and_validates(prepared: Path) -> None:
    result = validator.validate(prepared)
    assert result["validation_status"] == validator.PASS_STATUS, result["errors"]
    assert result["error_count"] == 0
    queue = builder.read_json(prepared / "speaking_capture_queue.private.json")
    bank = builder.read_json(prepared / "speaking_private_review_bank.json")
    report = builder.read_json(prepared / "speaking_safe_report.json")
    assert queue["item_count"] == 96
    assert bank["item_count"] == 96
    assert bank["evidence_count"] == 0
    assert bank["reviewed_count"] == 0
    assert report["validation_status"] == builder.ZERO_EVIDENCE_STATUS
    assert report["counts"]["pending_capture"] == 96


def test_one_realistic_private_attempt_can_be_materialized_and_reviewed(prepared: Path) -> None:
    template = builder.read_json(prepared / "speaking_evidence_input.template.json")
    template["attempts"] = [_approved_attempt(prepared)]
    input_path = prepared / "approved.private.json"
    builder.write_json_atomic(input_path, template)
    result = builder.materialize_evidence(prepared, input_path)
    assert result["bank"]["evidence_count"] == 1
    assert result["bank"]["reviewed_count"] == 1
    assert result["safe_report"]["validation_status"] == builder.PARTIAL_EVIDENCE_STATUS
    assert validator.validate(prepared)["error_count"] == 0
    reviewed = next(item for item in result["bank"]["items"] if item["evidence"] is not None)
    assert reviewed["capture_status"] == "REVIEWED_APPROVE"
    assert reviewed["evidence"]["audio_integrity"]["duration_ms"] == 1000


def test_safe_payload_and_report_do_not_expose_private_contracts(prepared: Path) -> None:
    payload = builder.read_json(prepared / "speaking_learner_safe_payload.json")
    report = builder.read_json(prepared / "speaking_safe_report.json")
    encoded = (json.dumps(payload) + json.dumps(report)).casefold()
    for forbidden in ("answer_contract", "model_text", "manual_transcript", "asr_transcript", "operator_notes", "source_payload"):
        assert forbidden not in encoded
    assert ":\\" not in encoded
    assert report["claim_boundaries"]["learner_mastery_claims"] == 0
    assert report["claim_boundaries"]["asr_enabled"] is False


def test_zero_evidence_rebuild_is_deterministic(prepared: Path) -> None:
    names = [
        "speaking_private_review_bank.json",
        "speaking_safe_report.json",
        "speaking_query_index.private.json",
    ]
    before = {name: builder.sha256_file(prepared / name) for name in names}
    template = builder.read_json(prepared / "speaking_evidence_input.template.json")
    path = prepared / "speaking_evidence_input.template.json"
    builder.materialize_evidence(prepared, path)
    after = {name: builder.sha256_file(prepared / name) for name in names}
    assert before == after
    assert template == builder.read_json(prepared / "speaking_evidence_input.private.json")


def test_queue_mutation_fails_independent_validation(prepared: Path) -> None:
    path = prepared / "speaking_capture_queue.private.json"
    queue = builder.read_json(path)
    queue["items"].pop()
    queue["item_count"] = 95
    builder.write_json_atomic(path, queue)
    result = validator.validate(prepared)
    assert result["error_count"] > 0
    assert any("capture_queue" in error or "evidence_queue_hash" in error for error in result["errors"])


def test_audio_hash_path_and_missing_file_fail_closed(prepared: Path) -> None:
    template = builder.read_json(prepared / "speaking_evidence_input.template.json")
    attempt = _approved_attempt(prepared)
    attempt["audio_sha256"] = "0" * 64
    template["attempts"] = [attempt]
    with pytest.raises(builder.SpeakingBuildError, match="audio_hash_drift"):
        builder.build_evidence_artifacts(prepared, template)
    attempt["audio_sha256"] = builder.sha256_file(prepared / attempt["audio_relative_path"])
    attempt["audio_relative_path"] = "../escape.wav"
    with pytest.raises(builder.SpeakingBuildError, match="unsafe_capture_path"):
        builder.build_evidence_artifacts(prepared, template)


def test_approval_requires_manual_transcript_reviewer_timestamp_and_scores(prepared: Path) -> None:
    template = builder.read_json(prepared / "speaking_evidence_input.template.json")
    attempt = _approved_attempt(prepared)
    attempt["manual_transcript_status"] = "NOT_PROVIDED"
    attempt["manual_transcript"] = None
    template["attempts"] = [attempt]
    with pytest.raises(builder.SpeakingBuildError, match="approved_without_manual_transcript"):
        builder.build_evidence_artifacts(prepared, template)
    attempt = _approved_attempt(prepared)
    attempt["reviewer_id"] = None
    template["attempts"] = [attempt]
    with pytest.raises(builder.SpeakingBuildError, match="reviewer_missing"):
        builder.build_evidence_artifacts(prepared, template)
    attempt = _approved_attempt(prepared)
    attempt["grammar_score"] = None
    template["attempts"] = [attempt]
    with pytest.raises(builder.SpeakingBuildError, match="approved_score_invalid"):
        builder.build_evidence_artifacts(prepared, template)


def test_asr_and_non_grammar_confound_boundaries_fail_closed(prepared: Path) -> None:
    template = builder.read_json(prepared / "speaking_evidence_input.template.json")
    attempt = _approved_attempt(prepared)
    attempt["asr_status"] = "CANDIDATE_ONLY"
    attempt["asr_transcript"] = "unsafe candidate output"
    template["attempts"] = [attempt]
    with pytest.raises(builder.SpeakingBuildError, match="asr_boundary_violation"):
        builder.build_evidence_artifacts(prepared, template)
    attempt = _approved_attempt(prepared)
    attempt["review_decision"] = "REJECT"
    attempt["failure_domain"] = "pronunciation"
    attempt["grammar_error_tags"] = ["ERR_GRAMMAR"]
    template["attempts"] = [attempt]
    with pytest.raises(builder.SpeakingBuildError, match="confound_domain_has_grammar_tags"):
        builder.build_evidence_artifacts(prepared, template)


def test_duplicate_unknown_and_invalid_audio_fail_closed(prepared: Path) -> None:
    template = builder.read_json(prepared / "speaking_evidence_input.template.json")
    attempt = _approved_attempt(prepared)
    template["attempts"] = [attempt, copy.deepcopy(attempt)]
    with pytest.raises(builder.SpeakingBuildError, match="duplicate_evidence_item"):
        builder.build_evidence_artifacts(prepared, template)
    template["attempts"] = [dict(attempt, shared_item_id="UNKNOWN")]
    with pytest.raises(builder.SpeakingBuildError, match="unknown_evidence_item"):
        builder.build_evidence_artifacts(prepared, template)
    bad = prepared / "captures/bad.wav"
    bad.write_bytes(b"not-wave")
    with pytest.raises(builder.SpeakingBuildError, match="invalid_wav"):
        builder.inspect_capture(bad, "audio/wav")


def test_query_surfaces_and_unknown_id(prepared: Path, capsys: pytest.CaptureFixture[str]) -> None:
    index = builder.read_json(prepared / "speaking_query_index.private.json")
    first = index["items"][0]
    cases = [
        ["--output-root", str(prepared), "summary"],
        ["--output-root", str(prepared), "item", "--id", first["shared_item_id"]],
        ["--output-root", str(prepared), "unit", "--grammar-unit-id", first["grammar_unit_id"]],
        ["--output-root", str(prepared), "row", "--egp-row-id", first["canonical_egp_row_ids"][0]],
        ["--output-root", str(prepared), "role", "--value", first["item_role"]],
        ["--output-root", str(prepared), "dimension", "--value", first["evidence_dimension"]],
        ["--output-root", str(prepared), "stage", "--value", first["internal_stage"]],
        ["--output-root", str(prepared), "status", "--value", first["capture_status"]],
    ]
    for argv in cases:
        assert consumer.main(argv) == 0
        capsys.readouterr()
    assert consumer.main(["--output-root", str(prepared), "item", "--id", "UNKNOWN"]) == 2
    capsys.readouterr()
    assert consumer.main(["--output-root", str(prepared), "--private", "summary"]) == 0


def test_local_recorder_is_offline_and_has_capture_contract(prepared: Path) -> None:
    html = (prepared / "local_recorder/index.html").read_text(encoding="utf-8").casefold()
    assert "getusermedia" in html and "mediarecorder" in html
    assert "localstorage" in html and "download evidence json" in html
    assert "answer_key" not in html and "model_text" not in html
    assert "fetch('http" not in html and 'fetch("http' not in html


def test_m05_gate_fails_closed(tmp_path: Path) -> None:
    receipt = _receipt()
    receipt["next_short_step"] = "WRONG"
    path = tmp_path / "m05.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(builder.SpeakingBuildError, match="progression_gate_closed"):
        builder._require_m05_gate(path)


def test_cli_direct_execution_help_outside_repo(tmp_path: Path) -> None:
    for module in (builder, validator, consumer):
        result = subprocess.run(
            [sys.executable, str(Path(module.__file__).resolve()), "--help"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr


def test_tracked_closeout_is_metadata_only_and_requests_real_evidence() -> None:
    path = Path(builder.__file__).resolve().parents[1] / "reports/e4s_a1v1_m06_speaking_v1_closeout.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    assert receipt["implementation"]["speaking_items"] == 96
    assert receipt["implementation"]["capture_review_engine"] == "PASS_READY"
    assert receipt["evidence_state"]["captured_audio"] == 0
    assert receipt["evidence_state"]["manual_transcripts"] == 0
    assert receipt["stop_reason"] == "REAL_SPEAKING_RECORDING_AND_OPERATOR_REVIEW_REQUIRED"
    assert receipt["ci_readback_status"] == "PENDING_REMOTE_CI_READBACK"
    encoded = json.dumps(receipt).casefold()
    for forbidden in ("manual_transcript_text", "model_text", "answer_key", "c:\\", "g:\\"):
        assert forbidden not in encoded
