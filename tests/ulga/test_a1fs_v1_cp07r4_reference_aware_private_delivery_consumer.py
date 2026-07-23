from __future__ import annotations

from copy import deepcopy
import json

import pytest

from ulga.builders import build_a1fs_v1_cp05_private_candidate_materialization_and_admission as cp05
from ulga.builders import build_a1fs_v1_cp07r3f_reference_aware_optional_context_lesson_composition as r3f
from ulga.builders import build_a1fs_v1_cp07r4_reference_aware_private_delivery_consumer as builder
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_a1fs_v1_m3_learner_profile_session_state_storage as m3
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4
from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as policy
from ulga.builders import cp07d_private_four_skill_delivery_consumer_impl as cp07d
from ulga.validators import validate_a1fs_v1_cp07r4_reference_aware_private_delivery_consumer as validator


BASE_ROLE = {
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
                "role": BASE_ROLE[skill],
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
                "roles": [BASE_ROLE[skill]],
                "requirement_node_ids": [] if skill == "LISTENING" else [f"REF:{skill}:A1"],
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
                "skill_contracts": [
                    {
                        "skill": skill,
                        "activity_kind": f"SOURCE_{skill}_CANARY",
                        "prompt": f"Complete one {skill.lower()} response about the source.",
                        "response_mode": "OPEN_TEXT",
                        "support_level": "SOURCE_TEXT_VISIBLE",
                        "initiative_level": "GUIDED",
                        "scoring_contract": {
                            "mode": "RUBRIC",
                            "automatic_exact_answer": False,
                            "criteria": ["SOURCE_RELEVANCE", "TARGET_LANGUAGE_USE"],
                        },
                        "evidence_level": "LEARNER_RESPONSE_REQUIRED",
                        "runtime_dependency_status": "READY_FOR_TEXT_RUNTIME_INTEGRATION",
                    }
                ],
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
        validation_receipts=[
            {
                "validator_id": "cp07r4_fixture",
                "status": "PASS",
                "receipt_sha256": "4" * 64,
            }
        ],
        decision_ref=f"CP07R4_FIXTURE_{skill}",
        producer_id=cp05.PRODUCER_ID,
    )


def _r3f(skill: str, consumer: dict, *, with_context: bool) -> dict:
    lesson = consumer["lesson_catalog"][0]
    base_key = lesson["asset_keys"][0]
    items = [
        {
            "composition_item_id": f"CP07A:KET:{skill}:BASE",
            "source_kind": "KET_ASSET_BODY",
            "skill": skill,
            "instructional_role": "STRUCTURED_KET_ASSET",
            "ket_role_refs": [BASE_ROLE[skill]],
            "runtime_readiness": "QUERYABLE_PRIVATE_KET_ASSET",
            "delivery_allowed_now": True,
            "source_lineage": {"m2_asset_key": base_key},
            "response_contract_ref": {"authority": "M2_ASSET_BODY"},
        }
    ]
    references = []
    mode = "KET_ONLY_NO_EXACT_KET99_REFERENCE"
    if with_context:
        references = [
            {
                "evidence_occurrence_id": "P001:01",
                "transcript_id": "P001",
                "source_evidence_sha256": "5" * 64,
                "instructional_roles": ["FOCUS"],
                "canonical_target_refs": [
                    {"target_type": "GRAMMAR_UNIT", "target_id": "GRAMMAR_BE_VERB_BASIC"}
                ],
                "mapping_basis": ["EXACT_R3C_AUTHORITY_EVIDENCE"],
                "runtime_effect": "OPTIONAL_TEACHING_REFERENCE_ONLY",
            }
        ]
        items.append(
            {
                "composition_item_id": f"CP07A:RAZ:{skill}:FOCUS",
                "source_kind": "RAZ_ACTIVITY_BINDING",
                "skill": skill,
                "instructional_role": "FOCUS",
                "grammar_unit_id": "GRAMMAR_BE_VERB_BASIC",
                "learning_unit_id": "E4S_A1V1_UNIT:GRAMMAR_BE_VERB_BASIC",
                "runtime_readiness": "QUERYABLE_TEXT_RUNTIME_CONTRACT",
                "delivery_allowed_now": True,
                "source_lineage": {
                    "cp05_activity_binding_id": f"RAZ_BIND_{skill}",
                    "cp05_material_id": f"RAZ_MAT_{skill}",
                },
                "response_contract_ref": {"authority": "CP05_APPROVED_SKILL_CONTRACT"},
            }
        )
        mode = "KET_WITH_KET99_REFERENCE_AND_OPTIONAL_CONTEXT"
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
        "cp07r3f_task_id": r3f.TASK_ID,
        "cp07r3f_schema_version": r3f.SCHEMA_VERSION,
        "cp07r3f_validation_status": r3f.PASS_STATUS,
        "source_identity": {"m2_consumer_sha256": cp07d._digest(consumer)},
        "unified_lesson_composition": {
            "selected_lesson_id": lesson["lesson_id"],
            "selected_skill": skill,
            "selected_level": "A1",
            "hard_selection_preserved": True,
            "requirement_node_ids": lesson["requirement_node_ids"],
            "composition_mode": mode,
            "instructional_reference_status": "REFERENCED" if references else "NO_EXACT_KET99_REFERENCE",
            "instructional_references": references,
            "bridged_grammar_unit_ids": ["GRAMMAR_BE_VERB_BASIC"] if references else [],
            "composition_items": items,
            "consumer_gate": {
                "m4_selected_lesson_unchanged": True,
                "m1_hard_prerequisite_graph_unchanged": True,
                "ket_asset_body_required": True,
                "ket99_reference_optional": True,
                "raz_context_optional": True,
                "m11b_checkpoint_optional": True,
                "missing_reference_blocks_delivery": False,
                "r4_cp07d_optional_context_consumer_completed": False,
                "a2_payload_included": False,
            },
        },
        "errors": [],
        "stop_reason": "NONE",
    }


@pytest.mark.parametrize("skill", ["LISTENING", "SPEAKING", "READING", "WRITING"])
def test_ket_only_consumer_mounts_selected_assets_without_fake_runtime_capability(skill: str) -> None:
    consumer = _m2(skill)
    plan = _r3f(skill, consumer, with_context=False)
    artifact = builder.build_private_delivery_consumer(consumer, {}, plan)
    report = validator.validate_artifact(
        artifact,
        m2_consumer=consumer,
        cp05_approved={},
        r3f_plan=plan,
    )
    contract = artifact["cp07d_delivery_contract"]
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert report["deterministic_rebuild_matches"] is True
    assert contract["delivery_mode"] == "KET_ASSET_BODY_ONLY"
    assert contract["mounted_ket_asset_keys"] == consumer["lesson_catalog"][0]["asset_keys"]
    assert contract["projected_asset_keys"] == []
    assert contract["missing_reference_blocks_delivery"] is False
    assert contract["m3_session_compatible"] is True
    assert contract["m5_private_renderer_compatible"] is True
    assert contract["m6_feature_rubric_compatible"] is False
    assert contract["m10_private_media_registration_compatible"] is False
    assert artifact["cp07r4_capability_gaps"]["response_capture_contract_missing"] is True


def test_exact_reading_context_still_uses_policy_bound_projection() -> None:
    consumer = _m2("READING")
    approved = _approved("READING")
    plan = _r3f("READING", consumer, with_context=True)
    artifact = builder.build_private_delivery_consumer(consumer, approved, plan)
    report = validator.validate_artifact(
        artifact,
        m2_consumer=consumer,
        cp05_approved=approved,
        r3f_plan=plan,
    )
    contract = artifact["cp07d_delivery_contract"]
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert contract["delivery_mode"] == "KET_ASSET_BODY_WITH_OPTIONAL_CONTEXT_PROJECTIONS"
    assert len(contract["projected_asset_keys"]) == 1
    assert len(contract["response_capture_asset_keys"]) == 1
    assert contract["m6_feature_rubric_compatible"] is True
    assert artifact["asset_records"][0] == consumer["asset_records"][0]
    assert artifact["cp07r4_source_identity"]["cp05_approved_artifact_sha256"] == approved["artifact_sha256"]


def test_ket_only_consumer_initializes_existing_m3_storage(tmp_path) -> None:
    consumer = _m2("LISTENING")
    plan = _r3f("LISTENING", consumer, with_context=False)
    artifact = builder.build_private_delivery_consumer(consumer, {}, plan)
    consumer_path = tmp_path / "consumer.json"
    consumer_path.write_text(json.dumps(artifact), encoding="utf-8")
    database = tmp_path / "state.sqlite3"
    result = m3.LearnerStateStore(database).initialize(consumer_path)
    assert result["validation_status"] == m3.STATUS
    assert result["lesson_count"] == 1
    assert result["asset_count"] == 1


def test_validator_rejects_base_m2_asset_rewrite() -> None:
    consumer = _m2("WRITING")
    plan = _r3f("WRITING", consumer, with_context=False)
    artifact = builder.build_private_delivery_consumer(consumer, {}, plan)
    tampered = deepcopy(artifact)
    tampered["asset_records"][0]["payload"]["learner_instruction"] = "Changed"
    report = validator.validate_artifact(
        tampered,
        m2_consumer=consumer,
        cp05_approved={},
        r3f_plan=plan,
    )
    assert report["validation_status"] != builder.PASS_STATUS
    assert any(error.startswith("base_m2_asset_drift:") for error in report["errors"])


def test_r3f_ket_asset_identity_drift_fails_closed() -> None:
    consumer = _m2("READING")
    plan = _r3f("READING", consumer, with_context=False)
    plan["unified_lesson_composition"]["composition_items"][0]["source_lineage"]["m2_asset_key"] = "KET:READING:OTHER"
    with pytest.raises(builder.R4BuildError, match="r3f_m2_ket_asset_bundle_not_reconciled"):
        builder.build_private_delivery_consumer(consumer, {}, plan)
