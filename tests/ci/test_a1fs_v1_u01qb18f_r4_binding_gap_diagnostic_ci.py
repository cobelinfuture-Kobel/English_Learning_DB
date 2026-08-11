from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from product.a1fs_v1_2_1 import u01qb18f_r4_full_semantic_language_pedagogical_replay as r4
from ulga.builders import (
    build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration
    as u13,
)


def _db(path: Path) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE u01qb13_blueprint_activities(
              activity_id TEXT PRIMARY KEY,
              form_ordinal INTEGER NOT NULL,
              scene_ref_id TEXT NOT NULL,
              situation_family TEXT NOT NULL,
              setting TEXT NOT NULL,
              skill TEXT NOT NULL,
              task_angle TEXT NOT NULL,
              support_level TEXT NOT NULL,
              scored INTEGER NOT NULL,
              assessment_candidate INTEGER NOT NULL,
              pattern_family_ids_json TEXT NOT NULL,
              scene_anchors_json TEXT NOT NULL
            );
            CREATE TABLE u01qb02_item_catalog(
              item_id TEXT PRIMARY KEY,
              asset_key TEXT NOT NULL,
              skill TEXT NOT NULL,
              pattern_family_id TEXT NOT NULL,
              private_item_json TEXT NOT NULL,
              capture_enabled INTEGER NOT NULL
            );
            CREATE TABLE response_contracts(
              asset_key TEXT PRIMARY KEY,
              contract_json TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO u01qb13_blueprint_activities VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "U01-FORM-06-S04-A03",
                6,
                "U01-C5-PARK-BIRTHDAY",
                "OUTDOORS",
                "PARK",
                "WRITING",
                "CONTEXTUAL_REFERENCE_GAP",
                "REDUCED_SUPPORT",
                1,
                0,
                json.dumps([u13.PF09]),
                json.dumps(["park"]),
            ),
        )
        private_item = {
            "pattern_family_id": u13.PF09,
            "context_id": "U01-C5-PARK-BIRTHDAY",
            "lexical_slots": {
                "noun": "park",
                "context_id": "U01-C5-PARK-BIRTHDAY",
            },
            "stimulus": "There is a park in the park. The park is easy to see.",
            "prompt": "Write the missing reference.",
            "options": [],
        }
        connection.execute(
            "INSERT INTO u01qb02_item_catalog VALUES(?,?,?,?,?,?)",
            (
                "AUTO-PARK-TAUTOLOGY",
                "ASSET-PARK",
                "WRITING",
                u13.PF09,
                json.dumps(private_item),
                1,
            ),
        )
        connection.execute(
            "INSERT INTO response_contracts VALUES(?,?)",
            (
                "ASSET-PARK",
                json.dumps({"scoring_mode": "NORMALIZED_TEXT"}),
            ),
        )


def test_r4_binding_gap_diagnostic_distinguishes_learner_quality_from_scoring(
    tmp_path: Path,
) -> None:
    database = tmp_path / "runtime.sqlite3"
    _db(database)
    report = r4.binding_gap_diagnostic(database, "U01-FORM-06-S04-A03")

    assert report["activity_id"] == "U01-FORM-06-S04-A03"
    assert report["skill"] == "WRITING"
    assert report["task_angle"] == "CONTEXTUAL_REFERENCE_GAP"
    assert report["required_scoring_class"] == "AUTO"
    assert report["family_candidate_count"] == 1
    assert report["scoring_class_candidate_count"] == 1
    assert report["scene_anchor_context_candidate_count"] == 1
    assert report["learner_quality_candidate_count"] == 0
    assert report["formal_candidate_count"] == 0
    assert report["root_cause"] == "LEARNER_QUALITY_CAPACITY_ZERO"
    assert report["database_modified"] is False


def test_r4_extracts_activity_id_from_binding_gap_error() -> None:
    assert r4._binding_gap_activity_id(
        "SCENE_TASK_RUNTIME_BINDING_GAP:U01-FORM-06-S04-A03:SCORING_CLASS=AUTO"
    ) == "U01-FORM-06-S04-A03"
    assert r4._binding_gap_activity_id("OTHER_ERROR") == ""
