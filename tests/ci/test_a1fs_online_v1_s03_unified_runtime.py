from __future__ import annotations

import copy
import json
import sqlite3
from pathlib import Path

import pytest

from ulga.builders import build_a1_a1plus_shared_item_contract as m03
from ulga.builders import build_a1fs_online_v1_s02_first_nonaudio_unit_admission as s02
from ulga.builders import build_a1fs_online_v1_s03_unified_learner_runtime as s03
from ulga.validators.validate_a1fs_online_v1_s03_unified_learner_runtime_integration import validate_outputs

GRAMMAR = "GRAMMAR_ARTICLES_BASIC"
UNIT = "E4S_A1V1_UNIT:GRAMMAR_ARTICLES_BASIC"
MODES = (
    "DETERMINISTIC_OPTION",
    "DETERMINISTIC_SEQUENCE",
    "DETERMINISTIC_NORMALIZED_TEXT",
    "FEATURE_RUBRIC_CANDIDATE",
)


def item(skill: str, number: int, mode: str, *, item_id: str | None = None) -> dict:
    shared_id = item_id or f"E4S_A1V1_ITEM:{GRAMMAR}:{skill}:{number}"
    answer: dict = {"answer_mode": mode, "answer_status": "CANDIDATE_CONTRACT_AVAILABLE"}
    response: dict = {"response_mode": "short_text", "learner_input_required": True}
    evidence = ["learner_text_response"]
    if mode == "DETERMINISTIC_OPTION":
        answer.update(answer_key={"accepted_texts": [f"choice-{number}"]}, options=[f"choice-{number}", "other"])
        response.update(response_mode="select_one", options=list(answer["options"]))
    elif mode == "DETERMINISTIC_SEQUENCE":
        answer["correct_token_sequence"] = ["a", f"word{number}"]
        response.update(response_mode="ordered_tokens", token_sequence=["a", f"word{number}"])
    elif mode == "DETERMINISTIC_NORMALIZED_TEXT":
        answer["answer_key"] = {"accepted_texts": [f"This is answer {number}."]}
    else:
        evidence = ["grammar_feature_evaluation", "teacher_review_required"]
    return {
        "shared_item_id": shared_id,
        "source_item_id": f"SRC:{shared_id}",
        "schema_version": m03.SCHEMA_VERSION,
        "learning_unit_id": UNIT,
        "grammar_unit_id": GRAMMAR,
        "official_cefr_level": "A1",
        "internal_stage": "A1",
        "skill": skill,
        "item_role": "practice",
        "evidence_dimension": "controlled_practice",
        "task_type": "guided_response",
        "prompt_contract": {
            "prompt_text": f"Complete {skill} item {number}.",
            "prompt_status": "PROJECT_AUTHORED_CANDIDATE",
        },
        "response_contract": response,
        "answer_contract": answer,
        "scoring_contract": {
            "scoring_mode": mode,
            "deterministic_candidate": mode != "FEATURE_RUBRIC_CANDIDATE",
            "real_skill_scoring_ready": mode != "FEATURE_RUBRIC_CANDIDATE",
            "human_review_fallback": mode == "FEATURE_RUBRIC_CANDIDATE",
            "required_evidence": evidence,
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
            "grammar_focus": [GRAMMAR],
            "canonical_egp_row_ids": ["EGP_ARTICLES_1"],
            "coverage_mode": "DIRECT_CANONICAL_ROWS",
        },
        "source_trace": {"source_kind": "TEST", "raw_external_source_text_copied": False},
        "readiness": {
            "shared_item_contract_complete": True,
            "answer_contract_complete": True,
            "scoring_contract_complete": True,
            "media_contract_complete": True,
        },
        "claim_boundaries": {"learner_mastery_claimed": False, "a2_a2plus_in_scope": False},
    }


def sources() -> tuple[dict, dict]:
    selected = [item(skill, n, mode) for skill in ("reading", "writing") for n, mode in enumerate(MODES, 1)]
    selected += [item("speaking", n, "FEATURE_RUBRIC_CANDIDATE") for n in range(1, 4)]
    filler = []
    for n in range(1, 384 - len(selected) + 1):
        row = item("reading", 1000 + n, "DETERMINISTIC_NORMALIZED_TEXT", item_id=f"E4S_A1V1_ITEM:FILLER:{n}")
        row["source_item_id"] = f"FILLER:{n}"
        row["grammar_unit_id"] = f"GRAMMAR_FILLER_{n:03d}"
        row["learning_unit_id"] = f"E4S_A1V1_UNIT:FILLER_{n:03d}"
        filler.append(row)
    shared = {
        "task_id": m03.TASK_ID,
        "epic_id": m03.EPIC_ID,
        "artifact_id": m03.ARTIFACT_ID,
        "schema_version": m03.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "coverage_summary": {"learning_unit_count": 24, "shared_item_count": 384},
        "shared_items": selected + filler,
        "stop_reason": "NONE",
    }
    by_skill = {
        skill: sorted(row["shared_item_id"] for row in selected if row["skill"] == skill)
        for skill in ("reading", "writing", "speaking")
    }
    lane = lambda skill, mode, policy: {
        "item_ids": by_skill[skill], "item_count": len(by_skill[skill]),
        "delivery_mode": mode, "evidence_policy": policy,
        "admission_status": "ADMITTED_FOR_AUDIO_DEFERRED_ONLINE_RELEASE",
    }
    core = {
        "task_id": s02.TASK_ID,
        "program_id": s02.PROGRAM_ID,
        "schema_version": s02.SCHEMA_VERSION,
        "validation_status": s02.PASS_STATUS,
        "artifact_type": "first_production_unit_nonaudio_admission_package",
        "scope": "A1_A1_PLUS_ONLY",
        "release_profile": s02.RELEASE_PROFILE,
        "selection_contract": {
            "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
            "new_unit_creation_allowed": False,
            "listening_without_playable_audio_allowed": False,
            "speaking_capture_or_scoring_claim_allowed": False,
        },
        "selected_unit": {
            "learning_unit_id": UNIT,
            "grammar_unit_id": GRAMMAR,
            "sequence_index": 1,
            "internal_stage": "A1",
            "canonical_egp_row_ids": ["EGP_ARTICLES_1"],
            "prerequisite_unit_ids": [],
            "admitted_lanes": {
                "reading": lane("reading", "INTERACTIVE_TEXT_ITEM", "EXISTING_DETERMINISTIC_OR_REVIEWED_SCORING_CONTRACT"),
                "writing": lane("writing", "INTERACTIVE_TEXT_ITEM", "EXISTING_DETERMINISTIC_OR_REVIEWED_SCORING_CONTRACT"),
                "speaking": lane("speaking", "ORAL_PRACTICE_CARD_NO_CAPTURE", "NO_SCORING_NO_MASTERY_EVIDENCE"),
            },
            "scene_candidate_ids": ["SCENE:1", "SCENE:2", "SCENE:3"],
            "deferred_lanes": {
                "listening": {"status": "DEFERRED_POST_LAUNCH_AUDIO", "item_ids": []},
                "speaking_assessment": {"status": "DEFERRED_POST_LAUNCH_AUDIO", "item_ids": []},
            },
            "unit_admission_status": "ADMITTED_NONAUDIO_FIRST_PRODUCTION_UNIT",
        },
        "admission_summary": {
            "admitted_unit_count": 1, "reading_item_count": 4, "writing_item_count": 4,
            "speaking_practice_card_count": 3, "listening_item_count": 0,
            "speaking_assessment_item_count": 0, "admitted_nonaudio_item_count": 11,
            "scene_candidate_count": 3,
        },
        "product_status": "INCOMPLETE_NOT_ONLINE_USABLE",
        "stop_reason": "NONE",
        "next_short_step": s02.NEXT_SHORT_STEP,
    }
    return {**core, "artifact_sha256": s02.digest(core)}, shared


def materialized(tmp_path: Path) -> tuple[dict, dict, dict, dict]:
    admitted, shared = sources()
    receipt, safe = s03.materialize_runtime(s02_artifact=admitted, m03_artifact=shared, output_root=tmp_path)
    report = validate_outputs(
        receipt=receipt, safe_report=safe, output_root=tmp_path,
        s02_artifact=admitted, m03_artifact=shared,
    )
    return admitted, shared, receipt, safe | {"_validation": report}


def test_projects_exact_s02_identity_without_listening_or_speaking_capture() -> None:
    admitted, shared = sources()
    consumer = s03.build_runtime_consumer(admitted, shared)
    assert consumer["counts"]["asset_record_count"] == 11
    assert {row["skill"] for row in consumer["lesson_catalog"]} == {"READING", "WRITING", "SPEAKING"}
    assert not any(row["skill"] == "LISTENING" for row in consumer["asset_records"])
    speaking = [row for row in consumer["asset_records"] if row["skill"] == "SPEAKING"]
    assert len(speaking) == 3
    assert all(row["payload"]["response_capture_enabled"] is False for row in speaking)
    assert all(row["payload"]["recording_capture_required"] is False for row in speaking)


def test_materializes_existing_m3_m5_m6_runtime_and_validates(tmp_path: Path) -> None:
    _, _, receipt, result = materialized(tmp_path)
    assert result["_validation"]["error_count"] == 0, result["_validation"]["errors"]
    assert receipt["runtime_summary"] == {
        "runtime_lesson_count": 3, "runtime_asset_count": 11,
        "m3_profile_count": 1, "m3_session_count": 3, "m3_completed_session_count": 3,
        "m3_exposure_event_count": 11, "m5_renderer_bundle_count": 3,
        "m6_response_contract_count": 11, "m6_capture_enabled_contract_count": 8,
        "speaking_capture_enabled_count": 0, "listening_runtime_item_count": 0,
        "audio_runtime_asset_count": 0,
    }


def test_m5_learner_bundles_do_not_disclose_private_scoring_answers(tmp_path: Path) -> None:
    materialized(tmp_path)
    for skill in ("reading", "writing", "speaking"):
        rendered = (tmp_path / "runtime/ui" / skill / "lesson.private.json").read_text(encoding="utf-8")
        for token in ("private_scoring_contract", "answer_contract", "accepted_texts", "accepted_sequence", "choice-1", "This is answer"):
            assert token not in rendered


def test_rejects_listening_admission_and_speaking_assessment() -> None:
    admitted, shared = sources()
    listening = copy.deepcopy(admitted)
    listening["admission_summary"]["listening_item_count"] = 1
    core = {key: value for key, value in listening.items() if key != "artifact_sha256"}
    listening["artifact_sha256"] = s02.digest(core)
    with pytest.raises(s03.RuntimeIntegrationError, match="s02_listening_count_not_zero"):
        s03.build_runtime_consumer(listening, shared)
    speaking_id = admitted["selected_unit"]["admitted_lanes"]["speaking"]["item_ids"][0]
    next(row for row in shared["shared_items"] if row["shared_item_id"] == speaking_id)["item_role"] = "assessment"
    with pytest.raises(s03.RuntimeIntegrationError, match="speaking_assessment_not_allowed"):
        s03.build_runtime_consumer(admitted, shared)


def test_validator_rejects_response_attempt_during_connection_canary(tmp_path: Path) -> None:
    admitted, shared, receipt, result = materialized(tmp_path)
    database = Path(receipt["runtime_outputs"]["database_path"])
    with sqlite3.connect(database) as connection:
        asset_key = connection.execute("SELECT asset_key FROM response_contracts WHERE capture_enabled=1 LIMIT 1").fetchone()[0]
        session_id, learner_id, lesson_id = connection.execute(
            "SELECT session_id,learner_id,lesson_id FROM learning_sessions WHERE skill='READING'"
        ).fetchone()
        connection.execute(
            "INSERT INTO response_attempts VALUES(?,?,?,?,?,?,?,?,?,?)",
            ("ATTEMPT", learner_id, session_id, lesson_id, asset_key, 1, '"x"',
             "2026-01-01T01:00:00Z", "0" * 64, "1" * 64),
        )
        connection.commit()
    report = validate_outputs(
        receipt=receipt, safe_report={key: value for key, value in result.items() if key != "_validation"},
        output_root=tmp_path, s02_artifact=admitted, m03_artifact=shared,
    )
    assert "runtime_database_count_invalid:response_attempt_count:1:0" in report["errors"]


def test_safe_readback_is_private_content_free_and_deterministic(tmp_path: Path) -> None:
    admitted, shared = sources()
    receipt1, safe1 = s03.materialize_runtime(s02_artifact=admitted, m03_artifact=shared, output_root=tmp_path)
    receipt2, safe2 = s03.materialize_runtime(s02_artifact=admitted, m03_artifact=shared, output_root=tmp_path)
    rendered = json.dumps(safe1, ensure_ascii=False)
    assert "E4S_A1V1_ITEM:" not in rendered
    assert "accepted_texts" not in rendered
    assert safe1 == safe2
    assert receipt1["artifact_sha256"] == receipt2["artifact_sha256"]
