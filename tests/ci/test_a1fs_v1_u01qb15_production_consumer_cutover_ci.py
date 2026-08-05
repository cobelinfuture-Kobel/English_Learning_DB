from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from product.a1fs_v1_2_1 import u01qb15_runtime_server as runtime


def _gate_database(path: Path, *, skill: str, count: int) -> Path:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE learning_sessions(
              session_id TEXT PRIMARY KEY,
              lesson_id TEXT NOT NULL,
              skill TEXT NOT NULL,
              session_state TEXT NOT NULL,
              session_version INTEGER NOT NULL
            );
            CREATE TABLE u01qb13_session_bindings(
              session_id TEXT NOT NULL,
              activity_id TEXT NOT NULL,
              item_id TEXT NOT NULL,
              item_position INTEGER NOT NULL,
              binding_quality TEXT NOT NULL,
              is_assessment_evidence INTEGER NOT NULL
            );
            CREATE TABLE u01qb02_item_exposures(
              session_id TEXT NOT NULL,
              item_id TEXT NOT NULL
            );
            CREATE TABLE u01qb02_item_catalog(
              item_id TEXT PRIMARY KEY,
              asset_key TEXT NOT NULL
            );
            CREATE TABLE response_attempts(
              attempt_id TEXT PRIMARY KEY,
              session_id TEXT NOT NULL,
              asset_key TEXT NOT NULL,
              attempt_sequence INTEGER NOT NULL
            );
            CREATE TABLE scoring_results(
              attempt_id TEXT PRIMARY KEY,
              outcome TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO learning_sessions VALUES(?,?,?,?,?)",
            ("S1", "L1", skill, "ACTIVE", 4),
        )
        for index in range(1, count + 1):
            item_id = f"ITEM-{index:02d}"
            asset_key = f"ASSET-{index:02d}"
            connection.execute(
                "INSERT INTO u01qb13_session_bindings VALUES(?,?,?,?,?,?)",
                ("S1", f"ACT-{index:02d}", item_id, index, "EXACT", 0),
            )
            connection.execute(
                "INSERT INTO u01qb02_item_catalog VALUES(?,?)", (item_id, asset_key)
            )
        connection.commit()
    return path


def test_product_manifest_points_at_u01qb15_consumer_without_redefining_static_asset_denominator() -> None:
    manifest_path = Path("product/a1fs_v1_2_1/product_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["serve_module"] == runtime.MODULE
    assert manifest["start_command"] == f"python -m {runtime.MODULE} start"
    assert manifest["asset_count"] == 277
    assert manifest["unit01_activity_count"] == 24
    assert manifest["unit01_questionbank_revision"] == "U01QB15-R1"
    assert manifest["unit01_questionbank_runtime_item_count"] == 474
    assert manifest["unit01_questionbank_form_count"] == 12


def test_reading_blueprint_completion_gate_counts_only_bound_form_activities(tmp_path: Path) -> None:
    database = _gate_database(tmp_path / "reading.sqlite3", skill="READING", count=8)
    with sqlite3.connect(database) as connection:
        for index in range(1, 9):
            item_id = f"ITEM-{index:02d}"
            asset_key = f"ASSET-{index:02d}"
            attempt_id = f"ATT-{index:02d}"
            outcome = "PENDING_HUMAN_REVIEW" if index == 8 else "AUTO_PASS"
            connection.execute(
                "INSERT INTO response_attempts VALUES(?,?,?,?)",
                (attempt_id, "S1", asset_key, 1),
            )
            connection.execute(
                "INSERT INTO scoring_results VALUES(?,?)", (attempt_id, outcome)
            )
        connection.commit()
    gate = runtime.u01qb15_completion_readiness(database, "S1")
    assert gate["gate_mode"] == "U01QB15_BLUEPRINT_LATEST_ATTEMPT_PASS_OR_HUMAN_APPROVAL"
    assert gate["required_response_count"] == 8
    assert gate["passed_response_count"] == 7
    assert gate["pending_human_review_count"] == 1
    assert gate["completion_allowed"] is False


def test_speaking_blueprint_completion_gate_requires_four_real_exposures(tmp_path: Path) -> None:
    database = _gate_database(tmp_path / "speaking.sqlite3", skill="SPEAKING", count=4)
    with sqlite3.connect(database) as connection:
        for index in range(1, 5):
            connection.execute(
                "INSERT INTO u01qb02_item_exposures VALUES(?,?)",
                ("S1", f"ITEM-{index:02d}"),
            )
        connection.commit()
    gate = runtime.u01qb15_completion_readiness(database, "S1")
    assert gate["gate_mode"] == "U01QB15_BLUEPRINT_PRACTICE_EXPOSURE"
    assert gate["required_response_count"] == 0
    assert gate["required_exposure_count"] == 4
    assert gate["completed_exposure_count"] == 4
    assert gate["completion_allowed"] is True
    assert gate["mastery_claimed"] is False


def test_cutover_status_requires_exact_474_186_240_12_denominators(tmp_path: Path) -> None:
    database = tmp_path / "cutover.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            f"""
            CREATE TABLE {runtime.CUTOVER_TABLE}(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE u01qb02_item_catalog(item_id INTEGER);
            CREATE TABLE razq01e_extension_items(item_id INTEGER);
            CREATE TABLE u01qb13_blueprint_activities(form_ordinal INTEGER);
            """
        )
        connection.executemany(
            f"INSERT INTO {runtime.CUTOVER_TABLE}(key,value) VALUES(?,?)",
            [
                ("validation_status", runtime.PASS_STATUS),
                ("real62_artifact_sha256", runtime.EXPECTED_REAL62_ARTIFACT_SHA256),
                ("questionbank_revision", "U01QB15-R1"),
                ("runtime_consumer", runtime.u13.TASK_ID),
            ],
        )
        connection.executemany("INSERT INTO u01qb02_item_catalog VALUES(?)", [(i,) for i in range(474)])
        connection.executemany("INSERT INTO razq01e_extension_items VALUES(?)", [(i,) for i in range(186)])
        connection.executemany(
            "INSERT INTO u01qb13_blueprint_activities VALUES(?)",
            [((i % 12) + 1,) for i in range(240)],
        )
        connection.commit()
    status = runtime.cutover_status(database)
    assert status["active"] is True
    assert status["runtime_item_count"] == 474
    assert status["extension_item_count"] == 186
    assert status["blueprint_activity_count"] == 240
    assert status["form_count"] == 12


def test_product_consumer_policy_boundaries() -> None:
    assert runtime.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert runtime.A1FS_CONTENT_POLICY_EXEMPTION
    assert runtime.NEXT_SHORT_STEP == "A1FS-V1-U01QB15_LearnerFacingE2EAcceptance"
