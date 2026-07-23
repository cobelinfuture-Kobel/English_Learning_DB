from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import wave

import pytest

from ulga.builders import build_a1fs_v1_cp07r4_reference_aware_private_delivery_consumer as r4
from ulga.builders import build_a1fs_v1_cp07r4a_ket_asset_response_media_capability_admission as builder
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4
from ulga.builders import build_a1fs_v1_m5_four_skill_renderer_learner_ui as m5
from ulga.builders import build_a1fs_v1_m6_response_capture_scoring_m12_evidence as m6
from ulga.builders import build_a1fs_v1_m9_teacher_dashboard_progress_reporting_export as m9
from ulga.builders import build_a1fs_v1_m10_listening_audio_speaking_recording_integration as m10
from ulga.builders import cp07d_private_four_skill_delivery_consumer_impl as cp07d
from ulga.validators import validate_a1fs_v1_cp07r4a_ket_asset_response_media_capability_admission as validator


BASE_ROLE = {
    "LISTENING": "GDT",
    "SPEAKING": "MOD",
    "READING": "TXT",
    "WRITING": "MOD",
}


def _asset(asset_key: str, lesson_id: str, skill: str, role: str, payload: dict) -> dict:
    return {
        "asset_id": asset_key,
        "asset_key": asset_key,
        "lesson_id": lesson_id,
        "skill": skill,
        "level": "A1",
        "role": role,
        "payload": payload,
        "content_digest": cp07d._digest(payload),
        "release_scope": "PRIVATE_INTERNAL_D0",
    }


def _r4_consumer(skill: str, *, include_response: bool = True) -> dict:
    lesson_id = f"{skill[:1]}-A1"
    assets = [
        _asset(
            f"KET:{skill}:BASE",
            lesson_id,
            skill,
            BASE_ROLE[skill],
            {"learner_instruction": f"Private KET {skill.lower()} base asset."},
        )
    ]
    if skill == "LISTENING":
        assets.append(
            _asset(
                "KET:LISTENING:AUD",
                lesson_id,
                skill,
                "AUD",
                {"learner_instruction": "Play registered private audio."},
            )
        )
        if include_response:
            assets.append(
                _asset(
                    "KET:LISTENING:CHK",
                    lesson_id,
                    skill,
                    "CHK",
                    {"question": "Which option did you hear?", "accepted_texts": ["A"]},
                )
            )
    elif skill == "SPEAKING" and include_response:
        assets.append(
            _asset(
                "KET:SPEAKING:PRD",
                lesson_id,
                skill,
                "PRD",
                {
                    "prompt": "Give a short spoken response.",
                    "scoring_rubric": {
                        "target_language_use": {"required": True},
                        "intelligibility": {"required": True},
                    },
                },
            )
        )
    elif skill == "READING" and include_response:
        assets.append(
            _asset(
                "KET:READING:CHK",
                lesson_id,
                skill,
                "CHK",
                {"question": "Choose the correct answer.", "accepted_texts": ["yes"]},
            )
        )
    elif skill == "WRITING" and include_response:
        assets.append(
            _asset(
                "KET:WRITING:PRD",
                lesson_id,
                skill,
                "PRD",
                {
                    "prompt": "Write one short answer.",
                    "scoring_rubric": {
                        "task_completion": {"required": True},
                        "target_language_use": {"required": True},
                    },
                },
            )
        )

    keys = [row["asset_key"] for row in assets]
    roles = sorted({row["role"] for row in assets})
    consumer = {
        "task_id": m2.TASK_ID,
        "schema_version": m2.SCHEMA_VERSION,
        "validation_status": m2.STATUS,
        "source_graph_sha256": "1" * 64,
        "asset_records": assets,
        "lesson_catalog": [
            {
                "lesson_id": lesson_id,
                "lesson_node_id": f"LESSON:{skill}:{lesson_id}",
                "skill": skill,
                "level": "A1",
                "asset_keys": keys,
                "roles": roles,
                "requirement_node_ids": [] if skill == "LISTENING" else [f"REF:{skill}:A1"],
                "release_scope": "PRIVATE_INTERNAL_D0",
            }
        ],
        "counts": {
            "asset_record_count": len(assets),
            "lesson_count": 1,
            "learning_lesson_count": 1,
            "a2_handoff_lesson_count": 0,
            "cp07r4_mounted_ket_asset_count": len(assets),
            "cp07d_projected_asset_count": 0,
            "cp07d_projection_artifact_count": 0,
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
        "cp07r4_task_id": r4.TASK_ID,
        "cp07r4_schema_version": r4.SCHEMA_VERSION,
        "cp07r4_validation_status": r4.PASS_STATUS,
        "cp07d_task_id": cp07d.TASK_ID,
        "cp07d_schema_version": cp07d.SCHEMA_VERSION,
        "cp07d_validation_status": cp07d.PASS_STATUS,
        "cp07d_projection_artifacts": [],
        "cp07d_delivery_contract": {
            "selected_lesson_id": lesson_id,
            "selected_skill": skill,
            "selected_level": "A1",
            "delivery_mode": "KET_ASSET_BODY_ONLY",
            "composition_mode": "KET_ONLY_NO_EXACT_KET99_REFERENCE",
            "mounted_ket_asset_keys": keys,
            "projected_context_asset_keys": [],
            "projected_asset_keys": [],
            "mounted_role_counts": {role: roles.count(role) for role in roles},
            "response_capture_asset_keys": [],
            "listening_audio_asset_keys": [],
            "speaking_recording_asset_keys": [],
            "ket99_instructional_reference_count": 0,
            "m3_session_compatible": True,
            "m5_private_renderer_compatible": True,
            "m6_feature_rubric_compatible": False,
            "m10_private_media_registration_compatible": False,
            "missing_reference_blocks_delivery": False,
            "optional_context_projection_required": False,
            "real_attempt_completed": False,
            "real_media_registered": False,
            "a2_payload_included": False,
        },
        "cp07r4_capability_gaps": {
            "response_capture_contract_missing": True,
            "listening_audio_registration_contract_missing": skill == "LISTENING",
            "speaking_recording_contract_missing": skill == "SPEAKING",
            "optional_context_not_projected": True,
        },
        "cp07d_claim_boundaries": {
            "real_learner_attempt_claimed": False,
            "real_listening_audio_claimed": False,
            "real_speaking_recording_claimed": False,
            "automatic_speaking_score_claimed": False,
            "mastery_or_retention_claimed": False,
            "public_delivery_claimed": False,
            "a2_a2plus_in_scope": False,
        },
        "cp07d_errors": [],
        "cp07d_stop_reason": "NONE",
    }
    return consumer


def _plan(consumer: dict) -> dict:
    lesson = consumer["lesson_catalog"][0]
    return {
        "task_id": m4.TASK_ID,
        "schema_version": m4.SCHEMA_VERSION,
        "validation_status": m4.STATUS,
        "plan_id": f"plan-{lesson['skill'].lower()}",
        "learner_id": "learner-1",
        "plan_status": "PLAN_LEARNING_LESSON",
        "selected_lesson": {
            "lesson_id": lesson["lesson_id"],
            "lesson_node_id": lesson["lesson_node_id"],
            "skill": lesson["skill"],
            "level": lesson["level"],
            "roles": lesson["roles"],
            "requirement_node_ids": lesson["requirement_node_ids"],
        },
        "a2_lock": {
            "a2_payload_access_granted": False,
            "a2_session_start_granted": False,
        },
        "a2_payload_included": False,
        "a2_session_started": False,
        "errors": [],
        "stop_reason": "NONE",
    }


def _write_runtime(tmp_path: Path, artifact: dict) -> tuple[Path, Path, Path, dict]:
    consumer_path = tmp_path / "consumer.json"
    plan_path = tmp_path / "plan.json"
    ui_root = tmp_path / "ui"
    database = tmp_path / "state.sqlite3"
    plan = _plan(artifact)
    consumer_path.write_text(json.dumps(artifact), encoding="utf-8")
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    state = m3.LearnerStateStore(database)
    result = state.initialize(consumer_path)
    assert result["validation_status"] == m3.STATUS
    state.create_profile(
        learner_id="learner-1",
        display_label="Learner One",
        at="2026-07-23T01:00:00Z",
    )
    session = state.start_session(
        learner_id="learner-1",
        lesson_id=artifact["cp07d_delivery_contract"]["selected_lesson_id"],
        session_id="session-1",
        at="2026-07-23T01:01:00Z",
    )
    manifest = m5.build_ui(
        consumer_path=consumer_path,
        plan_path=plan_path,
        output_root=ui_root,
    )
    assert manifest["validation_status"] == m5.STATUS
    response_store = m6.ResponseEvidenceStore(database)
    initialized = response_store.initialize(
        consumer_path=consumer_path,
        lesson_bundle_path=ui_root / "lesson.private.json",
    )
    return consumer_path, database, ui_root, {"state": state, "session": session, "store": response_store, "m6": initialized}


def _wav(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = b"\x00\x00" * 2400
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(frames)


@pytest.mark.parametrize(
    ("skill", "expected_response", "expected_audio", "expected_recording"),
    [
        ("LISTENING", 1, 1, 0),
        ("SPEAKING", 1, 0, 1),
        ("READING", 1, 0, 0),
        ("WRITING", 1, 0, 0),
    ],
)
def test_admission_uses_existing_m6_and_m10_contracts(
    skill: str,
    expected_response: int,
    expected_audio: int,
    expected_recording: int,
) -> None:
    source = _r4_consumer(skill)
    artifact = builder.build_capability_admission(source)
    report = validator.validate_artifact(artifact, r4_consumer=source)
    contract = artifact["cp07d_delivery_contract"]
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert report["deterministic_rebuild_matches"] is True
    assert len(contract["response_capture_asset_keys"]) == expected_response
    assert len(contract["listening_audio_asset_keys"]) == expected_audio
    assert len(contract["speaking_recording_asset_keys"]) == expected_recording
    assert artifact["asset_records"] == source["asset_records"]
    assert artifact["lesson_catalog"] == source["lesson_catalog"]
    assert artifact["cp07r4a_capability_admission"]["actual_attempt_count"] == 0
    assert artifact["cp07r4a_capability_admission"]["actual_media_registration_count"] == 0


def test_missing_explicit_response_evidence_remains_a_gap() -> None:
    source = _r4_consumer("READING", include_response=False)
    artifact = builder.build_capability_admission(source)
    report = validator.validate_artifact(artifact, r4_consumer=source)
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert artifact["cp07d_delivery_contract"]["response_capture_asset_keys"] == []
    assert artifact["cp07r4_capability_gaps"]["response_capture_contract_missing"] is True


@pytest.mark.parametrize("skill", ["LISTENING", "SPEAKING", "READING", "WRITING"])
def test_m6_initializes_and_captures_admitted_ket_response(tmp_path: Path, skill: str) -> None:
    artifact = builder.build_capability_admission(_r4_consumer(skill))
    _, _, _, runtime = _write_runtime(tmp_path, artifact)
    assert runtime["m6"]["capture_contract_count"] == 1
    asset_key = artifact["cp07d_delivery_contract"]["response_capture_asset_keys"][0]
    response = "A" if skill == "LISTENING" else "yes" if skill == "READING" else "A learner response"
    result = runtime["store"].capture_response(
        learner_id="learner-1",
        session_id=runtime["session"]["session_id"],
        asset_key=asset_key,
        response=response,
        expected_session_version=runtime["session"]["session_version"],
        submitted_at="2026-07-23T01:02:00Z",
    )
    expected = "AUTO_PASS" if skill in {"LISTENING", "READING"} else "PENDING_HUMAN_REVIEW"
    assert result["outcome"] == expected
    assert result["mastery_claimed"] is False


def test_listening_audio_admission_is_m10_registerable(tmp_path: Path) -> None:
    artifact = builder.build_capability_admission(_r4_consumer("LISTENING"))
    consumer_path, database, _, _ = _write_runtime(tmp_path, artifact)
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE m9_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        connection.execute("INSERT INTO m9_metadata VALUES('validation_status',?)", (m9.STATUS,))
        connection.commit()
    registry = m10.PrivateMediaRegistry(
        database_path=database,
        consumer_path=consumer_path,
        media_root=tmp_path / "media",
    )
    assert registry.initialize()["validation_status"] == m10.STATUS
    wav = tmp_path / "audio.wav"
    _wav(wav)
    result = registry.register_listening(
        asset_key=artifact["cp07d_delivery_contract"]["listening_audio_asset_keys"][0],
        wav_path=wav,
        created_at="2026-07-23T01:03:00Z",
    )
    assert result["validation_status"] == m10.STATUS


def test_speaking_recording_admission_is_m10_registerable_after_human_review_attempt(tmp_path: Path) -> None:
    artifact = builder.build_capability_admission(_r4_consumer("SPEAKING"))
    consumer_path, database, _, runtime = _write_runtime(tmp_path, artifact)
    asset_key = artifact["cp07d_delivery_contract"]["speaking_recording_asset_keys"][0]
    attempt = runtime["store"].capture_response(
        learner_id="learner-1",
        session_id=runtime["session"]["session_id"],
        asset_key=asset_key,
        response="A spoken answer",
        expected_session_version=runtime["session"]["session_version"],
        submitted_at="2026-07-23T01:02:00Z",
    )
    assert attempt["outcome"] == "PENDING_HUMAN_REVIEW"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE m9_metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL)")
        connection.execute("INSERT INTO m9_metadata VALUES('validation_status',?)", (m9.STATUS,))
        connection.commit()
    registry = m10.PrivateMediaRegistry(
        database_path=database,
        consumer_path=consumer_path,
        media_root=tmp_path / "media",
    )
    assert registry.initialize()["validation_status"] == m10.STATUS
    wav = tmp_path / "recording.wav"
    _wav(wav)
    result = registry.register_recording(
        learner_id="learner-1",
        attempt_id=attempt["attempt_id"],
        wav_path=wav,
        consent_granted=True,
        created_at="2026-07-23T01:03:00Z",
    )
    assert result["validation_status"] == m10.STATUS
    assert result["automatic_score_written"] is False


def test_validator_rejects_asset_payload_mutation() -> None:
    source = _r4_consumer("WRITING")
    artifact = builder.build_capability_admission(source)
    tampered = deepcopy(artifact)
    tampered["asset_records"][0]["payload"]["learner_instruction"] = "Changed"
    report = validator.validate_artifact(tampered, r4_consumer=source)
    assert report["validation_status"] != builder.PASS_STATUS
    assert "asset_records_mutated" in report["errors"]
