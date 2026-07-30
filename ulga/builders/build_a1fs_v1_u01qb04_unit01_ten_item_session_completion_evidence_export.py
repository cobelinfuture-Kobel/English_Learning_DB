#!/usr/bin/env python3
"""Complete one clean Unit01 ten-item session and export existing M6/M12 evidence.

U01QB04 consumes a U01QB02 session plan and routes every learner response through
U01QB03, M3, and M6. It creates no alternative planner, session store, response
capture, scoring engine, mastery write, or evidence schema.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02,
)
from ulga.builders import (
    build_a1fs_v1_u01qb03_unit01_approved_variant_learner_renderer_real_attempt as qb03,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Consumes one existing U01QB02 ten-item session and routes supplied learner responses through U01QB03, M3, M6, and the existing M12-compatible evidence export; no learner content, planner, database, scoring authority, mastery, audio, A2 content, or Unit02-Unit24 content is produced."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB04_Unit01TenItemSessionCompletionAndEvidenceExportAcceptance"
SCHEMA_VERSION = "a1fs.v1.u01qb04.unit01_ten_item_session_completion.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB04_UNIT01_TEN_ITEM_SESSION_COMPLETION_EVIDENCE_EXPORT"
NEXT_SHORT_STEP = "A1FS-V1-U01QB05_Unit01FailedItemRemediationReassessmentAndCarryOverAcceptance"
SESSION_SIZE = qb02.SESSION_SIZE
FINAL_CLEAN_SESSION_VERSION = 1 + (SESSION_SIZE * 2) + 1
READBACK_NAME = "a1fs_v1_u01qb04_session_completion_readback.json"
PRIVATE_EVIDENCE_DIR = "private_evidence"
SAFE_READBACK_BLOCKED_KEYS = {
    "accepted_answers", "accepted_sequence", "accepted_texts", "answer_contract",
    "contract_json", "entries", "private_item_json", "response", "response_json",
    "responses", "rubric",
}


class SessionCompletionError(ValueError):
    """Fail-closed U01QB04 completion error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SessionCompletionError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise SessionCompletionError(f"{code}_not_object")
    return value


def assert_safe_readback(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if str(key) in SAFE_READBACK_BLOCKED_KEYS:
                raise SessionCompletionError(f"private_key_in_safe_readback:{key}")
            assert_safe_readback(child)
    elif isinstance(value, list):
        for child in value:
            assert_safe_readback(child)


def artifact_record(path: Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    return {"file_name": Path(path).name, "sha256": digest_bytes(raw), "bytes": len(raw)}


def selected_contracts(database: Path, session_id: str) -> list[dict[str, Any]]:
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT s.item_position,s.item_id,c.asset_key,c.capture_enabled,r.contract_json
               FROM u01qb02_session_items s
               JOIN u01qb02_item_catalog c USING(item_id)
               JOIN response_contracts r USING(asset_key)
               WHERE s.session_id=? ORDER BY s.item_position""",
            (session_id,),
        ).fetchall()
    return [
        {
            "item_position": int(row["item_position"]),
            "item_id": str(row["item_id"]),
            "asset_key": str(row["asset_key"]),
            "capture_enabled": bool(row["capture_enabled"]),
            "contract": json.loads(row["contract_json"]),
        }
        for row in rows
    ]


def preflight(
    *, database: Path, learner_id: str, session_id: str, responses: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, str]]:
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database)
    plan = runtime.assemble_session(learner_id=learner_id, session_id=session_id)
    if plan.get("skill") not in {"READING", "WRITING"}:
        raise SessionCompletionError("session_skill_not_ten_item_capture_eligible")
    contracts = selected_contracts(database, session_id)
    if len(contracts) != SESSION_SIZE:
        raise SessionCompletionError(f"selected_contract_count_invalid:{len(contracts)}")
    item_ids = [row["item_id"] for row in contracts]
    if set(responses) != set(item_ids):
        missing = sorted(set(item_ids) - set(responses))
        extra = sorted(set(responses) - set(item_ids))
        raise SessionCompletionError(f"response_map_identity_invalid:missing={missing}:extra={extra}")
    with sqlite3.connect(database) as connection:
        session = connection.execute(
            "SELECT learner_id,lesson_id,skill,level,session_state,session_version FROM learning_sessions WHERE session_id=?",
            (session_id,),
        ).fetchone()
        if not session or session[0] != learner_id or session[1] != plan["lesson_id"]:
            raise SessionCompletionError("session_identity_invalid")
        if session[2] != plan["skill"] or session[3] != "A1" or session[4] != "ACTIVE" or session[5] != 1:
            raise SessionCompletionError("clean_active_a1_session_required")
        exposure_count = connection.execute(
            "SELECT COUNT(*) FROM u01qb02_item_exposures WHERE session_id=?", (session_id,)
        ).fetchone()[0]
        attempt_count = connection.execute(
            "SELECT COUNT(*) FROM response_attempts WHERE session_id=?", (session_id,)
        ).fetchone()[0]
        export_count = connection.execute(
            "SELECT COUNT(*) FROM evidence_exports WHERE session_id=?", (session_id,)
        ).fetchone()[0]
    if exposure_count or attempt_count or export_count:
        raise SessionCompletionError(
            f"clean_session_required:exposures={exposure_count}:attempts={attempt_count}:exports={export_count}"
        )
    predicted: dict[str, str] = {}
    for row in contracts:
        if not row["capture_enabled"]:
            raise SessionCompletionError(f"selected_item_capture_disabled:{row['item_id']}")
        outcome, _score = m6.ResponseEvidenceStore.score(row["contract"], responses[row["item_id"]])
        if outcome == "PENDING_HUMAN_REVIEW":
            raise SessionCompletionError(f"deterministic_completion_required:{row['item_id']}")
        predicted[row["item_id"]] = outcome
    return plan, contracts, predicted


def complete_session(
    *,
    database: Path,
    learner_id: str,
    session_id: str,
    responses: Mapping[str, Any],
    output_root: Path,
    completed_at: str | None = None,
) -> dict[str, Any]:
    database = Path(database)
    output_root = Path(output_root)
    plan, contracts, predicted = preflight(
        database=database,
        learner_id=learner_id,
        session_id=session_id,
        responses=responses,
    )
    controller = qb03.LearnerAttemptController(
        database, learner_id=learner_id, session_id=session_id
    )
    current_version = 1
    results: list[dict[str, Any]] = []
    for row in contracts:
        result = controller.submit(
            item_id=row["item_id"],
            response=responses[row["item_id"]],
            expected_session_version=current_version,
        )
        if result.get("outcome") != predicted[row["item_id"]]:
            raise SessionCompletionError(f"scoring_outcome_drift:{row['item_id']}")
        current_version = int(result["session_version"])
        results.append({"item_id": row["item_id"], "outcome": result["outcome"]})
    ended = m3.LearnerStateStore(database).end_session(
        session_id=session_id,
        outcome="COMPLETED",
        expected_session_version=current_version,
        at=completed_at,
    )
    if ended.get("session_version") != FINAL_CLEAN_SESSION_VERSION:
        raise SessionCompletionError(
            f"final_session_version_invalid:{ended.get('session_version')}:{FINAL_CLEAN_SESSION_VERSION}"
        )
    private_root = output_root / PRIVATE_EVIDENCE_DIR
    export = m6.ResponseEvidenceStore(database).export_evidence(
        session_id=session_id,
        output_root=private_root,
        exported_at=completed_at,
    )
    registry_path = Path(export["registry_path"])
    m12_path = Path(export["m12_registry_path"])
    registry = load_json(registry_path, "m6_registry")
    m12_registry = load_json(m12_path, "m12_registry")
    outcomes = dict(sorted(Counter(row["outcome"] for row in results).items()))
    readback = {
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "session": {
            "session_id": session_id,
            "learner_id": learner_id,
            "lesson_id": plan["lesson_id"],
            "skill": plan["skill"],
            "level": "A1",
            "session_state": ended["session_state"],
            "session_version": ended["session_version"],
        },
        "counts": {
            "planned_item_count": SESSION_SIZE,
            "completed_item_count": len(results),
            "exposure_count": len(results),
            "attempt_count": len(results),
            "scoring_result_count": len(results),
            "m6_registry_entry_count": registry.get("attempt_count"),
            "m12_attempt_count": len(m12_registry.get("attempts", [])),
        },
        "outcome_distribution": outcomes,
        "source_lineage": {
            "session_runtime_task_id": qb02.TASK_ID,
            "learner_renderer_task_id": qb03.TASK_ID,
            "learner_state_task_id": m3.TASK_ID,
            "response_evidence_task_id": m6.TASK_ID,
            "source_plan_digest": plan["plan_digest"],
            "source_bank_sha256": plan["source_bank_sha256"],
        },
        "evidence_artifacts": {
            "m6_registry": artifact_record(registry_path),
            "m12_registry": artifact_record(m12_path),
        },
        "private_evidence": True,
        "legacy_allowlist_import_ready": bool(export["legacy_allowlist_import_ready"]),
        "claim_boundaries": {
            "parallel_planner_created": False,
            "parallel_learner_database_created": False,
            "parallel_response_capture_created": False,
            "parallel_scoring_created": False,
            "parallel_evidence_schema_created": False,
            "unit02_to_unit24_modified": False,
            "speaking_capture_enabled": False,
            "mastery_written": False,
            "retention_confirmed": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    if readback["counts"] != {
        "planned_item_count": 10,
        "completed_item_count": 10,
        "exposure_count": 10,
        "attempt_count": 10,
        "scoring_result_count": 10,
        "m6_registry_entry_count": 10,
        "m12_attempt_count": 10,
    }:
        raise SessionCompletionError(f"completion_count_invalid:{readback['counts']}")
    assert_safe_readback(readback)
    readback_path = output_root / READBACK_NAME
    atomic_json(readback_path, readback)
    return {**readback, "readback_path": str(readback_path)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--learner-id", required=True)
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args(argv)
    responses = load_json(args.responses, "responses")
    result = complete_session(
        database=args.database,
        learner_id=args.learner_id,
        session_id=args.session_id,
        responses=responses,
        output_root=args.output_root,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
