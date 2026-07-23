from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_cp05_private_candidate_materialization_and_admission as cp05
from ulga.builders import build_a1fs_v1_cp06_grammar_spiral_role_population_and_content_capacity as cp06
from ulga.builders import build_a1fs_v1_cp07a_unified_runtime_activity_contract_and_lineage_adapter as builder
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy
from ulga.validators import validate_a1fs_v1_cp07a_unified_runtime_activity_contract_and_lineage_adapter as validator


def _skill_contract(skill: str, dependency: str) -> dict:
    return {
        "skill": skill,
        "activity_kind": f"TEST_{skill}",
        "prompt": f"Test {skill.lower()} prompt.",
        "response_mode": "OPEN_TEXT",
        "support_level": "GUIDED",
        "initiative_level": "GUIDED",
        "scoring_contract": {"mode": "RUBRIC", "criteria": ["SOURCE_RELEVANCE"]},
        "evidence_level": "LEARNER_RESPONSE_REQUIRED",
        "runtime_dependency_status": dependency,
    }


def _m2() -> dict:
    return {
        "task_id": m2.TASK_ID,
        "schema_version": m2.SCHEMA_VERSION,
        "validation_status": m2.STATUS,
        "source_graph_sha256": "1" * 64,
        "asset_records": [
            {
                "asset_id": "KETR_A1_001",
                "asset_key": "READING:KETR_A1_001",
                "lesson_id": "KETR_L001",
                "skill": "READING",
                "level": "A1",
                "role": "MODEL",
                "payload": {"body": "private KET payload"},
                "content_digest": "2" * 64,
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
            {
                "asset_id": "KETW_A1P_001",
                "asset_key": "WRITING:KETW_A1P_001",
                "lesson_id": "KETW_L001",
                "skill": "WRITING",
                "level": "A1+",
                "role": "CHECKPOINT",
                "payload": {"body": "private KET writing payload"},
                "content_digest": "3" * 64,
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
            {
                "asset_id": "KETL_A2_001",
                "asset_key": "LISTENING:KETL_A2_001",
                "lesson_id": "KETL_LA2",
                "skill": "LISTENING",
                "level": "A2",
                "role": "MODEL",
                "payload": {"body": "locked A2 payload"},
                "content_digest": "4" * 64,
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
        ],
        "lesson_catalog": [
            {
                "lesson_id": "KETR_L001",
                "lesson_node_id": "LESSON:READING:KETR_L001",
                "skill": "READING",
                "level": "A1",
                "asset_keys": ["READING:KETR_A1_001"],
                "roles": ["MODEL"],
                "requirement_node_ids": ["REQ_READING_001"],
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
            {
                "lesson_id": "KETW_L001",
                "lesson_node_id": "LESSON:WRITING:KETW_L001",
                "skill": "WRITING",
                "level": "A1+",
                "asset_keys": ["WRITING:KETW_A1P_001"],
                "roles": ["CHECKPOINT"],
                "requirement_node_ids": ["REQ_WRITING_001"],
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
            {
                "lesson_id": "KETL_LA2",
                "lesson_node_id": "LESSON:LISTENING:KETL_LA2",
                "skill": "LISTENING",
                "level": "A2",
                "asset_keys": ["LISTENING:KETL_A2_001"],
                "roles": ["MODEL"],
                "requirement_node_ids": ["REQ_A2_LOCKED"],
                "release_scope": "PRIVATE_INTERNAL_D0",
            },
        ],
        "counts": {
            "asset_record_count": 3,
            "lesson_count": 3,
            "learning_lesson_count": 2,
            "a2_handoff_lesson_count": 1,
        },
        "access_contract": {
            "visibility": "PRIVATE_INTERNAL",
            "learning_query_levels": ["A1", "A1+"],
            "a2_payload_query_allowed": False,
            "a2_handoff_metadata_allowed": True,
            "max_query_limit": 100,
            "filter_fields": ["skill", "level", "lesson_id", "role", "requirement_node_id"],
        },
        "claim_boundaries": {
            "learner_ui_implemented": False,
            "learner_state_implemented": False,
            "planner_implemented": False,
            "mastery_claimed": False,
            "learner_release_approved": False,
            "a2_unlocked": False,
        },
        "errors": [],
        "next_short_step": m2.NEXT_SHORT_STEP,
    }


def _cp05_approved() -> dict:
    payload = {
        "task_id": cp05.TASK_ID,
        "program_id": cp05.PROGRAM_ID,
        "schema_version": cp05.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "course_container": "EXISTING_24_CANONICAL_UNITS_ONLY",
        "learning_units": [
            {
                "learning_unit_id": f"UNIT_{index:02d}",
                "grammar_unit_id": f"GRAMMAR_{index:02d}",
                "sequence_index": index,
                "internal_stage": "A1" if index <= 12 else "A1_PLUS",
                "canonical_egp_row_ids": [f"EGP_{index:02d}"],
            }
            for index in range(1, 25)
        ],
        "materialized_raz_sources": [
            {
                "material_id": "RAZ_MAT_001",
                "semantic_identity_id": "SEM_001",
                "source_unit_ref": "RAZ_A_BOOK_001_P001",
                "source_level": "A",
                "candidate_cefr_scope": "A1",
                "source_content": {"text": "This is private RAZ source text."},
                "source_content_sha256": "5" * 64,
                "verified_skill_affordances": ["READING_SOURCE", "LISTENING_ADAPTATION"],
                "skill_contracts": [
                    _skill_contract("READING", "READY_FOR_TEXT_RUNTIME_INTEGRATION"),
                    _skill_contract("LISTENING", "AUDIO_GENERATION_REQUIRED"),
                ],
                "materialization_status": "MATERIALIZED_PRIVATE_SOURCE_BOUND",
                "admission_status": "ADMISSION_READY",
                "runtime_status": "CP06_ROLE_ASSIGNMENT_REQUIRED",
            }
        ],
        "raz_unit_activity_bindings": [
            {
                "activity_binding_id": "RAZ_BIND_001",
                "learning_unit_id": "UNIT_01",
                "grammar_unit_id": "GRAMMAR_01",
                "canonical_egp_row_ids": ["EGP_01"],
                "content_candidate_id": "CONTENT_001",
                "exercise_candidate_id": "EXERCISE_001",
                "material_id": "RAZ_MAT_001",
                "target_skill_lanes": ["READING", "LISTENING"],
                "admission_status": "ADMITTED_PRIVATE_SOURCE_BOUND_ACTIVITY",
                "runtime_status": "CP06_ROLE_ASSIGNMENT_REQUIRED",
            }
        ],
        "m11b_reuse_activities": [
            {
                "activity_id": "M11B_ACTIVITY_001",
                "learning_unit_id": "UNIT_13",
                "grammar_unit_id": "GRAMMAR_13",
                "exercise_candidate_id": "M11B_EX_001",
                "content_candidate_id": "M11B_CONTENT_001",
                "source_item_ref": "M11B_PRIVATE_ITEM_001",
                "target_skill": "WRITING",
                "admission_status": "REUSED_EXISTING_REVIEWED_ADMISSION",
                "runtime_status": "CP06_ROLE_ASSIGNMENT_REQUIRED",
            }
        ],
        "remediation_queue": [],
        "coverage_summary": {
            "existing_learning_unit_count": 24,
            "new_learning_unit_count": 0,
            "m11b_reused_activity_count": 1,
            "raz_distinct_candidate_material_count": 1,
            "raz_materialized_source_count": 1,
            "raz_source_remediation_material_count": 0,
            "raz_candidate_binding_count": 1,
            "raz_admitted_activity_binding_count": 1,
            "raz_remediation_binding_count": 0,
            "skill_binding_counts": {"LISTENING": 1, "READING": 1},
            "listening_audio_generation_pending_binding_count": 1,
        },
        "private_source_identity": {
            "private_source_set_sha256": "6" * 64,
            "private_source_record_count": 1,
            "resolved_source_count": 1,
            "source_index_sha256": "7" * 64,
        },
        "claim_boundaries": {
            "private_source_text_read": True,
            "private_source_text_in_private_candidate": True,
            "private_source_text_in_safe_readback": False,
            "objective_answer_fabricated": False,
            "canonical_unit_identity_changed": False,
            "canonical_egp_mapping_changed": False,
            "learner_runtime_publication_performed": False,
            "four_skill_runtime_projection_performed": False,
            "mastery_claimed": False,
            "retention_confirmed": False,
            "a2_a2plus_in_scope": False,
        },
        "stop_reason": "NONE",
        "next_short_step": cp05.NEXT_SHORT_STEP,
    }
    candidate = policy.build_candidate(
        payload=payload,
        producer_id=cp05.PRODUCER_ID,
        level_scope=["A1", "A1+"],
        source_bindings={"fixture": "CP07A_TEST"},
    )
    return policy.admit_candidate(
        candidate,
        validation_receipts=[
            {"validator_id": "fixture_validator", "status": "PASS", "receipt_sha256": "8" * 64}
        ],
        decision_ref="CP07A_TEST_APPROVAL",
        producer_id=cp05.PRODUCER_ID,
    )


def _cp06() -> dict:
    capacity = [
        {
            "learning_unit_id": f"UNIT_{index:02d}",
            "grammar_unit_id": f"GRAMMAR_{index:02d}",
            "sequence_index": index,
            "internal_stage": "A1" if index <= 12 else "A1_PLUS",
            "canonical_egp_row_ids": [f"EGP_{index:02d}"],
            "prerequisite_unit_ids": [],
            "contrast_unit_ids": [],
            "error_tags": [f"ERROR_{index:02d}"],
            "activity_capacity": {},
            "scene_capacity": {"capacity_status": "RAZ_VERIFIED_THEME_ONLY"},
            "content_capacity_status": "TEXT_AND_SCENE_CAPACITY_AVAILABLE",
        }
        for index in range(1, 25)
    ]
    return {
        "task_id": cp06.TASK_ID,
        "program_id": cp06.PROGRAM_ID,
        "schema_version": cp06.SCHEMA_VERSION,
        "artifact_type": "metadata_only_grammar_spiral_role_and_content_capacity",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {},
        "role_contract": {},
        "raz_activity_role_bindings": [
            {
                "activity_binding_id": "RAZ_BIND_001",
                "learning_unit_id": "UNIT_01",
                "grammar_unit_id": "GRAMMAR_01",
                "material_id": "RAZ_MAT_001",
                "target_skill_lanes": ["READING", "LISTENING"],
                "content_roles": ["FOCUS", "RECYCLE"],
                "role_evidence": [{"role": "FOCUS", "basis": "TEST", "evidence_refs": ["RAZ_BIND_001"]}],
                "lifecycle_role_contracts": {},
                "runtime_status": "CP07_RUNTIME_PROJECTION_REQUIRED",
            }
        ],
        "m11b_activity_role_bindings": [
            {
                "activity_id": "M11B_ACTIVITY_001",
                "learning_unit_id": "UNIT_13",
                "grammar_unit_id": "GRAMMAR_13",
                "target_skill": "WRITING",
                "content_roles": ["FOCUS"],
                "role_evidence": [{"role": "FOCUS", "basis": "TEST", "evidence_refs": ["M11B_ACTIVITY_001"]}],
                "lifecycle_role_contracts": {},
                "runtime_status": "CP07_RUNTIME_PROJECTION_REQUIRED",
            }
        ],
        "unit_content_capacity": capacity,
        "coverage_summary": {
            "existing_learning_unit_count": 24,
            "new_learning_unit_count": 0,
            "raz_distinct_material_count": 1,
            "raz_activity_binding_count": 1,
            "m11b_activity_count": 1,
            "content_role_assignment_counts": {"FOCUS": 2, "RECYCLE": 1, "CONTRAST": 0, "TRANSFER": 0},
            "lifecycle_role_eligible_activity_counts": {"REMEDIATION": 2, "REASSESSMENT": 2, "RETENTION": 2},
            "text_runtime_candidate_unit_count": 24,
            "cp04_scene_capacity_unit_count": 23,
            "effective_scene_capacity_unit_count": 24,
            "effective_scene_gap_unit_count": 0,
            "listening_audio_generation_pending_binding_count": 1,
            "speaking_recording_pending_binding_count": 0,
            "skill_binding_counts": {"LISTENING": 1, "READING": 1, "WRITING": 1},
        },
        "capacity_gate": {
            "decision": "GRAMMAR_SPIRAL_ROLES_AND_CONTENT_CAPACITY_READY",
            "all_existing_units_have_admitted_activity_capacity": True,
            "scene_gap_requires_source_evidence_not_invention": True,
            "runtime_publication_allowed": False,
            "cp07_runtime_integration_required": True,
            "a2_a2plus_status": "LOCKED",
        },
        "claim_boundaries": {},
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": cp06.NEXT_SHORT_STEP,
    }


def _inputs() -> tuple[dict, dict, dict]:
    return _m2(), _cp05_approved(), _cp06()


def test_builds_unified_queryable_index_without_private_content() -> None:
    m2_index, approved, cp06_artifact = _inputs()
    artifact = builder.build_artifact(m2_index, approved, cp06_artifact)
    summary = artifact["coverage_summary"]
    assert summary["runtime_activity_count"] == 5
    assert summary["ket_learning_asset_count"] == 2
    assert summary["raz_binding_count"] == 1
    assert summary["raz_skill_projection_count"] == 2
    assert summary["m11b_activity_count"] == 1
    assert summary["a2_activity_count"] == 0
    assert "private KET payload" not in str(artifact)
    assert "private RAZ source text" not in str(artifact)
    assert "Test reading prompt" not in str(artifact)


def test_query_supports_ket_raz_unit_role_and_requirement_filters() -> None:
    artifact = builder.build_artifact(*_inputs())
    ket = builder.query_runtime_activity_index(
        artifact, source_kind="KET_ASSET_BODY", requirement_node_id="REQ_READING_001"
    )
    assert ket["total_match_count"] == 1
    assert ket["runtime_activities"][0]["skill"] == "READING"
    raz = builder.query_runtime_activity_index(
        artifact,
        source_kind="RAZ_ACTIVITY_BINDING",
        learning_unit_id="UNIT_01",
        instructional_role="RECYCLE",
    )
    assert raz["total_match_count"] == 2


def test_a2_query_fails_closed_and_a2_asset_is_absent() -> None:
    artifact = builder.build_artifact(*_inputs())
    assert all(row["level"] != "A2" for row in artifact["runtime_activities"])
    with pytest.raises(builder.CP07ABuildError, match="A2_PAYLOAD_LOCKED"):
        builder.query_runtime_activity_index(artifact, level="A2")


def test_rejects_cp05_cp06_binding_drift() -> None:
    m2_index, approved, cp06_artifact = _inputs()
    cp06_artifact["raz_activity_role_bindings"][0]["material_id"] = "RAZ_MAT_DRIFT"
    with pytest.raises(builder.CP07ABuildError, match="cp05_cp06_raz_binding_drift"):
        builder.build_artifact(m2_index, approved, cp06_artifact)


def test_rejects_missing_skill_contract() -> None:
    m2_index, approved, cp06_artifact = _inputs()
    approved["payload"]["materialized_raz_sources"][0]["skill_contracts"] = [
        _skill_contract("READING", "READY_FOR_TEXT_RUNTIME_INTEGRATION")
    ]
    approved["artifact_sha256"] = policy.digest({key: value for key, value in approved.items() if key != "artifact_sha256"})
    with pytest.raises(builder.CP07ABuildError, match="cp05_exact_skill_contract_required"):
        builder.build_artifact(m2_index, approved, cp06_artifact)


def test_validator_accepts_deterministic_artifact_and_rejects_leakage() -> None:
    m2_index, approved, cp06_artifact = _inputs()
    artifact = builder.build_artifact(m2_index, approved, cp06_artifact)
    report = validator.validate_artifact(
        artifact,
        m2_index=m2_index,
        cp05_approved=approved,
        cp06_artifact=cp06_artifact,
    )
    assert report["validation_status"] == builder.PASS_STATUS
    assert report["deterministic_rebuild_matches"] is True
    assert report["ket_queryable"] is True
    assert report["raz_text_queryable"] is True
    assert report["a2_fail_closed"] is True
    tampered = deepcopy(artifact)
    tampered["runtime_activities"][0]["prompt"] = "leaked"
    failed = validator.validate_artifact(
        tampered,
        m2_index=m2_index,
        cp05_approved=approved,
        cp06_artifact=cp06_artifact,
    )
    assert failed["validation_status"] != builder.PASS_STATUS
    assert any("private_content_key_forbidden" in error for error in failed["errors"])
