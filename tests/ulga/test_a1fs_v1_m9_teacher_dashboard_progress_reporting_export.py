from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from jsonschema import Draft202012Validator

from ulga.builders.build_a1fs_v1_m9_teacher_dashboard_progress_reporting_export import DashboardExporter
from ulga.validators.validate_a1fs_v1_m9_teacher_dashboard_progress_reporting_export import validate


def digest_value(value):
    raw = value if isinstance(value, bytes) else json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def fixture(tmp_path: Path):
    graph = {
        "validation_status": "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE",
        "a2_lock_contract": {"required_mastery_node_ids": ["N1", "N2"]},
    }
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph))
    graph_sha = digest_value(graph_path.read_bytes())
    m7 = {
        "validation_status": "PASS_A1FS_V1_M7_MASTERY_REMEDIATION_REASSESSMENT",
        "learner_id": "learner",
        "source_graph_sha256": graph_sha,
        "required_mastery_node_count": 2,
        "mastered_required_count": 1,
        "missing_mastery_node_ids": ["N2"],
        "a2_lock_state": "LOCKED",
        "remediation_assignments": [{"node_id": "N2", "assignment_state": "OPEN"}],
        "reassessment_queue": [{"node_id": "N2", "queue_state": "PENDING"}],
    }
    m7_path = tmp_path / "m7.json"
    m7_path.write_text(json.dumps(m7))
    m8 = {
        "validation_status": "PASS_A1FS_V1_M8_REVIEW_SCHEDULING_RETENTION_SPACED_PRACTICE",
        "learner_id": "learner",
        "source_graph_sha256": graph_sha,
        "source_m7_snapshot_digest": digest_value(m7),
        "required_mastery_node_count": 2,
        "retained_required_count": 0,
        "retention_confirmed": False,
        "review_schedules": [{"node_id": "N1", "schedule_state": "DUE"}],
    }
    m8_path = tmp_path / "m8.json"
    m8_path.write_text(json.dumps(m8))
    database = tmp_path / "state.sqlite"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE learner_profiles(learner_id TEXT PRIMARY KEY,display_label TEXT,locale TEXT,timezone_name TEXT,profile_state TEXT);
            CREATE TABLE learning_sessions(session_id TEXT PRIMARY KEY,learner_id TEXT,skill TEXT,session_state TEXT);
            CREATE TABLE response_contracts(asset_key TEXT PRIMARY KEY,skill TEXT);
            CREATE TABLE response_attempts(attempt_id TEXT PRIMARY KEY,learner_id TEXT,asset_key TEXT,response_json TEXT);
            CREATE TABLE scoring_results(attempt_id TEXT PRIMARY KEY,outcome TEXT);
            """
        )
        connection.execute(
            "INSERT INTO learner_profiles VALUES(?,?,?,?,?)",
            ("learner", "Learner", "zh-TW", "Asia/Taipei", "ACTIVE"),
        )
        for index, skill, state in (
            (1, "READING", "COMPLETED"),
            (2, "WRITING", "ACTIVE"),
        ):
            connection.execute(
                "INSERT INTO learning_sessions VALUES(?,?,?,?)",
                (f"s{index}", "learner", skill, state),
            )
        for asset_key, skill in (("r", "READING"), ("w", "WRITING"), ("sp", "SPEAKING")):
            connection.execute(
                "INSERT INTO response_contracts VALUES(?,?)",
                (asset_key, skill),
            )
        for attempt_id, asset_key, outcome, text in (
            ("a1", "r", "AUTO_PASS", "private answer one"),
            ("a2", "w", "AUTO_FAIL", "private answer two"),
            ("a3", "sp", "PENDING_HUMAN_REVIEW", "private answer three"),
        ):
            connection.execute(
                "INSERT INTO response_attempts VALUES(?,?,?,?)",
                (attempt_id, "learner", asset_key, json.dumps(text)),
            )
            connection.execute(
                "INSERT INTO scoring_results VALUES(?,?)",
                (attempt_id, outcome),
            )
    exporter = DashboardExporter(
        database_path=database,
        graph_path=graph_path,
        m7_snapshot_path=m7_path,
        m8_snapshot_path=m8_path,
    )
    exporter.initialize()
    return database, graph_path, m7_path, m8_path, exporter


def build(tmp_path: Path):
    database, graph, m7, m8, exporter = fixture(tmp_path)
    result = exporter.build(
        learner_id="learner",
        output_root=tmp_path / "out",
        generated_at="2026-07-16T00:00:00Z",
    )
    return database, graph, m7, m8, result


def test_report_projects_four_skills_and_schema(tmp_path: Path) -> None:
    database, graph, m7, m8, result = build(tmp_path)
    report = json.loads(Path(result["json_path"]).read_text())
    assert [row["skill"] for row in report["four_skill_progress"]] == [
        "LISTENING", "SPEAKING", "READING", "WRITING"
    ]
    schema = json.loads(Path("ulga/schemas/a1fs_v1_m9_teacher_dashboard_report.schema.json").read_text())
    assert not list(Draft202012Validator(schema).iter_errors(report))
    validation = validate(
        database,
        graph,
        m7,
        m8,
        Path(result["json_path"]),
        Path(result["html_path"]),
    )
    assert not validation["errors"]


def test_attention_surfaces_review_remediation_and_due(tmp_path: Path) -> None:
    *_, result = build(tmp_path)
    report = json.loads(Path(result["json_path"]).read_text())
    assert report["human_review"]["pending_count"] == 1
    assert report["remediation"] == {
        "open_count": 1,
        "pending_reassessment_count": 1,
        "open_node_ids": ["N2"],
    }
    assert report["retention"]["due_or_overdue_count"] == 1
    assert len(report["attention_items"]) == 4


def test_raw_responses_never_exported(tmp_path: Path) -> None:
    *_, result = build(tmp_path)
    content = Path(result["json_path"]).read_text() + Path(result["html_path"]).read_text()
    assert "private answer" not in content
    assert "response_json" not in content


def test_html_is_static_and_network_free(tmp_path: Path) -> None:
    *_, result = build(tmp_path)
    content = Path(result["html_path"]).read_text().lower()
    assert "<script" not in content
    assert "http://" not in content
    assert "https://" not in content
    assert "fetch(" not in content


def test_a2_and_human_pilot_boundaries_remain_false(tmp_path: Path) -> None:
    *_, result = build(tmp_path)
    report = json.loads(Path(result["json_path"]).read_text())
    assert report["a2_lock"]["payload_access_granted"] is False
    assert report["a2_lock"]["session_start_granted"] is False
    assert report["privacy_boundaries"]["human_pilot_claimed"] is False


def test_report_tamper_is_detected(tmp_path: Path) -> None:
    database, graph, m7, m8, result = build(tmp_path)
    path = Path(result["json_path"])
    value = json.loads(path.read_text())
    value["four_skill_progress"][2]["pass_count"] = 99
    path.write_text(json.dumps(value))
    validation = validate(
        database,
        graph,
        m7,
        m8,
        path,
        Path(result["html_path"]),
    )
    assert validation["error_count"] > 0
