from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ulga.builders import _a1fs_online_v1_s16_canonical_learning_core as core
from ulga.builders import build_a1fs_online_v1_s16_canonical_mastery_remediation_reassessment_review_integration as s16


def _units() -> dict[str, dict]:
    result: dict[str, dict] = {}
    for index in range(1, 25):
        grammar_id = f"GRAMMAR_UNIT_{index:02d}"
        result[grammar_id] = {
            "grammar_unit_id": grammar_id,
            "learning_unit_id": f"LEARNING_UNIT_{index:02d}",
            "sequence_index": index,
            "internal_stage": "A1" if index <= 18 else "A1+",
            "canonical_egp_row_ids": [f"EGP_{index:03d}"],
            "prerequisite_unit_ids": [] if index == 1 else [f"LEARNING_UNIT_{index - 1:02d}"],
        }
    return result


def _runtime_database(path: Path) -> dict[str, int]:
    sequence = {f"GRAMMAR_UNIT_{index:02d}": index for index in range(1, 25)}
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE lesson_catalog(
              lesson_id TEXT PRIMARY KEY,
              skill TEXT NOT NULL,
              level TEXT NOT NULL
            );
            CREATE TABLE lesson_assets(
              asset_key TEXT PRIMARY KEY,
              asset_id TEXT NOT NULL,
              lesson_id TEXT NOT NULL,
              role TEXT NOT NULL
            );
            """
        )
        for grammar_id, index in sequence.items():
            level = "A1" if index <= 18 else "A1+"
            for skill in ("READING", "WRITING"):
                lesson_id = f"A1FS_ONLINE_V1:{grammar_id}:{skill}"
                connection.execute(
                    "INSERT INTO lesson_catalog VALUES(?,?,?)",
                    (lesson_id, skill, level),
                )
                for asset_index in range(1, 5):
                    connection.execute(
                        "INSERT INTO lesson_assets VALUES(?,?,?,?)",
                        (
                            f"{lesson_id}:ASSET:{asset_index}",
                            f"ASSET_ID:{grammar_id}:{skill}:{asset_index}",
                            lesson_id,
                            "CHK" if asset_index == 4 else "PRD",
                        ),
                    )
        connection.commit()
    return sequence


def test_s16_runtime_graph_projects_existing_24_units_into_72_required_nodes(tmp_path: Path) -> None:
    database = tmp_path / "runtime.sqlite3"
    sequence = _runtime_database(database)
    units = _units()

    graph = core.build_runtime_mastery_graph(
        cp01_artifact={"task_id": "CP01", "coverage_summary": {"learning_unit_count": 24}},
        units=units,
        database=database,
        sequence=sequence,
    )

    assert graph["validation_status"] == core.m7.GRAPH_STATUS
    assert graph["counts"]["node_count"] == 73
    assert graph["counts"]["lesson_count"] == 48
    assert graph["counts"]["coverage_record_count"] == 24
    assert graph["counts"]["required_mastery_node_count"] == 72
    assert graph["counts"]["uncovered_required_node_count"] == 0
    assert len(graph["a2_lock_contract"]["required_mastery_node_ids"]) == 72
    assert graph["a2_lock_contract"]["runtime_unlock_implemented"] is False
    assert graph["projection_identity"]["new_curriculum_created"] is False
    assert graph["projection_identity"]["runtime_projection_only"] is True
    assert all(len(row["asset_body_ids"]) == 8 for row in graph["coverage"])
    prerequisite_edges = [row for row in graph["edges"] if row["edge_type"] == "PREREQUISITE_OF"]
    assert len(prerequisite_edges) == 23


def test_s16_latest_projection_reports_m7_m8_counts_without_exposing_ids(tmp_path: Path) -> None:
    database = tmp_path / "state.sqlite3"
    snapshot = {
        "required_mastery_node_count": 72,
        "mastered_required_count": 3,
        "remediation_assignments": [
            {"node_id": "N1", "assignment_state": "OPEN"},
            {"node_id": "N2", "assignment_state": "COMPLETED"},
        ],
        "reassessment_queue": [
            {"node_id": "N1", "queue_state": "PENDING"},
            {"node_id": "N2", "queue_state": "COMPLETED"},
        ],
    }
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE mastery_snapshots(
              snapshot_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              source_graph_sha256 TEXT NOT NULL,
              snapshot_json TEXT NOT NULL,
              snapshot_digest TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
            CREATE TABLE review_schedules(
              schedule_id TEXT PRIMARY KEY,
              learner_id TEXT NOT NULL,
              schedule_state TEXT NOT NULL
            );
            CREATE TABLE retention_states(
              learner_id TEXT NOT NULL,
              node_id TEXT NOT NULL,
              retention_state TEXT NOT NULL
            );
            """
        )
        connection.execute(
            "INSERT INTO mastery_snapshots VALUES(?,?,?,?,?,?)",
            ("S", "LEARNER", "g" * 64, json.dumps(snapshot), "d" * 64, "2026-01-01T00:00:00Z"),
        )
        connection.executemany(
            "INSERT INTO review_schedules VALUES(?,?,?)",
            (("R1", "LEARNER", "DUE"), ("R2", "LEARNER", "OVERDUE")),
        )
        connection.execute(
            "INSERT INTO retention_states VALUES(?,?,?)",
            ("LEARNER", "N1", "RETAINED"),
        )
        connection.commit()

    value = core._latest_learning_projection(database, "LEARNER")

    assert value == {
        "evaluation_state": "EVALUATED",
        "required_mastery_node_count": 72,
        "mastered_required_count": 3,
        "missing_mastery_count": 69,
        "open_remediation_count": 1,
        "pending_reassessment_count": 1,
        "due_review_count": 1,
        "overdue_review_count": 1,
        "retained_required_count": 1,
        "retention_confirmed": False,
        "a2_unlocked": False,
    }
    assert "node_id" not in value
    assert "attempt_id" not in value


def test_s16_static_surface_and_launcher_preserve_product_boundaries(tmp_path: Path) -> None:
    learner = tmp_path / "learner"
    secure = tmp_path / "secure"
    s16._write_static(learner)
    s16.s15.s11._write_secure_static(learner, secure)
    index = (secure / "index.html").read_text(encoding="utf-8")
    app = (secure / "app.js").read_text(encoding="utf-8")

    assert "精熟、補救與複習" in index
    assert "既有 M7" in index
    assert "沿用 M8" in index
    assert "renderCanonical" in app
    assert "open_remediation_count" in app
    assert "pending_reassessment_count" in app
    assert "A2 仍鎖定" in app
    assert "innerHTML" not in app

    outputs = s16._write_launch_bundle(
        target_root=tmp_path / "launch",
        receipt_path=tmp_path / "receipt.private.json",
        auth_state_db=tmp_path / "auth.sqlite3",
    )
    start = Path(outputs["start_script_path"]).read_text(encoding="utf-8")
    stop = Path(outputs["stop_script_path"]).read_text(encoding="utf-8")
    contract = s16.read_json(Path(outputs["launch_contract_path"]), "contract")
    assert "build_a1fs_online_v1_s16_canonical_mastery_remediation_reassessment_review_integration" in start
    assert "PID_OWNERSHIP_MISMATCH" in stop
    assert contract["canonical_m7_mastery_enabled"] is True
    assert contract["canonical_m8_review_scheduling_enabled"] is True
    assert contract["a2_session_enabled"] is False
    assert contract["audio_enabled"] is False
    assert contract["cloudflare_enabled"] is False
