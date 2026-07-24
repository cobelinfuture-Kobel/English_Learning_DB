from __future__ import annotations

import copy
import json
from pathlib import Path

from ulga.builders import build_ket99_pku_evidence_reference_learning_value_evaluation as builder
from ulga.validators import validate_ket99_pku_evidence_reference_learning_value_evaluation as validator


def consumer() -> dict:
    return {
        "task_id": builder.M2_TASK,
        "schema_version": builder.M2_SCHEMA,
        "validation_status": builder.M2_STATUS,
        "asset_records": [
            {
                "asset_id": "A1", "asset_key": "A1", "lesson_id": "L1",
                "skill": "READING", "level": "A1+", "role": "CHK",
                "payload": {
                    "diagnostic_route": "repair detail relationship confusion",
                    "expected_evidence": "locate evidence",
                },
                "content_digest": "d1",
            },
            {
                "asset_id": "A2", "asset_key": "A2", "lesson_id": "L1",
                "skill": "READING", "level": "A1+", "role": "EVD",
                "payload": {"acceptance_rule": "answer with evidence"},
                "content_digest": "d2",
            },
            {
                "asset_id": "B1", "asset_key": "B1", "lesson_id": "L2",
                "skill": "READING", "level": "A1+", "role": "CTX",
                "payload": {"body": "short text"}, "content_digest": "d3",
            },
            {
                "asset_id": "C1", "asset_key": "C1", "lesson_id": "L3",
                "skill": "WRITING", "level": "A1", "role": "PRD",
                "payload": {
                    "teacher_delivery": "model adjective sentence",
                    "diagnostic_route": "contrast adjective form",
                },
                "content_digest": "d4",
            },
        ],
        "lesson_catalog": [
            {
                "lesson_id": "L1", "lesson_node_id": "LESSON:READING:L1",
                "skill": "READING", "level": "A1+", "asset_keys": ["A1", "A2"],
                "roles": ["CHK", "EVD"], "requirement_node_ids": [],
            },
            {
                "lesson_id": "L2", "lesson_node_id": "LESSON:READING:L2",
                "skill": "READING", "level": "A1+", "asset_keys": ["B1"],
                "roles": ["CTX"], "requirement_node_ids": [],
            },
            {
                "lesson_id": "L3", "lesson_node_id": "LESSON:WRITING:L3",
                "skill": "WRITING", "level": "A1", "asset_keys": ["C1"],
                "roles": ["PRD"],
                "requirement_node_ids": ["REF:WRITING:GRAMMAR_ADJECTIVE_PHRASES_A1"],
            },
        ],
        "counts": {
            "asset_record_count": 4, "lesson_count": 3,
            "learning_lesson_count": 3, "a2_handoff_lesson_count": 0,
        },
        "access_contract": {"a2_payload_query_allowed": False},
        "errors": [],
    }


def bridge() -> dict:
    return {
        "task_id": builder.BRIDGE_TASK,
        "validation_status": builder.BRIDGE_STATUS,
        "teaching_need_field_order": [
            "teaching_need_id", "pedagogical_concept_id", "level_scope",
            "skill_scope", "knowledge_mode", "knowledge_type",
            "teaching_roles", "source_pku_id",
        ],
        "teaching_need_registry": [
            [
                "TEACHING_NEED:READING.ERROR_DETAIL_RELATIONSHIP_CONFUSION",
                "READING.ERROR_DETAIL_RELATIONSHIP_CONFUSION", ["A1+"],
                ["READING"], "ERROR_REPAIR", "ERROR_PATTERN",
                ["ERROR_REPAIR", "REMEDIATION"], "PERR",
            ],
            [
                "TEACHING_NEED:TEACHING.READ_QUESTION_BEFORE_TEXT",
                "TEACHING.READ_QUESTION_BEFORE_TEXT", ["A1+"],
                ["READING"], "TEACHER_METHOD", "TEACHING_ROUTINE",
                ["SUPPORT", "PRACTICE"], "PMETHOD",
            ],
        ],
        "errors": [],
        "stop_reason": "NONE",
    }


def intake(consumer_value: dict) -> dict:
    m2_sha = builder.digest(consumer_value)
    common = {
        "source_lineage": {"m2_artifact_sha256": m2_sha},
        "learning_value_evaluation_status": "NOT_EVALUATED",
        "composition_item": False,
        "required_for_delivery": False,
        "learner_facing_allowed": False,
        "mastery_evidence_allowed": False,
        "production_activation_allowed": False,
    }
    candidates = [
        {
            "asset_candidate_id": "C1", "lesson_id": "L1", "lesson_node_id": "N1",
            "skill": "READING", "level": "A1+", "pku_id": "PERR",
            "mapping_class": "CONTROLLED_TRANSCRIPT_REFERENCE", "authority_ids": [],
            "teaching_need_id": "TEACHING_NEED:READING.ERROR_DETAIL_RELATIONSHIP_CONFUSION",
            **common,
        },
        {
            "asset_candidate_id": "C2", "lesson_id": "L2", "lesson_node_id": "N2",
            "skill": "READING", "level": "A1+", "pku_id": "PERR",
            "mapping_class": "CONTROLLED_TRANSCRIPT_REFERENCE", "authority_ids": [],
            "teaching_need_id": "TEACHING_NEED:READING.ERROR_DETAIL_RELATIONSHIP_CONFUSION",
            **common,
        },
        {
            "asset_candidate_id": "C3", "lesson_id": "L2", "lesson_node_id": "N2",
            "skill": "READING", "level": "A1+", "pku_id": "PMETHOD",
            "mapping_class": "CONTROLLED_TRANSCRIPT_REFERENCE", "authority_ids": [],
            "teaching_need_id": "TEACHING_NEED:TEACHING.READ_QUESTION_BEFORE_TEXT",
            **common,
        },
        {
            "asset_candidate_id": "C4", "lesson_id": "L3", "lesson_node_id": "N3",
            "skill": "WRITING", "level": "A1", "pku_id": "PGRAM",
            "mapping_class": "EXACT_AUTHORITY_REQUIREMENT",
            "authority_ids": ["GRAMMAR_ADJECTIVE_PHRASES_A1"],
            "teaching_need_id": None,
            **common,
        },
    ]
    value = {
        "task_id": builder.M4A_TASK,
        "schema_version": builder.M4A_SCHEMA,
        "validation_status": builder.M4A_STATUS,
        "asset_candidates": candidates,
        "counts": {"asset_candidate_count": len(candidates)},
        "claim_boundaries": {"learning_value_evaluated": False},
        "errors": [],
        "stop_reason": "NONE",
    }
    value["artifact_sha256"] = builder.digest(value)
    return value


def test_evaluates_against_current_material_surfaces() -> None:
    consumer_value = consumer()
    result = builder.build_artifact(intake(consumer_value), consumer_value, bridge())
    rows = {row["asset_candidate_id"]: row for row in result["binding_evaluations"]}
    assert rows["C2"]["raw_incremental_value_score"] > rows["C1"]["raw_incremental_value_score"]
    assert rows["C2"]["binding_decision"].startswith("RETAIN")
    assert rows["C4"]["material_profile"]["exact_authority_already_explicit"] is True
    assert result["counts"]["teacher_delivery_activated_count"] == 0
    assert result["counts"]["remediation_activated_count"] == 0


def test_pku_dedup_and_binding_caps() -> None:
    consumer_value = consumer()
    result = builder.build_artifact(intake(consumer_value), consumer_value, bridge())
    pkus = {row["pku_id"]: row for row in result["pku_evaluations"]}
    assert pkus["PERR"]["binding_count"] == 2
    assert pkus["PERR"]["retention_cap"] == 2
    assert result["counts"]["source_pku_count"] == 3
    assert result["counts"]["source_binding_count"] == 4


def test_build_is_deterministic() -> None:
    consumer_value = consumer()
    intake_value = intake(consumer_value)
    bridge_value = bridge()
    assert (
        builder.build_artifact(intake_value, consumer_value, bridge_value)
        == builder.build_artifact(intake_value, consumer_value, bridge_value)
    )


def test_m2_binding_tamper_fails_closed() -> None:
    consumer_value = consumer()
    intake_value = intake(consumer_value)
    intake_value["asset_candidates"][0]["source_lineage"]["m2_artifact_sha256"] = "bad"
    intake_value["artifact_sha256"] = builder.digest({
        key: value for key, value in intake_value.items() if key != "artifact_sha256"
    })
    try:
        builder.build_artifact(intake_value, consumer_value, bridge())
    except ValueError as exc:
        assert "m4a_m2_binding_invalid" in str(exc)
    else:
        raise AssertionError("tampered M2 binding accepted")


def test_validator_rejects_tamper(tmp_path: Path) -> None:
    consumer_value = consumer()
    intake_value = intake(consumer_value)
    bridge_value = bridge()
    artifact = builder.build_artifact(intake_value, consumer_value, bridge_value)
    tampered = copy.deepcopy(artifact)
    tampered["counts"]["teacher_delivery_activated_count"] = 1
    paths = []
    for name, value in (
        ("artifact.json", tampered),
        ("intake.json", intake_value),
        ("consumer.json", consumer_value),
        ("bridge.json", bridge_value),
    ):
        path = tmp_path / name
        path.write_text(json.dumps(value), encoding="utf-8")
        paths.append(path)
    report = validator.validate_paths(
        artifact_path=paths[0],
        intake_path=paths[1],
        consumer_path=paths[2],
        bridge_path=paths[3],
    )
    assert report["validation_status"] == validator.FAIL_STATUS
    assert "artifact_deterministic_rebuild_mismatch" in report["errors"]
