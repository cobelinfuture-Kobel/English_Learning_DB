from __future__ import annotations

from copy import deepcopy

from ulga.builders import build_a1fs_v1_cp07b_ket99_canonical_mapping_and_instructional_sequence_overlay as cp07b
from ulga.builders import build_a1fs_v1_cp07r3e_ket99_lesson_instructional_reference_overlay as r3e
from ulga.builders import build_a1fs_v1_cp07r3g_ket99_full_semantic_inventory_and_a1a1plus_coverage_expansion as builder
from ulga.builders import build_a1fs_v1_m1_prerequisite_graph_and_coverage as m1
from ulga.builders import build_a1fs_v1_m2_four_skill_asset_body_consumer as m2
from ulga.validators import validate_a1fs_v1_cp07r3g_ket99_full_semantic_inventory_and_a1a1plus_coverage_expansion as validator


def graph() -> dict:
    nodes = [
        {
            "node_id": "REF:LISTENING:ASK_NAME",
            "node_type": "CAPABILITY",
            "skill": "LISTENING",
            "level": "A1",
            "source_ref": "ask_name",
        },
        {
            "node_id": "REF:SPEAKING:ASK_NAME",
            "node_type": "CAPABILITY",
            "skill": "SPEAKING",
            "level": "A1",
            "source_ref": "ask_name",
        },
        {
            "node_id": "REF:READING:DETAIL",
            "node_type": "CAPABILITY",
            "skill": "READING",
            "level": "A1",
            "source_ref": "keyword_location",
        },
        {
            "node_id": "REF:WRITING:MESSAGE",
            "node_type": "CAPABILITY",
            "skill": "WRITING",
            "level": "A1+",
            "source_ref": "write_message",
        },
        {
            "node_id": "GATE:A1FS:A2_LOCK",
            "node_type": "A2_LOCK",
            "skill": "FOUR_SKILL",
            "level": "A2",
            "source_ref": "A2_ENTRY",
        },
    ]
    return {
        "task_id": m1.TASK_ID,
        "schema_version": m1.SCHEMA_VERSION,
        "validation_status": m1.STATUS,
        "nodes": nodes,
        "edges": [],
        "coverage": [],
        "counts": {"node_count": len(nodes), "edge_count": 0},
        "a2_lock_contract": {"state": "LOCKED_BY_DESIGN"},
        "errors": [],
    }


def consumer() -> dict:
    lessons = [
        {
            "lesson_id": "KETL-LF-L001",
            "lesson_node_id": "LESSON:LISTENING:KETL-LF-L001",
            "skill": "LISTENING",
            "level": "A1",
            "asset_keys": ["LISTENING:L1"],
            "roles": ["AUD", "CHK"],
            "requirement_node_ids": ["REF:LISTENING:ASK_NAME"],
        },
        {
            "lesson_id": "KETS-SF-L001",
            "lesson_node_id": "LESSON:SPEAKING:KETS-SF-L001",
            "skill": "SPEAKING",
            "level": "A1",
            "asset_keys": ["SPEAKING:S1"],
            "roles": ["PRD"],
            "requirement_node_ids": ["REF:SPEAKING:ASK_NAME"],
        },
        {
            "lesson_id": "KETR-RF-L001",
            "lesson_node_id": "LESSON:READING:KETR-RF-L001",
            "skill": "READING",
            "level": "A1",
            "asset_keys": ["READING:R1"],
            "roles": ["FOC"],
            "requirement_node_ids": ["REF:READING:DETAIL"],
        },
        {
            "lesson_id": "KETW-WF-L001",
            "lesson_node_id": "LESSON:WRITING:KETW-WF-L001",
            "skill": "WRITING",
            "level": "A1+",
            "asset_keys": ["WRITING:W1"],
            "roles": ["PRD"],
            "requirement_node_ids": ["REF:WRITING:MESSAGE"],
        },
    ]
    assets = [
        {
            "asset_id": "L1",
            "asset_key": "LISTENING:L1",
            "lesson_id": "KETL-LF-L001",
            "skill": "LISTENING",
            "level": "A1",
            "role": "CHK",
            "payload": {"target_language": "ask name"},
            "content_digest": "a" * 64,
        },
        {
            "asset_id": "S1",
            "asset_key": "SPEAKING:S1",
            "lesson_id": "KETS-SF-L001",
            "skill": "SPEAKING",
            "level": "A1",
            "role": "PRD",
            "payload": {"teacher_delivery": "ask name and give name"},
            "content_digest": "b" * 64,
        },
        {
            "asset_id": "R1",
            "asset_key": "READING:R1",
            "lesson_id": "KETR-RF-L001",
            "skill": "READING",
            "level": "A1",
            "role": "FOC",
            "payload": {"strategy": "keyword location and detail"},
            "content_digest": "c" * 64,
        },
        {
            "asset_id": "W1",
            "asset_key": "WRITING:W1",
            "lesson_id": "KETW-WF-L001",
            "skill": "WRITING",
            "level": "A1+",
            "role": "PRD",
            "payload": {"body_title": "write message"},
            "content_digest": "d" * 64,
        },
    ]
    return {
        "task_id": m2.TASK_ID,
        "schema_version": m2.SCHEMA_VERSION,
        "validation_status": m2.STATUS,
        "lesson_catalog": lessons,
        "asset_records": assets,
        "counts": {"learning_lesson_count": len(lessons)},
        "access_contract": {"a2_payload_query_allowed": False},
        "errors": [],
    }


def occurrence(
    transcript_id: str,
    index: int,
    normalized: str,
    *,
    roles: list[str],
    support_domains: list[str] | None = None,
    canonical_targets: list[dict] | None = None,
    disposition: str = "INSTRUCTIONAL_SUPPORT_ONLY",
) -> dict:
    return {
        "evidence_occurrence_id": f"KET99:{transcript_id}:{index:02d}",
        "evidence_index": index,
        "normalized_evidence_item": normalized,
        "disposition": disposition,
        "canonical_targets": canonical_targets or [],
        "support_domains": support_domains or [],
        "instructional_roles": roles,
        "target_role_assignments": [],
        "review_reason": None if disposition != "REVIEW_REQUIRED" else "NO_HIGH_CONFIDENCE_CANONICAL_RULE_DO_NOT_INVENT_MAPPING",
    }


def overlay(g: dict) -> dict:
    rows = []
    for number in range(4, 103):
        transcript_id = f"P{number:03d}"
        if transcript_id == "P004":
            content_roles = ["speaking", "teacher_delivery"]
            evidence = [occurrence(transcript_id, 1, "ask_name", roles=["FOCUS"])]
        elif transcript_id == "P005":
            content_roles = ["reading", "teacher_delivery"]
            evidence = [occurrence(transcript_id, 1, "keyword_location", roles=["SUPPORT"])]
        elif transcript_id == "P006":
            content_roles = ["listening", "teacher_delivery"]
            evidence = [
                occurrence(
                    transcript_id,
                    1,
                    "ask_name",
                    roles=["FOCUS"],
                    canonical_targets=[
                        {"target_type": "M1_NODE", "target_id": "REF:LISTENING:ASK_NAME"}
                    ],
                    disposition="CANONICAL_MATCH",
                )
            ]
        elif transcript_id == "P007":
            content_roles = ["writing", "teacher_delivery"]
            evidence = [occurrence(transcript_id, 1, "write_message", roles=["FOCUS"])]
        else:
            content_roles = ["teacher_delivery"]
            evidence = [
                occurrence(
                    transcript_id,
                    1,
                    f"generic_delivery_marker_{number}",
                    roles=[],
                    disposition="REVIEW_REQUIRED",
                )
            ]
        rows.append(
            {
                "transcript_id": transcript_id,
                "source_transcript_number": number,
                "content_unit_id": f"CU:{transcript_id}",
                "unit_id": "U01",
                "lesson_role": "unit_core",
                "content_roles": content_roles,
                "risk_flags": [],
                "source_lineage": {
                    "source_evidence_sha256": f"{number:064x}"[-64:],
                    "coverage_mode": "full_transcript_read",
                    "admission_id": f"ADM:{transcript_id}",
                },
                "planner_admission": "APPROVED_WITH_CONSTRAINTS",
                "canonical_promotion_allowed": False,
                "evidence_occurrences": evidence,
                "evidence_disposition_counts": {evidence[0]["disposition"]: 1},
            }
        )
    return {
        "task_id": cp07b.TASK_ID,
        "schema_version": cp07b.SCHEMA_VERSION,
        "scope": "A1_A1_PLUS_ONLY",
        "source_identity": {"m1_hard_graph_sha256": builder.digest(g)},
        "authority_contract": {
            "hard_graph_mutation_allowed": False,
            "a2_a2plus_status": "LOCKED",
        },
        "transcript_overlays": rows,
        "coverage_summary": {"transcript_count": 99},
        "errors": [],
        "stop_reason": "NONE",
    }


def baseline(g: dict, c: dict, o: dict) -> dict:
    lesson_rows = []
    for lesson in c["lesson_catalog"]:
        references = []
        if lesson["lesson_id"] == "KETL-LF-L001":
            references = [
                {
                    "evidence_occurrence_id": "KET99:P006:01",
                    "transcript_id": "P006",
                    "source_evidence_sha256": f"{6:064x}"[-64:],
                    "instructional_roles": ["FOCUS"],
                    "canonical_target_refs": [
                        {"target_type": "M1_NODE", "target_id": "REF:LISTENING:ASK_NAME"}
                    ],
                    "mapping_basis": ["EXACT_CP07B_M1_NODE_TARGET"],
                    "runtime_effect": "OPTIONAL_TEACHING_REFERENCE_ONLY",
                }
            ]
        lesson_rows.append(
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
            "m1_hard_graph_sha256": builder.digest(g),
            "m2_consumer_sha256": builder.digest(c),
            "cp07b_instructional_overlay_sha256": builder.digest(o),
            "r3c_semantic_bridge_sha256": "e" * 64,
        },
        "lesson_instructional_references": lesson_rows,
        "coverage_summary": {
            "learning_lesson_count": 4,
            "referenced_lesson_count": 1,
            "unreferenced_lesson_count": 3,
            "instructional_reference_count": 1,
            "transcript_count": 99,
            "referenced_transcript_count": 1,
            "unused_transcript_count": 98,
            "hard_graph_edge_delta": 0,
            "blocked_lesson_count": 0,
        },
        "errors": [],
        "stop_reason": "NONE",
    }


def inputs() -> tuple[dict, dict, dict, dict]:
    g = graph()
    c = consumer()
    o = overlay(g)
    return g, c, o, baseline(g, c, o)


def test_full_inventory_and_coverage_expansion() -> None:
    g, c, o, b = inputs()
    artifact = builder.build_artifact(g, c, o, b)
    summary = artifact["coverage_summary"]
    inventory = {row["transcript_id"]: row for row in artifact["transcript_semantic_inventory"]}
    lessons = {row["lesson_id"]: row for row in artifact["lesson_instructional_references"]}

    assert len(inventory) == 99
    assert len(lessons) == 4
    assert summary["baseline_referenced_transcript_count"] == 1
    assert summary["baseline_referenced_lesson_count"] == 1
    assert summary["referenced_transcript_delta"] >= 3
    assert summary["referenced_lesson_delta"] >= 3
    assert inventory["P004"]["disposition"] == "USED_FOR_A1_A1PLUS"
    assert inventory["P005"]["disposition"] == "USED_FOR_A1_A1PLUS"
    assert inventory["P006"]["disposition"] == "USED_FOR_A1_A1PLUS"
    assert inventory["P007"]["disposition"] == "USED_FOR_A1_A1PLUS"
    assert inventory["P008"]["disposition"] == "HUMAN_EVIDENCE_REQUIRED"
    assert lessons["KETL-LF-L001"]["reference_status"] == "REFERENCED"
    assert lessons["KETS-SF-L001"]["reference_status"] == "REFERENCED"
    assert lessons["KETR-RF-L001"]["reference_status"] == "REFERENCED"
    assert lessons["KETW-WF-L001"]["reference_status"] == "REFERENCED"
    assert all(row["delivery_blocked_by_missing_reference"] is False for row in lessons.values())


def test_generic_teacher_delivery_marker_does_not_create_mapping() -> None:
    g, c, o, b = inputs()
    artifact = builder.build_artifact(g, c, o, b)
    inventory = {row["transcript_id"]: row for row in artifact["transcript_semantic_inventory"]}
    assert inventory["P050"]["referenced_lesson_count"] == 0
    assert inventory["P050"]["disposition"] == "HUMAN_EVIDENCE_REQUIRED"


def test_validator_rebuilds_and_requires_real_delta() -> None:
    g, c, o, b = inputs()
    artifact = builder.build_artifact(g, c, o, b)
    report = validator.validate_artifact(
        artifact,
        m1_graph=g,
        m2_consumer=c,
        cp07b_overlay=o,
        r3e_baseline=b,
    )
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert report["transcript_count"] == 99
    assert report["transcript_disposition_count"] == 99
    assert report["referenced_lesson_delta"] > 0
    assert report["referenced_transcript_delta"] > 0
    assert report["deterministic_rebuild_matches"] is True


def test_baseline_reference_is_preserved() -> None:
    g, c, o, b = inputs()
    artifact = builder.build_artifact(g, c, o, b)
    listening = next(row for row in artifact["lesson_instructional_references"] if row["lesson_id"] == "KETL-LF-L001")
    occurrence_ids = {row["evidence_occurrence_id"] for row in listening["instructional_references"]}
    assert "KET99:P006:01" in occurrence_ids


def test_tampered_disposition_fails() -> None:
    g, c, o, b = inputs()
    artifact = builder.build_artifact(g, c, o, b)
    tampered = deepcopy(artifact)
    row = next(value for value in tampered["transcript_semantic_inventory"] if value["transcript_id"] == "P004")
    row["disposition"] = "A2_ONLY"
    report = validator.validate_artifact(
        tampered,
        m1_graph=g,
        m2_consumer=c,
        cp07b_overlay=o,
        r3e_baseline=b,
    )
    assert report["validation_status"] != builder.PASS_STATUS
    assert any("used_transcript_disposition_invalid:P004" == value for value in report["errors"])


def test_private_content_key_is_rejected() -> None:
    g, c, o, b = inputs()
    artifact = builder.build_artifact(g, c, o, b)
    tampered = deepcopy(artifact)
    tampered["transcript_semantic_inventory"][0]["transcript_text"] = "forbidden"
    report = validator.validate_artifact(
        tampered,
        m1_graph=g,
        m2_consumer=c,
        cp07b_overlay=o,
        r3e_baseline=b,
    )
    assert report["validation_status"] != builder.PASS_STATUS
    assert any("private_or_text_key_forbidden" in value for value in report["errors"])
