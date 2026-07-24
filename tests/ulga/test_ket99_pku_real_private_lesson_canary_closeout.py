from __future__ import annotations

import copy
import json
from pathlib import Path

from ulga.builders import build_ket99_pku_real_private_lesson_canary_closeout as builder
from ulga.validators import validate_ket99_pku_real_private_lesson_canary_closeout as validator


def m5(with_references: bool = True) -> dict:
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
    return {
        "ket99_pku_m5_task_id": builder.M5_TASK,
        "ket99_pku_m5_schema_version": builder.M5_SCHEMA,
        "ket99_pku_m5_validation_status": builder.M5_STATUS,
        "unified_lesson_composition": {
            "selected_lesson_id": "L1",
            "selected_skill": "READING",
            "selected_level": "A1",
            "composition_items": [{"source_kind": "KET_ASSET_BODY"}],
            "coverage_summary": {
                "composition_item_count_before_pku_overlay": 1,
                "composition_item_count_after_pku_overlay": 1,
                "delivery_allowed_count_before_pku_overlay": 1,
                "delivery_allowed_count_after_pku_overlay": 1,
            },
            "consumer_gate": {
                "ket99_pku_optional_overlay_connected": True,
                "ket99_pku_metadata_canary_passed": True,
                "ket_asset_body_required": True,
                "missing_pku_reference_blocks_delivery": False,
                "a2_payload_included": False,
            },
            "ket99_pku_optional_overlay": {
                "optional_pilot_references": references,
                "optional_reference_count": len(references),
                "composition_item_count_delta": 0,
                "delivery_allowed_count_delta": 0,
                "missing_reference_blocks_delivery": False,
                "hard_lesson_selection_changed": False,
                "production_mapping_allowed": False,
            },
        },
        "claim_boundaries": {
            "hard_lesson_selection_changed": False,
            "production_mapping_claimed": False,
            "a2_a2plus_in_scope": False,
        },
        "errors": [],
        "stop_reason": "NONE",
    }


def test_referenced_private_canary_closes_pilot() -> None:
    artifact = builder.build_artifact(m5(True))
    assert artifact["validation_status"] == builder.PASS_CLOSEOUT
    assert artifact["pilot_closeout"]["closeout_allowed"] is True
    assert artifact["next_short_step"] == builder.NEXT_MAINLINE
    assert artifact["real_private_lesson_canary"]["optional_pku_ids"] == ["P1"]


def test_no_metadata_canary_does_not_fake_closeout() -> None:
    artifact = builder.build_artifact(m5(False))
    assert artifact["validation_status"] == builder.PASS_PENDING
    assert artifact["pilot_closeout"]["closeout_allowed"] is False
    assert artifact["stop_reason"] == "REAL_REFERENCED_PRIVATE_CANARY_REQUIRED"
    assert artifact["next_short_step"] == builder.TASK_ID


def test_missing_ket_asset_fails_closed() -> None:
    bad = m5()
    bad["unified_lesson_composition"]["composition_items"] = []
    bad["unified_lesson_composition"]["coverage_summary"][
        "composition_item_count_before_pku_overlay"
    ] = 0
    bad["unified_lesson_composition"]["coverage_summary"][
        "composition_item_count_after_pku_overlay"
    ] = 0
    try:
        builder.build_artifact(bad)
    except ValueError as exc:
        assert str(exc) == "real_private_ket_asset_missing"
    else:
        raise AssertionError("missing KET Asset Body was accepted")


def test_item_or_delivery_delta_fails_closed() -> None:
    bad = m5()
    bad["unified_lesson_composition"]["coverage_summary"][
        "composition_item_count_after_pku_overlay"
    ] = 2
    try:
        builder.build_artifact(bad)
    except ValueError as exc:
        assert str(exc) == "composition_item_count_delta_invalid"
    else:
        raise AssertionError("composition item delta was accepted")


def test_production_reference_fails_closed() -> None:
    bad = m5()
    bad["unified_lesson_composition"]["ket99_pku_optional_overlay"][
        "optional_pilot_references"
    ][0]["production_mapping_allowed"] = True
    try:
        builder.build_artifact(bad)
    except ValueError as exc:
        assert str(exc) == "m5_reference_boundary_invalid"
    else:
        raise AssertionError("production reference was accepted")


def test_validator_rejects_tamper(tmp_path: Path) -> None:
    source = m5()
    artifact = builder.build_artifact(source)
    tampered = copy.deepcopy(artifact)
    tampered["pilot_closeout"]["synthetic_test_only"] = True
    artifact_path = tmp_path / "artifact.json"
    m5_path = tmp_path / "m5.json"
    artifact_path.write_text(json.dumps(tampered))
    m5_path.write_text(json.dumps(source))
    report = validator.validate_paths(
        artifact_path=artifact_path,
        m5_path=m5_path,
    )
    assert report["validation_status"] == validator.FAIL_STATUS
    assert "artifact_deterministic_rebuild_mismatch" in report["errors"]
