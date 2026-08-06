from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from product import a1fs_v1_2_1 as product_package
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
