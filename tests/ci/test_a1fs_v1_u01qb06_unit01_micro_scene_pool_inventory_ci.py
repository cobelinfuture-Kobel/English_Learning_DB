from __future__ import annotations

from copy import deepcopy

from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as builder
from ulga.validators import validate_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as validator


def asset(
    asset_id: str,
    *,
    setting: str,
    objects: list[str],
    action: str,
    lineage_mode: str = "SEMANTIC_EQUIVALENT_REWRITE",
    semantic_identity: str | None = None,
    relation_sentence: str = "",
    theme_id: str = "",
) -> dict:
    identity = semantic_identity or f"SEM-{asset_id}"
    legacy_signature = builder.digest({"identity": identity, "setting": setting, "objects": objects, "actions": [action]})
    return {
        "content_asset_id": asset_id,
        "content_kind": "MICRO_SCENE",
        "source_lineage": {
            "source_authority": "PROJECT_AUTHORED_UNIT01_CONTRACT"
            if lineage_mode == "PROJECT_AUTHORED_CONTRACT_COMPLETION"
            else "RAZ_READING_AUTHORITY",
            "semantic_identity": identity,
            "lineage_mode": lineage_mode,
        },
        "content": {"sentences": [relation_sentence] if relation_sentence else [], "dialogue_turns": []},
        "target_alignment": {
            "active_nouns": [v.casefold() for v in objects],
            "active_adjectives": [],
            "theme_id": theme_id,
            "situation_family_id": setting,
            "micro_situation_id": f"LEGACY-{asset_id}",
            "communicative_function_ids": ["IDENTIFY", "DESCRIBE"],
        },
        "scene_profile": {
            "setting": setting,
            "participants": ["LEARNER"],
            "objects": objects,
            "descriptors": [],
            "actions": [action],
            "information_structure": ["FIRST_MENTION", "KNOWN_REFERENCE"],
            "communicative_function_ids": ["IDENTIFY", "DESCRIBE"],
            "semantic_scene_id": f"LEGACY-SCENE-{asset_id}",
            "distinct_scene_signature": legacy_signature,
        },
        "admission": {"canonical_admission": True, "template_only": False},
    }


def approved(rows: list[dict]) -> dict:
    return {"payload": {"content_assets": rows}}


def context(
    context_id: str,
    setting: str,
    *,
    sentence: str = "A book is near a box.",
    role: str = "ANCHOR_CONTEXT",
    source_role: str = "TEST_CANONICAL_CONTEXT",
) -> dict:
    return {
        "context_id": context_id,
        "setting": setting,
        "role": role,
        "source_role": source_role,
        "sentences": [sentence],
    }


def test_v3_signature_excludes_source_identity_and_groups_semantic_duplicate() -> None:
    first = asset(
        "U01-MS-A",
        setting="PARK",
        objects=["DOG", "TREE"],
        action="LOCATE",
        semantic_identity="SOURCE-A",
        relation_sentence="A dog is near the tree.",
    )
    second = asset(
        "U01-MS-B",
        setting="PARK",
        objects=["DOG", "TREE"],
        action="LOCATE",
        semantic_identity="SOURCE-B",
        relation_sentence="The dog is near the tree.",
    )
    assert first["scene_profile"]["distinct_scene_signature"] != second["scene_profile"]["distinct_scene_signature"]
    result = builder.build_inventory(approved([first, second]), [])
    assert result["scene_rows"][0]["semantic_scene_signature_v2"] == result["scene_rows"][1]["semantic_scene_signature_v2"]
    assert len(result["semantic_duplicate_groups"]) == 1
    assert result["rotation_readiness"]["genuine_distinct_micro_scene_count"] == 1
    validator.validate(result)


def test_project_authored_gap_completion_does_not_count_as_genuine_scene() -> None:
    gap = asset(
        "U01-MS-GAP",
        setting="PARK",
        objects=["DOG", "TREE"],
        action="PROJECT_CONTRACT_COMPLETION",
        lineage_mode="PROJECT_AUTHORED_CONTRACT_COMPLETION",
        relation_sentence="A dog is near the tree.",
    )
    result = builder.build_inventory(approved([gap]), [context("U01-C1", "CLASSROOM")])
    assert result["classification_counts"]["COVERAGE_COMPLETION_NOT_SCENE"] == 1
    assert result["raw_counts"]["project_authored_completion_asset_count"] == 1
    assert result["rotation_readiness"]["genuine_distinct_micro_scene_count"] == 1
    assert result["rotation_readiness"]["twelve_form_rotation_ready"] is False
    validator.validate(result)


def test_under_specified_object_only_asset_is_scene_seed_not_rotation_scene() -> None:
    row = asset("U01-MS-OBJECT", setting="UNIT01_OBJECT_SCENE", objects=["BOOK"], action="A1_IMITATION")
    result = builder.build_inventory(approved([row]), [])
    assert result["scene_rows"][0]["rotation_class"] == "SCENE_SEED_NEEDS_ENRICHMENT"
    assert result["scene_rows"][0]["counts_toward_scene_rotation"] is False
    assert result["rotation_readiness"]["genuine_distinct_micro_scene_count"] == 0
    validator.validate(result)


def test_setting_only_identification_is_not_a_genuine_life_scene() -> None:
    park = asset("U01-MS-PARK", setting="PARK", objects=["PARK"], action="IDENTIFY")
    room = asset("U01-MS-ROOM", setting="ROOM", objects=["ROOM"], action="IDENTIFY")
    result = builder.build_inventory(approved([park, room]), [])
    assert result["rotation_readiness"]["genuine_distinct_micro_scene_count"] == 0
    assert result["classification_counts"]["SCENE_SEED_NEEDS_ENRICHMENT"] == 2
    for row in result["scene_rows"]:
        assert "NO_CONCRETE_SCENE_OBJECT" in row["rotation_reason_codes"]
        assert row["counts_toward_scene_rotation"] is False
    validator.validate(result)


def test_canonical_context_extracts_real_semantics_and_ignores_roles_in_signature() -> None:
    first = {
        "context_id": "U01-C1",
        "setting": "CLASSROOM",
        "role": "ANCHOR_CONTEXT",
        "source_role": "SOURCE_A",
        "sentences": [
            "Mia is in a classroom.",
            "She has a bag and a book.",
            "A cat is near the door.",
            "Mia puts the book on the desk.",
        ],
    }
    second = deepcopy(first)
    second["context_id"] = "U01-C1-ALT"
    second["role"] = "UNSEEN_TRANSFER"
    second["source_role"] = "SOURCE_B"
    result = builder.build_inventory(approved([asset("SEED", setting="UNIT01_OBJECT_SCENE", objects=["BOOK"], action="A1_IMITATION")]), [first, second])
    rows = [r for r in result["scene_rows"] if r["scene_origin"] == "CANONICAL_UNIT01_CONTEXT"]
    assert rows[0]["semantic_scene_signature_v2"] == rows[1]["semantic_scene_signature_v2"]
    core = rows[0]["semantic_scene_core"]
    assert {"BAG", "BOOK", "CAT", "DOOR", "DESK"} <= set(core["objects"])
    assert {"HAVE", "PUT"} <= set(core["actions"])
    assert {"NEAR", "ON", "IN"} <= set(core["relations"])
    assert "context_role" not in core
    assert "source_role" not in core
    assert rows[0]["rotation_class"] == "ROTATION_READY"
    assert result["rotation_readiness"]["genuine_distinct_micro_scene_count"] == 1
    validator.validate(result)


def test_theme_is_not_used_as_situation_family_fallback() -> None:
    row = asset(
        "U01-MS-CAT",
        setting="UNIT01_OBJECT_SCENE",
        objects=["CAT", "BED"],
        action="LOCATE",
        relation_sentence="A cat is near the bed.",
        theme_id="ANIMALS",
    )
    result = builder.build_inventory(approved([row]), [])
    scene = result["scene_rows"][0]
    assert scene["theme_id"] == "ANIMALS"
    assert scene["situation_family"] == "UNCLASSIFIED_OBJECT"
    assert scene["scene_taxonomy"]["large_situation_family"] == "UNCLASSIFIED_OBJECT"
    assert scene["rotation_class"] == "SCENE_SEED_NEEDS_ENRICHMENT"
    validator.validate(result)


def test_large_medium_small_taxonomy_and_cumulative_growth_policy_are_explicit() -> None:
    row = asset(
        "U01-MS-PARK-DOG",
        setting="PARK",
        objects=["DOG", "TREE"],
        action="LOCATE",
        relation_sentence="A dog is near the tree.",
    )
    result = builder.build_inventory(approved([row]), [])
    scene = result["scene_rows"][0]
    assert scene["scene_taxonomy"]["large_situation_family"] == "OUTDOORS"
    assert scene["scene_taxonomy"]["medium_setting"] == "PARK"
    assert scene["scene_taxonomy"]["small_micro_scene_event_id"].startswith("MS-EVT-")
    assert result["scene_growth_policy"]["prior_unit_scenes_remain_reusable"] is True
    assert result["scene_growth_policy"]["later_units_may_add_new_scenes"] is True
    assert result["scene_growth_policy"]["later_units_may_reproject_prior_scenes_with_new_language_targets"] is True
    assert result["scene_growth_policy"]["scene_identity_includes_unit_target"] is False
    validator.validate(result)


def test_24_distinct_scenes_across_five_families_meet_hard_12_form_capacity() -> None:
    settings = ["CLASSROOM", "HOME", "PARK", "SHOP", "FOOD_AND_PICNIC"]
    unique_objects = [
        "ant", "bird", "cake", "desk", "egg", "fish", "gift", "hat", "ink", "jar", "kite", "lamp",
        "map", "net", "owl", "pen", "queen", "ring", "sock", "toy", "urn", "van", "watch", "yak",
    ]
    contexts = [
        context(
            f"U01-C-{i:02d}",
            settings[i % 5],
            sentence=f"A {unique_objects[i]} is near a box.",
            role=f"ROLE_{i:02d}",
        )
        for i in range(24)
    ]
    seed = asset("U01-MS-SEED", setting="UNIT01_OBJECT_SCENE", objects=["BOOK"], action="A1_IMITATION")
    result = builder.build_inventory(approved([seed]), contexts)
    readiness = result["rotation_readiness"]
    assert readiness["genuine_distinct_micro_scene_count"] == 24
    assert readiness["maximum_scene_slots_at_two_uses_each"] == 48
    assert readiness["hard_distinct_scene_capacity_pass"] is True
    assert readiness["situation_family_capacity_pass"] is True
    assert readiness["twelve_form_rotation_ready"] is True
    assert readiness["release_classification"] == "READY_FOR_12_FORM_ROTATION"
    validator.validate(result)


def test_scope_and_mutation_boundaries_remain_closed() -> None:
    row = asset(
        "U01-MS-1",
        setting="PARK",
        objects=["DOG", "TREE"],
        action="LOCATE",
        relation_sentence="A dog is near the tree.",
    )
    result = builder.build_inventory(approved([row]), [context("U01-C1", "CLASSROOM")])
    assert result["scope"] == {
        "unit01_only": True,
        "question_bank_modified": False,
        "parallel_question_bank_created": False,
        "parallel_scoring_created": False,
        "unit02_to_unit24_modified": False,
        "a2_unlocked": False,
    }
    assert all(value is False for value in result["boundaries"].values())
    validator.validate(result)


def test_validator_rejects_nonsemantic_identity_in_semantic_core() -> None:
    row = asset(
        "U01-MS-1",
        setting="PARK",
        objects=["DOG", "TREE"],
        action="LOCATE",
        relation_sentence="A dog is near the tree.",
    )
    result = builder.build_inventory(approved([row]), [])
    drifted = deepcopy(result)
    drifted["scene_rows"][0]["semantic_scene_core"]["source_role"] = "FORBIDDEN"
    drifted["scene_rows"][0]["semantic_scene_signature_v2"] = builder.digest(drifted["scene_rows"][0]["semantic_scene_core"])
    drifted["scene_rows"][0]["scene_taxonomy"] = builder.scene_taxonomy(drifted["scene_rows"][0]["semantic_scene_core"])
    unsigned = deepcopy(drifted)
    unsigned.pop("inventory_sha256", None)
    drifted["inventory_sha256"] = builder.digest(unsigned)
    try:
        validator.validate(drifted)
    except validator.InventoryValidationError as exc:
        assert "nonsemantic_identity_leaked_into_semantic_core" in str(exc)
    else:
        raise AssertionError("validator accepted source/pedagogic identity in semantic scene core")
