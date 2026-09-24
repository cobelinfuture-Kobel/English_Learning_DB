from __future__ import annotations

import json
import sqlite3
from copy import deepcopy
from pathlib import Path

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s04_coverage_runtime_readback as builder,
)
from ulga.validators import (
    validate_a1fs_online_v1_2_u01e_s04_coverage_runtime_readback as validator,
)


def write_json(path: Path, value) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def m1_graph(path: Path) -> Path:
    required = [f"REQ:{index:03d}" for index in range(553)]
    skills = ("LISTENING", "SPEAKING", "READING", "WRITING")
    return write_json(
        path,
        {
            "task_id": "A1FS-V1-M1_A1A1PlusPrerequisiteGraphAndCoverage",
            "validation_status": "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE",
            "nodes": [
                {
                    "node_id": node_id,
                    "node_type": "CAPABILITY",
                    "skill": skills[index % 4],
                    "level": "A1" if index % 2 == 0 else "A1+",
                    "mastery_required_before_a2": True,
                }
                for index, node_id in enumerate(required)
            ],
            "counts": {
                "required_mastery_node_count": 553,
                "a2_handoff_lesson_count": 165,
                "uncovered_required_node_count": 0,
            },
            "a2_lock_contract": {
                "state": "LOCKED_BY_DESIGN",
                "required_mastery_node_ids": required,
                "runtime_unlock_implemented": False,
            },
        },
    )


def source_bundles(path: Path) -> Path:
    bundles: dict[str, dict] = {}
    unit_lessons = builder.s03.s02.s01.m01.LESSON_IDS
    for skill, count in (("READING", 4), ("WRITING", 4), ("SPEAKING", 3)):
        lesson_id = unit_lessons[skill]
        bundles[lesson_id] = {
            "lesson": {"lesson_id": lesson_id, "skill": skill, "level": "A1"},
            "assets": [
                {
                    "asset_key": f"U01-{skill[0]}-{index:02d}",
                    "role": "CHK" if index == count and skill != "SPEAKING" else "PRD",
                    "learner_payload": {
                        "prompt": f"legacy {skill} {index}",
                        "response_capture_enabled": skill != "SPEAKING",
                    },
                }
                for index in range(1, count + 1)
            ],
        }
    for index in range(69):
        lesson_id = f"DUMMY:{index:02d}"
        count = 3 if index < 23 else 4
        bundles[lesson_id] = {
            "lesson": {"lesson_id": lesson_id, "skill": "READING", "level": "A1"},
            "assets": [
                {
                    "asset_key": f"DUMMY:{index:02d}:{asset:02d}",
                    "role": "PRD",
                    "learner_payload": {
                        "prompt": "legacy",
                        "response_capture_enabled": True,
                    },
                }
                for asset in range(1, count + 1)
            ],
        }
    assert len(bundles) == 72
    assert sum(len(row["assets"]) for row in bundles.values()) == 264
    return write_json(path, bundles)


def contract_for(skill: str, index: int, role: str) -> dict:
    if skill == "READING":
        answers = ["a cat", "the book", "an apple", "a cat"]
        return {
            "scoring_mode": "EXACT_OPTION",
            "response_type": "string",
            "accepted_texts": [answers[index - 1]],
            "accepted_sequence": [],
            "human_review_fallback": False,
        }
    if skill == "WRITING":
        if index == 1:
            return {
                "scoring_mode": "NORMALIZED_TEXT",
                "response_type": "string",
                "accepted_texts": ["a bag"],
                "accepted_sequence": [],
                "human_review_fallback": False,
            }
        if index == 2:
            return {
                "scoring_mode": "EXACT_SEQUENCE",
                "response_type": "sequence",
                "accepted_texts": [],
                "accepted_sequence": ["an", "apple"],
                "human_review_fallback": False,
            }
        return {
            "scoring_mode": "FEATURE_RUBRIC",
            "response_type": "string",
            "accepted_texts": [],
            "accepted_sequence": [],
            "human_review_fallback": True,
            "rubric": {"complete_response": True, "grammar_target_match": True},
        }
    return {
        "scoring_mode": "FEATURE_RUBRIC",
        "response_type": "string",
        "accepted_texts": [],
        "accepted_sequence": [],
        "human_review_fallback": True,
        "rubric": {"practice_only": True},
    }


def database(path: Path, bundles_path: Path) -> Path:
    bundles = json.loads(bundles_path.read_text(encoding="utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys=ON;
            CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE lesson_catalog(
              lesson_id TEXT PRIMARY KEY,sequence_index INTEGER NOT NULL,grammar_unit_id TEXT NOT NULL,
              skill TEXT NOT NULL,level TEXT NOT NULL,title TEXT NOT NULL,bundle_digest TEXT NOT NULL
            );
            CREATE TABLE lesson_assets(
              asset_key TEXT PRIMARY KEY,asset_id TEXT NOT NULL,lesson_id TEXT NOT NULL,role TEXT NOT NULL,
              content_digest TEXT NOT NULL,FOREIGN KEY(lesson_id) REFERENCES lesson_catalog(lesson_id)
            );
            CREATE TABLE learner_profiles(
              learner_id TEXT PRIMARY KEY,display_label TEXT NOT NULL,level_scope TEXT NOT NULL,
              profile_state TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,profile_version INTEGER NOT NULL
            );
            CREATE TABLE learning_sessions(
              session_id TEXT PRIMARY KEY,learner_id TEXT NOT NULL,lesson_id TEXT NOT NULL,skill TEXT NOT NULL,
              session_state TEXT NOT NULL,started_at TEXT NOT NULL,updated_at TEXT NOT NULL,completed_at TEXT,
              abandoned_at TEXT,current_asset_index INTEGER NOT NULL,session_version INTEGER NOT NULL
            );
            CREATE TABLE lesson_progress(
              learner_id TEXT NOT NULL,lesson_id TEXT NOT NULL,lesson_state TEXT NOT NULL,exposure_count INTEGER NOT NULL,
              attempt_count INTEGER NOT NULL,completion_count INTEGER NOT NULL,last_event_at TEXT NOT NULL,
              last_session_id TEXT,progress_version INTEGER NOT NULL,PRIMARY KEY(learner_id,lesson_id)
            );
            CREATE TABLE state_events(
              event_id INTEGER PRIMARY KEY AUTOINCREMENT,learner_id TEXT NOT NULL,session_id TEXT,lesson_id TEXT,
              event_type TEXT NOT NULL,payload_json TEXT NOT NULL,occurred_at TEXT NOT NULL,event_hash TEXT NOT NULL
            );
            CREATE TABLE response_contracts(
              asset_key TEXT PRIMARY KEY,lesson_id TEXT NOT NULL,skill TEXT NOT NULL,role TEXT NOT NULL,
              capture_enabled INTEGER NOT NULL,contract_json TEXT NOT NULL,contract_digest TEXT NOT NULL
            );
            CREATE TABLE response_attempts(
              attempt_id TEXT PRIMARY KEY,learner_id TEXT NOT NULL,session_id TEXT NOT NULL,lesson_id TEXT NOT NULL,
              asset_key TEXT NOT NULL,attempt_sequence INTEGER NOT NULL,response_json TEXT NOT NULL,
              submitted_at TEXT NOT NULL,previous_hash TEXT NOT NULL,attempt_hash TEXT NOT NULL
            );
            CREATE TABLE scoring_results(
              attempt_id TEXT PRIMARY KEY,scoring_mode TEXT NOT NULL,outcome TEXT NOT NULL,score REAL,
              human_review_required INTEGER NOT NULL,scored_at TEXT NOT NULL,contract_digest TEXT NOT NULL
            );
            CREATE TABLE human_review_queue(attempt_id TEXT PRIMARY KEY,status TEXT NOT NULL);
            CREATE TABLE mastery_state(learner_id TEXT NOT NULL,requirement_node_id TEXT NOT NULL,state TEXT NOT NULL,PRIMARY KEY(learner_id,requirement_node_id));
            CREATE TABLE error_diagnoses(diagnosis_id TEXT PRIMARY KEY,learner_id TEXT NOT NULL);
            CREATE TABLE remediation_assignments(assignment_id TEXT PRIMARY KEY,learner_id TEXT NOT NULL);
            CREATE TABLE reassessment_records(record_id TEXT PRIMARY KEY,learner_id TEXT NOT NULL);
            CREATE TABLE review_schedule(schedule_id TEXT PRIMARY KEY,learner_id TEXT NOT NULL);
            CREATE TABLE retention_state(learner_id TEXT NOT NULL,requirement_node_id TEXT NOT NULL,state TEXT NOT NULL,PRIMARY KEY(learner_id,requirement_node_id));
            """
        )
        connection.execute("INSERT INTO metadata VALUES('schema','v1.1')")
        connection.execute(
            "INSERT INTO learner_profiles VALUES(?,?,?,?,?,?,?)",
            ("JAMES", "James", "A1+A1+", "ACTIVE", "2026-07-01T00:00:00Z", "2026-07-01T00:00:00Z", 1),
        )
        sequence = 0
        for lesson_id in sorted(bundles):
            sequence += 1
            bundle = bundles[lesson_id]
            lesson = bundle["lesson"]
            connection.execute(
                "INSERT INTO lesson_catalog VALUES(?,?,?,?,?,?,?)",
                (lesson_id, sequence, builder.UNIT_ID if lesson_id in builder.s03.s02.s01.m01.LESSON_IDS.values() else f"DUMMY-{sequence}", lesson["skill"], lesson["level"], lesson_id, f"bundle:{sequence}"),
            )
            for index, asset in enumerate(bundle["assets"], start=1):
                connection.execute(
                    "INSERT INTO lesson_assets VALUES(?,?,?,?,?)",
                    (asset["asset_key"], f"asset:{asset['asset_key']}", lesson_id, asset["role"], f"content:{asset['asset_key']}"),
                )
                skill = lesson["skill"]
                role = asset["role"]
                contract = contract_for(skill, index, role) if lesson_id in builder.s03.s02.s01.m01.LESSON_IDS.values() else {
                    "scoring_mode": "NORMALIZED_TEXT", "response_type": "string", "accepted_texts": ["dummy"], "accepted_sequence": [], "human_review_fallback": False
                }
                connection.execute(
                    "INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)",
                    (asset["asset_key"], lesson_id, skill, role, 0 if skill == "SPEAKING" else 1, json.dumps(contract), f"contract:{asset['asset_key']}"),
                )
        connection.execute(
            "INSERT INTO state_events(learner_id,session_id,lesson_id,event_type,payload_json,occurred_at,event_hash) VALUES(?,?,?,?,?,?,?)",
            ("JAMES", "SESSION-1", builder.s03.s02.s01.m01.LESSON_IDS["READING"], "ASSET_EXPOSED", json.dumps({"asset_key": "U01-R-01"}), "2026-07-28T01:00:00Z", "event-1"),
        )
        for attempt_id, outcome, submitted in (
            ("ATTEMPT-1", "AUTO_PASS", "2026-07-28T01:01:00Z"),
            ("ATTEMPT-2", "AUTO_FAIL", "2026-07-28T01:02:00Z"),
        ):
            connection.execute(
                "INSERT INTO response_attempts VALUES(?,?,?,?,?,?,?,?,?,?)",
                (attempt_id, "JAMES", "SESSION-1", builder.s03.s02.s01.m01.LESSON_IDS["READING"], "U01-R-01", 1, '"PRIVATE RESPONSE"', submitted, "0", f"hash:{attempt_id}"),
            )
            connection.execute(
                "INSERT INTO scoring_results VALUES(?,?,?,?,?,?,?)",
                (attempt_id, "EXACT_OPTION", outcome, 1.0 if outcome == "AUTO_PASS" else 0.0, 0, submitted, "contract:U01-R-01"),
            )
        connection.commit()
    return path


def static_root(path: Path) -> Path:
    path.mkdir(parents=True)
    (path / "index.html").write_text("<html><body><main><section>existing</section></main></body></html>", encoding="utf-8")
    (path / "app.js").write_text("'use strict';async function api(path){return {}};", encoding="utf-8")
    (path / "styles.css").write_text("body{}", encoding="utf-8")
    return path


def fixture(tmp_path: Path) -> dict[str, Path]:
    bundles = source_bundles(tmp_path / "bundles.json")
    return {
        "bundles": bundles,
        "database": database(tmp_path / "learner.sqlite3", bundles),
        "m1": m1_graph(tmp_path / "m1.private.json"),
        "static": static_root(tmp_path / "static"),
    }


def materialized(tmp_path: Path):
    paths = fixture(tmp_path)
    receipt, safe = builder.materialize(
        source_database=paths["database"],
        source_bundles_path=paths["bundles"],
        m1_graph_path=paths["m1"],
        source_static_root=paths["static"],
        output_root=tmp_path / "out",
        learner_id="JAMES",
    )
    return paths, receipt, safe


def test_overlay_preserves_72_lessons_and_expands_only_unit01_to_24_activities(tmp_path: Path) -> None:
    paths = fixture(tmp_path)
    source = json.loads(paths["bundles"].read_text(encoding="utf-8"))
    approved, _ = builder.approved_item_bank(paths["database"])
    target, added = builder.overlay_bundles(source, approved)
    assert len(target) == 72
    assert sum(len(row["assets"]) for row in target.values()) == 277
    assert len(added) == 13
    for skill, expected in builder.EXPECTED_UNIT01_COUNTS.items():
        assert len(target[builder.lesson_id_for_skill(skill)]["assets"]) == expected
    for lesson_id in set(source) - set(builder.s03.s02.s01.m01.LESSON_IDS.values()):
        assert target[lesson_id] == source[lesson_id]
    new_assets = [asset for row in added for asset in [builder.learner_asset(row["item"], approved["artifact_sha256"])]]
    assert all(asset["asset_key"].startswith("A1FS_V1_2:U01E-S03-") for asset in new_assets)
    assert all(asset["learner_payload"]["content_identity"]["approved_item_bank_sha256"] == approved["artifact_sha256"] for asset in new_assets)
    assert all(asset["learner_payload"]["response_capture_enabled"] is False for asset in new_assets if ":S01" in asset["asset_key"])


def test_migration_is_additive_and_preserves_existing_rows_and_table_shapes(tmp_path: Path) -> None:
    paths, receipt, _ = materialized(tmp_path)
    target_db = Path(receipt["runtime_outputs"]["database_path"])
    assert paths["database"].read_bytes() != target_db.read_bytes()
    with sqlite3.connect(paths["database"]) as source, sqlite3.connect(target_db) as target:
        for table in ("learner_profiles", "learning_sessions", "lesson_progress", "state_events", "response_attempts", "scoring_results", "human_review_queue", "mastery_state", "error_diagnoses", "remediation_assignments", "reassessment_records", "review_schedule", "retention_state"):
            assert builder.table_columns(source, table) == builder.table_columns(target, table)
            assert builder.table_rows(source, table) == builder.table_rows(target, table)
        source_assets = builder.table_rows(source, "lesson_assets")
        target_assets = builder.table_rows(target, "lesson_assets")
        source_contracts = builder.table_rows(source, "response_contracts")
        target_contracts = builder.table_rows(target, "response_contracts")
        assert all(row in target_assets for row in source_assets)
        assert all(row in target_contracts for row in source_contracts)
        assert len(source_assets) == 264 and len(target_assets) == 277
        assert len(source_contracts) == 264 and len(target_contracts) == 277
        assert target.execute(f"SELECT COUNT(*) FROM {builder.TARGET_TABLE}").fetchone()[0] == 24
        assert target.execute("SELECT COUNT(*) FROM response_contracts WHERE skill='SPEAKING' AND capture_enabled=1").fetchone()[0] == 0
    assert receipt["migration_summary"]["protected_state_preserved"] is True
    assert receipt["compatibility"]["additive_tables_only"] is True
    assert receipt["compatibility"]["existing_table_shape_changed"] is False


def test_coverage_counts_distinct_targets_and_not_duplicate_attempts(tmp_path: Path) -> None:
    _, receipt, _ = materialized(tmp_path)
    target_db = Path(receipt["runtime_outputs"]["database_path"])
    coverage = builder.coverage_readback(target_db, "JAMES")
    activity = coverage["activity_summary"]
    assert activity["selected_activity_count"] == 24
    assert activity["exposed_activity_count"] == 1
    assert activity["distinct_practised_activity_count"] == 1
    assert activity["attempt_count"] == 2
    assert activity["assessed_activity_count"] == 1
    evp = coverage["coverage_dimensions"]["EVP_SENSE"]
    assert evp["selected_count"] > evp["practised_count"] > 0
    assert evp["denominator"] == 784
    assert coverage["coverage_dimensions"]["EGP_ROW"]["denominator"] == 109
    assert coverage["coverage_dimensions"]["CANONICAL_CHUNK"]["denominator"] == 76
    assert coverage["coverage_dimensions"]["PATTERN"]["denominator"] == 27
    assert coverage["coverage_dimensions"]["KET_PREREQUISITE"]["denominator"] == 553
    assert coverage["coverage_dimensions"]["KET_PREREQUISITE"]["practised_count"] == 0
    assert coverage["ket_readback"]["coverage_claim_allowed"] is False
    assert coverage["semantic_boundaries"]["duplicate_attempts_duplicate_distinct_coverage"] is False
    assert coverage["coverage_dimensions"]["EVP_SENSE"]["mastered_count"] is None


def test_new_valid_attempt_increases_coverage_but_repeat_does_not_duplicate_distinct_counts(tmp_path: Path) -> None:
    _, receipt, _ = materialized(tmp_path)
    db = Path(receipt["runtime_outputs"]["database_path"])
    before = builder.coverage_readback(db, "JAMES")
    new_asset = "A1FS_V1_2:U01E-S03-C03-W01"
    lesson_id = builder.lesson_id_for_skill("WRITING")
    with sqlite3.connect(db) as connection:
        connection.execute(
            "INSERT INTO state_events(learner_id,session_id,lesson_id,event_type,payload_json,occurred_at,event_hash) VALUES(?,?,?,?,?,?,?)",
            ("JAMES", "SESSION-NEW", lesson_id, "ASSET_EXPOSED", json.dumps({"asset_key": new_asset}), "2026-07-28T04:00:00Z", "new-event"),
        )
        for index in (1, 2):
            attempt_id = f"NEW-ATTEMPT-{index}"
            connection.execute(
                "INSERT INTO response_attempts VALUES(?,?,?,?,?,?,?,?,?,?)",
                (attempt_id, "JAMES", "SESSION-NEW", lesson_id, new_asset, index, '"an egg"', f"2026-07-28T04:0{index}:00Z", "0", f"new-hash-{index}"),
            )
            connection.execute(
                "INSERT INTO scoring_results VALUES(?,?,?,?,?,?,?)",
                (attempt_id, "EXACT_SEQUENCE", "AUTO_PASS", 1.0, 0, f"2026-07-28T04:0{index}:01Z", "new-contract"),
            )
        connection.commit()
    after = builder.coverage_readback(db, "JAMES")
    assert after["activity_summary"]["distinct_practised_activity_count"] == before["activity_summary"]["distinct_practised_activity_count"] + 1
    assert after["activity_summary"]["attempt_count"] == before["activity_summary"]["attempt_count"] + 2
    assert after["activity_summary"]["exposed_activity_count"] == before["activity_summary"]["exposed_activity_count"] + 1
    assert after["coverage_dimensions"]["EVP_SENSE"]["practised_count"] >= before["coverage_dimensions"]["EVP_SENSE"]["practised_count"]
    assert after["coverage_dimensions"]["KET_PREREQUISITE"]["practised_count"] == 0


def test_context_phrases_are_never_counted_as_canonical_chunk_coverage(tmp_path: Path) -> None:
    _, receipt, _ = materialized(tmp_path)
    coverage = receipt["coverage_readback"]
    chunks = coverage["coverage_dimensions"]["CANONICAL_CHUNK"]
    phrases = coverage["coverage_dimensions"]["CONTEXT_PHRASE"]
    assert chunks["denominator"] == 76
    assert phrases["denominator_status"] == "UNIT_LOCAL_ONLY"
    assert set(chunks["selected_ids"]).isdisjoint(phrases["selected_ids"])
    assert coverage["semantic_boundaries"]["context_phrases_counted_as_canonical_chunks"] is False


def test_static_projection_adds_coverage_panel_without_item_or_answer_leak(tmp_path: Path) -> None:
    _, receipt, _ = materialized(tmp_path)
    static = Path(receipt["runtime_outputs"]["secure_static_root"])
    index = (static / "index.html").read_text(encoding="utf-8")
    app = (static / "app.js").read_text(encoding="utf-8")
    assert "u01e-coverage-panel" in index
    assert "/api/coverage" in app
    assert "loadU01eCoverage" in app
    assert "candidate_items" not in app
    assert "accepted_texts" not in app
    assert "accepted_sequence" not in app
    assert "runtime generation" not in app.casefold()


def test_receipt_and_safe_report_pass_independent_validation(tmp_path: Path) -> None:
    _, receipt, safe = materialized(tmp_path)
    report = validator.validate_outputs(receipt, safe)
    assert report["error_count"] == 0, report
    encoded = json.dumps(safe, ensure_ascii=False).casefold()
    assert "private response" not in encoded
    assert "accepted_texts" not in encoded
    assert "accepted_sequence" not in encoded
    assert safe["boundaries"]["production_database_mutated"] is False
    assert safe["boundaries"]["runtime_free_generation_enabled"] is False
