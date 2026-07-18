#!/usr/bin/env python3
"""Prepare and import real private M12G remediation reassessment evidence.

This module orchestrates the existing M3/M6/M7 implementation. It does not
create a second remediation engine. It reuses distinct Authority-reviewed
source-bank items from the same grammar unit and skill, materializes a private
reassessment overlay, and imports real learner evidence atomically.
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3  # noqa: E402
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6  # noqa: E402
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7  # noqa: E402
from ulga.builders import build_e4s_a1v1_m08_text_mode_learner_session as m08  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12f_dedicated_private_bridge_assets as dedicated  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12f_explicit_mapping_overlay as overlay  # noqa: E402
from ulga.builders import build_e4s_a1v1_m12f_m12e1_to_a1fs_remediation_bridge as bridge  # noqa: E402
from ulga.validators import validate_a1fs_v1_m7_mastery_error_remediation_reassessment as m7_validator  # noqa: E402

TASK_ID = "E4S-A1V1-M12G_RemediationReassessmentExecution"
SCHEMA_VERSION = "e4s.a1v1.m12g.remediation_reassessment_execution.v1"
PACKAGE_SCHEMA_VERSION = "e4s.a1v1.m12g.reassessment_package.v1"
REGISTRY_SCHEMA_VERSION = "e4s.a1v1.m12g.reassessment_response_registry.v1"
PREPARE_STATUS = "PASS_M12G_REASSESSMENT_PACKAGE_READY"
IMPORT_STATUS = "PASS_M12G_REMEDIATION_REASSESSMENT_COMPLETED"
PARTIAL_STATUS = "PASS_M12G_REASSESSMENT_EVIDENCE_IMPORTED_REMEDIATION_OPEN"
REPLAY_STATUS = "PASS_M12G_REASSESSMENT_ALREADY_IMPORTED"
EXPECTED_PENDING_NODES = 2
NEXT_AFTER_COMPLETE = "A1FS-V1-M8_ReviewSchedulingRetentionAndSpacedPractice"
GRAPH_FILENAME = "a1a1plus_prerequisite_graph_and_coverage.m12g_reassessment.private.json"
CONSUMER_FILENAME = "four_skill_asset_body_consumer.m12g_reassessment.private.json"
DATABASE_FILENAME = "a1fs_v1_m12g.private.sqlite3"
PACKAGE_FILENAME = "m12g_reassessment_package.private.json"
TEMPLATE_FILENAME = "m12g_reassessment_response_template.private.json"
HTML_FILENAME = "m12g_reassessment_ui.private.html"
PREPARE_REPORT_FILENAME = "m12g_reassessment_prepare.safe.json"
IMPORT_REPORT_FILENAME = "m12g_reassessment_import.safe.json"


class ReassessmentError(ValueError):
    """Fail-closed M12G error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8") if isinstance(value, str) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(actual: Any, expected: Any, code: str) -> None:
    if actual != expected:
        raise ReassessmentError(f"{code}:expected={expected!r}:actual={actual!r}")


def local_path(path: Path, code: str, *, must_exist: bool = True) -> Path:
    resolved = Path(path).resolve()
    approved = (REPO_ROOT / ".local").resolve()
    if not resolved.is_relative_to(approved):
        raise ReassessmentError(f"{code}_outside_local:{resolved}")
    if must_exist and not resolved.exists():
        raise ReassessmentError(f"{code}_missing:{resolved}")
    return resolved


def output_root(path: Path) -> Path:
    resolved = local_path(path, "output_root", must_exist=False)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReassessmentError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise ReassessmentError(f"{code}_not_object")
    return value


def write_private(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    os.chmod(path, 0o600)


def timezone_timestamp(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReassessmentError(code)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReassessmentError(code) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ReassessmentError(code)
    return value


def load_bank(path: Path) -> tuple[dict[str, Any], str, dict[str, dict[str, Any]]]:
    bank = read_json(local_path(path, "source_bank"), "source_bank")
    require(bank.get("task_id"), m08.TASK_ID, "bank_task")
    require(bank.get("schema_version"), m08.SESSION_SCHEMA_VERSION, "bank_schema")
    items = bank.get("items")
    if not isinstance(items, list) or not items:
        raise ReassessmentError("bank_items_invalid")
    by_id = {str(row.get("item_id")): row for row in items if isinstance(row, Mapping)}
    if len(by_id) != len(items):
        raise ReassessmentError("bank_item_identity_invalid")
    return bank, m08.sha256_value(bank), by_id


def load_consumer_graph(consumer_path: Path, graph_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    consumer_path = local_path(consumer_path, "consumer")
    graph_path = local_path(graph_path, "graph")
    consumer = read_json(consumer_path, "consumer")
    graph = read_json(graph_path, "graph")
    require(consumer.get("validation_status"), bridge.CONSUMER_STATUS, "consumer_status")
    require(graph.get("validation_status"), bridge.GRAPH_STATUS, "graph_status")
    require(consumer.get("source_graph_sha256"), file_sha(graph_path), "consumer_graph_hash")
    require(graph.get("a2_lock_contract", {}).get("state"), "LOCKED_BY_DESIGN", "a2_design_lock")
    return consumer, graph


def database_state(database_path: Path, consumer_path: Path, graph_path: Path, learner_id: str) -> dict[str, Any]:
    database_path = local_path(database_path, "database")
    connection = sqlite3.connect(database_path)
    try:
        connection.row_factory = sqlite3.Row
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ReassessmentError("database_integrity_failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ReassessmentError("database_foreign_key_failed")
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        require(metadata.get("consumer_sha256"), file_sha(consumer_path), "database_consumer_hash")
        m7_meta = dict(connection.execute("SELECT key,value FROM m7_metadata"))
        require(m7_meta.get("source_graph_sha256"), file_sha(graph_path), "database_graph_hash")
        profile = connection.execute("SELECT profile_state FROM learner_profiles WHERE learner_id=?", (learner_id,)).fetchone()
        if not profile or profile[0] != "ACTIVE":
            raise ReassessmentError("learner_profile_not_active")
        stored = connection.execute(
            "SELECT snapshot_json,snapshot_digest FROM mastery_snapshots WHERE learner_id=? ORDER BY rowid DESC LIMIT 1",
            (learner_id,),
        ).fetchone()
        if not stored:
            raise ReassessmentError("m7_snapshot_missing")
        snapshot = json.loads(stored["snapshot_json"])
        require(digest(snapshot), stored["snapshot_digest"], "m7_snapshot_digest")
        pending = [dict(row) for row in connection.execute(
            "SELECT * FROM reassessment_queue WHERE learner_id=? AND queue_state='PENDING' ORDER BY node_id",
            (learner_id,),
        )]
        return {"snapshot": snapshot, "pending": pending}
    finally:
        connection.close()


def additional_passes_required(state: Mapping[str, Any]) -> int:
    passes = int(state.get("pass_count", 0))
    resolved = int(state.get("resolved_attempt_count", 0))
    failures = int(state.get("fail_count", 0))
    recovered = bool(state.get("recovered_after_last_failure"))
    for additional in range(0, 21):
        future_passes = passes + additional
        future_resolved = resolved + additional
        rate = future_passes / future_resolved if future_resolved else 0.0
        recovery_ok = recovered or failures == 0 or additional >= 1
        if future_resolved >= m7.MIN_RESOLVED_ATTEMPTS and future_passes >= m7.MIN_PASS_COUNT and rate >= m7.MIN_PASS_RATE and recovery_ok:
            return additional
    raise ReassessmentError("reassessment_pass_requirement_unbounded")


def learner_item(item: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    learner = item.get("learner_contract")
    scoring = item.get("private_scoring_contract")
    if not isinstance(learner, Mapping) or not isinstance(scoring, Mapping):
        raise ReassessmentError(f"source_item_contract_missing:{item.get('item_id')}")
    if not isinstance(learner.get("prompt"), str) or not learner.get("prompt", "").strip():
        raise ReassessmentError(f"source_item_prompt_missing:{item.get('item_id')}")
    return deepcopy(dict(learner)), deepcopy(dict(scoring))


def choose_source_items(source_item: Mapping[str, Any], bank_items: Mapping[str, Mapping[str, Any]], required_count: int) -> list[dict[str, Any]]:
    item_id = str(source_item["item_id"])
    grammar_unit = str(source_item.get("grammar_unit_id") or "")
    skill = str(source_item.get("skill") or "").casefold()
    candidates = [
        row for row in bank_items.values()
        if str(row.get("grammar_unit_id") or "") == grammar_unit
        and str(row.get("skill") or "").casefold() == skill
        and isinstance(row.get("learner_contract"), Mapping)
        and isinstance(row.get("private_scoring_contract"), Mapping)
    ]
    candidates.sort(key=lambda row: str(row["item_id"]))
    original = next((row for row in candidates if str(row["item_id"]) == item_id), None)
    if original is None:
        raise ReassessmentError(f"original_source_item_missing:{item_id}")
    alternatives = [row for row in candidates if str(row["item_id"]) != item_id]
    selected = alternatives[: max(required_count - 1, 0)] + [original]
    if len(selected) != required_count or len({str(row["item_id"]) for row in selected}) != required_count:
        raise ReassessmentError(f"distinct_reassessment_items_insufficient:{item_id}:required={required_count}:available={len(candidates)}")
    for row in selected:
        learner_item(row)
    return selected


def reassessment_identity(node_id: str, source_item_id: str, skill: str) -> dict[str, str]:
    token = digest([node_id, source_item_id])[:16]
    lesson_token = digest(node_id)[:16]
    lesson_id = f"M12G-{skill[:3]}-{lesson_token}"
    return {
        "asset_id": f"M12G-REASSESS-{token}",
        "asset_key": f"{skill}:M12G:{token}",
        "lesson_id": lesson_id,
        "lesson_node_id": f"LESSON:{skill}:{lesson_id}",
    }


def build_overlay_and_package(
    *, bank_hash: str, bank_items: Mapping[str, Mapping[str, Any]], consumer: Mapping[str, Any],
    graph: Mapping[str, Any], source_state: Mapping[str, Any], learner_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    pending = list(source_state["pending"])
    require(len(pending), EXPECTED_PENDING_NODES, "pending_node_count")
    state_by_node = {str(row["node_id"]): row for row in source_state["snapshot"].get("node_states", [])}
    output_consumer = deepcopy(dict(consumer))
    output_graph = deepcopy(dict(graph))
    assets_by_key = {str(row["asset_key"]): row for row in output_consumer["asset_records"]}
    coverage_by_node = {str(row["node_id"]): row for row in output_graph["coverage"]}
    node_ids = {str(row["node_id"]) for row in output_graph["nodes"]}
    edge_keys = {(row["from_node_id"], row["to_node_id"], row["edge_type"]) for row in output_graph["edges"]}
    asset_keys = set(assets_by_key)
    asset_ids = {str(row["asset_id"]) for row in output_consumer["asset_records"]}
    lesson_ids = {str(row["lesson_id"]) for row in output_consumer["lesson_catalog"]}
    tasks: list[dict[str, Any]] = []
    node_plan: list[dict[str, Any]] = []
    added_lessons = 0

    for queue in pending:
        node_id = str(queue["node_id"])
        state = state_by_node.get(node_id)
        if not state:
            raise ReassessmentError(f"pending_node_state_missing:{node_id}")
        required_passes = additional_passes_required(state)
        if required_passes < 1:
            raise ReassessmentError(f"pending_node_needs_no_reassessment:{node_id}")
        queue_assets = json.loads(queue["asset_keys_json"])
        if not isinstance(queue_assets, list) or len(queue_assets) != 1:
            raise ReassessmentError(f"pending_asset_partition_invalid:{node_id}")
        original_asset = assets_by_key.get(str(queue_assets[0]))
        if not original_asset:
            raise ReassessmentError(f"pending_asset_missing:{node_id}")
        payload = original_asset.get("payload")
        source_item_id = str(payload.get("m12_item_id") if isinstance(payload, Mapping) else "")
        source_item = bank_items.get(source_item_id)
        if not source_item:
            raise ReassessmentError(f"pending_source_item_missing:{node_id}:{source_item_id}")
        skill = str(original_asset["skill"])
        level = str(original_asset["level"])
        selected = choose_source_items(source_item, bank_items, required_passes)
        coverage = coverage_by_node.get(node_id)
        if not coverage or str(original_asset["asset_id"]) not in {str(value) for value in coverage.get("asset_body_ids", [])}:
            raise ReassessmentError(f"pending_node_coverage_invalid:{node_id}")
        new_assets: list[dict[str, Any]] = []
        lesson_identity: dict[str, str] | None = None

        for order, item in enumerate(selected, 1):
            item_id = str(item["item_id"])
            learner_contract, scoring_contract = learner_item(item)
            human_review = str(scoring_contract.get("scoring_mode")) == "FEATURE_RUBRIC"
            if item_id == source_item_id:
                asset_key = str(original_asset["asset_key"])
                lesson_id = str(original_asset["lesson_id"])
            else:
                identity = reassessment_identity(node_id, item_id, skill)
                lesson_identity = lesson_identity or identity
                if identity["asset_key"] in asset_keys or identity["asset_id"] in asset_ids:
                    raise ReassessmentError(f"reassessment_asset_collision:{item_id}")
                role = dedicated.role_for(item, skill)
                new_payload = {
                    "body_title": f"M12G private reassessment — {item.get('grammar_unit_id')}",
                    "instruction": str(learner_contract["prompt"]),
                    "learner_contract": learner_contract,
                    "reassessment_source_item_id": item_id,
                    "reassessment_node_id": node_id,
                    "source_grammar_unit_id": str(item.get("grammar_unit_id") or ""),
                    "source_task_type": str(item.get("task_type") or ""),
                    "source_item_sha256": digest(item),
                    "m12g_reassessment_only": True,
                    "private_scoring_contract": scoring_contract,
                    "response_capture_enabled": True,
                }
                asset = {
                    "asset_id": identity["asset_id"], "asset_key": identity["asset_key"],
                    "lesson_id": identity["lesson_id"], "skill": skill, "level": level,
                    "role": role, "payload": new_payload, "content_digest": digest(new_payload),
                    "release_scope": "PRIVATE_INTERNAL_D0",
                }
                if not m6.derive_contract(asset).get("capture_enabled"):
                    raise ReassessmentError(f"reassessment_asset_capture_disabled:{item_id}")
                new_assets.append(asset)
                asset_keys.add(identity["asset_key"])
                asset_ids.add(identity["asset_id"])
                asset_key = identity["asset_key"]
                lesson_id = identity["lesson_id"]
            tasks.append({
                "task_instance_id": f"M12G_TASK:{digest([node_id, item_id])[:24]}",
                "reassessment_id": str(queue["reassessment_id"]), "node_id": node_id,
                "source_item_id": item_id, "grammar_unit_id": str(item.get("grammar_unit_id") or ""),
                "skill": skill, "level": level, "asset_key": asset_key, "lesson_id": lesson_id,
                "attempt_order": order, "learner_contract": learner_contract,
                "response_type": str(scoring_contract.get("response_type") or "string"),
                "scoring_mode": str(scoring_contract.get("scoring_mode") or ""),
                "human_review_required": human_review,
            })

        if new_assets:
            if lesson_identity is None:
                raise ReassessmentError(f"reassessment_lesson_identity_missing:{node_id}")
            lesson_id = lesson_identity["lesson_id"]
            if lesson_id in lesson_ids or lesson_identity["lesson_node_id"] in node_ids:
                raise ReassessmentError(f"reassessment_lesson_collision:{node_id}")
            output_consumer["asset_records"].extend(new_assets)
            output_consumer["lesson_catalog"].append({
                "lesson_id": lesson_id, "lesson_node_id": lesson_identity["lesson_node_id"],
                "skill": skill, "level": level,
                "asset_keys": sorted(str(row["asset_key"]) for row in new_assets),
                "roles": sorted({str(row["role"]) for row in new_assets}),
                "requirement_node_ids": [node_id], "release_scope": "PRIVATE_INTERNAL_D0",
            })
            output_graph["nodes"].append({
                "node_id": lesson_identity["lesson_node_id"], "node_type": "LESSON", "skill": skill,
                "level": level, "source_ref": lesson_id, "mastery_required_before_a2": False,
                "asset_body_count": len(new_assets), "roles": sorted({str(row["role"]) for row in new_assets}),
                "private_reassessment_only": True,
            })
            edge = (node_id, lesson_identity["lesson_node_id"], "TAUGHT_BY")
            if edge in edge_keys:
                raise ReassessmentError(f"reassessment_edge_collision:{node_id}")
            output_graph["edges"].append({"from_node_id": edge[0], "to_node_id": edge[1], "edge_type": edge[2]})
            edge_keys.add(edge)
            node_ids.add(lesson_identity["lesson_node_id"])
            lesson_ids.add(lesson_id)
            coverage["asset_body_ids"] = sorted(set(str(value) for value in coverage.get("asset_body_ids", [])) | {str(row["asset_id"]) for row in new_assets})
            coverage["lesson_ids"] = sorted(set(str(value) for value in coverage.get("lesson_ids", [])) | {lesson_id})
            coverage["roles"] = sorted(set(str(value) for value in coverage.get("roles", [])) | {str(row["role"]) for row in new_assets})
            added_lessons += 1

        node_plan.append({
            "node_id": node_id, "reassessment_id": str(queue["reassessment_id"]),
            "required_successful_attempt_count": required_passes,
            "source_pass_count": int(state.get("pass_count", 0)),
            "source_fail_count": int(state.get("fail_count", 0)),
            "source_resolved_attempt_count": int(state.get("resolved_attempt_count", 0)),
            "task_instance_ids": [row["task_instance_id"] for row in tasks if row["node_id"] == node_id],
        })

    output_graph["nodes"] = sorted(output_graph["nodes"], key=lambda row: row["node_id"])
    output_graph["edges"] = sorted(output_graph["edges"], key=lambda row: (row["from_node_id"], row["to_node_id"], row["edge_type"]))
    output_graph["coverage"] = sorted(output_graph["coverage"], key=lambda row: row["node_id"])
    output_graph["counts"]["node_count"] = len(output_graph["nodes"])
    output_graph["counts"]["edge_count"] = len(output_graph["edges"])
    output_graph["counts"]["coverage_record_count"] = len(output_graph["coverage"])
    output_graph["counts"]["lesson_count"] = int(output_graph["counts"]["lesson_count"]) + added_lessons
    by_level = dict(output_graph["counts"].get("lesson_count_by_level", {}))
    for plan in node_plan:
        node_level = next(row["level"] for row in output_graph["nodes"] if row["node_id"] == plan["node_id"])
        by_level[node_level] = int(by_level.get(node_level, 0)) + 1
    output_graph["counts"]["lesson_count_by_level"] = by_level
    require(output_graph["counts"]["required_mastery_node_count"], len(output_graph["a2_lock_contract"]["required_mastery_node_ids"]), "required_mastery_denominator")
    output_graph["m12g_reassessment_overlay"] = {
        "task_id": TASK_ID, "schema_version": SCHEMA_VERSION,
        "source_session_bank_sha256": bank_hash, "pending_node_count": len(node_plan),
        "required_attempt_count": len(tasks), "private_local_only": True,
    }

    output_consumer["asset_records"] = sorted(output_consumer["asset_records"], key=lambda row: row["asset_key"])
    output_consumer["lesson_catalog"] = sorted(output_consumer["lesson_catalog"], key=lambda row: row["lesson_id"])
    output_consumer["counts"]["asset_record_count"] = len(output_consumer["asset_records"])
    output_consumer["counts"]["lesson_count"] = len(output_consumer["lesson_catalog"])
    output_consumer["counts"]["learning_lesson_count"] = sum(row.get("level") in {"A1", "A1+"} for row in output_consumer["lesson_catalog"])
    output_consumer["m12g_reassessment_overlay"] = {
        "task_id": TASK_ID, "schema_version": SCHEMA_VERSION,
        "source_session_bank_sha256": bank_hash, "pending_node_count": len(node_plan),
        "required_attempt_count": len(tasks), "private_local_only": True,
    }

    package_core = {
        "task_id": TASK_ID, "schema_version": PACKAGE_SCHEMA_VERSION, "private_local_only": True,
        "learner_id": learner_id, "pending_node_count": len(node_plan),
        "required_attempt_count": len(tasks), "node_plan": node_plan,
        "tasks": sorted(tasks, key=lambda row: (row["node_id"], row["attempt_order"], row["task_instance_id"])),
        "claim_boundaries": {
            "answer_material_included": False, "scoring_rubric_included": False,
            "a2_content_included": False, "public_delivery": False,
            "mastery_claimed_before_import": False,
        },
    }
    return output_graph, output_consumer, {**package_core, "package_sha256": digest(package_core)}, node_plan


def html_ui(package: Mapping[str, Any]) -> str:
    data = json.dumps({
        "task_id": package["task_id"], "package_sha256": package["package_sha256"],
        "learner_id": package["learner_id"], "tasks": package["tasks"],
    }, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html><meta charset='utf-8'><title>M12G Reassessment</title><style>body{{font-family:system-ui;max-width:900px;margin:auto;padding:2rem}}article{{border:1px solid #aaa;padding:1rem;margin:1rem 0}}textarea,select,input{{width:100%;box-sizing:border-box;padding:.5rem}}</style><h1>M12G 重新評量</h1><label>Reviewer ID<input id='reviewer'></label><main id='root'></main><button id='save'>下載作答檔</button><script>const p={data},r=document.getElementById('root');p.tasks.forEach((t,i)=>{{const a=document.createElement('article'),c=t.learner_contract||{{}};a.innerHTML='<h2>'+(i+1)+'. '+String(c.prompt||'')+'</h2><textarea data-response></textarea>'+(t.human_review_required?'<fieldset><select data-decision><option></option><option>APPROVE</option><option>REJECT</option><option>DEFER</option></select><label><input type=checkbox data-c=grammar_target_match>grammar target</label><label><input type=checkbox data-c=meaning_matches_context>meaning/context</label><label><input type=checkbox data-c=complete_response>complete</label></fieldset>':'');r.appendChild(a)}});document.getElementById('save').onclick=()=>{{const now=new Date().toISOString(),reviewer=document.getElementById('reviewer').value.trim(),articles=[...r.children];const attempts=p.tasks.map((t,i)=>{{let raw=articles[i].querySelector('[data-response]').value,response=(t.learner_contract.response_mode||'').startsWith('ordered_')?raw.split('|').map(x=>x.trim()).filter(Boolean):raw,operator_review=null;if(t.human_review_required){{const f=articles[i].querySelector('fieldset');operator_review={{decision:f.querySelector('[data-decision]').value,reviewer_id:reviewer,reviewed_at:now,criteria:Object.fromEntries([...f.querySelectorAll('[data-c]')].map(x=>[x.dataset.c,x.checked])),notes:null}}}}return{{task_instance_id:t.task_instance_id,response,submitted_at:now,operator_review}}}});const out={{task_id:p.task_id,schema_version:'{REGISTRY_SCHEMA_VERSION}',private_local_only:true,package_sha256:p.package_sha256,learner_id:p.learner_id,attempts}},b=new Blob([JSON.stringify(out,null,2)],{{type:'application/json'}}),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='m12g_reassessment_response_registry.private.json';a.click();URL.revokeObjectURL(a.href)}};</script>"""


def prepare(
    *, source_bank_path: Path, base_consumer_path: Path, base_graph_path: Path,
    source_database_path: Path, resolved_root: Path, m12e1_root: Path,
    learner_id: str, display_label: str, target_root: Path,
) -> dict[str, Any]:
    target_root = output_root(target_root)
    graph_output = target_root / GRAPH_FILENAME
    consumer_output = target_root / CONSUMER_FILENAME
    database_output = target_root / DATABASE_FILENAME
    if database_output.exists():
        raise ReassessmentError("target_database_already_exists")
    _, bank_hash, bank_items = load_bank(source_bank_path)
    consumer, graph = load_consumer_graph(base_consumer_path, base_graph_path)
    require(consumer.get("m12f_dedicated_private_bridge_overlay", {}).get("source_session_bank_sha256"), bank_hash, "dedicated_bank_hash")
    state = database_state(source_database_path, base_consumer_path, base_graph_path, learner_id)
    new_graph, new_consumer, package, node_plan = build_overlay_and_package(
        bank_hash=bank_hash, bank_items=bank_items, consumer=consumer,
        graph=graph, source_state=state, learner_id=learner_id,
    )
    write_private(graph_output, new_graph)
    new_consumer["source_graph_sha256"] = file_sha(graph_output)
    new_consumer["m12g_reassessment_overlay"]["output_graph_sha256"] = new_consumer["source_graph_sha256"]
    write_private(consumer_output, new_consumer)
    bridge_result = bridge.import_resolved(
        source_bank_path=local_path(source_bank_path, "source_bank"),
        resolved_root=local_path(resolved_root, "resolved_root"),
        m12e1_root=local_path(m12e1_root, "m12e1_root"),
        consumer_path=consumer_output, graph_path=graph_output,
        database_path=database_output, learner_id=learner_id,
        display_label=display_label, output_root=target_root / "baseline_import",
    )
    require(bridge_result["safe_report"]["validation_status"], bridge.IMPORT_STATUS, "baseline_import_status")
    rebuilt = database_state(database_output, consumer_output, graph_output, learner_id)
    require({row["node_id"] for row in rebuilt["pending"]}, {row["node_id"] for row in node_plan}, "rebuilt_pending_partition")
    package.update({
        "source_session_bank_sha256": bank_hash,
        "source_consumer_sha256": file_sha(consumer_output),
        "source_graph_sha256": file_sha(graph_output),
    })
    package["package_sha256"] = digest({key: value for key, value in package.items() if key != "package_sha256"})
    package_path = target_root / PACKAGE_FILENAME
    template_path = target_root / TEMPLATE_FILENAME
    html_path = target_root / HTML_FILENAME
    write_private(package_path, package)
    write_private(template_path, {
        "task_id": TASK_ID, "schema_version": REGISTRY_SCHEMA_VERSION,
        "private_local_only": True, "package_sha256": package["package_sha256"],
        "learner_id": learner_id, "attempts": [{
            "task_instance_id": row["task_instance_id"], "response": None,
            "submitted_at": None,
            "operator_review": {
                "decision": None, "reviewer_id": None, "reviewed_at": None,
                "criteria": {"grammar_target_match": None, "meaning_matches_context": None, "complete_response": None},
                "notes": None,
            } if row["human_review_required"] else None,
        } for row in package["tasks"]],
    })
    html_path.write_text(html_ui(package), encoding="utf-8")
    os.chmod(html_path, 0o600)
    report = {
        "task_id": TASK_ID, "schema_version": SCHEMA_VERSION,
        "validation_status": PREPARE_STATUS,
        "pending_node_count": len(node_plan),
        "required_attempt_count": len(package["tasks"]),
        "human_review_required_count": sum(row["human_review_required"] for row in package["tasks"]),
        "node_plan": [{key: row[key] for key in (
            "node_id", "required_successful_attempt_count", "source_pass_count",
            "source_fail_count", "source_resolved_attempt_count",
        )} for row in node_plan],
        "a2_lock_state": new_graph["a2_lock_contract"]["state"],
        "claim_boundaries": {
            "real_reassessment_evidence_imported": False,
            "learner_response_included": False,
            "answer_material_included": False,
            "canonical_graph_modified": False,
            "a2_payload_access_granted": False,
            "public_delivery": False,
        },
        "stop_reason": "REAL_REASSESSMENT_EVIDENCE_REQUIRED",
        "next_short_step": TASK_ID,
    }
    write_private(target_root / PREPARE_REPORT_FILENAME, report)
    return {
        "report": report, "package_path": package_path,
        "template_path": template_path, "html_path": html_path,
        "consumer_path": consumer_output, "graph_path": graph_output,
        "database_path": database_output,
    }


def validate_registry(package: Mapping[str, Any], registry: Mapping[str, Any], learner_id: str) -> list[dict[str, Any]]:
    require(registry.get("task_id"), TASK_ID, "registry_task")
    require(registry.get("schema_version"), REGISTRY_SCHEMA_VERSION, "registry_schema")
    require(registry.get("private_local_only"), True, "registry_private")
    require(registry.get("package_sha256"), package.get("package_sha256"), "registry_package_hash")
    require(registry.get("learner_id"), learner_id, "registry_learner")
    attempts = registry.get("attempts")
    if not isinstance(attempts, list):
        raise ReassessmentError("registry_attempts_invalid")
    task_by_id = {str(row["task_instance_id"]): row for row in package["tasks"]}
    attempt_by_id = {str(row.get("task_instance_id")): row for row in attempts if isinstance(row, Mapping)}
    require(set(attempt_by_id), set(task_by_id), "registry_attempt_partition")
    require(len(attempt_by_id), len(attempts), "registry_attempt_identity")
    ordered: list[dict[str, Any]] = []
    for task in package["tasks"]:
        row = dict(attempt_by_id[task["task_instance_id"]])
        timezone_timestamp(row.get("submitted_at"), f"submitted_at_invalid:{task['task_instance_id']}")
        response = row.get("response")
        if task["response_type"] == "string_array":
            if not isinstance(response, list) or not response or not all(isinstance(value, str) and value.strip() for value in response):
                raise ReassessmentError(f"response_string_array_required:{task['task_instance_id']}")
        elif not isinstance(response, str) or not response.strip():
            raise ReassessmentError(f"response_string_required:{task['task_instance_id']}")
        review = row.get("operator_review")
        if task["human_review_required"]:
            if not isinstance(review, Mapping):
                raise ReassessmentError(f"operator_review_required:{task['task_instance_id']}")
            if review.get("decision") not in m6.REVIEW_DECISIONS:
                raise ReassessmentError(f"operator_review_decision_invalid:{task['task_instance_id']}")
            if not isinstance(review.get("reviewer_id"), str) or not review["reviewer_id"].strip():
                raise ReassessmentError(f"operator_reviewer_required:{task['task_instance_id']}")
            timezone_timestamp(review.get("reviewed_at"), f"reviewed_at_invalid:{task['task_instance_id']}")
            criteria = review.get("criteria")
            keys = {"grammar_target_match", "meaning_matches_context", "complete_response"}
            if not isinstance(criteria, Mapping) or set(criteria) != keys or any(criteria[key] not in {True, False} for key in keys):
                raise ReassessmentError(f"operator_review_criteria_invalid:{task['task_instance_id']}")
        elif review not in (None, {}):
            raise ReassessmentError(f"deterministic_review_forbidden:{task['task_instance_id']}")
        row["task"] = task
        ordered.append(row)
    timestamps = [datetime.fromisoformat(row["submitted_at"].replace("Z", "+00:00")) for row in ordered]
    if timestamps != sorted(timestamps):
        raise ReassessmentError("registry_attempt_timestamp_order_invalid")
    return ordered


def prior_receipt(target_db: Path, registry_hash: str) -> dict[str, Any] | None:
    connection = sqlite3.connect(target_db)
    try:
        connection.row_factory = sqlite3.Row
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='m12g_receipts'").fetchone():
            return None
        row = connection.execute("SELECT report_json FROM m12g_receipts WHERE registry_sha256=?", (registry_hash,)).fetchone()
        return json.loads(row["report_json"]) if row else None
    finally:
        connection.close()


def persist_receipt(temp_db: Path, registry_hash: str, report: Mapping[str, Any]) -> None:
    connection = sqlite3.connect(temp_db)
    try:
        connection.execute("CREATE TABLE IF NOT EXISTS m12g_receipts(registry_sha256 TEXT PRIMARY KEY,report_json TEXT NOT NULL,report_sha256 TEXT NOT NULL,imported_at TEXT NOT NULL)")
        connection.execute("INSERT INTO m12g_receipts VALUES(?,?,?,?)", (
            registry_hash, json.dumps(report, ensure_ascii=False, sort_keys=True),
            digest(report), m6.utc(),
        ))
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ReassessmentError("sqlite_integrity_failed")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ReassessmentError("sqlite_foreign_key_failed")
        connection.commit()
    finally:
        connection.close()


def backup_database(source: Path, destination: Path) -> None:
    source_connection = sqlite3.connect(source)
    destination_connection = sqlite3.connect(destination)
    try:
        source_connection.backup(destination_connection)
        destination_connection.commit()
        if destination_connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ReassessmentError("stage_integrity_failed")
        if destination_connection.execute("PRAGMA foreign_key_check").fetchall():
            raise ReassessmentError("stage_foreign_key_failed")
    finally:
        destination_connection.close()
        source_connection.close()


def import_evidence(
    *, package_path: Path, registry_path: Path, consumer_path: Path,
    graph_path: Path, database_path: Path, learner_id: str, target_root: Path,
) -> dict[str, Any]:
    target_root = output_root(target_root)
    package = read_json(local_path(package_path, "package"), "package")
    require(package.get("package_sha256"), digest({key: value for key, value in package.items() if key != "package_sha256"}), "package_hash")
    require(package.get("schema_version"), PACKAGE_SCHEMA_VERSION, "package_schema")
    require(package.get("learner_id"), learner_id, "package_learner")
    consumer_path = local_path(consumer_path, "consumer")
    graph_path = local_path(graph_path, "graph")
    require(package.get("source_consumer_sha256"), file_sha(consumer_path), "package_consumer_hash")
    require(package.get("source_graph_sha256"), file_sha(graph_path), "package_graph_hash")
    registry = read_json(local_path(registry_path, "response_registry"), "response_registry")
    ordered = validate_registry(package, registry, learner_id)
    registry_hash = digest(registry)
    target_db = local_path(database_path, "database")
    replay = prior_receipt(target_db, registry_hash)
    if replay:
        replay["validation_status"] = REPLAY_STATUS
        write_private(target_root / IMPORT_REPORT_FILENAME, replay)
        return {"report": replay, "replayed": True}

    temporary_root = Path(tempfile.mkdtemp(prefix="m12g-", dir=str(target_db.parent)))
    temp_db = temporary_root / target_db.name
    stage_db = target_db.with_suffix(target_db.suffix + ".m12g.tmp")
    try:
        shutil.copy2(target_db, temp_db)
        database_state(temp_db, consumer_path, graph_path, learner_id)
        state = m3.LearnerStateStore(temp_db)
        response_store = m6.ResponseEvidenceStore(temp_db)
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in ordered:
            grouped[str(row["task"]["lesson_id"])].append(row)
        consumer = read_json(consumer_path, "consumer")
        outcomes: Counter[str] = Counter()
        attempt_ids: list[str] = []

        for lesson_id in sorted(grouped):
            rows = grouped[lesson_id]
            bundle = bridge._bundle(consumer, consumer_path, lesson_id, temporary_root / "bundles" / f"{digest(lesson_id)[:16]}.private.json")
            response_store.initialize(consumer_path=consumer_path, lesson_bundle_path=bundle)
            session_id = f"M12G:{digest([registry_hash, lesson_id])[:24]}"
            session = state.start_session(learner_id=learner_id, lesson_id=lesson_id, session_id=session_id, at=rows[0]["submitted_at"])
            version = int(session["session_version"])
            for row in rows:
                task = row["task"]
                session = state.record_exposure(session_id=session_id, asset_key=task["asset_key"], expected_session_version=version, at=row["submitted_at"])
                version = int(session["session_version"])
                attempt_id = f"M12G_ATT:{digest([registry_hash, task['task_instance_id']])[:24]}"
                captured = response_store.capture_response(
                    learner_id=learner_id, session_id=session_id,
                    asset_key=task["asset_key"], response=deepcopy(row["response"]),
                    expected_session_version=version, attempt_id=attempt_id,
                    submitted_at=row["submitted_at"],
                )
                version += 1
                outcome = str(captured["outcome"])
                if task["human_review_required"]:
                    review = row["operator_review"]
                    reviewed = response_store.review_response(
                        attempt_id=attempt_id, decision=str(review["decision"]),
                        reviewer_id=str(review["reviewer_id"]), criteria=review["criteria"],
                        notes=review.get("notes"), reviewed_at=review["reviewed_at"],
                    )
                    outcome = str(reviewed["outcome"])
                outcomes[outcome] += 1
                attempt_ids.append(attempt_id)
            state.end_session(session_id=session_id, outcome="COMPLETED", expected_session_version=version, at=rows[-1]["submitted_at"])

        evidence_times = [
            (row.get("operator_review") or {}).get("reviewed_at") if row["task"]["human_review_required"] else row["submitted_at"]
            for row in ordered
        ]
        latest_time = max(timezone_timestamp(value, "latest_timestamp_invalid") for value in evidence_times)
        snapshot_root = temporary_root / "m7"
        engine = m7.MasteryRemediationEngine(database_path=temp_db, graph_path=graph_path)
        engine.initialize()
        engine.build_snapshot(learner_id=learner_id, output_root=snapshot_root, created_at=latest_time)
        snapshot_path = snapshot_root / "a1fs_v1_m7_mastery_snapshot.private.json"
        validation = m7_validator.validate(temp_db, graph_path, snapshot_path)
        if validation["error_count"]:
            raise ReassessmentError(f"m7_validation_failed:{validation['errors']}")
        snapshot = read_json(snapshot_path, "m7_snapshot")
        target_nodes = {str(row["node_id"]) for row in package["node_plan"]}
        mastered = set(snapshot["mastered_node_ids"])
        closed = sorted(target_nodes & mastered)
        pending = sorted(
            str(row["node_id"]) for row in snapshot["reassessment_queue"]
            if str(row["node_id"]) in target_nodes and row["queue_state"] == "PENDING"
        )
        complete = len(closed) == len(target_nodes)
        report = {
            "task_id": TASK_ID, "schema_version": SCHEMA_VERSION,
            "validation_status": IMPORT_STATUS if complete else PARTIAL_STATUS,
            "imported_attempt_count": len(attempt_ids),
            "imported_outcome_counts": dict(sorted(outcomes.items())),
            "target_node_count": len(target_nodes),
            "closed_remediation_node_count": len(closed),
            "closed_node_ids": closed, "pending_node_ids": pending,
            "m7_validation_error_count": 0,
            "a2_lock_state": snapshot["a2_lock_state"],
            "claim_boundaries": {
                "learner_response_included": False,
                "reviewer_identity_included": False,
                "canonical_graph_modified": False,
                "a2_payload_access_granted": False,
                "public_delivery": False,
                "retention_confirmed": False,
            },
            "stop_reason": "NONE" if complete else "ADDITIONAL_REASSESSMENT_REQUIRED",
            "next_short_step": NEXT_AFTER_COMPLETE if complete else TASK_ID,
        }
        bridge._safe_scan(report)
        persist_receipt(temp_db, registry_hash, report)
        stage_db.unlink(missing_ok=True)
        backup_database(temp_db, stage_db)
        gc.collect()
        os.chmod(stage_db, 0o600)
        os.replace(stage_db, target_db)
        final_m7 = target_root / "m7"
        final_m7.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snapshot_path, final_m7 / snapshot_path.name)
        write_private(target_root / IMPORT_REPORT_FILENAME, report)
        return {"report": report, "replayed": False}
    finally:
        stage_db.unlink(missing_ok=True)
        shutil.rmtree(temporary_root, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_parser = commands.add_parser("prepare")
    prepare_parser.add_argument("--source-bank", type=Path, required=True)
    prepare_parser.add_argument("--base-consumer", type=Path, required=True)
    prepare_parser.add_argument("--base-graph", type=Path, required=True)
    prepare_parser.add_argument("--source-database", type=Path, required=True)
    prepare_parser.add_argument("--resolved-root", type=Path, required=True)
    prepare_parser.add_argument("--m12e1-root", type=Path, required=True)
    prepare_parser.add_argument("--learner-id", required=True)
    prepare_parser.add_argument("--display-label", default="M12G Reassessment Learner")
    prepare_parser.add_argument("--output-root", type=Path, required=True)
    import_parser = commands.add_parser("import")
    import_parser.add_argument("--package", type=Path, required=True)
    import_parser.add_argument("--response-registry", type=Path, required=True)
    import_parser.add_argument("--consumer", type=Path, required=True)
    import_parser.add_argument("--graph", type=Path, required=True)
    import_parser.add_argument("--database", type=Path, required=True)
    import_parser.add_argument("--learner-id", required=True)
    import_parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(
                source_bank_path=args.source_bank,
                base_consumer_path=args.base_consumer,
                base_graph_path=args.base_graph,
                source_database_path=args.source_database,
                resolved_root=args.resolved_root,
                m12e1_root=args.m12e1_root,
                learner_id=args.learner_id,
                display_label=args.display_label,
                target_root=args.output_root,
            )
            report = result["report"]
            shown = {
                "validation_status": report["validation_status"],
                "pending_node_count": report["pending_node_count"],
                "required_attempt_count": report["required_attempt_count"],
                "human_review_required_count": report["human_review_required_count"],
                "a2_lock_state": report["a2_lock_state"],
                "stop_reason": report["stop_reason"],
                "package": str(result["package_path"]),
                "html": str(result["html_path"]),
                "database": str(result["database_path"]),
            }
        else:
            result = import_evidence(
                package_path=args.package,
                registry_path=args.response_registry,
                consumer_path=args.consumer,
                graph_path=args.graph,
                database_path=args.database,
                learner_id=args.learner_id,
                target_root=args.output_root,
            )
            report = result["report"]
            shown = {
                "validation_status": report["validation_status"],
                "imported_attempt_count": report["imported_attempt_count"],
                "closed_remediation_node_count": report["closed_remediation_node_count"],
                "pending_node_ids": report["pending_node_ids"],
                "m7_validation_error_count": report["m7_validation_error_count"],
                "a2_lock_state": report["a2_lock_state"],
                "stop_reason": report["stop_reason"],
                "next_short_step": report["next_short_step"],
            }
        print(json.dumps(shown, ensure_ascii=False, sort_keys=True))
        return 0
    except (
        ReassessmentError, bridge.BridgeError, dedicated.DedicatedBridgeError,
        overlay.OverlayError, m3.StateStoreError, m6.ResponseEvidenceError,
        m7.MasteryError, m08.TextModeSessionError, OSError, sqlite3.Error,
        KeyError, TypeError, ValueError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
