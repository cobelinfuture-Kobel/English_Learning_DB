from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q05_core_sentence_frame_authority.json"
Q03 = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q03_can_form_meaning_boundary_authority.json"
Q04R1 = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q04r1_yle_can_ability_chunk_expansion.json"
U05Q05 = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q05_core_sentence_frame_authority.json"
PATTERNS = ROOT / "ulga" / "graph" / "sentence_patterns.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_u06_q05_core_sentence_frame_authority() -> None:
    data = _load(ARTIFACT)
    q03 = _load(Q03)
    q04r1 = _load(Q04R1)
    u05 = _load(U05Q05)
    patterns = _load(PATTERNS)

    assert data["status"] == "PASS_A1FS_V1_U06Q05_UNIT06_CORE_SENTENCE_FRAME_AUTHORITY"
    assert data["unit_number"] == 6
    assert data["unit_id"] == "GRAMMAR_CAN_STATEMENT"
    assert data["source_main_sha"] == "da994c5b094db9e9bfb06012608d8b0350352a98"

    assert q03["status"] == "PASS_A1FS_V1_U06Q03_CAN_FORM_MEANING_BOUNDARY_AUTHORITY"
    assert q04r1["status"] == "PASS_A1FS_V1_U06Q04R1_YLE_PREA1_A1_CAN_ABILITY_EXPANSION"
    assert u05["status"] == "PASS_A1FS_V1_U05Q05_UNIT05_CORE_SENTENCE_FRAME_AUTHORITY"

    binding = data["global_pattern_authority_binding"]
    assert binding["source_record_id"] == "SP_000006"
    assert binding["pattern_node_id"] == "pattern:PATTERN_NODE_000006"
    assert binding["canonical_pattern"] == "I can {verb_stem}."
    assert binding["pattern_family_id"] == "family:ability_can"
    assert binding["cefr_level"] == "A1"
    assert binding["review_status"] == "accepted"
    assert binding["new_global_pattern_identity_created"] is False

    sp = next(row for row in patterns if row["authority_source"]["source_record_id"] == "SP_000006")
    assert sp["metadata"]["canonical_pattern"] == "I can {verb_stem}."
    assert sp["metadata"]["pattern_family_id"] == "family:ability_can"
    assert sp["metadata"]["pattern_type"] == "ability_statement"
    assert sp["metadata"]["generator_allowed"] is True
    assert sp["metadata"]["review_status"] == "accepted"

    lexical = data["lexical_slot_policy"]
    assert lexical["q04r1_subject_can_surface_count"] == 7
    assert lexical["q04r1_can_base_verb_surface_count"] == 62
    assert lexical["q04r1_non_scene_functional_surface_count"] == 41
    assert lexical["q04r1_course_cumulative_chunk_surface_count"] == 266
    assert lexical["contextual_ability_only_entries_direct_generation_allowed"] is False
    assert lexical["deferred_canonical_bridge_entries_direct_generation_allowed"] is False
    assert lexical["exact_semantic_sense_binding_required_before_q06_sentence_admission"] is True
    assert lexical["yle_a1_lexical_bridge_exception"]["a2_grammar_unlocked"] is False

    frames = {row["frame_id"]: row for row in data["unit06_operational_frames"]}
    assert set(frames) == {
        "U06-CF-ABILITY-INTRANSITIVE",
        "U06-CF-ABILITY-OBJECT",
        "U06-CF-ABILITY-PREDICATE-TAIL",
    }
    assert frames["U06-CF-ABILITY-INTRANSITIVE"]["template"] == "{SUBJECT} can {BASE_VERB}."
    assert frames["U06-CF-ABILITY-OBJECT"]["template"] == "{SUBJECT} can {BASE_VERB} {OBJECT}."
    assert frames["U06-CF-ABILITY-PREDICATE-TAIL"]["template"] == "{SUBJECT} can {APPROVED_ABILITY_PREDICATE_TAIL}."
    assert {row["q03_rule_primitive_id"] for row in frames.values()} == {
        "CAN_AFFIRMATIVE_INTRANSITIVE_ABILITY_CORE",
        "CAN_AFFIRMATIVE_TRANSITIVE_ABILITY_OBJECT",
        "CAN_AFFIRMATIVE_ACTIVITY_COMPLEMENT",
    }
    assert all(row["canonical_family_lineage"] == "family:ability_can" for row in frames.values())
    assert all(row["direct_generation_allowed"] is True for row in frames.values())
    assert all(row["ability_context_required"] is True for row in frames.values())

    subj = data["subject_resolution"]
    assert subj["allowed_subject_classes"][:7] == ["I", "you", "he", "she", "it", "we", "they"]
    assert subj["can_invariant_across_subjects"] is True
    assert subj["third_person_s_on_can_or_lexical_verb_allowed"] is False

    constraints = data["frame_family_constraints"]
    assert constraints["clause_type"] == "DECLARATIVE_STATEMENT_ONLY"
    assert constraints["polarity"] == "AFFIRMATIVE_ONLY"
    assert constraints["meaning"] == "ABILITY_OR_CAPABILITY"
    assert constraints["lexical_verb_form"] == "BASE_FORM"
    assert set(constraints["blocked_direct_target_forms"]) == {
        "CAN_QUESTION", "CAN_NEGATIVE", "CAN_AS_NOUN"
    }
    assert set(constraints["blocked_direct_target_readings"]) == {
        "PERMISSION", "OFFER", "REQUEST", "POSSIBILITY"
    }

    proj = data["q04r1_functional_projection"]
    assert proj["source_functional_surface_count"] == 41
    assert proj["q05_promoted_functional_chunk_identity_count"] == 0
    assert proj["q05_frame_projection_count"] == 1
    assert proj["q07_native_scene_functional_candidates_available"] is False
    assert proj["q07_backfill_still_required"] is True

    counts = data["frame_dedup_and_counts"]
    assert counts == {
        "prior_exact_frames": 29,
        "new_exact_operational_frames": 3,
        "within_new_exact_template_duplicate_count": 0,
        "exact_template_overlap_with_prior_29": 0,
        "cumulative_exact_frames": 32,
        "prior_cumulative_course_pattern_families": 8,
        "newly_unlocked_existing_global_pattern_families": 1,
        "newly_unlocked_existing_global_pattern_family_ids": ["family:ability_can"],
        "cumulative_course_pattern_families": 9,
        "new_global_pattern_identities": 0,
    }

    route = data["q06_primary_generation_routing"]
    assert route["frame_ids"] == [
        "U06-CF-ABILITY-INTRANSITIVE",
        "U06-CF-ABILITY-OBJECT",
        "U06-CF-ABILITY-PREDICATE-TAIL",
    ]
    assert route["predecessor_sentence_pool_for_dedup"] == 27371
    assert route["exact_and_normalized_sentence_dedup_required"] is True
    assert route["semantic_pedagogical_admission_required"] is True
    assert route["can_question_target_sentence_allowed"] is False
    assert route["can_negative_target_sentence_allowed"] is False
    assert route["non_ability_can_target_sentence_allowed"] is False

    boundaries = data["q05_boundaries"]
    assert boundaries["sentence_assets_materialized"] is False
    assert boundaries["scenes_materialized"] is False
    assert boundaries["global_sentence_pattern_authority_mutated"] is False
    assert boundaries["q07_scene_functional_backfill_materialized"] is False
    assert boundaries["a2_a2plus_grammar_unlocked"] is False

    acc = data["acceptance"]
    assert acc["prior_exact_frame_count"] == 29
    assert acc["new_exact_operational_frame_count"] == 3
    assert acc["cumulative_exact_frame_count"] == 32
    assert acc["q03_seed_family_count"] == "3/3"
    assert acc["q04r1_subject_can_chunks"] == "7/7"
    assert acc["q04r1_can_base_verb_chunks"] == 62
    assert acc["q04r1_non_scene_functional_chunks"] == 41
    assert acc["cumulative_course_pattern_family_count"] == 9
    assert acc["new_global_pattern_identity_count"] == 0
    assert acc["question_or_negative_target_frame_count"] == 0
    assert acc["non_ability_target_frame_count"] == 0
    assert acc["a2_grammar_unlocked"] is False

    assert data["next_short_step"] == "A1FS-V1-U06Q06_Unit06SentenceAssetProductionAndSemanticAdmission"
