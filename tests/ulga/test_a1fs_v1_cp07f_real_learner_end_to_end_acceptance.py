from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import wave

import pytest

from ulga.builders import run_a1fs_v1_cp07f_real_learner_end_to_end_acceptance as runner
from ulga.builders import build_a1fs_v1_m7_mastery_error_remediation_reassessment as m7
from ulga.builders import build_a1fs_v1_m8_review_scheduling_retention_spaced_practice as m8
from ulga.builders import build_a1fs_v1_m9_teacher_dashboard_progress_reporting_export as m9
from ulga.builders import build_a1fs_v1_m10_listening_audio_speaking_recording_integration as m10
from ulga.validators import validate_a1fs_v1_cp07f_real_learner_end_to_end_acceptance as validator


def _load_cp07d_fixture_module():
    path = Path("tests/ulga/cp07d_private_four_skill_delivery_consumer_test_impl.py")
    spec = importlib.util.spec_from_file_location("cp07f_cp07d_fixture", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cp07d_fixture_loader_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _wav(path: Path) -> None:
    frames = b"\x00\x00" * 2400
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(frames)


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
    store.review_response(
        attempt_id=attempt_id,
        decision=decision,
        reviewer_id="cp07f-fixture-reviewer",
        criteria={
            "grammar_target_match": decision == "APPROVE",
            "meaning_matches_context": True,
            "complete_response": True,
        },
        notes="CP07F TEST_FIXTURE only",
        reviewed_at=reviewed_at,
    )


def _skill_package(tmp_path: Path, skill: str, cp07d_fixture, wav: Path) -> dict:
    root = tmp_path / skill.lower()
    root.mkdir(parents=True, exist_ok=True)
    consumer, session, database, state, response_store = cp07d_fixture._initialize_runtime(root, skill)
    consumer_path = root / f"consumer-{skill}.json"
    capture_key = consumer["cp07d_delivery_contract"]["response_capture_asset_keys"][0]
    initial_attempt_ids: list[str] = []
    response_count = 5 if skill == "READING" else 2
    for index in range(1, response_count + 1):
        submitted_at = f"2026-07-23T0{SKILLS_ORDER[skill]}:{index:02d}:00Z"
        result = response_store.capture_response(
            learner_id="learner-1",
            session_id=session["session_id"],
            asset_key=capture_key,
            response=f"{skill} TEST_FIXTURE response {index}",
            expected_session_version=index,
            attempt_id=f"{skill.lower()}-attempt-{index}",
            submitted_at=submitted_at,
        )
        decision = "REJECT" if skill == "READING" and index == 1 else "APPROVE"
        _review(response_store, result["attempt_id"], decision, submitted_at)
        initial_attempt_ids.append(result["attempt_id"])
    state.end_session(
        session_id=session["session_id"],
        outcome="COMPLETED",
        expected_session_version=response_count + 1,
        at=f"2026-07-23T0{SKILLS_ORDER[skill]}:30:00Z",
    )

    evidence_root = root / "m6"
    evidence = response_store.export_evidence(
        session_id=session["session_id"],
        output_root=evidence_root,
        exported_at="2026-07-23T10:00:00Z",
    )
    m6_registry_path = Path(evidence["registry_path"])

    graph = _graph(consumer, capture_key)
    graph_path = root / "graph.json"
    graph_path.write_text(json.dumps(graph), encoding="utf-8")
    m7_engine = m7.MasteryRemediationEngine(database_path=database, graph_path=graph_path)
    m7_engine.initialize()
    m7_result = m7_engine.build_snapshot(
        learner_id="learner-1",
        output_root=root / "m7",
        created_at="2026-07-23T12:00:00Z",
    )
    m7_path = Path(m7_result["snapshot_path"])
    m8_engine = m8.ReviewRetentionEngine(
        database_path=database,
        graph_path=graph_path,
        m7_snapshot_path=m7_path,
    )
    m8_engine.initialize()
    m8_engine.build_schedule(learner_id="learner-1", as_of="2026-07-24T12:00:00Z")

    if skill == "READING":
        review_session = state.start_session(
            learner_id="learner-1",
            lesson_id=consumer["cp07d_delivery_contract"]["selected_lesson_id"],
            session_id="reading-delayed-review-session",
            at="2026-07-24T12:00:00Z",
        )
        review_attempt = response_store.capture_response(
            learner_id="learner-1",
            session_id=review_session["session_id"],
            asset_key=capture_key,
            response="Reading delayed TEST_FIXTURE response",
            expected_session_version=1,
            attempt_id="reading-delayed-review-attempt",
            submitted_at="2026-07-24T12:00:00Z",
        )
        _review(response_store, review_attempt["attempt_id"], "APPROVE", "2026-07-24T12:00:00Z")
        state.end_session(
            session_id=review_session["session_id"],
            outcome="COMPLETED",
            expected_session_version=2,
            at="2026-07-24T12:00:00Z",
        )
        m8_engine.record_review(
            learner_id="learner-1",
            node_id=graph["a2_lock_contract"]["required_mastery_node_ids"][0],
            attempt_id=review_attempt["attempt_id"],
        )
    m8_result = m8_engine.export_snapshot(
        learner_id="learner-1",
        output_root=root / "m8",
        as_of="2026-07-24T13:00:00Z",
    )
    m8_path = Path(m8_result["snapshot_path"])

    if skill in {"LISTENING", "SPEAKING"}:
        with sqlite3.connect(database) as connection:
            connection.execute("CREATE TABLE m9_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
            connection.execute("INSERT INTO m9_metadata VALUES('validation_status',?)", (m9.STATUS,))
            connection.commit()
        media = m10.PrivateMediaRegistry(
            database_path=database,
            consumer_path=consumer_path,
            media_root=root / "private-media",
        )
        media.initialize()
        if skill == "LISTENING":
            media.register_listening(
                asset_key=consumer["cp07d_delivery_contract"]["listening_audio_asset_keys"][0],
                wav_path=wav,
                created_at="2026-07-23T11:00:00Z",
            )
        else:
            media.register_recording(
                learner_id="learner-1",
                attempt_id=initial_attempt_ids[0],
                wav_path=wav,
                consent_granted=True,
                created_at="2026-07-23T11:00:00Z",
            )

    return {
        "skill": skill,
        "database": str(database.resolve()),
        "consumer": str(consumer_path.resolve()),
        "graph": str(graph_path.resolve()),
        "m6_registry": str(m6_registry_path.resolve()),
        "m7_snapshot": str(m7_path.resolve()),
        "m8_snapshot": str(m8_path.resolve()),
    }


SKILLS_ORDER = {"LISTENING": 2, "SPEAKING": 3, "READING": 4, "WRITING": 5}


def _manifest_fixture(tmp_path: Path) -> Path:
    cp07d_fixture = _load_cp07d_fixture_module()
    wav = tmp_path / "canary.wav"
    _wav(wav)
    packages = [
        _skill_package(tmp_path, skill, cp07d_fixture, wav)
        for skill in runner.SKILLS
    ]
    manifest = {
        "task_id": runner.TASK_ID,
        "schema_version": runner.MANIFEST_SCHEMA_VERSION,
        "private_local_only": True,
        "evidence_origin": "TEST_FIXTURE",
        "learner_ref": "learner-1",
        "skill_packages": packages,
        "operator_attestation": {
            "learner_or_guardian_consent_confirmed": False,
            "evidence_is_not_test_fixture": False,
            "private_storage_confirmed": True,
        },
    }
    path = tmp_path / "cp07f-manifest.private.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_prepare_emits_private_template_without_real_claim(tmp_path: Path) -> None:
    report = runner.prepare(tmp_path / "prepare")
    assert report["validation_status"] == runner.PREPARE_STATUS
    assert report["real_learner_acceptance_completed"] is False
    assert report["stop_reason"] == "REAL_LEARNER_FOUR_SKILL_EVIDENCE_REQUIRED"
    template = tmp_path / "prepare/real_learner_acceptance_manifest.template.private.json"
    assert template.exists()


def test_four_skill_fixture_validates_but_never_counts_as_real(tmp_path: Path) -> None:
    manifest_path = _manifest_fixture(tmp_path)
    report = runner.evaluate_manifest(manifest_path)
    assert report["validation_status"] == runner.TEST_STATUS
    assert report["aggregate_readback"]["attempted_skill_count"] == 4
    assert report["aggregate_readback"]["resolved_attempt_count"] >= 11
    assert report["aggregate_readback"]["m7_diagnosis_count"] >= 1
    assert report["aggregate_readback"]["completed_remediation_count"] >= 1
    assert report["aggregate_readback"]["completed_reassessment_count"] >= 1
    assert report["aggregate_readback"]["m8_review_event_count"] >= 1
    assert report["acceptance_gate"]["listening_audio_registered"] is True
    assert report["acceptance_gate"]["speaking_consented_recording_registered"] is True
    assert report["real_learner_evidence_captured"] is False
    assert report["real_learner_acceptance_completed"] is False
    assert report["real_retention_claimed"] is False
    assert report["stop_reason"] == "REAL_LEARNER_FOUR_SKILL_EVIDENCE_REQUIRED"
    assert report["next_short_step"] == runner.TASK_ID
    validation = validator.validate_report(report, manifest_path=manifest_path)
    assert validation["error_count"] == 0, validation["errors"]
    assert validation["deterministic_rebuild_matches"] is True
    text = json.dumps(report, sort_keys=True)
    for private_value in (
        "learner-1",
        "TEST_FIXTURE response",
        "cp07f-fixture-reviewer",
        "reading-attempt-1",
        str(tmp_path),
    ):
        assert private_value not in text


def test_missing_speaking_recording_fails_closed(tmp_path: Path) -> None:
    manifest_path = _manifest_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    speaking = next(row for row in manifest["skill_packages"] if row["skill"] == "SPEAKING")
    with sqlite3.connect(speaking["database"]) as connection:
        connection.execute("DELETE FROM private_media_assets WHERE media_kind='SPEAKING_RECORDING'")
        connection.commit()
    with pytest.raises(runner.CP07FAcceptanceError, match="consented_recording_required"):
        runner.evaluate_manifest(manifest_path)


def test_duplicate_skill_partition_and_fixture_real_attestation_fail_closed(tmp_path: Path) -> None:
    manifest_path = _manifest_fixture(tmp_path)
    manifest = json.loads(manifest_path.read_text())
    manifest["skill_packages"][0]["skill"] = "READING"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(runner.CP07FAcceptanceError, match="four_skill_package_partition_invalid"):
        runner.evaluate_manifest(manifest_path)

    manifest_path = _manifest_fixture(tmp_path / "real-claim")
    manifest = json.loads(manifest_path.read_text())
    manifest["evidence_origin"] = "REAL_LEARNER"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(runner.CP07FAcceptanceError, match="consent_attestation_required"):
        runner.evaluate_manifest(manifest_path)


def test_validator_rejects_fixture_promoted_to_real_status(tmp_path: Path) -> None:
    manifest_path = _manifest_fixture(tmp_path)
    report = runner.evaluate_manifest(manifest_path)
    tampered = deepcopy(report)
    tampered["validation_status"] = runner.REAL_STATUS
    tampered["real_learner_evidence_captured"] = True
    tampered["real_learner_acceptance_completed"] = True
    tampered["stop_reason"] = "NONE"
    validation = validator.validate_report(tampered, manifest_path=manifest_path)
    assert validation["error_count"] > 0
