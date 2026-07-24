from __future__ import annotations

import copy
import json
from pathlib import Path

from ulga.builders import build_ket99_pku_teacher_delivery_remediation_asset_intake as builder
from ulga.builders import build_ket99_pku_controlled_pilot_overlay_admission as m4
from ulga.validators import validate_ket99_pku_teacher_delivery_remediation_asset_intake as validator


def reference(pku_id: str, transcript_id: str) -> dict:
    return {
        "pku_id": pku_id,
        "source_transcript_id": transcript_id,
        "source_unit_id": "U1",
        "textbook_page": 10,
        "lesson_role": "REGULAR",
        "mapping_class": "CONTROLLED_TRANSCRIPT_REFERENCE",
        "authority_ids": [],
        "teaching_need_id": "READING.LOCATE_WITH_EVIDENCE",
        "evidence_anchor_ids": [f"{transcript_id}:E001"],
        "resolution_anchor_sha256s": ["a" * 64],
        "grammar_node_ids": [],
        "vocabulary_chunk_pattern_ids": ["DOMAIN:READING_DETAIL_LOCATION"],
        "r3g_artifact_sha256": "b" * 64,
        "cp07b_artifact_sha256": "c" * 64,
        "m2_artifact_sha256": "d" * 64,
        "m3_artifact_sha256": "e" * 64,
        "authority_status": "NON_AUTHORITATIVE_PILOT_OVERLAY",
        "admission_decision": "PILOT_ADMITTED",
        "runtime_effect": "OPTIONAL_PILOT_INSTRUCTIONAL_REFERENCE_ONLY",
        "hard_lesson_selection_allowed": False,
        "production_mapping_allowed": False,
        "repository_export_policy": "METADATA_ONLY_NO_PRIVATE_TRANSCRIPT_BODY",
    }


def overlay() -> dict:
    value = {
        "task_id": m4.TASK_ID,
        "schema_version": m4.SCHEMA_VERSION,
        "validation_status": m4.PASS_STATUS,
        "admission_policy": {
            "hard_lesson_selection_allowed": False,
            "production_mapping_allowed": False,
            "a2_mapping_allowed": False,
        },
        "lesson_pilot_overlays": [
            {
                "lesson_id": "L1",
                "lesson_node_id": "LESSON:READING:L1",
                "skill": "READING",
                "level": "A1",
                "pilot_reference_status": "PILOT_REFERENCED",
                "optional_pilot_references": [reference("P1", "P005"), reference("P2", "P008")],
                "delivery_blocked_by_missing_reference": False,
                "hard_lesson_selection_changed": False,
            },
            {
                "lesson_id": "L2",
                "lesson_node_id": "LESSON:WRITING:L2",
                "skill": "WRITING",
                "level": "A1+",
                "pilot_reference_status": "NO_PILOT_REFERENCE",
                "optional_pilot_references": [],
                "delivery_blocked_by_missing_reference": False,
                "hard_lesson_selection_changed": False,
            },
        ],
        "coverage_summary": {
            "optional_reference_count": 2,
            "pilot_referenced_lesson_count": 1,
            "admitted_pku_count": 2,
        },
        "claim_boundaries": {
            "hard_graph_modified": False,
            "canonical_denominator_modified": False,
            "mastery_denominator_modified": False,
            "a2_unlocked": False,
        },
        "errors": [],
        "stop_reason": "NONE",
    }
    value["artifact_sha256"] = builder.digest(value)
    return value


def coverage(overlay_value: dict) -> dict:
    value = {
        "task_id": m4.TASK_ID,
        "schema_version": builder.COVERAGE_SCHEMA,
        "validation_status": m4.PASS_STATUS,
        "source_identity": {"m4_overlay_sha256": builder.digest(overlay_value)},
        "coverage_counts": {
            "overlay_unique_new_coverage_count": 0,
            "overlay_already_covered_count": 1,
            "overlay_duplicate_only_count": 1,
            "coverage_double_count": 0,
            "canonical_graph_mutation_count": 0,
            "canonical_denominator_mutation_count": 0,
        },
        "claim_boundaries": {"learner_effectiveness_claimed": False},
        "errors": [],
        "stop_reason": "NONE",
    }
    value["artifact_sha256"] = builder.digest(value)
    return value


def test_builds_mainline_intake_without_activation() -> None:
    source = overlay()
    artifact = builder.build_artifact(source, coverage(source))
    assert artifact["counts"]["asset_candidate_count"] == 2
    assert artifact["counts"]["referenced_lesson_count"] == 1
    assert artifact["counts"]["learning_value_evaluated_count"] == 0
    assert artifact["counts"]["teacher_delivery_activated_count"] == 0
    assert artifact["counts"]["remediation_activated_count"] == 0
    candidate = artifact["asset_candidates"][0]
    assert candidate["candidate_lanes"]["teacher_delivery"]["intake_status"] == "EVALUATION_REQUIRED"
    assert candidate["candidate_lanes"]["remediation"]["intake_status"] == "EVALUATION_REQUIRED"
    assert candidate["composition_item"] is False
    assert candidate["learner_facing_allowed"] is False


def test_is_deterministic() -> None:
    source = overlay()
    coverage_value = coverage(source)
    assert builder.build_artifact(source, coverage_value) == builder.build_artifact(source, coverage_value)


def test_nonzero_unique_coverage_fails_closed() -> None:
    source = overlay()
    bad = coverage(source)
    bad["coverage_counts"]["overlay_unique_new_coverage_count"] = 1
    bad["artifact_sha256"] = builder.digest({key: value for key, value in bad.items() if key != "artifact_sha256"})
    try:
        builder.build_artifact(source, bad)
    except ValueError as exc:
        assert str(exc) == "m4_coverage_boundary_invalid"
    else:
        raise AssertionError("nonzero unique coverage was accepted")


def test_private_content_key_fails_closed() -> None:
    source = overlay()
    source["lesson_pilot_overlays"][0]["optional_pilot_references"][0]["transcript_text"] = "private"
    source["artifact_sha256"] = builder.digest({key: value for key, value in source.items() if key != "artifact_sha256"})
    try:
        builder.build_artifact(source, coverage(source))
    except ValueError as exc:
        assert "private_content_key_forbidden" in str(exc)
    else:
        raise AssertionError("private transcript text was accepted")


def test_validator_rejects_tamper(tmp_path: Path) -> None:
    source = overlay()
    coverage_value = coverage(source)
    artifact = builder.build_artifact(source, coverage_value)
    tampered = copy.deepcopy(artifact)
    tampered["counts"]["teacher_delivery_activated_count"] = 1
    artifact_path = tmp_path / "artifact.json"
    overlay_path = tmp_path / "overlay.json"
    coverage_path = tmp_path / "coverage.json"
    for path, value in (
        (artifact_path, tampered),
        (overlay_path, source),
        (coverage_path, coverage_value),
    ):
        path.write_text(json.dumps(value), encoding="utf-8")
    report = validator.validate_paths(
        artifact_path=artifact_path,
        m4_path=overlay_path,
        coverage_path=coverage_path,
    )
    assert report["validation_status"] == validator.FAIL_STATUS
    assert "artifact_deterministic_rebuild_mismatch" in report["errors"]
