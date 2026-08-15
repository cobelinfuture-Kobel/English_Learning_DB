from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from ulga.builders import build_a1fs_v1_u01qb19_unit01_canonical474_cumulative_reuse_reference_projection as u19


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _database(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE u01qb02_item_catalog(
              item_id TEXT PRIMARY KEY, asset_key TEXT UNIQUE, lesson_id TEXT, skill TEXT,
              pattern_family_id TEXT, unit_pattern_id TEXT, support_level TEXT,
              assessment_eligible INTEGER, transfer_eligible INTEGER, capture_enabled INTEGER,
              private_item_json TEXT, item_digest TEXT UNIQUE
            );
            CREATE TABLE u01qb02_item_exposures(
              exposure_seq INTEGER PRIMARY KEY AUTOINCREMENT, exposure_id TEXT, learner_id TEXT,
              session_id TEXT, item_id TEXT, selection_reason TEXT, exposure_at TEXT,
              previous_hash TEXT, exposure_hash TEXT
            );
            CREATE TABLE response_attempts(
              attempt_id TEXT PRIMARY KEY, learner_id TEXT, asset_key TEXT
            );
            CREATE TABLE scoring_results(attempt_id TEXT PRIMARY KEY, outcome TEXT);
            CREATE TABLE reassessment_queue(
              reassessment_id TEXT PRIMARY KEY, learner_id TEXT, node_id TEXT,
              source_remediation_id TEXT, lesson_ids_json TEXT, asset_keys_json TEXT,
              queue_state TEXT, created_at TEXT, queue_digest TEXT
            );
            CREATE TABLE review_schedules(
              schedule_id TEXT PRIMARY KEY, learner_id TEXT, node_id TEXT,
              sequence_index INTEGER, spacing_stage INTEGER, interval_days INTEGER,
              due_at TEXT, schedule_state TEXT, source_m7_snapshot_digest TEXT,
              evidence_attempt_id TEXT, reviewed_at TEXT, created_at TEXT, schedule_digest TEXT
            );
            """
        )
        rows = []
        for index in range(u19.EXPECTED_RUNTIME_ITEMS):
            skill = "READING" if index < 200 else "WRITING" if index < 400 else "SPEAKING"
            lesson = f"A1FS:UNIT01:{skill}"
            rows.append(
                (
                    f"U01-I{index:03d}", f"U01QB02:K{index:03d}", lesson, skill,
                    f"PF-{index % 17:02d}", "U01-PATTERN", "GUIDED",
                    int(skill != "SPEAKING"), int(index < 12), int(skill != "SPEAKING"),
                    json.dumps({"answer": "PRIVATE"}), hashlib.sha256(f"item:{index}".encode()).hexdigest(),
                )
            )
        connection.executemany(
            "INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", rows
        )
        for index in range(11):
            connection.execute(
                "INSERT INTO u01qb02_item_exposures(exposure_id,learner_id,session_id,item_id,selection_reason,exposure_at,previous_hash,exposure_hash) VALUES(?,?,?,?,?,?,?,?)",
                (f"E{index}", "L1", f"S{index}", f"U01-I{index:03d}", "NEW_OR_UNSEEN", f"2026-08-01T00:00:{index:02d}Z", "0", f"H{index}"),
            )
        connection.execute("INSERT INTO response_attempts VALUES(?,?,?)", ("A1", "L1", "U01QB02:K000"))
        connection.execute("INSERT INTO scoring_results VALUES(?,?)", ("A1", "AUTO_FAIL"))
        connection.execute(
            "INSERT INTO reassessment_queue VALUES(?,?,?,?,?,?,?,?,?)",
            ("R1", "L1", "NODE", "M7", "[]", json.dumps(["U01QB02:K001"]), "PENDING", "2026-08-01T00:00:00Z", "D"),
        )
        connection.execute(
            "INSERT INTO review_schedules VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("M8", "L1", "LESSON:READING:A1FS:UNIT01:READING", 1, 1, 1, "2026-08-02T00:00:00Z", "DUE", "M7SHA", None, None, "2026-08-01T00:00:00Z", "SD"),
        )
        connection.commit()


def test_u01qb19_projects_exact_474_references_without_database_mutation(tmp_path: Path) -> None:
    database = tmp_path / "learner.sqlite3"
    _database(database)
    before = _sha(database)
    result = u19.build_reuse_projection(database, learner_id="L1")
    after = _sha(database)

    assert before == after
    assert result["validation_status"] == u19.PASS_STATUS
    assert result["canonical_item_count"] == 474
    assert result["unique_canonical_item_count"] == 474
    assert result["base_item_count"] == 288
    assert result["extension_item_count"] == 186
    assert result["reuse_mode"] == "REFERENCE_ONLY"
    assert len(result["items"]) == 474
    assert len({row["item_id"] for row in result["items"]}) == 474
    assert len({row["asset_key"] for row in result["items"]}) == 474
    assert all("private_item_json" not in row for row in result["items"])
    assert all("answer" not in row for row in result["items"])

    by_id = {row["item_id"]: row for row in result["items"]}
    assert "REVIEW" in by_id["U01-I000"]["reuse_purposes"]
    assert "RETENTION" in by_id["U01-I000"]["reuse_purposes"]
    assert "REMEDIATION" in by_id["U01-I000"]["reuse_purposes"]
    assert "REASSESSMENT" in by_id["U01-I001"]["reuse_purposes"]
    assert "CROSS_UNIT_TRANSFER" in by_id["U01-I000"]["reuse_purposes"]
    assert "REVIEW" not in by_id["U01-I010"]["reuse_purposes"]

    boundaries = result["semantic_boundaries"]
    assert boundaries == {
        "question_authoring_performed": False,
        "canonical_id_mutation": False,
        "answer_read_or_mutation": False,
        "scoring_mutation": False,
        "selector_quota_mutation": False,
        "form_activity_authority_created": False,
        "parallel_questionbank_created": False,
        "parallel_learning_state_created": False,
        "unit02_content_created": False,
        "a2_unlocked": False,
    }


def test_u01qb19_is_bound_to_existing_authorities_and_denominators() -> None:
    assert u19.EXPECTED_RUNTIME_ITEMS == u19.u13.EXPECTED_RUNTIME_COUNT == 474
    assert u19.EXPECTED_BASE_ITEMS == u19.u12.EXPECTED_BASE_COUNT == 288
    assert u19.EXPECTED_EXTENSION_ITEMS == u19.u12.EXPECTED_EXTENSION_COUNT == 186
    assert u19.EXPECTED_BASE_ITEMS + u19.EXPECTED_EXTENSION_ITEMS == u19.EXPECTED_RUNTIME_ITEMS
    assert u19.qb02.SELECTION_REASONS >= {"REMEDIATION", "SCHEDULED_REVIEW", "TRANSFER"}
    assert u19.m7.TASK_ID == "A1FS-V1-M7_MasteryErrorDiagnosisRemediationAndReassessment"
    assert u19.m8.TASK_ID == "A1FS-V1-M8_ReviewSchedulingRetentionAndSpacedPractice"
