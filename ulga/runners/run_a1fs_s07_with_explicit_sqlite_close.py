#!/usr/bin/env python3
"""Run S07 with deterministic SQLite close and downstream-superset reentry.

S07 originally assumed the persistent database contained no lesson, asset, or
response-contract rows beyond its own three-unit runtime. After S09 legitimately
expands the same database to all 24 canonical units, an authority fingerprint
change may re-run S07. This entrypoint preserves the S07 CLI while treating the
S07 9-lesson/33-asset runtime as an immutable baseline inside the authoritative
S09 72-lesson/264-asset superset. Extra rows are accepted only when the database
contains the exact S09 authority markers, and every downstream row must remain
byte-for-byte unchanged through the S07 migration.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import Any, Iterator, Mapping, Sequence

from ulga.builders import build_a1fs_online_v1_s07_multiunit_runtime_expansion as s07
from ulga.validators import validate_a1fs_online_v1_s07_multiunit_runtime_expansion as s07_validator

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Provides cross-platform SQLite lifecycle control and reentrant preservation of the existing S07 baseline inside the authoritative S09 persistent runtime superset; it creates no curriculum, learner content, answer key, mastery, audio, public delivery, or parallel runtime."

TARGET_MODULE = "ulga.builders.build_a1fs_online_v1_s07_multiunit_runtime_expansion"
S09_TASK_ID = "A1FS-ONLINE-V1-S09_TwentyFourUnitProductionPopulation_NoAudio"
S09_SCHEMA_VERSION = "a1fs.online.v1.s09.twentyfour_unit_production_population.v1"
S09_PASS_STATUS = "PASS_A1FS_ONLINE_V1_S09_TWENTYFOUR_UNIT_PRODUCTION_POPULATED"
S09_UNIT_COUNT = 24
S09_LESSON_COUNT = 72
S09_ASSET_COUNT = 264
S09_CAPTURE_ENABLED_COUNT = 192


class ClosingConnection(sqlite3.Connection):
    """SQLite connection whose context manager also releases the OS handle."""

    context_exit_closed: bool

    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        super().__init__(*args, **kwargs)
        self.context_exit_closed = False

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        try:
            return bool(super().__exit__(exc_type, exc_value, traceback))
        finally:
            self.close()
            self.context_exit_closed = True


_ORIGINAL_CONNECT = sqlite3.connect
_ORIGINAL_VALIDATE_EXISTING_SUBSET = s07._validate_existing_subset
_ORIGINAL_MIGRATE_CLONE = s07._migrate_clone
_ORIGINAL_VALIDATE_OUTPUTS = s07_validator.validate_outputs
_ORIGINAL_VALIDATOR_DATABASE_COUNTS = s07_validator._database_counts


def _closing_connect(*args, **kwargs):  # type: ignore[no-untyped-def]
    requested_factory = kwargs.get("factory")
    if requested_factory not in (None, sqlite3.Connection, ClosingConnection):
        return _ORIGINAL_CONNECT(*args, **kwargs)
    kwargs["factory"] = ClosingConnection
    return _ORIGINAL_CONNECT(*args, **kwargs)


@contextmanager
def explicit_sqlite_context_close() -> Iterator[None]:
    """Temporarily make every context-managed SQLite connection close itself."""

    previous_connect = sqlite3.connect
    sqlite3.connect = _closing_connect  # type: ignore[assignment]
    try:
        yield
    finally:
        sqlite3.connect = previous_connect  # type: ignore[assignment]


def _consumer_maps(
    consumer: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, Mapping[str, Any]]]:
    lessons = {
        str(row["lesson_id"]): row
        for row in consumer.get("lesson_catalog", [])
        if isinstance(row, Mapping) and str(row.get("lesson_id") or "")
    }
    assets = {
        str(row["asset_key"]): row
        for row in consumer.get("asset_records", [])
        if isinstance(row, Mapping) and str(row.get("asset_key") or "")
    }
    if (
        not lessons
        or not assets
        or len(lessons) != len(consumer.get("lesson_catalog", []))
        or len(assets) != len(consumer.get("asset_records", []))
    ):
        raise s07.MultiUnitExpansionError("s07_reentrant_consumer_identity_invalid")
    if any(str(asset.get("lesson_id") or "") not in lessons for asset in assets.values()):
        raise s07.MultiUnitExpansionError("s07_reentrant_asset_lesson_binding_invalid")
    return lessons, assets


def _response_targets(
    assets: Mapping[str, Mapping[str, Any]],
) -> dict[str, tuple[Any, ...]]:
    targets: dict[str, tuple[Any, ...]] = {}
    for asset_key, asset in assets.items():
        contract = s07.m6.derive_contract(asset)
        targets[asset_key] = (
            contract["lesson_id"],
            contract["skill"],
            contract["role"],
            s07.m6.canonical(contract),
            s07.m6.sha(contract),
            int(contract["capture_enabled"]),
        )
    return targets


def _baseline_counts(consumer: Mapping[str, Any]) -> dict[str, int]:
    lessons, assets = _consumer_maps(consumer)
    contracts = _response_targets(assets)
    capture_enabled = sum(int(target[-1]) for target in contracts.values())
    speaking_capture = sum(
        int(target[-1])
        for target in contracts.values()
        if str(target[1]).upper() == "SPEAKING"
    )
    listening_lessons = sum(
        1 for lesson in lessons.values() if str(lesson.get("skill") or "").upper() == "LISTENING"
    )
    if speaking_capture or listening_lessons:
        raise s07.MultiUnitExpansionError("s07_reentrant_audio_or_capture_boundary_invalid")
    return {
        "lesson_count": len(lessons),
        "asset_count": len(assets),
        "response_contract_count": len(contracts),
        "capture_enabled_contract_count": capture_enabled,
        "speaking_capture_enabled_count": 0,
        "listening_lesson_count": 0,
    }


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone() is not None


def _s09_superset_authorized(metadata: Mapping[str, str]) -> bool:
    return (
        metadata.get("s09_task_id") == S09_TASK_ID
        and metadata.get("s09_schema_version") == S09_SCHEMA_VERSION
        and metadata.get("s09_validation_status") == S09_PASS_STATUS
        and metadata.get("s09_populated_unit_count") == str(S09_UNIT_COUNT)
        and metadata.get("s09_nonaudio_item_count") == str(S09_ASSET_COUNT)
    )


def _actual_database_counts(database_path: Path) -> dict[str, int]:
    return s07._database_counts(Path(database_path))


def _validate_s09_totals(database_path: Path, metadata: Mapping[str, str]) -> None:
    if not _s09_superset_authorized(metadata):
        return
    counts = _actual_database_counts(database_path)
    expected = {
        "lesson_count": S09_LESSON_COUNT,
        "asset_count": S09_ASSET_COUNT,
        "response_contract_count": S09_ASSET_COUNT,
        "capture_enabled_contract_count": S09_CAPTURE_ENABLED_COUNT,
        "speaking_capture_enabled_count": 0,
        "listening_lesson_count": 0,
    }
    for key, value in expected.items():
        if counts.get(key) != value:
            raise s07.MultiUnitExpansionError(
                f"s09_authorized_superset_count_invalid:{key}:{counts.get(key)}:{value}"
            )


def _validate_runtime_baseline(
    database_path: Path,
    consumer: Mapping[str, Any],
    *,
    require_complete: bool,
) -> dict[str, Any]:
    lessons, assets = _consumer_maps(consumer)
    response_targets = _response_targets(assets)
    database_path = Path(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        authorized_superset = _s09_superset_authorized(metadata)

        lesson_rows = {
            str(row["lesson_id"]): row
            for row in connection.execute(
                """SELECT lesson_id,lesson_node_id,skill,level,roles_json,
                          requirement_node_ids_json,payload_access_allowed
                   FROM lesson_catalog"""
            )
        }
        asset_rows = {
            str(row["asset_key"]): row
            for row in connection.execute(
                "SELECT asset_key,asset_id,lesson_id,role,content_digest FROM lesson_assets"
            )
        }
        response_rows: dict[str, sqlite3.Row] = {}
        if _table_exists(connection, "response_contracts"):
            response_rows = {
                str(row["asset_key"]): row
                for row in connection.execute(
                    """SELECT asset_key,lesson_id,skill,role,contract_json,
                              contract_digest,capture_enabled
                       FROM response_contracts"""
                )
            }

        extra_lessons = sorted(set(lesson_rows).difference(lessons))
        extra_assets = sorted(set(asset_rows).difference(assets))
        extra_contracts = sorted(set(response_rows).difference(assets))
        if (extra_lessons or extra_assets or extra_contracts) and not authorized_superset:
            raise s07.MultiUnitExpansionError(
                "unexpected_existing_runtime_row_without_s09_authority"
            )

        for lesson_id, expected in lessons.items():
            row = lesson_rows.get(lesson_id)
            if row is None:
                if require_complete:
                    raise s07.MultiUnitExpansionError(
                        f"s07_baseline_lesson_missing:{lesson_id}"
                    )
                continue
            actual = (
                row["lesson_node_id"],
                row["skill"],
                row["level"],
                json.loads(row["roles_json"]),
                json.loads(row["requirement_node_ids_json"]),
                int(row["payload_access_allowed"]),
            )
            target = (
                expected["lesson_node_id"],
                expected["skill"],
                expected["level"],
                sorted(expected["roles"]),
                sorted(expected["requirement_node_ids"]),
                1,
            )
            if actual != target:
                raise s07.MultiUnitExpansionError(
                    f"existing_lesson_contract_drift:{lesson_id}"
                )

        for asset_key, expected in assets.items():
            row = asset_rows.get(asset_key)
            if row is None:
                if require_complete:
                    raise s07.MultiUnitExpansionError(
                        f"s07_baseline_asset_missing:{asset_key}"
                    )
                continue
            actual = (
                row["asset_id"],
                row["lesson_id"],
                row["role"],
                row["content_digest"],
            )
            target = (
                expected["asset_id"],
                expected["lesson_id"],
                expected["role"],
                expected["content_digest"],
            )
            if actual != target:
                raise s07.MultiUnitExpansionError(
                    f"existing_asset_contract_drift:{asset_key}"
                )

        for asset_key, target in response_targets.items():
            row = response_rows.get(asset_key)
            if row is None:
                if require_complete:
                    raise s07.MultiUnitExpansionError(
                        f"s07_baseline_response_contract_missing:{asset_key}"
                    )
                continue
            actual = (
                row["lesson_id"],
                row["skill"],
                row["role"],
                row["contract_json"],
                row["contract_digest"],
                int(row["capture_enabled"]),
            )
            if actual != target:
                raise s07.MultiUnitExpansionError(
                    f"existing_response_contract_drift:{asset_key}"
                )

    _validate_s09_totals(database_path, metadata)
    return {
        "authorized_s09_superset": authorized_superset,
        "extra_lesson_count": len(extra_lessons),
        "extra_asset_count": len(extra_assets),
        "extra_response_contract_count": len(extra_contracts),
    }


def _snapshot_downstream_rows(
    database_path: Path,
    consumer: Mapping[str, Any],
) -> dict[str, dict[str, tuple[Any, ...]]]:
    lessons, assets = _consumer_maps(consumer)
    result: dict[str, dict[str, tuple[Any, ...]]] = {}
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        for table, key_column, baseline_keys in (
            ("lesson_catalog", "lesson_id", set(lessons)),
            ("lesson_assets", "asset_key", set(assets)),
            ("response_contracts", "asset_key", set(assets)),
        ):
            if not _table_exists(connection, table):
                result[table] = {}
                continue
            rows: dict[str, tuple[Any, ...]] = {}
            for row in connection.execute(f"SELECT * FROM {table} ORDER BY {key_column}"):
                key = str(row[key_column])
                if key not in baseline_keys:
                    rows[key] = tuple(row)
            result[table] = rows
    return result


def _reentrant_validate_existing_subset(
    database_path: Path,
    consumer: Mapping[str, Any],
) -> None:
    _validate_runtime_baseline(database_path, consumer, require_complete=False)


def _reentrant_migrate_clone(
    *,
    source_database: Path,
    target_database: Path,
    consumer_path: Path,
    consumer: Mapping[str, Any],
    bundle_paths: Mapping[str, str],
) -> dict[str, int]:
    source_database = Path(source_database)
    target_database = Path(target_database)
    shutil.copy2(source_database, target_database)
    before_state = _validate_runtime_baseline(
        target_database,
        consumer,
        require_complete=False,
    )
    downstream_before = _snapshot_downstream_rows(target_database, consumer)
    counts_before = _actual_database_counts(target_database)
    raw_digest = s07.file_digest(consumer_path)

    with sqlite3.connect(target_database) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("BEGIN IMMEDIATE")
        metadata = dict(connection.execute("SELECT key,value FROM metadata"))
        if metadata.get("validation_status") != s07.m3.STATUS:
            raise s07.MultiUnitExpansionError("m3_database_status_invalid")
        if metadata.get("mastery_write_enabled") != "false":
            raise s07.MultiUnitExpansionError("mastery_write_boundary_invalid")
        for lesson in consumer["lesson_catalog"]:
            connection.execute(
                """INSERT OR IGNORE INTO lesson_catalog
                (lesson_id,lesson_node_id,skill,level,roles_json,
                 requirement_node_ids_json,payload_access_allowed)
                VALUES(?,?,?,?,?,?,?)""",
                (
                    lesson["lesson_id"],
                    lesson["lesson_node_id"],
                    lesson["skill"],
                    lesson["level"],
                    s07.canonical(sorted(lesson["roles"])),
                    s07.canonical(sorted(lesson["requirement_node_ids"])),
                    1,
                ),
            )
        for asset in consumer["asset_records"]:
            connection.execute(
                """INSERT OR IGNORE INTO lesson_assets
                (asset_key,asset_id,lesson_id,role,content_digest)
                VALUES(?,?,?,?,?)""",
                (
                    asset["asset_key"],
                    asset["asset_id"],
                    asset["lesson_id"],
                    asset["role"],
                    asset["content_digest"],
                ),
            )
        updates = {
            "consumer_sha256": raw_digest,
            "s07_task_id": s07.TASK_ID,
            "s07_schema_version": s07.SCHEMA_VERSION,
            "s07_validation_status": s07.PASS_STATUS,
            "s07_admitted_unit_count": str(
                consumer["s07_runtime_projection"]["admitted_unit_count"]
            ),
            "s07_consumer_sha256": raw_digest,
            "mastery_write_enabled": "false",
            "a2_session_enabled": "false",
            "learner_release_approved": "false",
        }
        connection.executemany(
            "INSERT OR REPLACE INTO metadata(key,value) VALUES(?,?)",
            updates.items(),
        )
        connection.commit()

    response_store = s07.m6.ResponseEvidenceStore(target_database)
    for lesson in consumer["lesson_catalog"]:
        response_store.initialize(
            consumer_path=consumer_path,
            lesson_bundle_path=Path(bundle_paths[str(lesson["lesson_id"])]),
        )

    _validate_runtime_baseline(target_database, consumer, require_complete=True)
    downstream_after = _snapshot_downstream_rows(target_database, consumer)
    if downstream_after != downstream_before:
        raise s07.MultiUnitExpansionError(
            "downstream_runtime_rows_changed_during_s07_reentry"
        )

    counts_after = _actual_database_counts(target_database)
    for key in (
        "lesson_count",
        "asset_count",
        "response_contract_count",
        "capture_enabled_contract_count",
        "profile_count",
        "session_count",
        "attempt_count",
    ):
        if counts_after[key] < counts_before[key]:
            raise s07.MultiUnitExpansionError(
                f"persistent_runtime_count_decreased:{key}:{counts_before[key]}:{counts_after[key]}"
            )
    if (
        counts_after["speaking_capture_enabled_count"] != 0
        or counts_after["listening_lesson_count"] != 0
    ):
        raise s07.MultiUnitExpansionError(
            "audio_or_speaking_capture_boundary_invalid"
        )

    baseline = _baseline_counts(consumer)
    return {
        **baseline,
        "profile_count": counts_after["profile_count"],
        "session_count": counts_after["session_count"],
        "attempt_count": counts_after["attempt_count"],
        "authorized_s09_superset": int(before_state["authorized_s09_superset"]),
        "preserved_downstream_lesson_count": int(before_state["extra_lesson_count"]),
        "preserved_downstream_asset_count": int(before_state["extra_asset_count"]),
        "preserved_downstream_response_contract_count": int(
            before_state["extra_response_contract_count"]
        ),
    }


def _projected_validator_counts(
    database_path: Path,
    errors: list[str],
    consumer: Mapping[str, Any],
) -> dict[str, int]:
    actual = _ORIGINAL_VALIDATOR_DATABASE_COUNTS(database_path, errors)
    if not actual:
        return actual
    try:
        _validate_runtime_baseline(database_path, consumer, require_complete=True)
        baseline = _baseline_counts(consumer)
    except (s07.MultiUnitExpansionError, sqlite3.Error, OSError, KeyError, TypeError) as exc:
        errors.append(f"s07_reentrant_database_invalid:{exc}")
        return actual
    return {
        **actual,
        **baseline,
    }


def _reentrant_validate_outputs(**kwargs):  # type: ignore[no-untyped-def]
    receipt = kwargs.get("receipt") or {}
    outputs = receipt.get("runtime_outputs", {}) if isinstance(receipt, Mapping) else {}
    consumer_path = Path(str(outputs.get("consumer_path") or ""))
    database_path = Path(str(outputs.get("database_path") or ""))
    custom_errors: list[str] = []
    consumer: dict[str, Any] = {}
    try:
        consumer = s07.read_json(consumer_path, "s07_reentrant_consumer")
        _validate_runtime_baseline(database_path, consumer, require_complete=True)
    except (s07.MultiUnitExpansionError, sqlite3.Error, OSError, KeyError, TypeError) as exc:
        custom_errors.append(f"s07_reentrant_validation_failed:{exc}")

    previous_database_counts = s07_validator._database_counts
    if consumer:
        s07_validator._database_counts = (  # type: ignore[assignment]
            lambda path, errors: _projected_validator_counts(path, errors, consumer)
        )
    try:
        result = _ORIGINAL_VALIDATE_OUTPUTS(**kwargs)
    finally:
        s07_validator._database_counts = previous_database_counts  # type: ignore[assignment]

    errors = list(result.get("errors", []))
    errors.extend(custom_errors)
    result["errors"] = errors
    result["error_count"] = len(errors)
    result["validation_status"] = "PASS" if not errors else "FAIL"
    return result


@contextmanager
def reentrant_s07_runtime_patch() -> Iterator[None]:
    previous_validate_existing = s07._validate_existing_subset
    previous_migrate_clone = s07._migrate_clone
    previous_validate_outputs = s07_validator.validate_outputs
    s07._validate_existing_subset = _reentrant_validate_existing_subset  # type: ignore[assignment]
    s07._migrate_clone = _reentrant_migrate_clone  # type: ignore[assignment]
    s07_validator.validate_outputs = _reentrant_validate_outputs  # type: ignore[assignment]
    try:
        yield
    finally:
        s07._validate_existing_subset = previous_validate_existing  # type: ignore[assignment]
        s07._migrate_clone = previous_migrate_clone  # type: ignore[assignment]
        s07_validator.validate_outputs = previous_validate_outputs  # type: ignore[assignment]


def main(argv: Sequence[str] | None = None) -> int:
    with explicit_sqlite_context_close(), reentrant_s07_runtime_patch():
        return s07.main(list(argv) if argv is not None else None)


if __name__ == "__main__":
    raise SystemExit(main())
