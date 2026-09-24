#!/usr/bin/env python3
"""Project the approved Unit 01 item bank into an additive coverage runtime.

S04 performs an isolated migration over the existing learner database and lesson
bundles. It appends thirteen approved items, adds metadata-only target and
denominator tables, and exposes deterministic learner coverage readback. Existing
tables, rows, contracts, attempts, scores, learner state, and V1.1 identities are
never rewritten.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlparse

from ulga.builders import build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review as s17
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s00_multistandard_denominator_and_lineage as s00,
)
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s03_fixed_multitype_item_bank as s03,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Projects an already-approved fixed item bank into an isolated additive runtime, "
    "adds metadata-only target/denominator tables, and reads exposure/attempt lineage. "
    "It creates no new content, changes no existing answer or scoring contract, "
    "infers no mastery, enables no audio or A2, and creates no parallel state engine."
)

PROGRAM_ID = "A1FS-ONLINE-V1.2-U01E"
TASK_ID = (
    "A1FS-ONLINE-V1.2-U01E-S04_"
    "Unit01MultiStandardLearnerCoverageRuntimeReadback"
)
SCHEMA_VERSION = "a1fs.online.v1_2.u01e.s04.coverage_runtime_readback.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_2_U01E_S04_COVERAGE_RUNTIME_READBACK"
PRODUCT_STATUS = "A1FS_V1_2_UNIT01_COVERAGE_RUNTIME_READY"
NEXT_SHORT_STEP = (
    "A1FS-ONLINE-V1.2-U01E-S05_"
    "Unit01V1_2ReleaseMigrationVisualAcceptanceAndRollback"
)
UNIT_ID = s03.s02.s01.m01.UNIT_ID
TARGET_TOTAL_ACTIVITY_COUNT = 24
TARGET_TOTAL_ASSET_COUNT = 277
EXPECTED_UNIT01_COUNTS = {"READING": 10, "WRITING": 8, "SPEAKING": 6}
TARGET_TABLE = "a1fs_u01e_asset_target_bindings"
DENOMINATOR_TABLE = "a1fs_u01e_coverage_denominators"
MIGRATION_TABLE = "a1fs_u01e_runtime_migrations"

TARGET_DIMENSIONS = (
    "EVP_SENSE",
    "EGP_ROW",
    "CANONICAL_CHUNK",
    "CONTEXT_PHRASE",
    "SENTENCE",
    "PATTERN",
    "KET_PREREQUISITE",
    "ASSESSMENT_PATTERN",
)
GLOBAL_DENOMINATOR_KEYS = {
    "EVP_SENSE": "evp_a1_sense_count",
    "EGP_ROW": "egp_a1_row_count",
    "CANONICAL_CHUNK": "a1_generator_safe_chunk_count",
    "PATTERN": "a1_generator_safe_pattern_count",
}

ADDITIVE_SCHEMA_SQL = f"""
CREATE TABLE IF NOT EXISTS {TARGET_TABLE} (
  asset_key TEXT PRIMARY KEY,
  unit_id TEXT NOT NULL,
  lesson_id TEXT NOT NULL,
  skill TEXT NOT NULL CHECK(skill IN ('READING','WRITING','SPEAKING')),
  question_type TEXT NOT NULL,
  learning_role TEXT NOT NULL,
  context_id TEXT NOT NULL,
  target_evp_sense_ids_json TEXT NOT NULL,
  target_egp_row_ids_json TEXT NOT NULL,
  target_chunk_ids_json TEXT NOT NULL,
  target_context_phrase_ids_json TEXT NOT NULL,
  target_sentence_ids_json TEXT NOT NULL,
  target_pattern_ids_json TEXT NOT NULL,
  target_ket_prerequisite_node_ids_json TEXT NOT NULL,
  cambridge_stage TEXT NOT NULL,
  assessment_pattern_ref TEXT NOT NULL,
  source_artifact_sha256 TEXT NOT NULL,
  FOREIGN KEY(asset_key) REFERENCES lesson_assets(asset_key)
);
CREATE INDEX IF NOT EXISTS idx_u01e_target_lesson ON {TARGET_TABLE}(lesson_id);
CREATE INDEX IF NOT EXISTS idx_u01e_target_skill ON {TARGET_TABLE}(skill);
CREATE TABLE IF NOT EXISTS {DENOMINATOR_TABLE} (
  dimension TEXT NOT NULL,
  denominator_key TEXT NOT NULL,
  denominator_count INTEGER,
  denominator_status TEXT NOT NULL,
  denominator_role TEXT NOT NULL,
  source_ref TEXT NOT NULL,
  PRIMARY KEY(dimension, denominator_key)
);
CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
  migration_id TEXT PRIMARY KEY,
  source_asset_count INTEGER NOT NULL,
  target_asset_count INTEGER NOT NULL,
  added_asset_count INTEGER NOT NULL,
  source_identity_sha256 TEXT NOT NULL,
  approved_item_bank_sha256 TEXT NOT NULL,
  applied_at TEXT NOT NULL
);
"""


class S04CoverageRuntimeError(ValueError):
    """Fail-closed S04 projection, migration, or coverage error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path: Path, code: str) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise S04CoverageRuntimeError(f"{code}_unreadable:{exc}") from exc
    if not isinstance(value, dict):
        raise S04CoverageRuntimeError(f"{code}_not_object")
    return value


def write_json(path: Path, value: Mapping[str, Any], *, private: bool = False) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(dict(value), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    if private:
        try:
            path.chmod(0o600)
        except OSError:
            pass


def table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def table_columns(connection: sqlite3.Connection, table: str) -> list[str]:
    return [str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")]


def table_rows(connection: sqlite3.Connection, table: str) -> list[list[Any]]:
    if not table_exists(connection, table):
        return []
    columns = table_columns(connection, table)
    if not columns:
        return []
    order = ",".join(columns)
    return [list(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY {order}")]


def protected_snapshot(database_path: Path) -> dict[str, Any]:
    protected_tables = (
        "metadata",
        "lesson_catalog",
        "learner_profiles",
        "learning_sessions",
        "lesson_progress",
        "state_events",
        "response_attempts",
        "scoring_results",
        "human_review_queue",
        "mastery_state",
        "error_diagnoses",
        "remediation_assignments",
        "reassessment_records",
        "review_schedule",
        "retention_state",
    )
    with sqlite3.connect(database_path) as connection:
        return {
            table: table_rows(connection, table)
            for table in protected_tables
            if table_exists(connection, table)
        }


def existing_catalog_snapshot(database_path: Path) -> dict[str, Any]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        lessons = [dict(row) for row in connection.execute("SELECT * FROM lesson_catalog ORDER BY lesson_id")]
        assets = [dict(row) for row in connection.execute("SELECT * FROM lesson_assets ORDER BY asset_key")]
        contracts = [dict(row) for row in connection.execute("SELECT * FROM response_contracts ORDER BY asset_key")]
    return {
        "lessons": lessons,
        "assets": assets,
        "contracts": contracts,
        "sha256": digest({"lessons": lessons, "assets": assets, "contracts": contracts}),
    }


def validate_source_bundles(bundles: Mapping[str, Any]) -> None:
    if len(bundles) != 72:
        raise S04CoverageRuntimeError(f"source_bundle_count_invalid:{len(bundles)}")
    total = 0
    for lesson_id, bundle in bundles.items():
        if not isinstance(bundle, Mapping):
            raise S04CoverageRuntimeError(f"source_bundle_not_object:{lesson_id}")
        lesson = bundle.get("lesson")
        assets = bundle.get("assets")
        if not isinstance(lesson, Mapping) or lesson.get("lesson_id") != lesson_id:
            raise S04CoverageRuntimeError(f"source_lesson_identity_invalid:{lesson_id}")
        if not isinstance(assets, list):
            raise S04CoverageRuntimeError(f"source_assets_invalid:{lesson_id}")
        total += len(assets)
    if total != 264:
        raise S04CoverageRuntimeError(f"source_asset_count_invalid:{total}")


def stable_asset_key(item_id: str) -> str:
    return f"A1FS_V1_2:{item_id}"


def lesson_id_for_skill(skill: str) -> str:
    try:
        return s03.s02.s01.m01.LESSON_IDS[skill]
    except KeyError as exc:
        raise S04CoverageRuntimeError(f"item_skill_invalid:{skill}") from exc


def learner_asset(item: Mapping[str, Any], approved_sha256: str) -> dict[str, Any]:
    skill = str(item["skill"])
    question_type = str(item["question_type"])
    interaction = item["interaction_contract"]
    payload: dict[str, Any] = {
        "prompt": item["prompt"],
        "stimulus": deepcopy(item["stimulus"]),
        "options": deepcopy(item["options"]),
        "support_text": item["explanation"],
        "question_type": question_type,
        "interaction_mode": interaction["interaction_mode"],
        "content_identity": {
            "approved_item_bank_sha256": approved_sha256,
            "candidate_item_id": item["candidate_item_id"],
            "semantic_signature": item["semantic_signature"],
            "unit_id": UNIT_ID,
            "context_id": item["context_id"],
        },
        "response_capture_enabled": bool(item["response_contract"]["capture_enabled"]),
        "recording_capture_required": False,
        "learning_role": item["learning_role"],
        "support_level": item["support_level"],
    }
    if question_type == "word_order":
        payload["writing_stage"] = "CONTROLLED_SEQUENCE"
    if skill == "SPEAKING":
        payload["model_language"] = item["acceptable_variants"][0]
        payload["evidence_policy"] = "EXPOSURE_ONLY_NO_SCORING_NO_MASTERY"
    return {
        "asset_key": stable_asset_key(str(item["candidate_item_id"])),
        "role": "CHK" if question_type in {"checkpoint_choice", "checkpoint_write"} else "PRD",
        "learner_payload": payload,
    }


def approved_item_bank(database_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate, safe_pack = s03.build_candidate(database_path)
    approved = s03.admit_candidate(candidate, safe_pack)
    if approved.get("artifact_role") != "APPROVED_CANONICAL_JSON":
        raise S04CoverageRuntimeError("s03_approved_role_invalid")
    if approved.get("admission", {}).get("status") != "APPROVED":
        raise S04CoverageRuntimeError("s03_approved_status_invalid")
    return approved, safe_pack


def overlay_bundles(
    source_bundles: Mapping[str, Any], approved: Mapping[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    validate_source_bundles(source_bundles)
    result = deepcopy(dict(source_bundles))
    items = approved.get("payload", {}).get("candidate_items")
    if not isinstance(items, list) or len(items) != 13:
        raise S04CoverageRuntimeError("approved_item_bank_count_invalid")
    added: list[dict[str, Any]] = []
    for item in items:
        lesson_id = lesson_id_for_skill(str(item["skill"]))
        bundle = result.get(lesson_id)
        if not isinstance(bundle, dict) or not isinstance(bundle.get("assets"), list):
            raise S04CoverageRuntimeError(f"target_lesson_bundle_missing:{lesson_id}")
        asset = learner_asset(item, str(approved["artifact_sha256"]))
        if any(row.get("asset_key") == asset["asset_key"] for row in bundle["assets"]):
            raise S04CoverageRuntimeError(f"new_asset_identity_collision:{asset['asset_key']}")
        bundle["assets"].append(asset)
        added.append({
            "asset_key": asset["asset_key"],
            "lesson_id": lesson_id,
            "role": asset["role"],
            "item": deepcopy(item),
        })
    total = sum(len(bundle["assets"]) for bundle in result.values())
    if total != TARGET_TOTAL_ASSET_COUNT:
        raise S04CoverageRuntimeError(f"target_asset_count_invalid:{total}")
    for skill, expected in EXPECTED_UNIT01_COUNTS.items():
        actual = len(result[lesson_id_for_skill(skill)]["assets"])
        if actual != expected:
            raise S04CoverageRuntimeError(f"unit01_skill_asset_count_invalid:{skill}:{actual}")
    unchanged = set(result) - set(s03.s02.s01.m01.LESSON_IDS.values())
    for lesson_id in unchanged:
        if result[lesson_id] != source_bundles[lesson_id]:
            raise S04CoverageRuntimeError(f"non_unit01_bundle_changed:{lesson_id}")
    return result, added


def binding_row_from_existing(row: Mapping[str, Any], source_sha256: str) -> dict[str, Any]:
    return {
        "asset_key": str(row["asset_key"]),
        "unit_id": UNIT_ID,
        "lesson_id": str(row["lesson_id"]),
        "skill": str(row["skill"]),
        "question_type": str(row["question_type"]),
        "learning_role": "EXISTING_BASELINE",
        "context_id": str(row["context_id"]),
        "target_evp_sense_ids": list(row.get("target_evp_sense_ids", [])),
        "target_egp_row_ids": list(row.get("target_egp_row_ids", [])),
        "target_chunk_ids": list(row.get("target_chunk_ids", [])),
        "target_context_phrase_ids": list(row.get("target_context_phrase_ids", [])),
        "target_sentence_ids": list(row.get("target_sentence_ids", [])),
        "target_pattern_ids": list(row.get("target_pattern_ids", [])),
        "target_ket_prerequisite_node_ids": list(row.get("target_ket_prerequisite_node_ids", [])),
        "cambridge_stage": str(row["cambridge_stage"]),
        "assessment_pattern_ref": str(row["assessment_pattern_ref"]),
        "source_artifact_sha256": source_sha256,
    }


def binding_row_from_item(
    asset_key: str, lesson_id: str, item: Mapping[str, Any], source_sha256: str
) -> dict[str, Any]:
    return {
        "asset_key": asset_key,
        "unit_id": UNIT_ID,
        "lesson_id": lesson_id,
        "skill": str(item["skill"]),
        "question_type": str(item["question_type"]),
        "learning_role": str(item["learning_role"]),
        "context_id": str(item["context_id"]),
        "target_evp_sense_ids": list(item["target_evp_sense_ids"]),
        "target_egp_row_ids": list(item["target_egp_row_ids"]),
        "target_chunk_ids": list(item["target_chunk_ids"]),
        "target_context_phrase_ids": list(item["target_context_phrase_ids"]),
        "target_sentence_ids": list(item["target_sentence_ids"]),
        "target_pattern_ids": list(item["target_pattern_ids"]),
        "target_ket_prerequisite_node_ids": list(item["target_ket_prerequisite_node_ids"]),
        "cambridge_stage": str(item["cambridge_stage"]),
        "assessment_pattern_ref": str(item["assessment_pattern_ref"]),
        "source_artifact_sha256": source_sha256,
    }


def target_bindings(
    *, approved: Mapping[str, Any], safe_pack: Mapping[str, Any], added: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    existing = [
        binding_row_from_existing(row, str(safe_pack["source_identity"]["s01_approved_sha256"]))
        for row in safe_pack["existing_asset_target_index"]
    ]
    new = [
        binding_row_from_item(
            str(row["asset_key"]), str(row["lesson_id"]), row["item"], str(approved["artifact_sha256"])
        )
        for row in added
    ]
    rows = sorted(existing + new, key=lambda row: row["asset_key"])
    if len(rows) != TARGET_TOTAL_ACTIVITY_COUNT or len({row["asset_key"] for row in rows}) != len(rows):
        raise S04CoverageRuntimeError("target_binding_denominator_invalid")
    return rows


def denominator_rows(m1_graph_path: Path, safe_pack: Mapping[str, Any]) -> list[dict[str, Any]]:
    authority, _ = s00.authority_denominators()
    ket, _ = s00.ket_denominators(m1_graph_path)
    cambridge, _ = s00.cambridge_denominators()
    inventory = safe_pack["target_inventory"]
    return [
        {
            "dimension": "EVP_SENSE",
            "denominator_key": "EVP_A1_SENSES",
            "denominator_count": authority["evp_a1_sense_count"],
            "denominator_status": "AVAILABLE",
            "denominator_role": "CURRENT_REQUIRED_AUTHORITY",
            "source_ref": authority["authority_scope_task_id"],
        },
        {
            "dimension": "EGP_ROW",
            "denominator_key": "EGP_A1_ROWS",
            "denominator_count": authority["egp_a1_row_count"],
            "denominator_status": "AVAILABLE",
            "denominator_role": "CURRENT_REQUIRED_AUTHORITY",
            "source_ref": authority["authority_scope_task_id"],
        },
        {
            "dimension": "CANONICAL_CHUNK",
            "denominator_key": "A1_GENERATOR_SAFE_CHUNKS",
            "denominator_count": authority["a1_generator_safe_chunk_count"],
            "denominator_status": "AVAILABLE",
            "denominator_role": "CURRENT_REQUIRED_AUTHORITY",
            "source_ref": authority["authority_scope_task_id"],
        },
        {
            "dimension": "PATTERN",
            "denominator_key": "A1_GENERATOR_SAFE_PATTERNS",
            "denominator_count": authority["a1_generator_safe_pattern_count"],
            "denominator_status": "AVAILABLE",
            "denominator_role": "CURRENT_REQUIRED_AUTHORITY",
            "source_ref": authority["authority_scope_task_id"],
        },
        {
            "dimension": "CONTEXT_PHRASE",
            "denominator_key": "UNIT01_SELECTED_CONTEXT_PHRASES",
            "denominator_count": len(inventory["context_phrase_ids"]),
            "denominator_status": "UNIT_LOCAL_ONLY",
            "denominator_role": "NOT_CANONICAL_CHUNK_COVERAGE",
            "source_ref": safe_pack["source_identity"]["s01_approved_sha256"],
        },
        {
            "dimension": "SENTENCE",
            "denominator_key": "UNIT01_APPROVED_SENTENCES",
            "denominator_count": len(inventory["sentence_ids"]),
            "denominator_status": "UNIT_LOCAL_ONLY",
            "denominator_role": "UNIT_CONTENT_DENOMINATOR",
            "source_ref": safe_pack["source_identity"]["s01_approved_sha256"],
        },
        {
            "dimension": "KET_PREREQUISITE",
            "denominator_key": "KET_REQUIRED_A1_A1PLUS_NODES",
            "denominator_count": ket["required_a1_a1plus_mastery_node_count"],
            "denominator_status": "AVAILABLE_BUT_ACTIVITY_BINDING_UNRESOLVED",
            "denominator_role": "CURRENT_REQUIRED_SKILL_DENOMINATOR",
            "source_ref": str(m1_graph_path.resolve()),
        },
        {
            "dimension": "ASSESSMENT_PATTERN",
            "denominator_key": "CAMBRIDGE_TASK_PATTERNS",
            "denominator_count": cambridge["assessment_pattern_count"],
            "denominator_status": "AVAILABLE",
            "denominator_role": "CURRENT_STAGE_TASK_PATTERN_BASELINE",
            "source_ref": s00.CAMBRIDGE_POLICY_PATH.as_posix(),
        },
        {
            "dimension": "CAMBRIDGE_CAPABILITY",
            "denominator_key": "STARTERS_MOVERS_GRANULAR_CAPABILITIES",
            "denominator_count": None,
            "denominator_status": "NOT_MATERIALIZED_IN_COMMITTED_POLICY",
            "denominator_role": "NO_PERCENTAGE_CLAIM_ALLOWED",
            "source_ref": s00.CAMBRIDGE_POLICY_PATH.as_posix(),
        },
        {
            "dimension": "FLYERS_A2_HANDOFF",
            "denominator_key": "FLYERS_A2_HANDOFF_LESSONS",
            "denominator_count": ket["a2_handoff_lesson_count"],
            "denominator_status": "HANDOFF_ONLY",
            "denominator_role": "EXCLUDED_FROM_CURRENT_COMPLETION",
            "source_ref": str(m1_graph_path.resolve()),
        },
    ]


def insert_binding(connection: sqlite3.Connection, row: Mapping[str, Any]) -> None:
    connection.execute(
        f"""INSERT INTO {TARGET_TABLE}(
        asset_key,unit_id,lesson_id,skill,question_type,learning_role,context_id,
        target_evp_sense_ids_json,target_egp_row_ids_json,target_chunk_ids_json,
        target_context_phrase_ids_json,target_sentence_ids_json,target_pattern_ids_json,
        target_ket_prerequisite_node_ids_json,cambridge_stage,assessment_pattern_ref,
        source_artifact_sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            row["asset_key"], row["unit_id"], row["lesson_id"], row["skill"],
            row["question_type"], row["learning_role"], row["context_id"],
            canonical(sorted(row["target_evp_sense_ids"])),
            canonical(sorted(row["target_egp_row_ids"])),
            canonical(sorted(row["target_chunk_ids"])),
            canonical(sorted(row["target_context_phrase_ids"])),
            canonical(sorted(row["target_sentence_ids"])),
            canonical(sorted(row["target_pattern_ids"])),
            canonical(sorted(row["target_ket_prerequisite_node_ids"])),
            row["cambridge_stage"], row["assessment_pattern_ref"], row["source_artifact_sha256"],
        ),
    )


def migrate_clone(
    *, source_database: Path, target_database: Path, added: Sequence[Mapping[str, Any]],
    bindings: Sequence[Mapping[str, Any]], denominator_values: Sequence[Mapping[str, Any]],
    approved: Mapping[str, Any], applied_at: str,
) -> dict[str, Any]:
    source_database = Path(source_database)
    target_database = Path(target_database)
    target_database.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_database, target_database)
    protected_before = protected_snapshot(target_database)
    catalog_before = existing_catalog_snapshot(target_database)
    with sqlite3.connect(target_database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        connection.executescript(ADDITIVE_SCHEMA_SQL)
        for row in added:
            item = row["item"]
            asset_key = str(row["asset_key"])
            content_digest = digest({
                "learner_payload": learner_asset(item, str(approved["artifact_sha256"]))["learner_payload"],
                "response_contract": item["response_contract"],
            })
            connection.execute(
                "INSERT INTO lesson_assets(asset_key,asset_id,lesson_id,role,content_digest) VALUES(?,?,?,?,?)",
                (asset_key, str(item["candidate_item_id"]), row["lesson_id"], row["role"], content_digest),
            )
            contract = deepcopy(item["response_contract"])
            capture = int(bool(contract.pop("capture_enabled")))
            connection.execute(
                """INSERT INTO response_contracts
                (asset_key,lesson_id,skill,role,capture_enabled,contract_json,contract_digest)
                VALUES(?,?,?,?,?,?,?)""",
                (
                    asset_key, row["lesson_id"], item["skill"], row["role"], capture,
                    canonical(contract), digest(contract),
                ),
            )
        for row in bindings:
            insert_binding(connection, row)
        for row in denominator_values:
            connection.execute(
                f"INSERT INTO {DENOMINATOR_TABLE} VALUES(?,?,?,?,?,?)",
                (
                    row["dimension"], row["denominator_key"], row["denominator_count"],
                    row["denominator_status"], row["denominator_role"], row["source_ref"],
                ),
            )
        connection.execute(
            f"INSERT INTO {MIGRATION_TABLE} VALUES(?,?,?,?,?,?,?)",
            (
                "U01E-S04-ADD-13", len(catalog_before["assets"]), TARGET_TOTAL_ASSET_COUNT,
                len(added), catalog_before["sha256"], approved["artifact_sha256"], applied_at,
            ),
        )
        if table_exists(connection, "metadata"):
            connection.executemany(
                "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
                {
                    "u01e_s04_task_id": TASK_ID,
                    "u01e_s04_schema_version": SCHEMA_VERSION,
                    "u01e_s04_validation_status": PASS_STATUS,
                    "u01e_s04_approved_item_bank_sha256": approved["artifact_sha256"],
                    "u01e_s04_asset_target_binding_count": str(len(bindings)),
                }.items(),
            )
        connection.commit()
    protected_after = protected_snapshot(target_database)
    if protected_after != protected_before:
        raise S04CoverageRuntimeError("protected_state_or_evidence_rows_changed")
    with sqlite3.connect(target_database) as connection:
        asset_count = int(connection.execute("SELECT COUNT(*) FROM lesson_assets").fetchone()[0])
        contract_count = int(connection.execute("SELECT COUNT(*) FROM response_contracts").fetchone()[0])
        binding_count = int(connection.execute(f"SELECT COUNT(*) FROM {TARGET_TABLE}").fetchone()[0])
        speaking_capture = int(connection.execute(
            "SELECT COUNT(*) FROM response_contracts WHERE skill='SPEAKING' AND capture_enabled=1"
        ).fetchone()[0])
    if (asset_count, contract_count, binding_count, speaking_capture) != (
        TARGET_TOTAL_ASSET_COUNT, TARGET_TOTAL_ASSET_COUNT, TARGET_TOTAL_ACTIVITY_COUNT, 0
    ):
        raise S04CoverageRuntimeError(
            f"migrated_denominator_invalid:{asset_count}:{contract_count}:{binding_count}:{speaking_capture}"
        )
    return {
        "source_catalog_sha256": catalog_before["sha256"],
        "source_protected_sha256": digest(protected_before),
        "target_protected_sha256": digest(protected_after),
        "source_asset_count": len(catalog_before["assets"]),
        "target_asset_count": asset_count,
        "response_contract_count": contract_count,
        "target_binding_count": binding_count,
        "added_asset_count": len(added),
        "speaking_capture_enabled_count": speaking_capture,
        "protected_state_preserved": True,
    }


def json_ids(row: Mapping[str, Any], column: str) -> list[str]:
    value = json.loads(str(row[column]))
    if not isinstance(value, list):
        raise S04CoverageRuntimeError(f"target_json_not_list:{column}")
    return [str(item) for item in value]


def load_bindings(connection: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    connection.row_factory = sqlite3.Row
    rows = connection.execute(f"SELECT * FROM {TARGET_TABLE} ORDER BY asset_key").fetchall()
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        result[str(row["asset_key"])] = {
            "asset_key": str(row["asset_key"]),
            "unit_id": str(row["unit_id"]),
            "lesson_id": str(row["lesson_id"]),
            "skill": str(row["skill"]),
            "question_type": str(row["question_type"]),
            "learning_role": str(row["learning_role"]),
            "context_id": str(row["context_id"]),
            "EVP_SENSE": json_ids(row, "target_evp_sense_ids_json"),
            "EGP_ROW": json_ids(row, "target_egp_row_ids_json"),
            "CANONICAL_CHUNK": json_ids(row, "target_chunk_ids_json"),
            "CONTEXT_PHRASE": json_ids(row, "target_context_phrase_ids_json"),
            "SENTENCE": json_ids(row, "target_sentence_ids_json"),
            "PATTERN": json_ids(row, "target_pattern_ids_json"),
            "KET_PREREQUISITE": json_ids(row, "target_ket_prerequisite_node_ids_json"),
            "ASSESSMENT_PATTERN": [str(row["assessment_pattern_ref"])],
            "cambridge_stage": str(row["cambridge_stage"]),
        }
    return result


def exposed_asset_keys(connection: sqlite3.Connection, learner_id: str) -> set[str]:
    if not table_exists(connection, "state_events"):
        return set()
    rows = connection.execute(
        "SELECT payload_json FROM state_events WHERE learner_id=? AND event_type='ASSET_EXPOSED'",
        (learner_id,),
    ).fetchall()
    result: set[str] = set()
    for row in rows:
        payload = json.loads(str(row[0]))
        if isinstance(payload, Mapping) and payload.get("asset_key"):
            result.add(str(payload["asset_key"]))
    return result


def attempted_asset_keys(connection: sqlite3.Connection, learner_id: str) -> tuple[set[str], int]:
    if not table_exists(connection, "response_attempts"):
        return set(), 0
    rows = connection.execute(
        "SELECT asset_key FROM response_attempts WHERE learner_id=?", (learner_id,)
    ).fetchall()
    return {str(row[0]) for row in rows}, len(rows)


def assessed_asset_keys(connection: sqlite3.Connection, learner_id: str) -> set[str]:
    if not table_exists(connection, "response_attempts") or not table_exists(connection, "scoring_results"):
        return set()
    rows = connection.execute(
        """SELECT DISTINCT a.asset_key FROM response_attempts a
        JOIN scoring_results s ON s.attempt_id=a.attempt_id
        WHERE a.learner_id=? AND s.outcome IS NOT NULL""",
        (learner_id,),
    ).fetchall()
    return {str(row[0]) for row in rows}


def dimension_targets(bindings: Mapping[str, Mapping[str, Any]], assets: Iterable[str], dimension: str) -> set[str]:
    result: set[str] = set()
    for asset_key in assets:
        row = bindings.get(asset_key)
        if row:
            result.update(str(value) for value in row.get(dimension, []))
    return result


def pct(numerator: int, denominator: int | None) -> float | None:
    if denominator is None or denominator <= 0:
        return None
    return round(numerator * 100.0 / denominator, 4)


def coverage_readback(database_path: Path, learner_id: str) -> dict[str, Any]:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        if not table_exists(connection, TARGET_TABLE) or not table_exists(connection, DENOMINATOR_TABLE):
            raise S04CoverageRuntimeError("coverage_runtime_tables_missing")
        profile = connection.execute(
            "SELECT profile_state FROM learner_profiles WHERE learner_id=?", (learner_id,)
        ).fetchone()
        if not profile or str(profile[0]) != "ACTIVE":
            raise S04CoverageRuntimeError("learner_profile_not_active")
        bindings = load_bindings(connection)
        all_assets = set(bindings)
        exposed_assets = exposed_asset_keys(connection, learner_id) & all_assets
        attempted_assets, attempt_count = attempted_asset_keys(connection, learner_id)
        attempted_assets &= all_assets
        assessed_assets = assessed_asset_keys(connection, learner_id) & all_assets
        denominator_rows_db = connection.execute(
            f"SELECT * FROM {DENOMINATOR_TABLE} ORDER BY dimension,denominator_key"
        ).fetchall()
    denominators = {
        str(row["dimension"]): {
            "denominator_key": str(row["denominator_key"]),
            "count": None if row["denominator_count"] is None else int(row["denominator_count"]),
            "status": str(row["denominator_status"]),
            "role": str(row["denominator_role"]),
        }
        for row in denominator_rows_db
    }
    dimensions: dict[str, Any] = {}
    for dimension in TARGET_DIMENSIONS:
        selected = dimension_targets(bindings, all_assets, dimension)
        exposed = dimension_targets(bindings, exposed_assets, dimension)
        practised = dimension_targets(bindings, attempted_assets, dimension)
        assessed = dimension_targets(bindings, assessed_assets, dimension)
        denominator = denominators.get(dimension, {}).get("count")
        dimensions[dimension] = {
            "denominator": denominator,
            "denominator_status": denominators.get(dimension, {}).get("status", "NOT_AVAILABLE"),
            "selected_count": len(selected),
            "exposed_count": len(exposed),
            "practised_count": len(practised),
            "assessed_count": len(assessed),
            "selected_percentage": pct(len(selected), denominator),
            "exposed_percentage": pct(len(exposed), denominator),
            "practised_percentage": pct(len(practised), denominator),
            "assessed_percentage": pct(len(assessed), denominator),
            "selected_ids": sorted(selected),
            "exposed_ids": sorted(exposed),
            "practised_ids": sorted(practised),
            "assessed_ids": sorted(assessed),
            "stable_count": None,
            "mastered_count": None,
            "transfer_proven_count": None,
            "stable_status": "NOT_AVAILABLE_FROM_CURRENT_EVIDENCE",
            "mastery_status": "NOT_AVAILABLE_FROM_CURRENT_EVIDENCE",
            "transfer_status": "NOT_AVAILABLE_FROM_CURRENT_EVIDENCE",
        }
    by_skill = Counter(row["skill"] for row in bindings.values())
    by_question_type = Counter(row["question_type"] for row in bindings.values())
    by_context = Counter(row["context_id"] for row in bindings.values())
    return {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "learner_id": learner_id,
        "unit_id": UNIT_ID,
        "activity_summary": {
            "selected_activity_count": len(bindings),
            "exposed_activity_count": len(exposed_assets),
            "distinct_practised_activity_count": len(attempted_assets),
            "attempt_count": attempt_count,
            "assessed_activity_count": len(assessed_assets),
            "by_skill": dict(sorted(by_skill.items())),
            "by_question_type": dict(sorted(by_question_type.items())),
            "by_context": dict(sorted(by_context.items())),
        },
        "coverage_dimensions": dimensions,
        "cambridge_stage_readback": {
            "unit01_stage": "STARTERS",
            "starters_unit_alignment_present": True,
            "granular_capability_percentage": None,
            "granular_capability_status": "NOT_MATERIALIZED_IN_COMMITTED_POLICY",
            "flyers_a2_handoff_excluded_from_current_completion": True,
        },
        "ket_readback": {
            "required_node_denominator": denominators["KET_PREREQUISITE"]["count"],
            "activity_binding_status": "UNRESOLVED_NO_EVIDENCE_BACKED_UNIT01_ACTIVITY_BRIDGE",
            "selected_node_count": dimensions["KET_PREREQUISITE"]["selected_count"],
            "practised_node_count": dimensions["KET_PREREQUISITE"]["practised_count"],
            "coverage_claim_allowed": False,
        },
        "semantic_boundaries": {
            "support_only_content_counted_as_practised": False,
            "context_phrases_counted_as_canonical_chunks": False,
            "duplicate_attempts_duplicate_distinct_coverage": False,
            "mastery_inferred_from_attempts": False,
            "runtime_free_generation_enabled": False,
            "speaking_capture_enabled": False,
            "audio_enabled": False,
            "a2_unlocked": False,
        },
    }


class CoverageReadbackApplication(s17.DashboardReviewApplication):
    def coverage_readback(self) -> dict[str, Any]:
        return coverage_readback(self.database_path, self.default_learner_id)

    def bootstrap(self) -> dict[str, Any]:
        value = super().bootstrap()
        value["u01e_coverage"] = self.coverage_readback()
        return value

    def progress_readback(self) -> dict[str, Any]:
        value = super().progress_readback()
        coverage = self.coverage_readback()
        value["u01e_coverage_summary"] = {
            "selected_activity_count": coverage["activity_summary"]["selected_activity_count"],
            "distinct_practised_activity_count": coverage["activity_summary"]["distinct_practised_activity_count"],
            "evp_practised_count": coverage["coverage_dimensions"]["EVP_SENSE"]["practised_count"],
            "egp_practised_count": coverage["coverage_dimensions"]["EGP_ROW"]["practised_count"],
        }
        return value


class CoverageReadbackHandler(s17.DashboardReviewHandler):
    @property
    def coverage_app(self) -> CoverageReadbackApplication:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/coverage":
            super().do_GET()
            return
        if not self._transport_valid():
            return
        claims = self._claims()
        if claims is None:
            self._json(401, {"error": "authentication_required"})
            return
        try:
            self._json(200, self.coverage_app.coverage_readback())
        except (S04CoverageRuntimeError, sqlite3.Error, ValueError) as exc:
            self._json(409, {"error": str(exc)})


class CoverageReadbackServer(s17.DashboardReviewServer):
    def __init__(self, address: tuple[str, int], app: CoverageReadbackApplication, secure_static_root: Path, config: Any):
        if not s17.s16.s15.s11._is_loopback(address[0]):
            raise S04CoverageRuntimeError(f"non_loopback_host_forbidden:{address[0]}")
        self.app = app
        self.static_root = Path(secure_static_root)
        self.secure_static_root = Path(secure_static_root)
        self.config = config
        super(s17.s16.s15.s11.SecureBoundaryServer, self).__init__(address, CoverageReadbackHandler)
        self.config.bind_local_port(int(self.server_address[1]))


def patch_static(source_root: Path, target_root: Path) -> dict[str, Any]:
    source_root = Path(source_root)
    target_root = Path(target_root)
    if target_root.exists():
        shutil.rmtree(target_root)
    shutil.copytree(source_root, target_root)
    index_path = target_root / "index.html"
    app_path = target_root / "app.js"
    css_path = target_root / "styles.css"
    for path in (index_path, app_path, css_path):
        if not path.is_file():
            raise S04CoverageRuntimeError(f"secure_static_file_missing:{path.name}")
    index = index_path.read_text(encoding="utf-8")
    marker = "</main>" if "</main>" in index else "</body>"
    panel = '''<section id="u01e-coverage-panel" class="panel u01e-coverage-panel">
      <div class="section-heading"><h2>Unit 01 多標準覆蓋</h2></div>
      <div id="u01e-coverage-summary" class="summary-grid"></div>
      <p id="u01e-coverage-state" class="note"></p>
    </section>'''
    if marker not in index:
        raise S04CoverageRuntimeError("secure_static_panel_marker_missing")
    index_path.write_text(index.replace(marker, panel + marker, 1), encoding="utf-8")
    app = app_path.read_text(encoding="utf-8")
    extension = r'''
const u01eCoverageSummary=document.querySelector('#u01e-coverage-summary'),u01eCoverageState=document.querySelector('#u01e-coverage-state');
function u01eMetric(label,value){const card=document.createElement('div'),strong=document.createElement('strong'),span=document.createElement('span');strong.textContent=value==null?'—':value;span.textContent=label;card.append(strong,span);return card;}
function renderU01eCoverage(value){const evp=value.coverage_dimensions.EVP_SENSE,egp=value.coverage_dimensions.EGP_ROW,patterns=value.coverage_dimensions.ASSESSMENT_PATTERN;u01eCoverageSummary.replaceChildren(u01eMetric('EVP 已練習',`${evp.practised_count}/${evp.denominator}`),u01eMetric('EGP 已練習',`${egp.practised_count}/${egp.denominator}`),u01eMetric('已練習活動',`${value.activity_summary.distinct_practised_activity_count}/${value.activity_summary.selected_activity_count}`),u01eMetric('題型覆蓋',`${patterns.selected_count}/${patterns.denominator}`));u01eCoverageState.textContent='熟練與精熟度只在既有 M7/M8 證據可用時顯示；目前不由單次作答推定。';}
async function loadU01eCoverage(){if(!u01eCoverageSummary)return;try{renderU01eCoverage(await api('/api/coverage'));}catch(error){u01eCoverageState.textContent=`覆蓋資料讀取失敗：${error.message}`;}}
window.addEventListener('load',loadU01eCoverage);
'''
    if "loadU01eCoverage" in app:
        raise S04CoverageRuntimeError("secure_static_coverage_patch_duplicate")
    app_path.write_text(app + "\n" + extension, encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    css_path.write_text(css + "\n.u01e-coverage-panel{border-width:2px}.u01e-coverage-panel strong{display:block;font-size:1.2rem}\n", encoding="utf-8")
    return {
        "coverage_panel_added": True,
        "coverage_endpoint": "/api/coverage",
        "runtime_free_generation_added": False,
    }


def materialize(
    *, source_database: Path, source_bundles_path: Path, m1_graph_path: Path,
    source_static_root: Path, output_root: Path, learner_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_bundles = read_json(source_bundles_path, "source_bundles")
    approved, safe_pack = approved_item_bank(source_database)
    bundles, added = overlay_bundles(source_bundles, approved)
    bindings = target_bindings(approved=approved, safe_pack=safe_pack, added=added)
    denominators = denominator_rows(m1_graph_path, safe_pack)
    root = Path(output_root).resolve() / "u01e_s04_coverage_runtime"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    target_database = root / "database/learner_runtime.sqlite3"
    migration = migrate_clone(
        source_database=source_database,
        target_database=target_database,
        added=added,
        bindings=bindings,
        denominator_values=denominators,
        approved=approved,
        applied_at="2026-07-28T00:00:00Z",
    )
    bundles_path = root / "runtime/bundles.private.json"
    write_json(bundles_path, bundles, private=True)
    static_root = root / "runtime/secure_static"
    static_result = patch_static(source_static_root, static_root)
    coverage = coverage_readback(target_database, learner_id)
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "source_identity": {
            "source_database_sha256": file_digest(source_database),
            "source_bundles_sha256": file_digest(source_bundles_path),
            "m1_graph_sha256": file_digest(m1_graph_path),
            "s03_approved_item_bank_sha256": approved["artifact_sha256"],
            "s02_safe_pack_sha256": safe_pack["pack_sha256"],
        },
        "runtime_outputs": {
            "root": str(root),
            "database_path": str(target_database),
            "bundles_path": str(bundles_path),
            "secure_static_root": str(static_root),
        },
        "migration_summary": migration,
        "bundle_summary": {
            "unit_count": 24,
            "lesson_count": 72,
            "asset_count": TARGET_TOTAL_ASSET_COUNT,
            "unit01_activity_count": TARGET_TOTAL_ACTIVITY_COUNT,
            "unit01_skill_counts": deepcopy(EXPECTED_UNIT01_COUNTS),
            "added_activity_count": 13,
            "preserved_activity_count": 264,
            "modified_lesson_count": 3,
            "preserved_lesson_count": 69,
        },
        "coverage_readback": coverage,
        "static_summary": static_result,
        "compatibility": {
            "additive_tables_only": True,
            "existing_table_shape_changed": False,
            "existing_response_contract_rows_changed": False,
            "existing_attempt_rows_changed": False,
            "existing_score_rows_changed": False,
            "existing_asset_rows_changed": False,
            "v1_1_read_compatibility_expected": True,
        },
        "boundaries": {
            "production_database_mutated": False,
            "learner_state_authority_changed": False,
            "scoring_authority_replaced": False,
            "mastery_inferred": False,
            "runtime_free_generation_enabled": False,
            "unit02_modified": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
        },
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    receipt = {**receipt_core, "artifact_sha256": digest(receipt_core)}
    safe_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "migration_summary": migration,
        "bundle_summary": receipt_core["bundle_summary"],
        "coverage_summary": {
            "activity_summary": coverage["activity_summary"],
            "dimension_counts": {
                key: {
                    field: value[field]
                    for field in ("denominator", "denominator_status", "selected_count", "exposed_count", "practised_count", "assessed_count")
                }
                for key, value in coverage["coverage_dimensions"].items()
            },
            "ket_readback": coverage["ket_readback"],
            "cambridge_stage_readback": coverage["cambridge_stage_readback"],
        },
        "compatibility": receipt_core["compatibility"],
        "boundaries": receipt_core["boundaries"],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    return receipt, safe


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--bundles", type=Path, required=True)
    parser.add_argument("--m1-graph", type=Path, required=True)
    parser.add_argument("--static-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--learner-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt, safe = materialize(
            source_database=args.database,
            source_bundles_path=args.bundles,
            m1_graph_path=args.m1_graph,
            source_static_root=args.static_root,
            output_root=args.output_root,
            learner_id=args.learner_id,
        )
        from ulga.validators import (
            validate_a1fs_online_v1_2_u01e_s04_coverage_runtime_readback as validator,
        )
        validation = validator.validate_outputs(receipt, safe)
        if validation["error_count"]:
            raise S04CoverageRuntimeError("validation_failed:" + "|".join(validation["errors"]))
        write_json(args.output, receipt, private=True)
        write_json(args.report, safe)
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0
    except (
        S04CoverageRuntimeError,
        s03.S03ItemBankError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"FAIL:{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
