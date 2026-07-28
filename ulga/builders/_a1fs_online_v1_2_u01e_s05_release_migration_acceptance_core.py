#!/usr/bin/env python3
"""Package, migrate, accept, and rollback the A1FS V1.2 Unit 01 release.

S05 consumes the approved S03 bank and S04 target registry. It appends thirteen
stable assets to the three existing Unit 01 lessons, stages additive database
rows, installs through the existing R01 atomic channel, proves authenticated
localhost behavior and coverage readback, then proves V1.1.1 can run against the
post-migration database before switching the isolated acceptance root to V1.2.0.
Production is never mutated by materialization.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import threading
import time
from copy import deepcopy
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse
from urllib.request import urlopen

from ulga.builders import _a1fs_online_v1_2_u01e_s05_static as static_adapter
from ulga.builders import _a1fs_v1_1_m02_release_core as m02_core
from ulga.builders import build_a1fs_online_v1_r01_self_contained_product_root_update_channel as r01
from ulga.builders import build_a1fs_online_v1_s17_learner_parent_teacher_dashboard_human_review_runtime as s17
from ulga.builders import build_a1fs_online_v1_2_u01e_s03_fixed_multitype_item_bank as s03
from ulga.builders import build_a1fs_online_v1_2_u01e_s04_multistandard_coverage_readback as s04
from ulga.builders import build_a1fs_v1_1_m01_unit01_cross_skill_vertical_slice as m01

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Packages and installs the already-approved S03 Unit 01 bank through R01, "
    "adds S04 readback tables/rows, and executes isolated update/rollback acceptance. "
    "It creates no unapproved learner content, alternate scoring/mastery authority, "
    "audio, A2 unlock, external route, or parallel curriculum/state engine."
)

PROGRAM_ID = "A1FS-ONLINE-V1.2-U01E"
TASK_ID = (
    "A1FS-ONLINE-V1.2-U01E-S05_"
    "Unit01V1_2ReleaseMigrationVisualAcceptanceAndRollback"
)
SCHEMA_VERSION = "a1fs.online.v1_2.u01e.s05.release_acceptance.v1"
PASS_STATUS = "PASS_A1FS_ONLINE_V1_2_U01E_S05_RELEASE_MIGRATION_ACCEPTANCE_ROLLBACK"
PRODUCT_STATUS = "A1FS_V1_2_UNIT01_MULTI_STANDARD_FIXED_ITEM_PRODUCT_READY"
SOURCE_VERSION = "1.1.1"
TARGET_VERSION = "1.2.0"
RELEASE_ID = "A1FS-ONLINE-V1.2-U01E-UNIT01-RC1"
MODULE = "ulga.builders.build_a1fs_online_v1_2_u01e_s05_release_migration_acceptance"
EXPECTED_UNIT_COUNT = 24
EXPECTED_LESSON_COUNT = 72
EXPECTED_SOURCE_ASSET_COUNT = 264
EXPECTED_TARGET_ASSET_COUNT = 277
EXPECTED_UNIT01_COUNTS = {"READING": 10, "WRITING": 8, "SPEAKING": 6}
NEXT_SHORT_STEP = "A1FS-ONLINE-V1.2-U01E-CLOSEOUT_ProgramCompletionReadback"
CANARY_LEARNER_ID = "A1FS_V1_2_U01E_S05_CANARY"
CANARY_SUBJECT_KEY = "A1FS_V1_2_U01E_S05_PRIVATE_CANARY"
CANARY_PASSWORD = "u01e-s05-local-canary"
CANARY_SESSION_SECRET = "u01e-s05-local-acceptance-session-secret-2026"


class S05ReleaseError(ValueError):
    """Fail-closed release, migration, runtime, or rollback error."""


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return r01.digest(value)


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


def _legacy_schema(database: Path) -> list[dict[str, str]]:
    with sqlite3.connect(database) as connection:
        return s04.legacy_schema(connection)


def _row_digest(connection: sqlite3.Connection, table: str, order: str) -> str:
    rows = [tuple(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall()]
    return digest(rows)


def _legacy_row_identity(database: Path) -> dict[str, Any]:
    with sqlite3.connect(database) as connection:
        names = s04.table_names(connection)
        result: dict[str, Any] = {}
        specs = {
            "lesson_assets": "asset_key",
            "response_contracts": "asset_key",
            "response_attempts": "attempt_id",
            "scoring_results": "attempt_id",
            "human_review_queue": "attempt_id",
            "learner_profiles": "learner_id",
            "learning_sessions": "session_id",
            "state_events": "event_seq",
        }
        for table, order in specs.items():
            if table in names:
                result[table] = {
                    "count": int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]),
                    "sha256": _row_digest(connection, table, order),
                }
        return result


def source_product(product_root: Path) -> dict[str, Any]:
    root = Path(product_root).resolve()
    version, manifest, bundles, sequence = r01._load_product(root)
    if version != SOURCE_VERSION:
        raise S05ReleaseError(f"source_product_version_invalid:{version}")
    if len(bundles) != EXPECTED_LESSON_COUNT or len(sequence) != EXPECTED_UNIT_COUNT:
        raise S05ReleaseError("source_product_denominator_invalid")
    source_asset_count = sum(len(row.get("assets", [])) for row in bundles.values())
    if source_asset_count != EXPECTED_SOURCE_ASSET_COUNT:
        raise S05ReleaseError(f"source_asset_denominator_invalid:{source_asset_count}")
    release_root = root / "releases" / version
    static_root = r01._resolve(root, str(manifest["secure_static_root"]))
    database = r01._resolve(root, str(manifest["shared_database_path"]))
    graph = r01._resolve(root, str(manifest["graph_path"]))
    auth = r01._resolve(root, str(manifest["shared_auth_state_path"]))
    state = r01._resolve(root, str(manifest["shared_learner_state_root"]))
    app_js = static_root / "app.js"
    if not all(path.exists() for path in (release_root, static_root, database, graph, auth, state, app_js)):
        raise S05ReleaseError("source_runtime_missing")
    text = app_js.read_text(encoding="utf-8")
    if "serializeTextResponse" not in text or "CONTROLLED_SEQUENCE" not in text:
        raise S05ReleaseError("source_exact_sequence_fullfix_missing")
    unit01_counts = {
        skill: len(bundles[m01.LESSON_IDS[skill]].get("assets", []))
        for skill in EXPECTED_UNIT01_COUNTS
    }
    if unit01_counts != m01.EXPECTED_LANE_COUNTS:
        raise S05ReleaseError(f"source_unit01_counts_invalid:{unit01_counts}")
    return {
        "root": root,
        "version": version,
        "manifest": manifest,
        "bundles": bundles,
        "sequence": sequence,
        "release_root": release_root,
        "static_root": static_root,
        "database": database,
        "graph": graph,
        "auth": auth,
        "state": state,
        "source_asset_count": source_asset_count,
        "shared_identity": m02_core.shared_identity(root),
        "legacy_schema": _legacy_schema(database),
        "legacy_rows": _legacy_row_identity(database),
    }


def approved_bank(database_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate, safe_pack = s03.build_candidate(database_path)
    approved = s03.admit_candidate(candidate, safe_pack)
    payload = approved.get("payload")
    if not isinstance(payload, Mapping):
        raise S05ReleaseError("s03_approved_payload_missing")
    if payload.get("new_candidate_item_count") != s04.EXPECTED_NEW_COUNT:
        raise S05ReleaseError("s03_approved_new_count_invalid")
    return approved, safe_pack


def lesson_for_skill(skill: str) -> str:
    try:
        return m01.LESSON_IDS[str(skill).upper()]
    except KeyError as exc:
        raise S05ReleaseError(f"unsupported_unit01_skill:{skill}") from exc


def learner_payload(item: Mapping[str, Any], approved_sha: str) -> dict[str, Any]:
    question_type = str(item["question_type"])
    interaction = item.get("interaction_contract", {})
    response_type = str(interaction.get("response_type") or "string")
    original_options = list(item.get("options", []))
    is_sequence = response_type == "sequence"
    skill = str(item["skill"])
    payload = {
        "prompt": str(item["prompt"]),
        "stimulus": deepcopy(item["stimulus"]),
        "options": [] if is_sequence else original_options,
        "token_bank": original_options if is_sequence else [],
        "support_text": (
            "Words: " + " / ".join(original_options)
            if is_sequence
            else f"題型：{question_type}；支援層級：{item['support_level']}"
        ),
        "question_type": question_type,
        "interaction_mode": str(interaction.get("interaction_mode") or ""),
        "response_type": response_type,
        "context_id": str(item["context_id"]),
        "learning_role": str(item["learning_role"]),
        "support_level": str(item["support_level"]),
        "cambridge_stage": str(item["cambridge_stage"]),
        "assessment_pattern_ref": str(item["assessment_pattern_ref"]),
        "target_refs": {
            key: list(item.get(key, []))
            for key in (
                "target_evp_sense_ids",
                "target_egp_row_ids",
                "target_chunk_ids",
                "target_context_phrase_ids",
                "target_sentence_ids",
                "target_pattern_ids",
                "target_ket_prerequisite_node_ids",
            )
        },
        "content_identity": {
            "approved_item_bank_sha256": approved_sha,
            "candidate_item_id": str(item["candidate_item_id"]),
            "semantic_signature": str(item["semantic_signature"]),
            "unit_id": m01.UNIT_ID,
        },
        "response_capture_enabled": skill != "SPEAKING",
        "recording_capture_required": False,
        "runtime_generation_used": False,
    }
    if skill == "SPEAKING":
        variants = item.get("acceptable_variants", [])
        if variants:
            payload["model_language"] = str(variants[0])
        payload["evidence_policy"] = "EXPOSURE_ONLY_NO_SCORING_NO_MASTERY"
    return payload


def runtime_asset(item: Mapping[str, Any], approved_sha: str) -> dict[str, Any]:
    key = str(item["candidate_item_id"])
    return {
        "asset_key": key,
        "asset_id": key,
        "lesson_id": lesson_for_skill(str(item["skill"])),
        "skill": str(item["skill"]),
        "level": "A1",
        "role": str(item["role"]),
        "learner_payload": learner_payload(item, approved_sha),
        "content_digest": digest({
            "candidate_item_id": key,
            "semantic_signature": item["semantic_signature"],
            "approved_sha": approved_sha,
        }),
    }


def contract_record(item: Mapping[str, Any], asset: Mapping[str, Any]) -> dict[str, Any]:
    contract = deepcopy(dict(item["response_contract"]))
    capture = bool(contract.pop("capture_enabled", str(item["skill"]) != "SPEAKING"))
    contract.update({
        "asset_key": asset["asset_key"],
        "lesson_id": asset["lesson_id"],
        "skill": asset["skill"],
        "role": asset["role"],
    })
    return {
        "asset_key": asset["asset_key"],
        "lesson_id": asset["lesson_id"],
        "skill": asset["skill"],
        "role": asset["role"],
        "capture_enabled": int(capture),
        "contract": contract,
        "contract_digest": digest(contract),
    }


def build_runtime_overlay(source: Mapping[str, Any]) -> dict[str, Any]:
    approved, safe_pack = approved_bank(Path(source["database"]))
    items = approved["payload"]["candidate_items"]
    assets = [runtime_asset(item, approved["artifact_sha256"]) for item in items]
    contracts = [contract_record(item, asset) for item, asset in zip(items, assets, strict=True)]
    bundles = deepcopy(dict(source["bundles"]))
    existing_keys = {
        str(asset["asset_key"])
        for bundle in bundles.values()
        for asset in bundle.get("assets", [])
    }
    for asset in assets:
        if asset["asset_key"] in existing_keys:
            raise S05ReleaseError(f"new_asset_identity_collision:{asset['asset_key']}")
        bundles[asset["lesson_id"]]["assets"].append(asset)
    for lesson_id in m01.LESSON_IDS.values():
        bundles[lesson_id]["assets"].sort(key=lambda row: str(row["asset_key"]))
    counts = {
        skill: len(bundles[m01.LESSON_IDS[skill]]["assets"])
        for skill in EXPECTED_UNIT01_COUNTS
    }
    if counts != EXPECTED_UNIT01_COUNTS:
        raise S05ReleaseError(f"target_unit01_counts_invalid:{counts}")
    total = sum(len(row.get("assets", [])) for row in bundles.values())
    if total != EXPECTED_TARGET_ASSET_COUNT:
        raise S05ReleaseError(f"target_asset_denominator_invalid:{total}")
    changed = [
        lesson_id for lesson_id in bundles
        if canonical(bundles[lesson_id]) != canonical(source["bundles"][lesson_id])
    ]
    if set(changed) != set(m01.LESSON_IDS.values()):
        raise S05ReleaseError(f"changed_lesson_set_invalid:{changed}")
    registry, _, _ = s04.build_registry(Path(source["database"]))
    active_registry = []
    for row in registry:
        copy = deepcopy(row)
        copy["runtime_status"] = "RUNTIME_ACTIVE"
        if copy["identity_kind"] == "APPROVED_CANDIDATE_ITEM_ID":
            copy["lesson_id"] = lesson_for_skill(copy["skill"])
        active_registry.append(copy)
    return {
        "approved": approved,
        "safe_pack": safe_pack,
        "items": items,
        "assets": assets,
        "contracts": contracts,
        "bundles": bundles,
        "target_registry": active_registry,
        "changed_lesson_ids": sorted(changed),
        "unit01_counts": counts,
        "asset_count": total,
    }


def target_manifest(source: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    manifest = r01._release_manifest(TARGET_VERSION)
    manifest.update({
        "schema_version": SCHEMA_VERSION,
        "release_id": RELEASE_ID,
        "source_product_version": SOURCE_VERSION,
        "content_release_task_id": s03.TASK_ID,
        "approved_content_sha256": overlay["approved"]["artifact_sha256"],
        "modified_unit_ids": [m01.UNIT_ID],
        "modified_lesson_ids": list(overlay["changed_lesson_ids"]),
        "unit_count": EXPECTED_UNIT_COUNT,
        "lesson_count": EXPECTED_LESSON_COUNT,
        "asset_count": EXPECTED_TARGET_ASSET_COUNT,
        "unit01_activity_count": s04.EXPECTED_TOTAL_COUNT,
        "unit01_reading_activity_count": EXPECTED_UNIT01_COUNTS["READING"],
        "unit01_writing_activity_count": EXPECTED_UNIT01_COUNTS["WRITING"],
        "unit01_speaking_practice_count": EXPECTED_UNIT01_COUNTS["SPEAKING"],
        "unit01_context_count": 5,
        "unit01_question_type_count": s04.EXPECTED_ASSESSMENT_PATTERN_COUNT,
        "unit01_target_registry_path": f"releases/{TARGET_VERSION}/runtime/unit01_target_registry.json",
        "serve_module": MODULE,
        "database_migration_mode": "ADDITIVE_ROWS_AND_TABLES_ONLY",
        "legacy_table_shape_changed": False,
        "v1_1_rollback_supported": True,
        "learner_submission_adapter": "CONTROLLED_SEQUENCE_OR_RESPONSE_TYPE_SEQUENCE_TO_TOKEN_LIST",
        "runtime_free_generation_allowed": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "speaking_capture_enabled": False,
        "a2_session_enabled": False,
    })
    return manifest


def build_candidate_release(
    *, source: Mapping[str, Any], overlay: Mapping[str, Any], package_root: Path, code_root: Path,
) -> tuple[Path, dict[str, Any]]:
    candidate = Path(package_root).resolve() / "release_candidate" / TARGET_VERSION
    if candidate.exists():
        shutil.rmtree(candidate)
    candidate.mkdir(parents=True)
    r01._copy_tree(Path(code_root).resolve() / "ulga", candidate / "app/ulga")
    static_result = static_adapter.patch_static(
        Path(source["static_root"]), candidate / "runtime/secure_static"
    )
    shutil.copy2(Path(source["graph"]), candidate / "runtime/graph.json")
    write_json(candidate / "runtime/bundles.json", overlay["bundles"])
    write_json(candidate / "runtime/sequence.json", source["sequence"])
    write_json(candidate / "runtime/unit01_target_registry.json", {
        "task_id": TASK_ID,
        "unit_id": m01.UNIT_ID,
        "item_count": len(overlay["target_registry"]),
        "items": overlay["target_registry"],
        "runtime_generation_allowed": False,
        "hidden_answers_included": False,
    })
    write_json(candidate / "VERSION.json", {
        "product_id": r01.PRODUCT_ID,
        "product_version": TARGET_VERSION,
        "release_id": RELEASE_ID,
        "content_release_task_id": s03.TASK_ID,
        "approved_content_sha256": overlay["approved"]["artifact_sha256"],
        "immutable_release": True,
    })
    write_json(candidate / "release_manifest.json", target_manifest(source, overlay))
    r01._write_checksums(candidate)
    manifest = r01.validate_release(candidate)
    if manifest.get("product_version") != TARGET_VERSION or manifest.get("asset_count") != EXPECTED_TARGET_ASSET_COUNT:
        raise S05ReleaseError("candidate_manifest_invalid")
    return candidate, static_result


def _insert_exact(connection: sqlite3.Connection, table: str, key_column: str, key: str, values: Sequence[Any], sql: str) -> None:
    exists = connection.execute(f"SELECT 1 FROM {table} WHERE {key_column}=?", (key,)).fetchone()
    if exists:
        raise S05ReleaseError(f"migration_identity_already_exists:{table}:{key}")
    connection.execute(sql, tuple(values))


def migrate_database(
    *, database_path: Path, overlay: Mapping[str, Any], m1_graph_path: Path,
    inject_failure: bool = False,
) -> dict[str, Any]:
    database_path = Path(database_path)
    before_schema = _legacy_schema(database_path)
    before_rows = _legacy_row_identity(database_path)
    source_sha = r01.file_digest(database_path)
    denominators = s04.denominator_contract(m1_graph_path, overlay["target_registry"])
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        names = s04.table_names(connection)
        required = {"lesson_assets", "response_contracts"}
        missing = required - names
        if missing:
            raise S05ReleaseError(f"migration_required_table_missing:{sorted(missing)[0]}")
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.executescript(s04.ADDITIVE_SQL)
            for asset in overlay["assets"]:
                _insert_exact(
                    connection,
                    "lesson_assets",
                    "asset_key",
                    asset["asset_key"],
                    (
                        asset["asset_key"], asset["asset_id"], asset["lesson_id"],
                        asset["role"], asset["content_digest"],
                    ),
                    "INSERT INTO lesson_assets(asset_key,asset_id,lesson_id,role,content_digest) VALUES(?,?,?,?,?)",
                )
            for record in overlay["contracts"]:
                _insert_exact(
                    connection,
                    "response_contracts",
                    "asset_key",
                    record["asset_key"],
                    (
                        record["asset_key"], record["lesson_id"], record["skill"], record["role"],
                        record["contract_digest"], canonical(record["contract"]), record["capture_enabled"],
                    ),
                    "INSERT INTO response_contracts(asset_key,lesson_id,skill,role,contract_digest,contract_json,capture_enabled) VALUES(?,?,?,?,?,?,?)",
                )
            for key, value in sorted(denominators.items()):
                connection.execute(
                    "INSERT OR REPLACE INTO u01e_coverage_denominators VALUES(?,?,?,?,?)",
                    (key, int(value["count"]), str(value["status"]), canonical(value), digest(value)),
                )
            for row in overlay["target_registry"]:
                binding = {
                    "identity_kind": row["identity_kind"],
                    "lesson_id": row["lesson_id"],
                    "context_id": row["context_id"],
                    "assessment_pattern_ref": row["assessment_pattern_ref"],
                    "cambridge_stage": row["cambridge_stage"],
                    "learning_role": row["learning_role"],
                    "support_level": row["support_level"],
                    "targets": row["targets"],
                    "semantic_signature": row["semantic_signature"],
                    "ket_binding_status": row["ket_binding_status"],
                }
                connection.execute(
                    "INSERT OR REPLACE INTO u01e_asset_target_bindings VALUES(?,?,?,?,?,?,?)",
                    (
                        row["item_key"], row["unit_id"], row["skill"], row["question_type"],
                        "RUNTIME_ACTIVE", canonical(binding), digest(binding),
                    ),
                )
            if inject_failure:
                raise S05ReleaseError("injected_migration_failure")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    after_schema = _legacy_schema(database_path)
    after_rows = _legacy_row_identity(database_path)
    if before_schema != after_schema:
        raise S05ReleaseError("legacy_schema_changed")
    for table, identity in before_rows.items():
        if table in {"lesson_assets", "response_contracts"}:
            continue
        if after_rows.get(table) != identity:
            raise S05ReleaseError(f"legacy_row_identity_changed:{table}")
    if after_rows["lesson_assets"]["count"] != before_rows["lesson_assets"]["count"] + s04.EXPECTED_NEW_COUNT:
        raise S05ReleaseError("lesson_asset_row_delta_invalid")
    if after_rows["response_contracts"]["count"] != before_rows["response_contracts"]["count"] + s04.EXPECTED_NEW_COUNT:
        raise S05ReleaseError("response_contract_row_delta_invalid")
    return {
        "source_database_sha256_before": source_sha,
        "migrated_database_sha256": r01.file_digest(database_path),
        "legacy_schema_unchanged": True,
        "legacy_non_target_rows_unchanged": True,
        "lesson_asset_rows_added": s04.EXPECTED_NEW_COUNT,
        "response_contract_rows_added": s04.EXPECTED_NEW_COUNT,
        "additive_tables": sorted(s04.ADDITIVE_TABLES),
        "target_binding_count": s04.EXPECTED_TOTAL_COUNT,
        "v1_1_compatible": True,
    }


def _restore_backup(product_root: Path, backup_root: Path, source_version: str) -> None:
    root = Path(product_root)
    r01._copy_sqlite(backup_root / "database/learner_runtime.sqlite3", root / "shared/database/learner_runtime.sqlite3")
    r01._copy_sqlite(backup_root / "auth/auth_state.sqlite3", root / "shared/auth/auth_state.sqlite3")
    source_state = backup_root / "learner_state/canonical_learning_state"
    target_state = root / "shared/learner_state/canonical_learning_state"
    r01._copy_tree(source_state, target_state)
    r01._switch_version(root, source_version)


def install_with_migration(
    *, product_root: Path, candidate: Path, overlay: Mapping[str, Any], inject_failure: bool = False,
) -> dict[str, Any]:
    product_root = Path(product_root).resolve()
    installed = r01.install_candidate(
        product_root=product_root, candidate=candidate, version=TARGET_VERSION
    )
    backup = Path(installed["backup_root"])
    database = product_root / "shared/database/learner_runtime.sqlite3"
    manifest = r01.validate_release(product_root / f"releases/{TARGET_VERSION}")
    graph = r01._resolve(product_root, str(manifest["graph_path"]))
    try:
        migration = migrate_database(
            database_path=database,
            overlay=overlay,
            m1_graph_path=graph,
            inject_failure=inject_failure,
        )
    except Exception:
        _restore_backup(product_root, backup, SOURCE_VERSION)
        target = product_root / f"releases/{TARGET_VERSION}"
        if target.exists():
            shutil.rmtree(target)
        raise
    return {**installed, "migration": migration}


def load_registry(product_root: Path, manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    path = r01._resolve(product_root, str(manifest.get("unit01_target_registry_path") or ""))
    value = r01.read_json(path, "unit01_target_registry")
    items = value.get("items")
    if not isinstance(items, list) or len(items) != s04.EXPECTED_TOTAL_COUNT:
        raise S05ReleaseError("target_registry_runtime_invalid")
    return [dict(row) for row in items if isinstance(row, Mapping)]


class V12Application(s17.DashboardReviewApplication):
    def __init__(self, *args: Any, target_registry: Sequence[Mapping[str, Any]], **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.target_registry = [dict(row) for row in target_registry]

    def bootstrap(self) -> dict[str, Any]:
        value = super().bootstrap()
        value.update({
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "product_status": PRODUCT_STATUS,
            "product_version": TARGET_VERSION,
        })
        value["learner_product_semantics"].update({
            "unit01_fixed_item_bank_connected": True,
            "unit01_activity_count": s04.EXPECTED_TOTAL_COUNT,
            "unit01_context_count": 5,
            "unit01_question_type_count": s04.EXPECTED_ASSESSMENT_PATTERN_COUNT,
            "unit01_coverage_readback_connected": True,
            "runtime_free_generation_allowed": False,
        })
        return value

    def completion_readiness(self, session_id: str) -> dict[str, Any]:
        session_id = str(session_id)
        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            session = connection.execute(
                "SELECT session_id,lesson_id,skill,session_state,session_version FROM learning_sessions WHERE session_id=?",
                (session_id,),
            ).fetchone()
            if not session:
                raise S05ReleaseError("session_not_found")
            skill = str(session["skill"]).upper()
            lesson_id = str(session["lesson_id"])
            if skill == "SPEAKING":
                return {
                    "session_id": session_id,
                    "lesson_id": lesson_id,
                    "skill": skill,
                    "session_state": str(session["session_state"]),
                    "session_version": int(session["session_version"]),
                    "gate_mode": "PRACTICE_SESSION_NO_SCORE",
                    "required_response_count": 0,
                    "attempted_response_count": 0,
                    "passed_response_count": 0,
                    "not_attempted_count": 0,
                    "retry_required_count": 0,
                    "pending_human_review_count": 0,
                    "completion_allowed": True,
                    "blocking_reason_codes": [],
                    "assets": [],
                    "mastery_claimed": False,
                }
            bundle = self.lesson_bundles.get(lesson_id)
            if not isinstance(bundle, Mapping):
                raise S05ReleaseError("session_bundle_missing")
            keys = [str(row["asset_key"]) for row in bundle.get("assets", [])]
            placeholders = ",".join("?" for _ in keys)
            rows = connection.execute(
                f"SELECT asset_key,contract_json FROM response_contracts WHERE capture_enabled=1 AND asset_key IN ({placeholders}) ORDER BY asset_key",
                keys,
            ).fetchall()
            contracts = {str(row["asset_key"]): json.loads(str(row["contract_json"])) for row in rows}
            if len(contracts) != len(keys) or not keys:
                raise S05ReleaseError(f"dynamic_contract_denominator_invalid:{lesson_id}:{len(keys)}:{len(contracts)}")
            latest_rows = connection.execute(
                "SELECT a.asset_key,a.attempt_sequence,s.outcome FROM response_attempts a JOIN scoring_results s USING(attempt_id) WHERE a.session_id=? ORDER BY a.asset_key,a.attempt_sequence DESC",
                (session_id,),
            ).fetchall()
            latest: dict[str, sqlite3.Row] = {}
            for row in latest_rows:
                latest.setdefault(str(row["asset_key"]), row)
            counts = {
                str(row["asset_key"]): int(row["count"])
                for row in connection.execute(
                    "SELECT asset_key,COUNT(*) AS count FROM response_attempts WHERE session_id=? GROUP BY asset_key",
                    (session_id,),
                ).fetchall()
            }
        assets: list[dict[str, Any]] = []
        blockers: list[str] = []
        passed = pending = retry = attempted = not_attempted = 0
        for index, key in enumerate(keys, start=1):
            row = latest.get(key)
            outcome = None if row is None else str(row["outcome"])
            if row is None:
                state = "NOT_ATTEMPTED"; not_attempted += 1; blockers.append("REQUIRED_RESPONSE_NOT_ATTEMPTED")
            elif outcome in {"AUTO_PASS", "HUMAN_APPROVE"}:
                state = "PASSED"; attempted += 1; passed += 1
            elif outcome in {"AUTO_FAIL", "HUMAN_REJECT"}:
                state = "RETRY_REQUIRED"; attempted += 1; retry += 1; blockers.append("LATEST_ATTEMPT_RETRY_REQUIRED")
            elif outcome in {"PENDING_HUMAN_REVIEW", "HUMAN_DEFER"}:
                state = "PENDING_HUMAN_REVIEW"; attempted += 1; pending += 1; blockers.append("HUMAN_REVIEW_PENDING")
            else:
                raise S05ReleaseError(f"unsupported_scoring_outcome:{outcome}")
            assets.append({
                "asset_index": index,
                "asset_key": key,
                "scoring_mode": str(contracts[key].get("scoring_mode") or ""),
                "human_review_fallback": bool(contracts[key].get("human_review_fallback")),
                "attempt_count": counts.get(key, 0),
                "latest_outcome": outcome,
                "completion_state": state,
            })
        blockers = list(dict.fromkeys(blockers))
        return {
            "session_id": session_id,
            "lesson_id": lesson_id,
            "skill": skill,
            "session_state": str(session["session_state"]),
            "session_version": int(session["session_version"]),
            "gate_mode": "DYNAMIC_BUNDLE_LATEST_ATTEMPT_PASS_OR_HUMAN_APPROVAL",
            "required_response_count": len(keys),
            "attempted_response_count": attempted,
            "passed_response_count": passed,
            "not_attempted_count": not_attempted,
            "retry_required_count": retry,
            "pending_human_review_count": pending,
            "completion_allowed": not blockers and passed == len(keys),
            "blocking_reason_codes": blockers,
            "assets": assets,
            "mastery_claimed": False,
        }

    def coverage_readback(self) -> dict[str, Any]:
        readback, _ = s04.build_readback(
            database_path=self.database_path,
            learner_id=self.default_learner_id,
            m1_graph_path=self.graph_path,
            registry=self.target_registry,
        )
        return readback

    def progress_readback(self) -> dict[str, Any]:
        value = super().progress_readback()
        coverage = self.coverage_readback()
        value.update({
            "task_id": TASK_ID,
            "schema_version": SCHEMA_VERSION,
            "validation_status": PASS_STATUS,
            "product_status": PRODUCT_STATUS,
            "product_version": TARGET_VERSION,
            "unit01_coverage_summary": {
                "curriculum_item_count": coverage["curriculum_item_count"],
                "practised_item_count": coverage["learner_evidence_summary"]["distinct_attempted_item_count"],
                "evp_practised_count": coverage["coverage_by_domain"]["evp_senses"]["practised_count"],
                "egp_practised_count": coverage["coverage_by_domain"]["egp_rows"]["practised_count"],
                "ket_activity_bridge_status": coverage["ket_prerequisite_readback"]["activity_bridge_status"],
            },
        })
        return value


class V12Handler(s17.DashboardReviewHandler):
    @property
    def v12_app(self) -> V12Application:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/unit01-coverage":
            super().do_GET()
            return
        if not self._transport_valid():
            return
        claims = self._claims()
        if claims is None:
            self._json(401, {"error": "authentication_required"})
            return
        try:
            self._json(200, self.v12_app.coverage_readback())
        except (S05ReleaseError, s17.DashboardReviewError, sqlite3.Error, ValueError) as exc:
            self._json(409, {"error": str(exc)})


class V12Server(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: V12Application, static_root: Path, config: Any):
        if not s17.s16.s15.s11._is_loopback(address[0]):
            raise S05ReleaseError(f"non_loopback_host_forbidden:{address[0]}")
        self.app = app
        self.static_root = Path(static_root)
        self.secure_static_root = Path(static_root)
        self.config = config
        super().__init__(address, V12Handler)
        self.config.bind_local_port(int(self.server_address[1]))


def make_app(
    *, database: Path, bundles: Mapping[str, Mapping[str, Any]], sequence: Mapping[str, int],
    graph_path: Path, state_root: Path, registry: Sequence[Mapping[str, Any]],
    learner_id: str = CANARY_LEARNER_ID,
) -> V12Application:
    return V12Application(
        database_path=database,
        bundles=bundles,
        sequence_by_grammar=sequence,
        graph_path=graph_path,
        state_root=state_root,
        default_learner_id=learner_id,
        target_registry=registry,
    )


def _passing_response(contract: Mapping[str, Any]) -> Any:
    mode = str(contract.get("scoring_mode") or "")
    if mode in {"EXACT_OPTION", "NORMALIZED_TEXT"} and contract.get("accepted_texts"):
        return str(contract["accepted_texts"][0])
    if mode == "EXACT_SEQUENCE" and contract.get("accepted_sequence"):
        return list(contract["accepted_sequence"])
    if mode == "FEATURE_RUBRIC":
        return "There is a birthday party in the park."
    raise S05ReleaseError(f"passing_response_unavailable:{mode}")


def _contracts(database: Path, lesson_id: str) -> list[dict[str, Any]]:
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT asset_key,contract_json FROM response_contracts WHERE lesson_id=? AND capture_enabled=1 ORDER BY asset_key",
            (lesson_id,),
        ).fetchall()
    result = []
    for row in rows:
        contract = json.loads(str(row["contract_json"])); contract["asset_key"] = str(row["asset_key"]); result.append(contract)
    return result


def exercise_scored_lesson(app: V12Application, database: Path, lesson_id: str, session_id: str, prefix: str) -> dict[str, Any]:
    contracts = _contracts(database, lesson_id)
    current = app.start_session({"lesson_id": lesson_id, "session_id": session_id, "at": f"{prefix}:00Z"})
    pending: list[str] = []
    for index, contract in enumerate(contracts, start=1):
        exposure = app.record_exposure({
            "session_id": session_id,
            "asset_key": contract["asset_key"],
            "expected_session_version": current["session_version"],
            "at": f"{prefix}:{index:02d}Z",
        })
        attempt_id = f"{session_id}:ATTEMPT:{index}"
        current = app.submit_response({
            "session_id": session_id,
            "asset_key": contract["asset_key"],
            "response": _passing_response(contract),
            "expected_session_version": exposure["session_version"],
            "attempt_id": attempt_id,
            "submitted_at": f"{prefix}:{index + 20:02d}Z",
        })
        if current.get("outcome") in {"PENDING_HUMAN_REVIEW", "HUMAN_DEFER"}:
            pending.append(attempt_id)
    for attempt_id in pending:
        app.review_attempt(
            {
                "attempt_id": attempt_id,
                "decision": "APPROVE",
                "criteria": {
                    "grammar_target_match": True,
                    "meaning_matches_context": True,
                    "complete_response": True,
                },
                "notes": "S05 isolated release acceptance",
                "reviewed_at": f"{prefix}:50Z",
            },
            reviewer_id="A1FS_V1_2_U01E_S05_REVIEWER",
        )
    readiness = app.completion_readiness(session_id)
    if readiness.get("completion_allowed") is not True or readiness.get("required_response_count") != len(contracts):
        raise S05ReleaseError(f"dynamic_completion_gate_failed:{lesson_id}")
    completed = app.complete_session({
        "session_id": session_id,
        "expected_session_version": readiness["session_version"],
        "at": f"{prefix}:55Z",
    })
    return {
        "lesson_id": lesson_id,
        "contract_count": len(contracts),
        "pending_human_review_count": len(pending),
        "completion_allowed": True,
        "session_completed": completed.get("session_state") == "COMPLETED",
    }


def authenticated_http_acceptance(
    *, app: V12Application, static_root: Path, auth_state: Path,
) -> dict[str, Any]:
    config = s17.s16.s15.s13.PersistentBoundaryConfig.from_values(
        username=CANARY_LEARNER_ID,
        password=CANARY_PASSWORD,
        session_secret=CANARY_SESSION_SECRET,
        mode="local",
        allowed_origin="http://127.0.0.1",
        allowed_host="127.0.0.1",
        revocation_db_path=auth_state,
        port=0,
    )
    server = V12Server(("127.0.0.1", 0), app, static_root, config)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start(); port = int(server.server_address[1]); origin = f"http://127.0.0.1:{port}"
    request = s17.s16.s15.s11._request
    try:
        request(port, "GET", "/api/unit01-coverage", expected_status=401)
        login, headers = request(
            port, "POST", "/auth/login",
            {"username": CANARY_LEARNER_ID, "password": CANARY_PASSWORD}, origin=origin,
        )
        cookie = str(headers.get("Set-Cookie") or "").split(";", 1)[0]
        if not cookie or not login.get("csrf_token"):
            raise S05ReleaseError("http_login_invalid")
        bootstrap, _ = request(port, "GET", "/api/bootstrap", cookie=cookie)
        progress, _ = request(port, "GET", "/api/progress", cookie=cookie)
        coverage, _ = request(port, "GET", "/api/unit01-coverage", cookie=cookie)
        rendered = json.dumps(bootstrap, ensure_ascii=False, sort_keys=True)
        if len(bootstrap.get("units", [])) != 24 or "U01E-S03-C05-W01" not in rendered:
            raise S05ReleaseError("http_bootstrap_expanded_item_bank_missing")
        if progress.get("product_version") != TARGET_VERSION:
            raise S05ReleaseError("http_progress_version_invalid")
        if coverage.get("curriculum_item_count") != s04.EXPECTED_TOTAL_COUNT:
            raise S05ReleaseError("http_coverage_denominator_invalid")
        return {
            "authenticated_login_pass": True,
            "bootstrap_pass": True,
            "progress_pass": True,
            "coverage_endpoint_pass": True,
            "unit_count": len(bootstrap.get("units", [])),
            "unit01_activity_count": coverage["curriculum_item_count"],
            "practised_item_count": coverage["learner_evidence_summary"]["distinct_attempted_item_count"],
        }
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


def v1_1_rollback_acceptance(
    *, product_root: Path, migrated_database: Path,
) -> dict[str, Any]:
    result = r01.rollback(product_root=product_root, version=SOURCE_VERSION)
    if r01._current_version(product_root) != SOURCE_VERSION:
        raise S05ReleaseError("rollback_version_switch_failed")
    version, _, bundles, _ = r01._load_product(product_root)
    if version != SOURCE_VERSION:
        raise S05ReleaseError("rollback_product_load_failed")
    old_counts = {
        skill: len(bundles[m01.LESSON_IDS[skill]]["assets"])
        for skill in EXPECTED_UNIT01_COUNTS
    }
    if old_counts != m01.EXPECTED_LANE_COUNTS:
        raise S05ReleaseError(f"rollback_old_bundle_counts_invalid:{old_counts}")
    with sqlite3.connect(migrated_database) as connection:
        old_contracts = int(connection.execute(
            "SELECT COUNT(*) FROM response_contracts WHERE asset_key NOT LIKE 'U01E-S03-%' AND lesson_id IN (?,?,?)",
            tuple(m01.LESSON_IDS.values()),
        ).fetchone()[0])
        new_contracts = int(connection.execute(
            "SELECT COUNT(*) FROM response_contracts WHERE asset_key LIKE 'U01E-S03-%'",
        ).fetchone()[0])
        attempt_rows = int(connection.execute("SELECT COUNT(*) FROM response_attempts").fetchone()[0])
    if old_contracts != 11 or new_contracts != 13:
        raise S05ReleaseError("rollback_database_compatibility_invalid")
    r01._switch_version(product_root, TARGET_VERSION)
    if r01._current_version(product_root) != TARGET_VERSION:
        raise S05ReleaseError("forward_after_rollback_failed")
    return {
        "rollback_status": result["status"],
        "v1_1_version_loaded": True,
        "v1_1_unit01_old_activity_count": 11,
        "post_migration_database_readable": True,
        "old_contract_count": old_contracts,
        "new_contract_rows_ignored_by_old_bundle": new_contracts,
        "attempt_rows_preserved": attempt_rows,
        "forward_switch_back_to_v1_2_pass": True,
    }


def run_acceptance(
    *, product_root: Path, source: Mapping[str, Any], overlay: Mapping[str, Any], static_result: Mapping[str, Any],
    screenshot_path: Path,
) -> dict[str, Any]:
    version, manifest, bundles, sequence = r01._load_product(product_root)
    if version != TARGET_VERSION or manifest.get("asset_count") != EXPECTED_TARGET_ASSET_COUNT:
        raise S05ReleaseError("installed_product_identity_invalid")
    database = r01._resolve(product_root, str(manifest["shared_database_path"]))
    auth = r01._resolve(product_root, str(manifest["shared_auth_state_path"]))
    state = r01._resolve(product_root, str(manifest["shared_learner_state_root"]))
    graph = r01._resolve(product_root, str(manifest["graph_path"]))
    static_root = r01._resolve(product_root, str(manifest["secure_static_root"]))
    registry = load_registry(product_root, manifest)
    app = make_app(
        database=database, bundles=bundles, sequence=sequence, graph_path=graph,
        state_root=state, registry=registry,
    )
    app.enroll(
        learner_id=CANARY_LEARNER_ID,
        display_label="A1FS V1.2 U01E S05 Canary",
        subject_key=CANARY_SUBJECT_KEY,
        at="2026-07-28T11:00:00Z",
    )
    coverage_before = app.coverage_readback()
    reading = exercise_scored_lesson(
        app, database, m01.LESSON_IDS["READING"], "U01E-S05:READING", "2026-07-28T11:01"
    )
    writing = exercise_scored_lesson(
        app, database, m01.LESSON_IDS["WRITING"], "U01E-S05:WRITING", "2026-07-28T11:02"
    )
    speaking_session = app.start_session({
        "lesson_id": m01.LESSON_IDS["SPEAKING"],
        "session_id": "U01E-S05:SPEAKING",
        "at": "2026-07-28T11:03:00Z",
    })
    for index, asset in enumerate(bundles[m01.LESSON_IDS["SPEAKING"]]["assets"], start=1):
        speaking_session = app.record_exposure({
            "session_id": "U01E-S05:SPEAKING",
            "asset_key": asset["asset_key"],
            "expected_session_version": speaking_session["session_version"],
            "at": f"2026-07-28T11:03:{index:02d}Z",
        })
    speaking_ready = app.completion_readiness("U01E-S05:SPEAKING")
    if speaking_ready.get("completion_allowed") is not True:
        raise S05ReleaseError("speaking_practice_completion_not_allowed")
    app.complete_session({
        "session_id": "U01E-S05:SPEAKING",
        "expected_session_version": speaking_ready["session_version"],
        "at": "2026-07-28T11:03:50Z",
    })
    coverage_after = app.coverage_readback()
    if coverage_before["learner_evidence_summary"]["distinct_attempted_item_count"] != 0:
        raise S05ReleaseError("canary_coverage_before_not_zero")
    if coverage_after["learner_evidence_summary"]["distinct_attempted_item_count"] != 18:
        raise S05ReleaseError("canary_coverage_after_scored_count_invalid")
    http = authenticated_http_acceptance(app=app, static_root=static_root, auth_state=auth)
    visual = static_adapter.chromium_visual_acceptance(static_root, screenshot_path)
    rollback = v1_1_rollback_acceptance(product_root=product_root, migrated_database=database)
    return {
        "installed_version": TARGET_VERSION,
        "unit_count": EXPECTED_UNIT_COUNT,
        "lesson_count": EXPECTED_LESSON_COUNT,
        "asset_count": EXPECTED_TARGET_ASSET_COUNT,
        "unit01_activity_count": s04.EXPECTED_TOTAL_COUNT,
        "unit01_counts": EXPECTED_UNIT01_COUNTS,
        "context_count": 5,
        "question_type_count": s04.EXPECTED_ASSESSMENT_PATTERN_COUNT,
        "reading": reading,
        "writing": writing,
        "speaking_practice_card_count": EXPECTED_UNIT01_COUNTS["SPEAKING"],
        "coverage_before_practised_item_count": 0,
        "coverage_after_practised_item_count": 18,
        "coverage_distinct_attempt_semantics_pass": True,
        "http": http,
        "static_surface": dict(static_result),
        "visual": visual,
        "rollback": rollback,
        "speaking_capture_enabled": False,
        "listening_enabled": False,
        "audio_enabled": False,
        "a2_unlocked": False,
    }


def write_installer(package_root: Path, candidate: Path) -> Path:
    relative = candidate.relative_to(package_root).as_posix().replace("/", "\\")
    script = f'''param([string]$ProductRoot = (Join-Path $env:USERPROFILE "A1FS_V1"))
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$PackageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Candidate = Join-Path $PackageRoot "{relative}"
$Current = (Get-Content -LiteralPath (Join-Path $ProductRoot "current_version.txt") -Raw).Trim()
if ($Current -ne "{SOURCE_VERSION}") {{ throw "SOURCE_VERSION_REQUIRED={SOURCE_VERSION};ACTUAL=$Current" }}
$PidFile = Join-Path $ProductRoot "shared\\a1fs_v1.pid"
if (Test-Path -LiteralPath $PidFile) {{
  $PidValue = [int](Get-Content -LiteralPath $PidFile -Raw)
  if (Get-Process -Id $PidValue -ErrorAction SilentlyContinue) {{ throw "STOP_A1FS_BEFORE_UPDATE_PID=$PidValue" }}
  Remove-Item -LiteralPath $PidFile -Force
}}
$CurrentApp = Join-Path $ProductRoot "releases\\$Current\\app"
$env:PYTHONPATH = $CurrentApp
& python -m {MODULE} install --product-root $ProductRoot --candidate $Candidate
if ($LASTEXITCODE -ne 0) {{ throw "A1FS_V1_2_UPDATE_FAILED" }}
$Installed = (Get-Content -LiteralPath (Join-Path $ProductRoot "current_version.txt") -Raw).Trim()
if ($Installed -ne "{TARGET_VERSION}") {{ throw "A1FS_V1_2_VERSION_SWITCH_FAILED=$Installed" }}
Write-Host "A1FS_V1_2_U01E_INSTALL=PASS"
Write-Host "PRODUCT_ROOT=$ProductRoot"
Write-Host "CURRENT_VERSION=$Installed"
'''
    path = Path(package_root) / "INSTALL_A1FS_V1_2_U01E.ps1"
    path.write_text(script.replace("\n", "\r\n"), encoding="ascii")
    return path


def materialize(
    *, product_root: Path, code_root: Path, output_path: Path, report_path: Path,
    acceptance_runner: Any = run_acceptance,
) -> tuple[dict[str, Any], dict[str, Any]]:
    product_root = Path(product_root).resolve()
    output_path = Path(output_path).resolve(); report_path = Path(report_path).resolve()
    package_root = output_path.parent / "a1fs_v1_2_u01e_s05_release"
    if package_root.exists():
        shutil.rmtree(package_root)
    package_root.mkdir(parents=True)
    source = source_product(product_root)
    production_before = {
        "current_version": r01._current_version(product_root),
        "shared_identity": m02_core.shared_identity(product_root),
        "legacy_rows": source["legacy_rows"],
    }
    overlay = build_runtime_overlay(source)
    candidate, static_result = build_candidate_release(
        source=source, overlay=overlay, package_root=package_root, code_root=code_root,
    )
    acceptance_root = m02_core.build_acceptance_root(
        product_root=product_root, target_root=package_root / "acceptance_product_root"
    )
    install = install_with_migration(
        product_root=acceptance_root, candidate=candidate, overlay=overlay
    )
    acceptance = acceptance_runner(
        product_root=acceptance_root, source=source, overlay=overlay,
        static_result=static_result, screenshot_path=package_root / "visual/unit01_v1_2.png",
    )
    if r01._current_version(product_root) != SOURCE_VERSION:
        raise S05ReleaseError("production_version_mutated")
    if m02_core.shared_identity(product_root) != production_before["shared_identity"]:
        raise S05ReleaseError("production_shared_state_mutated")
    if source_product(product_root)["legacy_rows"] != production_before["legacy_rows"]:
        raise S05ReleaseError("production_legacy_rows_mutated")
    failure_root = m02_core.build_acceptance_root(
        product_root=product_root, target_root=package_root / "failed_update_product_root"
    )
    failed_rollback = False
    try:
        install_with_migration(
            product_root=failure_root, candidate=candidate, overlay=overlay, inject_failure=True
        )
    except S05ReleaseError as exc:
        if "injected_migration_failure" not in str(exc):
            raise
        failed_rollback = (
            r01._current_version(failure_root) == SOURCE_VERSION
            and m02_core.shared_identity(failure_root) == m02_core.shared_identity(product_root)
        )
    if not failed_rollback:
        raise S05ReleaseError("failed_update_rollback_acceptance_failed")
    installer = write_installer(package_root, candidate)
    receipt_core = {
        "task_id": TASK_ID,
        "program_id": PROGRAM_ID,
        "schema_version": SCHEMA_VERSION,
        "validation_status": PASS_STATUS,
        "product_status": PRODUCT_STATUS,
        "release_id": RELEASE_ID,
        "source_product_version": SOURCE_VERSION,
        "target_product_version": TARGET_VERSION,
        "source_identity": {
            "source_release_sha256": r01.directory_digest(source["release_root"]),
            "source_shared_identity": production_before["shared_identity"],
            "s03_approved_sha256": overlay["approved"]["artifact_sha256"],
            "s02_safe_pack_sha256": overlay["safe_pack"]["pack_sha256"],
        },
        "runtime_outputs": {
            "package_root": str(package_root),
            "candidate_root": str(candidate),
            "acceptance_product_root": str(acceptance_root),
            "installer_path": str(installer),
            "visual_screenshot_path": str(package_root / "visual/unit01_v1_2.png"),
        },
        "release_summary": {
            "unit_count": EXPECTED_UNIT_COUNT,
            "lesson_count": EXPECTED_LESSON_COUNT,
            "source_asset_count": EXPECTED_SOURCE_ASSET_COUNT,
            "target_asset_count": EXPECTED_TARGET_ASSET_COUNT,
            "new_asset_count": s04.EXPECTED_NEW_COUNT,
            "unit01_activity_count": s04.EXPECTED_TOTAL_COUNT,
            "unit01_counts": EXPECTED_UNIT01_COUNTS,
            "context_count": 5,
            "question_type_count": s04.EXPECTED_ASSESSMENT_PATTERN_COUNT,
            "changed_lesson_ids": overlay["changed_lesson_ids"],
            "preserved_lesson_count": 69,
        },
        "migration_summary": install["migration"],
        "acceptance_summary": acceptance,
        "recovery_summary": {
            "failed_update_automatic_rollback_pass": failed_rollback,
            "explicit_v1_1_rollback_pass": acceptance["rollback"]["v1_1_version_loaded"],
            "v1_1_post_migration_database_compatibility_pass": acceptance["rollback"]["post_migration_database_readable"],
            "forward_switch_back_to_v1_2_pass": acceptance["rollback"]["forward_switch_back_to_v1_2_pass"],
        },
        "production_safety": {
            "production_current_version_unchanged": True,
            "production_shared_state_unchanged": True,
            "production_legacy_rows_unchanged": True,
            "source_database_mutated": False,
            "existing_11_asset_identities_changed": False,
            "other_69_lessons_changed": False,
        },
        "boundaries": {
            "runtime_free_generation_allowed": False,
            "unit02_modified": False,
            "listening_enabled": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "external_binding_enabled": False,
            "mastery_inferred_from_single_attempt": False,
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
        "release_id": RELEASE_ID,
        "source_product_version": SOURCE_VERSION,
        "target_product_version": TARGET_VERSION,
        "release_summary": receipt_core["release_summary"],
        "acceptance_summary": acceptance,
        "recovery_summary": receipt_core["recovery_summary"],
        "production_safety": receipt_core["production_safety"],
        "boundaries": receipt_core["boundaries"],
        "stop_reason": "NONE",
        "next_short_step": NEXT_SHORT_STEP,
    }
    safe = {**safe_core, "report_sha256": digest(safe_core)}
    write_json(output_path, receipt, private=True)
    write_json(report_path, safe)
    return receipt, safe


def _load_v12(product_root: Path):
    root = Path(product_root).resolve()
    version, manifest, bundles, sequence = r01._load_product(root)
    if version != TARGET_VERSION:
        raise S05ReleaseError(f"v12_runtime_version_invalid:{version}")
    database = r01._resolve(root, str(manifest["shared_database_path"]))
    auth = r01._resolve(root, str(manifest["shared_auth_state_path"]))
    state = r01._resolve(root, str(manifest["shared_learner_state_root"]))
    graph = r01._resolve(root, str(manifest["graph_path"]))
    static = r01._resolve(root, str(manifest["secure_static_root"]))
    registry = load_registry(root, manifest)
    return root, manifest, bundles, sequence, database, auth, state, graph, static, registry


def serve(*, product_root: Path, host: str, port: int) -> None:
    if not s17.s16.s15.s11._is_loopback(host):
        raise S05ReleaseError(f"non_loopback_host_forbidden:{host}")
    _, _, bundles, sequence, database, auth, state, graph, static, registry = _load_v12(product_root)
    config = s17.s16.s15.s13.PersistentBoundaryConfig.from_environment(
        host=host, port=port, revocation_db_path=auth
    )
    server = V12Server(
        (host, port),
        make_app(database=database, bundles=bundles, sequence=sequence, graph_path=graph, state_root=state, registry=registry),
        static,
        config,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()


def _health(port: int, timeout: float = 2.0) -> bool:
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/health", timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
        return value.get("status") == "PASS" and value.get("authentication_required") is True
    except Exception:
        return False


def start(*, product_root: Path, port: int) -> dict[str, Any]:
    root = Path(product_root).resolve()
    missing = [name for name in r01.REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        raise S05ReleaseError(f"MISSING_ENV={missing[0]}")
    _load_v12(root)
    pid_path = root / "shared/a1fs_v1.pid"
    if pid_path.exists():
        pid = int(pid_path.read_text(encoding="ascii").strip())
        if r01._pid_alive(pid) and _health(port):
            return {"status": "ALREADY_RUNNING", "pid": pid, "version": TARGET_VERSION}
        pid_path.unlink(missing_ok=True)
    with socket.socket() as probe:
        if probe.connect_ex(("127.0.0.1", port)) == 0:
            raise S05ReleaseError(f"PORT_IN_USE={port}")
    logs = root / "shared/logs"
    logs.mkdir(parents=True, exist_ok=True)
    app_root = root / f"releases/{TARGET_VERSION}/app"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(app_root) + os.pathsep + env.get("PYTHONPATH", "")
    flags = 0
    if os.name == "nt":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    with (logs / "a1fs_v1.stdout.log").open("ab") as stdout, (logs / "a1fs_v1.stderr.log").open("ab") as stderr:
        process = subprocess.Popen(
            [sys.executable, "-m", MODULE, "serve", "--product-root", str(root), "--host", "127.0.0.1", "--port", str(port)],
            cwd=app_root,
            env=env,
            stdout=stdout,
            stderr=stderr,
            stdin=subprocess.DEVNULL,
            creationflags=flags,
            close_fds=(os.name != "nt"),
        )
    r01._atomic_text(pid_path, str(process.pid) + "\n")
    for _ in range(40):
        if process.poll() is not None:
            pid_path.unlink(missing_ok=True)
            raise S05ReleaseError(f"PROCESS_EXITED={process.returncode}")
        if _health(port, 1.0):
            return {
                "status": "PASS_A1FS_V1_2_STARTED",
                "pid": process.pid,
                "version": TARGET_VERSION,
                "url": f"http://127.0.0.1:{port}",
            }
        time.sleep(.5)
    process.terminate()
    pid_path.unlink(missing_ok=True)
    raise S05ReleaseError("READINESS_TIMEOUT")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("materialize")
    build.add_argument("--product-root", type=Path, required=True)
    build.add_argument("--code-root", type=Path, default=Path(__file__).resolve().parents[2])
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--report", type=Path, required=True)
    install = commands.add_parser("install")
    install.add_argument("--product-root", type=Path, required=True)
    install.add_argument("--candidate", type=Path, required=True)
    serve_cmd = commands.add_parser("serve")
    serve_cmd.add_argument("--product-root", type=Path, required=True)
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=r01.DEFAULT_PORT)
    start_cmd = commands.add_parser("start")
    start_cmd.add_argument("--product-root", type=Path, required=True)
    start_cmd.add_argument("--port", type=int, default=r01.DEFAULT_PORT)
    args = parser.parse_args(argv)
    try:
        if args.command == "materialize":
            receipt, safe = materialize(
                product_root=args.product_root,
                code_root=args.code_root,
                output_path=args.output,
                report_path=args.report,
            )
            from ulga.validators import validate_a1fs_online_v1_2_u01e_s05_release_migration_acceptance as validator
            validation = validator.validate_outputs(receipt, safe)
            if validation["error_count"]:
                raise S05ReleaseError("validation_failed:" + "|".join(validation["errors"]))
            print(json.dumps(safe, ensure_ascii=False, indent=2))
        elif args.command == "install":
            source = source_product(args.product_root)
            overlay = build_runtime_overlay(source)
            print(json.dumps(install_with_migration(product_root=args.product_root, candidate=args.candidate, overlay=overlay), indent=2))
        elif args.command == "serve":
            serve(product_root=args.product_root, host=args.host, port=args.port)
        else:
            print(json.dumps(start(product_root=args.product_root, port=args.port), indent=2))
        return 0
    except (
        S05ReleaseError,
        static_adapter.S05StaticError,
        s03.S03ItemBankError,
        s04.S04CoverageError,
        r01.ProductRootError,
        sqlite3.Error,
        OSError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL:{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
