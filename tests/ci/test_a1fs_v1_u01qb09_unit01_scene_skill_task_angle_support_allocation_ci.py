from __future__ import annotations

from copy import deepcopy

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy
from ulga.builders import build_a1fs_v1_u01qb01_unit01_pattern_family_approved_variant_pool as bank
from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as scene_policy
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u01qb07
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as u01qb08
from ulga.builders import build_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as builder
from ulga.validators import validate_a1fs_v1_u01qb09_unit01_scene_skill_task_angle_support_allocation as validator


def approved_scene_pool() -> dict:
    families = ["SCHOOL", "HOME", "OUTDOORS", "SHOPPING", "FOOD_SOCIAL", "OUTDOORS_SOCIAL"]
    settings = {
        "SCHOOL": "CLASSROOM",
        "HOME": "BEDROOM",
        "OUTDOORS": "PARK",
        "SHOPPING": "SHOPPING",
        "FOOD_SOCIAL": "PICNIC",
        "OUTDOORS_SOCIAL": "PARK_AND_BIRTHDAY",
    }
    rows = []
    for index in range(32):
        family = families[index % len(families)]
        rows.append(
            {
                "scene_ref_id": f"TEST-SCENE-{index + 1:02d}",
                "semantic_scene_signature_v2": scene_policy.digest({"scene": index + 1}),
                "situation_family": family,
                "setting": settings[family],
                "micro_scene_event_id": f"MS-EVT-{index + 1:04d}",
                "scene_origin": "TEST_APPROVED_SCENE",
            }
        )
    payload = {
        "task_id": u01qb07.TASK_ID,
        "unit_id": u01qb07.UNIT_ID,
        "status": u01qb07.PASS_STATUS,
        "rotation_capacity": {"twelve_form_rotation_ready": True},
        "cumulative_unique_scenes": rows,
    }
    candidate = content_policy.build_candidate(
        payload=payload,
        producer_id="test_u01qb09_scene_pool",
        level_scope=["A1"],
        source_bindings={"test_fixture": True},
    )
    return content_policy.admit_candidate(
        candidate,
        validation_receipts=[
            {"validator_id": "test_scene_validator", "status": "PASS", "receipt_sha256": "0" * 64}
        ],
        decision_ref="TEST:U01QB09",
        producer_id="test_u01qb09_scene_pool_approval",
    )


def rotation() -> dict:
    return u01qb08.build_rotation(approved_scene_pool())


def allocation() -> dict:
    return builder.build_allocation(rotation())


def test_12_forms_48_scene_exposures_and_240_activity_slots() -> None:
    result = allocation()
    metrics = result["allocation_metrics"]
    assert metrics["form_count"] == 12
    assert metrics["scene_exposure_count"] == 48
    assert metrics["activity_slot_count"] == 240
    assert metrics["scored_activity_slot_count"] == 192
    assert metrics["speaking_practice_slot_count"] == 48
    assert metrics["skill_slot_counts"] == {"READING": 96, "SPEAKING": 48, "WRITING": 96}
    validator.validate(result)


def test_each_scene_exposure_has_2_reading_2_writing_1_speaking() -> None:
    result = allocation()
    for form in result["forms"]:
        assert form["scene_count"] == 4
        assert form["activity_count"] == 20
        assert form["scored_activity_count"] == 16
        assert form["speaking_practice_count"] == 4
        for scene in form["scene_packages"]:
            skills = [row["skill"] for row in scene["activities"]]
            assert skills.count("READING") == 2
            assert skills.count("WRITING") == 2
            assert skills.count("SPEAKING") == 1
            speaking = next(row for row in scene["activities"] if row["skill"] == "SPEAKING")
            assert speaking["scored"] is False
            assert speaking["practice_only"] is True
            assert speaking["assessment_candidate"] is False


def test_support_progression_is_guided_reduced_independent_transfer() -> None:
    result = allocation()
    assert [form["support_level"] for form in result["forms"]] == [
        "GUIDED", "GUIDED", "GUIDED",
        "REDUCED_SUPPORT", "REDUCED_SUPPORT", "REDUCED_SUPPORT",
        "INDEPENDENT", "INDEPENDENT", "INDEPENDENT",
        "TRANSFER", "TRANSFER", "TRANSFER",
    ]
    assert result["allocation_metrics"]["support_scene_counts"] == {
        "GUIDED": 12, "INDEPENDENT": 12, "REDUCED_SUPPORT": 12, "TRANSFER": 12
    }


def test_repeat_scene_changes_support_perspective_and_task_angles_without_pair_replay() -> None:
    result = allocation()
    seen: dict[str, dict] = {}
    repeated = 0
    for form in result["forms"]:
        for scene in form["scene_packages"]:
            ref = scene["scene_ref_id"]
            if ref in seen:
                repeated += 1
                prior_pairs = {(row["skill"], row["task_angle"]) for row in seen[ref]["activities"]}
                current_pairs = {(row["skill"], row["task_angle"]) for row in scene["activities"]}
                assert not (prior_pairs & current_pairs)
                assert set(scene["reuse_change_dimensions"]) >= {"SUPPORT_LEVEL", "PROMPT_PERSPECTIVE", "TASK_ANGLE"}
            seen[ref] = scene
    assert repeated == 16


def test_current_12_family_bank_gaps_are_explicit_not_silently_claimed_supported() -> None:
    result = allocation()
    metrics = result["allocation_metrics"]
    assert metrics["question_bank_full_alignment_ready"] is False
    assert metrics["question_bank_reconciliation_required"] is True
    assert metrics["scored_gap_count"] > 0
    assert metrics["scored_partial_support_count"] > 0
    assert metrics["gap_task_angle_counts"]["COMPLETE_SENTENCE_PRODUCTION"] > 0
    assert metrics["gap_task_angle_counts"]["CONNECTED_SENTENCE_PRODUCTION"] > 0
    existing_family_ids = {row[0] for row in bank.FAMILIES}
    for binding in result["task_angle_bank_bindings"]:
        assert set(binding["pattern_family_ids"]) <= existing_family_ids


def test_transfer_forms_mark_reading_writing_as_assessment_candidates_but_not_speaking() -> None:
    result = allocation()
    for form in result["forms"][9:]:
        assert form["support_level"] == "TRANSFER"
        for scene in form["scene_packages"]:
            for activity in scene["activities"]:
                if activity["skill"] == "SPEAKING":
                    assert activity["assessment_candidate"] is False
                else:
                    assert activity["assessment_candidate"] is True


def test_validator_rejects_speaking_scoring_drift() -> None:
    result = allocation()
    drifted = deepcopy(result)
    speaking = next(
        row
        for form in drifted["forms"]
        for scene in form["scene_packages"]
        for row in scene["activities"]
        if row["skill"] == "SPEAKING"
    )
    speaking["scored"] = True
    unsigned = deepcopy(drifted)
    unsigned.pop("allocation_sha256", None)
    drifted["allocation_sha256"] = scene_policy.digest(unsigned)
    try:
        validator.validate(drifted)
    except validator.AllocationValidationError as exc:
        assert "speaking_boundary_invalid" in str(exc)
    else:
        raise AssertionError("validator accepted scored speaking drift")


def test_scope_boundaries_keep_question_bank_and_runtime_untouched() -> None:
    result = allocation()
    assert result["boundaries"] == {
        "scene_authority_modified": False,
        "new_scene_authored": False,
        "question_bank_modified": False,
        "question_items_materialized": False,
        "scoring_modified": False,
        "learner_state_modified": False,
        "speaking_scoring_enabled": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
    }
