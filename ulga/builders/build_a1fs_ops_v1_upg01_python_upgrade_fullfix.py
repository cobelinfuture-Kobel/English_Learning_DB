#!/usr/bin/env python3
"""Run UPG01 through one Python-only operator entry.

This adapter keeps the accepted portable/resumable orchestrator and Windows
runtime-shutdown FullFix. It also makes two rollback-resume boundaries
idempotent:

1. S01 reads only the original eleven Unit01 contracts when governed
   ``U01E-S03-*`` additive rows remain in shared state.
2. S05 replays an interrupted additive migration by verifying and reusing
   byte/semantic-identical rows, inserting only missing rows, and failing closed
   on any identity conflict.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import build_a1fs_ops_v1_upg01_runtime_shutdown_fullfix as runtime
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01,
)
from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s05_release_migration_acceptance as s05,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = (
    "Provides the canonical Python-only UPG01 operator entry, delegates migration, "
    "journaling, shutdown, acceptance, and rollback to accepted authorities, scopes "
    "S01 legacy-contract reads to the original eleven assets, and makes governed S05 "
    "additive migration replay idempotent by verifying identical rows and inserting "
    "only missing rows. It creates or deletes no content, contract, answer, learner "
    "attempt, score, mastery state, audio, A2 unlock, external route, release "
    "authority, or parallel migration engine."
)
PROGRAM_ID = runtime.core.PROGRAM_ID
TASK_ID = runtime.core.TASK_ID
SCHEMA_VERSION = runtime.core.SCHEMA_VERSION
PASS_STATUS = runtime.core.PASS_STATUS
PLAN_PASS_STATUS = runtime.core.PLAN_PASS_STATUS
DEFAULT_PORT = runtime.DEFAULT_PORT
RESIDUAL_CONTRACT_PREFIX = "U01E-S03-"
MAX_GOVERNED_RESIDUAL_CONTRACT_COUNT = 13

_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "lesson_assets": (
        "asset_key",
        "asset_id",
        "lesson_id",
        "role",
        "content_digest",
    ),
    "response_contracts": (
        "asset_key",
        "lesson_id",
        "skill",
        "role",
        "contract_digest",
        "contract_json",
        "capture_enabled",
    ),
}


class PythonUpgradeFullFixError(runtime.RuntimeShutdownFullFixError):
    """Fail-closed Python-entry or rollback-resume compatibility error."""


def load_legacy_unit01_contracts(
    database_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    """Read only the original eleven Unit01 contracts from shared state.

    A previous V1.2 attempt may have committed up to thirteen governed additive
    ``U01E-S03-*`` contracts before a later acceptance failure caused the release
    pointer to roll back. Those rows are forward-compatible shared state and must
    not be deleted. They are excluded only from S01's legacy eleven-asset intake.
    """

    lesson_ids = list(s01.m01.LESSON_IDS.values())
    placeholders = ",".join("?" for _ in lesson_ids)
    with sqlite3.connect(Path(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT asset_key,lesson_id,skill,role,capture_enabled,contract_json "
            f"FROM response_contracts WHERE lesson_id IN ({placeholders}) "
            "ORDER BY lesson_id,asset_key",
            tuple(lesson_ids),
        ).fetchall()

    legacy_rows = [
        row
        for row in rows
        if not str(row["asset_key"]).startswith(RESIDUAL_CONTRACT_PREFIX)
    ]
    residual_rows = [
        row
        for row in rows
        if str(row["asset_key"]).startswith(RESIDUAL_CONTRACT_PREFIX)
    ]
    if len(legacy_rows) != s01.EXPECTED_EXISTING_ASSET_COUNT:
        raise s01.S01AdmissionError(
            f"unit01_legacy_response_contract_count_invalid:{len(legacy_rows)}"
        )
    if len(residual_rows) > MAX_GOVERNED_RESIDUAL_CONTRACT_COUNT:
        raise s01.S01AdmissionError(
            f"unit01_residual_u01e_contract_count_invalid:{len(residual_rows)}"
        )

    assets: list[dict[str, Any]] = []
    contracts: dict[str, dict[str, Any]] = {}
    for row in legacy_rows:
        asset_key = str(row["asset_key"])
        contract = json.loads(str(row["contract_json"]))
        if not isinstance(contract, dict):
            raise s01.S01AdmissionError(f"response_contract_not_object:{asset_key}")
        contract.update(
            {
                "asset_key": asset_key,
                "lesson_id": str(row["lesson_id"]),
                "role": str(row["role"]),
                "capture_enabled": bool(row["capture_enabled"]),
            }
        )
        contracts[asset_key] = contract
        assets.append(
            {
                "asset_key": asset_key,
                "lesson_id": str(row["lesson_id"]),
                "skill": str(row["skill"]),
                "role": str(row["role"]),
            }
        )
    return assets, contracts


def _normalized_identity(table: str, values: Sequence[Any]) -> tuple[Any, ...]:
    normalized = list(values)
    if table == "response_contracts":
        try:
            normalized[5] = s05._core.canonical(json.loads(str(normalized[5])))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise PythonUpgradeFullFixError(
                "migration_contract_json_invalid"
            ) from exc
        normalized[6] = int(bool(normalized[6]))
    return tuple(normalized)


def _insert_or_reuse_exact(
    connection: sqlite3.Connection,
    table: str,
    key_column: str,
    key: str,
    values: Sequence[Any],
    sql: str,
) -> str:
    columns = _TABLE_COLUMNS.get(table)
    if columns is None:
        raise PythonUpgradeFullFixError(f"migration_table_not_supported:{table}")
    selected = ",".join(columns)
    row = connection.execute(
        f"SELECT {selected} FROM {table} WHERE {key_column}=?",
        (key,),
    ).fetchone()
    if row is None:
        connection.execute(sql, tuple(values))
        return "INSERTED"
    actual = _normalized_identity(table, tuple(row))
    expected = _normalized_identity(table, tuple(values))
    if actual != expected:
        raise PythonUpgradeFullFixError(
            f"migration_identity_conflict:{table}:{key}"
        )
    return "REUSED_IDENTICAL"


def _residual_keys(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            f"SELECT asset_key FROM {table} WHERE asset_key LIKE ?",
            (RESIDUAL_CONTRACT_PREFIX + "%",),
        ).fetchall()
    }


def replay_safe_migrate_database(
    *,
    database_path: Path,
    overlay: Mapping[str, Any],
    m1_graph_path: Path,
    inject_failure: bool = False,
) -> dict[str, Any]:
    """Apply or replay the governed additive S05 migration without duplication."""

    core = s05._core
    database_path = Path(database_path)
    before_schema = core._legacy_schema(database_path)
    before_rows = core._legacy_row_identity(database_path)
    source_sha = core.r01.file_digest(database_path)
    denominators = core.s04.denominator_contract(
        m1_graph_path, overlay["target_registry"]
    )
    expected_asset_keys = {
        str(row["asset_key"]) for row in overlay["assets"]
    }
    expected_contract_keys = {
        str(row["asset_key"]) for row in overlay["contracts"]
    }
    if (
        len(expected_asset_keys) != core.s04.EXPECTED_NEW_COUNT
        or expected_asset_keys != expected_contract_keys
    ):
        raise PythonUpgradeFullFixError(
            "migration_overlay_identity_denominator_invalid"
        )

    inserted_assets = reused_assets = 0
    inserted_contracts = reused_contracts = 0
    with closing(sqlite3.connect(database_path)) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        names = core.s04.table_names(connection)
        missing = {"lesson_assets", "response_contracts"} - names
        if missing:
            raise core.S05ReleaseError(
                f"migration_required_table_missing:{sorted(missing)[0]}"
            )
        existing_asset_keys = _residual_keys(connection, "lesson_assets")
        existing_contract_keys = _residual_keys(connection, "response_contracts")
        unexpected_assets = sorted(existing_asset_keys - expected_asset_keys)
        unexpected_contracts = sorted(existing_contract_keys - expected_contract_keys)
        if unexpected_assets:
            raise PythonUpgradeFullFixError(
                f"migration_unrecognized_residual_identity:lesson_assets:{unexpected_assets[0]}"
            )
        if unexpected_contracts:
            raise PythonUpgradeFullFixError(
                "migration_unrecognized_residual_identity:"
                f"response_contracts:{unexpected_contracts[0]}"
            )

        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.executescript(core.s04.ADDITIVE_SQL)
            for asset in overlay["assets"]:
                status = _insert_or_reuse_exact(
                    connection,
                    "lesson_assets",
                    "asset_key",
                    str(asset["asset_key"]),
                    (
                        asset["asset_key"],
                        asset["asset_id"],
                        asset["lesson_id"],
                        asset["role"],
                        asset["content_digest"],
                    ),
                    "INSERT INTO lesson_assets("
                    "asset_key,asset_id,lesson_id,role,content_digest"
                    ") VALUES(?,?,?,?,?)",
                )
                inserted_assets += int(status == "INSERTED")
                reused_assets += int(status == "REUSED_IDENTICAL")
            for record in overlay["contracts"]:
                status = _insert_or_reuse_exact(
                    connection,
                    "response_contracts",
                    "asset_key",
                    str(record["asset_key"]),
                    (
                        record["asset_key"],
                        record["lesson_id"],
                        record["skill"],
                        record["role"],
                        record["contract_digest"],
                        core.canonical(record["contract"]),
                        record["capture_enabled"],
                    ),
                    "INSERT INTO response_contracts("
                    "asset_key,lesson_id,skill,role,contract_digest,"
                    "contract_json,capture_enabled"
                    ") VALUES(?,?,?,?,?,?,?)",
                )
                inserted_contracts += int(status == "INSERTED")
                reused_contracts += int(status == "REUSED_IDENTICAL")
            for key, value in sorted(denominators.items()):
                connection.execute(
                    "INSERT OR REPLACE INTO u01e_coverage_denominators "
                    "VALUES(?,?,?,?,?)",
                    (
                        key,
                        int(value["count"]),
                        str(value["status"]),
                        core.canonical(value),
                        core.digest(value),
                    ),
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
                    "INSERT OR REPLACE INTO u01e_asset_target_bindings "
                    "VALUES(?,?,?,?,?,?,?)",
                    (
                        row["item_key"],
                        row["unit_id"],
                        row["skill"],
                        row["question_type"],
                        "RUNTIME_ACTIVE",
                        core.canonical(binding),
                        core.digest(binding),
                    ),
                )
            if inject_failure:
                raise core.S05ReleaseError("injected_migration_failure")
            final_asset_keys = _residual_keys(connection, "lesson_assets")
            final_contract_keys = _residual_keys(connection, "response_contracts")
            if final_asset_keys != expected_asset_keys:
                raise PythonUpgradeFullFixError(
                    "migration_final_lesson_asset_identity_set_invalid"
                )
            if final_contract_keys != expected_contract_keys:
                raise PythonUpgradeFullFixError(
                    "migration_final_response_contract_identity_set_invalid"
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    after_schema = core._legacy_schema(database_path)
    after_rows = core._legacy_row_identity(database_path)
    if before_schema != after_schema:
        raise core.S05ReleaseError("legacy_schema_changed")
    for table, identity in before_rows.items():
        if table in {"lesson_assets", "response_contracts"}:
            continue
        if after_rows.get(table) != identity:
            raise core.S05ReleaseError(f"legacy_row_identity_changed:{table}")
    if (
        after_rows["lesson_assets"]["count"]
        != before_rows["lesson_assets"]["count"] + inserted_assets
    ):
        raise PythonUpgradeFullFixError("lesson_asset_row_delta_invalid")
    if (
        after_rows["response_contracts"]["count"]
        != before_rows["response_contracts"]["count"] + inserted_contracts
    ):
        raise PythonUpgradeFullFixError("response_contract_row_delta_invalid")
    if inserted_assets + reused_assets != core.s04.EXPECTED_NEW_COUNT:
        raise PythonUpgradeFullFixError("lesson_asset_replay_denominator_invalid")
    if inserted_contracts + reused_contracts != core.s04.EXPECTED_NEW_COUNT:
        raise PythonUpgradeFullFixError(
            "response_contract_replay_denominator_invalid"
        )

    if reused_assets == reused_contracts == 0:
        replay_mode = "FRESH_INSERT"
    elif (
        reused_assets
        == reused_contracts
        == core.s04.EXPECTED_NEW_COUNT
    ):
        replay_mode = "COMPLETE_IDENTICAL_REUSE"
    else:
        replay_mode = "PARTIAL_IDENTICAL_REUSE"

    return {
        "source_database_sha256_before": source_sha,
        "migrated_database_sha256": core.r01.file_digest(database_path),
        "legacy_schema_unchanged": True,
        "legacy_non_target_rows_unchanged": True,
        "lesson_asset_rows_added": core.s04.EXPECTED_NEW_COUNT,
        "response_contract_rows_added": core.s04.EXPECTED_NEW_COUNT,
        "lesson_asset_rows_inserted_this_run": inserted_assets,
        "lesson_asset_rows_reused_identical": reused_assets,
        "response_contract_rows_inserted_this_run": inserted_contracts,
        "response_contract_rows_reused_identical": reused_contracts,
        "migration_replay_mode": replay_mode,
        "migration_identity_conflict_policy": "FAIL_CLOSED",
        "residual_rows_deleted": False,
        "additive_tables": sorted(core.s04.ADDITIVE_TABLES),
        "target_binding_count": core.s04.EXPECTED_TOTAL_COUNT,
        "v1_1_compatible": True,
    }


def activate() -> None:
    """Activate shutdown, S01 intake, and replay-safe S05 migration adapters."""

    runtime.activate()
    s01.load_contracts = load_legacy_unit01_contracts
    s05._core.migrate_database = replay_safe_migrate_database
    s05.migrate_database = replay_safe_migrate_database


def _entry_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    return {
        **dict(value),
        "operator_entry": "PYTHON_ONLY",
        "powershell_required": False,
        "residual_u01e_contract_compatibility": {
            "enabled": True,
            "legacy_contract_count": s01.EXPECTED_EXISTING_ASSET_COUNT,
            "governed_residual_prefix": RESIDUAL_CONTRACT_PREFIX,
            "residual_rows_deleted": False,
            "legacy_denominator_relaxed": False,
            "migration_replay_safe": True,
            "identity_conflict_policy": "FAIL_CLOSED",
        },
    }


def build_plan(**kwargs: Any) -> dict[str, Any]:
    return _entry_metadata(runtime.build_plan(**kwargs))


def upgrade(**kwargs: Any) -> dict[str, Any]:
    activate()
    return _entry_metadata(runtime.upgrade(**kwargs))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "upgrade"):
        command = commands.add_parser(name)
        command.add_argument("--code-root", type=Path)
        command.add_argument("--product-root", type=Path)
        command.add_argument("--output-root", type=Path)
        command.add_argument("--journal-path", type=Path)
        command.add_argument("--target-version", default="latest")
        command.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)
    kwargs = {
        "code_root": args.code_root,
        "product_root": args.product_root,
        "output_root": args.output_root,
        "journal_path": args.journal_path,
        "target_version": args.target_version,
        "port": args.port,
    }
    try:
        result = build_plan(**kwargs) if args.command == "plan" else upgrade(**kwargs)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (
        PythonUpgradeFullFixError,
        runtime.RuntimeShutdownFullFixError,
        runtime.core.UpgradeOrchestratorError,
        runtime.core.r01.ProductRootError,
        s01.S01AdmissionError,
        s05._core.S05ReleaseError,
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
