from __future__ import annotations

import json
from copy import deepcopy

import pytest

from ulga.builders import build_a1fs_online_v1_2_u01e_s01_unit01_five_context_authority_admission as s01
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u01qb07
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u01qb13
from ulga.builders import build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix as builder
from ulga.validators import validate_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08_validator
from ulga.validators import validate_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as u01qb09_validator
from ulga.validators import validate_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix as validator


CANONICAL_FAMILY = {
    "U01-C1-CLASSROOM-BAG": "SCHOOL",
    "U01-C2-HOME-TOY-BOX": "HOME",
    "U01-C3-PICNIC-FOOD": "FOOD_SOCIAL",
    "U01-C4-TOY-SHOP": "SHOPPING",
    "U01-C5-PARK-BIRTHDAY": "OUTDOORS_SOCIAL",
}


def _authority_scene_rows() -> list[dict]:
    rows: list[dict] = []
    for context in s01.CONTEXTS:
        ref = str(context["context_id"])
        rows.append(
            {
                "scene_ref_id": ref,
                "semantic_scene_signature_v2": u01qb08.scene_policy.digest({"scene_ref_id": ref}),
                "situation_family": CANONICAL_FAMILY[ref],
                "setting": str(context["setting"]),
                "micro_scene_event_id": str(context["title"]),
                "scene_origin": "CANONICAL_UNIT01_CONTEXT",
            }
        )
    supplement = json.loads(u01qb07.DEFAULT_SPEC.read_text(encoding="utf-8"))
    for candidate in u01qb07.candidates(supplement):
        ref = str(candidate["candidate_id"])
        rows.append(
            {
                "scene_ref_id": ref,
                "semantic_scene_signature_v2": u01qb08.scene_policy.digest({"scene_ref_id": ref}),
                "situation_family": str(candidate["large_situation_family"]),
                "setting": str(candidate["medium_setting"]),
                "micro_scene_event_id": str(candidate["small_micro_scene_event"]),
                "scene_origin": "MODEL_AUTHORED_SCENE_ENRICHMENT",
            }
        )
    assert len(rows) == 32
    return sorted(rows, key=lambda row: (row["situation_family"], row["scene_ref_id"]))


def _legacy_32_scene_rotation() -> dict:
    rows = _authority_scene_rows()
    original = u01qb08.approved_scene_rows
    fake_approved = {
        "artifact_sha256": "a" * 64,
        "artifact_role": "APPROVED_CANONICAL_JSON",
        "payload": {"task_id": u01qb07.TASK_ID},
    }
    try:
        u01qb08.approved_scene_rows = lambda _approved: deepcopy(rows)
        rotation = u01qb08.build_rotation(fake_approved)
    finally:
        u01qb08.approved_scene_rows = original
    u01qb08_validator.validate(rotation)
    assert rotation["rotation_metrics"]["distinct_scene_count"] == 32
    return rotation


def test_real_scene_authority_has_exactly_one_unit01_deferred_scene() -> None:
    index = builder.scene_bindability_index()
    assert len(index) == 32
    deferred = sorted(ref for ref, row in index.items() if row["runtime_bindable"] is False)
    assert deferred == ["U01-MA-FOOD-04"]
    assert index["U01-MA-FOOD-04"]["anchors"] == []
    assert index["U01-MA-FOOD-04"]["gate_reason"] == "UNIT_ACTIVE_NOUN_ANCHOR_MISSING_DEFER_FOR_LATER_UNIT"
    assert index["U01-MA-FOOD-03"]["anchors"] == ["apple"]
    assert index["U01-MA-OUT-06"]["anchors"] == ["tree"]


def test_runtime_projection_preserves_32_scene_world_but_rotates_only_31_bindable_scenes() -> None:
    legacy = _legacy_32_scene_rotation()
    projection = builder.project_existing_rotation(legacy)
    assert projection["cumulative_scene_world_count"] == 32
    assert projection["unit_runtime_bindable_scene_count"] == 31
    assert projection["unit_runtime_deferred_scene_count"] == 1
    assert projection["deferred_scene_refs"] == ["U01-MA-FOOD-04"]
    assert projection["deferred_scenes_remain_in_cumulative_scene_world"] is True
    assert projection["rotation_capacity_pass"] is True
    assert len(projection["runtime_rows"]) == 31
    assert projection["deferred_rows"][0]["scene_ref_id"] == "U01-MA-FOOD-04"
    assert projection["boundaries"]["cumulative_scene_authority_mutated"] is False
    assert projection["boundaries"]["deferred_scene_deleted"] is False


def test_rematerialized_rotation_is_48_slots_over_31_bindable_scenes() -> None:
    rotation = builder.rematerialize_rotation(_legacy_32_scene_rotation())
    u01qb08_validator.validate(rotation)
    gate = builder.validate_rotation_runtime_bindability(rotation)
    assert gate["cumulative_scene_world_count"] == 32
    assert gate["unit_runtime_bindable_scene_count"] == 31
    assert gate["deferred_scene_refs"] == ["U01-MA-FOOD-04"]
    assert gate["scene_slot_count"] == 48
    assert rotation["rotation_metrics"]["distinct_scene_count"] == 31
    assert rotation["rotation_metrics"]["reused_scene_count"] == 17
    assert rotation["rotation_metrics"]["single_exposure_scene_count"] == 14
    assert rotation["rotation_metrics"]["min_repeat_form_delta"] >= 3
    used = {
        slot["scene_ref_id"]
        for form in rotation["forms"]
        for slot in form["scene_slots"]
    }
    assert "U01-MA-FOOD-04" not in used
    assert len(used) == 31
    assert all(
        slot["unit_runtime_bindable"] is True and slot["unit_runtime_anchors"]
        for form in rotation["forms"]
        for slot in form["scene_slots"]
    )


def test_u01qb09_rebuild_stays_12_forms_48_scenes_240_activities() -> None:
    rotation = builder.rematerialize_rotation(_legacy_32_scene_rotation())
    allocation = builder.rematerialize_allocation(rotation)
    u01qb09_validator.validate(allocation)
    report = validator.validate(rotation, allocation)
    metrics = allocation["allocation_metrics"]
    assert metrics["form_count"] == 12
    assert metrics["scene_exposure_count"] == 48
    assert metrics["activity_slot_count"] == 240
    assert metrics["scored_activity_slot_count"] == 192
    assert metrics["speaking_practice_slot_count"] == 48
    assert report["status"] == validator.PASS_STATUS
    assert allocation["source_identity"]["rotation_sha256"] == rotation["rotation_sha256"]


def test_u01qb13_adapter_preserves_deferred_scene_but_does_not_require_it_for_rotation() -> None:
    original = u01qb13._scene_semantic_index
    with builder.u01qb13_deferred_scene_adapter():
        semantics = u01qb13._scene_semantic_index()
        assert len(semantics) == 32
        assert semantics["U01-MA-FOOD-04"]["unit_runtime_bindable"] is False
        assert semantics["U01-MA-FOOD-04"]["anchors"] == []
        assert semantics["U01-MA-FOOD-03"]["unit_runtime_bindable"] is True
        assert semantics["U01-MA-FOOD-03"]["anchors"] == ["apple"]
    assert u01qb13._scene_semantic_index is original


def test_old_32_scene_rotation_is_not_accepted_as_runtime_bindable_r1_rotation() -> None:
    legacy = _legacy_32_scene_rotation()
    with pytest.raises(builder.RuntimeBindabilityGateError, match="RUNTIME_BINDABILITY_PROJECTION_MISSING"):
        builder.validate_rotation_runtime_bindability(legacy)
