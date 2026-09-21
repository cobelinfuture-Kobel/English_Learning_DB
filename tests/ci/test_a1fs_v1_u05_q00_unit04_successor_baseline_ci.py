from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q00_unit04_successor_baseline.json"


def test_u05_q00_unit04_complete_package_successor_baseline() -> None:
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert data["status"] == "PASS_A1FS_V1_U05Q00_UNIT04_COMPLETE_PACKAGE_SUCCESSOR_BASELINE"
    assert data["unit_number"] == 5
    assert data["predecessor_unit_number"] == 4
    assert data["predecessor_unit_id"] == "GRAMMAR_BASIC_PREPOSITIONS_PLACE"

    scope = data["scope"]
    assert scope["unit04_package_read_complete"] is True
    assert scope["unit05_canonical_target_selected"] is False
    assert scope["unit05_new_learner_content_materialized"] is False
    assert scope["unit05_questionbank_materialized"] is False
    assert scope["unit05_forms_materialized"] is False
    assert scope["a2_a2plus_unlocked"] is False
    assert scope["no_new_design_docs"] is True

    audit = data["archive_audit"]
    assert audit["content_file_count"] == 69
    assert audit["content_files_readable"] == 69
    assert audit["content_files_failed"] == 0
    assert audit["package_content_read_complete"] is True
    assert sum(group["file_count"] for group in audit["nested_content_groups"]) == 69
    assert audit["classification_counts"] == {
        "REUSE": 18,
        "EXPAND": 5,
        "REVIEW_ONLY": 24,
        "REFERENCE_ONLY": 20,
        "BLOCKED": 0,
        "UNRESOLVED_BINDING": 2,
    }

    capabilities = data["predecessor_capabilities"]
    assert capabilities["cumulative_unit01_to_unit04"] == [
        "GRAMMAR_ARTICLES_BASIC",
        "GRAMMAR_REGULAR_PLURAL_NOUNS",
        "GRAMMAR_SUBJECT_PRONOUNS",
        "GRAMMAR_BASIC_PREPOSITIONS_PLACE",
    ]
    assert capabilities["unit04_target_kps"] == ["KP023", "KP024", "KP025"]
    assert capabilities["unit04_static_place_relation_count"] == 8
    assert set(capabilities["deferred_a1_directional_surfaces"]) == {"from", "into", "to"}
    assert set(capabilities["yle_safe_support_surfaces"]) == {"next to", "in front of"}

    denominator = data["exact_predecessor_denominator"]
    assert denominator["cumulative_sentence_assets"] == 26610
    assert denominator["unit04_new_sentence_assets"] == 96
    assert denominator["unit04_target_sentence_assets"] == 64
    assert denominator["unit04_support_sentence_assets"] == 32
    assert denominator["cumulative_chunk_surfaces"] == 90
    assert denominator["unit04_material_chunk_surfaces"] == 45
    assert denominator["unit04_new_chunk_surfaces"] == 40
    assert denominator["cumulative_exact_sentence_frames"] == 23
    assert denominator["unit04_new_exact_frames"] == 8
    assert denominator["cumulative_core_pattern_families"] == 7
    assert denominator["unit04_local_scene_bindings"] == 96
    assert denominator["governed_scene_family_count"] == 17
    assert denominator["unit04_distinct_event_variant_count"] == 48
    assert denominator["unit04_distinct_setting_count"] == 21

    readers = data["reader360_denominator"]
    assert readers["current360"]["entry_count"] == 360
    assert readers["current360"]["life_domain_count"] == 12
    assert readers["current360"]["micro_scene_count"] == 36
    assert readers["spoken360"]["entry_count"] == 360
    assert readers["spoken360"]["min_turns_per_entry"] == 5
    assert readers["spoken360"]["max_turns_per_entry"] == 6
    assert readers["pattern360"]["entry_count"] == 360
    assert readers["pattern360"]["families_per_entry"] == 7
    assert readers["pattern360"]["family_bundle_count"] == 2520

    ket = readers["current_ket_constraint_projection"]
    assert ket["capability_rows"] == 13
    assert ket["covered"] == 8
    assert ket["missing"] == 0
    assert ket["later_unit"] == 5
    assert ket["reader360_sufficient_for_current_unit04_constraint_layer"] is True

    binding = data["binding_state"]
    assert binding["grammar_refs_bound"] == 360
    assert binding["vocab_refs_bound"] == 360
    assert binding["route_refs_bound"] == 360
    assert binding["chunk_refs_bound"] == 182
    assert binding["episodes_without_chunk_refs"] == 178
    assert binding["sentence_refs_bound"] == 1
    assert binding["scene_refs_bound"] == 1
    assert binding["episodes_without_exact_q06_sentence_refs"] == 359
    assert binding["episodes_without_exact_q07_scene_refs"] == 359
    assert binding["unit01_03_asset_backfill"] == "DEFERRED"

    gap = data["gap_preparation"]
    assert gap["unit05_real_gap_computable"] is False
    assert gap["reason"] == "UNIT05_CANONICAL_GRAMMAR_TARGET_NOT_YET_SELECTED"
    assert gap["next_short_step"] == "A1FS-V1-U05Q01_Unit05CanonicalTargetAndGapProjection"

    acceptance = data["acceptance"]
    assert acceptance["package_content_files"] == "69/69"
    assert acceptance["predecessor_denominator_materialized"] is True
    assert acceptance["unit05_content_not_started"] is True
