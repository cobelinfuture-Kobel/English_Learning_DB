from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from ulga.builders import build_a1fs_v1_cp07e_diagnosis_remediation_reassessment_retention_closure as builder
from ulga.validators import validate_a1fs_v1_cp07e_diagnosis_remediation_reassessment_retention_closure as validator


def _load_cp07d_fixture_module():
    path = Path("tests/ulga/cp07d_private_four_skill_delivery_consumer_test_impl.py")
    spec = importlib.util.spec_from_file_location("cp07e_cp07d_fixture", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cp07d_fixture_loader_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _graph(consumer: dict, projected_asset_key: str) -> dict:
    lesson = consumer["lesson_catalog"][0]
    capability_id = lesson["requirement_node_ids"][0]
    projected = next(row for row in consumer["asset_records"] if row["asset_key"] == projected_asset_key)
    gate_id = "GATE:A1FS:A2_LOCK"
    return {
        "task_id": "A1FS-V1-M1_A1A1PlusPrerequisiteGraphAndCoverage",
        "schema_version": "a1fs.v1.m1.prerequisite_graph_and_coverage.v1",
        "validation_status": "PASS_A1FS_V1_M1_PREREQUISITE_GRAPH_AND_COVERAGE",
        "source_baseline_sha256": "b" * 64,
        "nodes": [
            {
                "node_id": lesson["lesson_node_id"],
                "node_type": "LESSON",
                "skill": lesson["skill"],
                "level": lesson["level"],
                "source_ref": lesson["lesson_id"],
                "mastery_required_before_a2": True,
            },
            {
                "node_id": capability_id,
                "node_type": "CAPABILITY",
                "skill": lesson["skill"],
                "level": lesson["level"],
                "source_ref": capability_id.split(":")[-1],
                "mastery_required_before_a2": True,
            },
            {
                "node_id": gate_id,
                "node_type": "A2_LOCK",
                "skill": "FOUR_SKILL",
                "level": "A2",
                "source_ref": "A2_ENTRY",
                "mastery_required_before_a2": False,
            },
        ],
        "edges": [
            {"from_node_id": capability_id, "to_node_id": lesson["lesson_node_id"], "edge_type": "TAUGHT_BY"},
            {"from_node_id": lesson["lesson_node_id"], "to_node_id": gate_id, "edge_type": "UNLOCK_REQUIRES"},
            {"from_node_id": capability_id, "to_node_id": gate_id, "edge_type": "UNLOCK_REQUIRES"},
        ],
        "coverage": [
            {
                "node_id": capability_id,
                "skill": lesson["skill"],
                "source_ref": capability_id.split(":")[-1],
                "coverage_class": "MASTERY",
                "levels": [lesson["level"]],
                "lesson_ids": [lesson["lesson_id"]],
                "asset_body_ids": [projected["asset_id"]],
                "roles": [projected["role"]],
                "coverage_status": "COVERED",
            }
        ],
        "counts": {
            "node_count": 3,
            "edge_count": 3,
            "coverage_record_count": 1,
            "lesson_count": 1,
            "lesson_count_by_level": {"A1": 1, "A1+": 0, "A2": 0},
            "required_mastery_node_count": 2,
            "a2_handoff_lesson_count": 0,
            "uncovered_required_node_count": 0,
        },
        "a2_lock_contract": {
            "gate_node_id": gate_id,
            "state": "LOCKED_BY_DESIGN",
            "required_mastery_node_ids": [lesson["lesson_node_id"], capability_id],
            "a2_handoff_lesson_node_ids": [],
            "unlock_rule": "ALL_REQUIRED_MASTERY_NODES_MUST_BE_MASTERED",
            "runtime_unlock_implemented": False,
        },
        "claim_boundaries": {
            "source_packages_committed": False,
            "asset_body_content_modified": False,
            "learner_release_approved": False,
            "mastery_claimed": False,
            "a2_unlocked": False,
            "runtime_planner_implemented": False,
            "human_pilot_claimed": False,
            "listening_audio_complete": False,
        },
        "errors": [],
        "next_short_step": "A1FS-V1-M2_FourSkillAssetBodyConsumerAndQuery",
    }


def _review(store, attempt_id: str, decision: str, reviewed_at: str) -> None:
    criteria = {
        "grammar_target_match": decision == "APPROVE",
        "meaning_matches_context": True,
        "complete_response": True,
    }
    store.review_response(
        attempt_id=attempt_id,
        decision=decision,
        reviewer_id="cp07e-synthetic-reviewer",
        criteria=criteria,
        notes="synthetic contract canary",
        reviewed_at=reviewed_at,
    )


def _fixture(tmp_path: Path) -> dict:
    cp07d_fixture = _load_cp07d_fixture_module()
    consumer, session, database, state, response_store = cp07d_fixture._initialize_runtime(tmp_path, "READING")
    consumer_path = tmp_path / "consumer-READING.json"
    projected_key = consumer["cp07d_delivery_contract"]["response_capture_asset_keys"][0]

    initial_attempts: list[str] = []
    for index in range(1, 6):
        submitted_at = f"2026-07-23T01:0{index + 1}:00Z"
        result = response_store.capture_response(
            learner_id="learner-1",
            session_id=session["session_id"],
            asset_key=projected_key,
            response=f"Synthetic source-grounded response {index}.",
            expected_session_version=index,
            attempt_id=f"initial-{index}",
            submitted_at=submitted_at,
        )
        initial_attempts.append(result["attempt_id"])
        _review(
            response_store,
            result["attempt_id"],
            "REJECT" if index == 1 else "APPROVE",
            submitted_at,
        )
    state.end_session(
        session_id=session["session_id"],
        outcome="COMPLETED",
        expected_session_version=6,
        at="2026-07-23T01:10:00Z",
    )

    review_attempts: list[str] = []
    for stage, submitted_at in enumerate(
        ("2026-07-24T02:00:00Z", "2026-07-27T02:00:00Z", "2026-08-03T02:00:00Z"),
        start=1,
    ):
        review_session = state.start_session(
            learner_id="learner-1",
            lesson_id=consumer["cp07d_delivery_contract"]["selected_lesson_id"],
            session_id=f"review-session-{stage}",
            at=submitted_at,
        )
        result = response_store.capture_response(
            learner_id="learner-1",
            session_id=review_session["session_id"],
            asset_key=projected_key,
            response=f"Delayed synthetic review response {stage}.",
            expected_session_version=1,
            attempt_id=f"review-attempt-{stage}",
            submitted_at=submitted_at,
        )
        _review(response_store, result["attempt_id"], "APPROVE", submitted_at)
        state.end_session(
            session_id=review_session["session_id"],
            outcome="COMPLETED",
            expected_session_version=2,
            at=submitted_at,
        )
        review_attempts.append(result["attempt_id"])

    graph = _graph(consumer, projected_key)
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    node_ids = graph["a2_lock_contract"]["required_mastery_node_ids"]
    records = [
        {"node_id": node_id, "attempt_id": attempt_id}
        for attempt_id in review_attempts
        for node_id in node_ids
    ]
    references = {
        "schema_version": builder.REVIEW_REFERENCE_SCHEMA_VERSION,
        "evidence_classification": builder.EVIDENCE_CLASSIFICATION,
        "records": records,
    }
    references_path = tmp_path / "review-references.private.json"
    references_path.write_text(json.dumps(references), encoding="utf-8")
    return {
        "consumer": consumer,
        "consumer_path": consumer_path,
        "database": database,
        "graph": graph,
        "graph_path": graph_path,
        "references": references,
        "references_path": references_path,
        "private_output_root": tmp_path / "cp07e-private",
    }


def _build(fixture: dict):
    return builder.build_closure(
        database=fixture["database"],
        graph_path=fixture["graph_path"],
        consumer_path=fixture["consumer_path"],
        learner_id="learner-1",
        review_references_path=fixture["references_path"],
        private_output_root=fixture["private_output_root"],
        m7_created_at="2026-07-23T02:00:00Z",
        schedule_as_of="2026-07-24T02:00:00Z",
        export_as_of="2026-08-03T03:00:00Z",
    )


def test_cp07d_m6_m7_m8_contract_closes_without_real_learner_claim(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    artifact, m7_path, m8_path = _build(fixture)
    assert artifact["validation_status"] == builder.PASS_STATUS
    assert artifact["m7_closure"]["resolved_diagnosis_count"] == 1
    assert artifact["m7_closure"]["completed_remediation_count"] == 2
    assert artifact["m7_closure"]["completed_reassessment_count"] == 2
    assert artifact["m8_closure"]["review_event_count"] == 6
    assert artifact["m8_closure"]["retained_required_count"] == 2
    assert artifact["m8_closure"]["synthetic_retention_state_reached"] is True
    assert artifact["claim_boundaries"]["real_learner_attempt_claimed"] is False
    assert artifact["claim_boundaries"]["real_retention_claimed"] is False
    assert artifact["next_short_step"] == builder.NEXT_SHORT_STEP

    report = validator.validate_artifact(
        artifact,
        database=fixture["database"],
        graph_path=fixture["graph_path"],
        consumer_path=fixture["consumer_path"],
        review_references_path=fixture["references_path"],
        m7_snapshot_path=m7_path,
        m8_snapshot_path=m8_path,
    )
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert report["synthetic_canary_only"] is True
    safe_text = json.dumps(artifact, sort_keys=True)
    for forbidden in (
        "Synthetic source-grounded response",
        "Delayed synthetic review response",
        "initial-1",
        "review-attempt-1",
        "learner-1",
        "cp07e-synthetic-reviewer",
    ):
        assert forbidden not in safe_text


def test_incomplete_three_stage_review_references_fail_closed(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    fixture["references"]["records"] = fixture["references"]["records"][:-1]
    fixture["references_path"].write_text(json.dumps(fixture["references"]), encoding="utf-8")
    with pytest.raises(builder.CP07EClosureError, match="synthetic_retention_state_not_reached"):
        _build(fixture)


def test_cp07d_projected_asset_level_drift_and_a2_fail_closed(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    tampered = deepcopy(fixture["consumer"])
    projected_keys = set(tampered["cp07d_delivery_contract"]["projected_asset_keys"])
    for row in tampered["asset_records"]:
        if row["asset_key"] in projected_keys:
            row["level"] = "A2"
    tampered_path = tmp_path / "consumer-a2-tampered.json"
    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")
    fixture["consumer_path"] = tampered_path
    with pytest.raises(builder.CP07EClosureError, match="projected_asset_selected_lesson_level_drift"):
        _build(fixture)


def test_validator_rejects_premature_real_retention_claim(tmp_path: Path) -> None:
    fixture = _fixture(tmp_path)
    artifact, m7_path, m8_path = _build(fixture)
    tampered = deepcopy(artifact)
    tampered["claim_boundaries"]["real_retention_claimed"] = True
    report = validator.validate_artifact(
        tampered,
        database=fixture["database"],
        graph_path=fixture["graph_path"],
        consumer_path=fixture["consumer_path"],
        review_references_path=fixture["references_path"],
        m7_snapshot_path=m7_path,
        m8_snapshot_path=m8_path,
    )
    assert report["validation_status"] != builder.PASS_STATUS
    assert any("claim_boundary_must_remain_false" in error for error in report["errors"])
