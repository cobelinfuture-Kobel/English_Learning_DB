#!/usr/bin/env python3
"""Migrate U01QB10 into the existing U01QB02 + Real62 runtime and replay all 474 items.

This milestone does not create a second QuestionBank, learner database, planner,
response-capture engine, or scoring engine. It reconciles the existing
u01qb02_item_catalog in place: the 48 U01QB01 base items retired by U01QB10 are
removed from the active catalog, the 48 U01QB10 production items are registered
through the same lesson_assets/response_contracts/U01QB02 tables, and the 186
RAZQ01E Real62 extension rows are preserved byte-for-byte by identity/hash.

Historical M6 response contracts and attempts for retired items are intentionally
retained. U01QB02 session-plan / exposure rows that directly reference retired
items are archived before deletion; M3 learner state and M6 attempts/scoring are
not deleted or rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as u01qb10
from ulga.builders import _razq01e_existing_qb_runtime_core as razq01e

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "In-place migration of already approved U01QB10 items into the existing "
    "U01QB02/M3/M6/Real62 runtime. No learner content, second QuestionBank, "
    "parallel planner, parallel learner database, parallel scoring authority, "
    "audio, Speaking scoring, Unit02-Unit24 content, or A2 content is produced."
)
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB11_Unit01ReconciledQuestionBankRuntimeMigrationAnd474Replay"
SCHEMA_VERSION = "a1fs.v1.u01qb11.unit01_reconciled_question_bank_runtime_migration_and_474_replay.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB11_UNIT01_RECONCILED_QUESTION_BANK_RUNTIME_MIGRATION_AND_474_REPLAY"
EXPECTED_BASE_COUNT = 288
EXPECTED_EXTENSION_COUNT = 186
EXPECTED_RUNTIME_COUNT = 474
EXPECTED_RETIRED_BASE_COUNT = 48
EXPECTED_PRODUCTION_ADDED_COUNT = 48
EXPECTED_SKILL_COUNTS = {"READING": 192, "SPEAKING": 87, "WRITING": 195}
EXPECTED_CAPTURE_ENABLED = 387
EXPECTED_AUTO_PASS_REPLAY = 351
EXPECTED_PENDING_HUMAN_REPLAY = 36
EXPECTED_SPEAKING_PRACTICE_ONLY = 87
EXPECTED_PRODUCTION_FAMILY_COUNTS = {
    u01qb10.PF13: 12,
    u01qb10.PF14: 24,
    u01qb10.PF15: 12,
}
DEFAULT_REPORT = Path("ulga/reports/a1fs_v1_u01qb11_unit01_runtime_migration_474_replay.json")
NEXT_SHORT_STEP = "A1FS-V1-U01QB12_Unit01ReferenceEvidenceAndPhraseConstructionPartialCoverageFullFix"

ARCHIVE_SQL = """
CREATE TABLE IF NOT EXISTS u01qb11_retired_runtime_history(
  archive_seq INTEGER PRIMARY KEY AUTOINCREMENT,
  record_type TEXT NOT NULL CHECK(record_type IN ('SESSION_PLAN','SESSION_ITEM','ITEM_EXPOSURE')),
  record_key TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  archived_at TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  UNIQUE(record_type,record_key,payload_sha256)
);
CREATE TABLE IF NOT EXISTS u01qb11_metadata(
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""


class RuntimeMigrationError(ValueError):
    """Fail-closed U01QB11 migration/replay error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _require_table(connection: sqlite3.Connection, name: str) -> None:
    if connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is None:
        raise RuntimeMigrationError(f"required_table_missing:{name}")


def _u01qb10_authority() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    candidate = u01qb10.build_candidate()
    approved = u01qb10.admit_candidate(candidate)
    from ulga.validators import validate_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as validator

    report = validator.validate_approved(candidate, approved)
    if report.get("error_count"):
        raise RuntimeMigrationError("u01qb10_authority_invalid:" + "|".join(report.get("errors") or []))
    items = approved.get("payload", {}).get("reconciled_items")
    if not isinstance(items, list) or len(items) != EXPECTED_BASE_COUNT:
        raise RuntimeMigrationError("u01qb10_reconciled_items_invalid")
    return approved, [deepcopy(dict(row)) for row in items]


def _extension_snapshot(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        """SELECT item_id,content_asset_id,skill,pattern_family_id,
                  approved_extension_artifact_sha256,extension_item_sha256
           FROM razq01e_extension_items ORDER BY item_id"""
    ).fetchall()
    if len(rows) != EXPECTED_EXTENSION_COUNT:
        raise RuntimeMigrationError(f"real62_extension_count_invalid:{len(rows)}")
    payload = [list(row) for row in rows]
    artifacts = {str(row[4]) for row in rows}
    if len(artifacts) != 1 or not next(iter(artifacts)):
        raise RuntimeMigrationError("real62_extension_artifact_identity_invalid")
    return {
        "count": len(rows),
        "item_ids": [str(row[0]) for row in rows],
        "artifact_sha256": next(iter(artifacts)),
        "identity_sha256": digest(payload),
    }


def _register_base_item(connection: sqlite3.Connection, item: Mapping[str, Any]) -> None:
    item_id = str(item["item_id"])
    skill = str(item["skill"])
    if skill not in qb02.UNIT01_LESSONS:
        raise RuntimeMigrationError(f"unsupported_skill:{item_id}:{skill}")
    lesson_id = qb02.UNIT01_LESSONS[skill]
    key = qb02.asset_key(item_id)
    item_digest = qb02.digest(item)
    role = qb02.item_role(item)
    response = qb02.m6_contract(item, lesson_id=lesson_id, key=key)
    contract_json = qb02.m6.canonical(response)
    contract_digest = qb02.m6.sha(response)

    existing_asset = connection.execute(
        "SELECT asset_id,lesson_id,content_digest FROM lesson_assets WHERE asset_key=?", (key,)
    ).fetchone()
    if existing_asset and (
        existing_asset["asset_id"] != item_id
        or existing_asset["lesson_id"] != lesson_id
        or existing_asset["content_digest"] != item_digest
    ):
        raise RuntimeMigrationError(f"lesson_asset_identity_drift:{item_id}")
    connection.execute(
        "INSERT OR IGNORE INTO lesson_assets(asset_key,asset_id,lesson_id,role,content_digest) VALUES(?,?,?,?,?)",
        (key, item_id, lesson_id, role, item_digest),
    )

    existing_contract = connection.execute(
        "SELECT lesson_id,contract_digest FROM response_contracts WHERE asset_key=?", (key,)
    ).fetchone()
    if existing_contract and (
        existing_contract["lesson_id"] != lesson_id
        or existing_contract["contract_digest"] != contract_digest
    ):
        raise RuntimeMigrationError(f"response_contract_identity_drift:{item_id}")
    connection.execute(
        """INSERT OR IGNORE INTO response_contracts
        (asset_key,lesson_id,skill,role,contract_json,contract_digest,capture_enabled)
        VALUES(?,?,?,?,?,?,?)""",
        (key, lesson_id, skill, role, contract_json, contract_digest, int(response["capture_enabled"])),
    )

    existing_item = connection.execute(
        "SELECT item_digest FROM u01qb02_item_catalog WHERE item_id=?", (item_id,)
    ).fetchone()
    if existing_item and existing_item["item_digest"] != item_digest:
        raise RuntimeMigrationError(f"item_catalog_identity_drift:{item_id}")
    connection.execute(
        """INSERT OR IGNORE INTO u01qb02_item_catalog
        (item_id,asset_key,lesson_id,skill,pattern_family_id,unit_pattern_id,support_level,
         assessment_eligible,transfer_eligible,capture_enabled,private_item_json,item_digest)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            item_id,
            key,
            lesson_id,
            skill,
            item["pattern_family_id"],
            item["unit_pattern_ids"][0],
            item["support_level"],
            int(item["assessment_eligible"]),
            int(item["transfer_eligible"]),
            int(response["capture_enabled"]),
            canonical(item),
            item_digest,
        ),
    )


def _archive_affected_history(
    connection: sqlite3.Connection, retired_ids: set[str], *, archived_at: str
) -> tuple[int, int]:
    if not retired_ids:
        return 0, 0
    placeholders = ",".join("?" for _ in retired_ids)
    ids = tuple(sorted(retired_ids))
    session_ids = {
        str(row[0])
        for row in connection.execute(
            f"SELECT DISTINCT session_id FROM u01qb02_session_items WHERE item_id IN ({placeholders})",
            ids,
        )
    }
    session_ids.update(
        str(row[0])
        for row in connection.execute(
            f"SELECT DISTINCT session_id FROM u01qb02_item_exposures WHERE item_id IN ({placeholders})",
            ids,
        )
    )
    archived = 0

    def archive(record_type: str, key: str, payload: Mapping[str, Any]) -> None:
        nonlocal archived
        raw = canonical(payload)
        connection.execute(
            """INSERT OR IGNORE INTO u01qb11_retired_runtime_history
            (record_type,record_key,payload_json,archived_at,payload_sha256)
            VALUES(?,?,?,?,?)""",
            (record_type, key, raw, archived_at, hashlib.sha256(raw.encode("utf-8")).hexdigest()),
        )
        archived += 1

    for session_id in sorted(session_ids):
        plan = connection.execute(
            "SELECT * FROM u01qb02_session_plans WHERE session_id=?", (session_id,)
        ).fetchone()
        if plan is not None:
            archive("SESSION_PLAN", session_id, dict(plan))
        for row in connection.execute(
            "SELECT * FROM u01qb02_session_items WHERE session_id=? ORDER BY item_position", (session_id,)
        ):
            archive("SESSION_ITEM", f"{session_id}:{row['item_position']}", dict(row))
        for row in connection.execute(
            "SELECT * FROM u01qb02_item_exposures WHERE session_id=? ORDER BY exposure_seq", (session_id,)
        ):
            archive("ITEM_EXPOSURE", str(row["exposure_id"]), dict(row))

    for session_id in sorted(session_ids):
        connection.execute("DELETE FROM u01qb02_item_exposures WHERE session_id=?", (session_id,))
        connection.execute("DELETE FROM u01qb02_session_items WHERE session_id=?", (session_id,))
        connection.execute("DELETE FROM u01qb02_session_plans WHERE session_id=?", (session_id,))
    return len(session_ids), archived


def migrate_runtime(database: Path) -> dict[str, Any]:
    database = Path(database)
    if not database.is_file():
        raise RuntimeMigrationError("learner_database_missing")
    approved, desired_items = _u01qb10_authority()
    desired_by_id = {str(row["item_id"]): row for row in desired_items}
    desired_ids = set(desired_by_id)
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(database)
    archived_at = utc_now()

    with runtime.write() as connection:
        connection.row_factory = sqlite3.Row
        for table in (
            "metadata",
            "lesson_catalog",
            "lesson_assets",
            "response_contracts",
            "response_attempts",
            "scoring_results",
            "u01qb02_metadata",
            "u01qb02_item_catalog",
            "u01qb02_session_plans",
            "u01qb02_session_items",
            "u01qb02_item_exposures",
            "razq01e_metadata",
            "razq01e_extension_items",
        ):
            _require_table(connection, table)
        connection.executescript(ARCHIVE_SQL)
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        if metadata.get("validation_status") != m3.STATUS:
            raise RuntimeMigrationError("m3_database_status_invalid")
        razq_metadata = dict(connection.execute("SELECT key,value FROM razq01e_metadata"))
        if razq_metadata.get("validation_status") != razq01e.PASS_STATUS:
            raise RuntimeMigrationError("real62_runtime_status_invalid")

        extension_before = _extension_snapshot(connection)
        extension_ids = set(extension_before["item_ids"])
        catalog_rows = connection.execute(
            "SELECT item_id,item_digest FROM u01qb02_item_catalog ORDER BY item_id"
        ).fetchall()
        current_ids = {str(row["item_id"]) for row in catalog_rows}
        current_base_ids = current_ids - extension_ids
        already_migrated = current_base_ids == desired_ids and len(current_ids) == EXPECTED_RUNTIME_COUNT

        if already_migrated:
            retired_ids: set[str] = set()
            missing_ids: set[str] = set()
            affected_session_count = 0
            archived_record_count = 0
        else:
            if len(current_ids) != EXPECTED_RUNTIME_COUNT or len(current_base_ids) != EXPECTED_BASE_COUNT:
                raise RuntimeMigrationError(
                    f"pre_migration_denominator_invalid:{len(current_ids)}:{len(current_base_ids)}"
                )
            retired_ids = current_base_ids - desired_ids
            missing_ids = desired_ids - current_base_ids
            if len(retired_ids) != EXPECTED_RETIRED_BASE_COUNT or len(missing_ids) != EXPECTED_PRODUCTION_ADDED_COUNT:
                raise RuntimeMigrationError(
                    f"u01qb10_delta_invalid:{len(retired_ids)}:{len(missing_ids)}"
                )
            affected_session_count, archived_record_count = _archive_affected_history(
                connection, retired_ids, archived_at=archived_at
            )
            placeholders = ",".join("?" for _ in retired_ids)
            connection.execute(
                f"DELETE FROM u01qb02_item_catalog WHERE item_id IN ({placeholders})",
                tuple(sorted(retired_ids)),
            )
            for item_id in sorted(missing_ids):
                _register_base_item(connection, desired_by_id[item_id])

        for item_id, item in desired_by_id.items():
            row = connection.execute(
                "SELECT item_digest FROM u01qb02_item_catalog WHERE item_id=?", (item_id,)
            ).fetchone()
            if row is None or row["item_digest"] != qb02.digest(item):
                raise RuntimeMigrationError(f"reconciled_base_identity_invalid:{item_id}")

        extension_after = _extension_snapshot(connection)
        if extension_after["identity_sha256"] != extension_before["identity_sha256"]:
            raise RuntimeMigrationError("real62_extension_identity_changed")
        total = int(connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0])
        extension_count = int(connection.execute("SELECT COUNT(*) FROM razq01e_extension_items").fetchone()[0])
        base_count = total - extension_count
        if (base_count, extension_count, total) != (
            EXPECTED_BASE_COUNT,
            EXPECTED_EXTENSION_COUNT,
            EXPECTED_RUNTIME_COUNT,
        ):
            raise RuntimeMigrationError(
                f"post_migration_denominator_invalid:{base_count}:{extension_count}:{total}"
            )

        combined_sha = digest(
            {
                "base_question_bank_artifact_sha256": approved["artifact_sha256"],
                "content_extension_artifact_sha256": extension_after["artifact_sha256"],
            }
        )
        qb02_values = {
            "base_source_bank_artifact_sha256": str(approved["artifact_sha256"]),
            "source_bank_artifact_sha256": combined_sha,
            "approved_item_count": str(EXPECTED_BASE_COUNT),
            "razq01e_extension_artifact_sha256": str(extension_after["artifact_sha256"]),
            "razq01e_extension_item_count": str(EXPECTED_EXTENSION_COUNT),
            "razq01e_combined_runtime_item_count": str(EXPECTED_RUNTIME_COUNT),
            "u01qb11_task_id": TASK_ID,
            "u01qb11_schema_version": SCHEMA_VERSION,
            "u01qb11_validation_status": PASS_STATUS,
            "u01qb11_base_revision": u01qb10.CANONICAL_REVISION,
            "u01qb11_next_short_step": NEXT_SHORT_STEP,
        }
        connection.executemany(
            "INSERT OR REPLACE INTO u01qb02_metadata(key,value) VALUES(?,?)", qb02_values.items()
        )
        connection.executemany(
            "INSERT OR REPLACE INTO razq01e_metadata(key,value) VALUES(?,?)",
            {
                "base_item_count": str(EXPECTED_BASE_COUNT),
                "combined_runtime_item_count": str(EXPECTED_RUNTIME_COUNT),
                "base_source_bank_artifact_sha256": str(approved["artifact_sha256"]),
                "combined_source_bank_sha256": combined_sha,
            }.items(),
        )
        migration_values = {
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "base_revision": u01qb10.CANONICAL_REVISION,
            "base_artifact_sha256": str(approved["artifact_sha256"]),
            "extension_artifact_sha256": str(extension_after["artifact_sha256"]),
            "combined_source_bank_sha256": combined_sha,
            "base_item_count": str(base_count),
            "extension_item_count": str(extension_count),
            "runtime_item_count": str(total),
            "next_short_step": NEXT_SHORT_STEP,
        }
        connection.executemany(
            "INSERT OR REPLACE INTO u01qb11_metadata(key,value) VALUES(?,?)", migration_values.items()
        )

    return {
        "validation_status": PASS_STATUS,
        "database": str(database),
        "already_migrated": already_migrated,
        "retired_base_item_count": len(retired_ids),
        "production_item_added_count": len(missing_ids),
        "affected_session_count": affected_session_count,
        "archived_runtime_history_record_count": archived_record_count,
        "base_item_count": EXPECTED_BASE_COUNT,
        "extension_item_count": EXPECTED_EXTENSION_COUNT,
        "combined_runtime_item_count": EXPECTED_RUNTIME_COUNT,
        "u01qb10_artifact_sha256": str(approved["artifact_sha256"]),
        "real62_extension_artifact_sha256": extension_after["artifact_sha256"],
        "real62_extension_identity_sha256": extension_after["identity_sha256"],
        "combined_source_bank_sha256": combined_sha,
        "m3_learner_state_rewritten": False,
        "m6_attempts_or_scoring_deleted": False,
        "historical_retired_response_contracts_preserved": True,
        "next_short_step": NEXT_SHORT_STEP,
    }


def _accepted_response(contract: Mapping[str, Any], private_item: Mapping[str, Any]) -> Any:
    mode = str(contract.get("scoring_mode") or "")
    if mode == "EXACT_SEQUENCE":
        value = list(contract.get("accepted_sequence") or [])
        if not value:
            raise RuntimeMigrationError("replay_sequence_answer_missing")
        return value
    texts = list(contract.get("accepted_texts") or [])
    if texts:
        return str(texts[0])
    answer = private_item.get("correct_answer")
    if isinstance(answer, str) and answer.strip():
        return answer
    raise RuntimeMigrationError("replay_text_answer_missing")


def replay_474(database: Path) -> dict[str, Any]:
    database = Path(database)
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """SELECT c.*,r.contract_json,r.contract_digest
               FROM u01qb02_item_catalog c
               JOIN response_contracts r USING(asset_key)
               ORDER BY c.skill,c.pattern_family_id,c.item_id"""
        ).fetchall()
        extension_ids = {
            str(row[0])
            for row in connection.execute(
                "SELECT item_id FROM razq01e_extension_items ORDER BY item_id"
            )
        }
    if len(rows) != EXPECTED_RUNTIME_COUNT or len(extension_ids) != EXPECTED_EXTENSION_COUNT:
        raise RuntimeMigrationError(f"replay_denominator_invalid:{len(rows)}:{len(extension_ids)}")

    skill_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    scoring_counts: Counter[str] = Counter()
    origin_counts: Counter[str] = Counter()
    auto_pass = 0
    pending_human = 0
    speaking_practice_only = 0
    capture_enabled = 0

    for row in rows:
        item_id = str(row["item_id"])
        private_item = json.loads(str(row["private_item_json"]))
        contract = json.loads(str(row["contract_json"]))
        if str(contract.get("m12_item_id") or "") != item_id:
            raise RuntimeMigrationError(f"m6_item_identity_invalid:{item_id}")
        if m6.sha(contract) != str(row["contract_digest"]):
            raise RuntimeMigrationError(f"m6_contract_digest_invalid:{item_id}")
        if qb02.digest(private_item) != str(row["item_digest"]):
            raise RuntimeMigrationError(f"private_item_digest_invalid:{item_id}")
        skill = str(row["skill"])
        family = str(row["pattern_family_id"])
        mode = str(contract["scoring_mode"])
        skill_counts[skill] += 1
        family_counts[family] += 1
        scoring_counts[mode] += 1
        origin_counts["REAL62_EXTENSION" if item_id in extension_ids else "U01QB10_BASE"] += 1

        if skill == "SPEAKING":
            if bool(row["capture_enabled"]) or bool(row["assessment_eligible"]):
                raise RuntimeMigrationError(f"speaking_boundary_invalid:{item_id}")
            if mode != "FEATURE_RUBRIC":
                raise RuntimeMigrationError(f"speaking_scoring_mode_invalid:{item_id}")
            speaking_practice_only += 1
            continue

        if not bool(row["capture_enabled"]) or not bool(row["assessment_eligible"]):
            raise RuntimeMigrationError(f"scored_item_capture_boundary_invalid:{item_id}")
        capture_enabled += 1
        response = _accepted_response(contract, private_item)
        outcome, _score = m6.ResponseEvidenceStore.score(contract, response)
        if mode == "FEATURE_RUBRIC":
            if outcome != "PENDING_HUMAN_REVIEW":
                raise RuntimeMigrationError(f"feature_rubric_replay_invalid:{item_id}:{outcome}")
            pending_human += 1
        else:
            if outcome != "AUTO_PASS":
                raise RuntimeMigrationError(f"deterministic_replay_invalid:{item_id}:{outcome}")
            auto_pass += 1

    if dict(sorted(skill_counts.items())) != EXPECTED_SKILL_COUNTS:
        raise RuntimeMigrationError(f"skill_distribution_invalid:{dict(skill_counts)}")
    for family_id, expected in EXPECTED_PRODUCTION_FAMILY_COUNTS.items():
        if family_counts.get(family_id) != expected:
            raise RuntimeMigrationError(f"production_family_count_invalid:{family_id}:{family_counts.get(family_id)}")
    if (
        capture_enabled != EXPECTED_CAPTURE_ENABLED
        or auto_pass != EXPECTED_AUTO_PASS_REPLAY
        or pending_human != EXPECTED_PENDING_HUMAN_REPLAY
        or speaking_practice_only != EXPECTED_SPEAKING_PRACTICE_ONLY
    ):
        raise RuntimeMigrationError(
            f"replay_outcome_denominator_invalid:{capture_enabled}:{auto_pass}:{pending_human}:{speaking_practice_only}"
        )
    core = {
        "runtime_item_count": len(rows),
        "base_item_count": origin_counts["U01QB10_BASE"],
        "extension_item_count": origin_counts["REAL62_EXTENSION"],
        "skill_distribution": dict(sorted(skill_counts.items())),
        "scoring_mode_distribution": dict(sorted(scoring_counts.items())),
        "production_family_counts": {
            key: family_counts[key] for key in EXPECTED_PRODUCTION_FAMILY_COUNTS
        },
        "capture_enabled_item_count": capture_enabled,
        "deterministic_auto_pass_replay_count": auto_pass,
        "feature_rubric_pending_human_replay_count": pending_human,
        "speaking_practice_only_count": speaking_practice_only,
        "m6_score_function_reused": True,
        "speaking_scoring_enabled": False,
    }
    return {**core, "replay_sha256": digest(core)}


def production_attempt_canary(
    database: Path,
    *,
    learner_id: str,
    session_id: str,
) -> dict[str, Any]:
    database = Path(database)
    state = m3.LearnerStateStore(database)
    try:
        profile = state.create_profile(
            learner_id=learner_id,
            display_label="U01QB11 Disposable Production Canary",
        )
    except m3.StateStoreError as exc:
        if "learner_profile_exists" not in str(exc):
            raise
        profile = state.profile_snapshot(learner_id)
    writing_lesson = qb02.UNIT01_LESSONS["WRITING"]
    with sqlite3.connect(database) as connection:
        active = connection.execute(
            "SELECT session_id,session_version FROM learning_sessions WHERE learner_id=? AND session_state='ACTIVE'",
            (learner_id,),
        ).fetchone()
    if active is not None:
        state.end_session(
            session_id=str(active[0]),
            outcome="ABANDONED",
            expected_session_version=int(active[1]),
        )
    session = state.start_session(
        learner_id=learner_id,
        lesson_id=writing_lesson,
        session_id=session_id,
        expected_profile_version=int(profile["profile_version"]),
    )
    store = m6.ResponseEvidenceStore(database)
    outcomes: dict[str, str] = {}
    attempt_ids: dict[str, str] = {}

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        selected = {
            family: connection.execute(
                """SELECT c.item_id,c.asset_key,c.private_item_json
                   FROM u01qb02_item_catalog c
                   WHERE c.pattern_family_id=? ORDER BY c.item_id LIMIT 1""",
                (family,),
            ).fetchone()
            for family in (u01qb10.PF13, u01qb10.PF14, u01qb10.PF15)
        }
    if any(row is None for row in selected.values()):
        raise RuntimeMigrationError("production_canary_family_missing")

    for family in (u01qb10.PF13, u01qb10.PF14, u01qb10.PF15):
        row = selected[family]
        snapshot = state.session_snapshot(session_id)
        exposed = state.record_exposure(
            session_id=session_id,
            asset_key=str(row["asset_key"]),
            expected_session_version=int(snapshot["session_version"]),
        )
        private_item = json.loads(str(row["private_item_json"]))
        response = private_item["correct_answer"]
        attempted = store.capture_response(
            learner_id=learner_id,
            session_id=session_id,
            asset_key=str(row["asset_key"]),
            response=response,
            expected_session_version=int(exposed["session_version"]),
        )
        outcomes[family] = str(attempted["outcome"])
        attempt_ids[family] = str(attempted["attempt_id"])

    final_snapshot = state.session_snapshot(session_id)
    state.end_session(
        session_id=session_id,
        outcome="COMPLETED",
        expected_session_version=int(final_snapshot["session_version"]),
    )
    expected = {
        u01qb10.PF13: "AUTO_PASS",
        u01qb10.PF14: "PENDING_HUMAN_REVIEW",
        u01qb10.PF15: "PENDING_HUMAN_REVIEW",
    }
    if outcomes != expected:
        raise RuntimeMigrationError(f"production_attempt_canary_invalid:{outcomes}")
    return {
        "learner_id": learner_id,
        "session_id": session_id,
        "lesson_id": writing_lesson,
        "attempt_count": 3,
        "outcomes": outcomes,
        "attempt_ids": attempt_ids,
        "m3_exposure_authority_reused": True,
        "m6_response_capture_reused": True,
        "m6_scoring_authority_reused": True,
        "speaking_capture_or_scoring_used": False,
    }


def run_acceptance(
    database: Path,
    *,
    run_attempt_canary: bool = False,
    canary_learner_id: str = "u01qb11-disposable-canary",
    canary_session_id: str = "u01qb11-disposable-writing-session",
) -> dict[str, Any]:
    migration = migrate_runtime(database)
    replay = replay_474(database)
    canary = (
        production_attempt_canary(
            database,
            learner_id=canary_learner_id,
            session_id=canary_session_id,
        )
        if run_attempt_canary
        else {"executed": False}
    )
    core = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "status": PASS_STATUS,
        "migration": migration,
        "replay_474": replay,
        "production_attempt_canary": canary,
        "boundaries": {
            "question_bank_total_expanded": False,
            "second_question_bank_created": False,
            "existing_u01qb02_runtime_reused": True,
            "existing_real62_extension_reused": True,
            "m3_learner_state_rewritten": False,
            "m6_attempts_or_scoring_deleted": False,
            "speaking_scoring_enabled": False,
            "unit02_to_unit24_modified": False,
            "a2_unlocked": False,
        },
        "next_short_step": NEXT_SHORT_STEP,
    }
    return {**core, "readback_sha256": digest(core)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--run-attempt-canary", action="store_true")
    parser.add_argument("--canary-learner-id", default="u01qb11-disposable-canary")
    parser.add_argument("--canary-session-id", default="u01qb11-disposable-writing-session")
    args = parser.parse_args(argv)
    try:
        report = run_acceptance(
            args.database,
            run_attempt_canary=args.run_attempt_canary,
            canary_learner_id=args.canary_learner_id,
            canary_session_id=args.canary_session_id,
        )
        from ulga.validators import validate_a1fs_v1_u01qb11_unit01_reconciled_question_bank_runtime_migration_and_474_replay as validator

        validator.validate_report(report)
        write_json(args.report, report)
    except (RuntimeMigrationError, m3.StateStoreError, m6.ResponseEvidenceError, sqlite3.Error, OSError, KeyError, TypeError, ValueError) as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB11_UNIT01_RECONCILED_QUESTION_BANK_RUNTIME_MIGRATION_AND_474_REPLAY")
        print(f"ERROR={exc}")
        return 1
    print(f"STATUS={PASS_STATUS}")
    print(f"RUNTIME_ITEM_COUNT={report['replay_474']['runtime_item_count']}")
    print(f"AUTO_PASS_REPLAY_COUNT={report['replay_474']['deterministic_auto_pass_replay_count']}")
    print(f"PENDING_HUMAN_REPLAY_COUNT={report['replay_474']['feature_rubric_pending_human_replay_count']}")
    print(f"SPEAKING_PRACTICE_ONLY_COUNT={report['replay_474']['speaking_practice_only_count']}")
    print(f"ATTEMPT_CANARY_EXECUTED={args.run_attempt_canary}")
    print(f"NEXT_SHORT_STEP={NEXT_SHORT_STEP}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
