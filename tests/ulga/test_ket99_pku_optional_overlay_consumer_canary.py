from __future__ import annotations

import copy
import json
from pathlib import Path

from ulga.builders import build_ket99_pku_optional_overlay_consumer_canary as builder
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


def overlay(with_references: bool = True) -> dict:
    references = []
    if with_references:
        references = [
            {
                "pku_id": "P1",
                "runtime_effect": "OPTIONAL_PILOT_INSTRUCTIONAL_REFERENCE_ONLY",
                "hard_lesson_selection_allowed": False,
                "production_mapping_allowed": False,
            }
        ]
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
        "errors": [],
        "stop_reason": "NONE",
    }
    value["artifact_sha256"] = builder.digest(value)
    return value


def test_attaches_metadata_without_mutating_composition_items() -> None:
    source = composition()
    result = builder.build_artifact(source, overlay())
    assert (
        result["unified_lesson_composition"]["composition_items"]
        == source["unified_lesson_composition"]["composition_items"]
    )
    attached = result["unified_lesson_composition"]["ket99_pku_optional_overlay"]
    assert attached["runtime_canary_status"] == "OPTIONAL_METADATA_AVAILABLE"
    assert attached["composition_item_count_delta"] == 0
    assert (
        result["unified_lesson_composition"]["coverage_summary"]
        ["delivery_allowed_count_after_pku_overlay"]
        == 1
    )


def test_missing_optional_metadata_does_not_block() -> None:
    result = builder.build_artifact(composition(), overlay(False))
    attached = result["unified_lesson_composition"]["ket99_pku_optional_overlay"]
    assert attached["runtime_canary_status"] == "NO_OPTIONAL_METADATA"
    assert attached["missing_reference_blocks_delivery"] is False
    assert (
        result["unified_lesson_composition"]["consumer_gate"]
        ["missing_pku_reference_blocks_delivery"]
        is False
    )


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


def test_validator_rejects_tamper(tmp_path: Path) -> None:
    composition_value = composition()
    overlay_value = overlay()
    artifact = builder.build_artifact(composition_value, overlay_value)
    tampered = copy.deepcopy(artifact)
    tampered["unified_lesson_composition"]["composition_items"].append(
        {"source_kind": "KET99_PKU"}
    )
    artifact_path = tmp_path / "artifact.json"
    composition_path = tmp_path / "composition.json"
    overlay_path = tmp_path / "overlay.json"
    for path, value in (
        (artifact_path, tampered),
        (composition_path, composition_value),
        (overlay_path, overlay_value),
    ):
        path.write_text(json.dumps(value))
    report = validator.validate_paths(
        artifact_path=artifact_path,
        r3f_path=composition_path,
        m4_path=overlay_path,
    )
    assert report["validation_status"] == validator.FAIL_STATUS
    assert "artifact_deterministic_rebuild_mismatch" in report["errors"]
