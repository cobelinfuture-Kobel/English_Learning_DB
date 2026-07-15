#!/usr/bin/env python3
"""Build the private/local E4S A1V1 Speaking capture and review surface."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import wave
from collections import Counter
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders.build_a1_a1plus_shared_item_contract import build_artifact as build_shared_contract  # noqa: E402
from ulga.builders.build_a1_grammar_speaking_integration import build_and_validate_from_repo as build_speaking_source  # noqa: E402

TASK_ID = "E4S-A1V1-M06_SpeakingV1CompletionAndIntegration"
PASS_STATUS = "PASS_M06_SPEAKING_CAPTURE_REVIEW_ENGINE_READY"
ZERO_EVIDENCE_STATUS = "PASS_AWAITING_REAL_SPEAKING_EVIDENCE"
PARTIAL_EVIDENCE_STATUS = "PASS_PARTIAL_SPEAKING_EVIDENCE"
NEXT_RESUME_TASK = "E4S-A1V1-M06_SpeakingV1RealEvidenceCollectionAndReview"
EXPECTED_COUNTS = {"items": 96, "practice": 72, "assessment": 24, "units": 24, "rows": 109}
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/speaking/m06"
PRIVATE_KEYS = {
    "answer", "answer_key", "answer_contract", "accepted_texts", "model_answer",
    "model_text", "model_texts", "manual_transcript", "asr_transcript", "transcript",
    "operator_notes", "review_notes", "source_payload", "private_prompt_contract",
    "private_response_contract", "private_scoring_contract", "private_answer_contract",
}
AUDIO_EXTENSIONS = {
    ".wav": {"audio/wav", "audio/x-wav"},
    ".webm": {"audio/webm"},
    ".ogg": {"audio/ogg"},
    ".m4a": {"audio/mp4", "audio/x-m4a"},
}
REVIEW_DECISIONS = {"PENDING", "APPROVE", "REJECT", "DEFER"}
FAILURE_DOMAINS = {
    "none", "grammar", "pronunciation", "asr", "fluency", "task_fulfillment",
    "transcript_uncertainty",
}


class SpeakingBuildError(ValueError):
    """Fail-closed M06 materialization error."""


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
        raise SpeakingBuildError(f"json_root_not_object:{path.name}")
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
        raise SpeakingBuildError(f"output_root_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _require_m05_gate(receipt_path: Path) -> dict[str, Any]:
    receipt = read_json(receipt_path)
    if receipt.get("task_id") != "E4S-A1V1-M05_ListeningV1CompletionAndIntegration":
        raise SpeakingBuildError("m05_receipt_task_invalid")
    completion = receipt.get("completion", {})
    if completion.get("listening_items") != 96 or completion.get("rendered_audio") != 96:
        raise SpeakingBuildError("m05_completion_counts_invalid")
    if completion.get("grammar_units") != 24 or completion.get("canonical_egp_rows") != 109:
        raise SpeakingBuildError("m05_coverage_invalid")
    if receipt.get("next_short_step") != TASK_ID:
        raise SpeakingBuildError("m05_progression_gate_closed")
    boundaries = receipt.get("claim_boundaries", {})
    if boundaries.get("canonical_authority_writes") != 0:
        raise SpeakingBuildError("m05_authority_boundary_invalid")
    if boundaries.get("public_delivery_count") != 0:
        raise SpeakingBuildError("m05_public_boundary_invalid")
    return receipt


def _upstream() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    source, source_report = build_speaking_source()
    if source_report.get("validation_status") != "PASS":
        raise SpeakingBuildError("speaking_source_validation_failed")
    shared = build_shared_contract()
    shared_items = [deepcopy(item) for item in shared.get("shared_items", []) if item.get("skill") == "speaking"]
    activities = source.get("speaking_activity_bank", [])
    if len(activities) != 96 or len(shared_items) != 96:
        raise SpeakingBuildError("upstream_speaking_count_not_96")
    source_ids = {str(item.get("activity_id")) for item in activities}
    shared_source_ids = {str(item.get("source_item_id")) for item in shared_items}
    if source_ids != shared_source_ids:
        raise SpeakingBuildError("shared_item_join_drift")
    summary = source.get("coverage_summary", {})
    for key, expected in {
        "speaking_practice_count": 72,
        "speaking_assessment_count": 24,
        "units_with_speaking_path": 24,
        "rows_with_speaking_path": 109,
        "rows_with_speaking_assessment": 109,
    }.items():
        if summary.get(key) != expected:
            raise SpeakingBuildError(f"upstream_count_drift:{key}")
    return source, shared, sorted(shared_items, key=lambda item: str(item["source_item_id"]))


def _scan_safe(value: Any, *, name: str) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                lowered = str(key).casefold()
                if lowered in PRIVATE_KEYS or "transcript" in lowered or "answer" in lowered or lowered.endswith("_notes"):
                    raise SpeakingBuildError(f"private_field_leak:{name}:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (len(node) > 2 and node[1:3] in {":\\", ":/"}):
                raise SpeakingBuildError(f"absolute_path_leak:{name}")
    walk(value)


def _resolved_capture_path(output_root: Path, relative: str) -> Path:
    relative_path = Path(relative)
    normalized = relative.replace("\\", "/")
    if relative_path.is_absolute() or not normalized.startswith("captures/") or ".." in relative_path.parts:
        raise SpeakingBuildError(f"unsafe_capture_path:{relative}")
    capture_root = (output_root / "captures").resolve()
    path = (output_root / relative_path).resolve(strict=True)
    if not path.is_relative_to(capture_root):
        raise SpeakingBuildError(f"capture_root_escape:{relative}")
    current = path
    while current != capture_root:
        if current.is_symlink() or bool(getattr(os.path, "isjunction", lambda _: False)(current)):
            raise SpeakingBuildError(f"capture_reparse_point_forbidden:{relative}")
        current = current.parent
    return path


def inspect_capture(path: Path, mime_type: str) -> dict[str, Any]:
    suffix = path.suffix.casefold()
    allowed_mimes = AUDIO_EXTENSIONS.get(suffix)
    if not allowed_mimes or mime_type not in allowed_mimes:
        raise SpeakingBuildError(f"unsupported_audio_contract:{path.name}:{mime_type}")
    size = path.stat().st_size
    if size <= 0 or size > 25 * 1024 * 1024:
        raise SpeakingBuildError(f"audio_size_out_of_range:{path.name}:{size}")
    details: dict[str, Any] = {"container": suffix.lstrip("."), "size_bytes": size}
    if suffix == ".wav":
        try:
            with wave.open(str(path), "rb") as handle:
                details.update({
                    "sample_rate_hz": handle.getframerate(),
                    "bits_per_sample": handle.getsampwidth() * 8,
                    "channels": handle.getnchannels(),
                    "frame_count": handle.getnframes(),
                })
        except (EOFError, wave.Error, OSError) as exc:
            raise SpeakingBuildError(f"invalid_wav:{path.name}:{exc}") from exc
        if details["frame_count"] <= 0:
            raise SpeakingBuildError(f"empty_audio_frames:{path.name}")
        duration_ms = round(details["frame_count"] * 1000 / details["sample_rate_hz"])
        details["duration_ms"] = duration_ms
        if duration_ms < 250 or duration_ms > 30000:
            raise SpeakingBuildError(f"audio_duration_out_of_range:{path.name}:{duration_ms}")
    else:
        details.update({"sample_rate_hz": None, "bits_per_sample": None, "channels": None, "frame_count": None, "duration_ms": None})
    return details


def _capture_item(item: Mapping[str, Any]) -> dict[str, Any]:
    activity_id = str(item["source_item_id"])
    return {
        "capture_item_id": f"M06_CAPTURE:{activity_id}",
        "shared_item_id": item["shared_item_id"],
        "activity_id": activity_id,
        "learning_unit_id": item["learning_unit_id"],
        "grammar_unit_id": item["grammar_unit_id"],
        "canonical_egp_row_ids": list(item.get("content_binding", {}).get("canonical_egp_row_ids", [])),
        "internal_stage": item["internal_stage"],
        "item_role": item["item_role"],
        "evidence_dimension": item["evidence_dimension"],
        "task_type": item["task_type"],
        "private_prompt_contract": deepcopy(item.get("prompt_contract", {})),
        "private_response_contract": deepcopy(item.get("response_contract", {})),
        "private_answer_contract": deepcopy(item.get("answer_contract", {})),
        "private_scoring_contract": deepcopy(item.get("scoring_contract", {})),
        "capture_policy": {
            "audio_capture_required": True,
            "manual_transcript_required_for_review": True,
            "asr_optional_candidate_only": True,
            "maximum_recording_seconds": 30,
            "private_local_only": True,
        },
        "capture_status": "AWAITING_CAPTURE",
    }


def _safe_item(item: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "shared_item_id": item["shared_item_id"],
        "activity_id": item["source_item_id"],
        "learning_unit_id": item["learning_unit_id"],
        "grammar_unit_id": item["grammar_unit_id"],
        "canonical_egp_row_ids": list(item.get("content_binding", {}).get("canonical_egp_row_ids", [])),
        "internal_stage": item["internal_stage"],
        "item_role": item["item_role"],
        "evidence_dimension": item["evidence_dimension"],
        "task_type": item["task_type"],
        "prompt": str(item.get("prompt_contract", {}).get("prompt_text") or "Record a short response."),
        "response_mode": "spoken_response",
        "capture_required": True,
        "maximum_recording_seconds": 30,
        "attempt_sequence": 1,
        "capture_status": "AWAITING_CAPTURE",
    }


def _local_recorder_html() -> str:
    return """<!doctype html>
<html lang=\"en\"><meta charset=\"utf-8\"><title>A1 Speaking V1 Local Recorder</title>
<body><h1>A1 Speaking V1 Local Recorder</h1><p id=\"status\">Local-only. No network submission.</p>
<select id=\"item\"></select><p id=\"prompt\"></p><button id=\"start\">Start</button>
<button id=\"stop\" disabled>Stop</button><button id=\"download\" disabled>Download recording</button>
<textarea id=\"manual\" placeholder=\"Optional manual transcript for the local operator\"></textarea>
<button id=\"evidence\">Download evidence JSON</button><script>
let payload, recorder, chunks=[], blob=null;
const stateKey='e4s-a1v1-m06-speaking-local-v1';
async function load(){payload=await (await fetch('./payload.json')).json(); const s=document.querySelector('#item');
payload.items.forEach((x,i)=>{const o=document.createElement('option');o.value=i;o.textContent=x.shared_item_id;s.appendChild(o)});
function show(){document.querySelector('#prompt').textContent=payload.items[Number(s.value)].prompt;}s.onchange=show;show();}
async function start(){const stream=await navigator.mediaDevices.getUserMedia({audio:true});chunks=[];recorder=new MediaRecorder(stream);
recorder.ondataavailable=e=>chunks.push(e.data);recorder.onstop=()=>{blob=new Blob(chunks,{type:recorder.mimeType||'audio/webm'});document.querySelector('#download').disabled=false;stream.getTracks().forEach(t=>t.stop());};recorder.start();document.querySelector('#stop').disabled=false;}
function stop(){if(recorder&&recorder.state!=='inactive')recorder.stop();}
function saveBlob(){const item=payload.items[Number(document.querySelector('#item').value)];const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=item.activity_id+'.webm';a.click();}
function saveEvidence(){const item=payload.items[Number(document.querySelector('#item').value)];const record={shared_item_id:item.shared_item_id,activity_id:item.activity_id,attempt_sequence:1,manual_transcript:document.querySelector('#manual').value};localStorage.setItem(stateKey,JSON.stringify(record));const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(record,null,2)],{type:'application/json'}));a.download=item.activity_id+'.evidence.json';a.click();}
document.querySelector('#start').onclick=start;document.querySelector('#stop').onclick=stop;document.querySelector('#download').onclick=saveBlob;document.querySelector('#evidence').onclick=saveEvidence;load();
</script></body></html>"""


def prepare_artifacts(output_root: Path, m05_receipt_path: Path) -> dict[str, Any]:
    output_root = _safe_output_root(output_root)
    receipt = _require_m05_gate(m05_receipt_path)
    source, shared, shared_items = _upstream()
    queue_items = [_capture_item(item) for item in shared_items]
    safe_items = [_safe_item(item) for item in shared_items]
    queue = {
        "task_id": TASK_ID,
        "schema_version": "e4s.a1v1.speaking_capture_queue.v1",
        "private_local_only": True,
        "item_count": len(queue_items),
        "upstream_hashes": {
            "m05_closeout_receipt_sha256": sha256_value(receipt),
            "speaking_source_sha256": sha256_value(source),
            "shared_contract_sha256": sha256_value(shared),
        },
        "items": queue_items,
    }
    safe_payload = {
        "task_id": TASK_ID,
        "schema_version": "e4s.a1v1.speaking_learner_safe_payload.v1",
        "item_count": len(safe_items),
        "items": safe_items,
        "claim_boundaries": {"network_submission": False, "answer_key_exposed": False, "persistent_learner_state_write": False},
    }
    _scan_safe(safe_payload, name="learner_payload")
    template = {
        "task_id": TASK_ID,
        "schema_version": "e4s.a1v1.speaking_evidence_input.v1",
        "private_local_only": True,
        "capture_queue_sha256": sha256_value(queue),
        "attempts": [],
    }
    write_json_atomic(output_root / "m05_closeout_receipt.private.json", receipt)
    write_json_atomic(output_root / "speaking_capture_queue.private.json", queue)
    write_json_atomic(output_root / "speaking_learner_safe_payload.json", safe_payload)
    write_json_atomic(output_root / "speaking_evidence_input.template.json", template)
    recorder = output_root / "local_recorder"
    recorder.mkdir(parents=True, exist_ok=True)
    (recorder / "index.html").write_text(_local_recorder_html(), encoding="utf-8")
    write_json_atomic(recorder / "payload.json", safe_payload)
    bank, report, query = build_evidence_artifacts(output_root, template)
    write_json_atomic(output_root / "speaking_private_review_bank.json", bank)
    write_json_atomic(output_root / "speaking_safe_report.json", report)
    write_json_atomic(output_root / "speaking_query_index.private.json", query)
    return {"queue": queue, "template": template, "bank": bank, "safe_report": report, "query": query}


def _validate_attempt(output_root: Path, row: Mapping[str, Any], expected: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "evidence_id", "shared_item_id", "activity_id", "learner_ref", "attempt_sequence",
        "audio_relative_path", "audio_sha256", "audio_size_bytes", "audio_mime_type",
        "manual_transcript_status", "manual_transcript", "asr_status", "asr_transcript",
        "review_decision", "reviewer_id", "reviewed_at", "grammar_score",
        "task_fulfillment_score", "failure_domain", "grammar_error_tags", "operator_notes",
    }
    missing = sorted(required - set(row))
    if missing:
        raise SpeakingBuildError(f"evidence_fields_missing:{expected['activity_id']}:{','.join(missing)}")
    if row.get("shared_item_id") != expected.get("shared_item_id") or row.get("activity_id") != expected.get("activity_id"):
        raise SpeakingBuildError(f"evidence_identity_mismatch:{expected['activity_id']}")
    if not isinstance(row.get("learner_ref"), str) or not row["learner_ref"].strip():
        raise SpeakingBuildError(f"learner_ref_invalid:{expected['activity_id']}")
    if not isinstance(row.get("attempt_sequence"), int) or row["attempt_sequence"] < 1:
        raise SpeakingBuildError(f"attempt_sequence_invalid:{expected['activity_id']}")
    path = _resolved_capture_path(output_root, str(row.get("audio_relative_path")))
    if row.get("audio_sha256") != sha256_file(path):
        raise SpeakingBuildError(f"audio_hash_drift:{expected['activity_id']}")
    if row.get("audio_size_bytes") != path.stat().st_size:
        raise SpeakingBuildError(f"audio_size_drift:{expected['activity_id']}")
    audio = inspect_capture(path, str(row.get("audio_mime_type")))
    decision = str(row.get("review_decision"))
    if decision not in REVIEW_DECISIONS:
        raise SpeakingBuildError(f"review_decision_invalid:{expected['activity_id']}:{decision}")
    failure_domain = str(row.get("failure_domain"))
    if failure_domain not in FAILURE_DOMAINS:
        raise SpeakingBuildError(f"failure_domain_invalid:{expected['activity_id']}:{failure_domain}")
    if row.get("asr_status") not in {"DISABLED", "NOT_REQUESTED"} or row.get("asr_transcript") is not None:
        raise SpeakingBuildError(f"asr_boundary_violation:{expected['activity_id']}")
    manual = row.get("manual_transcript")
    manual_status = row.get("manual_transcript_status")
    if manual_status == "PROVIDED":
        if not isinstance(manual, str) or not manual.strip():
            raise SpeakingBuildError(f"manual_transcript_missing:{expected['activity_id']}")
    elif manual_status == "NOT_PROVIDED":
        if manual is not None:
            raise SpeakingBuildError(f"manual_transcript_status_mismatch:{expected['activity_id']}")
    else:
        raise SpeakingBuildError(f"manual_transcript_status_invalid:{expected['activity_id']}")
    if decision != "PENDING":
        if not isinstance(row.get("reviewer_id"), str) or not row["reviewer_id"].strip():
            raise SpeakingBuildError(f"reviewer_missing:{expected['activity_id']}")
        if not isinstance(row.get("reviewed_at"), str) or "T" not in row["reviewed_at"]:
            raise SpeakingBuildError(f"review_timestamp_missing:{expected['activity_id']}")
    if decision == "APPROVE":
        if manual_status != "PROVIDED":
            raise SpeakingBuildError(f"approved_without_manual_transcript:{expected['activity_id']}")
        for key in ("grammar_score", "task_fulfillment_score"):
            value = row.get(key)
            if not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
                raise SpeakingBuildError(f"approved_score_invalid:{expected['activity_id']}:{key}")
    tags = row.get("grammar_error_tags")
    if not isinstance(tags, list) or any(not isinstance(tag, str) or not tag for tag in tags):
        raise SpeakingBuildError(f"grammar_error_tags_invalid:{expected['activity_id']}")
    if failure_domain != "grammar" and tags:
        raise SpeakingBuildError(f"confound_domain_has_grammar_tags:{expected['activity_id']}")
    evidence = deepcopy(dict(row))
    evidence["audio_integrity"] = audio
    evidence["audio_status"] = "CAPTURED_LOCAL_HASH_VALIDATED"
    return evidence


def build_evidence_artifacts(output_root: Path, evidence_input: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    output_root = _safe_output_root(output_root)
    queue = read_json(output_root / "speaking_capture_queue.private.json")
    if evidence_input.get("capture_queue_sha256") != sha256_value(queue):
        raise SpeakingBuildError("evidence_queue_hash_drift")
    queue_items = queue.get("items", [])
    expected_by_shared = {item["shared_item_id"]: item for item in queue_items}
    attempts = evidence_input.get("attempts")
    if not isinstance(attempts, list):
        raise SpeakingBuildError("evidence_attempts_not_array")
    by_shared: dict[str, dict[str, Any]] = {}
    evidence_ids: set[str] = set()
    for row in attempts:
        if not isinstance(row, Mapping):
            raise SpeakingBuildError("evidence_row_not_object")
        shared_id = str(row.get("shared_item_id"))
        if shared_id not in expected_by_shared:
            raise SpeakingBuildError(f"unknown_evidence_item:{shared_id}")
        if shared_id in by_shared:
            raise SpeakingBuildError(f"duplicate_evidence_item:{shared_id}")
        evidence_id = str(row.get("evidence_id"))
        if not evidence_id or evidence_id in evidence_ids:
            raise SpeakingBuildError(f"duplicate_or_missing_evidence_id:{evidence_id}")
        evidence_ids.add(evidence_id)
        by_shared[shared_id] = _validate_attempt(output_root, row, expected_by_shared[shared_id])

    review_items: list[dict[str, Any]] = []
    query_items: list[dict[str, Any]] = []
    capture_statuses: Counter[str] = Counter()
    decisions: Counter[str] = Counter()
    reviewed_count = 0
    for item in queue_items:
        evidence = by_shared.get(item["shared_item_id"])
        if evidence is None:
            status = "AWAITING_CAPTURE"
            decision = "PENDING"
        elif evidence["manual_transcript_status"] == "NOT_PROVIDED":
            status = "AWAITING_MANUAL_TRANSCRIPT"
            decision = evidence["review_decision"]
        elif evidence["review_decision"] == "PENDING":
            status = "PENDING_OPERATOR_REVIEW"
            decision = "PENDING"
        else:
            status = f"REVIEWED_{evidence['review_decision']}"
            decision = evidence["review_decision"]
            reviewed_count += 1
        capture_statuses[status] += 1
        decisions[decision] += 1
        review_items.append({
            "capture_item_id": item["capture_item_id"],
            "shared_item_id": item["shared_item_id"],
            "activity_id": item["activity_id"],
            "learning_unit_id": item["learning_unit_id"],
            "grammar_unit_id": item["grammar_unit_id"],
            "canonical_egp_row_ids": list(item["canonical_egp_row_ids"]),
            "internal_stage": item["internal_stage"],
            "item_role": item["item_role"],
            "evidence_dimension": item["evidence_dimension"],
            "private_prompt_contract": deepcopy(item["private_prompt_contract"]),
            "private_response_contract": deepcopy(item["private_response_contract"]),
            "private_answer_contract": deepcopy(item["private_answer_contract"]),
            "private_scoring_contract": deepcopy(item["private_scoring_contract"]),
            "capture_status": status,
            "evidence": deepcopy(evidence),
            "claim_boundaries": {
                "private_local_only": True,
                "learner_mastery_claimed": False,
                "persistent_learner_state_write": False,
                "canonical_authority_write": False,
                "public_delivery": False,
            },
        })
        query_items.append({
            "shared_item_id": item["shared_item_id"],
            "activity_id": item["activity_id"],
            "learning_unit_id": item["learning_unit_id"],
            "grammar_unit_id": item["grammar_unit_id"],
            "canonical_egp_row_ids": list(item["canonical_egp_row_ids"]),
            "internal_stage": item["internal_stage"],
            "item_role": item["item_role"],
            "evidence_dimension": item["evidence_dimension"],
            "capture_status": status,
            "review_decision": decision,
            "audio_captured": evidence is not None,
            "manual_transcript_present": bool(evidence and evidence["manual_transcript_status"] == "PROVIDED"),
        })
    bank = {
        "task_id": TASK_ID,
        "schema_version": "e4s.a1v1.speaking_private_review_bank.v1",
        "private_local_only": True,
        "item_count": len(review_items),
        "evidence_count": len(by_shared),
        "reviewed_count": reviewed_count,
        "items": review_items,
        "claim_boundaries": {
            "capture_and_review_engine_complete": True,
            "actual_learner_evidence_complete": len(by_shared) == 96,
            "learner_mastery_claimed": False,
            "persistent_learner_state_write": False,
            "canonical_authority_write": False,
            "public_delivery": False,
            "asr_enabled": False,
        },
    }
    rows = {row for item in queue_items for row in item["canonical_egp_row_ids"]}
    units = {item["grammar_unit_id"] for item in queue_items}
    roles = Counter(item["item_role"] for item in queue_items)
    dimensions = Counter(item["evidence_dimension"] for item in queue_items)
    status = ZERO_EVIDENCE_STATUS if not by_shared else PARTIAL_EVIDENCE_STATUS
    report = {
        "task_id": TASK_ID,
        "schema_version": "e4s.a1v1.speaking_safe_report.v1",
        "validation_status": status,
        "input_hashes": {
            "capture_queue_sha256": sha256_value(queue),
            "evidence_input_sha256": sha256_value(evidence_input),
        },
        "counts": {
            "capture_items": len(queue_items),
            "practice_items": roles["practice"],
            "assessment_items": roles["assessment"],
            "grammar_units": len(units),
            "canonical_egp_rows": len(rows),
            "captured_audio": len(by_shared),
            "reviewed_items": reviewed_count,
            "pending_capture": capture_statuses["AWAITING_CAPTURE"],
        },
        "capture_status_distribution": dict(sorted(capture_statuses.items())),
        "review_decision_distribution": dict(sorted(decisions.items())),
        "evidence_dimension_distribution": dict(sorted(dimensions.items())),
        "claim_boundaries": {
            "canonical_authority_writes": 0,
            "public_delivery_count": 0,
            "learner_mastery_claims": 0,
            "persistent_learner_state_writes": 0,
            "asr_enabled": False,
            "production_runtime_enabled": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "REAL_SPEAKING_RECORDING_AND_OPERATOR_REVIEW_REQUIRED" if len(by_shared) < 96 else "NONE",
        "next_resume_task": NEXT_RESUME_TASK,
        "errors": [],
    }
    _scan_safe(report, name="safe_report")
    query = {
        "task_id": TASK_ID,
        "schema_version": "e4s.a1v1.speaking_query_index.v1",
        "item_count": len(query_items),
        "items": query_items,
    }
    return bank, report, query


def materialize_evidence(output_root: Path, evidence_input_path: Path) -> dict[str, Any]:
    output_root = _safe_output_root(output_root)
    evidence_input = read_json(evidence_input_path)
    bank, report, query = build_evidence_artifacts(output_root, evidence_input)
    write_json_atomic(output_root / "speaking_evidence_input.private.json", evidence_input)
    write_json_atomic(output_root / "speaking_private_review_bank.json", bank)
    write_json_atomic(output_root / "speaking_safe_report.json", report)
    write_json_atomic(output_root / "speaking_query_index.private.json", query)
    return {"bank": bank, "safe_report": report, "query": query}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    prepare.add_argument("--m05-receipt", type=Path, required=True)
    materialize = sub.add_parser("materialize")
    materialize.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    materialize.add_argument("--evidence-input", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_artifacts(args.output_root, args.m05_receipt)
            print(json.dumps({
                "capture_items": result["queue"]["item_count"],
                "captured_audio": result["safe_report"]["counts"]["captured_audio"],
                "validation_status": result["safe_report"]["validation_status"],
                "next_resume_task": NEXT_RESUME_TASK,
            }, sort_keys=True))
        else:
            result = materialize_evidence(args.output_root, args.evidence_input)
            print(json.dumps({
                "capture_items": result["bank"]["item_count"],
                "captured_audio": result["bank"]["evidence_count"],
                "reviewed_items": result["bank"]["reviewed_count"],
                "validation_status": result["safe_report"]["validation_status"],
            }, sort_keys=True))
        return 0
    except (SpeakingBuildError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
