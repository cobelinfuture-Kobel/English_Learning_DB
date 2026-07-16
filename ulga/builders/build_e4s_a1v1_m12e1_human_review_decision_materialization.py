#!/usr/bin/env python3
"""Prepare and apply private human-review decisions for M12E pending evidence.

Only FEATURE_RUBRIC items with PENDING_HUMAN_REVIEW are exposed in a localhost
workbench. Decisions are materialized into a private copy of the cumulative
attempt registry, the M08 ledger/query are recomputed, and M12E QA is rerun.
Deterministic AUTO_PASS/AUTO_FAIL items are never editable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
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

from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12_real_learner_pilot_evidence_capture as m12  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12e_representative_pilot_evidence_qa as m12e  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12d_representative_pilot_expansion as m12d  # noqa: E402

TASK_ID = "E4S-A1V1-M12E1_HumanReviewDecisionMaterialization"
QUEUE_SCHEMA_VERSION = "e4s.a1v1.m12e1.human_review_queue.v1"
DECISION_SCHEMA_VERSION = "e4s.a1v1.m12e1.human_review_decisions.v1"
REPORT_SCHEMA_VERSION = "e4s.a1v1.m12e1.human_review_safe_report.v1"
PREPARE_STATUS = "PASS_M12E1_HUMAN_REVIEW_WORKBENCH_READY"
PARTIAL_STATUS = "PASS_M12E1_HUMAN_REVIEW_PARTIAL"
COMPLETE_STATUS = "PASS_M12E1_HUMAN_REVIEW_DECISIONS_MATERIALIZED"
NEXT_SELF = TASK_ID
DEFAULT_INPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12"
DEFAULT_QA_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12c"
DEFAULT_REPRESENTATIVE_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12d"
DEFAULT_M12E_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12e"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / ".local/e4s_a1v1/pilot/m12e1"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8773
SCHEMA_DIR = REPO_ROOT / "ulga/schemas"
OUTCOMES = m08.OUTCOMES
CRITERIA_KEYS = (
    "grammar_target_match",
    "meaning_matches_context",
    "complete_response",
)


class HumanReviewMaterializationError(ValueError):
    """Fail-closed M12E1 error."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_value(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HumanReviewMaterializationError(f"json_unreadable:{path}:{exc}") from exc
    if not isinstance(value, dict):
        raise HumanReviewMaterializationError(f"json_root_not_object:{path}")
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
        raise HumanReviewMaterializationError(f"path_outside_local:{resolved}")
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _schema(name: str) -> dict[str, Any]:
    return read_json(SCHEMA_DIR / name)


def _assert_schema(name: str, value: Mapping[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(_schema(name)).iter_errors(value),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        first = errors[0]
        location = ".".join(str(part) for part in first.absolute_path) or "$"
        raise HumanReviewMaterializationError(
            f"schema_validation_failed:{name}:{location}:{first.message}"
        )


def _require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise HumanReviewMaterializationError(
            f"{code}:expected={expected!r}:actual={actual!r}"
        )


def _safe_scan(value: Any, *, name: str) -> None:
    forbidden = {
        "response", "learner_response", "learner_responses", "prompt", "context",
        "answer", "answer_key", "accepted_texts", "accepted_sequence",
        "private_scoring_contract", "model_texts", "rubric", "learner_ref",
        "session_id", "submitted_at", "reviewer_id", "reviewed_at", "notes",
    }

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                lowered = str(key).casefold()
                if lowered in forbidden or lowered.endswith("_absolute_path"):
                    raise HumanReviewMaterializationError(
                        f"private_field_leak:{name}:{key}"
                    )
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
        elif isinstance(node, str):
            if Path(node).is_absolute() or (
                len(node) > 2 and node[1:3] in {":\\", ":/"}
            ):
                raise HumanReviewMaterializationError(f"absolute_path_leak:{name}")

    walk(value)


def _expected_m12e_status(origin: str) -> str:
    if origin == "REAL_LEARNER":
        return m12e.REAL_STATUS
    if origin == "TEST_FIXTURE":
        return m12e.TEST_STATUS
    raise HumanReviewMaterializationError(f"evidence_origin_invalid:{origin}")


def _load_sources(
    input_root: Path,
    representative_root: Path,
    m12e_root: Path,
    *,
    expected_origin: str,
) -> dict[str, Any]:
    source = _safe_root(input_root)
    representative = _safe_root(representative_root)
    qa = _safe_root(m12e_root)
    if expected_origin not in {"REAL_LEARNER", "TEST_FIXTURE"}:
        raise HumanReviewMaterializationError(
            f"evidence_origin_invalid:{expected_origin}"
        )

    report = read_json(qa / "representative_evidence_qa_safe_report.json")
    manifest = read_json(representative / "representative_batch_manifest.private.json")
    expansion_report = read_json(
        representative / "representative_pilot_expansion_safe_report.json"
    )
    registry = read_json(
        representative / "cumulative_attempt_registry.private.json"
    )
    ledger = read_json(
        representative / "cumulative_progress_ledger.private.json"
    )
    query = read_json(
        representative / "cumulative_progress_query_index.json"
    )
    bank = read_json(
        source / "runtime/source_m08/text_mode_session_bank.private.json"
    )

    _require(report.get("task_id"), m12e.TASK_ID, "m12e_task")
    _require(report.get("evidence_origin"), expected_origin, "m12e_origin")
    _require(
        report.get("validation_status"),
        _expected_m12e_status(expected_origin),
        "m12e_status",
    )
    _require(
        report.get("stop_reason"),
        "HUMAN_REVIEW_DECISIONS_REQUIRED",
        "m12e_stop_reason",
    )
    _require(report.get("next_short_step"), TASK_ID, "m12e_next_step")
    pending_count = int(
        report.get("evidence_summary", {}).get(
            "pending_human_review_count", 0
        )
    )
    if pending_count < 1:
        raise HumanReviewMaterializationError("m12e_pending_count_not_positive")

    _require(manifest.get("task_id"), m12d.TASK_ID, "m12d_manifest_task")
    _require(manifest.get("evidence_origin"), expected_origin, "m12d_origin")
    _require(expansion_report.get("task_id"), m12d.TASK_ID, "m12d_report_task")
    _require(registry.get("task_id"), m08.TASK_ID, "registry_task")
    _require(ledger.get("task_id"), m08.TASK_ID, "ledger_task")
    _require(query.get("task_id"), m08.TASK_ID, "query_task")
    _require(registry.get("session_bank_sha256"), m08.sha256_value(bank), "bank_hash")
    _require(ledger.get("attempt_count"), len(registry.get("attempts", [])), "registry_ledger_count")
    _require(query.get("attempt_count"), ledger.get("attempt_count"), "query_ledger_count")

    source_hashes = report.get("source_hashes", {})
    _require(
        source_hashes.get("cumulative_registry_sha256"),
        m12e.sha256_value(registry),
        "m12e_registry_hash",
    )
    _require(
        source_hashes.get("cumulative_ledger_sha256"),
        m12e.sha256_value(ledger),
        "m12e_ledger_hash",
    )
    _require(
        source_hashes.get("cumulative_query_sha256"),
        m12e.sha256_value(query),
        "m12e_query_hash",
    )

    pending_entries = [
        deepcopy(row)
        for row in ledger.get("entries", [])
        if row.get("outcome") == "PENDING_HUMAN_REVIEW"
    ]
    _require(len(pending_entries), pending_count, "pending_entry_count")
    pending_ids = {str(row["item_id"]) for row in pending_entries}
    query_pending = {
        str(row["item_id"])
        for row in query.get("items", [])
        if row.get("outcome") == "PENDING_HUMAN_REVIEW"
    }
    _require(query_pending, pending_ids, "query_pending_identity")

    bank_by_id = {str(row["item_id"]): row for row in bank.get("items", [])}
    attempts_by_id = {
        str(row["item_id"]): row for row in registry.get("attempts", [])
    }
    for entry in pending_entries:
        item_id = str(entry["item_id"])
        item = bank_by_id.get(item_id)
        attempt = attempts_by_id.get(item_id)
        if item is None or attempt is None:
            raise HumanReviewMaterializationError(
                f"pending_source_join_missing:{item_id}"
            )
        if item.get("private_scoring_contract", {}).get("scoring_mode") != "FEATURE_RUBRIC":
            raise HumanReviewMaterializationError(
                f"pending_non_rubric_item:{item_id}"
            )
        _require(
            attempt.get("operator_review", {}).get("decision"),
            "PENDING",
            f"pending_review_state:{item_id}",
        )

    return {
        "input_root": source,
        "representative_root": representative,
        "m12e_root": qa,
        "report": report,
        "manifest": manifest,
        "expansion_report": expansion_report,
        "registry": registry,
        "ledger": ledger,
        "query": query,
        "bank": bank,
        "pending_entries": sorted(
            pending_entries, key=lambda row: str(row["item_id"])
        ),
        "bank_by_id": bank_by_id,
        "attempts_by_id": attempts_by_id,
    }


def _decision_template(item_id: str) -> dict[str, Any]:
    return {
        "item_id": item_id,
        "decision": "PENDING",
        "criteria": {key: None for key in CRITERIA_KEYS},
        "notes": None,
    }


def _build_queue(source: Mapping[str, Any], *, expected_origin: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for entry in source["pending_entries"]:
        item_id = str(entry["item_id"])
        item = source["bank_by_id"][item_id]
        attempt = source["attempts_by_id"][item_id]
        items.append(
            {
                "item_id": item_id,
                "grammar_unit_id": item["grammar_unit_id"],
                "canonical_egp_row_ids": list(item["canonical_egp_row_ids"]),
                "internal_stage": item["internal_stage"],
                "skill": item["skill"],
                "item_role": item["item_role"],
                "evidence_dimension": item["evidence_dimension"],
                "task_type": item["task_type"],
                "learner_response": deepcopy(attempt["response"]),
                "submitted_at": attempt["submitted_at"],
                "learner_contract": deepcopy(item["learner_contract"]),
                "private_scoring_contract": deepcopy(
                    item["private_scoring_contract"]
                ),
                "current_operator_review": deepcopy(
                    attempt["operator_review"]
                ),
                "decision_template": _decision_template(item_id),
            }
        )
    queue = {
        "task_id": TASK_ID,
        "schema_version": QUEUE_SCHEMA_VERSION,
        "private_local_only": True,
        "evidence_origin": expected_origin,
        "source_hashes": {
            "m12e_report_sha256": sha256_value(source["report"]),
            "m12d_manifest_sha256": sha256_value(source["manifest"]),
            "m12d_report_sha256": sha256_value(source["expansion_report"]),
            "cumulative_registry_sha256": sha256_value(source["registry"]),
            "cumulative_ledger_sha256": sha256_value(source["ledger"]),
            "source_bank_sha256": sha256_value(source["bank"]),
        },
        "pending_item_count": len(items),
        "items": items,
        "items_sha256": sha256_value(items),
        "claim_boundaries": {
            "private_local_only": True,
            "contains_learner_responses": True,
            "contains_private_scoring_rubrics": True,
            "deterministic_items_editable": False,
            "canonical_authority_write": False,
            "public_delivery": False,
            "a2_content_promoted": False,
            "audio_or_recording_processed": False,
            "learner_mastery_claimed": False,
        },
    }
    _assert_schema(
        "e4s_a1v1_m12e1_human_review_queue.schema.json", queue
    )
    return queue


def _decision_registry_template(queue: Mapping[str, Any]) -> dict[str, Any]:
    value = {
        "task_id": TASK_ID,
        "schema_version": DECISION_SCHEMA_VERSION,
        "private_local_only": True,
        "source_review_queue_sha256": sha256_value(queue),
        "reviewer_id": None,
        "reviewed_at": None,
        "decisions": [
            deepcopy(row["decision_template"])
            for row in queue["items"]
        ],
    }
    _assert_schema(
        "e4s_a1v1_m12e1_human_review_decisions.schema.json", value
    )
    return value


def _outcome_counts(ledger: Mapping[str, Any]) -> dict[str, int]:
    counter = Counter(str(row.get("outcome")) for row in ledger.get("entries", []))
    return {outcome: counter[outcome] for outcome in OUTCOMES}


def _safe_report(
    *,
    mode: str,
    origin: str,
    source_pending: int,
    materialized: int,
    remaining: int,
    ledger: Mapping[str, Any],
    resolved_m12e: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if source_pending != materialized + remaining:
        raise HumanReviewMaterializationError(
            "human_review_decision_accounting_drift"
        )
    if mode == "PREPARE":
        status = PREPARE_STATUS
        stop_reason = "HUMAN_REVIEW_DECISIONS_REQUIRED"
        next_step = NEXT_SELF
        resolved_summary = None
    else:
        if resolved_m12e is None:
            raise HumanReviewMaterializationError("resolved_m12e_missing")
        resolved_summary = {
            "validation_status": resolved_m12e["validation_status"],
            "quality_state": resolved_m12e["quality_gate"]["state"],
            "pending_human_review_count": resolved_m12e["evidence_summary"]["pending_human_review_count"],
            "auto_fail_count": resolved_m12e["evidence_summary"]["auto_fail_count"],
            "next_short_step": resolved_m12e["next_short_step"],
            "stop_reason": resolved_m12e["stop_reason"],
        }
        if remaining:
            status = PARTIAL_STATUS
            stop_reason = "HUMAN_REVIEW_DECISIONS_REQUIRED"
            next_step = NEXT_SELF
        else:
            status = COMPLETE_STATUS
            stop_reason = resolved_m12e["stop_reason"]
            next_step = resolved_m12e["next_short_step"]
    report = {
        "task_id": TASK_ID,
        "schema_version": REPORT_SCHEMA_VERSION,
        "mode": mode,
        "evidence_origin": origin,
        "source_pending_count": source_pending,
        "materialized_decision_count": materialized,
        "remaining_pending_count": remaining,
        "outcome_counts": _outcome_counts(ledger),
        "resolved_m12e": resolved_summary,
        "claim_boundaries": {
            "metadata_only_report": True,
            "private_responses_included": False,
            "learner_identity_included": False,
            "reviewer_identity_included": False,
            "deterministic_outcomes_overridden": False,
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
    _safe_scan(report, name="m12e1_safe_report")
    _assert_schema(
        "e4s_a1v1_m12e1_human_review_safe_report.schema.json", report
    )
    return report


def _workbench_html() -> str:
    return """<!doctype html>
<html lang="en"><meta charset="utf-8"><title>M12E1 Human Review</title>
<style>body{font-family:system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem}.card{border:1px solid #999;padding:1rem;margin:1rem 0}pre{white-space:pre-wrap;background:#f3f3f3;padding:.75rem}label{display:block;margin:.5rem 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:1rem}</style>
<body><h1>M12E1 Private Human Review</h1><p>Localhost-only. Only pending FEATURE_RUBRIC items are shown. Deterministic outcomes cannot be edited.</p>
<label>Reviewer ID <input id="reviewer" value="operator-local"></label><div id="items"></div><button id="download">Download decisions</button><pre id="status"></pre>
<script>
let queue;
const criteria=['grammar_target_match','meaning_matches_context','complete_response'];
function esc(v){return JSON.stringify(v,null,2)}
async function load(){queue=await (await fetch('./review_queue.private.json')).json();const root=document.querySelector('#items');queue.items.forEach((x,i)=>{const card=document.createElement('section');card.className='card';card.dataset.item=x.item_id;card.innerHTML=`<h2>${i+1}. ${x.item_id}</h2><p>${x.grammar_unit_id} | ${x.skill} | ${x.item_role} | ${x.task_type}</p><div class="grid"><div><h3>Prompt/context</h3><pre>${esc(x.learner_contract)}</pre><h3>Learner response</h3><pre>${esc(x.learner_response)}</pre></div><div><h3>Rubric/model evidence</h3><pre>${esc(x.private_scoring_contract)}</pre></div></div><label>Decision <select class="decision"><option>PENDING</option><option>APPROVE</option><option>REJECT</option><option>DEFER</option></select></label>${criteria.map(k=>`<label>${k} <select class="criterion" data-key="${k}"><option value="null">Unset</option><option value="true">Yes</option><option value="false">No</option></select></label>`).join('')}<label>Notes <textarea class="notes"></textarea></label>`;root.append(card)});status(`Loaded ${queue.pending_item_count} pending item(s).`)}
function status(v){document.querySelector('#status').textContent=v}
function tri(v){return v==='true'?true:v==='false'?false:null}
function download(){const reviewer=document.querySelector('#reviewer').value.trim();const decisions=[...document.querySelectorAll('.card')].map(card=>{const c={};card.querySelectorAll('.criterion').forEach(x=>c[x.dataset.key]=tri(x.value));return {item_id:card.dataset.item,decision:card.querySelector('.decision').value,criteria:c,notes:card.querySelector('.notes').value.trim()||null}});const materialized=decisions.filter(x=>x.decision!=='PENDING').length;const value={task_id:queue.task_id,schema_version:'e4s.a1v1.m12e1.human_review_decisions.v1',private_local_only:true,source_review_queue_sha256:null,reviewer_id:materialized?reviewer:null,reviewed_at:materialized?new Date().toISOString():null,decisions};crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(queue))).then(()=>{value.source_review_queue_sha256=queue.__canonical_sha256||'';});value.source_review_queue_sha256=document.body.dataset.queueHash||'';fetch('./decision_template.private.json').then(r=>r.json()).then(t=>{value.source_review_queue_sha256=t.source_review_queue_sha256;const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)],{type:'application/json'}));a.download='m12e1_human_review_decisions.private.json';a.click();status(`Downloaded ${materialized} materialized decision(s).`)})}
document.querySelector('#download').onclick=download;load();
</script></body></html>"""


def prepare_workbench(
    input_root: Path,
    representative_root: Path,
    m12e_root: Path,
    output_root: Path,
    *,
    expected_origin: str,
) -> dict[str, Any]:
    target = _safe_root(output_root)
    source = _load_sources(
        input_root,
        representative_root,
        m12e_root,
        expected_origin=expected_origin,
    )
    queue = _build_queue(source, expected_origin=expected_origin)
    template = _decision_registry_template(queue)
    workbench = target / "workbench"
    workbench.mkdir(parents=True, exist_ok=True)
    (workbench / "index.html").write_text(_workbench_html(), encoding="utf-8")
    write_json_atomic(workbench / "review_queue.private.json", queue)
    write_json_atomic(workbench / "decision_template.private.json", template)
    write_json_atomic(target / "human_review_queue.private.json", queue)
    write_json_atomic(target / "human_review_decision_template.private.json", template)
    report = _safe_report(
        mode="PREPARE",
        origin=expected_origin,
        source_pending=queue["pending_item_count"],
        materialized=0,
        remaining=queue["pending_item_count"],
        ledger=source["ledger"],
        resolved_m12e=None,
    )
    write_json_atomic(target / "human_review_materialization_safe_report.json", report)
    return {
        "source": source,
        "queue": queue,
        "decision_template": template,
        "safe_report": report,
    }


def _validate_decisions(
    queue: Mapping[str, Any],
    decisions: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], int]:
    _assert_schema(
        "e4s_a1v1_m12e1_human_review_decisions.schema.json", decisions
    )
    _require(decisions.get("task_id"), TASK_ID, "decision_task")
    _require(
        decisions.get("source_review_queue_sha256"),
        sha256_value(queue),
        "decision_queue_hash",
    )
    expected_ids = {str(row["item_id"]) for row in queue["items"]}
    rows = list(decisions.get("decisions", []))
    ids = [str(row.get("item_id")) for row in rows]
    if len(ids) != len(set(ids)):
        raise HumanReviewMaterializationError("duplicate_decision_item")
    _require(set(ids), expected_ids, "decision_item_set")
    materialized = [row for row in rows if row.get("decision") != "PENDING"]
    if materialized:
        reviewer = decisions.get("reviewer_id")
        reviewed_at = decisions.get("reviewed_at")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise HumanReviewMaterializationError("reviewer_id_missing")
        m08._parse_timezone_timestamp(reviewed_at, "reviewed_at_invalid")
    elif decisions.get("reviewer_id") is not None or decisions.get("reviewed_at") is not None:
        raise HumanReviewMaterializationError("pending_only_registry_has_reviewer")

    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        item_id = str(row["item_id"])
        decision = str(row["decision"])
        criteria = row["criteria"]
        notes = row.get("notes")
        if decision == "PENDING":
            if any(criteria.get(key) is not None for key in CRITERIA_KEYS):
                raise HumanReviewMaterializationError(
                    f"pending_decision_has_criteria:{item_id}"
                )
            if notes not in {None, ""}:
                raise HumanReviewMaterializationError(
                    f"pending_decision_has_notes:{item_id}"
                )
            review = m08._empty_review()
        else:
            if decision == "APPROVE" and not all(
                criteria.get(key) is True for key in CRITERIA_KEYS
            ):
                raise HumanReviewMaterializationError(
                    f"approve_criteria_not_all_true:{item_id}"
                )
            if decision == "REJECT" and not any(
                criteria.get(key) is False for key in CRITERIA_KEYS
            ):
                raise HumanReviewMaterializationError(
                    f"reject_requires_false_criterion:{item_id}"
                )
            if decision == "DEFER":
                if not isinstance(notes, str) or not notes.strip():
                    raise HumanReviewMaterializationError(
                        f"defer_requires_notes:{item_id}"
                    )
                if not any(
                    criteria.get(key) is None for key in CRITERIA_KEYS
                ):
                    raise HumanReviewMaterializationError(
                        f"defer_requires_unresolved_criterion:{item_id}"
                    )
            review = {
                "decision": decision,
                "reviewer_id": decisions["reviewer_id"],
                "reviewed_at": decisions["reviewed_at"],
                "criteria": deepcopy(criteria),
                "notes": notes,
            }
            m08._validate_review(review, item_id=item_id)
        by_id[item_id] = review
    return by_id, len(materialized)


def apply_decisions(
    input_root: Path,
    qa_root: Path,
    representative_root: Path,
    m12e_root: Path,
    output_root: Path,
    decisions_path: Path,
    *,
    expected_origin: str,
) -> dict[str, Any]:
    target = _safe_root(output_root)
    prepared = prepare_workbench(
        input_root,
        representative_root,
        m12e_root,
        target,
        expected_origin=expected_origin,
    )
    source = prepared["source"]
    queue = prepared["queue"]
    decisions = read_json(decisions_path)
    reviews, materialized = _validate_decisions(queue, decisions)

    resolved_registry = deepcopy(source["registry"])
    for attempt in resolved_registry["attempts"]:
        item_id = str(attempt["item_id"])
        if item_id in reviews:
            attempt["operator_review"] = deepcopy(reviews[item_id])
    resolved_ledger, progress_report, resolved_query = m08.build_progress_artifacts(
        source["bank"], resolved_registry
    )

    resolved_root = target / "resolved_representative"
    resolved_root.mkdir(parents=True, exist_ok=True)
    write_json_atomic(
        resolved_root / "representative_batch_manifest.private.json",
        source["manifest"],
    )
    write_json_atomic(
        resolved_root / "representative_pilot_expansion_safe_report.json",
        source["expansion_report"],
    )
    write_json_atomic(
        resolved_root / "cumulative_attempt_registry.private.json",
        resolved_registry,
    )
    write_json_atomic(
        resolved_root / "cumulative_progress_ledger.private.json",
        resolved_ledger,
    )
    write_json_atomic(
        resolved_root / "cumulative_progress_query_index.json",
        resolved_query,
    )
    write_json_atomic(
        target / "human_review_decisions.private.json", decisions
    )
    write_json_atomic(
        target / "resolved_progress_safe_report.json", progress_report
    )

    resolved_m12e_root = target / "resolved_m12e"
    resolved_m12e = m12e.build_qa(
        input_root,
        qa_root,
        resolved_root,
        resolved_m12e_root,
        expected_origin=expected_origin,
    )
    remaining = int(
        resolved_m12e["evidence_summary"]["pending_human_review_count"]
    )
    _require(
        materialized + remaining,
        queue["pending_item_count"],
        "resolved_decision_accounting",
    )
    report = _safe_report(
        mode="APPLY",
        origin=expected_origin,
        source_pending=queue["pending_item_count"],
        materialized=materialized,
        remaining=remaining,
        ledger=resolved_ledger,
        resolved_m12e=resolved_m12e,
    )
    write_json_atomic(
        target / "human_review_materialization_safe_report.json", report
    )
    return {
        "queue": queue,
        "decisions": decisions,
        "resolved_registry": resolved_registry,
        "resolved_ledger": resolved_ledger,
        "resolved_query": resolved_query,
        "resolved_m12e": resolved_m12e,
        "safe_report": report,
    }


def serve_workbench(
    output_root: Path,
    *,
    host: str,
    port: int,
    dry_run: bool,
) -> int:
    root = _safe_root(output_root)
    if host != DEFAULT_HOST:
        raise HumanReviewMaterializationError(
            f"non_localhost_bind_forbidden:{host}"
        )
    if port < 1024 or port > 65535:
        raise HumanReviewMaterializationError(f"port_out_of_range:{port}")
    queue = read_json(root / "workbench/review_queue.private.json")
    _assert_schema(
        "e4s_a1v1_m12e1_human_review_queue.schema.json", queue
    )
    url = f"http://{host}:{port}/workbench/index.html"
    if dry_run:
        print(
            json.dumps(
                {
                    "pending_item_count": queue["pending_item_count"],
                    "url": url,
                },
                sort_keys=True,
            )
        )
        return 0
    handler = partial(SimpleHTTPRequestHandler, directory=str(root))
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving M12E1 private review workbench at {url}")
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
    apply_cmd = sub.add_parser("apply-decisions")
    serve = sub.add_parser("serve")
    for command in (prepare, apply_cmd):
        command.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_ROOT)
        command.add_argument("--qa-root", type=Path, default=DEFAULT_QA_ROOT)
        command.add_argument("--representative-root", type=Path, default=DEFAULT_REPRESENTATIVE_ROOT)
        command.add_argument("--m12e-root", type=Path, default=DEFAULT_M12E_ROOT)
        command.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
        command.add_argument(
            "--expected-origin",
            choices=["REAL_LEARNER", "TEST_FIXTURE"],
            required=True,
        )
    apply_cmd.add_argument("--decisions", type=Path, required=True)
    serve.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    serve.add_argument("--host", default=DEFAULT_HOST)
    serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    serve.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare_workbench(
                args.input_root,
                args.representative_root,
                args.m12e_root,
                args.output_root,
                expected_origin=args.expected_origin,
            )
        elif args.command == "apply-decisions":
            result = apply_decisions(
                args.input_root,
                args.qa_root,
                args.representative_root,
                args.m12e_root,
                args.output_root,
                args.decisions,
                expected_origin=args.expected_origin,
            )
        else:
            return serve_workbench(
                args.output_root,
                host=args.host,
                port=args.port,
                dry_run=args.dry_run,
            )
        report = result["safe_report"]
        print(
            json.dumps(
                {
                    "mode": report["mode"],
                    "evidence_origin": report["evidence_origin"],
                    "source_pending_count": report["source_pending_count"],
                    "materialized_decision_count": report["materialized_decision_count"],
                    "remaining_pending_count": report["remaining_pending_count"],
                    "outcome_counts": report["outcome_counts"],
                    "validation_status": report["validation_status"],
                    "stop_reason": report["stop_reason"],
                    "next_short_step": report["next_short_step"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    except (
        HumanReviewMaterializationError,
        m08.TextModeSessionError,
        m12.PilotCaptureError,
        m12d.RepresentativePilotError,
        m12e.RepresentativeEvidenceQAError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
