from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

import pytest

from ulga.builders import build_e4s_a1v1_speaking_evidence_registry as registry
from ulga.builders import build_e4s_a1v1_speaking_v1 as speaking
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
        "next_short_step": speaking.TASK_ID,
    }


def _write_wav(path: Path, *, frames: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\0" * frames * 2)


@pytest.fixture()
def prepared(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, dict]:
    monkeypatch.setattr(speaking, "REPO_ROOT", tmp_path)
    root = tmp_path / ".local/e4s_a1v1/speaking/m06"
    receipt = tmp_path / "m05.json"
    receipt.write_text(json.dumps(_receipt()), encoding="utf-8")
    speaking.prepare_artifacts(root, receipt)
    queue = speaking.read_json(root / "speaking_capture_queue.private.json")
    item = queue["items"][0]
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    return root, downloads, item


def _draft(path: Path, item: dict, *, manual: str | None = "I am ready.", extra: dict | None = None) -> Path:
    payload = {
        "shared_item_id": item["shared_item_id"],
        "activity_id": item["activity_id"],
        "attempt_sequence": 1,
        "manual_transcript": manual,
    }
    if extra:
        payload.update(extra)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_browser_draft_and_audio_become_complete_materialized_registry(
    prepared: tuple[Path, Path, dict],
) -> None:
    root, downloads, item = prepared
    audio = downloads / f"{item['activity_id']}.wav"
    _write_wav(audio)
    draft = _draft(downloads / f"{item['activity_id']}.evidence.json", item)

    result = registry.assemble_registry(root, [draft], downloads, "learner-local-01")

    assert result["validation_status"] == registry.PASS_STATUS
    assert result["imported_attempt_count"] == 1
    assert result["captured_audio_count"] == 1
    evidence = speaking.read_json(root / "speaking_evidence_input.private.json")
    assert len(evidence["attempts"]) == 1
    attempt = evidence["attempts"][0]
    assert attempt["audio_relative_path"] == f"captures/{item['activity_id']}.wav"
    assert len(attempt["audio_sha256"]) == 64
    assert attempt["audio_size_bytes"] > 0
    assert attempt["manual_transcript_status"] == "PROVIDED"
    assert attempt["review_decision"] == "PENDING"
    assert attempt["reviewer_id"] is None
    assert attempt["asr_status"] == "DISABLED"
    bank = speaking.read_json(root / "speaking_private_review_bank.json")
    captured = next(row for row in bank["items"] if row["shared_item_id"] == item["shared_item_id"])
    assert captured["capture_status"] == "PENDING_OPERATOR_REVIEW"
    assert validator.validate(root)["error_count"] == 0


def test_missing_manual_transcript_routes_to_manual_transcript_gate(
    prepared: tuple[Path, Path, dict],
) -> None:
    root, downloads, item = prepared
    _write_wav(downloads / f"{item['activity_id']}.wav")
    draft = _draft(downloads / "draft.json", item, manual="")
    result = registry.assemble_registry(root, [draft], downloads, "learner-local-01")
    assert result["captured_audio_count"] == 1
    bank = speaking.read_json(root / "speaking_private_review_bank.json")
    captured = next(row for row in bank["items"] if row["shared_item_id"] == item["shared_item_id"])
    assert captured["capture_status"] == "AWAITING_MANUAL_TRANSCRIPT"
    assert captured["evidence"]["manual_transcript"] is None


def test_repeated_identical_import_is_idempotent(
    prepared: tuple[Path, Path, dict],
) -> None:
    root, downloads, item = prepared
    _write_wav(downloads / f"{item['activity_id']}.wav")
    draft = _draft(downloads / "draft.json", item)
    first = registry.assemble_registry(root, [draft], downloads, "learner-local-01")
    before = speaking.sha256_file(root / "speaking_evidence_input.private.json")
    second = registry.assemble_registry(root, [draft], downloads, "learner-local-01")
    after = speaking.sha256_file(root / "speaking_evidence_input.private.json")
    assert first["imported_attempt_count"] == 1
    assert second["imported_attempt_count"] == 0
    assert before == after


def test_missing_or_ambiguous_audio_fails_closed(
    prepared: tuple[Path, Path, dict],
) -> None:
    root, downloads, item = prepared
    draft = _draft(downloads / "draft.json", item)
    with pytest.raises(registry.EvidenceRegistryError, match="capture_audio_missing"):
        registry.assemble_registry(root, [draft], downloads, "learner-local-01")
    _write_wav(downloads / f"{item['activity_id']}.wav")
    (downloads / f"{item['activity_id']}.webm").write_bytes(b"webm-fixture")
    with pytest.raises(registry.EvidenceRegistryError, match="capture_audio_ambiguous"):
        registry.assemble_registry(root, [draft], downloads, "learner-local-01")


def test_unknown_join_duplicate_draft_and_unknown_fields_fail_closed(
    prepared: tuple[Path, Path, dict],
) -> None:
    root, downloads, item = prepared
    _write_wav(downloads / f"{item['activity_id']}.wav")
    unknown = _draft(downloads / "unknown.json", dict(item, shared_item_id="UNKNOWN"))
    with pytest.raises(registry.EvidenceRegistryError, match="unknown_shared_item"):
        registry.assemble_registry(root, [unknown], downloads, "learner-local-01")
    valid = _draft(downloads / "valid.json", item)
    with pytest.raises(registry.EvidenceRegistryError, match="duplicate_identity"):
        registry.assemble_registry(root, [valid, valid], downloads, "learner-local-01")
    extra = _draft(downloads / "extra.json", item, extra={"unexpected": True})
    with pytest.raises(registry.EvidenceRegistryError, match="unknown_fields"):
        registry.assemble_registry(root, [extra], downloads, "learner-local-01")


def test_existing_registry_hash_drift_and_conflicting_attempt_fail_closed(
    prepared: tuple[Path, Path, dict],
) -> None:
    root, downloads, item = prepared
    _write_wav(downloads / f"{item['activity_id']}.wav")
    draft = _draft(downloads / "draft.json", item)
    registry.assemble_registry(root, [draft], downloads, "learner-local-01")
    evidence_path = root / "speaking_evidence_input.private.json"
    evidence = speaking.read_json(evidence_path)
    evidence["capture_queue_sha256"] = "0" * 64
    speaking.write_json_atomic(evidence_path, evidence)
    with pytest.raises(registry.EvidenceRegistryError, match="queue_hash_drift"):
        registry.assemble_registry(root, [draft], downloads, "learner-local-01")


def test_cli_help_runs_outside_repository(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(Path(registry.__file__).resolve()), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--capture-draft" in result.stdout
    assert "--audio-source-dir" in result.stdout
