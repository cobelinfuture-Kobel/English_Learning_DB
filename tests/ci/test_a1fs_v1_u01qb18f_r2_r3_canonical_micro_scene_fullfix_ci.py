from __future__ import annotations

import sqlite3
from copy import deepcopy
from pathlib import Path

import pytest

from product import a1fs_v1_2_1 as product_package  # noqa: F401
from ulga.builders import _u01qb18e_micro_scene_semantic_lineage_e2e_adapter as semantic
from ulga.builders import _u01qb18f_r2_canonical_micro_scene_authority_fullfix as r2
from ulga.builders import _u01qb18f_r3_micro_scene_cross_layer_consumer_cutover_adapter as r3
from ulga.builders import build_a1fs_v1_u01qb13_unit01_twelve_form_runtime_selection_and_assessment_blueprint_integration as u13
from ulga.builders import build_a1fs_v1_u01qb14r1_unit01_cumulative_scene_world_runtime_bindability_gate_fullfix as u14r1


def test_r2_canonical_authority_restores_32_scene_world_without_new_scenes():
    report = r2.require_authority_pass()
    assert report["validation_status"] == r2.PASS_STATUS
    assert report["canonical_scene_count"] == 32
    assert report["unit01_runtime_bindable_scene_count"] == 31
    assert report["deferred_scene_refs"] == ["U01-MA-FOOD-04"]
    assert report["all_32_scenes_dereferenceable"] is True
    assert report["required_scene_core_fields_missing"] == 0
    assert report["source_lineage_missing_count"] == 0
    assert report["new_scene_authored"] is False
    assert report["questionbank_modified"] is False


def test_all_scenes_expose_full_semantic_core_provenance_and_unit_projection():
    values = r2.canonical_micro_scene_authority()
    assert len(values) == 32
    for ref, package in values.items():
        core = package["scene_core"]
        assert core["setting"]
        assert core["participants"]
        assert core["objects"]
        assert core["information_structure"]
        assert core["communicative_function_ids"]
        assert isinstance(core["actions"], list)
        assert isinstance(core["relations"], list)
        assert package["communicative_goal"]
        assert package["semantic_scene_signature_v2"]
        assert package["source_lineage"]["lineage_mode"]
        projection = package["unit_language_projection"]
        assert projection["unit_id"] == r2.UNIT_ID
        assert projection["eligible_egp_refs"]
        assert projection["eligible_pattern_refs"]
        if package["unit_runtime_bindable"]:
            assert package["anchors"], ref
            assert projection["eligible_vocabulary_refs"], ref


def test_model_scene_provenance_retains_resolved_approved_seed_refs():
    package = r2.canonical_scene_package("U01-MA-OUT-02")
    assert package["scene_origin"] == "MODEL_AUTHORED_SCENE_ENRICHMENT"
    assert package["scene_core"]["setting"] == "GARDEN"
    assert set(package["scene_core"]["objects"]) == {"CAT", "TREE"}
    assert package["scene_core"]["relations"] == ["NEAR"]
    assert package["source_lineage"]["resolved_seed_scene_ref_ids"]
    assert package["source_lineage"]["source_equivalence_claimed"] is False


def test_r3_product_cutover_makes_all_scene_consumers_use_one_resolver():
    assert r3.installed() is True
    assert u13._scene_semantic_index is r2.tolerant_scene_semantic_index
    assert u14r1.tolerant_scene_semantic_index is r2.tolerant_scene_semantic_index
    assert semantic.scene_authority is r2
    assert semantic.semantic_fidelity is r3.semantic_fidelity_with_unit_language_projection


def test_r3_language_projection_overlap_is_part_of_semantic_fidelity():
    semantics = r2.tolerant_scene_semantic_index()["U01-MA-OUT-02"]
    noun = "cat"
    pattern = semantics["unit_language_projection"]["eligible_pattern_refs"][0]
    good = {
        "stimulus": "There is a cat near a tree.",
        "prompt": "Choose the article.",
        "lexical_slots": {"noun": noun},
        "target_pattern_ids": [pattern],
    }
    value = r3.semantic_fidelity_with_unit_language_projection(
        scene_ref_id="U01-MA-OUT-02", semantics=semantics, item=good
    )
    assert value["noun_bound"] is True
    assert value["unit_language_projection_compatible"] is True
    assert pattern in value["unit_language_projection_overlap_refs"]

    bad = deepcopy(good)
    bad["target_pattern_ids"] = ["pattern:outside-unit01-scene-projection"]
    value = r3.semantic_fidelity_with_unit_language_projection(
        scene_ref_id="U01-MA-OUT-02", semantics=semantics, item=bad
    )
    assert value["unit_language_projection_compatible"] is False
    assert value["mode"] == "LANGUAGE_PROJECTION_MISMATCH"
    assert value["tier"] >= 4


def test_cross_layer_gate_fails_if_original_scene_structure_is_dropped():
    package = r2.canonical_scene_package("U01-MA-OUT-02")
    damaged = deepcopy(package)
    damaged["scene_core"]["information_structure"] = []
    errors = r3._package_errors("U01-MA-OUT-02", damaged)
    assert "SCENE_CORE_FIELD_MISSING:U01-MA-OUT-02:information_structure" in errors


def test_unknown_scene_ref_is_fail_closed_in_blueprint_gate(tmp_path: Path):
    database = tmp_path / "blueprint.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TABLE u01qb13_blueprint_activities(
                activity_id TEXT,
                form_ordinal INTEGER,
                scene_ref_id TEXT,
                skill TEXT,
                task_angle TEXT,
                support_level TEXT
            )"""
        )
        connection.execute(
            "INSERT INTO u01qb13_blueprint_activities VALUES(?,?,?,?,?,?)",
            ("A1", 1, "UNKNOWN-SCENE", "READING", "ARTICLE_CONTROL", "GUIDED"),
        )
    report = r3.validate_blueprint_database(database)
    assert report["validation_status"] == r3.FAIL_STATUS
    assert any(
        row.startswith("BLUEPRINT_SCENE_REF_NOT_DEREFERENCEABLE:A1:UNKNOWN-SCENE")
        for row in report["errors"]
    )


def test_unknown_scene_cannot_be_silently_reconstructed():
    with pytest.raises(r2.CanonicalMicroSceneAuthorityError, match="CANONICAL_SCENE_REF_UNKNOWN"):
        r2.canonical_scene_package("U01-NOT-IN-AUTHORITY")
