from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from product import a1fs_v1_2_1 as product_package
from ulga.builders import _u01qb16b_task_angle_progression_adapter as u16b
from ulga.builders import _u01qb16d_question_diagnosis_remediation_identity_adapter as u16d
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7


def _private_item(stimulus: str, answer: str) -> str:
    return json.dumps(
        {
            "stimulus": stimulus,
            "prompt": "Choose the article for the first mention.",
            "options": ["a", "an", "the"],
            "correct_answer": answer,
            "grammar_target_ids": ["ARTICLE_NOUN_PHRASE_CONTROL"],
        }
    )


def _database(tmp_path: Path, *, include_distinct_candidate: bool = True) -> Path:
    path = tmp_path / "learner.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE response_attempts(
              attempt_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              session_id TEXT NOT NULL,
              asset_key TEXT NOT NULL
            );
            CREATE TABLE scoring_results(
              attempt_id TEXT PRIMARY KEY,
              outcome TEXT NOT NULL
            );
            CREATE TABLE u01qb02_item_catalog(
              asset_key TEXT PRIMARY KEY,
              item_id TEXT NOT NULL UNIQUE,
              skill TEXT NOT NULL,
              pattern_family_id TEXT NOT NULL,
              support_level TEXT NOT NULL,
              capture_enabled INTEGER NOT NULL,
              private_item_json TEXT NOT NULL
            );
            CREATE TABLE u01qb13_blueprint_activities(
              activity_id TEXT PRIMARY KEY,
              form_ordinal INTEGER NOT NULL,
              task_angle TEXT NOT NULL,
              support_level TEXT NOT NULL,
              pattern_family_ids_json TEXT NOT NULL
            );
            CREATE TABLE u01qb13_session_bindings(
              session_id TEXT NOT NULL,
              item_id TEXT NOT NULL,
              activity_id TEXT NOT NULL
            );
            CREATE TABLE error_diagnoses(
              diagnosis_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              attempt_id TEXT NOT NULL,
              node_ids_json TEXT NOT NULL
            );
            CREATE TABLE remediation_assignments(
              remediation_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              node_id TEXT NOT NULL
            );
            CREATE TABLE reassessment_queue(
              reassessment_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              node_id TEXT NOT NULL
            );
            CREATE TABLE u01qb02_item_exposures(
              learner_id TEXT NOT NULL,
              item_id TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO u01qb13_blueprint_activities VALUES(?,?,?,?,?)",
            (
                "ACT-1",
                1,
                "ARTICLE_CONTROL",
                "GUIDED",
                json.dumps(
                    [
                        "U01-PF04-FIRST-MENTION-CONTEXT",
                        "U01-PF08-TRANSFER-FIRST-MENTION",
                    ]
                ),
            ),
        )
        connection.execute(
            "INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?,?,?,?)",
            (
                "AK-FAIL",
                "ITEM-FAIL",
                "READING",
                "U01-PF04-FIRST-MENTION-CONTEXT",
                "GUIDED",
                1,
                _private_item("There is ___ apple at the picnic.", "an"),
            ),
        )
        if include_distinct_candidate:
            connection.execute(
                "INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?,?,?,?)",
                (
                    "AK-NEW",
                    "ITEM-NEW",
                    "READING",
                    "U01-PF04-FIRST-MENTION-CONTEXT",
                    "GUIDED",
                    1,
                    _private_item("There is ___ bag at the picnic.", "a"),
                ),
            )
        connection.execute(
            "INSERT INTO response_attempts VALUES(?,?,?,?)",
            ("ATT-FAIL", "LEARNER", "SESSION-1", "AK-FAIL"),
        )
        connection.execute(
            "INSERT INTO scoring_results VALUES(?,?)",
            ("ATT-FAIL", "AUTO_FAIL"),
        )
        connection.execute(
            "INSERT INTO u01qb13_session_bindings VALUES(?,?,?)",
            ("SESSION-1", "ITEM-FAIL", "ACT-1"),
        )
        connection.execute(
            "INSERT INTO error_diagnoses VALUES(?,?,?,?)",
            ("DIAG-1", "LEARNER", "ATT-FAIL", json.dumps(["NODE-1"])),
        )
        connection.execute(
            "INSERT INTO remediation_assignments VALUES(?,?,?)",
            ("REMED-1", "LEARNER", "NODE-1"),
        )
        connection.execute(
            "INSERT INTO reassessment_queue VALUES(?,?,?)",
            ("REASSESS-1", "LEARNER", "NODE-1"),
        )
        connection.commit()
    return path


def test_product_installs_single_u01qb16d_bridge_on_canonical_m7() -> None:
    assert product_package is not None
    assert u16d.installed() is True
    assert m7.MasteryRemediationEngine.build_snapshot is u16d.build_snapshot_with_u01qb16d_identity
    assert u16d.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert u16d.A1FS_CONTENT_POLICY_EXEMPTION


def test_failed_questionbank_attempt_links_to_existing_m7_identity_and_distinct_reassessment(
    tmp_path: Path,
) -> None:
    database = _database(tmp_path)
    result = u16d.materialize(database, learner_id="LEARNER")
    assert result["validation_status"] == u16d.PASS_STATUS
    assert result["failed_attempt_identity_count"] == 1
    assert result["link_count"] == 1
    assert result["different_item_candidate_ready_count"] == 1
    assert result["questionbank_modified"] is False
    assert result["scoring_modified"] is False

    with sqlite3.connect(database) as connection:
        identity = connection.execute(
            f"SELECT item_id,activity_id,task_angle,capability_class FROM {u16d.ATTEMPT_TABLE} WHERE attempt_id='ATT-FAIL'"
        ).fetchone()
        link = connection.execute(
            f"SELECT diagnosis_id,remediation_ids_json,reassessment_ids_json,different_item_id,candidate_state,targeted_error_tag,targeted_remediation_strategy FROM {u16d.LINK_TABLE} WHERE diagnosis_id='DIAG-1'"
        ).fetchone()
    assert identity == (
        "ITEM-FAIL",
        "ACT-1",
        "ARTICLE_CONTROL",
        u16b.FIRST_MENTION_SELECTION,
    )
    assert json.loads(link[1]) == ["REMED-1"]
    assert json.loads(link[2]) == ["REASSESS-1"]
    assert link[3] == "ITEM-NEW"
    assert link[4] == "READY"
    assert link[5] == "article_first_mention_selection_error"
    assert link[6] == "RETEACH_ARTICLE_FIRST_MENTION_WITH_CONTRAST"


def test_reassessment_candidate_is_learner_visible_distinct_from_failed_item(tmp_path: Path) -> None:
    database = _database(tmp_path)
    u16d.materialize(database, learner_id="LEARNER")
    candidate = u16d.reassessment_candidate(database, diagnosis_id="DIAG-1")
    assert candidate is not None
    assert candidate["candidate_state"] == "READY"
    assert candidate["different_item_id"] == "ITEM-NEW"
    assert candidate["different_learner_visible_signature"]


def test_no_distinct_candidate_fails_closed_without_mutating_m7_queue_identity(tmp_path: Path) -> None:
    database = _database(tmp_path, include_distinct_candidate=False)
    result = u16d.materialize(database, learner_id="LEARNER")
    assert result["different_item_candidate_ready_count"] == 0
    assert result["different_item_candidate_unresolved_count"] == 1
    candidate = u16d.reassessment_candidate(database, diagnosis_id="DIAG-1")
    assert candidate is not None
    assert candidate["candidate_state"] == "NO_DISTINCT_CANDIDATE"
    assert candidate["different_item_id"] is None
    with sqlite3.connect(database) as connection:
        remediation = connection.execute(
            "SELECT remediation_id FROM remediation_assignments WHERE learner_id='LEARNER' AND node_id='NODE-1'"
        ).fetchone()
        reassessment = connection.execute(
            "SELECT reassessment_id FROM reassessment_queue WHERE learner_id='LEARNER' AND node_id='NODE-1'"
        ).fetchone()
    assert remediation == ("REMED-1",)
    assert reassessment == ("REASSESS-1",)
