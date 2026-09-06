import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Q03 = ROOT / "ulga/contracts/a1fs_v1_u04_q03_place_relation_form_meaning_authority.json"
Q06 = ROOT / "ulga/contracts/a1fs_v1_u04_q06_sentence_assets.json"
Q07 = ROOT / "ulga/contracts/a1fs_v1_u04_q07_life_skill_micro_scenes.json"
Q08 = ROOT / "ulga/contracts/a1fs_v1_u04_q08_communicative_function_authority.json"
REUSABLE = ROOT / "ulga/contracts/a1fs_v1_reusable_unit_production_contract.json"

EXPECTED_FUNCTION_IDS = {
    "U04-CF01_STATE_ENTITY_LOCATION",
    "U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION",
    "U04-CF03_IDENTIFY_ENTITY_BY_LOCATION",
    "U04-CF04_CONFIRM_LOCATION_RELATION",
    "U04-CF05_DESCRIBE_SPATIAL_SCENE",
    "U04-CF06_DISTINGUISH_SPATIAL_RELATION",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_u04_q08_is_exact_communicative_function_authority_slot():
    q08 = load(Q08)
    reusable = load(REUSABLE)

    q08_slot = next(row for row in reusable["authority_pipeline"]["required_slots"] if row["q"] == "Q08")
    assert q08_slot["role"] == "COMMUNICATIVE_FUNCTION_AUTHORITY"
    assert q08["task_id"] == "A1FS-V1-U04Q08_Unit04CommunicativeFunctionAuthority"
    assert q08["authority_role"] == "Q08_COMMUNICATIVE_FUNCTION_AUTHORITY"
    assert q08["status"] == "PASS_Q08_UNIT04_COMMUNICATIVE_FUNCTION_AUTHORITY"
    assert q08["acceptance"]["status"] == q08["status"]


def test_u04_q08_function_inventory_is_unique_and_bounded():
    q08 = load(Q08)
    functions = q08["communicative_functions"]
    ids = [row["function_id"] for row in functions]

    assert len(functions) == 6
    assert len(ids) == len(set(ids)) == 6
    assert set(ids) == EXPECTED_FUNCTION_IDS
    assert q08["coverage"]["communicative_function_count"] == 6
    assert q08["acceptance"]["communicative_function_authority"] == "6/6"

    skills = {skill for row in functions for skill in row["skill_compatibility"]}
    assert skills == {"READING", "WRITING", "LISTENING", "SPEAKING"}
    assert all(row["creates_new_grammar_authority"] is False for row in functions)
    assert all(row["accepted_scene_or_reuse_pair_required"] is True for row in functions)


def test_u04_q08_covers_exact_q03_targets_without_promoting_support_relations():
    q03 = load(Q03)
    q08 = load(Q08)

    q03_targets = {row["surface"] for row in q03["relations"]}
    q08_targets = set(q08["scope"]["q03_target_relations"])
    support = set(q08["scope"]["q07_support_relations"])

    assert q03_targets == q08_targets == {
        "in",
        "inside",
        "on",
        "near",
        "at",
        "under",
        "behind",
        "between",
    }
    assert support == {"next to", "in front of"}
    assert support.isdisjoint(q08_targets)
    assert q08["relation_function_compatibility"]["YLE_SUPPORT_RELATION"]["does_not_promote_support_relation_to_q03_target"] is True
    assert q08["acceptance"]["q03_target_relation_function_coverage"] == "8/8"
    assert q08["acceptance"]["support_relation_target_promotion_count"] == 0


def test_u04_q08_all_96_q07_scenes_have_function_coverage():
    q07 = load(Q07)
    q08 = load(Q08)
    scenes = q07["micro_scenes"]
    matrix = q08["relation_function_compatibility"]
    target_relations = set(matrix["Q03_TARGET_RELATION"]["relations"])
    support_relations = set(matrix["YLE_SUPPORT_RELATION"]["relations"])

    assert len(scenes) == 96
    assert q07["acceptance"]["q06_sentence_bindings"] == "96/96"

    covered = 0
    for scene in scenes:
        relation = scene["relation_surface"]
        if scene["generation_role"] == "TARGET_RELATION":
            assert relation in target_relations
            function_ids = set(matrix["Q03_TARGET_RELATION"]["function_ids"])
        else:
            assert relation in support_relations
            function_ids = set(matrix["YLE_SUPPORT_RELATION"]["function_ids"])
        assert function_ids == EXPECTED_FUNCTION_IDS
        assert scene["answerability_guard"]["scene_binds_truth_of_bound_sentence"] is True
        covered += 1

    assert covered == 96
    assert q08["coverage"]["q07_new_scene_count"] == 96
    assert q08["coverage"]["q07_new_scene_function_coverage"] == "96/96"
    assert q08["acceptance"]["q07_new_scene_function_coverage"] == "96/96"


def test_u04_q08_preserves_q06_q07_sentence_scene_semantics():
    q06 = load(Q06)
    q07 = load(Q07)
    q08 = load(Q08)
    q06_by_id = {row["sentence_id"]: row for row in q06["assets"]}

    for scene in q07["micro_scenes"]:
        source = q06_by_id[scene["bound_sentence_id"]]
        assert scene["bound_sentence_text"] == source["text"]
        assert scene["located_entity_surface"] == source["subject_np_surface"]
        assert scene["located_entity_lemma"] == source["subject_lemma"]
        assert scene["relation_surface"] == source["relation_surface"]
        assert scene["relation_id"] == source["relation_id"]
        assert scene["generation_role"] == source["generation_role"]
        assert scene["place_chunk_surface"] == source["place_chunk_surface"]

    assert q08["scene_binding_acceptance"]["q07_scene_semantics_may_be_rewritten_by_q08"] is False
    assert q08["scene_binding_acceptance"]["q06_sentence_semantics_may_be_rewritten_by_q08"] is False
    assert q08["q08_boundaries"]["q07_scene_semantics_modified"] is False
    assert q08["q08_boundaries"]["q06_sentence_semantics_modified"] is False


def test_u04_q08_reuse_only_relations_fail_closed_without_fabricated_scene_refs():
    q07 = load(Q07)
    q08 = load(Q08)

    reuse = set(q08["scope"]["reuse_only_target_relations"])
    assert reuse == {"in", "near", "on", "at"}
    assert set(q07["prior_relation_scene_reuse"]["relations"]) == reuse
    assert q07["prior_relation_scene_reuse"]["fabricated_prior_scene_ref_count"] == 0
    assert q08["function_realization_policy"]["reuse_only_relations_require_a_valid_existing_sentence_scene_pair"] is True
    assert q08["function_realization_policy"]["unresolved_reuse_pair_fails_closed"] is True


def test_u04_q08_keeps_overlap_and_between_guards_authoritative():
    q07 = load(Q07)
    q08 = load(Q08)

    guards = q08["semantic_overlap_guards"]
    assert set(guards) == {"in_inside", "at_in", "near_overlay", "next_to_near", "between"}
    assert q08["scene_binding_acceptance"]["q07_answerability_guards_remain_authoritative"] is True
    assert q08["scene_binding_acceptance"]["q03_overlap_guards_remain_authoritative"] is True
    assert q08["scene_binding_acceptance"]["between_requires_exactly_two_distinct_landmarks"] is True

    for scene in q07["micro_scenes"]:
        if scene["relation_surface"] == "between":
            assert len(scene["reference_landmarks"]) == 2
            assert scene["reference_landmarks"][0] != scene["reference_landmarks"][1]
        assert scene["answerability_guard"]["overlap_sensitive_relation_selection_requires_downstream_unique_cue"] is True


def test_u04_q08_does_not_materialize_q09_q10_or_unlock_later_scope():
    q08 = load(Q08)
    policy = q08["function_realization_policy"]
    boundaries = q08["q08_boundaries"]

    assert policy["communicative_function_ids_are_semantic_intent_authority_only"] is True
    assert policy["learner_visible_prompt_or_utterance_templates_materialized_by_q08"] is False
    assert policy["new_question_grammar_authorized_by_q08"] is False
    assert policy["new_sentence_pattern_family_authorized_by_q08"] is False
    assert policy["new_vocabulary_identity_authorized_by_q08"] is False
    assert policy["new_scene_identity_authorized_by_q08"] is False

    assert boundaries == {
        "q07_scene_semantics_modified": False,
        "q06_sentence_semantics_modified": False,
        "learner_visible_prompts_materialized": False,
        "task_families_materialized": False,
        "questionbank_materialized": False,
        "forms_materialized": False,
        "directional_from_into_to_activated": False,
        "a2_unlocked": False,
    }
    assert q08["scope"]["motion_directional_relations_activated"] is False
    assert q08["scope"]["a2_unlocked"] is False
    assert q08["next_short_step"] == "A1FS-V1-U04Q09_Unit04TaskAndPedagogicalContract"
