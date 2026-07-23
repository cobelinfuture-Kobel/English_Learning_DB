from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import wave

import pytest

from ulga.builders import build_a1fs_v1_cp05_private_candidate_materialization_and_admission as cp05
from ulga.builders import build_a1fs_v1_cp07c_unified_m4_lesson_composition as cp07c
from ulga.builders import build_a1fs_v1_cp07d_private_four_skill_delivery_consumer as builder
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4
from ulga.builders import build_a1fs_v1_m5_four_skill_renderer_learner_ui as m5
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_m9_teacher_dashboard_progress_reporting_export as m9
from ulga.builders import build_a1fs_v1_m10_listening_audio_speaking_recording_integration as m10
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy
from ulga.validators import validate_a1fs_v1_cp07d_private_four_skill_delivery_consumer as validator


ORIGINAL_ROLE = {
    "LISTENING": "GDT",
    "SPEAKING": "MOD",
    "READING": "TXT",
    "WRITING": "MOD",
}


def _m2(skill: str) -> dict:
    lesson_id = f"{skill[:1]}-A1"
    asset_key = f"KET:{skill}:BASE"
    return {
        "task_id": m2.TASK_ID,
        "schema_version": m2.SCHEMA_VERSION,
        "validation_status": m2.STATUS,
        "source_graph_sha256": "1" * 64,
        "asset_records": [
            {
                "asset_id": asset_key,
                "asset_key": asset_key,
                "lesson_id": lesson_id,
                "skill": skill,
                "level": "A1",
                "role": ORIGINAL_ROLE[skill],
                "payload": {"learner_instruction": f"Private KET {skill.lower()} base asset."},
                "content_digest": "2" * 64,
                "release_scope": "PRIVATE_INTERNAL_D0",
            }
        ],
        "lesson_catalog": [
            {
                "lesson_id": lesson_id,
                "lesson_node_id": f"LESSON:{skill}:{lesson_id}",
                "skill": skill,
                "level": "A1",
                "asset_keys": [asset_key],
                "roles": [ORIGINAL_ROLE[skill]],
                "requirement_node_ids": [f"REF:{skill}:A1"],
                "release_scope": "PRIVATE_INTERNAL_D0",
            }
        ],
        "counts": {
            "asset_record_count": 1,
            "lesson_count": 1,
            "learning_lesson_count": 1,
            "a2_handoff_lesson_count": 0,
        },
        "access_contract": {
            "visibility": "PRIVATE_INTERNAL",
            "learning_query_levels": ["A1", "A1+"],
            "a2_payload_query_allowed": False,
            "a2_handoff_metadata_allowed": True,
            "max_query_limit": 100,
            "filter_fields": ["skill", "level", "lesson_id", "role", "requirement_node_id"],
        },
        "claim_boundaries": {"a2_unlocked": False},
        "errors": [],
    }


def _approved(skill: str) -> dict:
    material_id = f"RAZ_MAT_{skill}"
    binding_id = f"RAZ_BIND_{skill}"
    contract = {
        "skill": skill,
        "activity_kind": f"SOURCE_{skill}_CANARY",
        "prompt": f"Complete one {skill.lower()} response about the source.",
        "response_mode": "AUDIO_RECORDING" if skill == "SPEAKING" else "OPEN_TEXT_OR_AUDIO" if skill == "LISTENING" else "OPEN_TEXT",
        "support_level": "AUDIO_WITH_OPTIONAL_REPLAY" if skill == "LISTENING" else "SOURCE_TEXT_VISIBLE",
        "initiative_level": "GUIDED",
        "scoring_contract": {
            "mode": "RUBRIC",
            "automatic_exact_answer": False,
            "criteria": ["SOURCE_RELEVANCE", "TARGET_LANGUAGE_USE"],
        },
        "evidence_level": "RECORDED_LEARNER_RESPONSE_REQUIRED" if skill == "SPEAKING" else "LEARNER_RESPONSE_REQUIRED",
        "runtime_dependency_status": "AUDIO_GENERATION_REQUIRED" if skill == "LISTENING" else "RECORDING_CAPTURE_REQUIRED" if skill == "SPEAKING" else "READY_FOR_TEXT_RUNTIME_INTEGRATION",
    }
    payload = {
        "task_id": cp05.TASK_ID,
        "program_id": cp05.PROGRAM_ID,
        "schema_version": cp05.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "materialized_raz_sources": [
            {
                "material_id": material_id,
                "source_unit_ref": f"RAZ_A_{skill}_001",
                "source_content": {"text": f"This is private {skill.lower()} source content."},
                "source_content_sha256": "3" * 64,
                "skill_contracts": [contract],
                "materialization_status": "MATERIALIZED_PRIVATE_SOURCE_BOUND",
            }
        ],
        "raz_unit_activity_bindings": [
            {
                "activity_binding_id": binding_id,
                "material_id": material_id,
                "learning_unit_id": "E4S_A1V1_UNIT:GRAMMAR_BE_VERB_BASIC",
                "grammar_unit_id": "GRAMMAR_BE_VERB_BASIC",
            }
        ],
        "stop_reason": "NONE",
    }
    candidate = policy.build_candidate(
        payload=payload,
        producer_id=cp05.PRODUCER_ID,
        level_scope=["A1"],
        source_bindings={"fixture": skill},
    )
    return policy.admit_candidate(
        candidate,
        validation_receipts=[{"validator_id": "cp07d_fixture", "status": "PASS", "receipt_sha256": "4" * 64}],
        decision_ref=f"CP07D_FIXTURE_{skill}",
        producer_id=cp05.PRODUCER_ID,
    )


def _plan(skill: str, consumer: dict) -> dict:
    lesson = consumer["lesson_catalog"][0]
    runtime_id = f"CP07A:RAZ:{skill}:FOCUS"
    return {
        "task_id": m4.TASK_ID,
        "validation_status": m4.STATUS,
        "plan_id": f"plan-{skill.lower()}",
        "learner_id": "learner-1",
        "plan_status": "PLAN_LEARNING_LESSON",
        "selected_lesson": {
            "lesson_id": lesson["lesson_id"],
            "lesson_node_id": lesson["lesson_node_id"],
            "skill": skill,
            "level": "A1",
            "roles": lesson["roles"],
            "requirement_node_ids": lesson["requirement_node_ids"],
        },
        "a2_lock": {"a2_payload_access_granted": False, "a2_session_start_granted": False},
        "a2_payload_included": False,
        "a2_session_started": False,
        "cp07c_task_id": cp07c.TASK_ID,
        "cp07c_schema_version": cp07c.SCHEMA_VERSION,
        "cp07c_validation_status": cp07c.PASS_STATUS,
        "source_identity": {"m2_consumer_sha256": builder._digest(consumer)},
        "unified_lesson_composition": {
            "selected_lesson_id": lesson["lesson_id"],
            "selected_skill": skill,
            "composition_items": [
                {
                    "composition_item_id": runtime_id,
                    "source_kind": "RAZ_ACTIVITY_BINDING",
                    "skill": skill,
                    "instructional_role": "FOCUS",
                    "grammar_unit_id": "GRAMMAR_BE_VERB_BASIC",
                    "learning_unit_id": "E4S_A1V1_UNIT:GRAMMAR_BE_VERB_BASIC",
                    "runtime_readiness": "BLOCKED_AUDIO_GENERATION" if skill == "LISTENING" else "BLOCKED_RECORDING_CAPTURE" if skill == "SPEAKING" else "QUERYABLE_TEXT_RUNTIME_CONTRACT",
                    "source_lineage": {
                        "cp05_activity_binding_id": f"RAZ_BIND_{skill}",
                        "cp05_material_id": f"RAZ_MAT_{skill}",
                    },
                    "response_contract_ref": {"authority": "CP05_APPROVED_SKILL_CONTRACT"},
                }
            ],
        },
        "errors": [],
        "stop_reason": "NONE",
    }


def _inputs(skill: str) -> tuple[dict, dict, dict]:
    consumer = _m2(skill)
    return consumer, _approved(skill), _plan(skill, consumer)


def _wav(path: Path) -> None:
    frames = b"\x00\x00" * 2400
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(frames)


def _initialize_runtime(tmp_path: Path, skill: str) -> tuple[dict, dict, Path, m3.LearnerStateStore, m6.ResponseEvidenceStore]:
    inputs = _inputs(skill)
    consumer = builder.build_private_delivery_consumer(*inputs)
    consumer_path = tmp_path / f"consumer-{skill}.json"
    plan_path = tmp_path / f"plan-{skill}.json"
    consumer_path.write_text(json.dumps(consumer), encoding="utf-8")
    plan_path.write_text(json.dumps(inputs[2]), encoding="utf-8")
    database = tmp_path / f"runtime-{skill}.sqlite3"
    state = m3.LearnerStateStore(database)
    state.initialize(consumer_path)
    state.create_profile(learner_id="learner-1", display_label="Learner One", at="2026-07-23T01:00:00Z")
    session = state.start_session(
        learner_id="learner-1", lesson_id=consumer["cp07d_delivery_contract"]["selected_lesson_id"],
        session_id=f"session-{skill.lower()}", at="2026-07-23T01:01:00Z",
    )
    ui_root = tmp_path / f"ui-{skill}"
    m5.build_ui(consumer_path=consumer_path, plan_path=plan_path, output_root=ui_root)
    response_store = m6.ResponseEvidenceStore(database)
    response_store.initialize(consumer_path=consumer_path, lesson_bundle_path=ui_root / "lesson.private.json")
    return consumer, session, database, state, response_store


@pytest.mark.parametrize("skill", ["READING", "WRITING", "LISTENING", "SPEAKING"])
def test_policy_bound_projection_consumer_validates_for_each_skill(skill: str) -> None:
    inputs = _inputs(skill)
    artifact = builder.build_private_delivery_consumer(*inputs)
    report = validator.validate_artifact(
        artifact,
        m2_consumer=inputs[0], cp05_approved=inputs[1], cp07c_plan=inputs[2],
    )
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert report["deterministic_rebuild_matches"] is True
    assert report["projection_artifact_count"] == 1
    assert report["response_capture_asset_count"] == 1
    expected_assets = 2 if skill == "LISTENING" else 1
    assert report["projected_asset_count"] == expected_assets


@pytest.mark.parametrize("skill", ["READING", "WRITING", "LISTENING", "SPEAKING"])
def test_existing_m3_m5_m6_runtime_captures_projected_attempt(tmp_path: Path, skill: str) -> None:
    consumer, session, _, _, response_store = _initialize_runtime(tmp_path, skill)
    key = consumer["cp07d_delivery_contract"]["response_capture_asset_keys"][0]
    result = response_store.capture_response(
        learner_id="learner-1",
        session_id=session["session_id"],
        asset_key=key,
        response="A source-grounded learner response.",
        expected_session_version=session["session_version"],
        submitted_at="2026-07-23T01:02:00Z",
    )
    assert result["outcome"] == "PENDING_HUMAN_REVIEW"
    assert result["human_review_required"] is True
    assert result["mastery_claimed"] is False


def test_listening_audio_and_speaking_recording_are_m10_compatible(tmp_path: Path) -> None:
    wav = tmp_path / "canary.wav"
    _wav(wav)

    listening, _, listening_db, _, _ = _initialize_runtime(tmp_path / "listening", "LISTENING")
    with sqlite3.connect(listening_db) as connection:
        connection.execute("CREATE TABLE m9_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        connection.execute("INSERT INTO m9_metadata VALUES('validation_status',?)", (m9.STATUS,))
        connection.commit()
    listening_consumer = tmp_path / "listening-consumer.json"
    listening_consumer.write_text(json.dumps(listening), encoding="utf-8")
    registry = m10.PrivateMediaRegistry(
        database_path=listening_db,
        consumer_path=listening_consumer,
        media_root=tmp_path / "listening-media",
    )
    registry.initialize()
    audio = registry.register_listening(
        asset_key=listening["cp07d_delivery_contract"]["listening_audio_asset_keys"][0],
        wav_path=wav,
        created_at="2026-07-23T01:03:00Z",
    )
    assert audio["validation_status"] == m10.STATUS

    speaking, speaking_session, speaking_db, _, speaking_store = _initialize_runtime(tmp_path / "speaking", "SPEAKING")
    speaking_key = speaking["cp07d_delivery_contract"]["speaking_recording_asset_keys"][0]
    attempt = speaking_store.capture_response(
        learner_id="learner-1",
        session_id=speaking_session["session_id"],
        asset_key=speaking_key,
        response="recording-submitted",
        expected_session_version=speaking_session["session_version"],
        submitted_at="2026-07-23T01:04:00Z",
    )
    with sqlite3.connect(speaking_db) as connection:
        connection.execute("CREATE TABLE m9_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        connection.execute("INSERT INTO m9_metadata VALUES('validation_status',?)", (m9.STATUS,))
        connection.commit()
    speaking_consumer = tmp_path / "speaking-consumer.json"
    speaking_consumer.write_text(json.dumps(speaking), encoding="utf-8")
    speaking_registry = m10.PrivateMediaRegistry(
        database_path=speaking_db,
        consumer_path=speaking_consumer,
        media_root=tmp_path / "speaking-media",
    )
    speaking_registry.initialize()
    recording = speaking_registry.register_recording(
        learner_id="learner-1",
        attempt_id=attempt["attempt_id"],
        wav_path=wav,
        consent_granted=True,
        created_at="2026-07-23T01:05:00Z",
    )
    assert recording["validation_status"] == m10.STATUS
    assert recording["automatic_score_written"] is False


def test_unresolved_cp05_lineage_and_a2_are_rejected() -> None:
    inputs = list(_inputs("READING"))
    inputs[2] = deepcopy(inputs[2])
    inputs[2]["unified_lesson_composition"]["composition_items"][0]["source_lineage"]["cp05_material_id"] = "UNKNOWN"
    with pytest.raises(builder.CP07DBuildError, match="source_identity_unresolved"):
        builder.build_private_delivery_consumer(*inputs)

    inputs = list(_inputs("READING"))
    inputs[2] = deepcopy(inputs[2])
    inputs[2]["selected_lesson"]["level"] = "A2"
    with pytest.raises(builder.CP07DBuildError, match="selected_lesson_scope_invalid"):
        builder.build_private_delivery_consumer(*inputs)
