from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7


def _graph() -> dict:
    required = [f"NODE:{index:02d}" for index in range(72)]
    return {
        "validation_status": m7.GRAPH_STATUS,
        "projection_identity": {
            "task_id": m7.S16_PROJECTION_TASK_ID,
            "source_unit_count": 24,
            "source_s15_scored_lesson_count": 48,
            "new_curriculum_created": False,
            "runtime_projection_only": True,
        },
        "nodes": [],
        "coverage": [],
        "counts": {
            "lesson_count": 48,
            "required_mastery_node_count": 72,
        },
        "a2_lock_contract": {
            "state": "LOCKED_BY_DESIGN",
            "required_mastery_node_ids": required,
            "runtime_unlock_implemented": False,
        },
        "claim_boundaries": {
            "asset_body_content_modified": False,
            "mastery_claimed": False,
            "a2_unlocked": False,
            "listening_audio_complete": False,
        },
    }


def _database(path: Path, planner_hash: str) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE planner_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            """
        )
        connection.execute(
            "INSERT INTO metadata VALUES('m6_validation_status',?)",
            (m7.M6_STATUS,),
        )
        connection.execute(
            "INSERT INTO planner_metadata VALUES('graph_sha256',?)",
            (planner_hash,),
        )
        connection.commit()


def test_exact_s16_projection_is_audited_without_rewriting_planner_metadata(tmp_path: Path) -> None:
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(_graph()), encoding="utf-8")
    database = tmp_path / "state.sqlite3"
    planner_hash = "a" * 64
    _database(database, planner_hash)

    result = m7.MasteryRemediationEngine(
        database_path=database,
        graph_path=graph_path,
    ).initialize()

    assert result["runtime_projection_binding_used"] is True
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT value FROM planner_metadata WHERE key='graph_sha256'"
        ).fetchone()[0] == planner_hash
        row = connection.execute(
            """SELECT authority_task_id,source_planner_graph_sha256,runtime_graph_sha256,
                      source_unit_count,source_scored_lesson_count,required_mastery_node_count,binding_status
               FROM m7_runtime_graph_projection_bindings"""
        ).fetchone()
        metadata = dict(connection.execute("SELECT key,value FROM m7_metadata"))
    assert row == (
        m7.S16_PROJECTION_TASK_ID,
        planner_hash,
        m7.digest(graph_path.read_bytes()),
        24,
        48,
        72,
        m7.S16_PROJECTION_BINDING_STATUS,
    )
    assert metadata["runtime_projection_binding_used"] == "true"


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (lambda graph: graph["projection_identity"].update(source_unit_count=23), "planner_graph_binding_mismatch"),
        (lambda graph: graph["projection_identity"].update(task_id="OTHER"), "planner_graph_binding_mismatch"),
        (lambda graph: graph["counts"].update(required_mastery_node_count=71), "required_mastery_denominator_invalid"),
        (lambda graph: graph["a2_lock_contract"].update(runtime_unlock_implemented=True), "planner_graph_binding_mismatch"),
        (lambda graph: graph["claim_boundaries"].update(a2_unlocked=True), "planner_graph_binding_mismatch"),
    ],
)
def test_non_exact_runtime_projection_remains_fail_closed(tmp_path: Path, mutator, expected: str) -> None:
    graph = copy.deepcopy(_graph())
    mutator(graph)
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    database = tmp_path / "state.sqlite3"
    _database(database, "b" * 64)

    with pytest.raises(m7.MasteryError, match=expected):
        m7.MasteryRemediationEngine(
            database_path=database,
            graph_path=graph_path,
        ).initialize()
