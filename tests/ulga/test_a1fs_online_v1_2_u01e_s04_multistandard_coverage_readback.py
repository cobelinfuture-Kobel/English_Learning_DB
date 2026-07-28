from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
from pathlib import Path

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s04_multistandard_coverage_readback as builder,
)
from ulga.validators import (
    validate_a1fs_online_v1_2_u01e_s04_multistandard_coverage_readback as validator,
)


def database(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE legacy_marker(id TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE response_contracts(
              asset_key TEXT PRIMARY KEY,
              lesson_id TEXT NOT NULL,
              skill TEXT NOT NULL,
              role TEXT NOT NULL,
              capture_enabled INTEGER NOT NULL,
              contract_json TEXT NOT NULL,
              contract_digest TEXT NOT NULL
            );
            CREATE TABLE response_attempts(
              attempt_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              session_id TEXT NOT NULL,
              lesson_id TEXT NOT NULL,
              asset_key TEXT NOT NULL,
              attempt_sequence INTEGER NOT NULL,
              response_json TEXT NOT NULL,
              submitted_at TEXT NOT NULL,
              previous_hash TEXT NOT NULL,
              attempt_hash TEXT NOT NULL
            );
            CREATE TABLE scoring_results(
              attempt_id TEXT PRIMARY KEY,
              scoring_mode TEXT NOT NULL,
              outcome TEXT NOT NULL,
              score REAL,
              human_review_required INTEGER NOT NULL,
              scored_at TEXT NOT NULL,
              contract_digest TEXT NOT NULL
            );
            CREATE TABLE state_events(
              event_seq INTEGER PRIMARY KEY AUTOINCREMENT,
              event_id TEXT NOT NULL UNIQUE,
              learner_id TEXT NOT NULL,
              session_id TEXT,
              event_type TEXT NOT NULL,
              event_at TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              previous_hash TEXT NOT NULL,
              event_hash TEXT NOT NULL UNIQUE
            );
            """
        )
        connection.execute("INSERT INTO legacy_marker VALUES('legacy','preserve')")
        contracts: list[tuple] = []
        reading = (
            ("U01-R-01", "PRD", {"scoring_mode": "EXACT_OPTION", "response_type": "string", "accepted_texts": ["a cat"], "accepted_sequence": []}),
            ("U01-R-02", "PRD", {"scoring_mode": "EXACT_OPTION", "response_type": "string", "accepted_texts": ["the book"], "accepted_sequence": []}),
            ("U01-R-03", "PRD", {"scoring_mode": "EXACT_OPTION", "response_type": "string", "accepted_texts": ["an apple"], "accepted_sequence": []}),
            ("U01-R-04", "CHK", {"scoring_mode": "EXACT_OPTION", "response_type": "string", "accepted_texts": ["a cat"], "accepted_sequence": []}),
        )
        for key, role, contract in reading:
            contracts.append(
                (
                    key,
                    builder.s03.s02.s01.m01.LESSON_IDS["READING"],
                    "READING",
                    role,
                    1,
                    json.dumps(contract),
                    f"digest:{key}",
                )
            )
        writing = (
            ("U01-W-01", "PRD", {"scoring_mode": "NORMALIZED_TEXT", "response_type": "string", "accepted_texts": ["a bag"], "accepted_sequence": []}),
            ("U01-W-02", "PRD", {"scoring_mode": "EXACT_SEQUENCE", "response_type": "sequence", "accepted_texts": [], "accepted_sequence": ["an", "apple"]}),
            ("U01-W-03", "PRD", {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "rubric": {"grammar_target_match": True}}),
            ("U01-W-04", "CHK", {"scoring_mode": "FEATURE_RUBRIC", "response_type": "string", "accepted_texts": [], "accepted_sequence": [], "rubric": {"complete_response": True}}),
        )
        for key, role, contract in writing:
            contracts.append(
                (
                    key,
                    builder.s03.s02.s01.m01.LESSON_IDS["WRITING"],
                    "WRITING",
                    role,
                    1,
                    json.dumps(contract),
                    f"digest:{key}",
                )
            )
        for index in range(1, 4):
            key = f"U01-S-{index:02d}"
            contract = {
                "scoring_mode": "FEATURE_RUBRIC",
                "response_type": "string",
                "accepted_texts": [],
                "accepted_sequence": [],
                "human_review_fallback": True,
                "rubric": {"practice_only": True},
            }
            contracts.append(
                (
                    key,
                    builder.s03.s02.s01.m01.LESSON_IDS["SPEAKING"],
                    "SPEAKING",
                    "PRD",
                    0,
                    json.dumps(contract),
                    f"digest:{key}",
                )
            )
        connection.executemany(
            "INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)", contracts
        )
        attempts = [
            (
                "ATTEMPT-001",
                "learner-1",
                "SESSION-1",
                builder.s03.s02.s01.m01.LESSON_IDS["READING"],
                "U01-R-01",
                1,
                '"PRIVATE RESPONSE ONE"',
                "2026-07-28T01:00:00Z",
                "0",
                "hash-1",
            ),
            (
                "ATTEMPT-002",
                "learner-1",
                "SESSION-2",
                builder.s03.s02.s01.m01.LESSON_IDS["READING"],
                "U01-R-01",
                2,
                '"PRIVATE RESPONSE TWO"',
                "2026-07-28T02:00:00Z",
                "hash-1",
                "hash-2",
            ),
            (
                "ATTEMPT-003",
                "learner-1",
                "SESSION-3",
                builder.s03.s02.s01.m01.LESSON_IDS["WRITING"],
                "U01-W-02",
                1,
                '["an","apple"]',
                "2026-07-28T03:00:00Z",
                "hash-2",
                "hash-3",
            ),
            (
                "ATTEMPT-OTHER",
                "learner-2",
                "SESSION-4",
                builder.s03.s02.s01.m01.LESSON_IDS["READING"],
                "U01-R-02",
                1,
                '"OTHER PRIVATE RESPONSE"',
                "2026-07-28T04:00:00Z",
                "0",
                "hash-4",
            ),
        ]
        connection.executemany(
            "INSERT INTO response_attempts VALUES(?,?,?,?,?,?,?,?,?,?)", attempts
        )
        results = [
            ("ATTEMPT-001", "EXACT_OPTION", "AUTO_FAIL", 0.0, 0, "2026-07-28T01:00:01Z", "digest:U01-R-01"),
            ("ATTEMPT-002", "EXACT_OPTION", "AUTO_PASS", 1.0, 0, "2026-07-28T02:00:01Z", "digest:U01-R-01"),
            ("ATTEMPT-003", "EXACT_SEQUENCE", "AUTO_PASS", 1.0, 0, "2026-07-28T03:00:01Z", "digest:U01-W-02"),
            ("ATTEMPT-OTHER", "EXACT_OPTION", "AUTO_PASS", 1.0, 0, "2026-07-28T04:00:01Z", "digest:U01-R-02"),
        ]
        connection.executemany(
            "INSERT INTO scoring_results VALUES(?,?,?,?,?,?,?)", results
        )
        events = [
            (
                "EVENT-1",
                "learner-1",
                "SESSION-1",
                "ASSET_EXPOSED",
                "2026-07-28T00:59:00Z",
                json.dumps({"asset_key": "U01-R-01", "lesson_id": builder.s03.s02.s01.m01.LESSON_IDS["READING"]}),
                "0",
                "event-hash-1",
            ),
            (
                "EVENT-2",
                "learner-1",
                "SESSION-3",
                "ASSET_EXPOSED",
                "2026-07-28T02:59:00Z",
                json.dumps({"asset_key": "U01-W-02", "lesson_id": builder.s03.s02.s01.m01.LESSON_IDS["WRITING"]}),
                "event-hash-1",
                "event-hash-2",
            ),
        ]
        connection.executemany(
            "INSERT INTO state_events(event_id,learner_id,session_id,event_type,event_at,payload_json,previous_hash,event_hash) VALUES(?,?,?,?,?,?,?,?)",
            events,
        )
        connection.commit()
    return path


def m1_graph(path: Path) -> Path:
    required_ids = [f"REQ:{index:03d}" for index in range(553)]
    skills = ("LISTENING", "SPEAKING", "READING", "WRITING")
    graph = {
        "task_id": "A1FS-V1-M1_A1A1PlusPrerequisiteGraphAndCoverage",
        "validation_status": "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE",
        "counts": {
            "required_mastery_node_count": 553,
            "a2_handoff_lesson_count": 165,
            "uncovered_required_node_count": 0,
        },
        "a2_lock_contract": {
            "required_mastery_node_ids": required_ids,
            "state": "LOCKED_BY_DESIGN",
            "runtime_unlock_implemented": False,
        },
        "nodes": [
            {
                "node_id": node_id,
                "skill": skills[index % len(skills)],
                "node_type": "CAPABILITY",
                "level": "A1" if index % 2 == 0 else "A1+",
            }
            for index, node_id in enumerate(required_ids)
        ],
    }
    path.write_text(json.dumps(graph), encoding="utf-8")
    return path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def built(tmp_path: Path) -> tuple[Path, Path, dict, dict]:
    db = database(tmp_path / "learner.sqlite3")
    graph = m1_graph(tmp_path / "m1.private.json")
    artifact, safe = builder.build_artifact(
        database_path=db,
        learner_id="learner-1",
        m1_graph_path=graph,
    )
    return db, graph, artifact, safe


def test_builds_exact_24_item_registry_and_keeps_new_items_pending_runtime(tmp_path: Path) -> None:
    _, _, artifact, _ = built(tmp_path)
    registry = artifact["target_registry"]
    assert len(registry) == 24
    assert len({row["item_key"] for row in registry}) == 24
    assert len({row["semantic_signature"] for row in registry}) == 24
    statuses = {status: sum(row["runtime_status"] == status for row in registry) for status in {row["runtime_status"] for row in registry}}
    assert statuses == {
        "RUNTIME_EXISTING": 11,
        "APPROVED_PENDING_RUNTIME_MATERIALIZATION": 13,
    }
    assert len({row["question_type"] for row in registry}) == 8
    assert all(row["cambridge_stage"] == "STARTERS" for row in registry)
    assert all(row["targets"]["target_ket_prerequisite_node_ids"] == [] for row in registry)


def test_coverage_counts_distinct_targets_not_repeat_attempts(tmp_path: Path) -> None:
    _, _, artifact, safe = built(tmp_path)
    readback = artifact["coverage_readback"]
    evidence = readback["learner_evidence_summary"]
    assert evidence["attempt_count"] == 3
    assert evidence["distinct_attempted_item_count"] == 2
    assert evidence["distinct_exposed_item_count"] == 2
    assert evidence["outcome_counts"] == {"AUTO_FAIL": 1, "AUTO_PASS": 2}
    evp = readback["coverage_by_domain"]["evp_senses"]
    assert evp["selected_count"] > evp["practised_count"] > 0
    assert evp["assessed_count"] == evp["practised_count"]
    assert evp["denominator_count"] == 784
    assert readback["coverage_by_domain"]["egp_rows"]["denominator_count"] == 109
    assert readback["coverage_by_domain"]["canonical_chunks"]["denominator_count"] == 76
    assert readback["coverage_by_domain"]["patterns"]["denominator_count"] == 27
    assert safe["coverage_readback"] == builder.safe_readback(readback)


def test_ket_cambridge_mastery_and_flyers_boundaries_fail_closed(tmp_path: Path) -> None:
    _, _, artifact, _ = built(tmp_path)
    readback = artifact["coverage_readback"]
    ket = readback["ket_prerequisite_readback"]
    assert ket["denominator_count"] == 553
    assert ket["selected_count"] == 0
    assert ket["practised_count"] == 0
    assert ket["coverage_claim_allowed"] is False
    cambridge = readback["cambridge_readback"]
    assert cambridge["stage"] == "STARTERS"
    assert cambridge["flyers_a2_handoff_excluded"] is True
    assert cambridge["granular_capability_status"] == "NOT_AVAILABLE_DO_NOT_DERIVE_CAPABILITY_PERCENTAGE_FROM_UNIT_STAGE_LABELS"
    assert readback["mastery_bridge_status"] == "NOT_AVAILABLE_NO_ITEM_TARGET_TO_M7_M8_NODE_BRIDGE"
    for domain, row in readback["coverage_by_domain"].items():
        if domain == "cambridge_capabilities":
            continue
        assert row["stable_count"] is None
        assert row["mastered_count"] is None
        assert row["transfer_proven_count"] is None


def test_additive_staging_preserves_source_and_all_legacy_table_shapes(tmp_path: Path) -> None:
    db = database(tmp_path / "learner.sqlite3")
    graph = m1_graph(tmp_path / "m1.private.json")
    before_sha = sha(db)
    with sqlite3.connect(db) as connection:
        before_schema = builder.legacy_schema(connection)
        before_contracts = connection.execute("SELECT COUNT(*) FROM response_contracts").fetchone()[0]
        before_attempts = connection.execute("SELECT COUNT(*) FROM response_attempts").fetchone()[0]
    artifact_path = tmp_path / "s04.private.json"
    report_path = tmp_path / "s04.safe.json"
    validation_path = tmp_path / "s04.validation.json"
    staged = tmp_path / "staged.sqlite3"
    artifact, safe, report = builder.materialize(
        database_path=db,
        learner_id="learner-1",
        m1_graph_path=graph,
        staged_database_path=staged,
        artifact_path=artifact_path,
        report_path=report_path,
        validation_path=validation_path,
    )
    assert report["error_count"] == 0, report
    assert sha(db) == before_sha
    with sqlite3.connect(db) as connection:
        assert builder.legacy_schema(connection) == before_schema
        assert connection.execute("SELECT COUNT(*) FROM response_contracts").fetchone()[0] == before_contracts
        assert connection.execute("SELECT COUNT(*) FROM response_attempts").fetchone()[0] == before_attempts
        assert not (builder.ADDITIVE_TABLES & builder.table_names(connection))
    with sqlite3.connect(staged) as connection:
        assert builder.legacy_schema(connection) == before_schema
        assert builder.ADDITIVE_TABLES.issubset(builder.table_names(connection))
        assert connection.execute("SELECT COUNT(*) FROM u01e_asset_target_bindings").fetchone()[0] == 24
        assert connection.execute("SELECT COUNT(*) FROM u01e_learner_coverage_snapshots").fetchone()[0] == 1
        assert connection.execute("SELECT value FROM legacy_marker WHERE id='legacy'").fetchone()[0] == "preserve"
    assert artifact["staging_readback"]["source_database_preserved"] is True
    assert artifact["staging_readback"]["legacy_schema_unchanged"] is True
    assert safe["staging_readback"]["v1_1_backward_compatible_schema"] is True


def test_safe_report_contains_no_private_identifiers_responses_or_database_digests(tmp_path: Path) -> None:
    db = database(tmp_path / "learner.sqlite3")
    graph = m1_graph(tmp_path / "m1.private.json")
    artifact, safe = builder.build_artifact(
        database_path=db,
        learner_id="learner-1",
        m1_graph_path=graph,
    )
    encoded = json.dumps(safe, ensure_ascii=False, sort_keys=True).casefold()
    for forbidden in (
        "learner-1",
        "attempt-001",
        "private response",
        '"learner_id"',
        '"item_key"',
        '"asset_key"',
        '"response_json"',
        '"accepted_texts"',
        '"correct_answer"',
        artifact["source_identity"]["learner_database_sha256"],
    ):
        assert forbidden.casefold() not in encoded


def test_validator_rejects_fabricated_ket_coverage(tmp_path: Path) -> None:
    db = database(tmp_path / "learner.sqlite3")
    graph = m1_graph(tmp_path / "m1.private.json")
    artifact, safe = builder.build_artifact(
        database_path=db,
        learner_id="learner-1",
        m1_graph_path=graph,
    )
    staged = builder.stage_additive_database(
        source_database_path=db,
        staged_database_path=tmp_path / "staged.sqlite3",
        artifact=artifact,
    )
    artifact = {**{key: value for key, value in artifact.items() if key != "artifact_sha256"}, "staging_readback": staged}
    artifact["coverage_readback"]["ket_prerequisite_readback"]["practised_count"] = 1
    artifact["artifact_sha256"] = builder.digest({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    safe_core = {key: value for key, value in safe.items() if key != "report_sha256"}
    safe_core["coverage_readback"] = builder.safe_readback(artifact["coverage_readback"])
    safe_core["staging_readback"] = {
        key: staged[key]
        for key in (
            "source_database_preserved",
            "legacy_schema_unchanged",
            "additive_tables",
            "additive_table_row_counts",
            "v1_1_backward_compatible_schema",
        )
    }
    safe = {**safe_core, "report_sha256": builder.digest(safe_core)}
    report = validator.validate_artifact(artifact, safe)
    assert report["error_count"] > 0
    assert "ket_practised_overclaim" in report["errors"]


def test_validator_passes_materialized_artifact(tmp_path: Path) -> None:
    db = database(tmp_path / "learner.sqlite3")
    graph = m1_graph(tmp_path / "m1.private.json")
    artifact, safe = builder.build_artifact(
        database_path=db,
        learner_id="learner-1",
        m1_graph_path=graph,
    )
    staging = builder.stage_additive_database(
        source_database_path=db,
        staged_database_path=tmp_path / "staged.sqlite3",
        artifact=artifact,
    )
    artifact = {**{key: value for key, value in artifact.items() if key != "artifact_sha256"}, "staging_readback": staging}
    artifact["artifact_sha256"] = builder.digest({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    safe_core = {key: value for key, value in safe.items() if key != "report_sha256"}
    safe_core["staging_readback"] = {
        key: staging[key]
        for key in (
            "source_database_preserved",
            "legacy_schema_unchanged",
            "additive_tables",
            "additive_table_row_counts",
            "v1_1_backward_compatible_schema",
        )
    }
    safe = {**safe_core, "report_sha256": builder.digest(safe_core)}
    report = validator.validate_artifact(artifact, safe)
    assert report["error_count"] == 0, report
    assert report["validation_status"] == builder.PASS_STATUS
