import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REUSABLE = ROOT / "ulga/contracts/a1fs_v1_reusable_unit_production_contract.json"
Q03 = ROOT / "ulga/contracts/a1fs_v1_u04_q03_place_relation_form_meaning_authority.json"
Q06 = ROOT / "ulga/contracts/a1fs_v1_u04_q06_sentence_assets.json"
Q07 = ROOT / "ulga/contracts/a1fs_v1_u04_q07_life_skill_micro_scenes.json"
Q08 = ROOT / "ulga/contracts/a1fs_v1_u04_q08_communicative_function_authority.json"
Q09 = ROOT / "ulga/contracts/a1fs_v1_u04_q09_task_pedagogical_contract.json"

EXPECTED_TASK_FAMILIES = {
    "RECOGNITION",
    "MEANING_DISCRIMINATION",
    "FORM_SELECTION",
    "PLACE_PHRASE_CONSTRUCTION",
    "ERROR_DETECTION",
    "ERROR_CORRECTION",
    "CONTEXT_GAP",
    "U01_U02_U03_INTEGRATION",
    "PRODUCTIVE_RESPONSE",
    "TRANSFER",
}
EXPECTED_PROGRESSIONS = {"GUIDED", "REDUCED_SUPPORT", "INDEPENDENT", "TRANSFER", "RETENTION"}
EXPECTED_FUNCTION_IDS = {
    "U04-CF01_STATE_ENTITY_LOCATION",
    "U04-CF02_REQUEST_ENTITY_LOCATION_INFORMATION",
    "U04-CF03_IDENTIFY_ENTITY_BY_LOCATION",
    "U04-CF04_CONFIRM_LOCATION_RELATION",
    "U04-CF05_DESCRIBE_SPATIAL_SCENE",
    "U04-CF06_DISTINGUISH_SPATIAL_RELATION",
}
EXPECTED_TARGET_RELATIONS = {"in", "inside", "on", "near", "at", "under", "behind", "between"}
EXPECTED_SUPPORT_RELATIONS = {"next to", "in front of"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_u04_q09_is_exact_task_and_pedagogical_contract_slot():
    reusable = load(REUSABLE)
    q09 = load(Q09)
    slot = next(row for row in reusable["authority_pipeline"]["required_slots"] if row["q"] == "Q09")

    assert slot["role"] == "TASK_AND_PEDAGOGICAL_CONTRACT"
    assert q09["task_id"] == "A1FS-V1-U04Q09_Unit04TaskAndPedagogicalContract"
    assert q09["authority_role"] == "Q09_TASK_AND_PEDAGOGICAL_CONTRACT"
    assert q09["status"] == "PASS_Q09_UNIT04_TASK_AND_PEDAGOGICAL_CONTRACT"
    assert q09["acceptance"]["status"] == q09["status"]


def test_u04_q09_has_exact_unique_ten_family_inventory():
    q09 = load(Q09)
    families = q09["task_families"]
    ids = [row["task_family_id"] for row in families]
    names = [row["family_name"] for row in families]

    assert len(families) == 10
    assert len(ids) == len(set(ids)) == 10
    assert set(names) == EXPECTED_TASK_FAMILIES
    assert len(names) == len(set(names)) == 10
    assert all(row["creates_new_grammar_authority"] is False for row in families)
    assert q09["acceptance"]["task_family_count"] == 10
    assert q09["acceptance"]["task_family_unique_id_count"] == 10


def test_u04_q09_uses_only_q08_functions_and_covers_all_six():
    q08 = load(Q08)
    q09 = load(Q09)
    q08_ids = {row["function_id"] for row in q08["communicative_functions"]}
    used = {fid for row in q09["task_families"] for fid in row["allowed_function_ids"]}

    assert q08_ids == EXPECTED_FUNCTION_IDS
    assert set(q09["scope"]["q08_communicative_function_ids"]) == EXPECTED_FUNCTION_IDS
    assert used == EXPECTED_FUNCTION_IDS
    assert q09["acceptance"]["q08_communicative_function_task_coverage"] == "6/6"

    for row in q09["task_families"]:
        assert set(row["allowed_function_ids"]).issubset(q08_ids)


def test_u04_q09_covers_exact_target_relations_without_promoting_support():
    q03 = load(Q03)
    q08 = load(Q08)
    q09 = load(Q09)

    q03_targets = {row["surface"] for row in q03["relations"]}
    assert q03_targets == EXPECTED_TARGET_RELATIONS
    assert set(q09["scope"]["q03_target_relations"]) == EXPECTED_TARGET_RELATIONS
    assert set(q09["relation_evidence_contract"]["target_relations_count_as_unit04_target_evidence"]) == EXPECTED_TARGET_RELATIONS
    assert set(q09["scope"]["q07_support_relations"]) == EXPECTED_SUPPORT_RELATIONS
    assert set(q09["relation_evidence_contract"]["support_relations"]) == EXPECTED_SUPPORT_RELATIONS
    assert set(q08["scope"]["q07_support_relations"]) == EXPECTED_SUPPORT_RELATIONS
    assert q09["relation_evidence_contract"]["support_relations_count_as_q03_target_evidence"] is False
    assert q09["acceptance"]["support_relation_target_promotion_count"] == 0
    assert q09["acceptance"]["q03_target_relation_task_contract_coverage"] == "8/8"


def test_u04_q09_single_answer_capable_families_fail_closed_on_ambiguity():
    q09 = load(Q09)
    guards = q09["answerability_and_distractor_contract"]

    for family in q09["task_families"]:
        if family["single_answer_possible"]:
            assert family["single_answer_unique_cue_required"] is True

    assert guards["single_answer_item_requires_exactly_one_truthfully_licensed_answer"] is True
    assert guards["multiple_valid_answer_count_required"] == 0
    assert guards["duplicate_or_semantically_equivalent_option_count_required"] == 0
    assert guards["lexical_surface_presence_alone_is_not_unique_spatial_evidence"] is True
    assert guards["in_inside_may_not_be_forced_as_mutually_exclusive_without_unique_cue"] is True
    assert guards["at_in_may_not_be_forced_as_mutually_exclusive_when_both_viewpoints_are_natural"] is True
    assert guards["near_may_not_compete_in_single_answer_item_when_co_true_without_unique_cue"] is True
    assert guards["next_to_near_may_not_be_forced_as_unique_contrast_without_unique_cue"] is True
    assert guards["multiple_true_relation_scene_policy"] == "USE_OPEN_RESPONSE_OR_RECAST_WITH_EXPLICIT_UNIQUE_CUE; DO_NOT_FORCE_SINGLE_ANSWER"


def test_u04_q09_between_and_q07_scene_truth_guards_remain_exact():
    q07 = load(Q07)
    q09 = load(Q09)

    assert len(q07["micro_scenes"]) == 96
    assert q07["acceptance"]["q06_sentence_bindings"] == "96/96"
    assert q09["answerability_and_distractor_contract"]["between_requires_exactly_two_distinct_reference_landmarks"] is True
    assert q09["relation_evidence_contract"]["q07_new_sentence_scene_bindings_must_be_preserved_exactly"] is True

    for scene in q07["micro_scenes"]:
        assert scene["answerability_guard"]["scene_binds_truth_of_bound_sentence"] is True
        if scene["relation_surface"] == "between":
            assert len(scene["reference_landmarks"]) == 2
            assert scene["reference_landmarks"][0] != scene["reference_landmarks"][1]


def test_u04_q09_preserves_all_96_q06_q07_semantic_bindings():
    q06 = load(Q06)
    q07 = load(Q07)
    q09 = load(Q09)
    q06_by_id = {row["sentence_id"]: row for row in q06["assets"]}

    assert len(q06_by_id) == 96
    assert len(q07["micro_scenes"]) == 96

    for scene in q07["micro_scenes"]:
        source = q06_by_id[scene["bound_sentence_id"]]
        assert scene["bound_sentence_text"] == source["text"]
        assert scene["located_entity_surface"] == source["subject_np_surface"]
        assert scene["located_entity_lemma"] == source["subject_lemma"]
        assert scene["relation_surface"] == source["relation_surface"]
        assert scene["relation_id"] == source["relation_id"]
        assert scene["generation_role"] == source["generation_role"]
        assert scene["place_chunk_surface"] == source["place_chunk_surface"]

    boundaries = q09["q09_boundaries"]
    assert boundaries["q06_sentence_semantics_modified"] is False
    assert boundaries["q07_scene_semantics_modified"] is False
    assert boundaries["q08_communicative_function_semantics_modified"] is False


def test_u04_q09_inherits_exact_five_progression_roles_and_bounded_sections():
    reusable = load(REUSABLE)
    q09 = load(Q09)

    inherited = set(reusable["common_contract"]["reading_writing"]["form_architecture"]["required_progression_roles"])
    actual = {row["progression_role"] for row in q09["progression_contract"]}
    assert inherited == actual == EXPECTED_PROGRESSIONS
    assert len(q09["progression_contract"]) == 5

    sections = q09["section_architecture"]
    assert [row["section_id"] for row in sections] == ["A", "B", "C", "D", "E"]
    assert len(sections) == 5
    all_family_ids = {row["task_family_id"] for row in q09["task_families"]}
    referenced_family_ids = {fid for row in sections for fid in row["allowed_task_family_ids"]}
    assert referenced_family_ids == all_family_ids
    assert q09["acceptance"]["section_role_count"] == 5
    assert q09["acceptance"]["progression_role_count"] == 5


def test_u04_q09_cross_unit_integration_keeps_unit04_as_target():
    q09 = load(Q09)
    integration = q09["cross_unit_integration_contract"]
    family = next(row for row in q09["task_families"] if row["family_name"] == "U01_U02_U03_INTEGRATION")

    assert integration["allowed_prior_units"] == [
        "UNIT01_ARTICLES",
        "UNIT02_REGULAR_PLURALS",
        "UNIT03_SUBJECT_PRONOUNS_AND_REFERENCE",
    ]
    assert integration["prior_unit_grammar_role"] == "PREREQUISITE_OR_CONTEXT_CARRIER"
    assert integration["prior_unit_content_alone_counts_as_unit04_target_evidence"] is False
    assert integration["unit04_place_relation_must_remain_the_assessed_target"] is True
    assert integration["later_unit_grammar_may_be_introduced_for_convenience"] is False
    assert "Unit04 static place relation remains the assessed target" in family["pedagogical_role"]


def test_u04_q09_reuse_only_relations_fail_closed_without_new_scene_identity():
    q07 = load(Q07)
    q09 = load(Q09)

    reuse = set(q09["scope"]["reuse_only_target_relations"])
    assert reuse == {"in", "near", "on", "at"}
    assert set(q07["prior_relation_scene_reuse"]["relations"]) == reuse
    assert q07["prior_relation_scene_reuse"]["fabricated_prior_scene_ref_count"] == 0
    assert q09["relation_evidence_contract"]["reuse_only_target_relations_require_valid_existing_sentence_scene_pair"] is True
    assert q09["relation_evidence_contract"]["unresolved_reuse_pair_fails_closed"] is True
    assert q09["q09_boundaries"]["new_scene_identity_created"] is False


def test_u04_q09_defers_all_numeric_q10_materialization_and_later_scope():
    q09 = load(Q09)
    mat = q09["q10_materialization_requirements"]
    boundaries = q09["q09_boundaries"]
    policy = q09["task_authority_policy"]

    assert mat["form_count"] == "DEFERRED_TO_Q10_CURRENT_UNIT_MATERIALIZATION"
    assert mat["questions_per_form"] == "DEFERRED_TO_Q10_CURRENT_UNIT_MATERIALIZATION"
    assert mat["questions_per_section"] == "DEFERRED_TO_Q10_CURRENT_UNIT_MATERIALIZATION"
    assert mat["questionbank_capacity"] == "DEFERRED_TO_Q10_CURRENT_UNIT_MATERIALIZATION"
    assert mat["numeric_distribution_thresholds"] == "DEFERRED_TO_Q10_CURRENT_UNIT_MATERIALIZATION"
    assert mat["all_ten_task_families_require_nonzero_materialized_coverage"] is True
    assert mat["all_eight_q03_target_relations_require_materialized_coverage"] is True

    assert policy["learner_visible_question_items_materialized_by_q09"] is False
    assert policy["learner_visible_prompt_templates_materialized_by_q09"] is False
    assert policy["new_question_grammar_authorized_by_q09"] is False
    assert boundaries["questionbank_items_materialized"] is False
    assert boundaries["forms_materialized"] is False
    assert boundaries["q10_numeric_form_parameters_materialized"] is False
    assert boundaries["directional_from_into_to_activated"] is False
    assert boundaries["a2_unlocked"] is False
    assert q09["acceptance"]["q10_items_materialized"] == 0
    assert q09["acceptance"]["q10_forms_materialized"] == 0
    assert q09["next_short_step"] == "A1FS-V1-U04Q10_Unit04QuestionBankAndFormMaterialization"
