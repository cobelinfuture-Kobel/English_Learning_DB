#!/usr/bin/env python3
"""Recovery-safe facade for the U01QB15-aware A1FS V1.2.1 runtime.

The original production cutover correctly materializes the accepted 474-item
QuestionBank, but its direct U01QB13 blueprint build omitted the existing
U01QB14R1 deferred-scene semantic adapter.  A failed first cutover can therefore
leave the count-preserving U01QB15 migration committed while the final product
cutover metadata remains absent.

This facade preserves the same product/runtime authority.  Fresh cutovers run
through the existing U01QB14R1 deferred-scene adapter.  Exact partial states
(288 base + 186 Real62 extension = 474, U01QB15-R1 metadata PASS) skip the
non-idempotent migration and resume only the missing U01QB13 blueprint install
and final product cutover metadata write.  Learner-owned state and all existing
lesson/response-contract rows are still fail-closed invariants.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path
from typing import Any, Mapping, Sequence

from product.a1fs_v1_2_1 import u01qb15_runtime_server as impl
from ulga.builders import (
    build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix
    as r1,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Recovery facade over the existing U01QB15 product consumer: reuses the approved U01QB14R1 deferred-scene projection and resumes an exact already-migrated 474-item partial cutover without regenerating learner content, rerunning non-idempotent QuestionBank migration, creating a second runtime/database/scoring authority, modifying Unit02-24, enabling audio, or unlocking A2."

PROGRAM_ID = impl.PROGRAM_ID
TASK_ID = impl.TASK_ID
REPAIR_TASK_ID = "A1FS-V1-U01QB15_ProductionConsumerDeferredSceneAndPartialMigrationRecoveryFullFix"
PASS_STATUS = impl.PASS_STATUS
MODULE = "product.a1fs_v1_2_1.u01qb15_runtime_server_recovery"
NEXT_SHORT_STEP = impl.NEXT_SHORT_STEP
EXPECTED_BASE_ITEMS = 288
EXPECTED_EXTENSION_ITEMS = impl.EXPECTED_EXTENSION_ITEMS
EXPECTED_RUNTIME_ITEMS = impl.EXPECTED_RUNTIME_ITEMS
EXPECTED_FORMS = impl.EXPECTED_FORMS
EXPECTED_BLUEPRINT_ACTIVITIES = impl.EXPECTED_BLUEPRINT_ACTIVITIES

_ORIGINAL_CUTOVER_DATABASE = impl.cutover_database


class ProductCutoverRecoveryError(impl.ProductCutoverError):
    """Fail-closed recovery error for an incomplete U01QB15 product cutover."""


def _expected_migration_inputs(
    approved_content: Mapping[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    extension_candidate = impl.razq01e.build_candidate(approved_content)
    extension_approved = impl.razq01e.admit_candidate(extension_candidate)

    # U01QB15's accepted construction policy is deterministic.  Rebuild only
    # the policy artifact/coverage proof in memory; never rerun database migration.
    impl.private_runner.optimizer.install()
    u15_candidate = impl.private_runner.u15.build_candidate()
    u15_approved = impl.private_runner.u15.admit_candidate(u15_candidate)
    payload = u15_approved.get("payload")
    if not isinstance(payload, Mapping):
        raise ProductCutoverRecoveryError("U01QB15_APPROVED_PAYLOAD_MISSING")
    capacity = payload.get("per_scene_runtime_capacity")
    if not isinstance(capacity, Mapping):
        raise ProductCutoverRecoveryError("U01QB15_CAPACITY_PROOF_MISSING")
    if (
        capacity.get("runtime_bindable_scene_count") != r1.EXPECTED_UNIT01_BINDABLE_SCENE_COUNT
        or tuple(capacity.get("deferred_scene_refs") or ()) != r1.EXPECTED_DEFERRED_SCENE_REFS
        or capacity.get("verified_activity_count") != EXPECTED_BLUEPRINT_ACTIVITIES
        or capacity.get("all_36_skill_sessions_distinct_item_capacity_proven") is not True
    ):
        raise ProductCutoverRecoveryError("U01QB15_CAPACITY_PROOF_IDENTITY_INVALID")
    return (
        str(u15_approved["artifact_sha256"]),
        str(extension_approved["artifact_sha256"]),
        dict(capacity),
    )


def _partial_migration_state(
    database: Path,
    *,
    expected_base_artifact_sha256: str,
    expected_extension_artifact_sha256: str,
    capacity: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return migration-like readback only for an exact already-migrated state."""
    with closing(sqlite3.connect(database)) as connection:
        if not impl._table_exists(connection, "u01qb15_metadata"):
            return None
        required = {
            "u01qb02_item_catalog",
            "razq01e_extension_items",
            "u01qb02_metadata",
            "razq01e_metadata",
        }
        missing = sorted(table for table in required if not impl._table_exists(connection, table))
        if missing:
            raise ProductCutoverRecoveryError(
                "PARTIAL_U01QB15_REQUIRED_TABLE_MISSING:" + missing[0]
            )
        metadata = dict(connection.execute("SELECT key,value FROM u01qb15_metadata"))
        if metadata.get("validation_status") != impl.private_runner.u15.PASS_STATUS:
            raise ProductCutoverRecoveryError("PARTIAL_U01QB15_STATUS_INVALID")
        if metadata.get("canonical_revision") != impl.private_runner.u15.CANONICAL_REVISION:
            raise ProductCutoverRecoveryError("PARTIAL_U01QB15_REVISION_INVALID")
        if metadata.get("base_artifact_sha256") != expected_base_artifact_sha256:
            raise ProductCutoverRecoveryError("PARTIAL_U01QB15_BASE_ARTIFACT_IDENTITY_DRIFT")
        if metadata.get("extension_artifact_sha256") != expected_extension_artifact_sha256:
            raise ProductCutoverRecoveryError("PARTIAL_REAL62_EXTENSION_ARTIFACT_IDENTITY_DRIFT")

        runtime_count = int(
            connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0]
        )
        extension_count = int(
            connection.execute("SELECT COUNT(*) FROM razq01e_extension_items").fetchone()[0]
        )
        base_count = runtime_count - extension_count
        if (base_count, extension_count, runtime_count) != (
            EXPECTED_BASE_ITEMS,
            EXPECTED_EXTENSION_ITEMS,
            EXPECTED_RUNTIME_ITEMS,
        ):
            raise ProductCutoverRecoveryError(
                f"PARTIAL_U01QB15_DENOMINATOR_INVALID:{base_count}:{extension_count}:{runtime_count}"
            )

        # If blueprint session bindings already exist while the final product
        # cutover marker is absent, do not rewrite under live learner history.
        if impl._table_exists(connection, "u01qb13_session_bindings"):
            bound_sessions = int(
                connection.execute(
                    "SELECT COUNT(DISTINCT session_id) FROM u01qb13_session_bindings"
                ).fetchone()[0]
            )
            if bound_sessions:
                raise ProductCutoverRecoveryError(
                    f"PARTIAL_U01QB13_BOUND_SESSIONS_REQUIRE_FAIL_CLOSED:{bound_sessions}"
                )

    return {
        "validation_status": impl.private_runner.u15.PASS_STATUS,
        "base_item_count": EXPECTED_BASE_ITEMS,
        "extension_item_count": EXPECTED_EXTENSION_ITEMS,
        "runtime_item_count": EXPECTED_RUNTIME_ITEMS,
        "per_scene_runtime_capacity": dict(capacity),
        "real62_extension_modified": False,
        "recovered_existing_migration": True,
    }


def _fresh_cutover_with_deferred_scene_adapter(
    *, database: Path, real62_path: Path
) -> dict[str, Any]:
    with r1.u01qb13_deferred_scene_adapter():
        return _ORIGINAL_CUTOVER_DATABASE(
            database=database,
            real62_path=real62_path,
        )


def _resume_partial_cutover(
    *,
    database: Path,
    real62_path: Path,
    artifact_sha: str,
    raw_file_sha: str,
    migration: Mapping[str, Any],
) -> dict[str, Any]:
    with closing(sqlite3.connect(database)) as connection:
        learner_before = impl._learner_owned_snapshot(connection)
        lesson_assets_before = impl._existing_keyed_rows(connection, "lesson_assets")
        response_contracts_before = impl._existing_keyed_rows(connection, "response_contracts")

    impl.matching.install()
    with tempfile.TemporaryDirectory(prefix="a1fs_u01qb15_cutover_recovery_") as temporary:
        paths = impl.private_runner._paths(Path(temporary))
        rotation, allocation = impl.private_runner._materialize_r2_and_allocation(
            database, paths, migration
        )
        r1.validate_rotation_runtime_bindability(rotation)
        with r1.u01qb13_deferred_scene_adapter():
            blueprint_candidate = impl.u13.build_candidate(rotation, allocation)
            blueprint_approved = impl.u13.admit_candidate(blueprint_candidate)
            installed = impl.u13.install_blueprint(database, blueprint_approved)

    if installed.get("runtime_item_count") != EXPECTED_RUNTIME_ITEMS:
        raise ProductCutoverRecoveryError("U01QB13_RUNTIME_DENOMINATOR_INVALID")

    with closing(sqlite3.connect(database)) as connection:
        connection.row_factory = sqlite3.Row
        impl._assert_existing_rows_preserved(
            connection, "lesson_assets", lesson_assets_before
        )
        impl._assert_existing_rows_preserved(
            connection, "response_contracts", response_contracts_before
        )
        learner_after = impl._learner_owned_snapshot(connection)
        if learner_after != learner_before:
            raise ProductCutoverRecoveryError(
                "LEARNER_OWNED_STATE_CHANGED_DURING_RECOVERY"
            )
        connection.executescript(impl.CUTOVER_SQL)
        metadata = {
            "task_id": TASK_ID,
            "validation_status": PASS_STATUS,
            "real62_artifact_sha256": artifact_sha,
            "questionbank_revision": "U01QB15-R1",
            "runtime_consumer": impl.u13.TASK_ID,
            "runtime_item_count": str(EXPECTED_RUNTIME_ITEMS),
            "extension_item_count": str(EXPECTED_EXTENSION_ITEMS),
            "form_count": str(EXPECTED_FORMS),
            "blueprint_activity_count": str(EXPECTED_BLUEPRINT_ACTIVITIES),
            "static_product_asset_denominator_unchanged": "true",
            "learner_owned_state_unchanged": "true",
            "unit02_to_unit24_modified": "false",
            "a2_unlocked": "false",
            "partial_migration_recovered": "true",
            "deferred_scene_projection_task_id": r1.TASK_ID,
            "next_short_step": NEXT_SHORT_STEP,
        }
        connection.executemany(
            f"INSERT OR REPLACE INTO {impl.CUTOVER_TABLE}(key,value) VALUES(?,?)",
            metadata.items(),
        )
        connection.commit()

    status = impl.require_cutover(database)
    return {
        "status": PASS_STATUS,
        "repair_task_id": REPAIR_TASK_ID,
        "idempotent_reuse": False,
        "partial_migration_recovered": True,
        "real62_artifact_sha256": artifact_sha,
        "real62_file_sha256": raw_file_sha,
        "cutover": status,
        "learner_owned_state_unchanged": True,
        "preexisting_product_rows_unchanged": True,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
        "next_short_step": NEXT_SHORT_STEP,
    }


def cutover_database(*, database: Path, real62_path: Path) -> dict[str, Any]:
    database = Path(database).resolve()
    real62_path = Path(real62_path).resolve(strict=True)
    impl._product_database_preflight(database)
    approved_content, artifact_sha, raw_file_sha = impl.private_runner._real62_identity(
        real62_path
    )
    if artifact_sha != impl.EXPECTED_REAL62_ARTIFACT_SHA256:
        raise ProductCutoverRecoveryError(
            f"REAL62_ARTIFACT_SHA256_INVALID:{artifact_sha}:{impl.EXPECTED_REAL62_ARTIFACT_SHA256}"
        )

    active = impl.cutover_status(database)
    if active.get("active") is True:
        if active.get("real62_artifact_sha256") != artifact_sha:
            raise ProductCutoverRecoveryError("ACTIVE_CUTOVER_REAL62_IDENTITY_DRIFT")
        return {
            "status": PASS_STATUS,
            "repair_task_id": REPAIR_TASK_ID,
            "idempotent_reuse": True,
            "partial_migration_recovered": False,
            "real62_artifact_sha256": artifact_sha,
            "real62_file_sha256": raw_file_sha,
            "cutover": active,
            "learner_owned_state_unchanged": True,
            "preexisting_product_rows_unchanged": True,
            "next_short_step": NEXT_SHORT_STEP,
        }

    base_sha, extension_sha, capacity = _expected_migration_inputs(approved_content)
    partial = _partial_migration_state(
        database,
        expected_base_artifact_sha256=base_sha,
        expected_extension_artifact_sha256=extension_sha,
        capacity=capacity,
    )
    if partial is None:
        return _fresh_cutover_with_deferred_scene_adapter(
            database=database, real62_path=real62_path
        )
    return _resume_partial_cutover(
        database=database,
        real62_path=real62_path,
        artifact_sha=artifact_sha,
        raw_file_sha=raw_file_sha,
        migration=partial,
    )


# Preserve one runtime authority: patch the already-merged product implementation
# rather than constructing another application/server/scoring stack.
impl.cutover_database = cutover_database
impl.MODULE = MODULE
impl.base.MODULE = MODULE


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return impl.main(argv)
    except ProductCutoverRecoveryError as exc:
        print(f"FAIL:{exc}", file=impl.os.sys.stderr)
        return 1


def __getattr__(name: str) -> Any:
    return getattr(impl, name)


if __name__ == "__main__":
    raise SystemExit(main())
