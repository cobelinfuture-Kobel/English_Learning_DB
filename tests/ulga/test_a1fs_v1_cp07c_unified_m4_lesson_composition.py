from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

from ulga.builders import build_a1fs_v1_cp07a_unified_runtime_activity_contract_and_lineage_adapter as cp07a
from ulga.builders import build_a1fs_v1_cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay as cp07b
from ulga.builders import build_a1fs_v1_cp07c_unified_m4_lesson_composition as builder
from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4
from ulga.builders import build_a1fs_v1_m5_four_skill_renderer_learner_ui as m5
from ulga.validators import validate_a1fs_v1_cp07c_unified_m4_lesson_composition as validator


def _graph() -> dict:
    nodes = [
        {"node_id": "LESSON:READING:R-A1", "node_type": "LESSON", "skill": "READING", "level": "A1", "source_ref": "R-A1"},
        {"node_id": "REF:READING:be_present_affirmative", "node_type": "CAPABILITY", "skill": "READING", "level": "A1", "source_ref": "be_present_affirmative"},
        {"node_id": "GATE:A1FS:A2_LOCK", "node_type": "A2_LOCK", "skill": "FOUR_SKILL", "level": "A2", "source_ref": "A2_ENTRY"},
    ]
    edges = [{"from_node_id": nodes[1]["node_id"], "to_node_id": nodes[2]["node_id"], "edge_type": "UNLOCK_REQUIRES"}]
    return {
        "task_id": m1.TASK_ID,
        "schema_version": m1.SCHEMA_VERSION,
        "validation_status": m1.STATUS,
        "nodes": nodes,
        "edges": edges,
        "counts": {"node_count": len(nodes), "edge_count": len(edges), "required_mastery_node_count": 1},
        "a2_lock_contract": {"state": "LOCKED_BY_DESIGN", "required_mastery_node_ids": [nodes[1]["node_id"]]},
        "errors": [],
    }


def _consumer() -> dict:
    lesson = {
        "lesson_id": "R-A1",
        "lesson_node_id": "LESSON:READING:R-A1",
        "skill": "READING",
        "level": "A1",
        "asset_keys": ["ASSET:R-A1:TXT", "ASSET:R-A1:CHK"],
        "roles": ["TXT", "CHK"],
        "requirement_node_ids": ["REF:READING:be_present_affirmative"],
        "release_scope": "PRIVATE_INTERNAL_D0",
    }
    assets = [
        {
            "asset_id": "R-A1-TXT", "asset_key": "ASSET:R-A1:TXT", "lesson_id": "R-A1",
            "skill": "READING", "level": "A1", "role": "TXT",
            "payload": {"passage": "Private KET reading passage."}, "content_digest": "1" * 64,
            "release_scope": "PRIVATE_INTERNAL_D0",
        },
        {
            "asset_id": "R-A1-CHK", "asset_key": "ASSET:R-A1:CHK", "lesson_id": "R-A1",
            "skill": "READING", "level": "A1", "role": "CHK",
            "payload": {"question": "Private KET checkpoint?"}, "content_digest": "2" * 64,
            "release_scope": "PRIVATE_INTERNAL_D0",
        },
    ]
    return {
        "task_id": m2.TASK_ID,
        "schema_version": m2.SCHEMA_VERSION,
        "validation_status": m2.STATUS,
        "lesson_catalog": [lesson],
        "asset_records": assets,
        "counts": {"lesson_count": 1, "asset_record_count": 2, "learning_lesson_count": 1, "a2_handoff_lesson_count": 0},
        "access_contract": {"a2_payload_query_allowed": False},
        "errors": [],
    }


def _plan() -> dict:
    return {
        "task_id": m4.TASK_ID,
        "validation_status": m4.STATUS,
        "plan_id": "plan-cp07c-1",
        "learner_id": "learner-1",
        "plan_status": "PLAN_LEARNING_LESSON",
        "selected_lesson": {
            "lesson_id": "R-A1", "lesson_node_id": "LESSON:READING:R-A1",
            "skill": "READING", "level": "A1", "roles": ["TXT", "CHK"],
            "requirement_node_ids": ["REF:READING:be_present_affirmative"],
        },
        "rationale": {"reason": "PREREQUISITES_SATISFIED_BALANCED_SKILL_SELECTION"},
        "a2_lock": {
            "a2_lock_state": "LOCKED", "a2_payload_access_granted": False,
            "a2_session_start_granted": False, "required_mastery_count": 1,
            "missing_mastery_count": 1,
        },
        "a2_payload_included": False,
        "a2_session_started": False,
        "next_short_step": m4.NEXT_SHORT_STEP,
    }


def _ket_runtime(asset_key: str, role: str) -> dict:
    return {
        "runtime_activity_id": f"CP07A:{asset_key}",
        "source_kind": "KET_ASSET_BODY",
        "skill": "READING",
        "level": "A1",
        "curriculum_binding": {
            "ket_lesson_id": "R-A1", "ket_lesson_node_id": "LESSON:READING:R-A1",
            "requirement_node_ids": ["REF:READING:be_present_affirmative"],
            "learning_unit_id": None, "grammar_unit_id": None, "canonical_egp_row_ids": [],
        },
        "instructional_roles": ["FOCUS", role],
        "source_lineage": {"m2_asset_key": asset_key, "m2_content_digest": "3" * 64},
        "response_contract_ref": {"authority": "KET_ASSET_BODY_PRIVATE_PAYLOAD", "contract_resolution_status": "RESOLVE_AT_M5_DELIVERY"},
        "runtime_readiness": "QUERYABLE_PRIVATE_KET_ASSET",
        "learner_facing": False,
        "a2_payload_included": False,
    }


def _raz_runtime(role: str, material_number: int) -> dict:
    return {
        "runtime_activity_id": f"CP07A:RAZ:{role}",
        "source_kind": "RAZ_ACTIVITY_BINDING",
        "skill": "READING",
        "level": "A1",
        "curriculum_binding": {
            "ket_lesson_id": None, "ket_lesson_node_id": None, "requirement_node_ids": [],
            "learning_unit_id": "E4S_A1V1_UNIT:GRAMMAR_BE_VERB_BASIC",
            "grammar_unit_id": "GRAMMAR_BE_VERB_BASIC", "canonical_egp_row_ids": ["EGP_BE_001"],
        },
        "instructional_roles": ["FOCUS", role] if role != "FOCUS" else ["FOCUS"],
        "source_lineage": {
            "cp05_activity_binding_id": f"RAZ_BIND_{material_number}",
            "cp05_material_id": f"RAZ_MAT_{material_number}",
            "cp05_source_unit_ref": f"RAZ_A_{material_number}",
            "cp05_source_content_sha256": f"{material_number:064x}"[-64:],
        },
        "response_contract_ref": {
            "authority": "CP05_APPROVED_SKILL_CONTRACT",
            "skill_contract_sha256": "4" * 64,
            "prompt_sha256": "5" * 64,
            "scoring_contract_sha256": "6" * 64,
            "contract_resolution_status": "RESOLVE_AT_M5_DELIVERY",
        },
        "runtime_readiness": "QUERYABLE_TEXT_RUNTIME_CONTRACT",
        "learner_facing": False,
        "a2_payload_included": False,
    }


def _cp07a(consumer: dict) -> dict:
    rows = [
        _ket_runtime("ASSET:R-A1:TXT", "TXT"),
        _ket_runtime("ASSET:R-A1:CHK", "CHK"),
    ] + [_raz_runtime(role, index) for index, role in enumerate(builder.CONTEXT_ROLES, start=1)]
    rows.append({
        "runtime_activity_id": "CP07A:M11B:1",
        "source_kind": "M11B_REVIEWED_ACTIVITY",
        "skill": "READING",
        "level": "A1",
        "curriculum_binding": {
            "ket_lesson_id": None, "ket_lesson_node_id": None, "requirement_node_ids": [],
            "learning_unit_id": "E4S_A1V1_UNIT:GRAMMAR_BE_VERB_BASIC",
            "grammar_unit_id": "GRAMMAR_BE_VERB_BASIC", "canonical_egp_row_ids": [],
        },
        "instructional_roles": ["FOCUS"],
        "source_lineage": {"cp05_m11b_activity_id": "M11B_1", "m11b_source_item_ref": "M11B_PRIVATE_1"},
        "response_contract_ref": {"authority": "EXISTING_M11B_REVIEWED_CONTENT_STORE", "contract_resolution_status": "PENDING_CP07C_OR_CP07D_RESOLUTION"},
        "runtime_readiness": "PENDING_REVIEWED_PAYLOAD_RESOLUTION",
        "learner_facing": False,
        "a2_payload_included": False,
    })
    return {
        "task_id": cp07a.TASK_ID,
        "program_id": cp07a.PROGRAM_ID,
        "schema_version": cp07a.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {"m2_consumer_sha256": builder._digest(consumer)},
        "runtime_activities": rows,
        "errors": [],
        "stop_reason": "NONE",
    }


def _cp07b(graph: dict) -> dict:
    occurrence = {
        "evidence_occurrence_id": "KET99:P006:01",
        "evidence_index": 1,
        "evidence_item": "be_present_affirmative",
        "normalized_evidence_item": "be_present_affirmative",
        "disposition": "CANONICAL_MATCH",
        "canonical_targets": [
            {
                "target_type": "M1_NODE", "target_id": "REF:READING:be_present_affirmative",
                "skill": "READING", "level": "A1", "node_type": "CAPABILITY",
                "mapping_basis": "EXACT_NORMALIZED_SOURCE_REF_MATCH", "mapping_confidence": "HIGH_EXACT",
            },
            {
                "target_type": "GRAMMAR_UNIT", "target_id": "GRAMMAR_BE_VERB_BASIC",
                "learning_unit_id": "E4S_A1V1_UNIT:GRAMMAR_BE_VERB_BASIC", "internal_stage": "A1",
                "mapping_basis": "EXACT_BE_FORM_LABEL", "mapping_confidence": "HIGH_RULE_EXACT",
            },
        ],
        "support_domains": [],
        "instructional_roles": ["FOCUS"],
        "target_role_assignments": [],
        "review_reason": None,
    }
    return {
        "task_id": cp07b.TASK_ID,
        "program_id": cp07b.PROGRAM_ID,
        "schema_version": cp07b.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {"m1_hard_graph_sha256": builder._digest(graph)},
        "authority_contract": {"hard_graph_mutation_allowed": False, "a2_a2plus_status": "LOCKED"},
        "transcript_overlays": [
            {
                "transcript_id": "P006", "textbook_page": 10, "unit_id": "U01",
                "lesson_role": "unit_core", "content_roles": ["grammar", "teacher_delivery"],
                "source_lineage": {"source_evidence_sha256": "7" * 64},
                "evidence_occurrences": [occurrence],
            }
        ],
        "canonical_target_sequences": [
            {"target_type": "GRAMMAR_UNIT", "target_id": "GRAMMAR_BE_VERB_BASIC", "soft_order_rank": 1}
        ],
        "planner_overlay_gate": {"m4_planner_integration_completed": False},
        "errors": [],
        "stop_reason": "NONE",
    }


def _inputs() -> tuple[dict, dict, dict, dict, dict]:
    consumer = _consumer(); graph = _graph()
    return _plan(), consumer, graph, _cp07a(consumer), _cp07b(graph)


def test_composes_ket_raz_and_m11b_without_changing_m4_selection() -> None:
    inputs = _inputs(); artifact = builder.build_composition(*inputs)
    assert artifact["selected_lesson"] == inputs[0]["selected_lesson"]
    summary = artifact["unified_lesson_composition"]["coverage_summary"]
    assert summary["ket_asset_count"] == 2
    assert summary["raz_contextual_activity_count"] == 4
    assert summary["m11b_checkpoint_count"] == 1
    assert summary["bridged_grammar_unit_count"] == 1
    assert summary["delivery_allowed_now_count"] == 6
    assert artifact["next_short_step"] == builder.NEXT_SHORT_STEP


def test_context_roles_prefer_distinct_materials_and_are_bounded() -> None:
    artifact = builder.build_composition(*_inputs())
    raz = [row for row in artifact["unified_lesson_composition"]["composition_items"] if row["source_kind"] == "RAZ_ACTIVITY_BINDING"]
    assert [row["instructional_role"] for row in raz] == list(builder.CONTEXT_ROLES)
    assert len({row["source_lineage"]["cp05_material_id"] for row in raz}) == 4


def test_missing_exact_requirement_bridge_fails_closed() -> None:
    inputs = list(_inputs())
    inputs[4] = deepcopy(inputs[4])
    inputs[4]["transcript_overlays"][0]["evidence_occurrences"][0]["canonical_targets"] = [
        target for target in inputs[4]["transcript_overlays"][0]["evidence_occurrences"][0]["canonical_targets"]
        if target["target_type"] != "M1_NODE"
    ]
    with pytest.raises(builder.CP07CBuildError, match="NO_EXACT_KET_REQUIREMENT_TO_TRANSCRIPT_BRIDGE"):
        builder.build_composition(*inputs)


def test_missing_raz_focus_for_bridged_grammar_fails_closed() -> None:
    inputs = list(_inputs())
    inputs[3] = deepcopy(inputs[3])
    inputs[3]["runtime_activities"] = [row for row in inputs[3]["runtime_activities"] if row["source_kind"] != "RAZ_ACTIVITY_BINDING"]
    with pytest.raises(builder.CP07CBuildError, match="NO_RAZ_CONTEXTUAL_ACTIVITY"):
        builder.build_composition(*inputs)


def test_a2_or_missing_requirement_plan_is_rejected() -> None:
    inputs = list(_inputs())
    inputs[0] = deepcopy(inputs[0]); inputs[0]["selected_lesson"]["level"] = "A2"
    with pytest.raises(builder.CP07CBuildError, match="level_outside_a1_a1plus"):
        builder.build_composition(*inputs)
    inputs = list(_inputs()); inputs[0] = deepcopy(inputs[0]); inputs[0]["selected_lesson"]["requirement_node_ids"] = []
    with pytest.raises(builder.CP07CBuildError, match="requirement_nodes_missing"):
        builder.build_composition(*inputs)


def test_validator_and_existing_m5_accept_enriched_plan(tmp_path: Path) -> None:
    inputs = _inputs(); artifact = builder.build_composition(*inputs)
    report = validator.validate_artifact(
        artifact,
        m4_plan=inputs[0], m2_consumer=inputs[1], m1_graph=inputs[2],
        cp07a_index=inputs[3], cp07b_overlay=inputs[4],
    )
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert report["deterministic_rebuild_matches"] is True
    assert report["m5_backward_compatible"] is True

    consumer_path = tmp_path / "consumer.json"
    plan_path = tmp_path / "plan.json"
    output_root = tmp_path / "ui"
    consumer_path.write_text(json.dumps(inputs[1]), encoding="utf-8")
    plan_path.write_text(json.dumps(artifact), encoding="utf-8")
    manifest = m5.build_ui(consumer_path=consumer_path, plan_path=plan_path, output_root=output_root)
    assert manifest["lesson_id"] == "R-A1"
    assert manifest["asset_count"] == 2
    assert (output_root / "lesson.private.json").is_file()


def test_validator_detects_selected_lesson_tampering() -> None:
    inputs = _inputs(); artifact = builder.build_composition(*inputs)
    tampered = deepcopy(artifact); tampered["selected_lesson"]["lesson_id"] = "OTHER"
    report = validator.validate_artifact(
        tampered,
        m4_plan=inputs[0], m2_consumer=inputs[1], m1_graph=inputs[2],
        cp07a_index=inputs[3], cp07b_overlay=inputs[4],
    )
    assert report["validation_status"] != builder.PASS_STATUS
    assert "m4_selected_lesson_changed" in report["errors"]
