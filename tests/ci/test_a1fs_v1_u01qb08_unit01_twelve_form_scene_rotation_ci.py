from __future__ import annotations

import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy
from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as r1
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u01qb07
from ulga.builders import build_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as builder
from ulga.validators import validate_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as u01qb07_validator
from ulga.validators import validate_a1fs_v1_u01qb08_unit01_twelve_form_scene_rotation as validator

SPEC_PATH = Path(__file__).resolve().parents[2] / "ulga" / "contracts" / "a1fs_v1_u01qb07_unit01_model_authored_scene_supplement.json"


def gap_asset() -> dict:
    return {"content_asset_id":"GAP","content_kind":"MICRO_SCENE","source_lineage":{"source_authority":"PROJECT_AUTHORED_UNIT01_CONTRACT","lineage_mode":"PROJECT_AUTHORED_CONTRACT_COMPLETION"},"content":{"sentences":[]},"target_alignment":{"active_nouns":["book"],"communicative_function_ids":["IDENTIFY","DESCRIBE"]},"scene_profile":{"setting":"UNIT01_OBJECT_SCENE","participants":["LEARNER"],"objects":["BOOK"],"actions":["PROJECT_CONTRACT_COMPLETION"],"information_structure":["FIRST_MENTION","KNOWN_REFERENCE"],"communicative_function_ids":["IDENTIFY","DESCRIBE"]},"admission":{"canonical_admission":True,"template_only":False}}


def window_seed() -> dict:
    return {"content_asset_id":"WINDOW-SEED","content_kind":"MICRO_SCENE","source_lineage":{"source_authority":"RAZ_READING_AUTHORITY","lineage_mode":"SEMANTIC_ANCHOR_A1_IMITATION"},"content":{"sentences":[]},"target_alignment":{"active_nouns":["window"],"communicative_function_ids":["IDENTIFY","DESCRIBE"]},"scene_profile":{"setting":"UNIT01_OBJECT_SCENE","participants":["LEARNER"],"objects":["WINDOW"],"actions":["A1_IMITATION"],"information_structure":["FIRST_MENTION","KNOWN_REFERENCE"],"communicative_function_ids":["IDENTIFY","DESCRIBE"]},"admission":{"canonical_admission":True,"template_only":False}}


def contexts() -> list[dict]:
    return [
        {"context_id":"U01-C1","setting":"CLASSROOM","sentences":["Mia is in a classroom.","She has a bag and a book.","There is an apple in the bag.","A cat is near the door.","Mia puts the book on the desk."]},
        {"context_id":"U01-C2","setting":"HOME","sentences":["There is a CD player in the living room.","A toy is in a box near the bed.","The toy is a robot."]},
        {"context_id":"U01-C3","setting":"FOOD_AND_PICNIC","sentences":["Mia has an orange and an egg in a basket.","There is an ice cream near the basket."]},
        {"context_id":"U01-C4","setting":"SHOPPING","sentences":["There is a toy shop near the bus stop.","Mia sees a robot in the shop window."]},
        {"context_id":"U01-C5","setting":"PARK_AND_BIRTHDAY","sentences":["There is a birthday party in the park.","A dog is near a tree and a bench.","The dog has a toy."]},
    ]


def approved_scene_pool() -> dict:
    inventory = r1.build_inventory(
        {"payload":{"content_assets":[gap_asset(), window_seed()]}},
        contexts(),
    )
    spec = json.loads(SPEC_PATH.read_text())
    candidate = u01qb07.build_pool(inventory, spec)
    report = u01qb07_validator.validate(candidate)
    return u01qb07.admit_validated_candidate(candidate, report)


def rotation() -> dict:
    return builder.build_rotation(approved_scene_pool())


def test_12_forms_48_slots_and_32_scene_pool_are_materialized() -> None:
    result = rotation()
    assert len(result["forms"]) == 12
    assert sum(form["scene_count"] for form in result["forms"]) == 48
    assert result["rotation_metrics"]["distinct_scene_count"] == 32
    assert result["rotation_metrics"]["reused_scene_count"] == 16
    assert result["rotation_metrics"]["single_exposure_scene_count"] == 16
    validator.validate(result)


def test_every_form_has_four_distinct_scenes_and_at_least_three_families() -> None:
    result = rotation()
    for form in result["forms"]:
        refs = [slot["scene_ref_id"] for slot in form["scene_slots"]]
        families = Counter(slot["situation_family"] for slot in form["scene_slots"])
        assert len(refs) == 4
        assert len(set(refs)) == 4
        assert len(families) >= 3
        assert max(families.values()) <= 2


def test_exact_scene_never_appears_more_than_twice_and_repeat_gap_is_at_least_three() -> None:
    result = rotation()
    forms_by_scene: dict[str, list[int]] = defaultdict(list)
    for form in result["forms"]:
        for slot in form["scene_slots"]:
            forms_by_scene[slot["scene_ref_id"]].append(form["form_ordinal"])
    assert set(forms_by_scene) == {row["scene_ref_id"] for row in result["scene_usage_summary"]}
    for ordinals in forms_by_scene.values():
        assert 1 <= len(ordinals) <= 2
        if len(ordinals) == 2:
            assert ordinals[1] - ordinals[0] >= 3


def test_second_exposure_carries_downstream_two_dimension_change_obligation() -> None:
    result = rotation()
    second_exposures = [
        slot
        for form in result["forms"]
        for slot in form["scene_slots"]
        if slot["exposure_ordinal"] == 2
    ]
    assert len(second_exposures) == 16
    for slot in second_exposures:
        obligation = slot["downstream_reuse_obligation"]
        assert obligation["changed_dimensions_min"] == 2
        assert obligation["same_skill_same_task_angle_repeat_allowed"] is False


def test_rotation_is_deterministic_for_same_approved_pool() -> None:
    approved = approved_scene_pool()
    assert builder.build_rotation(approved) == builder.build_rotation(deepcopy(approved))


def test_candidate_scene_pool_is_rejected_until_approved() -> None:
    inventory = r1.build_inventory(
        {"payload":{"content_assets":[gap_asset(), window_seed()]}},
        contexts(),
    )
    spec = json.loads(SPEC_PATH.read_text())
    candidate = u01qb07.build_pool(inventory, spec)
    assert candidate["artifact_role"] == content_policy.CANDIDATE_ROLE
    try:
        builder.build_rotation(candidate)
    except builder.SceneRotationError as exc:
        assert "APPROVED_SCENE_ARTIFACT_POLICY_INVALID" in str(exc)
    else:
        raise AssertionError("unapproved scene candidate was accepted by rotation builder")


def test_validator_rejects_repeat_gap_tamper() -> None:
    result = rotation()
    tampered = deepcopy(result)
    second = next(
        slot
        for form in tampered["forms"]
        for slot in form["scene_slots"]
        if slot["exposure_ordinal"] == 2
    )
    second["repeat_form_delta"] = 1
    unsigned = deepcopy(tampered)
    unsigned.pop("rotation_sha256", None)
    tampered["rotation_sha256"] = r1.digest(unsigned)
    try:
        validator.validate(tampered)
    except validator.SceneRotationValidationError as exc:
        assert "repeat_form_gap_invalid" in str(exc)
    else:
        raise AssertionError("validator accepted invalid repeat gap")


def test_two_week_calendar_mapping_is_six_days_per_week() -> None:
    result = rotation()
    assert [(form["week"], form["day_in_week"]) for form in result["forms"]] == [
        (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6),
        (2, 1), (2, 2), (2, 3), (2, 4), (2, 5), (2, 6),
    ]
