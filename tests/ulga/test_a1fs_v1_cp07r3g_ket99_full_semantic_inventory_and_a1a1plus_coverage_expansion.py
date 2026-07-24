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
            "node_id": "REF:READING:FAMILY",
            "node_type": "CAPABILITY",
            "skill": "READING",
            "level": "A1",
            "source_ref": "read_family_names",
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
            "lesson_id": "KETR-RF-L002",
            "lesson_node_id": "LESSON:READING:KETR-RF-L002",
            "skill": "READING",
            "level": "A1",
            "asset_keys": ["READING:R2"],
            "roles": ["FOC"],
            "requirement_node_ids": ["REF:READING:FAMILY"],
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
            "asset_id": "R2",
            "asset_key": "READING:R2",
            "lesson_id": "KETR-RF-L002",
            "skill": "READING",
            "level": "A1",
            "role": "FOC",
            "payload": {"target_language": "read family names"},
            "content_digest": "d" * 64,
        },
        {
            "asset_id": "W1",
            "asset_key": "WRITING:W1",
            "lesson_id": "KETW-WF-L001",
            "skill": "WRITING",
            "level": "A1+",
            "role": "PRD",
            "payload": {"body_title": "write message about cheap clothes and descriptive adjectives"},
            "content_digest": "e" * 64,
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
    canonical_targets: list[dict] | None = None,
    disposition: str = "INSTRUCTIONAL_SUPPORT_ONLY",
) -> dict:
    return {
        "evidence_occurrence_id": f"KET99:{transcript_id}:{index:02d}",
        "evidence_index": index,
        "normalized_evidence_item": normalized,
        "disposition": disposition,
        "canonical_targets": canonical_targets or [],
        "support_domains": [],
        "instructional_roles": roles,
        "target_role_assignments": [],
        "review_reason": None if disposition != "REVIEW_REQUIRED" else "NO_HIGH_CONFIDENCE_CANONICAL_RULE_DO_NOT_INVENT_MAPPING",
    }


def overlay(g: dict) -> dict:
    rows = []
    for number in range(4, 103):
        transcript_id = f"P{number:03d}"
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
        elif transcript_id == "P008":
            content_roles = ["teacher_delivery"]
            evidence = [
                occurrence(transcript_id, 1, "閱讀審題", roles=["SUPPORT"]),
                occurrence(transcript_id, 2, "畫關鍵詞", roles=["SUPPORT"]),
            ]
        elif transcript_id == "P026":
            content_roles = ["grammar", "vocabulary", "teacher_delivery"]
            evidence = [
                occurrence(transcript_id, 1, "cheap", roles=["FOCUS"]),
                occurrence(transcript_id, 2, "expensive", roles=["RECYCLE"]),
            ]
        elif 40 <= number <= 70:
            content_roles = ["speaking", "teacher_delivery"]
            evidence = [occurrence(transcript_id, 1, "ask_name", roles=["RECYCLE"])]
        elif transcript_id == "P030":
            content_roles = ["listening", "speaking", "reading", "writing", "teacher_delivery"]
            evidence = [occurrence(transcript_id, 1, "generic_question_marker", roles=[])]

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
                "evidence_disposition_counts": dict(
                    __import__("collections").Counter(row["disposition"] for row in evidence)
                ),
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
            "r3c_semantic_bridge_sha256": "f" * 64,
        },
        "lesson_instructional_references": lesson_rows,
        "coverage_summary": {
            "learning_lesson_count": len(lesson_rows),
            "referenced_lesson_count": 1,
            "unreferenced_lesson_count": len(lesson_rows) - 1,
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


def ket99_contract(o: dict) -> dict:
    sources = [
        {
            "transcript_id": f"P{number:03d}",
            "sha256": f"{number:064x}"[-64:],
        }
        for number in range(4, 103)
    ]
    results = [
        {
            "transcript_id": "P008",
            "source_sha256": f"{8:064x}"[-64:],
            "resolution_status": "RESOLVED",
            "resolution_basis": "CONTROLLED_READING_STRATEGY_LEXICON",
            "semantic_atoms": [
                "reading_strategy",
                "keyword_location",
                "detail_location",
            ],
            "evidence_anchors": [
                {"normalized_cue_sha256": "8" * 64}
            ],
            "raw_text_included": False,
        },
        {
            "transcript_id": "P026",
            "source_sha256": f"{26:064x}"[-64:],
            "resolution_status": "RESOLVED",
            "resolution_basis": (
                "CONTROLLED_DESCRIPTIVE_ADJECTIVE_AND_SHOPPING_LEXICON"
            ),
            "semantic_atoms": ["dirty", "clean", "expensive", "cheap", "light"],
            "evidence_anchors": [
                {"normalized_cue_sha256": "a" * 64}
            ],
            "raw_text_included": False,
        },
    ]
    return {
        "consumer_locator": {
            "task_id": builder.KET99_TASK_ID,
            "schema_version": "ket99.srt.consumer_input_locator.v1",
            "private_body": builder.KET99_PRIVATE_LOCATOR,
            "r3g": {"upstream_consumer": "CP07B"},
        },
        "source_manifest": {
            "task_id": builder.KET99_TASK_ID,
            "source_count": 99,
            "source_range": ["P004", "P102"],
            "raw_srt_committed": False,
            "sources": sources,
        },
        "evidence_resolution": {
            "task_id": builder.KET99_TASK_ID,
            "results": results,
        },
        "artifact_index": {},
        "validation_result": {
            "validation_status": builder.KET99_VALIDATION_STATUS,
            "error_count": 0,
        },
        "private_body_locator": builder.KET99_PRIVATE_LOCATOR,
        "private_body_sha256": "b" * 64,
        "private_body_verified": True,
    }


def inputs() -> tuple[dict, dict, dict, dict, dict]:
    g = graph()
    c = consumer()
    o = overlay(g)
    return g, c, o, baseline(g, c, o), ket99_contract(o)


def test_precision_guarded_inventory_and_coverage_expansion() -> None:
    g, c, o, b, k = inputs()
    artifact = builder.build_artifact(g, c, o, b, k)
    summary = artifact["coverage_summary"]
    precision = artifact["precision_summary"]
    inventory = {row["transcript_id"]: row for row in artifact["transcript_semantic_inventory"]}
    lessons = {row["lesson_id"]: row for row in artifact["lesson_instructional_references"]}

    assert len(inventory) == 99
    assert len(lessons) == 5
    assert summary["referenced_transcript_count"] > 1
    assert summary["referenced_lesson_count"] > 1
    assert precision["maximum_reference_count_per_lesson"] <= builder.MAX_REFERENCES_PER_LESSON
    assert precision["pruned_reference_count"] > 0
    assert precision["token_only_mapping_allowed"] is False
    assert inventory["P008"]["disposition"] == "USED_FOR_A1_A1PLUS"
    assert inventory["P026"]["disposition"] == "USED_FOR_A1_A1PLUS"
    assert inventory["P030"]["disposition"] == "HUMAN_EVIDENCE_REQUIRED"
    assert artifact["human_evidence_resolution_summary"]["unresolved_transcript_ids"] == []
    assert artifact["human_evidence_resolution_summary"]["resolution_usage"]["P008"]["used"] is True
    assert artifact["human_evidence_resolution_summary"]["resolution_usage"]["P026"]["used"] is True
    assert artifact["private_source_contract"]["private_body_included"] is False
    assert artifact["next_short_step"] == builder.NEXT_SHORT_STEP

    reading_strategy_refs = lessons["KETR-RF-L001"]["instructional_references"]
    reading_family_refs = lessons["KETR-RF-L002"]["instructional_references"]
    assert any(row["transcript_id"] == "P008" for row in reading_strategy_refs)
    assert any(
        row["transcript_id"] == "P008"
        and "CONTROLLED_HUMAN_EVIDENCE_RESOLUTION" in row["mapping_basis"]
        for row in reading_strategy_refs
    )
    assert all(row["transcript_id"] != "P008" for row in reading_family_refs)
    writing_refs = lessons["KETW-WF-L001"]["instructional_references"]
    assert any(row["transcript_id"] == "P026" for row in writing_refs)
    assert any(
        row["transcript_id"] == "P026"
        and "CONTROLLED_HUMAN_EVIDENCE_RESOLUTION" in row["mapping_basis"]
        for row in writing_refs
    )
    assert all(row["transcript_id"] != "P030" for row in lessons.values() for row in row["instructional_references"])


def test_validator_rebuilds_and_enforces_precision_contract() -> None:
    g, c, o, b, k = inputs()
    artifact = builder.build_artifact(g, c, o, b, k)
    report = validator.validate_artifact(
        artifact,
        m1_graph=g,
        m2_consumer=c,
        cp07b_overlay=o,
        r3e_baseline=b,
        ket99_contract=k,
    )
    assert report["validation_status"] == builder.PASS_STATUS, report["errors"]
    assert report["deterministic_rebuild_matches"] is True
    assert report["precision_gate_passed"] is True
    assert report["human_evidence_resolution_complete"] is True
    assert report["maximum_reference_count_per_lesson"] <= builder.MAX_REFERENCES_PER_LESSON


def test_baseline_reference_is_preserved_and_pinned() -> None:
    g, c, o, b, k = inputs()
    artifact = builder.build_artifact(g, c, o, b, k)
    listening = next(
        row for row in artifact["lesson_instructional_references"] if row["lesson_id"] == "KETL-LF-L001"
    )
    baseline_ref = next(
        row for row in listening["instructional_references"] if row["evidence_occurrence_id"] == "KET99:P006:01"
    )
    assert baseline_ref["pinned_baseline"] is True
    assert baseline_ref["mapping_basis"] == ["BASELINE_R3E_REFERENCE"]
    assert baseline_ref["admission_rank"] == 1


def test_density_and_human_resolution_tamper_fail_closed() -> None:
    g, c, o, b, k = inputs()
    artifact = builder.build_artifact(g, c, o, b, k)

    density_tampered = deepcopy(artifact)
    lesson = next(row for row in density_tampered["lesson_instructional_references"] if row["lesson_id"] == "KETL-LF-L001")
    lesson["instructional_references"].append(deepcopy(lesson["instructional_references"][0]))
    report = validator.validate_artifact(
        density_tampered,
        m1_graph=g,
        m2_consumer=c,
        cp07b_overlay=o,
        r3e_baseline=b,
        ket99_contract=k,
    )
    assert report["validation_status"] != builder.PASS_STATUS

    resolution_tampered = deepcopy(artifact)
    resolution_tampered["human_evidence_resolution_summary"]["resolved_transcript_ids"] = ["P008"]
    resolution_tampered["human_evidence_resolution_summary"]["unresolved_transcript_ids"] = ["P026"]
    report = validator.validate_artifact(
        resolution_tampered,
        m1_graph=g,
        m2_consumer=c,
        cp07b_overlay=o,
        r3e_baseline=b,
        ket99_contract=k,
    )
    assert report["validation_status"] != builder.PASS_STATUS


def test_ket99_resolution_contract_tamper_fails_closed() -> None:
    g, c, o, b, k = inputs()
    tampered = deepcopy(k)
    tampered["evidence_resolution"]["results"][0]["source_sha256"] = "0" * 64
    try:
        builder.build_artifact(g, c, o, b, tampered)
    except builder.R3GError as exc:
        assert "ket99_resolution_source_digest_mismatch:P008" in str(exc)
    else:
        raise AssertionError("tampered KET99 resolution contract was accepted")


def test_unverified_private_body_fails_closed() -> None:
    graph, consumer, overlay, baseline, ket99_contract = inputs()
    ket99_contract["private_body_verified"] = False
    try:
        builder.build_artifact(
            graph, consumer, overlay, baseline, ket99_contract
        )
    except builder.R3GError as exc:
        assert "ket99_private_body_not_verified" in str(exc)
    else:
        raise AssertionError("unverified KET99 private body was accepted")
