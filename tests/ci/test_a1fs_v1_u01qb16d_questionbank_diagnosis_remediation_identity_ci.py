from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from product import a1fs_v1_2_1 as product_package
from ulga.builders import _u01qb16_learner_visible_distinctness_adapter as u16
from ulga.builders import _u01qb16b_task_angle_progression_adapter as u16b
from ulga.builders import _u01qb16d_questionbank_diagnosis_remediation_identity_adapter as u16d
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7


def _database(tmp_path: Path) -> Path:
    path = tmp_path / "learner.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE response_attempts(
              attempt_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              asset_key TEXT NOT NULL,
              response_json TEXT NOT NULL
            );
            CREATE TABLE u01qb02_item_catalog(
              asset_key TEXT PRIMARY KEY,
              item_id TEXT NOT NULL,
              pattern_family_id TEXT NOT NULL,
              private_item_json TEXT NOT NULL
            );
            """
        )
        items = [
            (
                "AK-FIRST",
                "ITEM-FIRST",
                "U01-PF04-FIRST-MENTION-CONTEXT",
                {
                    "correct_answer": "an",
                    "grammar_target_ids": ["ARTICLE_NOUN_PHRASE_CONTROL"],
                },
                "ATT-FIRST",
                "a",
            ),
            (
                "AK-REF",
                "ITEM-REF",
                "U01-PF05-KNOWN-REFERENCE-CONTEXT",
                {
                    "correct_answer": "the",
                    "grammar_target_ids": ["ARTICLE_NOUN_PHRASE_CONTROL"],
                },
                "ATT-REF",
                "a",
            ),
        ]
        for asset_key, item_id, family, private_item, attempt_id, answer in items:
            connection.execute(
                "INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?)",
                (asset_key, item_id, family, json.dumps(private_item)),
            )
            connection.execute(
                "INSERT INTO response_attempts VALUES(?,?,?,?)",
                (attempt_id, "LEARNER", asset_key, json.dumps(answer)),
            )
        connection.commit()
    return path


def _visible_item(*, stimulus: str, correct: str = "an") -> str:
    return json.dumps(
        {
            "stimulus": stimulus,
            "prompt": "Choose the best article.",
            "options": ["a", "an", "the"],
            "correct_answer": correct,
            "grammar_target_ids": ["ARTICLE_NOUN_PHRASE_CONTROL"],
        },
        separators=(",", ":"),
    )


def _lineage_database(tmp_path: Path) -> Path:
    path = tmp_path / "lineage.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE response_attempts(
              attempt_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              session_id TEXT NOT NULL,
              asset_key TEXT NOT NULL,
              response_json TEXT NOT NULL
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
        failed = _visible_item(stimulus="There is ___ apple in the bag.")
        duplicate = json.dumps(
            {
                "stimulus": "There is ___ apple in the bag.",
                "prompt": "Choose the best article.",
                "options": ["the", "a", "an"],
                "correct_answer": "an",
                "grammar_target_ids": ["ARTICLE_NOUN_PHRASE_CONTROL"],
            },
            separators=(",", ":"),
        )
        distinct = _visible_item(stimulus="Mia can see ___ orange at the picnic.")
        for item_id, asset_key, private_json in (
            ("ITEM-FAIL", "ASSET-FAIL", failed),
            ("ITEM-DUP", "ASSET-DUP", duplicate),
            ("ITEM-DISTINCT", "ASSET-DISTINCT", distinct),
        ):
            connection.execute(
                "INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    item_id,
                    asset_key,
                    "UNIT01-READING",
                    "READING",
                    "U01-PF04-FIRST-MENTION-CONTEXT",
                    "PATTERN-U01",
                    "GUIDED",
                    1,
                    0,
                    1,
                    private_json,
                    f"DIGEST-{item_id}",
                ),
            )
        connection.execute(
            "INSERT INTO response_attempts VALUES(?,?,?,?,?)",
            ("ATTEMPT-1", "LEARNER", "SESSION-1", "ASSET-FAIL", json.dumps("a")),
        )
        connection.execute(
            "INSERT INTO u01qb13_blueprint_activities VALUES(?,?,?,?,?)",
            (
                "ACTIVITY-1",
                1,
                "READING",
                "ARTICLE_CONTROL",
                '["U01-PF04-FIRST-MENTION-CONTEXT","U01-PF08-TRANSFER-FIRST-MENTION"]',
            ),
        )
        connection.execute(
            "INSERT INTO u01qb13_session_bindings VALUES(?,?,?)",
            ("SESSION-1", "ACTIVITY-1", "ITEM-FAIL"),
        )
        connection.execute(
            "INSERT INTO error_diagnoses VALUES(?,?,?,?)",
            ("DIAG-1", "LEARNER", "ATTEMPT-1", '["NODE-U01"]'),
        )
        connection.execute(
            "INSERT INTO remediation_assignments VALUES(?,?,?)",
            ("REMED-1", "LEARNER", "NODE-U01"),
        )
        connection.execute(
            "INSERT INTO reassessment_queue VALUES(?,?,?)",
            ("REASSESS-1", "LEARNER", "NODE-U01"),
        )
        connection.execute(
            "INSERT INTO u01qb02_item_exposures(learner_id,item_id) VALUES(?,?)",
            ("LEARNER", "ITEM-FAIL"),
        )
        connection.commit()
    return path


def test_product_installs_u01qb16d_into_existing_m7_authority() -> None:
    assert product_package is not None
    assert u16d.installed() is True
    assert m7._diagnostic_tags is u16d.diagnostic_tags
    assert m7._strategy is u16d.strategy
    assert m7.MasteryRemediationEngine.build_snapshot is u16d.build_snapshot
    assert u16d.A1FS_CONTENT_POLICY_MODE == "NOT_CONTENT_PRODUCER"
    assert u16d.A1FS_CONTENT_POLICY_EXEMPTION


def test_first_mention_a_an_error_gets_precise_questionbank_identity(tmp_path: Path) -> None:
    mapping = u16d.attempt_diagnostic_identity_map(_database(tmp_path), learner_id="LEARNER")
    tags = set(mapping["ATT-FIRST"]["tags"])
    assert "u01_questionbank_attempt" in tags
    assert "u01_first_mention_article_control" in tags
    assert "u01_a_an_sound_choice_error" in tags
    assert "grammar_target_article_noun_phrase_control" in tags
    assert mapping["ATT-FIRST"]["item_id"] == "ITEM-FIRST"


def test_known_reference_error_gets_definiteness_diagnosis(tmp_path: Path) -> None:
    mapping = u16d.attempt_diagnostic_identity_map(_database(tmp_path), learner_id="LEARNER")
    tags = set(mapping["ATT-REF"]["tags"])
    assert "u01_known_reference_control" in tags
    assert "u01_known_reference_definiteness_error" in tags


def test_m7_diagnostic_tags_and_strategy_are_enriched_without_replacing_generic_tag(
    tmp_path: Path,
) -> None:
    mapping = u16d.attempt_diagnostic_identity_map(_database(tmp_path), learner_id="LEARNER")
    token = u16d._ATTEMPT_DIAGNOSTIC_CONTEXT.set(mapping)
    try:
        tags = u16d.diagnostic_tags(
            {
                "attempt_id": "ATT-FIRST",
                "skill": "READING",
                "scoring_mode": "EXACT_OPTION",
            }
        )
    finally:
        u16d._ATTEMPT_DIAGNOSTIC_CONTEXT.reset(token)
    assert "response_mismatch" in tags
    assert "skill_reading" in tags
    assert "u01_a_an_sound_choice_error" in tags
    assert u16d.strategy(set(tags)) == "RETEACH_A_AN_SOUND_CHOICE_WITH_MINIMAL_PAIRS"


def test_nonquestionbank_diagnosis_and_strategy_remain_canonical() -> None:
    row = {
        "attempt_id": "OTHER",
        "skill": "READING",
        "scoring_mode": "EXACT_OPTION",
    }
    assert u16d.diagnostic_tags(row) == u16d._ORIGINAL_DIAGNOSTIC_TAGS(row)
    generic = {"skill_reading", "response_mismatch"}
    assert u16d.strategy(generic) == u16d._ORIGINAL_STRATEGY(generic)


def test_diagnosis_links_to_activity_capability_m7_queues_and_distinct_item(
    tmp_path: Path,
) -> None:
    database = _lineage_database(tmp_path)
    with sqlite3.connect(database) as connection:
        before_catalog = connection.execute(
            "SELECT item_id,private_item_json,item_digest FROM u01qb02_item_catalog ORDER BY item_id"
        ).fetchall()

    result = u16d.materialize_diagnosis_remediation_links(
        database,
        learner_id="LEARNER",
    )
    assert result["validation_status"] == u16d.PASS_STATUS
    assert result["diagnosis_link_count"] == 1
    assert result["different_item_candidate_ready_count"] == 1
    assert result["different_item_candidate_unresolved_count"] == 0
    assert result["questionbank_modified"] is False
    assert result["scoring_modified"] is False

    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        link = dict(connection.execute(f"SELECT * FROM {u16d.LINK_TABLE}").fetchone())
        after_catalog = [
            tuple(row)
            for row in connection.execute(
                "SELECT item_id,private_item_json,item_digest FROM u01qb02_item_catalog ORDER BY item_id"
            ).fetchall()
        ]

    assert before_catalog == after_catalog
    assert link["item_id"] == "ITEM-FAIL"
    assert link["activity_id"] == "ACTIVITY-1"
    assert link["task_angle"] == "ARTICLE_CONTROL"
    assert link["capability_class"] == u16b.FIRST_MENTION_SELECTION
    assert link["targeted_error_tag"] == "u01_a_an_sound_choice_error"
    assert link["targeted_remediation_strategy"] == "RETEACH_A_AN_SOUND_CHOICE_WITH_MINIMAL_PAIRS"
    assert json.loads(link["remediation_ids_json"]) == ["REMED-1"]
    assert json.loads(link["reassessment_ids_json"]) == ["REASSESS-1"]
    assert link["candidate_state"] == "READY"
    assert link["different_item_id"] == "ITEM-DISTINCT"
    assert link["different_asset_key"] == "ASSET-DISTINCT"
    assert link["different_item_id"] != link["item_id"]
    assert link["different_learner_visible_signature"] != link["failed_learner_visible_signature"]


def test_option_reordering_does_not_count_as_different_reassessment_item(
    tmp_path: Path,
) -> None:
    database = _lineage_database(tmp_path)
    with sqlite3.connect(database) as connection:
        connection.execute("DELETE FROM u01qb02_item_catalog WHERE item_id='ITEM-DISTINCT'")
        connection.commit()

    result = u16d.materialize_diagnosis_remediation_links(database, learner_id="LEARNER")
    assert result["different_item_candidate_ready_count"] == 0
    assert result["different_item_candidate_unresolved_count"] == 1
    candidate = u16d.reassessment_candidate(database, diagnosis_id="DIAG-1")
    assert candidate is not None
    assert candidate["candidate_state"] == "NO_DISTINCT_CANDIDATE"
    assert candidate["different_item_id"] is None

    left = {
        "item_id": "A",
        "skill": "READING",
        "private_item_json": _visible_item(stimulus="There is ___ apple in the bag."),
    }
    right = {
        "item_id": "B",
        "skill": "READING",
        "private_item_json": json.dumps(
            {
                "stimulus": "There is ___ apple in the bag.",
                "prompt": "Choose the best article.",
                "options": ["the", "an", "a"],
            }
        ),
    }
    assert u16.learner_visible_signature(left) == u16.learner_visible_signature(right)


def test_lineage_materialization_is_deterministic_and_does_not_rewrite_attempts(
    tmp_path: Path,
) -> None:
    database = _lineage_database(tmp_path)
    first = u16d.materialize_diagnosis_remediation_links(database, learner_id="LEARNER")
    with sqlite3.connect(database) as connection:
        attempts_before = connection.execute("SELECT * FROM response_attempts").fetchall()
        link_before = connection.execute(
            f"SELECT diagnosis_id,item_id,different_item_id,link_digest FROM {u16d.LINK_TABLE}"
        ).fetchall()
    second = u16d.materialize_diagnosis_remediation_links(database, learner_id="LEARNER")
    with sqlite3.connect(database) as connection:
        attempts_after = connection.execute("SELECT * FROM response_attempts").fetchall()
        link_after = connection.execute(
            f"SELECT diagnosis_id,item_id,different_item_id,link_digest FROM {u16d.LINK_TABLE}"
        ).fetchall()
    assert first == second
    assert attempts_before == attempts_after
    assert link_before == link_after
    assert first["next_short_step"] == "A1FS-V1-U01QB16E_Unit01DifferentItemReassessmentConsumerIntegration"
