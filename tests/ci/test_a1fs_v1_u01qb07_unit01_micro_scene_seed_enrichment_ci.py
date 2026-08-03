from __future__ import annotations
import json
from copy import deepcopy
from pathlib import Path

from ulga.builders import build_a1fs_v1_policy_bound_content_artifact as content_policy
from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as r1
from ulga.builders import build_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as builder
from ulga.validators import validate_a1fs_v1_policy_bound_content_artifact as policy_validator
from ulga.validators import validate_a1fs_v1_u01qb07_unit01_micro_scene_seed_enrichment as validator

SPEC_PATH = Path(__file__).resolve().parents[2] / "ulga" / "contracts" / "a1fs_v1_u01qb07_unit01_model_authored_scene_supplement.json"


def gap_asset() -> dict:
    return {"content_asset_id":"GAP","content_kind":"MICRO_SCENE","source_lineage":{"source_authority":"PROJECT_AUTHORED_UNIT01_CONTRACT","lineage_mode":"PROJECT_AUTHORED_CONTRACT_COMPLETION"},"content":{"sentences":[]},"target_alignment":{"active_nouns":["book"],"communicative_function_ids":["IDENTIFY","DESCRIBE"]},"scene_profile":{"setting":"UNIT01_OBJECT_SCENE","participants":["LEARNER"],"objects":["BOOK"],"actions":["PROJECT_CONTRACT_COMPLETION"],"information_structure":["FIRST_MENTION","KNOWN_REFERENCE"],"communicative_function_ids":["IDENTIFY","DESCRIBE"]},"admission":{"canonical_admission":True,"template_only":False}}


def contexts() -> list[dict]:
    return [
        {"context_id":"U01-C1","setting":"CLASSROOM","sentences":["Mia is in a classroom.","She has a bag and a book.","There is an apple in the bag.","A cat is near the door.","Mia puts the book on the desk."]},
        {"context_id":"U01-C2","setting":"HOME","sentences":["There is a CD player in the living room.","A toy is in a box near the bed.","The toy is a robot."]},
        {"context_id":"U01-C3","setting":"FOOD_AND_PICNIC","sentences":["Mia has an orange and an egg in a basket.","There is an ice cream near the basket."]},
        {"context_id":"U01-C4","setting":"SHOPPING","sentences":["There is a toy shop near the bus stop.","Mia sees a robot in the shop window."]},
        {"context_id":"U01-C5","setting":"PARK_AND_BIRTHDAY","sentences":["There is a birthday party in the park.","A dog is near a tree and a bench.","The dog has a toy."]},
    ]


def window_seed() -> dict:
    return {"content_asset_id":"WINDOW-SEED","content_kind":"MICRO_SCENE","source_lineage":{"source_authority":"RAZ_READING_AUTHORITY","lineage_mode":"SEMANTIC_ANCHOR_A1_IMITATION"},"content":{"sentences":[]},"target_alignment":{"active_nouns":["window"],"communicative_function_ids":["IDENTIFY","DESCRIBE"]},"scene_profile":{"setting":"UNIT01_OBJECT_SCENE","participants":["LEARNER"],"objects":["WINDOW"],"actions":["A1_IMITATION"],"information_structure":["FIRST_MENTION","KNOWN_REFERENCE"],"communicative_function_ids":["IDENTIFY","DESCRIBE"]},"admission":{"canonical_admission":True,"template_only":False}}


def inventory() -> dict:
    return r1.build_inventory({"payload":{"content_assets":[gap_asset(),window_seed()]}}, contexts())


def spec() -> dict:
    return json.loads(SPEC_PATH.read_text())


def candidate() -> dict:
    return builder.build_pool(inventory(), spec())


def payload() -> dict:
    return candidate()["payload"]


def test_fixture_has_five_existing_genuine_contexts() -> None:
    inv = inventory()
    assert inv["rotation_readiness"]["genuine_distinct_micro_scene_count"] == 5
    assert inv["rotation_readiness"]["non_unclassified_situation_family_count"] == 5


def test_27_model_scenes_expand_policy_bound_candidate_to_32() -> None:
    artifact = candidate()
    assert artifact["artifact_role"] == content_policy.CANDIDATE_ROLE
    assert artifact["learner_facing"] is False
    assert policy_validator.validate_artifact(artifact, expected_role=content_policy.CANDIDATE_ROLE)["error_count"] == 0
    pool = artifact["payload"]
    assert pool["source_counts"]["existing_rotation_ready_scene_count"] == 5
    assert pool["source_counts"]["model_authored_supplement_count"] == 27
    assert pool["rotation_capacity"]["genuine_distinct_micro_scene_count"] == 32
    assert pool["rotation_capacity"]["target_range_pass"] is True
    assert pool["rotation_capacity"]["twelve_form_rotation_ready"] is True
    report = validator.validate(artifact)
    assert report["candidate_artifact_sha256"] == artifact["artifact_sha256"]


def test_independent_validation_can_admit_approved_canonical_scene_pool() -> None:
    artifact = candidate()
    report = validator.validate(artifact)
    approved = builder.admit_validated_candidate(artifact, report)
    assert approved["artifact_role"] == content_policy.APPROVED_ROLE
    assert approved["admission"]["status"] == "APPROVED"
    assert approved["learner_facing"] is False
    assert approved["payload"]["rotation_capacity"]["genuine_distinct_micro_scene_count"] == 32
    assert policy_validator.validate_artifact(approved, expected_role=content_policy.APPROVED_ROLE)["error_count"] == 0


def test_six_life_families_and_large_medium_small_taxonomy_are_present() -> None:
    pool = payload()
    assert set(pool["situation_family_counts"]) == {"SCHOOL","HOME","OUTDOORS","SHOPPING","FOOD_SOCIAL","OUTDOORS_SOCIAL"}
    for row in pool["model_authored_scenes"]:
        assert row["scene_taxonomy"]["large_situation_family"] == row["situation_family"]
        assert row["scene_taxonomy"]["medium_setting"]
        assert row["scene_taxonomy"]["small_micro_scene_event_id"].startswith("MS-EVT-")


def test_every_model_object_is_resolved_to_existing_approved_anchor() -> None:
    pool = payload()
    for row in pool["model_authored_scenes"]:
        assert row["provenance"]["resolved_seed_scene_ref_ids"]
        assert row["provenance"]["source_equivalence_claimed"] is False


def test_new_object_invention_fails_closed() -> None:
    bad = deepcopy(spec())
    bad["candidates"][0]["objects"] = ["BOOK", "HELICOPTER"]
    try:
        builder.build_pool(inventory(), bad)
    except builder.SceneEnrichmentError as exc:
        assert "UNBACKED_MODEL_OBJECTS" in str(exc)
    else:
        raise AssertionError("unbacked model object was admitted")


def test_semantic_duplicate_fails_closed() -> None:
    bad = deepcopy(spec())
    bad["candidates"][1].update({key:deepcopy(bad["candidates"][0][key]) for key in ("large_situation_family","medium_setting","participants","objects","descriptors","actions","relations","information_structure","communicative_function_ids")})
    try:
        builder.build_pool(inventory(), bad)
    except builder.SceneEnrichmentError as exc:
        assert "SEMANTIC_SCENE_DUPLICATE" in str(exc)
    else:
        raise AssertionError("duplicate model scene was admitted")


def test_cumulative_policy_preserves_future_cross_unit_reuse() -> None:
    pool = payload()
    policy = pool["scene_growth_policy"]
    assert policy["later_units_may_add_new_scenes"] is True
    assert policy["prior_unit_scenes_remain_reusable"] is True
    assert policy["later_units_may_reproject_prior_scenes_with_new_language_targets"] is True
    assert policy["scene_identity_includes_unit_target"] is False


def test_validation_report_tamper_cannot_be_admitted() -> None:
    artifact = candidate()
    report = validator.validate(artifact)
    report["cumulative_distinct_scene_count"] = 999
    try:
        builder.admit_validated_candidate(artifact, report)
    except builder.SceneEnrichmentError as exc:
        assert "VALIDATION_REPORT_SHA256_INVALID" in str(exc)
    else:
        raise AssertionError("tampered validation report was admitted")
