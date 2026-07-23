from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_cp07a_unified_runtime_activity_contract_and_lineage_adapter as cp07a
from ulga.builders import build_a1fs_v1_cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay as cp07b
from ulga.builders import build_a1fs_v1_cp07c_unified_m4_lesson_composition as cp07c
from ulga.builders import build_a1fs_v1_cp07r3c_ket_authority_semantic_bridge as bridge_builder
from ulga.builders import build_a1fs_v1_cp07r3c_semantic_lesson_composition as composition_builder
from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4
from ulga.builders import cp07d_private_four_skill_delivery_consumer_impl as cp07d
from ulga.validators import validate_a1fs_v1_cp07r3c_ket_authority_semantic_bridge as bridge_validator
from ulga.validators import validate_a1fs_v1_cp07r3c_semantic_lesson_composition as composition_validator

GRAMMAR_ID = "GRAMMAR_BE_VERB_BASIC"
LEARNING_ID = "E4S_A1V1_UNIT:GRAMMAR_BE_VERB_BASIC"
SKILL_SPECS = (
    ("LISTENING", "KETL-LF-L001", "L-ASSET-001", None, "learning_objective"),
    ("SPEAKING", "SF-00-L01", "S-ASSET-001", "EGP-SPK-001", "grammar_focus"),
    ("READING", "KETR-RF-00-L01", "R-ASSET-001", "KETR-A1R-001", "target_language"),
    ("WRITING", "KLSN-WF00-L01", "W-ASSET-001", "A1W-01", "body_title"),
)


def _graph() -> dict:
    nodes: list[dict] = []
    coverage: list[dict] = []
    required: list[str] = []
    for skill, lesson_id, asset_id, ref, _ in SKILL_SPECS:
        lesson_node_id = f"LESSON:{skill}:{lesson_id}"
        nodes.append({
            "node_id": lesson_node_id,
            "node_type": "LESSON",
            "skill": skill,
            "level": "A1",
            "source_ref": lesson_id,
            "mastery_required_before_a2": True,
            "asset_body_count": 1,
            "roles": ["EVD"],
        })
        required.append(lesson_node_id)
        if ref is None:
            continue
        node_id = f"REF:{skill}:{ref}"
        nodes.append({
            "node_id": node_id,
            "node_type": "CAPABILITY",
            "skill": skill,
            "level": "A1",
            "source_ref": ref,
            "mastery_required_before_a2": True,
        })
        coverage.append({
            "node_id": node_id,
            "skill": skill,
            "source_ref": ref,
            "coverage_class": "MASTERY",
            "levels": ["A1"],
            "lesson_ids": [lesson_id],
            "asset_body_ids": [asset_id],
            "roles": ["EVD"],
            "coverage_status": "COVERED",
        })
        required.append(node_id)
    nodes.append({
        "node_id": "GATE:A1FS:A2_LOCK",
        "node_type": "A2_LOCK",
        "skill": "FOUR_SKILL",
        "level": "A2",
        "source_ref": "A2_ENTRY",
        "mastery_required_before_a2": False,
    })
    edges = [
        {"from_node_id": node_id, "to_node_id": "GATE:A1FS:A2_LOCK", "edge_type": "UNLOCK_REQUIRES"}
        for node_id in required
    ]
    return {
        "task_id": m1.TASK_ID,
        "schema_version": m1.SCHEMA_VERSION,
        "validation_status": m1.STATUS,
        "nodes": nodes,
        "edges": edges,
        "coverage": coverage,
        "counts": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "coverage_record_count": len(coverage),
            "lesson_count": 4,
            "required_mastery_node_count": len(required),
        },
        "a2_lock_contract": {
            "gate_node_id": "GATE:A1FS:A2_LOCK",
            "state": "LOCKED_BY_DESIGN",
            "required_mastery_node_ids": required,
            "a2_handoff_lesson_node_ids": [],
            "unlock_rule": "ALL_REQUIRED_MASTERY_NODES_MUST_BE_MASTERED",
            "runtime_unlock_implemented": False,
        },
        "errors": [],
    }


def _consumer() -> dict:
    assets: list[dict] = []
    catalog: list[dict] = []
    for skill, lesson_id, asset_id, ref, semantic_field in SKILL_SPECS:
        asset_key = f"{skill}:{asset_id}"
        assets.append({
            "asset_id": asset_id,
            "asset_key": asset_key,
            "lesson_id": lesson_id,
            "skill": skill,
            "level": "A1",
            "role": "EVD",
            "payload": {semantic_field: "be present affirmative"},
            "content_digest": "a" * 64,
            "release_scope": "PRIVATE_INTERNAL_D0",
        })
        catalog.append({
            "lesson_id": lesson_id,
            "lesson_node_id": f"LESSON:{skill}:{lesson_id}",
            "skill": skill,
            "level": "A1",
            "asset_keys": [asset_key],
            "roles": ["EVD"],
            "requirement_node_ids": [] if ref is None else [f"REF:{skill}:{ref}"],
            "release_scope": "PRIVATE_INTERNAL_D0",
        })
    return {
        "task_id": m2.TASK_ID,
        "schema_version": m2.SCHEMA_VERSION,
        "validation_status": m2.STATUS,
        "source_graph_sha256": "b" * 64,
        "asset_records": assets,
        "lesson_catalog": catalog,
        "counts": {
            "asset_record_count": len(assets),
            "lesson_count": len(catalog),
            "learning_lesson_count": len(catalog),
            "a2_handoff_lesson_count": 0,
        },
        "access_contract": {"a2_payload_query_allowed": False},
        "errors": [],
    }


def _overlay(graph: dict) -> dict:
    occurrence = {
        "evidence_occurrence_id": "KET99:P006:01",
        "evidence_index": 1,
        "evidence_item": "be_present_affirmative",
        "normalized_evidence_item": "be_present_affirmative",
        "disposition": "CANONICAL_MATCH",
        "canonical_targets": [{
            "target_type": "GRAMMAR_UNIT",
            "target_id": GRAMMAR_ID,
            "learning_unit_id": LEARNING_ID,
            "internal_stage": "A1",
            "mapping_basis": "EXACT_BE_FORM_LABEL",
            "mapping_confidence": "HIGH_RULE_EXACT",
        }],
        "support_domains": [],
        "instructional_roles": ["FOCUS"],
        "target_role_assignments": [],
        "review_reason": None,
    }
    return {
        "task_id": cp07b.TASK_ID,
        "program_id": "A1FS-V1",
        "schema_version": cp07b.SCHEMA_VERSION,
        "artifact_type": "metadata_only_ket99_instructional_sequence_overlay",
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {"m1_hard_graph_sha256": bridge_builder._digest(graph)},
        "authority_contract": {"hard_graph_mutation_allowed": False, "a2_a2plus_status": "LOCKED"},
        "transcript_overlays": [{
            "transcript_id": "P006",
            "textbook_page": 10,
            "unit_id": "U01",
            "lesson_role": "unit_core",
            "content_roles": ["grammar", "teacher_delivery"],
            "source_lineage": {"source_evidence_sha256": "c" * 64},
            "evidence_occurrences": [occurrence],
        }],
        "canonical_target_sequences": [{
            "target_type": "GRAMMAR_UNIT",
            "target_id": GRAMMAR_ID,
            "soft_order_rank": 1,
        }],
        "planner_overlay_gate": {"m4_planner_integration_completed": False},
        "errors": [],
        "stop_reason": "NONE",
    }


def _runtime_index(consumer: dict) -> dict:
    rows: list[dict] = []
    readiness = {
        "LISTENING": "BLOCKED_AUDIO_GENERATION",
        "SPEAKING": "BLOCKED_RECORDING_CAPTURE",
        "READING": "QUERYABLE_TEXT_RUNTIME_CONTRACT",
        "WRITING": "QUERYABLE_TEXT_RUNTIME_CONTRACT",
    }
    for skill, lesson_id, asset_id, _, _ in SKILL_SPECS:
        rows.append({
            "runtime_activity_id": f"CP07A:KET:{skill}",
            "source_kind": "KET_ASSET_BODY",
            "skill": skill,
            "level": "A1",
            "curriculum_binding": {
                "ket_lesson_id": lesson_id,
                "ket_lesson_node_id": f"LESSON:{skill}:{lesson_id}",
                "requirement_node_ids": [],
                "learning_unit_id": None,
                "grammar_unit_id": None,
                "canonical_egp_row_ids": [],
            },
            "instructional_roles": ["FOCUS", "EVD"],
            "source_lineage": {"m2_asset_key": f"{skill}:{asset_id}", "m2_content_digest": "a" * 64},
            "response_contract_ref": {
                "authority": "KET_ASSET_BODY_PRIVATE_PAYLOAD",
                "contract_resolution_status": "RESOLVE_AT_M5_DELIVERY",
            },
            "runtime_readiness": "QUERYABLE_PRIVATE_KET_ASSET",
            "learner_facing": False,
            "a2_payload_included": False,
        })
        for index, role in enumerate(cp07c.CONTEXT_ROLES, start=1):
            rows.append({
                "runtime_activity_id": f"CP07A:RAZ:{skill}:{role}",
                "source_kind": "RAZ_ACTIVITY_BINDING",
                "skill": skill,
                "level": "A1",
                "curriculum_binding": {
                    "ket_lesson_id": None,
                    "ket_lesson_node_id": None,
                    "requirement_node_ids": [],
                    "learning_unit_id": LEARNING_ID,
                    "grammar_unit_id": GRAMMAR_ID,
                    "canonical_egp_row_ids": ["EGP_BE_001"],
                },
                "instructional_roles": ["FOCUS", role] if role != "FOCUS" else ["FOCUS"],
                "source_lineage": {
                    "cp05_activity_binding_id": f"RAZ-{skill}-{role}",
                    "cp05_material_id": f"MAT-{skill}-{index}",
                    "cp05_source_unit_ref": f"RAZ-A-{index}",
                    "cp05_source_content_sha256": f"{index:064x}"[-64:],
                },
                "response_contract_ref": {
                    "authority": "CP05_APPROVED_SKILL_CONTRACT",
                    "skill_contract_sha256": "d" * 64,
                    "prompt_sha256": "e" * 64,
                    "scoring_contract_sha256": "f" * 64,
                    "contract_resolution_status": "RESOLVE_AT_M5_DELIVERY",
                },
                "runtime_readiness": readiness[skill],
                "learner_facing": False,
                "a2_payload_included": False,
            })
        rows.append({
            "runtime_activity_id": f"CP07A:M11B:{skill}",
            "source_kind": "M11B_REVIEWED_ACTIVITY",
            "skill": skill,
            "level": "A1",
            "curriculum_binding": {
                "ket_lesson_id": None,
                "ket_lesson_node_id": None,
                "requirement_node_ids": [],
                "learning_unit_id": LEARNING_ID,
                "grammar_unit_id": GRAMMAR_ID,
                "canonical_egp_row_ids": [],
            },
            "instructional_roles": ["FOCUS"],
            "source_lineage": {
                "cp05_m11b_activity_id": f"M11B-{skill}",
                "m11b_source_item_ref": f"M11B-PRIVATE-{skill}",
            },
            "response_contract_ref": {
                "authority": "EXISTING_M11B_REVIEWED_CONTENT_STORE",
                "contract_resolution_status": "PENDING_CP07C_OR_CP07D_RESOLUTION",
            },
            "runtime_readiness": "PENDING_REVIEWED_PAYLOAD_RESOLUTION",
            "learner_facing": False,
            "a2_payload_included": False,
        })
    return {
        "task_id": cp07a.TASK_ID,
        "program_id": cp07a.PROGRAM_ID,
        "schema_version": cp07a.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {"m2_consumer_sha256": cp07c._digest(consumer)},
        "runtime_activities": rows,
        "errors": [],
        "stop_reason": "NONE",
    }


def _plan(skill: str, lesson_id: str, ref: str | None) -> dict:
    return {
        "task_id": m4.TASK_ID,
        "validation_status": m4.STATUS,
        "plan_id": f"plan-r3c-{skill.lower()}",
        "learner_id": "learner-r3c",
        "plan_status": "PLAN_LEARNING_LESSON",
        "selected_lesson": {
            "lesson_id": lesson_id,
            "lesson_node_id": f"LESSON:{skill}:{lesson_id}",
            "skill": skill,
            "level": "A1",
            "roles": ["EVD"],
            "requirement_node_ids": [] if ref is None else [f"REF:{skill}:{ref}"],
        },
        "rationale": {"reason": "PREREQUISITES_SATISFIED_BALANCED_SKILL_SELECTION"},
        "a2_lock": {
            "a2_lock_state": "LOCKED",
            "a2_payload_access_granted": False,
            "a2_session_start_granted": False,
            "required_mastery_count": 1,
            "missing_mastery_count": 1,
        },
        "a2_payload_included": False,
        "a2_session_started": False,
        "next_short_step": m4.NEXT_SHORT_STEP,
    }


def _inputs() -> tuple[dict, dict, dict, dict]:
    graph = _graph()
    consumer = _consumer()
    overlay = _overlay(graph)
    return graph, consumer, overlay, _runtime_index(consumer)


def test_bridge_resolves_root_and_opaque_ids_without_manual_mapping() -> None:
    graph, consumer, overlay, _ = _inputs()
    artifact = bridge_builder.build_artifact(graph, consumer, overlay)
    rows = {row["lesson_id"]: row for row in artifact["lesson_semantic_bridges"]}
    assert len(rows) == 4
    assert rows["KETL-LF-L001"]["anchor_mode"] == "ROOT_LESSON_ASSET_AUTHORITY"
    assert rows["KETL-LF-L001"]["requirement_node_ids"] == []
    assert all(row["resolution_status"] == "RESOLVED" for row in rows.values())
    assert all(row["grammar_unit_ids"] == [GRAMMAR_ID] for row in rows.values())
    assert artifact["coverage_summary"]["new_hard_prerequisite_edge_count"] == 0
    bridge_builder._walk_forbidden(artifact)
    assert "Be present affirmative" not in str(artifact)


def test_bridge_validator_rebuilds_deterministically() -> None:
    graph, consumer, overlay, _ = _inputs()
    artifact = bridge_builder.build_artifact(graph, consumer, overlay)
    report = bridge_validator.validate_artifact(
        artifact, m1_graph=graph, m2_consumer=consumer, cp07b_overlay=overlay
    )
    assert report["validation_status"] == bridge_builder.PASS_STATUS, report["errors"]
    assert report["deterministic_rebuild_matches"] is True
    assert report["private_payload_text_absent"] is True
    assert report["hard_graph_unchanged"] is True


@pytest.mark.parametrize("skill,lesson_id,asset_id,ref,semantic_field", SKILL_SPECS)
def test_four_skill_composition_is_cp07c_and_cp07d_compatible(
    skill: str, lesson_id: str, asset_id: str, ref: str | None, semantic_field: str
) -> None:
    graph, consumer, overlay, runtime_index = _inputs()
    bridge = bridge_builder.build_artifact(graph, consumer, overlay)
    plan = _plan(skill, lesson_id, ref)
    artifact = composition_builder.build_composition(
        plan, consumer, graph, runtime_index, overlay, bridge
    )
    assert artifact["selected_lesson"] == plan["selected_lesson"]
    assert artifact["cp07c_task_id"] == cp07c.TASK_ID
    assert artifact["cp07c_validation_status"] == cp07c.PASS_STATUS
    summary = artifact["unified_lesson_composition"]["coverage_summary"]
    assert summary["ket_asset_count"] == 1
    assert summary["raz_contextual_activity_count"] == 4
    assert summary["m11b_checkpoint_count"] == 1
    assert summary["bridged_grammar_unit_count"] == 1
    selected, raz_items = cp07d._verify_cp07c(artifact, consumer)
    assert selected["lesson_id"] == lesson_id
    assert len(raz_items) == 4
    report = composition_validator.validate_artifact(
        artifact,
        m4_plan=plan,
        m2_consumer=consumer,
        m1_graph=graph,
        cp07a_index=runtime_index,
        cp07b_overlay=overlay,
        semantic_bridge=bridge,
    )
    assert report["validation_status"] == composition_builder.PASS_STATUS, report["errors"]
    assert report["m4_selected_lesson_unchanged"] is True
    assert report["cp07d_contract_compatible"] is True


def test_root_without_authority_target_fails_closed() -> None:
    graph, consumer, overlay, runtime_index = _inputs()
    consumer = deepcopy(consumer)
    listening = next(row for row in consumer["asset_records"] if row["skill"] == "LISTENING")
    listening["payload"] = {"operational_note": "play the audio"}
    runtime_index = _runtime_index(consumer)
    bridge = bridge_builder.build_artifact(graph, consumer, overlay)
    root = next(row for row in bridge["lesson_semantic_bridges"] if row["lesson_id"] == "KETL-LF-L001")
    assert root["resolution_status"] == "UNRESOLVED"
    with pytest.raises(composition_builder.SemanticCompositionError, match="semantic_bridge_selected_lesson_unresolved"):
        composition_builder.build_composition(
            _plan("LISTENING", "KETL-LF-L001", None),
            consumer,
            graph,
            runtime_index,
            overlay,
            bridge,
        )


def test_opaque_requirement_id_alone_does_not_create_mapping() -> None:
    graph, consumer, overlay, _ = _inputs()
    consumer = deepcopy(consumer)
    speaking = next(row for row in consumer["asset_records"] if row["skill"] == "SPEAKING")
    speaking["payload"] = {"resource_code": "EGP-SPK-001"}
    bridge = bridge_builder.build_artifact(graph, consumer, overlay)
    row = next(item for item in bridge["lesson_semantic_bridges"] if item["lesson_id"] == "SF-00-L01")
    assert row["resolution_status"] == "UNRESOLVED"
    assert row["grammar_unit_ids"] == []
    assert row["matched_requirement_node_ids"] == []
