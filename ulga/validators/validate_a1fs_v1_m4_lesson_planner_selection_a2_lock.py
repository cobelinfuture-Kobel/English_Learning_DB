#!/usr/bin/env python3
"""Independent validator for M4 planner decisions and A2 boundaries."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

TASK_ID = "A1FS-V1-M4_LessonPlannerSelectionAndA2Lock"
SCHEMA_VERSION = "a1fs.v1.m4.lesson_planner.v1"
STATUS = "PASS_A1FS_V1_M4_LESSON_PLANNER_AND_A2_LOCK_READY"
GRAPH_STATUS = "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE"
CONSUMER_STATUS = "PASS_A1FS_V1_M2_FOUR_SKILL_ASSET_BODY_CONSUMER_READY"
NEXT_SHORT_STEP = "A1FS-V1-M5_FourSkillRendererAndLearnerUI"


def _sha(value: bytes) -> str: return hashlib.sha256(value).hexdigest()
def _canonical(value: Any) -> str: return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); os.replace(tmp, path)


def validate(database_path: Path, consumer_path: Path, graph_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        consumer_raw = consumer_path.read_bytes(); consumer = json.loads(consumer_raw)
        graph_raw = graph_path.read_bytes(); graph = json.loads(graph_raw)
    except (OSError, json.JSONDecodeError) as exc:
        return {"validation_status": "FAIL_A1FS_V1_M4", "error_count": 1, "errors": [f"source_unreadable:{exc}"]}
    if consumer.get("validation_status") != CONSUMER_STATUS: errors.append("consumer_status_invalid")
    if graph.get("validation_status") != GRAPH_STATUS: errors.append("graph_status_invalid")
    if consumer.get("source_graph_sha256") != _sha(graph_raw): errors.append("consumer_graph_binding_invalid")
    required_count = len(graph.get("a2_lock_contract", {}).get("required_mastery_node_ids", []))
    catalog = {row["lesson_id"]: row for row in consumer.get("lesson_catalog", [])}
    if not database_path.is_file(): return {"validation_status": "FAIL_A1FS_V1_M4", "error_count": 1, "errors": ["database_missing"]}
    connection = sqlite3.connect(database_path); connection.row_factory = sqlite3.Row
    try:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok": errors.append("sqlite_integrity_failure")
        metadata = {row[0]: row[1] for row in connection.execute("SELECT key,value FROM planner_metadata")}
        expected = {"task_id": TASK_ID, "schema_version": SCHEMA_VERSION, "validation_status": STATUS,
                    "consumer_sha256": _sha(consumer_raw), "graph_sha256": _sha(graph_raw),
                    "a2_payload_access_granted": "false", "a2_session_start_granted": "false", "next_short_step": NEXT_SHORT_STEP}
        for key, value in expected.items():
            if metadata.get(key) != value: errors.append(f"planner_metadata_invalid:{key}")
        if connection.execute("SELECT COUNT(*) FROM learning_sessions WHERE level='A2'").fetchone()[0]: errors.append("a2_session_present")
        previous = "0" * 64; decision_count = 0
        for row in connection.execute("SELECT * FROM planner_decisions ORDER BY decision_seq"):
            decision_count += 1
            try: rationale = json.loads(row["rationale_json"])
            except json.JSONDecodeError:
                errors.append(f'planner_rationale_invalid:{row["plan_id"]}'); continue
            core = {"plan_id": row["plan_id"], "learner_id": row["learner_id"], "plan_status": row["plan_status"],
                    "selected_lesson_id": row["selected_lesson_id"], "selected_skill": row["selected_skill"], "selected_level": row["selected_level"],
                    "a2_lock_state": row["a2_lock_state"], "required_mastery_count": row["required_mastery_count"],
                    "missing_mastery_count": row["missing_mastery_count"], "state_snapshot_digest": row["state_snapshot_digest"],
                    "rationale": rationale, "created_at": row["created_at"]}
            expected_hash = _sha((previous + _canonical(core)).encode("utf-8"))
            if row["previous_hash"] != previous or row["decision_hash"] != expected_hash: errors.append(f'planner_decision_chain_invalid:{row["plan_id"]}')
            previous = row["decision_hash"]
            if row["required_mastery_count"] != required_count: errors.append(f'planner_required_count_invalid:{row["plan_id"]}')
            selected = catalog.get(row["selected_lesson_id"]) if row["selected_lesson_id"] else None
            if row["plan_status"] in {"PLAN_LEARNING_LESSON", "RESUME_ACTIVE_SESSION"}:
                if not selected or selected["level"] not in {"A1", "A1+"} or row["a2_lock_state"] != "LOCKED": errors.append(f'learning_plan_boundary_invalid:{row["plan_id"]}')
            elif row["plan_status"] == "A2_HANDOFF_READY":
                if not selected or selected["level"] != "A2" or row["a2_lock_state"] != "HANDOFF_READY" or row["missing_mastery_count"] != 0: errors.append(f'a2_handoff_plan_invalid:{row["plan_id"]}')
            elif row["selected_lesson_id"] is not None: errors.append(f'awaiting_plan_selected_lesson:{row["plan_id"]}')
        profile_count = connection.execute("SELECT COUNT(*) FROM learner_profiles").fetchone()[0]
    except sqlite3.DatabaseError as exc:
        errors.append(f"sqlite_unreadable:{exc}"); decision_count = profile_count = 0
    finally: connection.close()
    return {"task_id": TASK_ID, "validation_status": STATUS if not errors else "FAIL_A1FS_V1_M4_LESSON_PLANNER_SELECTION_A2_LOCK",
            "error_count": len(errors), "errors": errors, "checked_decision_count": decision_count,
            "profile_count": profile_count, "required_mastery_node_count": required_count,
            "next_short_step": NEXT_SHORT_STEP if not errors else TASK_ID}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--database", type=Path, required=True); parser.add_argument("--consumer", type=Path, required=True); parser.add_argument("--graph", type=Path, required=True); parser.add_argument("--validation-report", type=Path, required=True)
    args = parser.parse_args(); report = validate(args.database, args.consumer, args.graph); _atomic(args.validation_report, report)
    print(json.dumps(report, ensure_ascii=False, indent=2)); return 0 if not report["errors"] else 1


if __name__ == "__main__": raise SystemExit(main())
