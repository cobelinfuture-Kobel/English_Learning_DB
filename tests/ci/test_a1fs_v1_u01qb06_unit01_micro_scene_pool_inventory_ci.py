from __future__ import annotations

from copy import deepcopy

from ulga.builders import build_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as builder
from ulga.validators import validate_a1fs_v1_u01qb06_unit01_micro_scene_pool_inventory as validator


def asset(asset_id: str, *, setting: str, objects: list[str], action: str, lineage_mode: str = "SEMANTIC_EQUIVALENT_REWRITE", semantic_identity: str | None = None, relation_sentence: str = "") -> dict:
    identity = semantic_identity or f"SEM-{asset_id}"
    legacy_signature = builder.digest({"identity": identity, "setting": setting, "objects": objects, "actions": [action]})
    return {
        "content_asset_id": asset_id, "content_kind": "MICRO_SCENE",
        "source_lineage": {"source_authority": "PROJECT_AUTHORED_UNIT01_CONTRACT" if lineage_mode == "PROJECT_AUTHORED_CONTRACT_COMPLETION" else "RAZ_READING_AUTHORITY", "semantic_identity": identity, "lineage_mode": lineage_mode},
        "content": {"sentences": [relation_sentence] if relation_sentence else [], "dialogue_turns": []},
        "target_alignment": {"active_nouns": [v.casefold() for v in objects], "active_adjectives": [], "theme_id": "", "situation_family_id": setting, "micro_situation_id": f"LEGACY-{asset_id}", "communicative_function_ids": ["IDENTIFY", "DESCRIBE"]},
        "scene_profile": {"setting": setting, "participants": ["LEARNER"], "objects": objects, "descriptors": [], "actions": [action], "information_structure": ["FIRST_MENTION", "KNOWN_REFERENCE"], "communicative_function_ids": ["IDENTIFY", "DESCRIBE"], "semantic_scene_id": f"LEGACY-SCENE-{asset_id}", "distinct_scene_signature": legacy_signature},
        "admission": {"canonical_admission": True, "template_only": False},
    }

def approved(rows: list[dict]) -> dict: return {"payload": {"content_assets": rows}}

def context(context_id: str, setting: str, role: str = "ANCHOR_CONTEXT") -> dict:
    return {"context_id": context_id, "setting": setting, "context_role": role, "source_role": "TEST_CANONICAL_CONTEXT"}

def test_v2_signature_excludes_source_identity_and_groups_semantic_duplicate() -> None:
    first = asset("U01-MS-A", setting="PARK", objects=["DOG", "TREE"], action="LOCATE", semantic_identity="SOURCE-A", relation_sentence="A dog is near the tree.")
    second = asset("U01-MS-B", setting="PARK", objects=["DOG", "TREE"], action="LOCATE", semantic_identity="SOURCE-B", relation_sentence="The dog is near the tree.")
    assert first["scene_profile"]["distinct_scene_signature"] != second["scene_profile"]["distinct_scene_signature"]
    result = builder.build_inventory(approved([first, second]), [])
    assert result["scene_rows"][0]["semantic_scene_signature_v2"] == result["scene_rows"][1]["semantic_scene_signature_v2"]
    assert len(result["semantic_duplicate_groups"]) == 1
    assert result["rotation_readiness"]["genuine_distinct_micro_scene_count"] == 1
    validator.validate(result)

def test_project_authored_gap_completion_does_not_count_as_genuine_scene() -> None:
    gap = asset("U01-MS-GAP", setting="PARK", objects=["DOG", "TREE"], action="PROJECT_CONTRACT_COMPLETION", lineage_mode="PROJECT_AUTHORED_CONTRACT_COMPLETION", relation_sentence="A dog is near the tree.")
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

def test_24_distinct_scenes_across_five_families_meet_hard_12_form_capacity() -> None:
    settings = ["CLASSROOM", "HOME", "PARK", "SHOP", "FOOD_AND_PICNIC"]
    contexts = [context(f"U01-C-{i:02d}", settings[i % 5], role=f"ROLE_{i:02d}") for i in range(24)]
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
    row = asset("U01-MS-1", setting="PARK", objects=["DOG", "TREE"], action="LOCATE", relation_sentence="A dog is near the tree.")
    result = builder.build_inventory(approved([row]), [context("U01-C1", "CLASSROOM")])
    assert result["scope"] == {"unit01_only": True, "question_bank_modified": False, "parallel_question_bank_created": False, "parallel_scoring_created": False, "unit02_to_unit24_modified": False, "a2_unlocked": False}
    assert all(value is False for value in result["boundaries"].values())
    validator.validate(result)

def test_validator_rejects_source_identity_in_semantic_core() -> None:
    row = asset("U01-MS-1", setting="PARK", objects=["DOG", "TREE"], action="LOCATE", relation_sentence="A dog is near the tree.")
    result = builder.build_inventory(approved([row]), [])
    drifted = deepcopy(result)
    drifted["scene_rows"][0]["semantic_scene_core"]["semantic_identity"] = "FORBIDDEN"
    drifted["scene_rows"][0]["semantic_scene_signature_v2"] = builder.digest(drifted["scene_rows"][0]["semantic_scene_core"])
    unsigned = deepcopy(drifted); unsigned.pop("inventory_sha256", None); drifted["inventory_sha256"] = builder.digest(unsigned)
    try:
        validator.validate(drifted)
    except validator.InventoryValidationError as exc:
        assert "source_identity_leaked_into_semantic_core" in str(exc)
    else:
        raise AssertionError("validator accepted source identity in semantic scene core")
