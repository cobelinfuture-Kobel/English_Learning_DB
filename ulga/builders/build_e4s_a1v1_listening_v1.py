#!/usr/bin/env python3
"""Materialize the private/local E4S A1V1 Listening V1 delivery surface."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import wave
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_shared_item_contract import build_artifact as build_shared_contract  # noqa: E402
from ulga.builders.build_a1_grammar_listening_integration import build_and_validate_from_repo as build_listening_source  # noqa: E402

TASK_ID = "E4S-A1V1-M05_ListeningV1CompletionAndIntegration"
PASS_STATUS = "PASS_M05_LISTENING_V1_LOCAL"
NEXT_SHORT_STEP = "E4S-A1V1-M06_SpeakingV1CompletionAndIntegration"
EXPECTED_COUNTS = {"items": 96, "practice": 72, "assessment": 24, "units": 24, "rows": 109}
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/listening/m05"
RENDERER_PATH = REPO_ROOT / "tools/render_e4s_a1v1_listening_sapi.ps1"
PRIVATE_NAMES = {
    "transcript", "transcript_text", "accepted_texts", "answer_key", "answer_contract",
    "model_answer", "scoring_target", "review_notes", "source_payload",
}


class ListeningBuildError(ValueError):
    """Fail-closed M05 materialization error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ListeningBuildError(f"json_root_not_object:{path.name}")
    return value


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _safe_output_root(path: Path) -> Path:
    resolved = path.resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise ListeningBuildError(f"output_root_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _require_m04_gate(receipt_path: Path) -> dict[str, Any]:
    receipt = read_json(receipt_path)
    expected = {
        "validation_status": "PASS_M04_READING_PROMOTION_CLOSEOUT_RECEIPT",
        "reviewed_item_count": 81,
        "pending_count": 0,
    }
    if receipt.get("validation_status") != expected["validation_status"]:
        raise ListeningBuildError("m04_closeout_not_pass")
    completion = receipt.get("reading_completion", {})
    gate = receipt.get("m04_gate", {})
    boundaries = receipt.get("claim_boundaries", {})
    if completion.get("reviewed_item_count") != 81 or completion.get("pending_count") != 0:
        raise ListeningBuildError("m04_reading_counts_invalid")
    if gate.get("reading_v1_complete") is not True or gate.get("m05_progression_allowed") is not True:
        raise ListeningBuildError("m04_progression_gate_closed")
    if boundaries.get("canonical_authority_write_count") != 0 or boundaries.get("public_delivery_count") != 0:
        raise ListeningBuildError("m04_boundary_invalid")
    return receipt


def _upstream() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    source, source_report = build_listening_source()
    if source_report.get("validation_status") != "PASS":
        raise ListeningBuildError("listening_source_validation_failed")
    shared = build_shared_contract()
    shared_items = [deepcopy(item) for item in shared.get("shared_items", []) if item.get("skill") == "listening"]
    activities = source.get("listening_activity_bank", [])
    if len(activities) != 96 or len(shared_items) != 96:
        raise ListeningBuildError("upstream_listening_count_not_96")
    source_ids = {str(item.get("activity_id")) for item in activities}
    shared_source_ids = {str(item.get("source_item_id")) for item in shared_items}
    if source_ids != shared_source_ids:
        raise ListeningBuildError("shared_item_join_drift")
    summary = source.get("coverage_summary", {})
    for key, expected in {
        "listening_practice_count": 72, "listening_assessment_count": 24,
        "units_with_listening_path": 24, "rows_with_listening_path": 109,
        "rows_with_listening_assessment": 109,
    }.items():
        if summary.get(key) != expected:
            raise ListeningBuildError(f"upstream_count_drift:{key}")
    return source, shared, sorted(shared_items, key=lambda item: item["source_item_id"])


def prepare_render_requests(output_root: Path, m04_receipt_path: Path) -> dict[str, Any]:
    output_root = _safe_output_root(output_root)
    m04_receipt = _require_m04_gate(m04_receipt_path)
    source, shared, shared_items = _upstream()
    requests: list[dict[str, Any]] = []
    for item in shared_items:
        activity_id = str(item["source_item_id"])
        transcript = item.get("answer_contract", {}).get("transcript_text")
        if not isinstance(transcript, str) or not transcript.strip():
            raise ListeningBuildError(f"transcript_missing:{activity_id}")
        requests.append({
            "activity_id": activity_id,
            "shared_item_id": item["shared_item_id"],
            "transcript": transcript,
            "transcript_sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
            "audio_relative_path": f"audio/{activity_id}.wav",
        })
    payload = {
        "task_id": TASK_ID,
        "schema_version": "e4s.a1v1.listening_render_requests.v1",
        "private_local_only": True,
        "request_count": len(requests),
        "upstream_hashes": {
            "m04_closeout_receipt_sha256": sha256_value(m04_receipt),
            "listening_source_sha256": sha256_value(source),
            "shared_contract_sha256": sha256_value(shared),
        },
        "requests": requests,
    }
    write_json_atomic(output_root / "render_requests.private.json", payload)
    return payload


def inspect_wav(path: Path) -> dict[str, int]:
    try:
        with wave.open(str(path), "rb") as handle:
            channels = handle.getnchannels()
            sample_width = handle.getsampwidth()
            sample_rate = handle.getframerate()
            frames = handle.getnframes()
    except (EOFError, wave.Error, OSError) as exc:
        raise ListeningBuildError(f"invalid_wav:{path.name}:{exc}") from exc
    duration_ms = round(frames * 1000 / sample_rate) if sample_rate else 0
    if sample_rate != 16000:
        raise ListeningBuildError(f"wrong_sample_rate:{path.name}:{sample_rate}")
    if sample_width != 2:
        raise ListeningBuildError(f"wrong_sample_width:{path.name}:{sample_width}")
    if channels != 1:
        raise ListeningBuildError(f"wrong_channel_count:{path.name}:{channels}")
    if frames <= 0:
        raise ListeningBuildError(f"empty_frames:{path.name}")
    if duration_ms <= 500 or duration_ms >= 15000:
        raise ListeningBuildError(f"duration_out_of_range:{path.name}:{duration_ms}")
    return {"sample_rate_hz": sample_rate, "bits_per_sample": sample_width * 8, "channels": channels, "frame_count": frames, "duration_ms": duration_ms}


def _resolved_audio_path(output_root: Path, relative: str) -> Path:
    if Path(relative).is_absolute() or not relative.replace("\\", "/").startswith("audio/"):
        raise ListeningBuildError(f"unsafe_audio_path:{relative}")
    audio_root = (output_root / "audio").resolve()
    path = (output_root / relative).resolve(strict=True)
    if not path.is_relative_to(audio_root):
        raise ListeningBuildError(f"audio_root_escape:{relative}")
    return path


def _scan_safe(value: Any, *, name: str) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                if str(key).lower() in PRIVATE_NAMES:
                    raise ListeningBuildError(f"private_field_leak:{name}:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (len(node) > 2 and node[1:3] in {":\\", ":/"}):
                raise ListeningBuildError(f"absolute_path_leak:{name}")
    walk(value)


def finalize_artifacts(output_root: Path, voice: Mapping[str, Any]) -> dict[str, Any]:
    output_root = _safe_output_root(output_root)
    requests_payload = read_json(output_root / "render_requests.private.json")
    source, shared, shared_items = _upstream()
    request_by_id = {row["activity_id"]: row for row in requests_payload.get("requests", [])}
    shared_by_id = {item["source_item_id"]: item for item in shared_items}
    if len(request_by_id) != 96:
        raise ListeningBuildError("render_request_identity_count_not_96")
    audio_dir = output_root / "audio"
    expected_names = {f"{activity_id}.wav" for activity_id in request_by_id}
    actual_names = {path.name for path in audio_dir.glob("*.wav") if path.is_file()}
    missing, extra = expected_names - actual_names, actual_names - expected_names
    if missing:
        raise ListeningBuildError(f"missing_audio:{sorted(missing)[0]}")
    if extra:
        raise ListeningBuildError(f"extra_audio:{sorted(extra)[0]}")

    assets: list[dict[str, Any]] = []
    bank_items: list[dict[str, Any]] = []
    safe_items: list[dict[str, Any]] = []
    rows: set[str] = set()
    for activity_id in sorted(request_by_id):
        request = request_by_id[activity_id]
        item = shared_by_id.get(activity_id)
        if not item or item["shared_item_id"] != request.get("shared_item_id"):
            raise ListeningBuildError(f"wrong_shared_item_join:{activity_id}")
        transcript = item["answer_contract"]["transcript_text"]
        transcript_hash = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
        if request.get("transcript_sha256") != transcript_hash:
            raise ListeningBuildError(f"transcript_hash_drift:{activity_id}")
        path = _resolved_audio_path(output_root, str(request["audio_relative_path"]))
        wav = inspect_wav(path)
        row_ids = list(item["content_binding"]["canonical_egp_row_ids"])
        rows.update(row_ids)
        asset = {
            "audio_asset_id": f"E4S_A1V1_AUDIO:{activity_id}", "activity_id": activity_id,
            "shared_item_id": item["shared_item_id"], "grammar_unit_id": item["grammar_unit_id"],
            "canonical_egp_row_ids": row_ids, "item_role": item["item_role"],
            "evidence_dimension": item["evidence_dimension"], "transcript_sha256": transcript_hash,
            "audio_relative_path": request["audio_relative_path"], "audio_sha256": sha256_file(path),
            "wav": wav, "voice": dict(voice), "audio_status": "RENDERED_LOCAL_VALIDATED",
            "private_local_only": True, "public_delivery": False, "canonical_authority_write": False,
        }
        assets.append(asset)
        private_item = deepcopy(item)
        private_item.update({
            "activity_id": activity_id, "audio_asset_binding": deepcopy(asset),
            "transcript_sha256": transcript_hash,
        })
        private_item["readiness"]["real_skill_delivery_complete"] = True
        private_item["readiness"]["actual_learner_evidence_complete"] = False
        private_item["claim_boundaries"].update({"learner_mastery_claimed": False, "persistent_learner_state_write": False})
        bank_items.append(private_item)
        safe_items.append({
            "shared_item_id": item["shared_item_id"], "learning_unit_id": item["learning_unit_id"],
            "grammar_unit_id": item["grammar_unit_id"], "internal_stage": item["internal_stage"],
            "item_role": item["item_role"], "evidence_dimension": item["evidence_dimension"],
            "task_type": "listening_candidate", "prompt": item["prompt_contract"]["prompt_text"],
            "response_mode": item["response_contract"]["response_mode"],
            "audio_uri": request["audio_relative_path"], "playback_controls": True,
            "attempt_sequence": None,
        })

    manifest = {"task_id": TASK_ID, "schema_version": "e4s.a1v1.listening_audio_asset_manifest.v1", "private_local_only": True, "asset_count": len(assets), "assets": assets}
    bank = {
        "task_id": TASK_ID, "schema_version": "e4s.a1v1.listening_private_delivery_bank.v1", "private_local_only": True,
        "item_count": len(bank_items), "items": bank_items,
        "claim_boundaries": {"real_skill_delivery_complete": True, "actual_learner_evidence_complete": False, "learner_mastery_claimed": False, "canonical_authority_write": False, "public_delivery": False, "persistent_learner_state_write": False},
    }
    safe_payload = {"task_id": TASK_ID, "schema_version": "e4s.a1v1.listening_learner_safe_payload.v1", "item_count": len(safe_items), "items": safe_items}
    _scan_safe(safe_payload, name="learner_payload")
    query_items = [{
        "shared_item_id": asset["shared_item_id"], "activity_id": asset["activity_id"],
        "grammar_unit_id": asset["grammar_unit_id"], "learning_unit_id": shared_by_id[asset["activity_id"]]["learning_unit_id"],
        "canonical_egp_row_ids": asset["canonical_egp_row_ids"], "internal_stage": shared_by_id[asset["activity_id"]]["internal_stage"],
        "item_role": asset["item_role"], "evidence_dimension": asset["evidence_dimension"],
        "voice_culture": voice.get("culture"), "audio_status": asset["audio_status"],
    } for asset in assets]
    query_index = {"task_id": TASK_ID, "schema_version": "e4s.a1v1.listening_query_index.v1", "item_count": 96, "items": query_items}
    durations = [asset["wav"]["duration_ms"] for asset in assets]
    roles = Counter(asset["item_role"] for asset in assets)
    dimensions = Counter(asset["evidence_dimension"] for asset in assets)
    units = {asset["grammar_unit_id"] for asset in assets}
    safe_report = {
        "task_id": TASK_ID, "schema_version": "e4s.a1v1.listening_safe_report.v1", "validation_status": PASS_STATUS,
        "input_artifact_hashes": {**requests_payload["upstream_hashes"], "render_requests_sha256": sha256_value(requests_payload)},
        "voice": dict(voice),
        "counts": {"source_activities": 96, "shared_items": 96, "audio_bindings": 96, "validated_wav_files": 96, "learner_safe_items": 96, "missing_audio": 0, "extra_audio": 0, "duplicate_bindings": 0, "invalid_wav": 0},
        "duration_ms": {"minimum": min(durations), "maximum": max(durations), "total": sum(durations)},
        "distributions": {"audio_format": {"PCM_16000HZ_16BIT_MONO": 96}, "item_role": dict(sorted(roles.items())), "evidence_dimension": dict(sorted(dimensions.items()))},
        "coverage": {"units": len(units), "canonical_rows": len(rows), "rows_with_listening_path": 109, "rows_with_listening_assessment": 109},
        "query_surface_counts": {"items": 96, "units": 24, "rows": 109, "roles": len(roles), "dimensions": len(dimensions), "stages": len({item["internal_stage"] for item in query_items})},
        "claim_boundaries": {"canonical_authority_writes": 0, "public_delivery_count": 0, "learner_evidence_count": 0, "mastery_claims": 0, "persistent_learner_state_writes": 0, "private_local_delivery_only": True},
        "errors": [], "next_short_step": NEXT_SHORT_STEP,
    }
    _scan_safe(safe_report, name="safe_report")
    write_json_atomic(output_root / "audio_asset_manifest.private.json", manifest)
    write_json_atomic(output_root / "listening_private_delivery_bank.json", bank)
    write_json_atomic(output_root / "listening_learner_safe_payload.json", safe_payload)
    write_json_atomic(output_root / "listening_query_index.private.json", query_index)
    write_json_atomic(output_root / "listening_safe_report.json", safe_report)
    player = output_root / "local_player"
    write_json_atomic(player / "payload.json", safe_payload)
    html = """<!doctype html><meta charset=\"utf-8\"><title>E4S A1V1 Listening</title><main id=\"app\"></main><script>fetch('payload.json').then(r=>r.json()).then(p=>{const a=document.querySelector('#app');for(const x of p.items){const s=document.createElement('section');const h=document.createElement('p');h.textContent=x.prompt;const audio=document.createElement('audio');audio.controls=true;audio.src='../'+x.audio_uri;const input=document.createElement('input');input.setAttribute('aria-label','Learner response');s.append(h,audio,input);a.append(s)}})</script>"""
    (player / "index.html").write_text(html + "\n", encoding="utf-8")
    return safe_report


def _invoke_sapi(output_root: Path, requests_path: Path, voice_name: str | None, rate: int, volume: int) -> dict[str, Any]:
    command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(RENDERER_PATH), "-RequestFile", str(requests_path), "-OutputRoot", str(output_root), "-Rate", str(rate), "-Volume", str(volume)]
    if voice_name:
        command.extend(["-VoiceName", voice_name])
    result = subprocess.run(command, check=False, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise ListeningBuildError(f"sapi_renderer_failed:{result.stderr.strip() or result.stdout.strip()}")
    try:
        value = json.loads(result.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError) as exc:
        raise ListeningBuildError("sapi_renderer_metadata_invalid") from exc
    return value["voice"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--m04-closeout-receipt", type=Path)
    parser.add_argument("--renderer", choices=("windows-sapi", "requests-only", "existing"), default="windows-sapi")
    parser.add_argument("--voice-name")
    parser.add_argument("--rate", type=int, choices=range(-3, 2), default=-1)
    parser.add_argument("--volume", type=int, choices=range(0, 101), default=100)
    args = parser.parse_args(argv)
    output_root = _safe_output_root(args.output_root)
    receipt = args.m04_closeout_receipt or output_root / "m04_closeout_receipt.private.json"
    try:
        prepare_render_requests(output_root, receipt)
        if args.renderer == "requests-only":
            print(json.dumps({"status": "RENDER_REQUESTS_READY", "requests": 96}, sort_keys=True))
            return 0
        if args.renderer == "windows-sapi":
            voice = _invoke_sapi(output_root, output_root / "render_requests.private.json", args.voice_name, args.rate, args.volume)
            write_json_atomic(output_root / "voice_metadata.private.json", voice)
        else:
            voice_path = output_root / "voice_metadata.private.json"
            if not voice_path.exists():
                raise ListeningBuildError("voice_metadata_missing_for_existing_audio")
            voice = read_json(voice_path)
        report = finalize_artifacts(output_root, voice)
        print(json.dumps({"status": report["validation_status"], "items": report["counts"]["validated_wav_files"], "next_short_step": report["next_short_step"]}, sort_keys=True))
        return 0
    except (ListeningBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
