from __future__ import annotations

import copy
import json
from pathlib import Path

from ulga.builders import build_ket99_pku_controlled_pilot_overlay_admission as builder
from ulga.validators import validate_ket99_pku_controlled_pilot_overlay_admission as validator


def consumer(count: int = 12) -> dict:
    lessons = []
    for index in range(count):
        skill = "READING" if index < 10 else "WRITING"
        level = "A1+" if index % 2 else "A1"
        lessons.append({
            "lesson_id": f"L{index:02d}",
            "lesson_node_id": f"LESSON:{skill}:L{index:02d}",
            "skill": skill,
            "level": level,
            "requirement_node_ids": [],
        })
    lessons.append({
        "lesson_id": "A2L",
        "lesson_node_id": "LESSON:READING:A2L",
        "skill": "READING",
        "level": "A2",
        "requirement_node_ids": [],
    })
    return {
        "task_id": builder.M2_TASK,
        "schema_version": builder.M2_SCHEMA,
        "validation_status": builder.M2_STATUS,
        "lesson_catalog": lessons,
        "access_contract": {"a2_payload_query_allowed": False},
    }


def m3(consumer_value: dict) -> dict:
    mappings = []
    lesson_ids = [f"L{index:02d}" for index in range(8)]
    mappings.append({
        "pku_id": "P1",
        "source_transcript_id": "T1",
        "mapping_class": "EXACT_AUTHORITY_REQUIREMENT",
        "authority_ids": ["G"],
        "teaching_need_id": None,
        "level_scope": ["A1", "A1+"],
        "skill_scope": ["READING"],
        "candidate_lesson_ids": lesson_ids,
        "candidate_count": len(lesson_ids),
        "candidate_evidence": {lesson_id: ["REF:READING:G"] for lesson_id in lesson_ids},
        "candidate_status": "EXACT_AUTHORITY_CANDIDATES_READY",
        "production_mapping_allowed": False,
    })
    for index in range(10):
        mappings.append({
            "pku_id": f"C{index}",
            "source_transcript_id": f"T{index + 2}",
            "mapping_class": "CONTROLLED_TRANSCRIPT_REFERENCE",
            "authority_ids": [],
            "teaching_need_id": f"TN{index}",
            "level_scope": ["A1"],
            "skill_scope": ["READING"],
            "candidate_lesson_ids": ["L00"],
            "candidate_count": 1,
            "candidate_evidence": {"L00": ["CONTROLLED_HUMAN_EVIDENCE_RESOLUTION"]},
            "candidate_status": "CONTROLLED_REFERENCE_CANDIDATES_READY",
            "production_mapping_allowed": False,
        })
    mappings.append({
        "pku_id": "U1",
        "source_transcript_id": "TU",
        "mapping_class": "CONTROLLED_TRANSCRIPT_REFERENCE",
        "authority_ids": [],
        "teaching_need_id": "TNU",
        "level_scope": ["A1"],
        "skill_scope": ["READING"],
        "candidate_lesson_ids": [],
        "candidate_count": 0,
        "candidate_evidence": {},
        "candidate_status": "NO_CONTROLLED_CANDIDATE_REQUIRES_EVIDENCE",
        "production_mapping_allowed": False,
    })
    mappings.append({
        "pku_id": "X1",
        "source_transcript_id": "TX",
        "mapping_class": "REJECTED_EXAM_PROCEDURE_ONLY",
        "candidate_lesson_ids": [],
        "candidate_status": "NOT_ELIGIBLE",
        "production_mapping_allowed": False,
    })
    artifact = {
        "task_id": builder.M3_TASK,
        "schema_version": builder.M3_SCHEMA,
        "validation_status": builder.M3_STATUS,
        "source_identity": {"m2_consumer_sha256": builder.digest(consumer_value)},
        "mapping_policy": {
            "skill_level_only_mapping_allowed": False,
            "token_only_mapping_allowed": False,
            "hard_lesson_selection_allowed": False,
            "production_lesson_mapping_allowed": False,
            "a2_mapping_allowed": False,
        },
        "candidate_mappings": mappings,
        "counts": {
            "source_pku_count": 13,
            "admitted_pku_count": 12,
            "candidate_mapped_pku_count": 11,
            "unresolved_pku_count": 1,
            "rejected_exam_procedure_count": 1,
            "candidate_lesson_reference_count": 18,
            "production_lesson_mapping_count": 0,
        },
        "errors": [],
        "stop_reason": "NONE",
    }
    artifact["artifact_sha256"] = builder.digest(artifact)
    return artifact


def lineage(source: dict, consumer_value: dict) -> tuple[dict, dict]:
    transcript_ids = sorted(
        {row["source_transcript_id"] for row in source["candidate_mappings"]}
    )
    cp07b = {
        "task_id": builder.CP07B_TASK,
        "schema_version": builder.CP07B_SCHEMA,
        "transcript_overlays": [
            {
                "transcript_id": transcript_id,
                "unit_id": "U1",
                "textbook_page": 1,
                "lesson_role": "REGULAR",
            }
            for transcript_id in transcript_ids
        ],
        "errors": [],
        "stop_reason": "NONE",
    }
    lesson_references: dict[str, list[dict]] = {}
    for mapping in source["candidate_mappings"]:
        for rank, lesson_id in enumerate(mapping.get("candidate_lesson_ids", []), 1):
            lesson_references.setdefault(lesson_id, []).append({
                "transcript_id": mapping["source_transcript_id"],
                "evidence_occurrence_id": (
                    f"{mapping['source_transcript_id']}:E{rank:03d}"
                ),
                "canonical_target_refs": [
                    {"target_type": "GRAMMAR", "target_id": "G"}
                ],
                "semantic_domains": ["READING_DETAIL_LOCATION"],
                "ket99_resolution_anchor_sha256s": ["a" * 64],
                "admission_rank": rank,
            })
    r3g = {
        "task_id": builder.R3G_TASK,
        "schema_version": builder.R3G_SCHEMA,
        "validation_status": builder.R3G_STATUS,
        "source_identity": {
            "m2_consumer_sha256": builder.digest(consumer_value),
            "cp07b_instructional_overlay_sha256": builder.digest(cp07b),
        },
        "precision_summary": {
            "token_only_mapping_allowed": False,
            "precision_gate_passed": True,
        },
        "human_evidence_resolution_summary": {
            "unresolved_transcript_ids": [],
        },
        "transcript_semantic_inventory": [
            {
                "transcript_id": transcript_id,
                "unit_id": "U1",
                "lesson_role": "REGULAR",
            }
            for transcript_id in transcript_ids
        ],
        "lesson_instructional_references": [
            {
                "lesson_id": lesson["lesson_id"],
                "instructional_references": lesson_references.get(
                    lesson["lesson_id"], []
                ),
            }
            for lesson in consumer_value["lesson_catalog"]
            if lesson["level"] in {"A1", "A1+"}
        ],
        "errors": [],
        "stop_reason": "NONE",
    }
    source["source_identity"]["r3g_sha256"] = builder.digest(r3g)
    source["artifact_sha256"] = builder.digest(
        {key: value for key, value in source.items() if key != "artifact_sha256"}
    )
    return r3g, cp07b


def inputs() -> tuple[dict, dict, dict, dict]:
    consumer_value = consumer()
    source = m3(consumer_value)
    r3g, cp07b = lineage(source, consumer_value)
    return consumer_value, source, r3g, cp07b


def test_overlay_admission_caps_and_priority() -> None:
    consumer_value, source, r3g, cp07b = inputs()
    artifact = builder.build_artifact(source, consumer_value, r3g, cp07b)
    overlays = {row["lesson_id"]: row for row in artifact["lesson_pilot_overlays"]}
    references = overlays["L00"]["optional_pilot_references"]
    assert len(references) == builder.MAX_REFERENCES_PER_LESSON
    assert references[0]["pku_id"] == "P1"
    assert sum(row["mapping_class"] == "CONTROLLED_TRANSCRIPT_REFERENCE" for row in references) == 7
    assert artifact["coverage_summary"]["pruned_by_pku_cap_reference_count"] == 2
    assert artifact["coverage_summary"]["pruned_by_lesson_cap_reference_count"] == 3
    assert artifact["coverage_summary"]["production_lesson_mapping_count"] == 0
    assert artifact["claim_boundaries"]["m4_selection_changed"] is False
    assert references[0]["authority_status"] == "NON_AUTHORITATIVE_PILOT_OVERLAY"
    assert references[0]["admission_decision"] == "PILOT_ADMITTED"
    assert references[0]["evidence_anchor_ids"]
    assert references[0]["repository_export_policy"] == "METADATA_ONLY_NO_PRIVATE_TRANSCRIPT_BODY"


def test_unresolved_and_rejected_preserved() -> None:
    consumer_value, source, r3g, cp07b = inputs()
    artifact = builder.build_artifact(source, consumer_value, r3g, cp07b)
    rows = {row["pku_id"]: row for row in artifact["pku_admissions"]}
    assert rows["U1"]["admission_status"] == "PILOT_PENDING"
    assert rows["X1"]["admission_status"] == "PILOT_REJECTED"


def test_a2_candidate_fails_closed() -> None:
    consumer_value, source, r3g, cp07b = inputs()
    source["candidate_mappings"][0]["candidate_lesson_ids"].append("A2L")
    source["candidate_mappings"][0]["candidate_count"] += 1
    source["artifact_sha256"] = builder.digest({key: value for key, value in source.items() if key != "artifact_sha256"})
    try:
        builder.build_artifact(source, consumer_value, r3g, cp07b)
    except ValueError as exc:
        assert "candidate_lesson_missing_or_a2" in str(exc)
    else:
        raise AssertionError("A2 candidate was admitted")


def test_partition_drift_fails_closed() -> None:
    consumer_value, source, r3g, cp07b = inputs()
    source["candidate_mappings"][0]["skill_scope"] = ["WRITING"]
    source["artifact_sha256"] = builder.digest({key: value for key, value in source.items() if key != "artifact_sha256"})
    try:
        builder.build_artifact(source, consumer_value, r3g, cp07b)
    except ValueError as exc:
        assert "candidate_partition_drift" in str(exc)
    else:
        raise AssertionError("partition drift was admitted")


def test_build_is_deterministic() -> None:
    consumer_value, source, r3g, cp07b = inputs()
    first = builder.build_artifact(source, consumer_value, r3g, cp07b)
    second = builder.build_artifact(source, consumer_value, r3g, cp07b)
    assert first == second
    assert (
        builder.build_coverage_readback(first, source, consumer_value)
        == builder.build_coverage_readback(second, source, consumer_value)
    )


def test_coverage_readback_preserves_denominator_and_suppresses_duplicates() -> None:
    consumer_value, source, r3g, cp07b = inputs()
    overlay = builder.build_artifact(source, consumer_value, r3g, cp07b)
    coverage = builder.build_coverage_readback(overlay, source, consumer_value)
    counts = coverage["coverage_counts"]
    assert counts["baseline_covered_count"] == 12
    assert counts["overlay_unique_new_coverage_count"] == 0
    assert counts["overlay_already_covered_count"] > 0
    assert counts["overlay_duplicate_only_count"] > 0
    assert counts["coverage_double_count"] == 0
    assert coverage["coverage_by_level"]["A1"]["coverage_delta_percentage_points"] == 0.0
    assert coverage["coverage_by_level"]["A1+"]["coverage_delta_percentage_points"] == 0.0
    assert coverage["no_double_count_proof"]["proof_status"] == "PASS"


def test_r3g_cp07b_lineage_tamper_fails_closed() -> None:
    consumer_value, source, r3g, cp07b = inputs()
    cp07b["transcript_overlays"][0]["unit_id"] = "DRIFT"
    try:
        builder.build_artifact(source, consumer_value, r3g, cp07b)
    except ValueError as exc:
        assert (
            "r3g_cp07b_binding_invalid" in str(exc)
            or "candidate_transcript_lineage_drift" in str(exc)
        )
    else:
        raise AssertionError("tampered CP07B lineage was admitted")


def test_validator_rejects_tamper(tmp_path: Path) -> None:
    consumer_value, source, r3g, cp07b = inputs()
    artifact = builder.build_artifact(source, consumer_value, r3g, cp07b)
    coverage = builder.build_coverage_readback(artifact, source, consumer_value)
    tampered = copy.deepcopy(artifact)
    tampered["coverage_summary"]["production_lesson_mapping_count"] = 1
    artifact_path = tmp_path / "artifact.json"
    m3_path = tmp_path / "m3.json"
    consumer_path = tmp_path / "consumer.json"
    coverage_path = tmp_path / "coverage.json"
    r3g_path = tmp_path / "r3g.json"
    cp07b_path = tmp_path / "cp07b.json"
    for path, value in (
        (artifact_path, tampered),
        (coverage_path, coverage),
        (m3_path, source),
        (consumer_path, consumer_value),
        (r3g_path, r3g),
        (cp07b_path, cp07b),
    ):
        path.write_text(json.dumps(value))
    report = validator.validate_paths(
        artifact_path=artifact_path,
        coverage_path=coverage_path,
        m3_path=m3_path,
        consumer_path=consumer_path,
        r3g_path=r3g_path,
        cp07b_path=cp07b_path,
    )
    assert report["validation_status"] == validator.FAIL_STATUS
    assert "artifact_deterministic_rebuild_mismatch" in report["errors"]
