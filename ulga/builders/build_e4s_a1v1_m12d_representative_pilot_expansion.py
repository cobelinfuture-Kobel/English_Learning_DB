#!/usr/bin/env python3
"""Prepare, resume, and import a balanced representative A1/A1+ pilot batch.

M12D consumes accepted M12 evidence and the M12C iteration queue. It chooses
four priority grammar units and exposes two items per unit, balanced as Reading
4 / Writing 4 and practice 4 / assessment 4. Partial learner exports are
preserved as resumable evidence but cannot advance to M12E. Only a cumulative
8/8 batch is complete. CI fixtures remain explicitly separated from real
learner evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from copy import deepcopy
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m12_real_learner_pilot_evidence_capture as m12  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12c_real_learner_pilot_evidence_qa as m12c  # noqa: E402

TASK_ID = "E4S-A1V1-M12D_RepresentativePilotExpansion"
MANIFEST_SCHEMA_VERSION = "e4s.a1v1.m12d.representative_pilot_batch_manifest.v1"
REPORT_SCHEMA_VERSION = "e4s.a1v1.m12d.representative_pilot_safe_report.v1"
PREPARE_STATUS = "PASS_M12D_REPRESENTATIVE_PILOT_BATCH_READY"
PARTIAL_STATUS = "PASS_M12D_REPRESENTATIVE_PILOT_BATCH_PARTIAL"
TEST_STATUS = "PASS_M12D_TEST_FIXTURE_REPRESENTATIVE_BATCH_VALIDATED"
REAL_STATUS = "PASS_M12D_REAL_LEARNER_REPRESENTATIVE_BATCH_CAPTURED"
NEXT_IMPORT = "E4S-A1V1-M12D_RepresentativePilotExpansion"
NEXT_QA = "E4S-A1V1-M12E_RepresentativePilotEvidenceQAAndCoverageExpansion"
DEFAULT_INPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12"
DEFAULT_QA_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12c"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12d"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8772
SCHEMA_DIR = REPO_ROOT / "ulga/schemas"
DEFERRED_GRAMMAR_ID = "GRAMMAR_WILL_FUTURE_A1"
EVIDENCE_ORIGINS = {"REAL_LEARNER", "TEST_FIXTURE"}
BATCH_SIZE = 8
OUTCOMES = (
    "AUTO_PASS",
    "AUTO_FAIL",
    "PENDING_HUMAN_REVIEW",
    "HUMAN_APPROVE",
    "HUMAN_REJECT",
    "HUMAN_DEFER",
)


class RepresentativePilotError(ValueError):
    """Fail-closed M12D error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RepresentativePilotError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise RepresentativePilotError(f"json_root_not_object:{path}")
    return value


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _safe_root(path: Path) -> Path:
    resolved = path.resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise RepresentativePilotError(f"path_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise RepresentativePilotError(f"{code}:expected={expected!r}:actual={actual!r}")


def _assert_schema(name: str, value: Mapping[str, Any]) -> None:
    schema = read_json(SCHEMA_DIR / name)
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise RepresentativePilotError(f"schema_validation_failed:{name}:{location}:{first.message}")


def _safe_scan(value: Any, *, name: str) -> None:
    forbidden = {
        "response", "learner_response", "learner_responses", "prompt", "answer",
        "answer_key", "accepted_texts", "accepted_sequence", "private_scoring_contract",
        "model_texts", "session_id", "learner_ref", "submitted_at",
    }

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                lowered = str(key).casefold()
                if lowered in forbidden or lowered.endswith("_absolute_path"):
                    raise RepresentativePilotError(f"private_field_leak:{name}:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (len(node) > 2 and node[1:3] in {":\\", ":/"}):
                raise RepresentativePilotError(f"absolute_path_leak:{name}")

    walk(value)


def _expected_qa_status(origin: str) -> str:
    if origin == "REAL_LEARNER":
        return m12c.REAL_STATUS
    if origin == "TEST_FIXTURE":
        return m12c.TEST_STATUS
    raise RepresentativePilotError(f"evidence_origin_invalid:{origin}")


def _load_sources(input_root: Path, qa_root: Path, *, expected_origin: str) -> dict[str, Any]:
    source = _safe_root(input_root)
    qa = _safe_root(qa_root)
    if expected_origin not in EVIDENCE_ORIGINS:
        raise RepresentativePilotError(f"evidence_origin_invalid:{expected_origin}")
    manifest = read_json(source / "pilot_capture_manifest.private.json")
    capture = read_json(source / "pilot_evidence_capture_safe_report.json")
    registry = read_json(source / "pilot_attempt_registry.private.json")
    ledger = read_json(source / "pilot_progress_ledger.private.json")
    query = read_json(source / "pilot_progress_query_index.json")
    qa_report = read_json(qa / "real_evidence_qa_safe_report.json")
    source_bank = read_json(source / "runtime/source_m08/text_mode_session_bank.private.json")
    learner_payload = read_json(source / "runtime/authority_session/payload.json")

    _require(manifest.get("task_id"), m12.TASK_ID, "m12_manifest_task")
    _require(capture.get("task_id"), m12.TASK_ID, "m12_capture_task")
    _require(capture.get("mode"), "IMPORT", "m12_capture_mode")
    _require(capture.get("evidence_origin"), expected_origin, "m12_capture_origin")
    _require(qa_report.get("task_id"), m12c.TASK_ID, "m12c_task")
    _require(qa_report.get("evidence_origin"), expected_origin, "m12c_origin")
    _require(qa_report.get("validation_status"), _expected_qa_status(expected_origin), "m12c_status")
    _require(qa_report.get("stop_reason"), "NONE", "m12c_stop_reason")
    _require(manifest.get("selection", {}).get("selectable_item_count"), 184, "m12_selectable_items")
    _require(manifest.get("selection", {}).get("private_ready_unit_count"), 23, "m12_private_units")
    _require(manifest.get("selection", {}).get("private_ready_row_count"), 107, "m12_private_rows")
    _require(ledger.get("attempt_count"), len(registry.get("attempts", [])), "prior_registry_ledger_attempts")
    if int(ledger.get("attempt_count", 0)) < 1:
        raise RepresentativePilotError("representative_expansion_requires_prior_evidence")
    _require(query.get("attempt_count"), ledger.get("attempt_count"), "prior_query_ledger_attempts")
    _require(learner_payload.get("item_count"), 184, "learner_payload_item_count")
    _require(source_bank.get("item_count"), 192, "source_bank_item_count")
    _require(registry.get("session_bank_sha256"), m12.m08.sha256_value(source_bank), "prior_registry_bank_hash")
    return {
        "root": source,
        "qa_root": qa,
        "manifest": manifest,
        "capture": capture,
        "registry": registry,
        "ledger": ledger,
        "query": query,
        "qa_report": qa_report,
        "source_bank": source_bank,
        "learner_payload": learner_payload,
    }


def _pick_exact(rows: list[dict[str, Any]], *, skill: str, role: str) -> dict[str, Any]:
    matches = [row for row in rows if row.get("skill") == skill and row.get("item_role") == role]
    if not matches:
        raise RepresentativePilotError(f"balanced_item_missing:{skill}:{role}")
    return sorted(matches, key=lambda row: str(row["item_id"]))[0]


def _select_batch(source: Mapping[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    attempted_ids = {str(row["item_id"]) for row in source["ledger"].get("entries", [])}
    selectable = [
        dict(row)
        for row in source["query"].get("items", [])
        if str(row.get("item_id")) not in attempted_ids
        and row.get("grammar_unit_id") != DEFERRED_GRAMMAR_ID
    ]
    if len(selectable) < BATCH_SIZE:
        raise RepresentativePilotError("insufficient_unattempted_items_for_batch")
    priority_units: list[str] = []
    for row in source["qa_report"].get("iteration_queue", {}).get("items", []):
        grammar_id = str(row.get("grammar_unit_id") or "")
        if grammar_id and grammar_id != DEFERRED_GRAMMAR_ID and grammar_id not in priority_units:
            priority_units.append(grammar_id)
    for grammar_id in sorted({str(row["grammar_unit_id"]) for row in selectable}):
        if grammar_id not in priority_units:
            priority_units.append(grammar_id)
    chosen_units = priority_units[:4]
    if len(chosen_units) != 4:
        raise RepresentativePilotError(f"representative_unit_count_not_4:{chosen_units}")
    selected: list[dict[str, Any]] = []
    for index, grammar_id in enumerate(chosen_units):
        unit_rows = [row for row in selectable if row["grammar_unit_id"] == grammar_id]
        pairs = (("reading", "practice"), ("writing", "assessment")) if index % 2 == 0 else (("writing", "practice"), ("reading", "assessment"))
        for skill, role in pairs:
            selected.append(_pick_exact(unit_rows, skill=skill, role=role))
    item_ids = [str(row["item_id"]) for row in selected]
    if len(item_ids) != BATCH_SIZE or len(set(item_ids)) != BATCH_SIZE:
        raise RepresentativePilotError("representative_item_identity_not_8")
    skill_counts = Counter(str(row["skill"]) for row in selected)
    role_counts = Counter(str(row["item_role"]) for row in selected)
    unit_ids = sorted({str(row["grammar_unit_id"]) for row in selected})
    row_ids = sorted({str(row_id) for row in selected for row_id in row["canonical_egp_row_ids"]})
    if skill_counts != {"reading": 4, "writing": 4}:
        raise RepresentativePilotError(f"representative_skill_distribution_drift:{dict(skill_counts)}")
    if role_counts != {"practice": 4, "assessment": 4}:
        raise RepresentativePilotError(f"representative_role_distribution_drift:{dict(role_counts)}")
    if len(unit_ids) != 4:
        raise RepresentativePilotError(f"representative_unit_identity_not_4:{unit_ids}")
    return selected, {
        "batch_size": BATCH_SIZE,
        "grammar_unit_count": 4,
        "canonical_egp_row_count": len(row_ids),
        "skill_counts": {"reading": 4, "writing": 4},
        "role_counts": {"practice": 4, "assessment": 4},
        "item_ids": item_ids,
        "grammar_unit_ids": unit_ids,
        "canonical_egp_row_ids": row_ids,
        "selection_policy": "M12C_PRIORITY_UNITS_BALANCED_4X2",
    }


def _prior_summary(source: Mapping[str, Any]) -> dict[str, int]:
    summary = source["qa_report"]["evidence_summary"]
    return {
        "attempt_count": int(summary["attempt_count"]),
        "attempted_unit_count": int(summary["attempted_unit_count"]),
        "attempted_row_count": int(summary["attempted_row_count"]),
        "auto_pass_count": int(summary["auto_pass_count"]),
        "auto_fail_count": int(summary["auto_fail_count"]),
        "pending_human_review_count": int(summary["pending_human_review_count"]),
    }


def _build_report(
    *,
    mode: str,
    origin: str,
    prior: Mapping[str, int],
    selection: Mapping[str, Any],
    batch_attempt_count: int,
    cumulative_ledger: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not 0 <= batch_attempt_count <= BATCH_SIZE:
        raise RepresentativePilotError(f"batch_attempt_count_out_of_range:{batch_attempt_count}")
    remaining = BATCH_SIZE - batch_attempt_count
    if cumulative_ledger is None:
        cumulative_attempt_count = prior["attempt_count"]
        cumulative_unit_count = prior["attempted_unit_count"]
        cumulative_row_count = prior["attempted_row_count"]
        outcome_counts = {name: 0 for name in OUTCOMES}
        outcome_counts.update({
            "AUTO_PASS": prior["auto_pass_count"],
            "AUTO_FAIL": prior["auto_fail_count"],
            "PENDING_HUMAN_REVIEW": prior["pending_human_review_count"],
        })
    else:
        cumulative_attempt_count = int(cumulative_ledger["attempt_count"])
        cumulative_unit_count = int(cumulative_ledger["attempted_unit_count"])
        cumulative_row_count = int(cumulative_ledger["attempted_row_count"])
        raw_counts = cumulative_ledger.get("outcome_counts", {})
        outcome_counts = {name: int(raw_counts.get(name, 0)) for name in OUTCOMES}

    if mode == "PREPARE":
        status = PREPARE_STATUS
        stop_reason = "REAL_LEARNER_REPRESENTATIVE_BATCH_REQUIRED" if batch_attempt_count == 0 else "REAL_LEARNER_REPRESENTATIVE_BATCH_INCOMPLETE"
        next_step = NEXT_IMPORT
    elif remaining:
        status = PARTIAL_STATUS
        stop_reason = "REAL_LEARNER_REPRESENTATIVE_BATCH_INCOMPLETE"
        next_step = NEXT_IMPORT
    elif origin == "REAL_LEARNER":
        status = REAL_STATUS
        stop_reason = "NONE"
        next_step = NEXT_QA
    else:
        status = TEST_STATUS
        stop_reason = "REAL_LEARNER_REPRESENTATIVE_BATCH_REQUIRED"
        next_step = NEXT_IMPORT

    report = {
        "task_id": TASK_ID,
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": mode,
        "evidence_origin": origin,
        "prior_attempt_count": prior["attempt_count"],
        "batch_attempt_count": batch_attempt_count,
        "remaining_batch_attempt_count": remaining,
        "cumulative_attempt_count": cumulative_attempt_count,
        "cumulative_attempted_unit_count": cumulative_unit_count,
        "cumulative_attempted_row_count": cumulative_row_count,
        "outcome_counts": outcome_counts,
        "batch_selection": {
            "batch_size": selection["batch_size"],
            "grammar_unit_count": selection["grammar_unit_count"],
            "canonical_egp_row_count": selection["canonical_egp_row_count"],
            "skill_counts": selection["skill_counts"],
            "role_counts": selection["role_counts"],
        },
        "claim_boundaries": {
            "metadata_only_report": True,
            "private_responses_included": False,
            "learner_identity_included": False,
            "test_fixture_counted_as_real_evidence": False,
            "canonical_authority_write": False,
            "canonical_egp_mapping_changed": False,
            "public_delivery": False,
            "production_runtime_enabled": False,
            "a2_content_promoted": False,
            "audio_or_recording_processed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
        },
        "validation_status": status,
        "stop_reason": stop_reason,
        "next_short_step": next_step,
        "errors": [],
    }
    _safe_scan(report, name="m12d_safe_report")
    _assert_schema("e4s_a1v1_m12d_representative_pilot_safe_report.schema.json", report)
    return report


def _validate_batch_registry(
    manifest: Mapping[str, Any],
    prior_registry: Mapping[str, Any],
    batch_registry: Mapping[str, Any],
) -> list[dict[str, Any]]:
    contract = manifest["attempt_registry_contract"]
    _require(batch_registry.get("task_id"), contract["task_id"], "batch_registry_task")
    _require(batch_registry.get("schema_version"), contract["schema_version"], "batch_registry_schema")
    _require(batch_registry.get("private_local_only"), True, "batch_registry_private")
    _require(batch_registry.get("session_bank_sha256"), contract["session_bank_sha256"], "batch_registry_bank_hash")
    if batch_registry.get("learner_ref") != prior_registry.get("learner_ref"):
        raise RepresentativePilotError("batch_registry_learner_ref_mismatch")
    attempts = batch_registry.get("attempts")
    if not isinstance(attempts, list):
        raise RepresentativePilotError("batch_registry_attempts_not_array")
    if not 1 <= len(attempts) <= BATCH_SIZE:
        raise RepresentativePilotError(f"batch_registry_attempt_count_out_of_range:{len(attempts)}")
    item_ids = [str(row.get("item_id") or "") for row in attempts]
    if len(set(item_ids)) != len(item_ids):
        raise RepresentativePilotError("batch_registry_duplicate_item")
    allowed = set(contract["allowed_item_ids"])
    unknown = sorted(set(item_ids) - allowed)
    if unknown:
        raise RepresentativePilotError(f"batch_registry_nonbatch_items:{unknown}")
    prior_ids = {str(row.get("item_id")) for row in prior_registry.get("attempts", [])}
    duplicates = sorted(set(item_ids) & prior_ids)
    if duplicates:
        raise RepresentativePilotError(f"batch_registry_duplicates_prior_items:{duplicates}")
    if any(item_id.startswith(DEFERRED_GRAMMAR_ID) for item_id in item_ids):
        raise RepresentativePilotError("batch_registry_deferred_will_item")
    return [deepcopy(row) for row in attempts]


def _attempt_replay_signature(attempt: Mapping[str, Any]) -> bytes:
    value = deepcopy(dict(attempt))
    value.pop("attempt_sequence", None)
    return canonical_bytes(value)


def _merge_batch_registries(
    manifest: Mapping[str, Any],
    prior_registry: Mapping[str, Any],
    existing_registry: Mapping[str, Any] | None,
    incoming_registry: Mapping[str, Any],
) -> dict[str, Any]:
    incoming = _validate_batch_registry(manifest, prior_registry, incoming_registry)
    existing: list[dict[str, Any]] = []
    if existing_registry is not None:
        existing = _validate_batch_registry(manifest, prior_registry, existing_registry)
    by_id = {str(row["item_id"]): deepcopy(row) for row in existing}
    for row in incoming:
        item_id = str(row["item_id"])
        if item_id in by_id and _attempt_replay_signature(by_id[item_id]) != _attempt_replay_signature(row):
            raise RepresentativePilotError(f"batch_registry_conflicting_replay:{item_id}")
        by_id[item_id] = deepcopy(row)
    order = {item_id: index for index, item_id in enumerate(manifest["batch_selection"]["item_ids"])}
    merged_attempts = sorted(by_id.values(), key=lambda row: order[str(row["item_id"])])
    if not 1 <= len(merged_attempts) <= BATCH_SIZE:
        raise RepresentativePilotError(f"merged_batch_attempt_count_out_of_range:{len(merged_attempts)}")
    merged = deepcopy(dict(incoming_registry))
    merged["attempts"] = merged_attempts
    return merged


def _cumulative_artifacts(source: Mapping[str, Any], batch_attempts: list[dict[str, Any]], *, origin: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    cumulative = deepcopy(source["registry"])
    cumulative["session_id"] = f"m12d-cumulative-{origin.casefold()}"
    attempts = [deepcopy(row) for row in source["registry"]["attempts"]] + [deepcopy(row) for row in batch_attempts]
    for sequence, attempt in enumerate(attempts, start=1):
        attempt["attempt_sequence"] = sequence
    cumulative["attempts"] = attempts
    ledger, progress_report, query = m12.m08.build_progress_artifacts(source["source_bank"], cumulative)
    if int(ledger["attempt_count"]) != int(source["ledger"]["attempt_count"]) + len(batch_attempts):
        raise RepresentativePilotError("cumulative_attempt_accounting_drift")
    return cumulative, ledger, progress_report, query


def _resume_state(selection: Mapping[str, Any], captured_attempts: list[dict[str, Any]]) -> dict[str, Any]:
    captured = [str(row["item_id"]) for row in captured_attempts]
    allowed = list(selection["item_ids"])
    return {
        "task_id": TASK_ID,
        "captured_item_ids": captured,
        "remaining_item_ids": [item_id for item_id in allowed if item_id not in set(captured)],
        "captured_attempt_count": len(captured),
        "remaining_attempt_count": BATCH_SIZE - len(captured),
    }


def _representative_session_html() -> str:
    return """<!doctype html>
<html lang="en"><meta charset="utf-8"><title>A1/A1+ Representative Pilot</title>
<body><h1>A1/A1+ Representative Pilot Batch</h1>
<p>Local-only. Previously captured items are hidden; responses remain private.</p>
<label>Learner ref <input id="learner" value="learner-local-001"></label>
<label>Session ID <input id="session" value="m12d-representative-session"></label>
<select id="item"></select><div id="meta"></div><h2 id="prompt"></h2>
<div id="context"></div><div id="response"></div>
<button id="save">Save attempt</button><button id="export">Download attempt registry</button>
<pre id="status"></pre><script>
let payload, items=[]; const storageKey='e4s-a1v1-m12d-current-attempts'; let attempts=new Map();
async function load(){payload=await (await fetch('./payload.json')).json();const resume=await (await fetch('./resume_state.json')).json();const captured=new Set(resume.captured_item_ids||[]);items=payload.items.filter(x=>!captured.has(x.item_id));const saved=JSON.parse(localStorage.getItem(storageKey)||'[]').filter(x=>items.some(i=>i.item_id===x.item_id));attempts=new Map(saved.map(x=>[x.item_id,x]));const s=document.querySelector('#item');s.innerHTML='';items.forEach((x,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${i+1}. ${x.skill} | ${x.item_role} | ${x.grammar_unit_id}`;s.appendChild(o)});s.onchange=render;if(items.length){render();status(`Remaining ${items.length}; saved in this session ${attempts.size}.`)}else{document.querySelector('#save').disabled=true;status('All 8 representative items are already captured.')}}
function status(v){document.querySelector('#status').textContent=v}function current(){return items[Number(document.querySelector('#item').value)]}
function render(){const x=current();if(!x)return;document.querySelector('#meta').textContent=`${x.internal_stage} | ${x.evidence_dimension} | ${x.task_type}`;document.querySelector('#prompt').textContent=x.prompt;document.querySelector('#context').textContent=x.context?JSON.stringify(x.context):'';const r=document.querySelector('#response');r.innerHTML='';if(x.response_mode==='select_one'){x.options.forEach(v=>{const l=document.createElement('label');const i=document.createElement('input');i.type='radio';i.name='response';i.value=v;l.append(i,document.createTextNode(v));r.append(l,document.createElement('br'))})}else if(x.response_mode==='ordered_tokens'||x.response_mode==='ordered_morphemes'){const source=x.supplied_tokens||x.supplied_morphemes||[];const p=document.createElement('p');p.textContent='Supplied: '+source.join(' | ');const t=document.createElement('textarea');t.id='text-response';t.placeholder='Enter ordered parts separated by |';r.append(p,t)}else{const t=document.createElement('textarea');t.id='text-response';t.placeholder='Type your response';r.append(t)}}
function readResponse(){const x=current();if(x.response_mode==='select_one'){const i=document.querySelector('input[name=response]:checked');return i?i.value:''}const v=(document.querySelector('#text-response')||{}).value||'';return (x.response_mode==='ordered_tokens'||x.response_mode==='ordered_morphemes')?v.split('|').map(s=>s.trim()).filter(Boolean):v}
function emptyReview(){return {decision:'PENDING',reviewer_id:null,reviewed_at:null,criteria:{grammar_target_match:null,meaning_matches_context:null,complete_response:null},notes:null}}
function save(){const x=current();const row={item_id:x.item_id,attempt_sequence:1,response:readResponse(),submitted_at:new Date().toISOString(),operator_review:emptyReview()};attempts.set(x.item_id,row);localStorage.setItem(storageKey,JSON.stringify([...attempts.values()]));status(`Saved ${attempts.size} new attempt(s).`)}
function exportRegistry(){const value={task_id:payload.task_id,schema_version:'e4s.a1v1.text_mode_attempt_registry.v1',private_local_only:true,session_bank_sha256:payload.session_bank_sha256,session_id:document.querySelector('#session').value,learner_ref:document.querySelector('#learner').value,attempts:[...attempts.values()]};const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));a.download='m08_text_mode_attempt_registry.private.json';a.click()}
document.querySelector('#save').onclick=save;document.querySelector('#export').onclick=exportRegistry;load();
</script></body></html>"""


def prepare_batch(
    input_root: Path,
    qa_root: Path,
    output_root: Path,
    *,
    expected_origin: str,
    port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    target = _safe_root(output_root)
    if port < 1024 or port > 65535:
        raise RepresentativePilotError(f"port_out_of_range:{port}")
    source = _load_sources(input_root, qa_root, expected_origin=expected_origin)
    _, selection = _select_batch(source)
    prior = _prior_summary(source)
    source_bank_hash = m12.m08.sha256_value(source["source_bank"])
    learner_by_id = {str(row["item_id"]): row for row in source["learner_payload"]["items"]}
    batch_items = [deepcopy(learner_by_id[item_id]) for item_id in selection["item_ids"]]
    if len(batch_items) != BATCH_SIZE:
        raise RepresentativePilotError("learner_batch_item_count_not_8")
    batch_payload = deepcopy(source["learner_payload"])
    batch_payload["item_count"] = BATCH_SIZE
    batch_payload["items"] = batch_items
    batch_payload["representative_batch_task_id"] = TASK_ID
    batch_payload["representative_batch_item_ids"] = list(selection["item_ids"])
    manifest = {
        "task_id": TASK_ID,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "private_local_only": True,
        "evidence_origin": expected_origin,
        "source_hashes": {
            "m12_capture_manifest_sha256": sha256_value(source["manifest"]),
            "m12_capture_report_sha256": sha256_value(source["capture"]),
            "m12_prior_registry_sha256": sha256_value(source["registry"]),
            "m12_prior_ledger_sha256": sha256_value(source["ledger"]),
            "m12c_qa_report_sha256": sha256_value(source["qa_report"]),
            "m08_source_bank_sha256": source_bank_hash,
            "batch_payload_sha256": sha256_value(batch_payload),
        },
        "prior_evidence": prior,
        "batch_selection": selection,
        "runtime": {
            "allowed_host": DEFAULT_HOST,
            "default_port": port,
            "session_entrypoint": "session/index.html",
            "network_submission_enabled": False,
        },
        "attempt_registry_contract": {
            "task_id": m12.m08.TASK_ID,
            "schema_version": "e4s.a1v1.text_mode_attempt_registry.v1",
            "session_bank_sha256": source_bank_hash,
            "minimum_attempt_count": 1,
            "maximum_attempt_count": BATCH_SIZE,
            "completion_attempt_count": BATCH_SIZE,
            "allowed_item_ids": list(selection["item_ids"]),
            "duplicate_prior_item_allowed": False,
            "deferred_item_submission_allowed": False,
        },
        "claim_boundaries": {
            "private_local_only": True,
            "prior_real_responses_exposed": False,
            "canonical_authority_write": False,
            "public_delivery": False,
            "a2_content_promoted": False,
            "audio_or_recording_processed": False,
            "learner_mastery_claimed": False,
        },
        "batch_status": "READY_FOR_REPRESENTATIVE_PILOT_BATCH",
    }
    _assert_schema("e4s_a1v1_m12d_representative_pilot_batch_manifest.schema.json", manifest)

    existing_path = target / "representative_batch_attempt_registry.private.json"
    existing_registry = read_json(existing_path) if existing_path.is_file() else None
    existing_attempts = _validate_batch_registry(manifest, source["registry"], existing_registry) if existing_registry else []
    cumulative_ledger = None
    if existing_attempts:
        _, cumulative_ledger, _, _ = _cumulative_artifacts(source, existing_attempts, origin=expected_origin)

    session = target / "session"
    session.mkdir(parents=True, exist_ok=True)
    (session / "index.html").write_text(_representative_session_html(), encoding="utf-8")
    write_json_atomic(session / "payload.json", batch_payload)
    write_json_atomic(session / "resume_state.json", _resume_state(selection, existing_attempts))
    template = m12.m08.empty_attempt_registry(source["source_bank"])
    report = _build_report(
        mode="PREPARE",
        origin=expected_origin,
        prior=prior,
        selection=selection,
        batch_attempt_count=len(existing_attempts),
        cumulative_ledger=cumulative_ledger,
    )
    write_json_atomic(target / "representative_batch_manifest.private.json", manifest)
    write_json_atomic(target / "representative_batch_attempt_registry.template.json", template)
    write_json_atomic(target / "representative_batch_readiness_safe_report.json", report)
    return {
        "manifest": manifest,
        "template": template,
        "safe_report": report,
        "batch_payload": batch_payload,
        "resume_state": _resume_state(selection, existing_attempts),
        "source": source,
    }


def import_batch(
    input_root: Path,
    qa_root: Path,
    output_root: Path,
    batch_registry_path: Path,
    *,
    expected_origin: str,
    port: int = DEFAULT_PORT,
) -> dict[str, Any]:
    target = _safe_root(output_root)
    prepared = prepare_batch(input_root, qa_root, target, expected_origin=expected_origin, port=port)
    manifest = prepared["manifest"]
    source = prepared["source"]
    incoming_registry = read_json(batch_registry_path)
    existing_path = target / "representative_batch_attempt_registry.private.json"
    existing_registry = read_json(existing_path) if existing_path.is_file() else None
    merged_registry = _merge_batch_registries(manifest, source["registry"], existing_registry, incoming_registry)
    batch_attempts = _validate_batch_registry(manifest, source["registry"], merged_registry)
    cumulative, ledger, progress_report, query = _cumulative_artifacts(source, batch_attempts, origin=expected_origin)
    report = _build_report(
        mode="IMPORT",
        origin=expected_origin,
        prior=_prior_summary(source),
        selection=manifest["batch_selection"],
        batch_attempt_count=len(batch_attempts),
        cumulative_ledger=ledger,
    )
    write_json_atomic(existing_path, merged_registry)
    write_json_atomic(target / "cumulative_attempt_registry.private.json", cumulative)
    write_json_atomic(target / "cumulative_progress_ledger.private.json", ledger)
    write_json_atomic(target / "cumulative_progress_query_index.json", query)
    write_json_atomic(target / "representative_pilot_expansion_safe_report.json", report)
    write_json_atomic(target / "session/resume_state.json", _resume_state(manifest["batch_selection"], batch_attempts))
    return {
        "manifest": manifest,
        "batch_registry": merged_registry,
        "cumulative_registry": cumulative,
        "ledger": ledger,
        "progress_report": progress_report,
        "query": query,
        "safe_report": report,
    }


def serve_batch(output_root: Path, *, host: str, port: int, dry_run: bool) -> int:
    root = _safe_root(output_root)
    if host != DEFAULT_HOST:
        raise RepresentativePilotError(f"non_localhost_bind_forbidden:{host}")
    if port < 1024 or port > 65535:
        raise RepresentativePilotError(f"port_out_of_range:{port}")
    manifest = read_json(root / "representative_batch_manifest.private.json")
    _assert_schema("e4s_a1v1_m12d_representative_pilot_batch_manifest.schema.json", manifest)
    url = f"http://{host}:{port}/session/index.html"
    if dry_run:
        resume = read_json(root / "session/resume_state.json")
        print(json.dumps({"batch_status": manifest["batch_status"], "remaining_attempt_count": resume["remaining_attempt_count"], "url": url}, sort_keys=True))
        return 0
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving representative pilot batch at {url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    prepare.add_argument("--qa-root", type=Path, default=DEFAULT_QA_ROOT)
    prepare.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    prepare.add_argument("--expected-origin", choices=sorted(EVIDENCE_ORIGINS), required=True)
    prepare.add_argument("--port", type=int, default=DEFAULT_PORT)
    import_cmd = sub.add_parser("import-batch")
    import_cmd.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
    import_cmd.add_argument("--qa-root", type=Path, default=DEFAULT_QA_ROOT)
    import_cmd.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    import_cmd.add_argument("--batch-registry", type=Path, required=True)
    import_cmd.add_argument("--expected-origin", choices=sorted(EVIDENCE_ORIGINS), required=True)
    import_cmd.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve = sub.add_parser("serve")
    serve.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    serve.add_argument("--host", default=DEFAULT_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_batch(args.input_root, args.qa_root, args.output_root, expected_origin=args.expected_origin, port=args.port)
        elif args.command == "import-batch":
            result = import_batch(args.input_root, args.qa_root, args.output_root, args.batch_registry, expected_origin=args.expected_origin, port=args.port)
        else:
            return serve_batch(args.output_root, host=args.host, port=args.port, dry_run=args.dry_run)
        report = result["safe_report"]
        print(json.dumps({
            "mode": report["mode"],
            "evidence_origin": report["evidence_origin"],
            "prior_attempt_count": report["prior_attempt_count"],
            "batch_attempt_count": report["batch_attempt_count"],
            "remaining_batch_attempt_count": report["remaining_batch_attempt_count"],
            "cumulative_attempt_count": report["cumulative_attempt_count"],
            "cumulative_attempted_unit_count": report["cumulative_attempted_unit_count"],
            "cumulative_attempted_row_count": report["cumulative_attempted_row_count"],
            "validation_status": report["validation_status"],
            "stop_reason": report["stop_reason"],
            "next_short_step": report["next_short_step"],
        }, ensure_ascii=False, sort_keys=True))
        return 0
    except (
        RepresentativePilotError,
        m12.PilotCaptureError,
        m12c.EvidenceQAError,
        m12.m11c.AuthorityRuntimeError,
        m12.m08.TextModeSessionError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
