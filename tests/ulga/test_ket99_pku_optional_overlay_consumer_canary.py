from __future__ import annotations

import copy
import json
from pathlib import Path

from ulga.builders import build_ket99_pku_optional_overlay_consumer_canary as builder
from ulga.builders import build_ket99_pku_teacher_delivery_remediation_asset_intake as intake_builder
from ulga.validators import validate_ket99_pku_optional_overlay_consumer_canary as validator


def composition() -> dict:
    return {
        "cp07r3f_task_id": builder.R3F_TASK,
        "cp07r3f_schema_version": builder.R3F_SCHEMA,
        "cp07r3f_validation_status": builder.R3F_STATUS,
        "source_identity": {"m2_consumer_sha256": "m2"},
        "unified_lesson_composition": {
            "selected_lesson_id": "L1",
            "selected_skill": "READING",
            "selected_level": "A1",
            "composition_items": [
                {
                    "source_kind": "KET_ASSET_BODY",
                    "composition_item_id": "K1",
                    "delivery_allowed_now": True,
                }
            ],
            "coverage_summary": {
                "composition_item_count": 1,
                "delivery_allowed_now_count": 1,
                "ket_asset_count": 1,
            },
            "consumer_gate": {
                "m4_selected_lesson_unchanged": True,
                "m1_hard_prerequisite_graph_unchanged": True,
                "ket_asset_body_required": True,
                "a2_payload_included": False,
            },
        },
        "claim_boundaries": {"hard_lesson_selection_changed": False},
        "errors": [],
        "stop_reason": "NONE",
    }


def reference() -> dict:
    return {
        "pku_id": "P1",
        "source_transcript_id": "P005",
        "source_unit_id": "U1",
        "textbook_page": 9,
        "lesson_role": "REGULAR",
        "mapping_class": "CONTROLLED_TRANSCRIPT_REFERENCE",
        "authority_ids": [],
        "teaching_need_id": "READING.LOCATE_WITH_EVIDENCE",
        "evidence_anchor_ids": ["P005:E001"],
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


def overlay(with_references: bool = True) -> dict:
    references = [reference()] if with_references else []
    value = {
        "task_id": builder.M4_TASK,
        "schema_version": builder.M4_SCHEMA,
        "validation_status": builder.M4_STATUS,
        "source_identity": {"m2_consumer_sha256": "m2"},
        "admission_policy": {
            "hard_lesson_selection_allowed": False,
            "production_mapping_allowed": False,
            "a2_mapping_allowed": False,
            "missing_reference_blocks_delivery": False,
        },
        "lesson_pilot_overlays": [
            {
                "lesson_id": "L1",
                "lesson_node_id": "LESSON:READING:L1",
                "skill": "READING",
                "level": "A1",
                "pilot_reference_status": (
                    "PILOT_REFERENCED" if references else "NO_PILOT_REFERENCE"
                ),
                "optional_pilot_references": references,
                "delivery_blocked_by_missing_reference": False,
                "hard_lesson_selection_changed": False,
            }
        ],
        "coverage_summary": {
            "optional_reference_count": len(references),
            "pilot_referenced_lesson_count": 1 if references else 0,
            "admitted_pku_count": 1 if references else 0,
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
    reference_count = len(
        overlay_value["lesson_pilot_overlays"][0]["optional_pilot_references"]
    )
    value = {
        "task_id": builder.M4_TASK,
        "schema_version": intake_builder.COVERAGE_SCHEMA,
        "validation_status": builder.M4_STATUS,
        "source_identity": {"m4_overlay_sha256": intake_builder.digest(overlay_value)},
        "coverage_counts": {
            "overlay_unique_new_coverage_count": 0,
            "overlay_already_covered_count": 1 if reference_count else 0,
            "overlay_duplicate_only_count": max(reference_count - 1, 0),
            "coverage_double_count": 0,
            "canonical_graph_mutation_count": 0,
            "canonical_denominator_mutation_count": 0,
        },
        "claim_boundaries": {"learner_effectiveness_claimed": False},
        "errors": [],
        "stop_reason": "NONE",
    }
    value["artifact_sha256"] = intake_builder.digest(value)
    return value


def intake(overlay_value: dict) -> dict | None:
    if not overlay_value["lesson_pilot_overlays"][0]["optional_pilot_references"]:
        return None
    return intake_builder.build_artifact(overlay_value, coverage(overlay_value))


def test_attaches_metadata_without_mutating_composition_items() -> None:
    source = composition()
    overlay_value = overlay()
    result = builder.build_artifact(source, overlay_value, intake(overlay_value))
    assert (
        result["unified_lesson_composition"]["composition_items"]
        == source["unified_lesson_composition"]["composition_items"]
    )
    attached = result["unified_lesson_composition"]["ket99_pku_optional_overlay"]
    assert attached["runtime_canary_status"] == "OPTIONAL_METADATA_AVAILABLE"
    assert attached["composition_item_count_delta"] == 0
    intake_attached = attached["teacher_delivery_remediation_asset_intake"]
    assert intake_attached["connection_status"] == "MAINLINE_INTAKE_CONNECTED"
    assert intake_attached["asset_candidate_count"] == 1
    assert intake_attached["learning_value_evaluated_count"] == 0
    assert intake_attached["activated_candidate_count"] == 0
    assert (
        result["unified_lesson_composition"]["coverage_summary"]
        ["delivery_allowed_count_after_pku_overlay"]
        == 1
    )


def test_missing_optional_metadata_does_not_block() -> None:
    result = builder.build_artifact(composition(), overlay(False), None)
    attached = result["unified_lesson_composition"]["ket99_pku_optional_overlay"]
    assert attached["runtime_canary_status"] == "NO_OPTIONAL_METADATA"
    assert attached["missing_reference_blocks_delivery"] is False
    assert attached["teacher_delivery_remediation_asset_intake"]["connection_status"] == "NO_INTAKE_CANDIDATES"
    assert (
        result["unified_lesson_composition"]["consumer_gate"]
        ["missing_pku_reference_blocks_delivery"]
        is False
    )


def test_existing_two_input_call_remains_compatible() -> None:
    result = builder.build_artifact(composition(), overlay())
    attached = result["unified_lesson_composition"]["ket99_pku_optional_overlay"]
    assert attached["teacher_delivery_remediation_asset_intake"]["asset_candidate_count"] == 0
    assert result["claim_boundaries"]["ket99_teacher_delivery_assets_activated"] is False


def test_m2_binding_drift_fails_closed() -> None:
    bad = overlay()
    bad["source_identity"]["m2_consumer_sha256"] = "other"
    bad["artifact_sha256"] = builder.digest(
        {key: value for key, value in bad.items() if key != "artifact_sha256"}
    )
    try:
        builder.build_artifact(composition(), bad)
    except ValueError as exc:
        assert str(exc) == "r3f_m4_m2_binding_invalid"
    else:
        raise AssertionError("M2 binding drift was accepted")


def test_selected_lesson_partition_drift_fails_closed() -> None:
    bad = overlay()
    bad["lesson_pilot_overlays"][0]["skill"] = "WRITING"
    bad["artifact_sha256"] = builder.digest(
        {key: value for key, value in bad.items() if key != "artifact_sha256"}
    )
    try:
        builder.build_artifact(composition(), bad)
    except ValueError as exc:
        assert str(exc) == "m4_selected_lesson_partition_drift"
    else:
        raise AssertionError("selected lesson partition drift was accepted")


def test_production_reference_fails_closed() -> None:
    bad = overlay()
    bad["lesson_pilot_overlays"][0]["optional_pilot_references"][0][
        "production_mapping_allowed"
    ] = True
    bad["artifact_sha256"] = builder.digest(
        {key: value for key, value in bad.items() if key != "artifact_sha256"}
    )
    try:
        builder.build_artifact(composition(), bad)
    except ValueError as exc:
        assert str(exc) == "m4_optional_reference_boundary_invalid"
    else:
        raise AssertionError("production reference was accepted")


def test_asset_intake_activation_tamper_fails_closed() -> None:
    overlay_value = overlay()
    bad = intake(overlay_value)
    assert bad is not None
    bad["intake_policy"]["teacher_delivery_asset_activation_allowed"] = True
    bad["artifact_sha256"] = intake_builder.digest(
        {key: value for key, value in bad.items() if key != "artifact_sha256"}
    )
    try:
        builder.build_artifact(composition(), overlay_value, bad)
    except ValueError as exc:
        assert str(exc) == "m4a_asset_intake_policy_invalid"
    else:
        raise AssertionError("activated unevaluated asset intake was accepted")


def test_validator_rejects_tamper(tmp_path: Path) -> None:
    composition_value = composition()
    overlay_value = overlay()
    intake_value = intake(overlay_value)
    assert intake_value is not None
    artifact = builder.build_artifact(composition_value, overlay_value, intake_value)
    tampered = copy.deepcopy(artifact)
    tampered["unified_lesson_composition"]["composition_items"].append(
        {"source_kind": "KET99_PKU"}
    )
    artifact_path = tmp_path / "artifact.json"
    composition_path = tmp_path / "composition.json"
    overlay_path = tmp_path / "overlay.json"
    intake_path = tmp_path / "intake.json"
    for path, value in (
        (artifact_path, tampered),
        (composition_path, composition_value),
        (overlay_path, overlay_value),
        (intake_path, intake_value),
    ):
        path.write_text(json.dumps(value), encoding="utf-8")
    report = validator.validate_paths(
        artifact_path=artifact_path,
        r3f_path=composition_path,
        m4_path=overlay_path,
        asset_intake_path=intake_path,
    )
    assert report["validation_status"] == validator.FAIL_STATUS
    assert "artifact_deterministic_rebuild_mismatch" in report["errors"]
