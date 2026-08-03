from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as qb02
from ulga.builders import build_a1fs_v1_u01qb10_unit01_question_bank_production_angle_coverage_reconciliation as u01qb10
from ulga.builders import build_a1fs_v1_u01qb11_unit01_reconciled_question_bank_runtime_migration_and_474_replay as builder
from ulga.builders import _razq01e_existing_qb_runtime_core as razq01e
from ulga.validators import validate_a1fs_v1_u01qb11_unit01_reconciled_question_bank_runtime_migration_and_474_replay as validator


EXTENSION_SHA = "b" * 64


def _prepare_m3_database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(m3.SCHEMA_SQL)
        connection.execute(
            "INSERT INTO metadata(key,value) VALUES('validation_status',?)", (m3.STATUS,)
        )
        for skill, lesson_id in qb02.UNIT01_LESSONS.items():
            connection.execute(
                """INSERT INTO lesson_catalog
                (lesson_id,lesson_node_id,skill,level,roles_json,requirement_node_ids_json,payload_access_allowed)
                VALUES(?,?,?,?,?,?,1)""",
                (lesson_id, f"NODE:{lesson_id}", skill, "A1", "[]", "[]"),
            )


def _fixture_extension_items() -> list[dict]:
    _approved, base_items = qb02.approved_bank()
    by_skill = {
        skill: [deepcopy(row) for row in base_items if row["skill"] == skill]
        for skill in ("READING", "WRITING", "SPEAKING")
    }
    result: list[dict] = []
    for index in range(62):
        content_asset_id = f"FIXTURE-REAL62-{index:03d}"
        for skill in ("READING", "WRITING", "SPEAKING"):
            source = deepcopy(by_skill[skill][index % len(by_skill[skill])])
            source["item_id"] = f"U01QB01-RAZQ01E-{skill}-FIXTURE-{index:03d}"
            source["content_asset_id"] = content_asset_id
            source["semantic_signature"] = qb02.digest(
                {
                    "fixture": "REAL62",
                    "content_asset_id": content_asset_id,
                    "skill": skill,
                    "source": source["semantic_signature"],
                }
            )
            result.append(source)
    return result


def _install_legacy_474(path: Path) -> None:
    _prepare_m3_database(path)
    runtime = qb02.Unit01ApprovedVariantSessionRuntime(path)
    initialized = runtime.initialize()
    assert initialized["registered_item_count"] == 288
    items = _fixture_extension_items()
    assert len(items) == 186
    with runtime.write() as connection:
        connection.executescript(razq01e.EXTENSION_SQL)
        for item in items:
            razq01e._register_item(
                connection,
                item,
                approved_extension_sha256=EXTENSION_SHA,
            )
        connection.executemany(
            "INSERT OR REPLACE INTO razq01e_metadata(key,value) VALUES(?,?)",
            {
                "task_id": razq01e.TASK_ID,
                "schema_version": razq01e.SCHEMA_VERSION,
                "validation_status": razq01e.PASS_STATUS,
                "approved_extension_artifact_sha256": EXTENSION_SHA,
                "extension_item_count": "186",
                "base_item_count": "288",
                "combined_runtime_item_count": "474",
                "existing_u01qb02_runtime_reused": "true",
                "parallel_runtime_created": "false",
                "a2_unlocked": "false",
            }.items(),
        )
        connection.executemany(
            "INSERT OR REPLACE INTO u01qb02_metadata(key,value) VALUES(?,?)",
            {
                "razq01e_extension_artifact_sha256": EXTENSION_SHA,
                "razq01e_extension_item_count": "186",
                "razq01e_combined_runtime_item_count": "474",
            }.items(),
        )
        assert connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0] == 474
        assert connection.execute("SELECT COUNT(*) FROM razq01e_extension_items").fetchone()[0] == 186


def test_u01qb11_migrates_legacy_474_to_reconciled_474_and_preserves_real62(tmp_path: Path) -> None:
    database = tmp_path / "learner_runtime.sqlite3"
    _install_legacy_474(database)
    with sqlite3.connect(database) as connection:
        before_extension = connection.execute(
            "SELECT item_id,extension_item_sha256 FROM razq01e_extension_items ORDER BY item_id"
        ).fetchall()
        legacy_contract_count = connection.execute(
            "SELECT COUNT(*) FROM response_contracts WHERE asset_key LIKE 'U01QB02:%'"
        ).fetchone()[0]
    assert legacy_contract_count == 474

    result = builder.migrate_runtime(database)
    assert result["already_migrated"] is False
    assert result["retired_base_item_count"] == 48
    assert result["production_item_added_count"] == 48
    assert result["base_item_count"] == 288
    assert result["extension_item_count"] == 186
    assert result["combined_runtime_item_count"] == 474

    with sqlite3.connect(database) as connection:
        after_extension = connection.execute(
            "SELECT item_id,extension_item_sha256 FROM razq01e_extension_items ORDER BY item_id"
        ).fetchall()
        assert before_extension == after_extension
        assert connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0] == 474
        # Retired response contracts remain available for historical M6 attempts.
        assert connection.execute(
            "SELECT COUNT(*) FROM response_contracts WHERE asset_key LIKE 'U01QB02:%'"
        ).fetchone()[0] == 522
        family_counts = dict(
            connection.execute(
                "SELECT pattern_family_id,COUNT(*) FROM u01qb02_item_catalog GROUP BY pattern_family_id"
            ).fetchall()
        )
    for family, count in builder.EXPECTED_PRODUCTION_FAMILY_COUNTS.items():
        assert family_counts[family] == count


def test_u01qb11_replays_all_474_through_existing_m6_contracts(tmp_path: Path) -> None:
    database = tmp_path / "learner_runtime.sqlite3"
    _install_legacy_474(database)
    builder.migrate_runtime(database)
    replay = builder.replay_474(database)
    assert replay["runtime_item_count"] == 474
    assert replay["base_item_count"] == 288
    assert replay["extension_item_count"] == 186
    assert replay["skill_distribution"] == {
        "READING": 192,
        "SPEAKING": 87,
        "WRITING": 195,
    }
    assert replay["capture_enabled_item_count"] == 387
    assert replay["deterministic_auto_pass_replay_count"] == 351
    assert replay["feature_rubric_pending_human_replay_count"] == 36
    assert replay["speaking_practice_only_count"] == 87
    assert replay["production_family_counts"] == builder.EXPECTED_PRODUCTION_FAMILY_COUNTS


def test_u01qb11_executes_real_m3_m6_attempt_canary_for_three_new_families(tmp_path: Path) -> None:
    database = tmp_path / "learner_runtime.sqlite3"
    _install_legacy_474(database)
    report = builder.run_acceptance(
        database,
        run_attempt_canary=True,
        canary_learner_id="u01qb11-test-learner",
        canary_session_id="u01qb11-test-writing-session",
    )
    validated = validator.validate_report(report)
    assert validated["runtime_item_count"] == 474
    assert validated["production_attempt_canary_executed"] is True
    canary = report["production_attempt_canary"]
    assert canary["outcomes"] == {
        u01qb10.PF13: "AUTO_PASS",
        u01qb10.PF14: "PENDING_HUMAN_REVIEW",
        u01qb10.PF15: "PENDING_HUMAN_REVIEW",
    }
    with sqlite3.connect(database) as connection:
        outcomes = dict(
            connection.execute(
                """SELECT c.pattern_family_id,r.outcome
                   FROM response_attempts a
                   JOIN scoring_results r USING(attempt_id)
                   JOIN u01qb02_item_catalog c ON c.asset_key=a.asset_key
                   WHERE a.session_id=?""",
                ("u01qb11-test-writing-session",),
            ).fetchall()
        )
    assert outcomes == canary["outcomes"]


def test_u01qb11_migration_is_idempotent(tmp_path: Path) -> None:
    database = tmp_path / "learner_runtime.sqlite3"
    _install_legacy_474(database)
    first = builder.migrate_runtime(database)
    second = builder.migrate_runtime(database)
    assert first["already_migrated"] is False
    assert second["already_migrated"] is True
    assert second["retired_base_item_count"] == 0
    assert second["production_item_added_count"] == 0
    assert second["real62_extension_identity_sha256"] == first["real62_extension_identity_sha256"]
    assert builder.replay_474(database)["runtime_item_count"] == 474


def test_u01qb11_validator_rejects_expanded_bank_claim(tmp_path: Path) -> None:
    database = tmp_path / "learner_runtime.sqlite3"
    _install_legacy_474(database)
    report = builder.run_acceptance(database)
    drifted = deepcopy(report)
    drifted["boundaries"]["question_bank_total_expanded"] = True
    unsigned = dict(drifted)
    unsigned.pop("readback_sha256", None)
    drifted["readback_sha256"] = builder.digest(unsigned)
    try:
        validator.validate_report(drifted)
    except validator.RuntimeMigrationValidationError as exc:
        assert "BOUNDARIES_INVALID" in str(exc)
    else:
        raise AssertionError("validator accepted expanded-bank claim")
