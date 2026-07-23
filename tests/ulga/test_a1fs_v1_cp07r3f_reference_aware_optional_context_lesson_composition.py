from __future__ import annotations

from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_v1_cp07a_unified_runtime_activity_contract_and_lineage_adapter as cp07a
from ulga.builders import build_a1fs_v1_cp07r3e_ket99_lesson_instructional_reference_overlay as r3e
from ulga.builders import build_a1fs_v1_cp07r3f_reference_aware_optional_context_lesson_composition as builder
from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.builders import build_a1fs_v1_m4_lesson_planner_selection_a2_lock as m4
from ulga.validators import validate_a1fs_v1_cp07r3f_reference_aware_optional_context_lesson_composition as validator


LESSONS = {
    "LISTENING": {
        "lesson_id": "KETL-LF-L001",
        "lesson_node_id": "LESSON:LISTENING:KETL-LF-L001",
        "skill": "LISTENING",
        "level": "A1",
        "asset_keys": ["LISTENING:L1"],
        "roles": ["EVD"],
        "requirement_node_ids": [],
    },
    "SPEAKING": {
        "lesson_id": "KETS-SF-L001",
        "lesson_node_id": "LESSON:SPEAKING:KETS-SF-L001",
        "skill": "SPEAKING",
        "level": "A1",
        "asset_keys": ["SPEAKING:S1"],
        "roles": ["EVD"],
        "requirement_node_ids": ["REF:SPEAKING:SPEAK-A"],
    },
    "READING": {
        "lesson_id": "KETR-RF-L001",
        "lesson_node_id": "LESSON:READING:KETR-RF-L001",
        "skill": "READING",
        "level": "A1",
        "asset_keys": ["READING:R1"],
        "roles": ["EVD"],
        "requirement_node_ids": ["REF:READING:READ-A"],
    },
    "WRITING": {
        "lesson_id": "KETW-WF-L001",
        "lesson_node_id": "LESSON:WRITING:KETW-WF-L001",
        "skill": "WRITING",
        "level": "A1",
        "asset_keys": ["WRITING:W1"],
        "roles": ["EVD"],
        "requirement_node_ids": ["REF:WRITING:WRITE-A"],
    },
}


def _graph() -> dict:
    nodes = [
        {
            "node_id": lesson["lesson_node_id"],
            "node_type": "LESSON",
            "skill": lesson["skill"],
            "level": lesson["level"],
            "source_ref": lesson["lesson_id"],
        }
        for lesson in LESSONS.values()
    ]
    nodes.extend(
        {
            "node_id": requirement_id,
            "node_type": "CAPABILITY",
            "skill": lesson["skill"],
            "level": "A1",
            "source_ref": requirement_id.rsplit(":", 1)[-1],
        }
        for lesson in LESSONS.values()
        for requirement_id in lesson["requirement_node_ids"]
    )
    nodes.append(
        {
            "node_id": "GATE:A1FS:A2_LOCK",
            "node_type": "A2_LOCK",
            "skill": "FOUR_SKILL",
            "level": "A2",
            "source_ref": "A2_ENTRY",
        }
    )
    return {
        "task_id": m1.TASK_ID,
        "schema_version": m1.SCHEMA_VERSION,
        "validation_status": m1.STATUS,
        "nodes": nodes,
        "edges": [],
        "coverage": [],
        "counts": {"edge_count": 0},
        "a2_lock_contract": {"state": "LOCKED_BY_DESIGN"},
        "errors": [],
    }


def _consumer() -> dict:
    assets = []
    for index, lesson in enumerate(LESSONS.values(), start=1):
        asset_key = lesson["asset_keys"][0]
        assets.append(
            {
                "asset_id": f"A{index}",
                "asset_key": asset_key,
                "lesson_id": lesson["lesson_id"],
                "skill": lesson["skill"],
                "level": lesson["level"],
                "role": "EVD",
                "payload": {"body_title": f"private-{index}"},
                "content_digest": f"{index}" * 64,
            }
        )
    return {
        "task_id": m2.TASK_ID,
        "schema_version": m2.SCHEMA_VERSION,
        "validation_status": m2.STATUS,
        "lesson_catalog": [deepcopy(lesson) for lesson in LESSONS.values()],
        "asset_records": assets,
        "counts": {"learning_lesson_count": len(LESSONS), "asset_record_count": len(assets)},
        "access_contract": {"a2_payload_query_allowed": False},
        "errors": [],
    }


def _runtime_index(consumer: dict) -> dict:
    rows = []
    for lesson in LESSONS.values():
        asset_key = lesson["asset_keys"][0]
        rows.append(
            {
                "runtime_activity_id": f"KET:{asset_key}",
                "source_kind": "KET_ASSET_BODY",
                "skill": lesson["skill"],
                "level": "A1",
                "curriculum_binding": {
                    "ket_lesson_id": lesson["lesson_id"],
                    "ket_lesson_node_id": lesson["lesson_node_id"],
                    "requirement_node_ids": lesson["requirement_node_ids"],
                    "learning_unit_id": None,
                    "grammar_unit_id": None,
                    "canonical_egp_row_ids": [],
                },
                "instructional_roles": ["FOCUS", "EVD"],
                "source_lineage": {"m2_asset_key": asset_key, "m2_content_digest": "a" * 64},
                "response_contract_ref": {"authority": "KET_ASSET_BODY_PRIVATE_PAYLOAD"},
                "runtime_readiness": "QUERYABLE_PRIVATE_KET_ASSET",
                "learner_facing": False,
                "a2_payload_included": False,
            }
        )
    rows.extend(
        [
            {
                "runtime_activity_id": "RAZ:READING:FOCUS",
                "source_kind": "RAZ_ACTIVITY_BINDING",
                "skill": "READING",
                "level": "A1",
                "curriculum_binding": {
                    "ket_lesson_id": None,
                    "ket_lesson_node_id": None,
                    "requirement_node_ids": [],
                    "learning_unit_id": "UNIT:BE",
                    "grammar_unit_id": "GRAMMAR_BE_VERB_BASIC",
                    "canonical_egp_row_ids": [],
                },
                "instructional_roles": ["FOCUS"],
                "source_lineage": {
                    "cp05_activity_binding_id": "BIND:READ:1",
                    "cp05_material_id": "MAT:READ:1",
                },
                "response_contract_ref": {"authority": "CP05_APPROVED_SKILL_CONTRACT"},
                "runtime_readiness": "QUERYABLE_TEXT_RUNTIME_CONTRACT",
                "learner_facing": False,
                "a2_payload_included": False,
            },
            {
                "runtime_activity_id": "M11B:READING:1",
                "source_kind": "M11B_REVIEWED_ACTIVITY",
                "skill": "READING",
                "level": "A1",
                "curriculum_binding": {
                    "ket_lesson_id": None,
                    "ket_lesson_node_id": None,
                    "requirement_node_ids": [],
                    "learning_unit_id": "UNIT:BE",
                    "grammar_unit_id": "GRAMMAR_BE_VERB_BASIC",
                    "canonical_egp_row_ids": [],
                },
                "instructional_roles": ["FOCUS"],
                "source_lineage": {"cp05_m11b_activity_id": "M11B:READ:1"},
                "response_contract_ref": {"authority": "EXISTING_M11B_REVIEWED_CONTENT_STORE"},
                "runtime_readiness": "PENDING_REVIEWED_PAYLOAD_RESOLUTION",
                "learner_facing": False,
                "a2_payload_included": False,
            },
        ]
    )
    return {
        "task_id": cp07a.TASK_ID,
        "schema_version": cp07a.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {"m2_consumer_sha256": builder.cp07c._digest(consumer)},
        "runtime_activities": rows,
        "errors": [],
        "stop_reason": "NONE",
    }


def _reference_overlay(graph: dict, consumer: dict) -> dict:
    rows = []
    for lesson in LESSONS.values():
        references = []
        if lesson["skill"] == "READING":
            references = [
                {
                    "evidence_occurrence_id": "P001:01",
                    "transcript_id": "P001",
                    "source_evidence_sha256": "d" * 64,
                    "instructional_roles": ["INTRO", "FOCUS"],
                    "canonical_target_refs": [
                        {"target_type": "GRAMMAR_UNIT", "target_id": "GRAMMAR_BE_VERB_BASIC"},
                        {"target_type": "M1_NODE", "target_id": "REF:READING:READ-A"},
                    ],
                    "mapping_basis": ["EXACT_CP07B_M1_NODE_TARGET"],
                    "runtime_effect": "OPTIONAL_TEACHING_REFERENCE_ONLY",
                }
            ]
        rows.append(
            {
                "lesson_id": lesson["lesson_id"],
                "lesson_node_id": lesson["lesson_node_id"],
                "skill": lesson["skill"],
                "level": lesson["level"],
                "requirement_node_ids": lesson["requirement_node_ids"],
                "reference_status": "REFERENCED" if references else "NO_EXACT_KET99_REFERENCE",
                "instructional_references": references,
                "delivery_blocked_by_missing_reference": False,
                "hard_lesson_selection_changed": False,
            }
        )
    return {
        "task_id": r3e.TASK_ID,
        "schema_version": r3e.SCHEMA_VERSION,
        "validation_status": r3e.PASS_STATUS,
        "source_identity": {
            "m1_hard_graph_sha256": builder.cp07c._digest(graph),
            "m2_consumer_sha256": builder.cp07c._digest(consumer),
            "cp07b_instructional_overlay_sha256": "b" * 64,
            "r3c_semantic_bridge_sha256": "c" * 64,
        },
        "authority_contract": {
            "source_role": "NON_AUTHORITATIVE_KET_TEACHER_DELIVERY_REFERENCE",
            "hard_graph_mutation_allowed": False,
            "hard_lesson_selection_allowed": False,
            "mastery_gate_creation_allowed": False,
            "delivery_block_on_missing_reference_allowed": False,
            "fuzzy_matching_allowed": False,
            "a2_a2plus_status": "LOCKED",
        },
        "lesson_instructional_references": rows,
        "errors": [],
        "stop_reason": "NONE",
    }


def _plan(skill: str) -> dict:
    return {
        "task_id": m4.TASK_ID,
        "schema_version": m4.SCHEMA_VERSION,
        "validation_status": m4.STATUS,
        "plan_id": f"PLAN:{skill}",
        "learner_id": "learner-001",
        "plan_status": "PLAN_LEARNING_LESSON",
        "selected_lesson": deepcopy(LESSONS[skill]),
        "a2_lock": {
            "a2_lock_state": "LOCKED",
            "a2_payload_access_granted": False,
            "a2_session_start_granted": False,
        },
        "a2_payload_included": False,
        "a2_session_started": False,
        "next_short_step": m4.NEXT_SHORT_STEP,
    }


def _inputs(skill: str) -> tuple[dict, dict, dict, dict, dict]:
    graph = _graph()
    consumer = _consumer()
    return _plan(skill), consumer, graph, _runtime_index(consumer), _reference_overlay(graph, consumer)


@pytest.mark.parametrize("skill", ["LISTENING", "SPEAKING", "WRITING"])
def test_unreferenced_lesson_is_ket_only_and_not_blocked(skill: str) -> None:
    plan, consumer, graph, runtime_index, overlay = _inputs(skill)
    artifact = builder.build_composition(plan, consumer, graph, runtime_index, overlay)
    composition = artifact["unified_lesson_composition"]
    assert composition["composition_mode"] == "KET_ONLY_NO_EXACT_KET99_REFERENCE"
    assert composition["instructional_references"] == []
    assert composition["bridged_grammar_unit_ids"] == []
    assert {row["source_kind"] for row in composition["composition_items"]} == {"KET_ASSET_BODY"}
    assert composition["consumer_gate"]["missing_reference_blocks_delivery"] is False
    report = validator.validate_artifact(
        artifact,
        m4_plan=plan,
        m2_consumer=consumer,
        m1_graph=graph,
        cp07a_index=runtime_index,
        r3e_overlay=overlay,
    )
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert report["deterministic_rebuild_matches"] is True


def test_referenced_reading_lesson_adds_optional_context() -> None:
    plan, consumer, graph, runtime_index, overlay = _inputs("READING")
    artifact = builder.build_composition(plan, consumer, graph, runtime_index, overlay)
    composition = artifact["unified_lesson_composition"]
    assert composition["composition_mode"] == "KET_WITH_KET99_REFERENCE_AND_OPTIONAL_CONTEXT"
    assert len(composition["instructional_references"]) == 1
    assert composition["bridged_grammar_unit_ids"] == ["GRAMMAR_BE_VERB_BASIC"]
    assert {row["source_kind"] for row in composition["composition_items"]} == {
        "KET_ASSET_BODY",
        "RAZ_ACTIVITY_BINDING",
        "M11B_REVIEWED_ACTIVITY",
    }
    assert composition["coverage_summary"]["raz_contextual_activity_count"] == 1
    assert composition["coverage_summary"]["m11b_checkpoint_count"] == 1
    report = validator.validate_artifact(
        artifact,
        m4_plan=plan,
        m2_consumer=consumer,
        m1_graph=graph,
        cp07a_index=runtime_index,
        r3e_overlay=overlay,
    )
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]


def test_reference_without_grammar_remains_ket_only() -> None:
    plan, consumer, graph, runtime_index, overlay = _inputs("READING")
    reference = overlay["lesson_instructional_references"][2]["instructional_references"][0]
    reference["canonical_target_refs"] = [
        {"target_type": "M1_NODE", "target_id": "REF:READING:READ-A"}
    ]
    artifact = builder.build_composition(plan, consumer, graph, runtime_index, overlay)
    composition = artifact["unified_lesson_composition"]
    assert composition["composition_mode"] == "KET_WITH_KET99_REFERENCE_NO_GRAMMAR_CONTEXT"
    assert composition["bridged_grammar_unit_ids"] == []
    assert {row["source_kind"] for row in composition["composition_items"]} == {"KET_ASSET_BODY"}
    report = validator.validate_artifact(
        artifact,
        m4_plan=plan,
        m2_consumer=consumer,
        m1_graph=graph,
        cp07a_index=runtime_index,
        r3e_overlay=overlay,
    )
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]


def test_missing_ket_asset_bundle_fails_closed() -> None:
    plan, consumer, graph, runtime_index, overlay = _inputs("READING")
    runtime_index["runtime_activities"] = [
        row
        for row in runtime_index["runtime_activities"]
        if row["runtime_activity_id"] != "KET:READING:R1"
    ]
    with pytest.raises(builder.ReferenceAwareCompositionError, match="KET_ASSET_BUNDLE_NOT_RECONCILED"):
        builder.build_composition(plan, consumer, graph, runtime_index, overlay)


def test_missing_reference_cannot_be_changed_into_delivery_block() -> None:
    plan, consumer, graph, runtime_index, overlay = _inputs("LISTENING")
    artifact = builder.build_composition(plan, consumer, graph, runtime_index, overlay)
    tampered = deepcopy(artifact)
    tampered["unified_lesson_composition"]["consumer_gate"]["missing_reference_blocks_delivery"] = True
    report = validator.validate_artifact(
        tampered,
        m4_plan=plan,
        m2_consumer=consumer,
        m1_graph=graph,
        cp07a_index=runtime_index,
        r3e_overlay=overlay,
    )
    assert report["validation_status"] != builder.PASS_STATUS
    assert "missing_reference_blocks_delivery" in report["errors"]
