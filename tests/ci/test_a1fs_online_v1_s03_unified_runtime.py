from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1_a1plus_shared_item_contract as m03
from ulga.builders import build_a1fs_online_v1_s02_first_nonaudio_unit_admission as s02
from ulga.builders import build_a1fs_online_v1_s03_unified_learner_runtime_integration as s03
from ulga.validators.validate_a1fs_online_v1_s03_unified_learner_runtime_integration import validate_outputs


GRAMMAR_ID = "GRAMMAR_ARTICLES_BASIC"
LEARNING_ID = "E4S_A1V1_UNIT:GRAMMAR_ARTICLES_BASIC"


def _item(skill: str, ordinal: int, mode: str, *, role: str = "practice") -> dict:
    item_id = f"E4S_A1V1_ITEM:{GRAMMAR_ID}:{skill}:{ordinal}"
    answer: dict = {
        "answer_mode": mode,
        "answer_status": "CANDIDATE_CONTRACT_AVAILABLE",
        "exact_text_match_required": mode in {"DETERMINISTIC_OPTION", "DETERMINISTIC_SEQUENCE"},
    }
    response: dict = {"response_mode": "short_text", "learner_input_required": True}
    required = ["learner_text_response"]
    if mode == "DETERMINISTIC_OPTION":
        answer["answer_key"] = {"accepted_texts": [f"choice-{ordinal}"]}
        answer["options"] = [f"choice-{ordinal}", f"distractor-{ordinal}"]
        response["response_mode"] = "select_one"
        response["options"] = list(answer["options"])
    elif mode == "DETERMINISTIC_SEQUENCE":
        answer["correct_token_sequence"] = ["a", f"word{ordinal}"]
        response["response_mode"] = "ordered_tokens"
        response["token_sequence"] = ["a", f"word{ordinal}"]
    elif mode == "DETERMINISTIC_NORMALIZED_TEXT":
        answer["answer_key"] = {"accepted_texts": [f"This is answer {ordinal}."]}
    else:
        required = ["grammar_feature_evaluation", "teacher_review_required"]
    prompt_text = (
        f"Say practice sentence {ordinal}."
        if skill == "speaking"
        else f"Complete {skill} item {ordinal}."
    )
    return {
        "shared_item_id": item_id,
        "source_item_id": f"SRC:{skill}:{ordinal}",
        "schema_version": m03.SCHEMA_VERSION,
        "learning_unit_id": LEARNING_ID,
        "grammar_unit_id": GRAMMAR_ID,
        "official_cefr_level": "A1",
        "internal_stage": "A1",
        "skill": skill,
        "item_role": role,
        "evidence_dimension": "controlled_practice",
        "task_type": "guided_response",
        "prompt_contract": {
            "prompt_text": prompt_text,
            "prompt_status": "PROJECT_AUTHORED_CANDIDATE",
        },
        "response_contract": response,
        "answer_contract": answer,
        "scoring_contract": {
            "scoring_mode": mode,
            "deterministic_candidate": mode != "FEATURE_RUBRIC_CANDIDATE",
            "real_skill_scoring_ready": mode != "FEATURE_RUBRIC_CANDIDATE",
            "human_review_fallback": mode == "FEATURE_RUBRIC_CANDIDATE",
            "required_evidence": required,
        },
        "media_contract": {
            "text_status": "AVAILABLE",
            "audio_required": skill == "speaking",
            "audio_status": "NOT_IMPLEMENTED" if skill == "speaking" else "NOT_REQUIRED",
            "transcript_required": skill == "speaking",
            "transcript_status": "NOT_COLLECTED" if skill == "speaking" else "NOT_REQUIRED",
            "learner_capture_required": skill == "speaking",
            "learner_capture_status": "NOT_IMPLEMENTED" if skill == "speaking" else "NOT_REQUIRED",
        },
        "content_binding": {
            "grammar_focus": [GRAMMAR_ID],
            "canonical_egp_row_ids": ["EGP_ARTICLES_1"],
            "coverage_mode": "DIRECT_CANONICAL_ROWS",
        },
        "source_trace": {
            "source_kind": "TEST",
            "source_artifact_id": "TEST",
            "source_builder_path": "tests/ci/test_a1fs_online_v1_s03_unified_runtime.py",
            "raw_external_source_text_copied": False,
        },
        "readiness": {
            "shared_item_contract_complete": True,
            "answer_contract_complete": True,
            "scoring_contract_complete": True,
            "media_contract_complete": True,
            "real_skill_delivery_complete": False,
            "actual_learner_evidence_complete": False,
        },
        "claim_boundaries": {
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "persistent_learner_state_write": False,
            "production_runtime_event": False,
            "a2_a2plus_in_scope": False,
        },
    }


def _sources() -> tuple[dict, dict]:
    selected: list[dict] = []
    modes = (
        "DETERMINISTIC_OPTION",
        "DETERMINISTIC_SEQUENCE",
        "DETERMINISTIC_NORMALIZED_TEXT",
        "FEATURE_RUBRIC_CANDIDATE",
    )
    for skill in ("reading", "writing"):
        selected.extend(_item(skill, index, mode) for index, mode in enumerate(modes, start=1))
    selected.extend(_item("speaking", index, "FEATURE_RUBRIC_CANDIDATE") for index in range(1, 4))
    selected_ids = {row["shared_item_id"] for row in selected}
    filler: list[dict] = []
    ordinal = 1
    while len(selected) + len(filler) < 384:
        row = _item("reading", 1000 + ordinal, "DETERMINISTIC_NORMALIZED_TEXT")
        row["shared_item_id"] = f"E4S_A1V1_ITEM:FILLER:{ordinal}"
        row["source_item_id"] = f"FILLER:{ordinal}"
        row["grammar_unit_id"] = f"GRAMMAR_FILLER_{ordinal:03d}"
        row["learning_unit_id"] = f"E4S_A1V1_UNIT:FILLER_{ordinal:03d}"
        filler.append(row)
        ordinal += 1
    items = selected + filler
    shared = {
        "task_id": m03.TASK_ID,
        "epic_id": m03.EPIC_ID,
        "artifact_id": m03.ARTIFACT_ID,
        "artifact_type": "a1_a1plus_shared_four_skill_item_contract",
        "schema_version": m03.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "coverage_summary": {
            "learning_unit_count": 24,
            "shared_item_count": 384,
        },
        "shared_items": items,
        "stop_reason": "NONE",
    }
    reading = sorted(row["shared_item_id"] for row in selected if row["skill"] == "reading")
    writing = sorted(row["shared_item_id"] for row in selected if row["skill"] == "writing")
    speaking = sorted(row["shared_item_id"] for row in selected if row["skill"] == "speaking")
    core = {
        "task_id": s02.TASK_ID,
        "program_id": s02.PROGRAM_ID,
        "schema_version": s02.SCHEMA_VERSION,
        "validation_status": s02.PASS_STATUS,
        "artifact_type": "first_production_unit_nonaudio_admission_package",
        "scope": "A1_A1_PLUS_ONLY",
        "release_profile": s02.RELEASE_PROFILE,
        "source_identity": {
            "cp01_task_id": "CP01",
            "cp01_sha256": "0" * 64,
            "cp04_task_id": "CP04",
            "cp04_sha256": "1" * 64,
            "m03_task_id": m03.TASK_ID,
            "m03_sha256": s02.digest(shared),
        },
        "selection_contract": {
            "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
            "eligibility": "PREREQUISITE_FREE_AND_READING_WRITING_SPEAKING_PRACTICE_AVAILABLE",
            "ranking": "HIGHEST_MINIMUM_LANE_COUNT_THEN_TOTAL_COUNT_THEN_SEQUENCE",
            "required_prelaunch_lanes": ["reading", "writing", "speaking"],
            "audio_deferred_lanes": ["listening", "speaking_assessment"],
            "new_unit_creation_allowed": False,
            "listening_without_playable_audio_allowed": False,
            "speaking_capture_or_scoring_claim_allowed": False,
        },
        "eligible_unit_count": 1,
        "selected_unit": {
            "learning_unit_id": LEARNING_ID,
            "grammar_unit_id": GRAMMAR_ID,
            "sequence_index": 1,
            "internal_stage": "A1",
            "canonical_egp_row_ids": ["EGP_ARTICLES_1"],
            "prerequisite_unit_ids": [],
            "selection_rank": 1,
            "availability_score": 30011,
            "admitted_lanes": {
                "reading": {
                    "item_ids": reading,
                    "item_count": 4,
                    "delivery_mode": "INTERACTIVE_TEXT_ITEM",
                    "evidence_policy": "EXISTING_DETERMINISTIC_OR_REVIEWED_SCORING_CONTRACT",
                    "admission_status": "ADMITTED_FOR_AUDIO_DEFERRED_ONLINE_RELEASE",
                },
                "writing": {
                    "item_ids": writing,
                    "item_count": 4,
                    "delivery_mode": "INTERACTIVE_TEXT_ITEM",
                    "evidence_policy": "EXISTING_DETERMINISTIC_OR_REVIEWED_SCORING_CONTRACT",
                    "admission_status": "ADMITTED_FOR_AUDIO_DEFERRED_ONLINE_RELEASE",
                },
                "speaking": {
                    "item_ids": speaking,
                    "item_count": 3,
                    "delivery_mode": "ORAL_PRACTICE_CARD_NO_CAPTURE",
                    "evidence_policy": "NO_SCORING_NO_MASTERY_EVIDENCE",
                    "admission_status": "ADMITTED_FOR_AUDIO_DEFERRED_ONLINE_RELEASE",
                },
            },
            "scene_candidate_ids": ["SCENE:1", "SCENE:2", "SCENE:3"],
            "deferred_lanes": {
                "listening": {
                    "status": "DEFERRED_POST_LAUNCH_AUDIO",
                    "reason": "PLAYABLE_AUDIO_REQUIRED_AND_NOT_IN_PRELAUNCH_SCOPE",
                    "item_ids": [],
                },
                "speaking_assessment": {
                    "status": "DEFERRED_POST_LAUNCH_AUDIO",
                    "reason": "RECORDING_TRANSCRIPT_AND_SCORING_NOT_IN_PRELAUNCH_SCOPE",
                    "item_ids": [],
                },
            },
            "unit_admission_status": "ADMITTED_NONAUDIO_FIRST_PRODUCTION_UNIT",
        },
        "admission_summary": {
            "admitted_unit_count": 1,
            "reading_item_count": 4,
            "writing_item_count": 4,
            "speaking_practice_card_count": 3,
            "listening_item_count": 0,
            "speaking_assessment_item_count": 0,
            "admitted_nonaudio_item_count": 11,
            "scene_candidate_count": 3,
        },
        "product_status": "INCOMPLETE_NOT_ONLINE_USABLE",
        "claim_boundaries": {
            "canonical_unit_identity_changed": False,
            "new_curriculum_created": False,
            "new_learner_content_authored": False,
            "listening_complete": False,
            "speaking_recording_complete": False,
            "speaking_assessment_evidence_claimed": False,
            "complete_four_skill_product_claimed": False,
            "online_usable_claimed": False,
            "learner_mastery_claimed": False,
            "retention_confirmed": False,
            "a2_a2plus_in_scope": False,
            "a2_unlocked": False,
        },
        "stop_reason": "NONE",
        "next_short_step": s02.NEXT_SHORT_STEP,
    }
    admitted = {**core, "artifact_sha256": s02.digest(core)}
    assert len(selected_ids) == 11
    return admitted, shared


def test_build_runtime_consumer_preserves_s02_item_identity_and_audio_lock() -> None:
    admitted, shared = _sources()
    consumer = s03.build_runtime_consumer(admitted, shared)
    assert consumer["task_id"] == s03.m2.TASK_ID
    assert consumer["validation_status"] == s03.m2.STATUS
    assert consumer["counts"] == {
        "asset_record_count": 11,
        "lesson_count": 3,
        "learning_lesson_count": 3,
        "a2_handoff_lesson_count": 0,
    }
    assert {row["skill"] for row in consumer["lesson_catalog"]} == {"READING", "WRITING", "SPEAKING"}
    assert all(row["skill"] != "LISTENING" for row in consumer["asset_records"])
    speaking = [row for row in consumer["asset_records"] if row["skill"] == "SPEAKING"]
    assert len(speaking) == 3
    assert all(row["payload"]["response_capture_enabled"] is False for row in speaking)
    assert all(row["payload"]["recording_capture_required"] is False for row in speaking)


def test_materializes_existing_m3_m5_m6_runtime_and_independent_validation(tmp_path: Path) -> None:
    admitted, shared = _sources()
    receipt, safe = s03.materialize_runtime(
        s02_artifact=admitted,
        m03_artifact=shared,
        output_root=tmp_path,
    )
    report = validate_outputs(
        receipt=receipt,
        safe_report=safe,
        output_root=tmp_path,
        s02_artifact=admitted,
        m03_artifact=shared,
    )
    assert report["error_count"] == 0, report["errors"]
    assert receipt["runtime_summary"] == {
        "runtime_lesson_count": 3,
        "runtime_asset_count": 11,
        "m3_profile_count": 1,
        "m3_session_count": 3,
        "m3_completed_session_count": 3,
        "m3_exposure_event_count": 11,
        "m5_renderer_bundle_count": 3,
        "m6_response_contract_count": 11,
        "m6_capture_enabled_contract_count": 8,
        "speaking_capture_enabled_count": 0,
        "listening_runtime_item_count": 0,
        "audio_runtime_asset_count": 0,
    }
    assert safe["product_status"] == "PRIVATE_RUNTIME_CONNECTED_NOT_PUBLIC_ONLINE"


def test_rejects_any_listening_admission() -> None:
    admitted, shared = _sources()
    tampered = copy.deepcopy(admitted)
    tampered["admission_summary"]["listening_item_count"] = 1
    core = {key: value for key, value in tampered.items() if key != "artifact_sha256"}
    tampered["artifact_sha256"] = s02.digest(core)
    with pytest.raises(s03.RuntimeIntegrationError, match="s02_listening_count_not_zero"):
        s03.build_runtime_consumer(tampered, shared)


def test_rejects_speaking_assessment_from_display_only_lane() -> None:
    admitted, shared = _sources()
    speaking_id = admitted["selected_unit"]["admitted_lanes"]["speaking"]["item_ids"][0]
    item = next(row for row in shared["shared_items"] if row["shared_item_id"] == speaking_id)
    item["item_role"] = "assessment"
    with pytest.raises(s03.RuntimeIntegrationError, match="speaking_assessment_not_allowed"):
        s03.build_runtime_consumer(admitted, shared)


def test_validator_rejects_actual_response_attempt_in_s03_canary(tmp_path: Path) -> None:
    admitted, shared = _sources()
    receipt, safe = s03.materialize_runtime(
        s02_artifact=admitted,
        m03_artifact=shared,
        output_root=tmp_path,
    )
    database = Path(receipt["runtime_outputs"]["database_path"])
    with sqlite3.connect(database) as connection:
        contract = connection.execute(
            "SELECT asset_key FROM response_contracts WHERE capture_enabled=1 ORDER BY asset_key LIMIT 1"
        ).fetchone()[0]
        session = connection.execute(
            "SELECT session_id,learner_id,lesson_id FROM learning_sessions WHERE skill='READING'"
        ).fetchone()
        connection.execute(
            "INSERT INTO response_attempts VALUES(?,?,?,?,?,?,?,?,?)",
            (
                "ATTEMPT_INJECTED",
                session[1],
                session[0],
                session[2],
                contract,
                1,
                json.dumps("x"),
                "2026-01-01T01:00:00Z",
                "0" * 64,
            ),
        )
        connection.commit()
    report = validate_outputs(
        receipt=receipt,
        safe_report=safe,
        output_root=tmp_path,
        s02_artifact=admitted,
        m03_artifact=shared,
    )
    assert "runtime_database_count_invalid:response_attempt_count:1:0" in report["errors"]


def test_safe_report_contains_no_private_item_or_scoring_content(tmp_path: Path) -> None:
    admitted, shared = _sources()
    _, safe = s03.materialize_runtime(
        s02_artifact=admitted,
        m03_artifact=shared,
        output_root=tmp_path,
    )
    rendered = json.dumps(safe, ensure_ascii=False)
    for token in (
        "E4S_A1V1_ITEM:",
        "accepted_texts",
        "private_scoring_contract",
        "answer_contract",
        "prompt_text",
        "choice-1",
    ):
        assert token not in rendered


def test_rebuild_is_deterministic_at_safe_readback_level(tmp_path: Path) -> None:
    admitted, shared = _sources()
    receipt1, safe1 = s03.materialize_runtime(
        s02_artifact=admitted,
        m03_artifact=shared,
        output_root=tmp_path,
    )
    receipt2, safe2 = s03.materialize_runtime(
        s02_artifact=admitted,
        m03_artifact=shared,
        output_root=tmp_path,
    )
    assert safe1 == safe2
    assert receipt1["artifact_sha256"] == receipt2["artifact_sha256"]
