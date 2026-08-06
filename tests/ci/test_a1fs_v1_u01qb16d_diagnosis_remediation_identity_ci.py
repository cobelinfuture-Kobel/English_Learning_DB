from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as u16
from ulga.builders import _u01qb16b_task_angle_progression_adapter as u16b
from ulga.builders import _u01qb16d_question_diagnosis_remediation_identity_adapter as u16d


def _private_item(*, stimulus: str, prompt: str, options: list[str]) -> str:
    return json.dumps(
        {"stimulus": stimulus, "prompt": prompt, "options": options},
        separators=(",", ":"),
    )


def _database(path: Path) -> None:
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
              item_id TEXT PRIMARY KEY,
              asset_key TEXT NOT NULL,
              lesson_id TEXT NOT NULL,
              skill TEXT NOT NULL,
              pattern_family_id TEXT NOT NULL,
              unit_pattern_id TEXT NOT NULL,
              support_level TEXT NOT NULL,
              assessment_eligible INTEGER NOT NULL,
              transfer_eligible INTEGER NOT NULL,
              capture_enabled INTEGER NOT NULL,
              private_item_json TEXT NOT NULL,
              item_digest TEXT NOT NULL
            );
            CREATE TABLE u01qb02_item_exposures(
              exposure_seq INTEGER PRIMARY KEY AUTOINCREMENT,
              learner_id TEXT NOT NULL,
              item_id TEXT NOT NULL
            );
            CREATE TABLE u01qb13_blueprint_activities(
              activity_id TEXT PRIMARY KEY,
              form_ordinal INTEGER NOT NULL,
              skill TEXT NOT NULL,
              task_angle TEXT NOT NULL,
              support_level TEXT NOT NULL,
              pattern_family_ids_json TEXT NOT NULL
            );
            CREATE TABLE u01qb13_session_bindings(
              session_id TEXT NOT NULL,
              activity_id TEXT NOT NULL,
              item_id TEXT NOT NULL
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
            """
        )
        failed_private = _private_item(
            stimulus="There is ___ tree in the park.",
            prompt="Choose the best article.",
            options=["a", "an", "the"],
        )
        duplicate_private = _private_item(
            stimulus="There is ___ tree in the park.",
            prompt="Choose the best article.",
            options=["the", "an", "a"],
        )
        distinct_private = _private_item(
            stimulus="Mia can see ___ book on the desk.",
            prompt="Choose the best article.",
            options=["a", "an", "the"],
        )
        items = [
            ("ITEM-FAIL", "ASSET-FAIL", "READING", "U01-PF04-FIRST-MENTION-CONTEXT", "GUIDED", failed_private),
            ("ITEM-DUP", "ASSET-DUP", "READING", "U01-PF04-FIRST-MENTION-CONTEXT", "GUIDED", duplicate_private),
            ("ITEM-DISTINCT", "ASSET-DISTINCT", "READING", "U01-PF04-FIRST-MENTION-CONTEXT", "GUIDED", distinct_private),
        ]
        for item_id, asset_key, skill, family, support, private_json in items:
            connection.execute(
                "INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    item_id,
                    asset_key,
                    "UNIT01-READING",
                    skill,
                    family,
                    "PATTERN-U01",
                    support,
                    1,
                    0,
                    1,
                    private_json,
                    f"DIGEST-{item_id}",
                ),
            )
        connection.execute(
            "INSERT INTO response_attempts VALUES('ATTEMPT-1','LEARNER','SESSION-1','ASSET-FAIL')"
        )
        connection.execute("INSERT INTO scoring_results VALUES('ATTEMPT-1','AUTO_FAIL')")
        connection.execute(
            "INSERT INTO u01qb13_blueprint_activities VALUES(?,?,?,?,?,?)",
            (
                "ACTIVITY-1",
                1,
                "READING",
                "ARTICLE_CONTROL",
                "GUIDED",
                '["U01-PF04-FIRST-MENTION-CONTEXT","U01-PF08-TRANSFER-FIRST-MENTION"]',
            ),
        )
        connection.execute(
            "INSERT INTO u01qb13_session_bindings VALUES('SESSION-1','ACTIVITY-1','ITEM-FAIL')"
        )
        connection.execute(
            "INSERT INTO error_diagnoses VALUES('DIAG-1','LEARNER','ATTEMPT-1','[\"NODE-U01\"]')"
        )
        connection.execute(
            "INSERT INTO remediation_assignments VALUES('REMED-1','LEARNER','NODE-U01')"
        )
        connection.execute(
            "INSERT INTO reassessment_queue VALUES('REASSESS-1','LEARNER','NODE-U01')"
        )
        connection.execute(
            "INSERT INTO u01qb02_item_exposures(learner_id,item_id) VALUES('LEARNER','ITEM-FAIL')"
        )
        connection.commit()


def test_failed_question_is_bound_to_capability_m7_chain_and_distinct_reassessment(tmp_path: Path) -> None:
    database = tmp_path / "learner.sqlite3"
    _database(database)

    result = u16d.materialize(database, learner_id="LEARNER")

    assert result["validation_status"] == u16d.PASS_STATUS
    assert result["failed_attempt_identity_count"] == 1
    assert result["link_count"] == 1
    assert result["different_item_candidate_ready_count"] == 1
    assert result["different_item_candidate_unresolved_count"] == 0
    assert result["questionbank_modified"] is False
    assert result["scoring_modified"] is False

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        identity = dict(connection.execute(f"SELECT * FROM {u16d.ATTEMPT_TABLE}").fetchone())
        link = dict(connection.execute(f"SELECT * FROM {u16d.LINK_TABLE}").fetchone())

    assert identity["item_id"] == "ITEM-FAIL"
    assert identity["activity_id"] == "ACTIVITY-1"
    assert identity["task_angle"] == "ARTICLE_CONTROL"
    assert identity["capability_class"] == u16b.FIRST_MENTION_SELECTION
    assert link["diagnosis_id"] == "DIAG-1"
    assert json.loads(link["remediation_ids_json"]) == ["REMED-1"]
    assert json.loads(link["reassessment_ids_json"]) == ["REASSESS-1"]
    assert link["targeted_error_tag"] == "article_first_mention_selection_error"
    assert link["targeted_remediation_strategy"] == "RETEACH_ARTICLE_FIRST_MENTION_WITH_CONTRAST"
    assert link["candidate_state"] == "READY"
    assert link["different_item_id"] == "ITEM-DISTINCT"
    assert link["different_asset_key"] == "ASSET-DISTINCT"
    assert link["different_item_id"] != identity["item_id"]
    assert link["different_learner_visible_signature"] != identity["learner_visible_signature"]


def test_visible_duplicate_is_not_a_valid_reassessment_candidate(tmp_path: Path) -> None:
    database = tmp_path / "learner.sqlite3"
    _database(database)
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM u01qb02_item_catalog WHERE item_id='ITEM-DISTINCT'")
        connection.commit()

    result = u16d.materialize(database, learner_id="LEARNER")
    assert result["different_item_candidate_ready_count"] == 0
    assert result["different_item_candidate_unresolved_count"] == 1
    candidate = u16d.reassessment_candidate(database, diagnosis_id="DIAG-1")
    assert candidate is not None
    assert candidate["candidate_state"] == "NO_DISTINCT_CANDIDATE"
    assert candidate["different_item_id"] is None


def test_identity_materialization_is_deterministic_and_count_preserving(tmp_path: Path) -> None:
    database = tmp_path / "learner.sqlite3"
    _database(database)
    first = u16d.materialize(database, learner_id="LEARNER")
    with sqlite3.connect(database) as connection:
        before = connection.execute(
            "SELECT item_id,private_item_json,item_digest FROM u01qb02_item_catalog ORDER BY item_id"
        ).fetchall()
        attempt_before = connection.execute("SELECT * FROM response_attempts").fetchall()
        score_before = connection.execute("SELECT * FROM scoring_results").fetchall()
    second = u16d.materialize(database, learner_id="LEARNER")
    with sqlite3.connect(database) as connection:
        after = connection.execute(
            "SELECT item_id,private_item_json,item_digest FROM u01qb02_item_catalog ORDER BY item_id"
        ).fetchall()
        attempt_after = connection.execute("SELECT * FROM response_attempts").fetchall()
        score_after = connection.execute("SELECT * FROM scoring_results").fetchall()
        identity_count = connection.execute(f"SELECT COUNT(*) FROM {u16d.ATTEMPT_TABLE}").fetchone()[0]
        link_count = connection.execute(f"SELECT COUNT(*) FROM {u16d.LINK_TABLE}").fetchone()[0]
    assert first == second
    assert before == after
    assert attempt_before == attempt_after
    assert score_before == score_after
    assert identity_count == 1
    assert link_count == 1


def test_adapter_installs_on_existing_m7_build_snapshot_only() -> None:
    original = u16d._ORIGINAL_BUILD_SNAPSHOT
    try:
        u16d.install()
        assert u16d.installed() is True
        assert u16d.m7.MasteryRemediationEngine.build_snapshot is u16d.build_snapshot_with_u01qb16d_identity
    finally:
        u16d.m7.MasteryRemediationEngine.build_snapshot = original
        u16d._INSTALLED = False


def test_option_reordering_is_same_learner_visible_question() -> None:
    left = {
        "item_id": "A",
        "skill": "READING",
        "private_item_json": _private_item(
            stimulus="There is ___ tree in the park.",
            prompt="Choose the best article.",
            options=["a", "an", "the"],
        ),
    }
    right = {
        "item_id": "B",
        "skill": "READING",
        "private_item_json": _private_item(
            stimulus="There is ___ tree in the park.",
            prompt="Choose the best article.",
            options=["the", "a", "an"],
        ),
    }
    assert u16.learner_visible_signature(left) == u16.learner_visible_signature(right)
