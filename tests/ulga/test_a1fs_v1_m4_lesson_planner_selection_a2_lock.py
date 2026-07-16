from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4
from ulga.validators import validate_a1fs_v1_m4_lesson_planner_selection_a2_lock as validator


def _fixture(tmp_path: Path) -> tuple[m4.LessonPlanner, m3.LearnerStateStore, Path, Path, Path, dict]:
    lesson_specs = [
        ("LISTENING", "L-A1", "A1", "EVD"), ("LISTENING", "L-A1P", "A1+", "EVD"),
        ("SPEAKING", "S-A1", "A1", "PRD"), ("SPEAKING", "S-A1P", "A1+", "PRD"),
        ("READING", "R-A1", "A1", "TXT"), ("WRITING", "W-A1", "A1", "EVD"),
        ("LISTENING", "L-A2", "A2", "AUD"), ("SPEAKING", "S-A2", "A2", "PRD"),
        ("READING", "R-A2", "A2", "TXT"), ("WRITING", "W-A2", "A2", "EVD"),
    ]
    nodes = [{"node_id": f"LESSON:{skill}:{lesson}", "node_type": "LESSON", "skill": skill, "level": level, "source_ref": lesson, "mastery_required_before_a2": level in {"A1", "A1+"}} for skill, lesson, level, _ in lesson_specs]
    nodes += [{"node_id": "REF:LISTENING:R1", "node_type": "CAPABILITY", "skill": "LISTENING", "level": "A1", "source_ref": "R1", "mastery_required_before_a2": True}]
    required = sorted(row["node_id"] for row in nodes if row["mastery_required_before_a2"])
    a2 = sorted(row["node_id"] for row in nodes if row["node_type"] == "LESSON" and row["level"] == "A2")
    edges = [
        {"from_node_id": "LESSON:LISTENING:L-A1", "to_node_id": "LESSON:LISTENING:L-A1P", "edge_type": "PRECEDES"},
        {"from_node_id": "LESSON:SPEAKING:S-A1", "to_node_id": "LESSON:SPEAKING:S-A1P", "edge_type": "PRECEDES"},
    ]
    edges += [{"from_node_id": node, "to_node_id": "GATE:A1FS:A2_LOCK", "edge_type": "UNLOCK_REQUIRES"} for node in required]
    graph = {"validation_status": m4.GRAPH_STATUS, "nodes": nodes, "edges": edges,
             "counts": {"required_mastery_node_count": len(required)},
             "a2_lock_contract": {"required_mastery_node_ids": required, "a2_handoff_lesson_node_ids": a2}}
    graph_path = tmp_path / "graph.json"; graph_path.write_text(json.dumps(graph), encoding="utf-8")
    lessons = []; assets = []
    for skill, lesson, level, role in lesson_specs:
        key = f"ASSET:{lesson}"
        lessons.append({"lesson_id": lesson, "lesson_node_id": f"LESSON:{skill}:{lesson}", "skill": skill, "level": level,
                        "asset_keys": [key], "roles": [role], "requirement_node_ids": ["REF:LISTENING:R1"] if lesson == "L-A1" else [], "release_scope": "PRIVATE_INTERNAL_D0"})
        assets.append({"asset_key": key, "asset_id": key, "lesson_id": lesson, "skill": skill, "level": level, "role": role,
                       "payload": {"text": lesson}, "content_digest": hashlib.sha256(lesson.encode()).hexdigest(), "release_scope": "PRIVATE_INTERNAL_D0"})
    consumer = {"validation_status": m4.CONSUMER_STATUS, "source_graph_sha256": hashlib.sha256(graph_path.read_bytes()).hexdigest(),
                "lesson_catalog": lessons, "asset_records": assets,
                "counts": {"lesson_count": len(lessons), "asset_record_count": len(assets), "learning_lesson_count": 6, "a2_handoff_lesson_count": 4}}
    consumer_path = tmp_path / "consumer.json"; consumer_path.write_text(json.dumps(consumer), encoding="utf-8")
    database = tmp_path / "state.sqlite3"; store = m3.LearnerStateStore(database); store.initialize(consumer_path)
    store.create_profile(learner_id="learner-1", display_label="Learner", at="2026-01-01T00:00:00Z")
    planner = m4.LessonPlanner(database_path=database, consumer_path=consumer_path, graph_path=graph_path); planner.initialize()
    return planner, store, database, consumer_path, graph_path, graph


def test_initial_plan_is_first_balanced_eligible_lesson(tmp_path: Path) -> None:
    planner, _, _, _, _, _ = _fixture(tmp_path)
    result = planner.plan_next(learner_id="learner-1", plan_id="plan-1", at="2026-01-01T00:01:00Z")
    assert result["plan_status"] == "PLAN_LEARNING_LESSON"
    assert result["selected_lesson"]["lesson_id"] == "L-A1"
    assert result["a2_lock"]["a2_lock_state"] == "LOCKED"


def test_active_session_must_resume(tmp_path: Path) -> None:
    planner, store, _, _, _, _ = _fixture(tmp_path)
    store.start_session(learner_id="learner-1", lesson_id="S-A1", session_id="session-1")
    result = planner.plan_next(learner_id="learner-1", plan_id="plan-1")
    assert result["plan_status"] == "RESUME_ACTIVE_SESSION"
    assert result["selected_lesson"]["lesson_id"] == "S-A1"


def test_completed_lesson_opens_successor_and_balances_other_skill(tmp_path: Path) -> None:
    planner, store, _, _, _, _ = _fixture(tmp_path)
    store.start_session(learner_id="learner-1", lesson_id="L-A1", session_id="session-1")
    store.end_session(session_id="session-1", outcome="COMPLETED", expected_session_version=1)
    balanced = planner.plan_next(learner_id="learner-1", plan_id="plan-balanced")
    assert balanced["selected_lesson"]["lesson_id"] == "S-A1"
    listening = planner.plan_next(learner_id="learner-1", preferred_skill="LISTENING", plan_id="plan-listening")
    assert listening["selected_lesson"]["lesson_id"] == "L-A1P"


def test_partial_or_wrong_authority_mastery_keeps_a2_locked(tmp_path: Path) -> None:
    planner, _, _, _, graph_path, graph = _fixture(tmp_path)
    snapshot = {"validation_status": "NOT_AUTHORIZED", "learner_id": "learner-1", "source_graph_sha256": hashlib.sha256(graph_path.read_bytes()).hexdigest(), "mastered_node_ids": graph["a2_lock_contract"]["required_mastery_node_ids"]}
    lock = planner.evaluate_a2_lock(learner_id="learner-1", mastery_snapshot=snapshot)
    assert lock["a2_lock_state"] == "LOCKED" and lock["mastery_authority_valid"] is False
    assert lock["a2_payload_access_granted"] is False


def test_exact_authoritative_mastery_yields_metadata_only_handoff(tmp_path: Path) -> None:
    planner, _, _, _, graph_path, graph = _fixture(tmp_path)
    snapshot = {"validation_status": m4.MASTERY_SNAPSHOT_STATUS, "learner_id": "learner-1", "source_graph_sha256": hashlib.sha256(graph_path.read_bytes()).hexdigest(), "mastered_node_ids": graph["a2_lock_contract"]["required_mastery_node_ids"]}
    result = planner.plan_next(learner_id="learner-1", mastery_snapshot=snapshot, plan_id="plan-a2")
    assert result["plan_status"] == "A2_HANDOFF_READY"
    assert result["selected_lesson"]["level"] == "A2"
    assert result["a2_payload_included"] is False and result["a2_session_started"] is False


def test_no_unseen_lessons_waits_for_mastery_evidence(tmp_path: Path) -> None:
    planner, store, _, _, _, _ = _fixture(tmp_path)
    for index, lesson in enumerate(("L-A1", "L-A1P", "S-A1", "S-A1P", "R-A1", "W-A1"), 1):
        store.start_session(learner_id="learner-1", lesson_id=lesson, session_id=f"s-{index}")
        store.end_session(session_id=f"s-{index}", outcome="COMPLETED", expected_session_version=1)
    result = planner.plan_next(learner_id="learner-1", plan_id="plan-wait")
    assert result["plan_status"] == "AWAITING_MASTERY_EVIDENCE"
    assert result["selected_lesson"] is None


def test_independent_validator_checks_decision_chain_and_boundaries(tmp_path: Path) -> None:
    planner, _, database, consumer, graph, _ = _fixture(tmp_path)
    planner.plan_next(learner_id="learner-1", plan_id="plan-1")
    report = validator.validate(database, consumer, graph)
    assert report["error_count"] == 0, report["errors"]


def test_validator_detects_planner_decision_tampering(tmp_path: Path) -> None:
    planner, _, database, consumer, graph, _ = _fixture(tmp_path)
    planner.plan_next(learner_id="learner-1", plan_id="plan-1")
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE planner_decisions SET rationale_json='{}' WHERE plan_id='plan-1'"); connection.commit()
    report = validator.validate(database, consumer, graph)
    assert any(error.startswith("planner_decision_chain_invalid:") for error in report["errors"])
