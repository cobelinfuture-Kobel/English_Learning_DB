from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

from ulga.builders import (
    build_a1fs_online_v1_2_u01e_s00_multistandard_denominator_and_lineage as builder,
)
from ulga.validators import (
    validate_a1fs_online_v1_2_u01e_s00_multistandard_denominator_and_lineage as validator,
)


def m1_graph(path: Path) -> Path:
    required = [f"REQ:{index:03d}" for index in range(553)]
    skills = ("LISTENING", "SPEAKING", "READING", "WRITING")
    nodes = [
        {
            "node_id": node_id,
            "node_type": "CAPABILITY",
            "skill": skills[index % len(skills)],
            "level": "A1" if index % 2 == 0 else "A1+",
            "mastery_required_before_a2": True,
        }
        for index, node_id in enumerate(required)
    ]
    payload = {
        "task_id": "A1FS-V1-M1_A1A1PlusPrerequisiteGraphAndCoverage",
        "validation_status": "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE",
        "nodes": nodes,
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
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def database(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
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
            """
        )
        rows = []
        for skill, count in builder.EXPECTED_UNIT01_SKILL_COUNTS.items():
            lesson_id = builder.m01.LESSON_IDS[skill]
            for index in range(1, count + 1):
                asset_key = f"U01:{skill}:{index}"
                mode = (
                    "FEATURE_RUBRIC"
                    if skill == "SPEAKING"
                    else "EXACT_SEQUENCE"
                    if skill == "WRITING" and index == 2
                    else "NORMALIZED_TEXT"
                )
                contract = {
                    "scoring_mode": mode,
                    "response_type": "sequence" if mode == "EXACT_SEQUENCE" else "string",
                    "accepted_texts": ["private answer"],
                    "accepted_sequence": ["private", "answer"],
                }
                rows.append(
                    (
                        asset_key,
                        lesson_id,
                        skill,
                        "PRD",
                        0 if skill == "SPEAKING" else 1,
                        json.dumps(contract),
                        f"digest-{skill}-{index}",
                    )
                )
        connection.executemany("INSERT INTO response_contracts VALUES(?,?,?,?,?,?,?)", rows)
        attempts = [
            (
                "ATTEMPT-1",
                "LEARNER-PRIVATE",
                "SESSION-1",
                builder.m01.LESSON_IDS["READING"],
                "U01:READING:1",
                1,
                '"private response"',
                "2026-07-28T01:00:00Z",
                "0",
                "hash-1",
            ),
            (
                "ATTEMPT-2",
                "LEARNER-PRIVATE",
                "SESSION-2",
                builder.m01.LESSON_IDS["WRITING"],
                "U01:WRITING:1",
                1,
                '"private response"',
                "2026-07-28T02:00:00Z",
                "0",
                "hash-2",
            ),
        ]
        connection.executemany("INSERT INTO response_attempts VALUES(?,?,?,?,?,?,?,?,?,?)", attempts)
        connection.executemany(
            "INSERT INTO scoring_results VALUES(?,?,?,?,?,?,?)",
            [
                (
                    "ATTEMPT-1",
                    "NORMALIZED_TEXT",
                    "AUTO_PASS",
                    1.0,
                    0,
                    "2026-07-28T01:00:01Z",
                    "digest-READING-1",
                ),
                (
                    "ATTEMPT-2",
                    "NORMALIZED_TEXT",
                    "AUTO_FAIL",
                    0.0,
                    0,
                    "2026-07-28T02:00:01Z",
                    "digest-WRITING-1",
                ),
            ],
        )
        connection.commit()
    return path


def built(tmp_path: Path) -> tuple[dict, dict]:
    return builder.build_artifact(
        m1_graph_path=m1_graph(tmp_path / "m1.private.json"),
        database_path=database(tmp_path / "learner.sqlite3"),
    )


def test_rebuilds_all_current_denominators_and_explicit_cambridge_gap(tmp_path: Path) -> None:
    artifact, safe = built(tmp_path)
    report = validator.validate_artifact(artifact, safe)
    assert report["error_count"] == 0, report
    authority = artifact["denominators"]["authority"]
    assert authority["evp_a1_sense_count"] == 784
    assert authority["egp_a1_row_count"] == 109
    assert authority["a1_generator_safe_chunk_count"] == 76
    assert authority["a1_generator_safe_pattern_count"] == 27
    assert authority["evp_a1_unique_lemma_count"] > 0
    ket = artifact["denominators"]["ket_prerequisite"]
    assert ket["required_a1_a1plus_mastery_node_count"] == 553
    assert ket["a2_handoff_lesson_count"] == 165
    cambridge = artifact["denominators"]["cambridge"]
    assert cambridge["unit_alignment_count"] == 24
    assert cambridge["required_current_path_unit_alignment_count"] == 23
    assert cambridge["flyers_handoff_only_unit_alignment_count"] == 1
    assert cambridge["unit01_cambridge_stage"] == "STARTERS"
    assert cambridge["assessment_pattern_count"] == 8
    assert (
        cambridge["granular_capability_denominator_status"]
        == "NOT_MATERIALIZED_IN_COMMITTED_POLICY"
    )


def test_reconciles_eleven_existing_assets_without_guessing_targets(tmp_path: Path) -> None:
    artifact, _ = built(tmp_path)
    runtime = artifact["unit01_current_runtime_lineage"]
    assert runtime["response_contract_count"] == 11
    assert runtime["response_contract_count_by_skill"] == {
        "READING": 4,
        "WRITING": 4,
        "SPEAKING": 3,
    }
    assert runtime["attempt_count"] == 2
    assert runtime["distinct_attempted_asset_count"] == 2
    assert runtime["outcome_counts"] == {"AUTO_FAIL": 1, "AUTO_PASS": 1}
    assert runtime["asset_target_binding_gap_count"] == 11
    assert all(
        row["asset_target_binding_status"] == "UNIT_LEVEL_ONLY_ASSET_TARGET_UNRESOLVED"
        for row in runtime["assets"]
    )
    assert all(row["target_evp_sense_ids"] == [] for row in runtime["assets"])
    assert all(row["target_egp_row_ids"] == [] for row in runtime["assets"])


def test_private_responses_and_answers_never_enter_artifact_or_safe_report(tmp_path: Path) -> None:
    artifact, safe = built(tmp_path)
    encoded = json.dumps(artifact, ensure_ascii=False).casefold()
    assert "private response" not in encoded
    assert "private answer" not in encoded
    assert "learner-private" not in encoded
    safe_encoded = json.dumps(safe, ensure_ascii=False).casefold()
    assert "asset_key" not in safe_encoded
    assert "attempt_id" not in safe_encoded
    assert "learner-private" not in safe_encoded


def test_validator_rejects_false_asset_target_resolution(tmp_path: Path) -> None:
    artifact, safe = built(tmp_path)
    tampered = copy.deepcopy(artifact)
    row = tampered["unit01_current_runtime_lineage"]["assets"][0]
    row["asset_target_binding_status"] = "RESOLVED_AUTHORITY_TARGET_BINDING"
    row["target_evp_sense_ids"] = ["invented"]
    core = {key: value for key, value in tampered.items() if key != "artifact_sha256"}
    tampered["artifact_sha256"] = builder.digest(core)
    report = validator.validate_artifact(tampered, safe)
    assert report["error_count"] > 0
    assert any("asset_binding_guessed" in error for error in report["errors"])


def test_ket_denominator_drift_fails_closed(tmp_path: Path) -> None:
    graph_path = m1_graph(tmp_path / "m1.private.json")
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["counts"]["required_mastery_node_count"] = 552
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    try:
        builder.build_artifact(
            m1_graph_path=graph_path,
            database_path=database(tmp_path / "learner.sqlite3"),
        )
    except builder.S00ReconciliationError as exc:
        assert "m1_required_mastery_count_mismatch" in str(exc)
    else:
        raise AssertionError("KET denominator drift did not fail closed")
