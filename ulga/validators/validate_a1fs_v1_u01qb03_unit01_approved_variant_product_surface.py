#!/usr/bin/env python3
"""Validate U01QB03 product-surface and existing-runtime integration."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping

from ulga.builders import (
    build_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as session_runtime,
)
from ulga.builders import (
    build_a1fs_v1_u01qb03_unit01_approved_variant_product_surface as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u01qb02_unit01_approved_variant_session_runtime as session_validator,
)

A1FS_CONTENT_POLICY_MODE = "POLICY_ENFORCER"
VALIDATOR_ID = "A1FS_V1_U01QB03_UNIT01_APPROVED_VARIANT_PRODUCT_SURFACE_VALIDATOR"
FORBIDDEN_LEARNER_KEYS = frozenset(
    {
        "accepted_answers",
        "accepted_sequence",
        "accepted_texts",
        "answer",
        "answer_contract",
        "answer_key",
        "correct_answer",
        "private_item_json",
        "response_contract",
        "rubric",
        "scoring_contract",
    }
)


class ProductSurfaceValidationError(ValueError):
    pass


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ProductSurfaceValidationError(code)


def safe_scan(value: Any) -> None:
    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            for key, child in node.items():
                require(str(key).casefold() not in FORBIDDEN_LEARNER_KEYS, f"learner_private_key_leak:{key}")
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(value)


def validate_bootstrap(value: Mapping[str, Any]) -> None:
    require(value.get("u01qb03_task_id") == builder.TASK_ID, "bootstrap_task_invalid")
    require(value.get("u01qb03_schema_version") == builder.SCHEMA_VERSION, "bootstrap_schema_invalid")
    require(value.get("u01qb03_validation_status") == builder.PASS_STATUS, "bootstrap_status_invalid")
    semantics = value.get("learner_product_semantics")
    require(isinstance(semantics, Mapping), "bootstrap_semantics_missing")
    expected = {
        "unit01_dynamic_approved_variant_sessions_connected": True,
        "unit01_registered_approved_item_count": 288,
        "unit01_session_item_count": 10,
        "unit01_exposure_history_connected": True,
        "unit01_existing_response_scoring_reused": True,
        "unit01_runtime_free_generation_allowed": False,
    }
    for key, target in expected.items():
        require(semantics.get(key) == target, f"bootstrap_semantics_invalid:{key}")
    marked = []
    untouched = []
    for unit in value.get("units", []):
        for lane in unit.get("lanes", []):
            lesson_id = str(lane.get("lesson_id") or "")
            if lesson_id in session_runtime.LESSON_TO_SKILL:
                marked.append(lane)
            else:
                untouched.append(lane)
    require(len(marked) == 3, f"unit01_lane_count_invalid:{len(marked)}")
    for lane in marked:
        require(lane.get("session_item_source") == "U01QB02_VALIDATOR_APPROVED_DYNAMIC_SESSION", "unit01_lane_source_invalid")
        require(lane.get("session_item_count") == 10, "unit01_lane_count_metadata_invalid")
        require(lane.get("static_assets_are_regression_baseline_only") is True, "unit01_static_baseline_invalid")
    require(all("session_item_source" not in lane for lane in untouched), "non_unit01_lane_modified")


def validate_session_payload(value: Mapping[str, Any], *, expected_lesson_id: str) -> None:
    require(value.get("lesson_id") == expected_lesson_id, "session_lesson_invalid")
    require(value.get("dynamic_item_session") is True, "dynamic_session_flag_missing")
    require(value.get("answer_keys_exposed") is False, "answer_exposure_flag_invalid")
    require(value.get("u01qb03_task_id") == builder.TASK_ID, "session_task_invalid")
    assets = value.get("assets")
    require(isinstance(assets, list) and len(assets) == 10, "session_asset_count_invalid")
    require(len({str(row.get("asset_key")) for row in assets}) == 10, "session_asset_duplicate")
    require(len({str(row.get("item_id")) for row in assets}) == 10, "session_item_duplicate")
    for position, asset in enumerate(assets, 1):
        require(str(asset.get("asset_key") or "").startswith("U01QB02:"), f"session_asset_namespace_invalid:{position}")
        require(asset.get("role") == "DYNAMIC_APPROVED_VARIANT", f"session_asset_role_invalid:{position}")
        learner = asset.get("learner_payload")
        require(isinstance(learner, Mapping), f"learner_payload_missing:{position}")
        require(learner.get("item_position") == position, f"item_position_invalid:{position}")
        require(bool(str(learner.get("prompt") or "").strip()), f"prompt_missing:{position}")
        require(learner.get("selection_reason") in session_runtime.SELECTION_REASONS, f"selection_reason_invalid:{position}")
        if learner.get("response_type") == "sequence":
            require(learner.get("options") == [], f"sequence_options_leak:{position}")
            require(bool(learner.get("token_bank")), f"sequence_token_bank_missing:{position}")
        safe_scan(asset)


def validate_completion_gate(value: Mapping[str, Any], *, skill: str) -> None:
    require(value.get("dynamic_item_session") is True, "completion_dynamic_flag_missing")
    require(value.get("mastery_claimed") is False, "completion_mastery_claim_invalid")
    if skill == "SPEAKING":
        require(value.get("gate_mode") == "PRACTICE_SESSION_NO_SCORE", "speaking_gate_mode_invalid")
        require(value.get("required_response_count") == 0, "speaking_denominator_invalid")
        require(value.get("completion_allowed") is True, "speaking_completion_invalid")
        return
    require(
        value.get("gate_mode")
        == "U01QB02_DYNAMIC_SESSION_LATEST_ATTEMPT_PASS_OR_HUMAN_APPROVAL",
        "scored_gate_mode_invalid",
    )
    require(value.get("required_response_count") == 10, "scored_denominator_invalid")
    assets = value.get("assets")
    require(isinstance(assets, list) and len(assets) == 10, "completion_asset_count_invalid")
    require(
        value.get("attempted_response_count", 0)
        + value.get("not_attempted_count", 0)
        == 10,
        "completion_partition_invalid",
    )


def validate_database(database_path: Path) -> dict[str, Any]:
    base = session_validator.validate(database_path)
    require(base.get("error_count") == 0, "u01qb02_runtime_invalid:" + "|".join(base.get("errors", [])))
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        dynamic_sessions = int(
            connection.execute("SELECT COUNT(*) FROM u01qb02_session_plans").fetchone()[0]
        )
        dynamic_assets = int(
            connection.execute("SELECT COUNT(*) FROM u01qb02_item_catalog").fetchone()[0]
        )
        non_unit01_dynamic = int(
            connection.execute(
                """SELECT COUNT(*) FROM u01qb02_item_catalog
                WHERE lesson_id NOT IN (?,?,?)""",
                tuple(session_runtime.UNIT01_LESSONS.values()),
            ).fetchone()[0]
        )
        speaking_capture = int(
            connection.execute(
                """SELECT COUNT(*) FROM u01qb02_item_catalog
                WHERE skill='SPEAKING' AND capture_enabled=1"""
            ).fetchone()[0]
        )
    require(dynamic_assets == 288, f"dynamic_asset_count_invalid:{dynamic_assets}")
    require(non_unit01_dynamic == 0, "dynamic_asset_outside_unit01")
    require(speaking_capture == 0, "speaking_capture_enabled")
    return {
        "registered_dynamic_item_count": dynamic_assets,
        "dynamic_session_count": dynamic_sessions,
        "speaking_capture_enabled_count": speaking_capture,
        "u01qb02_validator_status": base["status"],
    }


def validate_application(app: builder.Unit01VariantProductApplication) -> dict[str, Any]:
    errors: list[str] = []
    readback: dict[str, Any] = {}
    try:
        bootstrap = app.bootstrap()
        validate_bootstrap(bootstrap)
        readback = validate_database(app.database_path)
    except (
        ProductSurfaceValidationError,
        builder.ProductSurfaceError,
        sqlite3.Error,
        OSError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        errors.append(str(exc))
    return {
        "validator_id": VALIDATOR_ID,
        "status": "PASS" if not errors else "FAIL",
        "error_count": len(errors),
        "errors": errors,
        **readback,
        "claim_boundaries": {
            "new_http_route_created": False,
            "parallel_ui_created": False,
            "parallel_response_capture_created": False,
            "parallel_scoring_created": False,
            "unit02_to_unit24_modified": False,
            "audio_enabled": False,
            "speaking_capture_enabled": False,
            "a2_unlocked": False,
            "mastery_claimed": False,
        },
    }
