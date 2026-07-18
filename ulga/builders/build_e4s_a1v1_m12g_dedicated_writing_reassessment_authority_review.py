#!/usr/bin/env python3
"""Build and approve two private A1 writing reassessment candidates for M12G.

The real GRAMMAR_ADVERB_PHRASES_A1 writing cohort contains only two unique,
learner-valid reassessment stimuli. This builder prepares exactly two additional
project-authored candidates for explicit private Authority review. Only after both
are approved does it create a hash-bound source-bank overlay and invoke the
existing M12G assessment-validity pipeline. It never edits M08, canonical
Authority, the frozen graph, or the A2 lock.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12g_learner_contract_assessment_validity_fullfix as fullfix  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12g_remediation_reassessment_execution as base  # noqa: E402

TASK_ID = "E4S-A1V1-M12G_DedicatedWritingReassessmentAuthorityReview"
QUEUE_SCHEMA = "e4s.a1v1.m12g.writing_reassessment_review_queue.v1"
DECISION_SCHEMA = "e4s.a1v1.m12g.writing_reassessment_decisions.v1"
STATUS_PENDING = "PASS_M12G_WRITING_REASSESSMENT_CANDIDATES_PENDING_AUTHORITY_REVIEW"
STATUS_READY = "PASS_M12G_WRITING_REASSESSMENT_AUTHORITY_REVIEWED_PACKAGE_READY"
QUEUE_FILENAME = "m12g_writing_reassessment_review_queue.private.json"
DECISION_FILENAME = "m12g_writing_reassessment_decisions.private.json"
HTML_FILENAME = "m12g_writing_reassessment_review.private.html"
REPORT_FILENAME = "m12g_writing_reassessment_authority_review.safe.json"
TARGET_DEFAULT = "GRAMMAR_ADVERB_PHRASES_A1__TFX_P04"
REVIEW_CRITERIA = (
    "grammar_target_alignment",
    "a1_level_appropriate",
    "context_clear",
    "response_open_but_scorable",
    "model_response_natural",
    "rubric_complete",
    "stimulus_distinct",
    "no_a2_content",
)

CANDIDATE_SPECS = (
    {
        "suffix": "M12G_WRA01",
        "prompt": "Write one complete A1 sentence for the situation. Use an adverb to say how the action happens.",
        "context": {
            "situation": "A girl closes the classroom door without making a loud sound.",
            "required_target": "Use an adverb to say how she closes the door.",
        },
        "model_text": "The girl closes the classroom door quietly.",
    },
    {
        "suffix": "M12G_WRA02",
        "prompt": "Write one complete A1 sentence for the situation. Use an adverb phrase to say when the action happens.",
        "context": {
            "situation": "A boy does his homework when school finishes.",
            "required_target": "Use an adverb phrase to say when he does his homework.",
        },
        "model_text": "The boy does his homework after school.",
    },
)


class WritingReviewError(fullfix.AssessmentValidityError):
    """Fail-closed dedicated writing reassessment review error."""


def _write(path: Path, value: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    os.chmod(path, 0o600)
    return path


def _timestamp(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WritingReviewError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise WritingReviewError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise WritingReviewError(code)
    return value


def _normalized_answers(scoring: Mapping[str, Any]) -> set[str]:
    answers = scoring.get("accepted_texts")
    if not isinstance(answers, list):
        return set()
    return {
        " ".join(value.casefold().split())
        for value in answers
        if isinstance(value, str) and value.strip()
    }


def _cohort_diagnosis(
    bank_items: Mapping[str, Mapping[str, Any]], target_item_id: str
) -> dict[str, Any]:
    target = bank_items.get(target_item_id)
    if not target:
        raise WritingReviewError(f"target_item_missing:{target_item_id}")
    grammar_unit = str(target.get("grammar_unit_id") or "")
    skill = str(target.get("skill") or "").casefold()
    if skill != "writing":
        raise WritingReviewError(f"target_skill_not_writing:{skill}")

    cohort = [
        row
        for row in bank_items.values()
        if str(row.get("grammar_unit_id") or "") == grammar_unit
        and str(row.get("skill") or "").casefold() == skill
    ]
    cohort.sort(key=lambda row: str(row.get("item_id") or ""))
    valid: list[dict[str, Any]] = []
    rejected: dict[str, str] = {}
    fingerprints: set[str] = set()
    duplicate_count = 0
    for row in cohort:
        item_id = str(row.get("item_id") or "")
        try:
            learner, _ = fullfix.learner_item(row)
        except fullfix.AssessmentValidityError as exc:
            rejected[item_id] = str(exc).split(":", 1)[0]
            continue
        fingerprint = fullfix._contract_fingerprint(learner)
        if fingerprint in fingerprints:
            rejected[item_id] = "duplicate_learner_stimulus"
            duplicate_count += 1
            continue
        fingerprints.add(fingerprint)
        valid.append(dict(row))

    scoring = target.get("private_scoring_contract")
    if not isinstance(scoring, Mapping):
        raise WritingReviewError("target_scoring_contract_missing")
    answer_count = len(_normalized_answers(scoring))
    target_reason = rejected.get(target_item_id)
    if answer_count < 2:
        raise WritingReviewError(
            f"target_not_genuinely_ambiguous:{target_item_id}:distinct={answer_count}"
        )
    if target_reason != "gap_disambiguating_stimulus_missing":
        raise WritingReviewError(
            f"target_failure_shape_changed:{target_item_id}:{target_reason}"
        )
    if len(valid) != 2 or duplicate_count < 1:
        raise WritingReviewError(
            f"writing_shortage_shape_changed:valid={len(valid)}:duplicates={duplicate_count}"
        )

    rubric_templates = [
        row
        for row in cohort
        if isinstance(row.get("private_scoring_contract"), Mapping)
        and row["private_scoring_contract"].get("scoring_mode") == "FEATURE_RUBRIC"
        and isinstance(row["private_scoring_contract"].get("rubric"), Mapping)
        and row["private_scoring_contract"]["rubric"]
    ]
    if not rubric_templates:
        raise WritingReviewError("writing_feature_rubric_template_missing")
    rubric_templates.sort(key=lambda row: str(row.get("item_id") or ""))
    return {
        "target": target,
        "grammar_unit_id": grammar_unit,
        "skill": skill,
        "cohort_count": len(cohort),
        "valid_unique_count": len(valid),
        "duplicate_count": duplicate_count,
        "rejected": rejected,
        "template": rubric_templates[0],
    }


def _candidate_item(
    template: Mapping[str, Any], grammar_unit_id: str, spec: Mapping[str, Any]
) -> dict[str, Any]:
    item = deepcopy(dict(template))
    item_id = f"{grammar_unit_id}__{spec['suffix']}"
    scoring = deepcopy(dict(template["private_scoring_contract"]))
    scoring.update(
        {
            "scoring_mode": "FEATURE_RUBRIC",
            "response_type": "string",
            "model_texts": [str(spec["model_text"])],
            "human_review_fallback": True,
        }
    )
    if not isinstance(scoring.get("rubric"), Mapping) or not scoring["rubric"]:
        raise WritingReviewError("candidate_rubric_missing")
    item.update(
        {
            "item_id": item_id,
            "shared_item_id": f"SHARED_{item_id}",
            "grammar_unit_id": grammar_unit_id,
            "skill": "writing",
            "item_role": "assessment",
            "evidence_dimension": "reassessment",
            "task_type": "guided_contextual_writing",
            "learner_contract": {
                "prompt": str(spec["prompt"]),
                "response_mode": "short_text",
                "context": deepcopy(spec["context"]),
            },
            "private_scoring_contract": scoring,
            "session_status": "PENDING_PRIVATE_AUTHORITY_REVIEW",
            "m12g_candidate_authoring": {
                "task_id": TASK_ID,
                "project_authored": True,
                "private_local_only": True,
                "canonical_authority": False,
                "a2_content": False,
            },
        }
    )
    fullfix.learner_item(item)
    return item


def _queue_html(queue: Mapping[str, Any]) -> str:
    public = json.dumps(
        {
            "task_id": queue["task_id"],
            "review_queue_sha256": queue["review_queue_sha256"],
            "candidates": queue["candidates"],
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")
    criteria = json.dumps(list(REVIEW_CRITERIA), ensure_ascii=False)
    return f"""<!doctype html>
<html lang='zh-Hant'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>M12G Writing Reassessment Review</title><style>
body{{font-family:system-ui,sans-serif;max-width:920px;margin:auto;padding:24px;background:#f4f4f4}}article{{background:white;border:1px solid #aaa;border-radius:8px;padding:18px;margin:16px 0}}pre{{white-space:pre-wrap;background:#f6f7f8;padding:12px}}label{{display:block;margin:8px 0}}input,select,textarea{{box-sizing:border-box;padding:8px}}.wide{{width:100%}}button{{padding:10px 18px;font-weight:600}}.error{{color:#a00000;font-weight:600}}</style></head>
<body><h1>M12G Writing Reassessment Authority Review</h1><p>這兩題尚未核准。請逐題檢查內容、model response 與 rubric。只有兩題都 APPROVE_AS_IS 才能進入 M12G。</p>
<label>Reviewer ID <input id='reviewer' class='wide'></label><div id='error' class='error'></div><main id='root'></main><button id='save'>下載審核決策檔</button>
<script>const q={public},criteria={criteria},root=document.getElementById('root');q.candidates.forEach((c,i)=>{{const a=document.createElement('article');a.dataset.id=c.review_entry_id;a.innerHTML=`<h2>${{i+1}}. ${{c.candidate.item_id}}</h2><p><strong>Prompt</strong></p><pre>${{c.candidate.learner_contract.prompt}}</pre><p><strong>Context</strong></p><pre>${{JSON.stringify(c.candidate.learner_contract.context,null,2)}}</pre><p><strong>Model response</strong></p><pre>${{c.candidate.private_scoring_contract.model_texts.join('\n')}}</pre><p><strong>Rubric</strong></p><pre>${{JSON.stringify(c.candidate.private_scoring_contract.rubric,null,2)}}</pre><label>Decision <select data-decision><option value=''>請選擇</option><option>APPROVE_AS_IS</option><option>REJECT</option><option>DEFER</option></select></label>`;criteria.forEach(k=>{{const l=document.createElement('label'),x=document.createElement('input');x.type='checkbox';x.dataset.criterion=k;l.appendChild(x);l.appendChild(document.createTextNode(k));a.appendChild(l)}});root.appendChild(a)}});
document.getElementById('save').onclick=()=>{{const reviewer=document.getElementById('reviewer').value.trim(),now=new Date().toISOString(),errors=[];if(!reviewer)errors.push('Reviewer ID 必填');const decisions=[...root.children].map((a,i)=>{{const decision=a.querySelector('[data-decision]').value,criteriaResult=Object.fromEntries([...a.querySelectorAll('[data-criterion]')].map(x=>[x.dataset.criterion,x.checked]));if(!decision)errors.push(`第 ${{i+1}} 題尚未選擇決策`);if(decision==='APPROVE_AS_IS'&&!Object.values(criteriaResult).every(Boolean))errors.push(`第 ${{i+1}} 題核准時所有 criteria 必須通過`);const source=q.candidates[i];return{{review_entry_id:source.review_entry_id,candidate_item_id:source.candidate.item_id,candidate_sha256:source.candidate_sha256,decision,reviewer_id:reviewer,reviewed_at:now,criteria:criteriaResult,notes:null}}}});if(errors.length){{document.getElementById('error').textContent=errors.join('；');return}}const out={{task_id:q.task_id,schema_version:'{DECISION_SCHEMA}',private_local_only:true,review_queue_sha256:q.review_queue_sha256,decision_count:decisions.length,decisions}},blob=new Blob([JSON.stringify(out,null,2)],{{type:'application/json'}}),link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='{DECISION_FILENAME}';link.click();URL.revokeObjectURL(link.href)}};</script></body></html>"""


def prepare_review(*, source_bank_path: Path, target_item_id: str, target_root: Path) -> dict[str, Any]:
    target_root = base.output_root(target_root)
    bank, bank_hash, bank_items = base.load_bank(source_bank_path)
    diagnosis = _cohort_diagnosis(bank_items, target_item_id)
    candidates = [
        _candidate_item(diagnosis["template"], diagnosis["grammar_unit_id"], spec)
        for spec in CANDIDATE_SPECS
    ]
    fingerprints = {
        fullfix._contract_fingerprint(fullfix.learner_item(item)[0]) for item in candidates
    }
    if len(fingerprints) != 2:
        raise WritingReviewError("candidate_stimulus_not_distinct")
    entries = [
        {
            "review_entry_id": f"M12G_WR_REVIEW_{index:02d}",
            "candidate_sha256": base.digest(item),
            "candidate": item,
            "review_criteria": list(REVIEW_CRITERIA),
        }
        for index, item in enumerate(candidates, 1)
    ]
    queue_core = {
        "task_id": TASK_ID,
        "schema_version": QUEUE_SCHEMA,
        "private_local_only": True,
        "source_session_bank_sha256": bank_hash,
        "target_item_id": target_item_id,
        "grammar_unit_id": diagnosis["grammar_unit_id"],
        "skill": diagnosis["skill"],
        "source_cohort_count": diagnosis["cohort_count"],
        "source_valid_unique_count": diagnosis["valid_unique_count"],
        "candidate_count": 2,
        "candidates": entries,
        "claim_boundaries": {
            "candidates_approved": False,
            "canonical_authority_modified": False,
            "source_bank_modified": False,
            "a2_content_included": False,
        },
    }
    queue = {**queue_core, "review_queue_sha256": base.digest(queue_core)}
    decision_template = {
        "task_id": TASK_ID,
        "schema_version": DECISION_SCHEMA,
        "private_local_only": True,
        "review_queue_sha256": queue["review_queue_sha256"],
        "decision_count": 2,
        "decisions": [
            {
                "review_entry_id": entry["review_entry_id"],
                "candidate_item_id": entry["candidate"]["item_id"],
                "candidate_sha256": entry["candidate_sha256"],
                "decision": "PENDING",
                "reviewer_id": None,
                "reviewed_at": None,
                "criteria": {key: None for key in REVIEW_CRITERIA},
                "notes": None,
            }
            for entry in entries
        ],
    }
    queue_path = _write(target_root / QUEUE_FILENAME, queue)
    decision_path = _write(target_root / DECISION_FILENAME, decision_template)
    html_path = target_root / HTML_FILENAME
    html_path.write_text(_queue_html(queue), encoding="utf-8")
    os.chmod(html_path, 0o600)
    report = {
        "task_id": TASK_ID,
        "validation_status": STATUS_PENDING,
        "source_valid_unique_count": 2,
        "candidate_count": 2,
        "approved_candidate_count": 0,
        "canonical_authority_modified": False,
        "a2_lock_state": "LOCKED_BY_DESIGN",
        "stop_reason": "PRIVATE_AUTHORITY_REVIEW_REQUIRED",
    }
    report_path = _write(target_root / REPORT_FILENAME, report)
    return {
        "report": report,
        "queue_path": queue_path,
        "decision_path": decision_path,
        "html_path": html_path,
        "report_path": report_path,
    }


def _approved_candidates(
    queue: Mapping[str, Any], decisions: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if decisions.get("task_id") != TASK_ID or decisions.get("schema_version") != DECISION_SCHEMA:
        raise WritingReviewError("decision_contract_invalid")
    if decisions.get("review_queue_sha256") != queue.get("review_queue_sha256"):
        raise WritingReviewError("decision_queue_hash_mismatch")
    entries = {row["review_entry_id"]: row for row in queue.get("candidates", [])}
    rows = decisions.get("decisions")
    if not isinstance(rows, list) or len(rows) != 2:
        raise WritingReviewError("decision_partition_invalid")
    if {row.get("review_entry_id") for row in rows} != set(entries):
        raise WritingReviewError("decision_identity_invalid")
    approved: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    for row in rows:
        entry = entries[str(row["review_entry_id"])]
        if row.get("candidate_item_id") != entry["candidate"]["item_id"]:
            raise WritingReviewError("decision_candidate_join_invalid")
        if row.get("candidate_sha256") != entry["candidate_sha256"]:
            raise WritingReviewError("decision_candidate_hash_invalid")
        if row.get("decision") != "APPROVE_AS_IS":
            raise WritingReviewError(f"candidate_not_approved:{row.get('candidate_item_id')}")
        reviewer = row.get("reviewer_id")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise WritingReviewError("reviewer_id_missing")
        reviewed_at = _timestamp(row.get("reviewed_at"), "reviewed_at_invalid")
        criteria = row.get("criteria")
        if not isinstance(criteria, Mapping) or set(criteria) != set(REVIEW_CRITERIA):
            raise WritingReviewError("review_criteria_invalid")
        if any(criteria[key] is not True for key in REVIEW_CRITERIA):
            raise WritingReviewError("review_criteria_not_all_pass")
        item = deepcopy(entry["candidate"])
        item["session_status"] = "READY_FOR_LOCAL_TEXT_SESSION"
        item["m12g_private_authority_review"] = {
            "decision": "APPROVE_AS_IS",
            "reviewer_id": reviewer,
            "reviewed_at": reviewed_at,
            "review_queue_sha256": queue["review_queue_sha256"],
            "candidate_sha256": entry["candidate_sha256"],
            "canonical_authority": False,
            "private_reassessment_authority": True,
        }
        approved.append(item)
        receipts.append(
            {
                "candidate_item_id": item["item_id"],
                "candidate_sha256": entry["candidate_sha256"],
                "reviewer_id_sha256": base.digest(reviewer),
                "reviewed_at": reviewed_at,
                "criteria_pass_count": len(REVIEW_CRITERIA),
            }
        )
    return approved, receipts


def apply_review_and_prepare(
    *,
    source_bank_path: Path,
    base_consumer_path: Path,
    base_graph_path: Path,
    source_database_path: Path,
    resolved_root: Path,
    m12e1_root: Path,
    review_queue_path: Path,
    decision_registry_path: Path,
    learner_id: str,
    display_label: str,
    target_root: Path,
) -> dict[str, Any]:
    target_root = base.output_root(target_root)
    bank, bank_hash, bank_items = base.load_bank(source_bank_path)
    queue = base.read_json(base.local_path(review_queue_path, "review_queue"), "review_queue")
    decisions = base.read_json(base.local_path(decision_registry_path, "decision_registry"), "decision_registry")
    if queue.get("source_session_bank_sha256") != bank_hash:
        raise WritingReviewError("review_queue_source_bank_hash_mismatch")
    diagnosis = _cohort_diagnosis(bank_items, str(queue.get("target_item_id") or ""))
    if diagnosis["grammar_unit_id"] != queue.get("grammar_unit_id"):
        raise WritingReviewError("review_queue_grammar_unit_drift")
    approved, receipts = _approved_candidates(queue, decisions)

    overlay_root = target_root / "approved_overlay"
    overlay_root.mkdir(parents=True, exist_ok=True)
    overlay_bank = deepcopy(bank)
    existing_ids = {str(row.get("item_id")) for row in overlay_bank["items"]}
    if any(item["item_id"] in existing_ids for item in approved):
        raise WritingReviewError("approved_candidate_identity_collision")
    overlay_bank["items"].extend(approved)
    overlay_bank["items"] = sorted(overlay_bank["items"], key=lambda row: str(row["item_id"]))
    overlay_bank["item_count"] = len(overlay_bank["items"])
    overlay_bank["items_sha256"] = m08.sha256_value(overlay_bank["items"])
    overlay_bank["m12g_dedicated_writing_reassessment_overlay"] = {
        "task_id": TASK_ID,
        "review_queue_sha256": queue["review_queue_sha256"],
        "approved_candidate_count": 2,
        "private_local_only": True,
        "canonical_authority_modified": False,
    }
    overlay_bank_hash = m08.sha256_value(overlay_bank)
    overlay_bank_path = _write(
        overlay_root / "text_mode_session_bank.m12g_writing_reviewed.private.json",
        overlay_bank,
    )

    consumer = base.read_json(base.local_path(base_consumer_path, "base_consumer"), "base_consumer")
    for asset in consumer.get("asset_records", []):
        payload = asset.get("payload")
        if isinstance(payload, dict) and "m12_session_bank_sha256" in payload:
            payload["m12_session_bank_sha256"] = overlay_bank_hash
            asset["content_digest"] = base.digest(payload)
    overlay_contract = consumer.get("m12f_dedicated_private_bridge_overlay")
    if not isinstance(overlay_contract, dict):
        raise WritingReviewError("consumer_bridge_overlay_missing")
    overlay_contract["source_session_bank_sha256"] = overlay_bank_hash
    consumer["m12g_writing_reassessment_authority_review"] = {
        "task_id": TASK_ID,
        "review_queue_sha256": queue["review_queue_sha256"],
        "approved_candidate_count": 2,
        "private_local_only": True,
    }
    overlay_consumer_path = _write(
        overlay_root / "four_skill_asset_body_consumer.m12g_writing_reviewed.private.json",
        consumer,
    )

    source_m12e1 = base.local_path(m12e1_root, "m12e1_root")
    source_resolved = base.local_path(resolved_root, "resolved_root")
    try:
        resolved_relative = source_resolved.relative_to(source_m12e1)
    except ValueError as exc:
        raise WritingReviewError("resolved_root_not_inside_m12e1_root") from exc
    overlay_m12e1 = overlay_root / "m12e1"
    shutil.copytree(source_m12e1, overlay_m12e1)
    overlay_resolved = overlay_m12e1 / resolved_relative
    registry_path = overlay_resolved / "cumulative_attempt_registry.private.json"
    ledger_path = overlay_resolved / "cumulative_progress_ledger.private.json"
    registry = base.read_json(registry_path, "overlay_registry")
    ledger = base.read_json(ledger_path, "overlay_ledger")
    registry["session_bank_sha256"] = overlay_bank_hash
    _write(registry_path, registry)
    ledger["session_bank_sha256"] = overlay_bank_hash
    ledger["attempt_registry_sha256"] = m08.sha256_value(registry)
    _write(ledger_path, ledger)

    prepared = fullfix.prepare(
        source_bank_path=overlay_bank_path,
        base_consumer_path=overlay_consumer_path,
        base_graph_path=base_graph_path,
        source_database_path=source_database_path,
        resolved_root=overlay_resolved,
        m12e1_root=overlay_m12e1,
        learner_id=learner_id,
        display_label=display_label,
        target_root=target_root / "m12g",
    )
    report = prepared["report"]
    if report.get("validation_status") != fullfix.STATUS:
        raise WritingReviewError("prepared_fullfix_status_invalid")
    if report.get("required_attempt_count") != 8 or report.get("learner_contract_valid_count") != 8:
        raise WritingReviewError("prepared_attempt_accounting_invalid")
    package = base.read_json(prepared["package_path"], "prepared_package")
    selected_ids = {str(row.get("source_item_id")) for row in package.get("tasks", [])}
    approved_ids = {item["item_id"] for item in approved}
    if not approved_ids.issubset(selected_ids):
        raise WritingReviewError("approved_candidates_not_selected")

    safe_report = {
        "task_id": TASK_ID,
        "validation_status": STATUS_READY,
        "source_valid_unique_count": 2,
        "approved_candidate_count": 2,
        "approved_candidate_ids": sorted(approved_ids),
        "review_receipts": sorted(receipts, key=lambda row: row["candidate_item_id"]),
        "pending_node_count": report["pending_node_count"],
        "required_attempt_count": report["required_attempt_count"],
        "learner_contract_valid_count": report["learner_contract_valid_count"],
        "a2_lock_state": report["a2_lock_state"],
        "canonical_authority_modified": False,
        "source_bank_original_modified": False,
        "stop_reason": report["stop_reason"],
    }
    report_path = _write(target_root / REPORT_FILENAME, safe_report)
    prepared.update(
        {
            "report": safe_report,
            "report_path": report_path,
            "overlay_bank_path": overlay_bank_path,
            "overlay_consumer_path": overlay_consumer_path,
        }
    )
    return prepared


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser("prepare-review")
    prepare.add_argument("--source-bank", type=Path, required=True)
    prepare.add_argument("--target-item-id", default=TARGET_DEFAULT)
    prepare.add_argument("--output-root", type=Path, required=True)

    apply = commands.add_parser("apply-review")
    for name in (
        "source-bank",
        "base-consumer",
        "base-graph",
        "source-database",
        "resolved-root",
        "m12e1-root",
        "review-queue",
        "decision-registry",
        "output-root",
    ):
        apply.add_argument(f"--{name}", type=Path, required=True)
    apply.add_argument("--learner-id", required=True)
    apply.add_argument("--display-label", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare-review":
            result = prepare_review(
                source_bank_path=args.source_bank,
                target_item_id=args.target_item_id,
                target_root=args.output_root,
            )
            report = result["report"]
            payload = {
                "validation_status": report["validation_status"],
                "source_valid_unique_count": report["source_valid_unique_count"],
                "candidate_count": report["candidate_count"],
                "approved_candidate_count": report["approved_candidate_count"],
                "a2_lock_state": report["a2_lock_state"],
                "stop_reason": report["stop_reason"],
                "review_queue": str(result["queue_path"]),
                "decision_template": str(result["decision_path"]),
                "html": str(result["html_path"]),
            }
        else:
            result = apply_review_and_prepare(
                source_bank_path=args.source_bank,
                base_consumer_path=args.base_consumer,
                base_graph_path=args.base_graph,
                source_database_path=args.source_database,
                resolved_root=args.resolved_root,
                m12e1_root=args.m12e1_root,
                review_queue_path=args.review_queue,
                decision_registry_path=args.decision_registry,
                learner_id=args.learner_id,
                display_label=args.display_label,
                target_root=args.output_root,
            )
            report = result["report"]
            payload = {
                "validation_status": report["validation_status"],
                "approved_candidate_count": report["approved_candidate_count"],
                "pending_node_count": report["pending_node_count"],
                "required_attempt_count": report["required_attempt_count"],
                "learner_contract_valid_count": report["learner_contract_valid_count"],
                "a2_lock_state": report["a2_lock_state"],
                "stop_reason": report["stop_reason"],
                "html": str(result["html_path"]),
                "package": str(result["package_path"]),
                "database": str(result["database_path"]),
                "report": str(result["report_path"]),
            }
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return 0
    except (WritingReviewError, fullfix.AssessmentValidityError, base.ReassessmentError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
