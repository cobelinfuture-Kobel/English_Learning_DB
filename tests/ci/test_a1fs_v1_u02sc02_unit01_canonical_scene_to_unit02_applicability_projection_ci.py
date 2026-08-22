from ulga.builders import (
    build_a1fs_v1_u02sc02_unit01_canonical_scene_to_unit02_applicability_projection
    as builder,
)
from ulga.validators import (
    validate_a1fs_v1_u02sc02_unit01_canonical_scene_to_unit02_applicability_projection
    as validator,
)


def validated_payload():
    value = builder.payload()
    report = validator.validate_payload(value)
    assert report["error_count"] == 0
    return value


def test_u02sc02_resolves_exact_current_32_scene_world_not_only_31_unit01_bindable():
    value = validated_payload()
    scenes = value["scene_rows"]
    assert len(scenes) == 32
    assert sum(row["source"] == "CANONICAL_CONTEXT" for row in scenes) == 5
    assert sum(row["source"] == "MODEL_AUTHORED_APPROVED_SCENE" for row in scenes) == 27

    by_ref = {row["scene_ref_id"]: row for row in scenes}
    assert by_ref["U01-MA-FOOD-04"]["unit01_runtime_bindable"] is False
    assert by_ref["U01-MA-FOOD-04"]["anchors"] == []
    assert sorted(
        ref for ref, row in by_ref.items() if not row["unit01_runtime_bindable"]
    ) == ["U01-MA-FOOD-04"]


def test_u02sc02_accepts_current_canonical_resolver_alias_and_normalizes_projection_source():
    original = builder.u01_scene_resolver.tolerant_scene_semantic_index

    def current_alias_index():
        rows = original()
        for row in rows.values():
            if row.get("source") == "CANONICAL_CONTEXT":
                row["source"] = "CANONICAL_UNIT01_CONTEXT"
        return rows

    builder.u01_scene_resolver.tolerant_scene_semantic_index = current_alias_index
    try:
        scenes = builder.canonical_scene_rows()
    finally:
        builder.u01_scene_resolver.tolerant_scene_semantic_index = original

    assert len(scenes) == 32
    assert sum(row["source"] == "CANONICAL_CONTEXT" for row in scenes) == 5
    assert sum(row["source"] == "MODEL_AUTHORED_APPROVED_SCENE" for row in scenes) == 27


def test_u02sc02_accepts_current_model_resolver_alias_and_normalizes_projection_source():
    original = builder.u01_scene_resolver.tolerant_scene_semantic_index

    def current_alias_index():
        rows = original()
        for row in rows.values():
            if row.get("source") in {
                "MODEL_AUTHORED_APPROVED_SCENE",
                "MODEL_AUTHORED_SCENE_ENRICHMENT",
            }:
                row["source"] = "MODEL_AUTHORED_SCENE_ENRICHMENT"
        return rows

    builder.u01_scene_resolver.tolerant_scene_semantic_index = current_alias_index
    try:
        scenes = builder.canonical_scene_rows()
    finally:
        builder.u01_scene_resolver.tolerant_scene_semantic_index = original

    assert len(scenes) == 32
    assert sum(row["source"] == "CANONICAL_CONTEXT" for row in scenes) == 5
    assert sum(row["source"] == "MODEL_AUTHORED_APPROVED_SCENE" for row in scenes) == 27


def test_u02sc02_materializes_complete_32_by_162_read_only_relation_space():
    value = validated_payload()
    relations = value["relations"]
    assert len(relations) == 32 * 162 == 5184
    assert len(
        {(row["scene_ref_id"], row["singular"]) for row in relations}
    ) == 5184
    assert set(row["classification"] for row in relations) <= set(
        builder.CLASSIFICATIONS
    )


def test_u02sc02_distinguishes_direct_reprojection_and_true_scene_gap():
    rows = {
        row["singular"]: row for row in validated_payload()["vocabulary_summary"]
    }

    assert rows["book"]["direct_scene_refs"]
    assert rows["book"]["genuine_missing_new_unit02_scene_need"] is False

    assert rows["ice cream"]["reprojection_scene_refs"]
    assert rows["ice cream"]["genuine_missing_new_unit02_scene_need"] is False

    assert rows["train"]["direct_scene_refs"] == []
    assert rows["train"]["reprojection_scene_refs"] == []
    assert rows["train"]["genuine_missing_new_unit02_scene_need"] is True


def test_u02sc02_family_compatibility_alone_does_not_claim_scene_reuse():
    rows = {
        row["singular"]: row for row in validated_payload()["vocabulary_summary"]
    }
    chair = rows["chair"]
    assert chair["family_compatible_scene_refs"]
    assert chair["semantic_reuse_scene_refs"] == []
    assert chair["genuine_missing_new_unit02_scene_need"] is True


def test_u02sc02_respects_u02sc01_non_direct_scene_gates_without_false_gap_claims():
    rows = {
        row["singular"]: row for row in validated_payload()["vocabulary_summary"]
    }

    assert rows["beer"]["scene_gate"] == "PEDAGOGICAL_DEFER"
    assert rows["beer"]["semantic_reuse_scene_refs"] == []
    assert rows["beer"]["genuine_missing_new_unit02_scene_need"] is False

    assert rows["answer"]["scene_gate"] == "SUPPORT_ONLY"
    assert rows["answer"]["genuine_missing_new_unit02_scene_need"] is False

    assert rows["ice cream"]["scene_gate"] == "SENSE_CHECK_REQUIRED"
    assert rows["ice cream"]["genuine_missing_new_unit02_scene_need"] is False


def test_u02sc02_preserves_authority_and_does_not_author_new_scenes():
    value = validated_payload()
    assert value["source_authority"]["unit01_cumulative_scene_count"] == 32
    assert value["source_authority"]["unit01_runtime_bindable_scene_count"] == 31
    assert value["source_authority"]["unit01_deferred_scene_refs"] == [
        "U01-MA-FOOD-04"
    ]
    assert value["source_authority"]["unit01_canonical_resolver_source_aliases"] == [
        "CANONICAL_CONTEXT",
        "CANONICAL_UNIT01_CONTEXT",
    ]
    assert value["source_authority"]["unit01_model_resolver_source_aliases"] == [
        "MODEL_AUTHORED_APPROVED_SCENE",
        "MODEL_AUTHORED_SCENE_ENRICHMENT",
    ]
    assert value["projection_contract"][
        "u01qb14r1_resolver_is_reused_not_reimplemented"
    ] is True
    assert value["projection_contract"][
        "resolver_source_alias_is_normalized_without_scene_identity_change"
    ] is True
    assert value["projection_contract"][
        "family_compatibility_alone_does_not_claim_scene_reuse"
    ] is True
    assert value["claim_boundaries"] == {
        "canonical_scene_authority_mutated": False,
        "unit01_scene_authority_mutated": False,
        "unit02_vocabulary_authority_mutated": False,
        "new_scene_created": False,
        "questionbank_mutated": False,
        "learner_runtime_connected": False,
        "a2_unlocked": False,
    }