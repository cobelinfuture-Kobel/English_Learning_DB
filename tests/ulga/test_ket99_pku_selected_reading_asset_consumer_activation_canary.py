from __future__ import annotations

import copy

from ulga.builders import build_ket99_pku_selected_reading_asset_consumer_activation_canary as builder
from ulga.validators import validate_ket99_pku_selected_reading_asset_consumer_activation_canary as validator


def signed_m4c() -> dict:
    bundles = []
    for pku_id, definition in builder.m4c.ASSET_DEFINITIONS.items():
        bundle = {
            "asset_id": definition["asset_id"],
            "pku_id": pku_id,
            "concept_id": definition["concept_id"],
            "title": definition["title"],
            "skill": "READING",
            "level": "A1+",
            "recommended_lanes": definition["lanes"],
            "teacher_delivery_contract": definition["teacher_delivery"],
            "remediation_contract": definition["remediation"],
            "placements": [{"lesson_id": lesson_id} for lesson_id in builder.m4c.PLACEMENT_POLICY[pku_id]],
            "content_sha256": "b" * 64,
        }
        bundles.append(bundle)
    value = {
        "task_id": builder.m4c.TASK_ID,
        "schema_version": builder.m4c.SCHEMA_VERSION,
        "validation_status": builder.m4c.PASS_STATUS,
        "asset_bundles": bundles,
        "lesson_asset_index": [
            {
                "lesson_id": lesson_id,
                "asset_ids": [
                    bundle["asset_id"]
                    for bundle in bundles
                    if lesson_id in builder.m4c.PLACEMENT_POLICY[bundle["pku_id"]]
                ],
            }
            for lesson_id in sorted(
                {lesson for lessons in builder.m4c.PLACEMENT_POLICY.values() for lesson in lessons}
            )
        ],
        "counts": {
            "authored_asset_bundle_count": 4,
            "authored_placement_count": 11,
            "teacher_delivery_activated_count": 0,
            "remediation_activated_count": 0,
        },
        "errors": [],
        "stop_reason": "NONE",
    }
    value["artifact_sha256"] = builder.digest(value)
    return value


def cp07d(selected_lesson_id: str = "KETR-RB-00-L01", skill: str = "READING", level: str = "A1+") -> dict:
    return {
        "task_id": "M2",
        "schema_version": "m2",
        "validation_status": "PASS",
        "asset_records": [{"asset_key": "A1", "lesson_id": selected_lesson_id}],
        "lesson_catalog": [{"lesson_id": selected_lesson_id, "asset_keys": ["A1"], "roles": ["PRD"]}],
        "counts": {"asset_record_count": 1, "cp07d_projected_asset_count": 1},
        "cp07d_task_id": builder.cp07d.TASK_ID,
        "cp07d_schema_version": builder.cp07d.SCHEMA_VERSION,
        "cp07d_validation_status": builder.cp07d.PASS_STATUS,
        "cp07d_errors": [],
        "cp07d_stop_reason": "NONE",
        "cp07d_delivery_contract": {
            "selected_lesson_id": selected_lesson_id,
            "selected_skill": skill,
            "selected_level": level,
            "projected_asset_keys": ["A1"],
            "response_capture_asset_keys": ["A1"],
            "a2_payload_included": False,
        },
    }


def test_referenced_lesson_attaches_optional_assets_without_mutation() -> None:
    source = cp07d()
    artifact = builder.build_artifact(signed_m4c(), source)
    assert artifact["m4d_private_canary"]["canary_status"] == "PASS_REFERENCED_READING_ASSET_PRIVATE_CANARY"
    assert artifact["m4d_counts"]["selected_lesson_bundle_count"] == 4
    assert artifact["m4d_counts"]["teacher_delivery_asset_attached_count"] == 3
    assert artifact["m4d_counts"]["remediation_asset_registered_count"] == 3
    assert artifact["asset_records"] == source["asset_records"]
    assert artifact["counts"] == source["counts"]


def test_unreferenced_lesson_is_nonblocking() -> None:
    artifact = builder.build_artifact(signed_m4c(), cp07d("KETR-RB-99-L01"))
    assert artifact["m4d_private_canary"]["canary_status"] == "PASS_NON_BLOCKING_NO_SELECTED_READING_ASSET"
    assert artifact["cp07d_delivery_contract"]["optional_teacher_delivery_assets"] == []
    assert artifact["m7_optional_remediation_asset_registry"] == []


def test_nonreading_selection_is_nonblocking() -> None:
    artifact = builder.build_artifact(signed_m4c(), cp07d("KETL-LB-L001", "LISTENING", "A1+"))
    assert artifact["m4d_private_canary"]["selected_lesson_has_authored_assets"] is False


def test_remediation_query_matches_trigger() -> None:
    artifact = builder.build_artifact(signed_m4c(), cp07d())
    rows = builder.remediation_assets_for_tags(artifact, ["SPEAKER_VS_FRIEND_CONFUSION"])
    assert [row["support_asset_id"] for row in rows] == ["KET99-RDG-RM-DETAIL-RELATIONSHIP-V1"]


def test_validator_detects_cp07d_mutation() -> None:
    m4c = signed_m4c()
    source = cp07d()
    artifact = builder.build_artifact(m4c, source)
    report = validator.validate_paths(artifact=artifact, m4c_value=m4c, cp07d_value=source)
    assert report["error_count"] == 0
    tampered = copy.deepcopy(artifact)
    tampered["asset_records"].append({"asset_key": "BAD"})
    report = validator.validate_paths(artifact=tampered, m4c_value=m4c, cp07d_value=source)
    assert report["error_count"] > 0
