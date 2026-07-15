from __future__ import annotations

import copy
import json
import subprocess
import sys
import wave
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_listening_v1 as builder
from ulga.query import e4s_a1v1_listening_consumer as consumer
from ulga.validators import validate_e4s_a1v1_listening_v1 as validator


def _receipt() -> dict:
    return {
        "validation_status": "PASS_M04_READING_PROMOTION_CLOSEOUT_RECEIPT",
        "reading_completion": {"reviewed_item_count": 81, "pending_count": 0},
        "m04_gate": {"reading_v1_complete": True, "m05_progression_allowed": True},
        "claim_boundaries": {"canonical_authority_write_count": 0, "public_delivery_count": 0},
    }


def _write_wav(path: Path, *, rate: int = 16000, width: int = 2, channels: int = 1, frames: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(channels)
        handle.setsampwidth(width)
        handle.setframerate(rate)
        handle.writeframes(b"\0" * frames * width * channels)


@pytest.fixture()
def materialized(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(builder, "REPO_ROOT", tmp_path)
    root = tmp_path / ".local/e4s_a1v1/listening/m05"
    receipt = root / "m04_closeout_receipt.private.json"
    builder.write_json_atomic(receipt, _receipt())
    requests = builder.prepare_render_requests(root, receipt)
    for request in requests["requests"]:
        _write_wav(root / request["audio_relative_path"])
    voice = {"name": "CI_FIXTURE", "culture": "en-US", "gender": "NotSet", "age": "NotSet", "rate": -1, "volume": 100, "audio_format": "WAV_PCM_16000HZ_16BIT_MONO"}
    builder.finalize_artifacts(root, voice)
    return root


def test_full_fixture_materialization_and_independent_validation(materialized: Path) -> None:
    result = validator.validate(materialized)
    assert result["validation_status"] == validator.PASS_STATUS, result["errors"]
    assert result["error_count"] == 0
    manifest = builder.read_json(materialized / "audio_asset_manifest.private.json")
    assert manifest["asset_count"] == 96
    assert len({item["activity_id"] for item in manifest["assets"]}) == 96
    assert len({item["audio_asset_id"] for item in manifest["assets"]}) == 96
    assert {item["item_role"] for item in manifest["assets"]} == {"practice", "assessment"}


def test_private_and_safe_delivery_boundaries(materialized: Path) -> None:
    bank = builder.read_json(materialized / "listening_private_delivery_bank.json")
    payload = builder.read_json(materialized / "listening_learner_safe_payload.json")
    report = builder.read_json(materialized / "listening_safe_report.json")
    assert bank["claim_boundaries"] == {
        "real_skill_delivery_complete": True, "actual_learner_evidence_complete": False,
        "learner_mastery_claimed": False, "canonical_authority_write": False,
        "public_delivery": False, "persistent_learner_state_write": False,
    }
    encoded_payload = json.dumps(payload).lower()
    encoded_report = json.dumps(report).lower()
    for forbidden in ("transcript", "accepted_texts", "answer_key", "answer_contract", "model_answer", "review_notes"):
        assert forbidden not in encoded_payload
        assert forbidden not in encoded_report
    assert ":\\" not in encoded_payload and "source_payload" not in encoded_payload
    assert report["claim_boundaries"]["learner_evidence_count"] == 0
    assert report["claim_boundaries"]["mastery_claims"] == 0


def test_metadata_rebuild_is_deterministic(materialized: Path) -> None:
    names = list(validator.ARTIFACT_FILES.values()) + ["local_player/payload.json"]
    before = {name: builder.sha256_file(materialized / name) for name in names}
    voice = builder.read_json(materialized / "audio_asset_manifest.private.json")["assets"][0]["voice"]
    builder.finalize_artifacts(materialized, voice)
    after = {name: builder.sha256_file(materialized / name) for name in names}
    assert before == after


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda value: value["assets"].pop(), "audio_binding_identity_count_not_96"),
        (lambda value: value["assets"][1].update(audio_asset_id=value["assets"][0]["audio_asset_id"]), "duplicate_audio_asset_id"),
        (lambda value: value["assets"][0].update(shared_item_id="WRONG"), "wrong_shared_item_join"),
        (lambda value: value["assets"][0].update(transcript_sha256="0" * 64), "transcript_hash_drift"),
        (lambda value: value["assets"][0].update(audio_sha256="0" * 64), "audio_hash_drift"),
        (lambda value: value["assets"][0].update(public_delivery=True), "false_claim"),
        (lambda value: value["assets"][0].update(canonical_authority_write=True), "false_claim"),
    ],
)
def test_manifest_adversarial_mutations_fail_closed(materialized: Path, mutation, expected: str) -> None:
    path = materialized / "audio_asset_manifest.private.json"
    value = builder.read_json(path)
    mutation(value)
    builder.write_json_atomic(path, value)
    result = validator.validate(materialized)
    assert result["error_count"] > 0
    assert any(expected in error for error in result["errors"])


def test_missing_and_extra_audio_fail_closed(materialized: Path) -> None:
    target = next((materialized / "audio").glob("*.wav"))
    target.unlink()
    result = validator.validate(materialized)
    assert any("missing_audio" in error for error in result["errors"])
    _write_wav(target)
    _write_wav(materialized / "audio/EXTRA.wav")
    result = validator.validate(materialized)
    assert any("extra_audio" in error for error in result["errors"])


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"rate": 8000}, "wrong_sample_rate"), ({"width": 1}, "wrong_sample_width"),
        ({"channels": 2}, "wrong_channel_count"), ({"frames": 8000}, "duration_out_of_range"),
        ({"frames": 240000}, "duration_out_of_range"), ({"frames": 0}, "empty_frames"),
    ],
)
def test_wav_integrity_rejects_wrong_contract(tmp_path: Path, kwargs: dict, expected: str) -> None:
    path = tmp_path / "bad.wav"
    _write_wav(path, **kwargs)
    with pytest.raises(builder.ListeningBuildError, match=expected):
        builder.inspect_wav(path)


def test_invalid_riff_header_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad.wav"
    path.write_bytes(b"not a wav")
    with pytest.raises(builder.ListeningBuildError, match="invalid_wav"):
        builder.inspect_wav(path)


def test_path_traversal_and_root_escape_rejected(materialized: Path) -> None:
    with pytest.raises(builder.ListeningBuildError, match="unsafe_audio_path"):
        builder._resolved_audio_path(materialized, "../escape.wav")
    with pytest.raises(builder.ListeningBuildError, match="unsafe_audio_path"):
        builder._resolved_audio_path(materialized, str((materialized / "audio/x.wav").resolve()))


def test_m04_gate_fails_closed(tmp_path: Path) -> None:
    receipt = _receipt()
    receipt["m04_gate"]["m05_progression_allowed"] = False
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(builder.ListeningBuildError, match="progression_gate_closed"):
        builder._require_m04_gate(path)


def test_query_surfaces_and_unknown_id(materialized: Path, capsys: pytest.CaptureFixture[str]) -> None:
    index = builder.read_json(materialized / "listening_query_index.private.json")
    first = index["items"][0]
    cases = [
        ["--output-root", str(materialized), "summary"],
        ["--output-root", str(materialized), "item", "--id", first["shared_item_id"]],
        ["--output-root", str(materialized), "unit", "--grammar-unit-id", first["grammar_unit_id"]],
        ["--output-root", str(materialized), "row", "--egp-row-id", first["canonical_egp_row_ids"][0]],
        ["--output-root", str(materialized), "role", "--value", first["item_role"]],
        ["--output-root", str(materialized), "dimension", "--value", first["evidence_dimension"]],
        ["--output-root", str(materialized), "stage", "--value", first["internal_stage"]],
    ]
    for argv in cases:
        assert consumer.main(argv) == 0
        capsys.readouterr()
    assert consumer.main(["--output-root", str(materialized), "--private", "summary"]) == 0
    capsys.readouterr()
    assert consumer.main(["--output-root", str(materialized), "--private", "row", "--egp-row-id", first["canonical_egp_row_ids"][0]]) == 0
    capsys.readouterr()
    assert consumer.main(["--output-root", str(materialized), "item", "--id", "UNKNOWN"]) == 2


def test_local_player_and_sapi_contract_are_private_and_offline(materialized: Path) -> None:
    html = (materialized / "local_player/index.html").read_text(encoding="utf-8").lower()
    script = (Path(builder.__file__).resolve().parents[2] / "tools/render_e4s_a1v1_listening_sapi.ps1").read_text(encoding="utf-8").lower()
    assert "audio.controls=true" in html
    assert "localstorage" not in html and "answer_key" not in html and "fetch('http" not in html
    assert "system.speech" in script and "speak([string]$request.transcript)" in script
    assert "output path escapes audio root" in script and "reparse-point audio file is not allowed" in script
    assert "invoke-webrequest" not in script and "invoke-restmethod" not in script


def test_cli_direct_execution_help_outside_repo(tmp_path: Path) -> None:
    for module in (builder, validator, consumer):
        result = subprocess.run([sys.executable, str(Path(module.__file__).resolve()), "--help"], cwd=tmp_path, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stderr


def test_tracked_closeout_is_metadata_only_and_does_not_preclaim_ci() -> None:
    path = Path(builder.__file__).resolve().parents[1] / "reports/e4s_a1v1_m05_listening_v1_closeout.json"
    receipt = json.loads(path.read_text(encoding="utf-8"))
    assert receipt["completion"]["listening_items"] == 96
    assert receipt["completion"]["rendered_audio"] == 96
    assert receipt["ci_readback_status"] == "PENDING_REMOTE_CI_READBACK"
    assert receipt["claim_boundaries"]["audio_bytes_committed"] is False
    assert receipt["claim_boundaries"]["actual_learner_evidence_count"] == 0
    encoded = json.dumps(receipt).lower()
    for forbidden in ("transcript_text", "accepted_texts", "answer_key", "private_prompt", "c:\\", "g:\\"):
        assert forbidden not in encoded
