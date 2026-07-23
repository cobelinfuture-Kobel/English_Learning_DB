from __future__ import annotations

from copy import deepcopy

from ulga.builders import build_a1fs_v1_cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay as cp07b
from ulga.builders import build_a1fs_v1_cp07r3c_ket_authority_semantic_bridge as r3c
from ulga.builders import build_a1fs_v1_cp07r3e_ket99_lesson_instructional_reference_overlay as builder
from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.validators import validate_a1fs_v1_cp07r3e_ket99_lesson_instructional_reference_overlay as validator


def _graph() -> dict:
    return {
        "task_id": m1.TASK_ID,
        "schema_version": m1.SCHEMA_VERSION,
        "validation_status": m1.STATUS,
        "nodes": [
            {"node_id": "REF:READING:READ-A", "node_type": "CAPABILITY", "skill": "READING", "level": "A1", "source_ref": "READ-A"},
            {"node_id": "REF:WRITING:WRITE-A", "node_type": "CAPABILITY", "skill": "WRITING", "level": "A1", "source_ref": "WRITE-A"},
            {"node_id": "GATE:A1FS:A2_LOCK", "node_type": "A2_LOCK", "skill": "FOUR_SKILL", "level": "A2", "source_ref": "A2_ENTRY"},
        ],
        "edges": [],
        "coverage": [],
        "counts": {"edge_count": 0},
        "a2_lock_contract": {"state": "LOCKED_BY_DESIGN"},
        "errors": [],
    }


def _consumer() -> dict:
    lessons = [
        {
            "lesson_id": "KETR-RF-L001",
            "lesson_node_id": "LESSON:READING:KETR-RF-L001",
            "skill": "READING",
            "level": "A1",
            "asset_keys": ["READING:R1"],
            "roles": ["EVD"],
            "requirement_node_ids": ["REF:READING:READ-A"],
        },
        {
            "lesson_id": "KETW-WF-L001",
            "lesson_node_id": "LESSON:WRITING:KETW-WF-L001",
            "skill": "WRITING",
            "level": "A1",
            "asset_keys": ["WRITING:W1"],
            "roles": ["EVD"],
            "requirement_node_ids": ["REF:WRITING:WRITE-A"],
        },
        {
            "lesson_id": "KETL-LF-L001",
            "lesson_node_id": "LESSON:LISTENING:KETL-LF-L001",
            "skill": "LISTENING",
            "level": "A1",
            "asset_keys": ["LISTENING:L1"],
            "roles": ["EVD"],
            "requirement_node_ids": [],
        },
    ]
    assets = [
        {"asset_id": "R1", "asset_key": "READING:R1", "lesson_id": "KETR-RF-L001", "skill": "READING", "level": "A1", "role": "EVD", "payload": {"target_language": "read a name"}, "content_digest": "a" * 64},
        {"asset_id": "W1", "asset_key": "WRITING:W1", "lesson_id": "KETW-WF-L001", "skill": "WRITING", "level": "A1", "role": "EVD", "payload": {"body_title": "write a name"}, "content_digest": "b" * 64},
        {"asset_id": "L1", "asset_key": "LISTENING:L1", "lesson_id": "KETL-LF-L001", "skill": "LISTENING", "level": "A1", "role": "EVD", "payload": {"operational_note": "play audio"}, "content_digest": "c" * 64},
    ]
    return {
        "task_id": m2.TASK_ID,
        "schema_version": m2.SCHEMA_VERSION,
        "validation_status": m2.STATUS,
        "lesson_catalog": lessons,
        "asset_records": assets,
        "counts": {"learning_lesson_count": 3},
        "access_contract": {"a2_payload_query_allowed": False},
        "errors": [],
    }


def _overlay(graph: dict) -> dict:
    return {
        "task_id": cp07b.TASK_ID,
        "schema_version": cp07b.SCHEMA_VERSION,
        "source_identity": {"m1_hard_graph_sha256": builder._digest(graph)},
        "authority_contract": {"hard_graph_mutation_allowed": False, "a2_a2plus_status": "LOCKED"},
        "transcript_overlays": [
            {
                "transcript_id": "P001",
                "source_lineage": {"source_evidence_sha256": "d" * 64},
                "evidence_occurrences": [
                    {
                        "evidence_occurrence_id": "P001:01",
                        "instructional_roles": ["INTRO", "FOCUS"],
                        "canonical_targets": [
                            {"target_type": "M1_NODE", "target_id": "REF:READING:READ-A"},
                            {"target_type": "GRAMMAR_UNIT", "target_id": "GRAMMAR_BE_VERB_BASIC"},
                        ],
                    }
                ],
            },
            {
                "transcript_id": "P002",
                "source_lineage": {"source_evidence_sha256": "e" * 64},
                "evidence_occurrences": [
                    {
                        "evidence_occurrence_id": "P002:01",
                        "instructional_roles": ["REVIEW"],
                        "canonical_targets": [
                            {"target_type": "GRAMMAR_UNIT", "target_id": "GRAMMAR_PERSONAL_INFORMATION"}
                        ],
                    }
                ],
            },
        ],
        "errors": [],
        "stop_reason": "NONE",
    }


def _bridge(graph: dict, consumer: dict, overlay: dict) -> dict:
    rows = []
    for lesson in consumer["lesson_catalog"]:
        evidence = []
        if lesson["lesson_id"] == "KETW-WF-L001":
            evidence = [
                {
                    "authority_asset_key": "WRITING:W1",
                    "authority_asset_id": "W1",
                    "authority_payload_path": "$.body_title",
                    "authority_scalar_sha256": "f" * 64,
                    "normalized_semantic_key": "write_a_name",
                    "match_mode": "EXACT_NORMALIZED_AUTHORITY_TEXT",
                    "cp07b_evidence_occurrence_id": "P002:01",
                    "cp07b_transcript_id": "P002",
                    "cp07b_source_evidence_sha256": "e" * 64,
                    "grammar_unit_ids": ["GRAMMAR_PERSONAL_INFORMATION"],
                }
            ]
        rows.append(
            {
                "lesson_id": lesson["lesson_id"],
                "lesson_node_id": lesson["lesson_node_id"],
                "skill": lesson["skill"],
                "level": lesson["level"],
                "anchor_mode": "ROOT_LESSON_ASSET_AUTHORITY" if not lesson["requirement_node_ids"] else "REQUIREMENT_ASSET_AUTHORITY",
                "requirement_node_ids": lesson["requirement_node_ids"],
                "matched_requirement_node_ids": lesson["requirement_node_ids"] if evidence else [],
                "grammar_unit_ids": ["GRAMMAR_PERSONAL_INFORMATION"] if evidence else [],
                "authority_evidence": evidence,
                "requirement_resolutions": [],
                "resolution_status": "RESOLVED" if evidence else "UNRESOLVED",
                "unresolved_reason": None if evidence else "NO_EXACT_TARGET",
            }
        )
    return {
        "task_id": r3c.TASK_ID,
        "schema_version": r3c.SCHEMA_VERSION,
        "validation_status": r3c.PASS_STATUS,
        "source_identity": {
            "m1_hard_graph_sha256": builder._digest(graph),
            "m2_consumer_sha256": builder._digest(consumer),
            "cp07b_instructional_overlay_sha256": builder._digest(overlay),
        },
        "lesson_semantic_bridges": rows,
        "errors": [],
        "stop_reason": "NONE",
    }


def _inputs() -> tuple[dict, dict, dict, dict]:
    graph = _graph()
    consumer = _consumer()
    overlay = _overlay(graph)
    return graph, consumer, overlay, _bridge(graph, consumer, overlay)


def test_all_lessons_are_indexed_and_missing_reference_does_not_block() -> None:
    graph, consumer, overlay, bridge = _inputs()
    artifact = builder.build_artifact(graph, consumer, overlay, bridge)
    rows = {row["lesson_id"]: row for row in artifact["lesson_instructional_references"]}
    assert set(rows) == {"KETR-RF-L001", "KETW-WF-L001", "KETL-LF-L001"}
    assert rows["KETR-RF-L001"]["reference_status"] == "REFERENCED"
    assert rows["KETW-WF-L001"]["reference_status"] == "REFERENCED"
    assert rows["KETL-LF-L001"]["reference_status"] == "NO_EXACT_KET99_REFERENCE"
    assert rows["KETL-LF-L001"]["instructional_references"] == []
    assert all(row["delivery_blocked_by_missing_reference"] is False for row in rows.values())
    assert artifact["coverage_summary"]["blocked_lesson_count"] == 0
    assert artifact["authority_contract"]["hard_lesson_selection_allowed"] is False
    assert artifact["authority_contract"]["delivery_block_on_missing_reference_allowed"] is False
    builder._walk_forbidden(artifact)


def test_reference_overlay_validator_rebuilds_deterministically() -> None:
    graph, consumer, overlay, bridge = _inputs()
    artifact = builder.build_artifact(graph, consumer, overlay, bridge)
    report = validator.validate_artifact(
        artifact,
        m1_graph=graph,
        m2_consumer=consumer,
        cp07b_overlay=overlay,
        r3c_bridge=bridge,
    )
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert report["deterministic_rebuild_matches"] is True
    assert report["learning_lesson_count"] == 3
    assert report["referenced_lesson_count"] == 2
    assert report["unreferenced_lesson_count"] == 1
    assert report["blocked_lesson_count"] == 0
    assert report["hard_graph_unchanged"] is True


def test_missing_reference_cannot_be_changed_into_delivery_block() -> None:
    graph, consumer, overlay, bridge = _inputs()
    artifact = builder.build_artifact(graph, consumer, overlay, bridge)
    tampered = deepcopy(artifact)
    root = next(row for row in tampered["lesson_instructional_references"] if row["lesson_id"] == "KETL-LF-L001")
    root["delivery_blocked_by_missing_reference"] = True
    report = validator.validate_artifact(
        tampered,
        m1_graph=graph,
        m2_consumer=consumer,
        cp07b_overlay=overlay,
        r3c_bridge=bridge,
    )
    assert report["validation_status"] != builder.PASS_STATUS
    assert "missing_reference_blocks_delivery:KETL-LF-L001" in report["errors"]
