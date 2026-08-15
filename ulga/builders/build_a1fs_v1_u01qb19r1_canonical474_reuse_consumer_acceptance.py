#!/usr/bin/env python3
"""Accept U01QB19 against the existing Actual Real62 fresh-474 runtime path.

This is an acceptance consumer, not a QuestionBank producer.  The only 474-item
materialization path used here is U01QB15's already-established Actual Real62
bootstrap (U01QB02 base 288 + RAZQ01E extension 186).  Once that disposable
runtime exists, U01QB19 is exercised read-only and its projected identities are
compared with the live U01QB02 catalog before and after the projection.

The private answer column is protected with a SQLite authorizer while U01QB19
runs.  Any attempted read of private_item_json fails closed.  No Unit02 content,
A2 unlock, selector, planner, scoring, or learner-state authority is created.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from ulga.builders import (
    build_a1fs_v1_u01qb15_actual_real62_fresh474_r2_private_acceptance_runner
    as actual474,
)
from ulga.builders import (
    build_a1fs_v1_u01qb19_unit01_canonical474_cumulative_reuse_reference_projection
    as u19,
)

A1FS_CONTENT_POLICY_MODE = "NOT_CONTENT_PRODUCER"
A1FS_CONTENT_POLICY_EXEMPTION = "Read-only acceptance over the existing U01QB15 Actual Real62 fresh-474 materialization helper and U01QB19 reference projection; creates no second QuestionBank, selector, planner, learner-state/scoring authority, Unit02 content, private-answer consumer, or A2 unlock."
PROGRAM_ID = "A1FS-V1"
TASK_ID = "A1FS-V1-U01QB19R1_Canonical474ReuseConsumerAcceptance"
SCHEMA_VERSION = "a1fs.v1.u01qb19r1.canonical474_reuse_consumer_acceptance.v1"
PASS_STATUS = "PASS_A1FS_V1_U01QB19R1_CANONICAL474_REUSE_CONSUMER_ACCEPTANCE"
EXPECTED_RUNTIME_ITEMS = u19.EXPECTED_RUNTIME_ITEMS
EXPECTED_BASE_ITEMS = u19.EXPECTED_BASE_ITEMS
EXPECTED_EXTENSION_ITEMS = u19.EXPECTED_EXTENSION_ITEMS
ACTUAL_474_BOOTSTRAP_OWNER = actual474.TASK_ID
EXPECTED_REAL62_ARTIFACT_SHA256 = actual474.EXPECTED_REAL62_ARTIFACT_SHA256
DEFAULT_OUTPUT_DIR = Path(".local/a1fs_v1/u01qb19r1/actual474_consumer_acceptance")
NEXT_SHORT_STEP = "A1FS-V1-U02QB00_Unit02QuestionBankScopeAndCurrentStateAdmission"
NEXT_SHORT_STEP_SCOPE = "OUTSIDE_U01QB19_APPROVED_SCOPE"

FORBIDDEN_PROJECTION_KEYS = frozenset(
    {
        "private_item_json",
        "answer",
        "correct_answer",
        "accepted_texts",
        "private_scoring_contract",
        "scoring_contract",
    }
)


class Canonical474ReuseConsumerAcceptanceError(ValueError):
    """Fail-closed U01QB19R1 acceptance error."""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_only(database: Path) -> sqlite3.Connection:
    path = Path(database).resolve()
    if not path.is_file():
        raise Canonical474ReuseConsumerAcceptanceError("RUNTIME_DATABASE_MISSING")
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


def _catalog_identity(database: Path) -> list[dict[str, str]]:
    with _read_only(database) as connection:
        rows = connection.execute(
            """SELECT item_id,asset_key,item_digest
               FROM u01qb02_item_catalog ORDER BY item_id"""
        ).fetchall()
    identity = [
        {
            "item_id": str(row["item_id"]),
            "asset_key": str(row["asset_key"]),
            "item_digest": str(row["item_digest"]),
        }
        for row in rows
    ]
    if len(identity) != EXPECTED_RUNTIME_ITEMS:
        raise Canonical474ReuseConsumerAcceptanceError(
            f"ACTUAL_QB02_CATALOG_DENOMINATOR_INVALID:{len(identity)}"
        )
    if len({row["item_id"] for row in identity}) != EXPECTED_RUNTIME_ITEMS:
        raise Canonical474ReuseConsumerAcceptanceError("ACTUAL_QB02_ITEM_ID_NOT_UNIQUE")
    if len({row["asset_key"] for row in identity}) != EXPECTED_RUNTIME_ITEMS:
        raise Canonical474ReuseConsumerAcceptanceError("ACTUAL_QB02_ASSET_KEY_NOT_UNIQUE")
    if len({row["item_digest"] for row in identity}) != EXPECTED_RUNTIME_ITEMS:
        raise Canonical474ReuseConsumerAcceptanceError("ACTUAL_QB02_ITEM_DIGEST_NOT_UNIQUE")
    return identity


def _identity_mutation_counts(
    before: Sequence[Mapping[str, str]],
    projected: Sequence[Mapping[str, Any]],
    after: Sequence[Mapping[str, str]],
) -> dict[str, int]:
    before_by_id = {str(row["item_id"]): row for row in before}
    after_by_id = {str(row["item_id"]): row for row in after}
    projected_by_id = {str(row["item_id"]): row for row in projected}

    all_ids = set(before_by_id) | set(after_by_id) | set(projected_by_id)
    item_id_mutation_count = len(all_ids - set(before_by_id)) + len(
        set(before_by_id) - set(projected_by_id)
    ) + len(set(before_by_id) - set(after_by_id))
    asset_key_mutation_count = 0
    item_digest_mutation_count = 0
    for item_id in set(before_by_id) & set(after_by_id) & set(projected_by_id):
        expected = before_by_id[item_id]
        if (
            str(projected_by_id[item_id].get("asset_key")) != str(expected["asset_key"])
            or str(after_by_id[item_id]["asset_key"]) != str(expected["asset_key"])
        ):
            asset_key_mutation_count += 1
        if (
            str(projected_by_id[item_id].get("item_digest")) != str(expected["item_digest"])
            or str(after_by_id[item_id]["item_digest"]) != str(expected["item_digest"])
        ):
            item_digest_mutation_count += 1
    return {
        "item_id_mutation_count": item_id_mutation_count,
        "asset_key_mutation_count": asset_key_mutation_count,
        "item_digest_mutation_count": item_digest_mutation_count,
    }


def verify_existing_runtime(database: Path, *, learner_id: str) -> dict[str, Any]:
    """Verify one already-materialized 474 runtime without generating any items."""
    database = Path(database).resolve(strict=True)
    before_database_sha256 = _sha256(database)
    before_identity = _catalog_identity(database)

    private_read_attempt_count = 0
    original_connect = u19._connect_read_only

    def guarded_connect(path: Path) -> sqlite3.Connection:
        connection = original_connect(path)

        def authorizer(
            action_code: int,
            arg1: str | None,
            arg2: str | None,
            _database_name: str | None,
            _trigger_name: str | None,
        ) -> int:
            nonlocal private_read_attempt_count
            if (
                action_code == sqlite3.SQLITE_READ
                and str(arg1) == "u01qb02_item_catalog"
                and str(arg2) == "private_item_json"
            ):
                private_read_attempt_count += 1
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK

        connection.set_authorizer(authorizer)
        return connection

    u19._connect_read_only = guarded_connect
    try:
        projection = u19.build_reuse_projection(database, learner_id=learner_id)
    finally:
        u19._connect_read_only = original_connect

    after_identity = _catalog_identity(database)
    after_database_sha256 = _sha256(database)
    projected_items = list(projection.get("items") or [])
    mutations = _identity_mutation_counts(before_identity, projected_items, after_identity)
    forbidden_projection_field_count = sum(
        1
        for row in projected_items
        for key in row
        if str(key) in FORBIDDEN_PROJECTION_KEYS
    )

    if projection.get("validation_status") != u19.PASS_STATUS:
        raise Canonical474ReuseConsumerAcceptanceError("U01QB19_PROJECTION_NOT_PASS")
    if len(projected_items) != EXPECTED_RUNTIME_ITEMS:
        raise Canonical474ReuseConsumerAcceptanceError(
            f"PROJECTION_DENOMINATOR_INVALID:{len(projected_items)}"
        )
    if any(mutations.values()):
        raise Canonical474ReuseConsumerAcceptanceError(
            f"CANONICAL_IDENTITY_MUTATION_DETECTED:{mutations}"
        )
    if before_database_sha256 != after_database_sha256:
        raise Canonical474ReuseConsumerAcceptanceError("DATABASE_MUTATED_BY_REUSE_PROJECTION")
    if private_read_attempt_count != 0:
        raise Canonical474ReuseConsumerAcceptanceError(
            f"PRIVATE_ANSWER_READ_ATTEMPTED:{private_read_attempt_count}"
        )
    if forbidden_projection_field_count != 0:
        raise Canonical474ReuseConsumerAcceptanceError(
            f"PRIVATE_FIELD_LEAKED_TO_PROJECTION:{forbidden_projection_field_count}"
        )
    if projection.get("semantic_boundaries", {}).get("unit02_content_created") is not False:
        raise Canonical474ReuseConsumerAcceptanceError("UNIT02_CONTENT_BOUNDARY_INVALID")
    if projection.get("semantic_boundaries", {}).get("a2_unlocked") is not False:
        raise Canonical474ReuseConsumerAcceptanceError("A2_BOUNDARY_INVALID")

    expected_identity_sha256 = u19.digest(before_identity)
    if projection.get("canonical_identity_sha256") != expected_identity_sha256:
        raise Canonical474ReuseConsumerAcceptanceError(
            "PROJECTION_CANONICAL_IDENTITY_DIGEST_MISMATCH"
        )

    return {
        "actual_qb02_catalog_count": len(before_identity),
        "projection_reference_count": len(projected_items),
        "canonical_identity_sha256": expected_identity_sha256,
        **mutations,
        "database_mutation_count": 0,
        "database_sha256_before": before_database_sha256,
        "database_sha256_after": after_database_sha256,
        "private_answer_read_count": private_read_attempt_count,
        "private_projection_field_count": forbidden_projection_field_count,
        "unit02_content_created_count": 0,
        "a2_unlock_count": 0,
        "reuse_mode": projection.get("reuse_mode"),
        "semantic_boundaries": dict(projection.get("semantic_boundaries") or {}),
    }


def _actual_runtime_boundaries(database: Path) -> dict[str, Any]:
    unit01_lessons = set(u19.qb02.UNIT01_LESSONS.values())
    with _read_only(database) as connection:
        runtime_lessons = {
            str(row[0])
            for row in connection.execute(
                "SELECT DISTINCT lesson_id FROM u01qb02_item_catalog"
            ).fetchall()
        }
        unit02_catalog_count = int(
            connection.execute(
                """SELECT COUNT(*) FROM u01qb02_item_catalog
                   WHERE lesson_id LIKE '%UNIT02%'"""
            ).fetchone()[0]
        )
        unit02_lesson_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM lesson_catalog WHERE lesson_id LIKE '%UNIT02%'"
            ).fetchone()[0]
        )
        a2_lesson_count = int(
            connection.execute(
                "SELECT COUNT(*) FROM lesson_catalog WHERE level='A2'"
            ).fetchone()[0]
        )
        row = connection.execute(
            "SELECT value FROM metadata WHERE key='a2_session_enabled'"
        ).fetchone()
        a2_session_enabled = str(row[0]).lower() if row is not None else "missing"

    if runtime_lessons != unit01_lessons:
        raise Canonical474ReuseConsumerAcceptanceError(
            f"ACTUAL_RUNTIME_LESSON_SCOPE_INVALID:{sorted(runtime_lessons)}"
        )
    if unit02_catalog_count or unit02_lesson_count:
        raise Canonical474ReuseConsumerAcceptanceError(
            f"UNIT02_CONTENT_PRESENT:{unit02_catalog_count}:{unit02_lesson_count}"
        )
    if a2_lesson_count != 0 or a2_session_enabled != "false":
        raise Canonical474ReuseConsumerAcceptanceError(
            f"A2_NOT_LOCKED:{a2_lesson_count}:{a2_session_enabled}"
        )
    return {
        "runtime_lesson_ids": sorted(runtime_lessons),
        "unit02_catalog_item_count": unit02_catalog_count,
        "unit02_lesson_count": unit02_lesson_count,
        "a2_lesson_count": a2_lesson_count,
        "a2_session_enabled": a2_session_enabled,
    }


def run_acceptance(
    *,
    real62_path: Path,
    output_dir: Path,
    replace: bool,
    learner_id: str,
    expected_real62_artifact_sha256: str | None = EXPECTED_REAL62_ARTIFACT_SHA256,
) -> dict[str, Any]:
    """Materialize via the existing Actual Real62 helper, then accept U01QB19."""
    real62_path = Path(real62_path).resolve(strict=True)
    approved_content, artifact_sha256, file_sha256 = actual474._real62_identity(real62_path)
    if expected_real62_artifact_sha256 and artifact_sha256 != expected_real62_artifact_sha256:
        raise Canonical474ReuseConsumerAcceptanceError(
            "REAL62_ARTIFACT_SHA256_INVALID:"
            f"{artifact_sha256}:{expected_real62_artifact_sha256}"
        )

    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    database = output_dir / "u01qb19r1_actual_real62_fresh474.sqlite3"
    report_path = output_dir / "u01qb19r1_actual474_reuse_consumer_acceptance.json"
    managed = (database, report_path)
    existing = [path for path in managed if path.exists()]
    if existing and not replace:
        raise Canonical474ReuseConsumerAcceptanceError("OUTPUT_EXISTS_USE_REPLACE")
    if replace:
        for path in managed:
            if path.exists():
                path.unlink()
            for suffix in ("-wal", "-shm", "-journal"):
                sidecar = Path(str(path) + suffix)
                if sidecar.exists():
                    sidecar.unlink()

    bootstrap = actual474._bootstrap_fresh_474(database, approved_content)
    if (
        int(bootstrap.get("base_item_count") or -1) != EXPECTED_BASE_ITEMS
        or int(bootstrap.get("extension_item_count") or -1) != EXPECTED_EXTENSION_ITEMS
        or int(bootstrap.get("runtime_item_count") or -1) != EXPECTED_RUNTIME_ITEMS
    ):
        raise Canonical474ReuseConsumerAcceptanceError(
            f"ACTUAL_474_BOOTSTRAP_DENOMINATOR_INVALID:{bootstrap}"
        )

    consumer = verify_existing_runtime(database, learner_id=learner_id)
    boundaries = _actual_runtime_boundaries(database)
    if consumer["unit02_content_created_count"] != 0 or boundaries["unit02_catalog_item_count"] != 0:
        raise Canonical474ReuseConsumerAcceptanceError("UNIT02_CONTENT_CREATED")
    if consumer["a2_unlock_count"] != 0 or boundaries["a2_session_enabled"] != "false":
        raise Canonical474ReuseConsumerAcceptanceError("A2_UNLOCKED")

    report = {
        "schema_version": SCHEMA_VERSION,
        "program_id": PROGRAM_ID,
        "task_id": TASK_ID,
        "validation_status": PASS_STATUS,
        "actual_474_bootstrap_owner": ACTUAL_474_BOOTSTRAP_OWNER,
        "actual_real62_artifact_sha256": artifact_sha256,
        "actual_real62_file_sha256": file_sha256,
        "fresh_runtime": dict(bootstrap),
        "consumer_acceptance": consumer,
        "runtime_boundaries": boundaries,
        "questionbank_created_by_r1": False,
        "selector_created_by_r1": False,
        "planner_created_by_r1": False,
        "learner_state_authority_created_by_r1": False,
        "next_short_step": NEXT_SHORT_STEP,
        "next_short_step_scope": NEXT_SHORT_STEP_SCOPE,
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real62", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--learner-id", default="u01qb19r1-actual474-consumer")
    args = parser.parse_args(argv)
    try:
        report = run_acceptance(
            real62_path=args.real62,
            output_dir=args.output_dir,
            replace=args.replace,
            learner_id=args.learner_id,
        )
    except Exception as exc:
        print("STATUS=FAIL_A1FS_V1_U01QB19R1_CANONICAL474_REUSE_CONSUMER_ACCEPTANCE")
        print(f"ERROR={exc}")
        return 1

    consumer = report["consumer_acceptance"]
    print(f"STATUS={report['validation_status']}")
    print(f"ACTUAL_QB02_CATALOG={consumer['actual_qb02_catalog_count']}")
    print(f"PROJECTION_REFS={consumer['projection_reference_count']}")
    print(f"ITEM_ID_MUTATION={consumer['item_id_mutation_count']}")
    print(f"ASSET_KEY_MUTATION={consumer['asset_key_mutation_count']}")
    print(f"ITEM_DIGEST_MUTATION={consumer['item_digest_mutation_count']}")
    print(f"DATABASE_MUTATION={consumer['database_mutation_count']}")
    print(f"PRIVATE_ANSWER_READ={consumer['private_answer_read_count']}")
    print(f"UNIT02_CONTENT={consumer['unit02_content_created_count']}")
    print(f"A2_UNLOCK={consumer['a2_unlock_count']}")
    print(f"NEXT_SHORT_STEP={report['next_short_step']}")
    print(f"NEXT_SHORT_STEP_SCOPE={report['next_short_step_scope']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
