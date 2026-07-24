from __future__ import annotations

import copy
from pathlib import Path

import pytest

from ulga.builders import build_ket99_pku_m4d_private_chain_materialization as builder
from ulga.validators import validate_ket99_pku_m4d_private_chain_materialization as validator


def path_map(tmp_path: Path) -> dict[str, Path]:
    keys = {
        "cp01", "cp02", "registry", "dedup", "unit_contract", "raz_source_root",
        "m1", "m2", "cp07b", "m4c", "cp03", "cp03_report", "cp04",
        "cp04_report", "cp05_candidate", "cp05_approved", "cp05_safe",
        "cp05_report", "cp06", "cp06_report", "cp07a", "cp07a_report",
        "state_db", "m4_plan", "cp07c", "cp07c_report", "cp07d",
        "cp07d_report", "m4d", "m4d_report",
    }
    return {key: tmp_path / key for key in keys}


def m4d_value() -> dict:
    return {
        "m4d_task_id": builder.m4d.TASK_ID,
        "m4d_validation_status": builder.m4d.PASS_STATUS,
        "m4d_errors": [],
        "m4d_stop_reason": "NONE",
        "m4d_private_canary": {
            "selected_lesson_id": "KETL-LB-L001",
            "canary_status": "PASS_NON_BLOCKING_NO_SELECTED_READING_ASSET",
            "selected_lesson_has_authored_assets": False,
            "teacher_delivery_asset_count": 0,
            "remediation_asset_count": 0,
        },
        "m4d_counts": {
            "composition_item_delta": 0,
            "required_delivery_asset_delta": 0,
            "asset_record_delta": 0,
            "response_capture_contract_delta": 0,
            "mastery_evidence_delta": 0,
            "canonical_coverage_delta": 0,
            "a2_unlock_count": 0,
        },
    }


def summary() -> dict:
    value = {
        "task_id": builder.TASK_ID,
        "schema_version": builder.SCHEMA_VERSION,
        "validation_status": builder.PASS_STATUS,
        "scope": "A1_A1_PLUS_ONLY",
        "stage_order": list(builder.STAGE_ORDER),
        "stages": [
            {"stage": stage, "status": "PASS", "artifact_sha256": "a" * 64}
            for stage in builder.STAGE_ORDER
        ],
        "selected_lesson": {
            "lesson_id": "KETL-LB-L001",
            "skill": "LISTENING",
            "level": "A1+",
            "planner_selection_preserved": True,
            "preferred_skill_override_used": False,
        },
        "m4d_private_canary": {
            "canary_status": "PASS_NON_BLOCKING_NO_SELECTED_READING_ASSET",
            "selected_lesson_has_authored_assets": False,
            "teacher_delivery_asset_count": 0,
            "remediation_asset_count": 0,
        },
        "source_identity": {
            "m1_sha256": "1" * 64,
            "m2_sha256": "2" * 64,
            "cp07b_sha256": "3" * 64,
            "m4c_sha256": "4" * 64,
            "m4d_sha256": "5" * 64,
        },
        "claim_boundaries": {
            "canonical_data_modified": False,
            "operator_learner_state_modified": False,
            "planner_preferred_skill_forced": False,
            "synthetic_lesson_composition_created": False,
            "learner_facing_content_added": False,
            "mastery_or_retention_claimed": False,
            "a2_unlocked": False,
        },
        "errors": [],
        "stop_reason": "NONE",
        "next_short_step": builder.NEXT_SHORT_STEP,
    }
    value["artifact_sha256"] = builder.digest(value)
    return value


def test_command_plan_uses_existing_mainline_order(tmp_path: Path) -> None:
    plan = builder.build_command_plan(path_map(tmp_path))
    assert [stage for stage, _ in plan] == list(builder.STAGE_ORDER)
    assert all(command[:2] == [builder.sys.executable, "-m"] for _, command in plan)


def test_m4_plan_does_not_force_reading_or_any_preferred_skill(tmp_path: Path) -> None:
    plan = dict(builder.build_command_plan(path_map(tmp_path)))
    m4_command = plan["M4"]
    assert "--preferred-skill" not in m4_command
    assert "--plan-id" in m4_command
    assert builder.CANARY_PLAN_ID in m4_command


def test_explicit_missing_artifact_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(builder.ChainMaterializationError, match="explicit_artifact_missing"):
        builder.discover_artifact(
            explicit=tmp_path / "missing.json",
            filename="missing.json",
            roots=[tmp_path],
        )


def test_validator_accepts_nonblocking_mainline_canary() -> None:
    report = validator.validate_artifact(summary(), m4d_value())
    assert report["error_count"] == 0
    assert report["validation_status"] == builder.PASS_STATUS
    assert report["stage_count"] == len(builder.STAGE_ORDER)


def test_validator_rejects_forced_selection_and_mastery_mutation() -> None:
    artifact = summary()
    artifact["selected_lesson"]["preferred_skill_override_used"] = True
    artifact["artifact_sha256"] = builder.digest({key: value for key, value in artifact.items() if key != "artifact_sha256"})
    m4d = copy.deepcopy(m4d_value())
    m4d["m4d_counts"]["mastery_evidence_delta"] = 1
    report = validator.validate_artifact(artifact, m4d)
    assert report["error_count"] >= 2
    assert "preferred_skill_override_forbidden" in report["errors"]
    assert "m4d_zero_delta_invalid:mastery_evidence_delta" in report["errors"]
