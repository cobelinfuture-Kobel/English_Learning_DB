from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REUSABLE = ROOT / "ulga/contracts/a1fs_v1_reusable_unit_production_contract.json"
Q06 = ROOT / "ulga/contracts/a1fs_v1_u05_q06_sentence_assets.json"
Q07 = ROOT / "ulga/contracts/a1fs_v1_u05_q07_life_skill_micro_scenes.json"
Q08 = ROOT / "ulga/contracts/a1fs_v1_u05_q08_communicative_function_authority.json"
Q09 = ROOT / "ulga/contracts/a1fs_v1_u05_q09_task_pedagogical_contract.json"

EXPECTED_TASK_FAMILIES = {
    "BE_FORM_RECOGNITION",
    "SUBJECT_BE_AGREEMENT_SELECTION",
    "COMPLEMENT_MEANING_DISCRIMINATION",
    "AFFIRMATIVE_NEGATIVE_INTERPRETATION",
    "SENTENCE_CONSTRUCTION",
    "ERROR_DETECTION_AND_CORRECTION",
    "CONTEXT_GAP",
    "U01_U04_CUMULATIVE_INTEGRATION",
    "PRODUCTIVE_RESPONSE",
    "TRANSFER",
}

EXPECTED_FUNCTION_IDS = {
    "U05-CF01_IDENTIFY_OR_CLASSIFY_ENTITY",
    "U05-CF02_DESCRIBE_ENTITY_OR_STATE",
    "U05-CF03_STATE_STATIC_LOCATION",
    "U05-CF04_DENY_OR_CORRECT_BASIC_BE_INFORMATION",
    "U05-CF05_REQUEST_BASIC_BE_INFORMATION",
    "U05-CF06_CONFIRM_BASIC_BE_INFORMATION",
    "U05-CF07_MATCH_ENTITY_OR_SCENE_TO_BE_DESCRIPTION",
}

EXPECTED_FRAMES = {
    "U05-BF-NP-AFF",
    "U05-BF-ADJ-AFF",
    "U05-BF-PLACE-AFF",
    "U05-BF-NP-NEG",
    "U05-BF-ADJ-NEG",
    "U05-BF-PLACE-NEG",
}

EXPECTED_PROGRESSIONS = {"GUIDED", "REDUCED_SUPPORT", "INDEPENDENT", "TRANSFER", "RETENTION"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_u05_q09_is_exact_task_and_pedagogical_contract_slot():
    reusable = load(REUSABLE)
    q09 = load(Q09)
    slot = next(row for row in reusable["authority_pipeline"]["required_slots"] if row["q"] == "Q09")
    assert slot["role"] == "TASK_AND_PEDAGOGICAL_CONTRACT"
    assert q09["task_id"] == "A1FS-V1-U05Q09_Unit05TaskAndPedagogicalContract"
    assert q09["authority_role"] == "Q09_TASK_AND_PEDAGOGICAL_CONTRACT"
    assert q09["status"] == "PASS_A1FS_V1_U05Q09_TASK_AND_PEDAGOGICAL_CONTRACT"
    assert q09["acceptance"]["status"] == q09["status"]


def test_u05_q09_has_exact_unique_ten_family_inventory():
    q09 = load(Q09)
    families = q09["task_families"]
    ids = [row["task_family_id"] for row in families]
    names = [row["family_name"] for row in families]
    assert len(families) == 10
    assert len(ids) == len(set(ids)) == 10
    assert len(names) == len(set(names)) == 10
    assert set(names) == EXPECTED_TASK_FAMILIES
    assert all(row["creates_new_grammar_authority"] is False for row in families)
    assert q09["acceptance"]["task_family_count"] == 10
    assert q09["acceptance"]["task_family_unique_id_count"] == 10


def test_u05_q09_uses_only_q08_functions_and_covers_all_seven():
    q08 = load(Q08)
    q09 = load(Q09)
    q08_ids = {row["function_id"] for row in q08["communicative_functions"]}
    used = {fid for row in q09["task_families"] for fid in row["allowed_function_ids"]}
    assert q08_ids == EXPECTED_FUNCTION_IDS
    assert used == EXPECTED_FUNCTION_IDS
    assert q09["acceptance"]["q08_communicative_function_task_coverage"] == "7/7"


def test_u05_q09_scope_preserves_all_six_q05_frames_and_all_nine_subject_classes():
    q06 = load(Q06)
    q09 = load(Q09)
    assert set(q09["scope"]["q05_frame_ids"]) == EXPECTED_FRAMES
    assert set(q06["coverage"]["frame_counts"]) == EXPECTED_FRAMES
    assert q09["acceptance"]["q05_frame_task_contract_coverage"] == "6/6"

    subject_classes = set(q06["coverage"]["subject_class_counts"])
    assert subject_classes == {
        "I",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "ADMITTED_SINGULAR_NOUN_PHRASE",
        "ADMITTED_PLURAL_NOUN_PHRASE",
    }
    assert q09["acceptance"]["q06_subject_class_task_contract_coverage"] == "9/9"


def test_u05_q09_preserves_q07_context_truth_and_standalone_boundary():
    q07 = load(Q07)
    q09 = load(Q09)
    assert q07["coverage"]["q06_context_required_sentence_surface_count"] == 478
    assert q07["coverage"]["q06_standalone_sentence_surface_count"] == 377
    assert q07["coverage"]["q06_unbound_context_required_sentence_count"] == 0

    policy = q09["task_authority_policy"]
    connected = q09["connected_context_contract"]
    guards = q09["answerability_and_distractor_contract"]
    assert policy["context_required_sentence_use_must_resolve_q07_scene_binding"] is True
    assert policy["standalone_q06_sentence_use_does_not_require_forced_scene_binding"] is True
    assert connected["context_required_q06_sentences_require_existing_q07_binding"] is True
    assert connected["standalone_q06_sentences_may_be_used_without_forced_scene_binding"] is True
    assert guards["context_required_items_must_reference_existing_q07_scene_or_binding"] is True
    assert guards["standalone_items_may_use_only_q06_approve_supply_without_forced_scene"] is True


def test_u05_q09_negative_and_pronoun_answerability_fail_closed():
    q09 = load(Q09)
    guards = q09["answerability_and_distractor_contract"]
    assert guards["single_answer_item_requires_exactly_one_truthfully_licensed_answer"] is True
    assert guards["multiple_valid_answer_count_required"] == 0
    assert guards["duplicate_or_semantically_equivalent_option_count_required"] == 0
    assert guards["affirmative_negative_items_must_have_explicit_truth_evidence"] is True
    assert guards["negative_scene_items_require_positive_contrast_evidence"] is True
    assert guards["absence_of_visual_evidence_is_not_proof_of_negative_be"] is True
    assert guards["context_bound_pronoun_items_require_explicit_referent_anchor"] is True

    for family in q09["task_families"]:
        if family["single_answer_possible"]:
            assert family["single_answer_unique_cue_required"] is True


def test_u05_q09_information_request_function_does_not_unlock_be_interrogative():
    q09 = load(Q09)
    cf05 = "U05-CF05_REQUEST_BASIC_BE_INFORMATION"
    carriers = [row for row in q09["task_families"] if cf05 in row["allowed_function_ids"]]
    assert {row["family_name"] for row in carriers} == {"PRODUCTIVE_RESPONSE", "TRANSFER"}
    assert all(row["existing_cumulative_question_form_required_for_cf05"] is True for row in carriers)
    assert q09["task_authority_policy"]["new_question_grammar_authorized_by_q09"] is False
    assert q09["scope"]["be_interrogative_mastery_activated"] is False
    assert q09["q09_boundaries"]["be_interrogative_mastery_activated"] is False


def test_u05_q09_has_five_sections_and_inherits_five_progression_roles():
    reusable = load(REUSABLE)
    q09 = load(Q09)
    inherited = set(reusable["common_contract"]["reading_writing"]["form_architecture"]["required_progression_roles"])
    actual = {row["progression_role"] for row in q09["progression_contract"]}
    assert inherited == actual == EXPECTED_PROGRESSIONS

    sections = q09["section_architecture"]
    assert [row["section_id"] for row in sections] == ["A", "B", "C", "D", "E"]
    family_ids = {row["task_family_id"] for row in q09["task_families"]}
    referenced = {fid for row in sections for fid in row["allowed_task_family_ids"]}
    assert referenced == family_ids
    assert q09["acceptance"]["section_role_count"] == 5
    assert q09["acceptance"]["progression_role_count"] == 5


def test_u05_q09_cross_unit_integration_keeps_unit05_as_assessed_target():
    q09 = load(Q09)
    integration = q09["cross_unit_integration_contract"]
    family = next(row for row in q09["task_families"] if row["family_name"] == "U01_U04_CUMULATIVE_INTEGRATION")
    assert integration["allowed_prior_units"] == [
        "UNIT01_ARTICLES",
        "UNIT02_REGULAR_PLURALS",
        "UNIT03_SUBJECT_PRONOUNS_AND_REFERENCE",
        "UNIT04_STATIC_PLACE_RELATIONS",
    ]
    assert integration["prior_unit_grammar_role"] == "PREREQUISITE_OR_CONTEXT_CARRIER"
    assert integration["prior_unit_content_alone_counts_as_unit05_target_evidence"] is False
    assert integration["unit05_present_be_must_remain_the_assessed_target"] is True
    assert integration["later_unit_grammar_may_be_introduced_for_convenience"] is False
    assert "Unit05 present be remains the assessed target" in family["pedagogical_role"]


def test_u05_q09_q10_requirements_cover_core_dimensions_but_defer_numbers():
    q09 = load(Q09)
    mat = q09["q10_materialization_requirements"]
    assert mat["all_ten_task_families_require_nonzero_materialized_coverage"] is True
    assert mat["all_six_q05_frames_require_materialized_coverage"] is True
    assert mat["all_seven_q08_communicative_functions_require_task_compatibility_coverage"] is True
    assert mat["all_nine_q06_subject_classes_require_materialized_coverage"] is True
    assert mat["affirmative_and_negative_polarity_require_materialized_coverage"] is True
    assert mat["np_adjective_and_place_complement_classes_require_materialized_coverage"] is True
    assert mat["full_and_contracted_surface_variants_require_coverage_without_treating_surface_variant_as_new_semantics"] is True
    assert mat["selected_response_items_must_pass_answerability_and_distractor_contract"] is True
    assert mat["q07_context_required_items_must_reference_existing_q07_scene_or_binding_ids"] is True

    for key in (
        "form_count",
        "questions_per_form",
        "questions_per_section",
        "questionbank_capacity",
        "numeric_distribution_thresholds",
    ):
        assert mat[key] == "DEFERRED_TO_Q10_CURRENT_UNIT_MATERIALIZATION"


def test_u05_q09_does_not_materialize_q10_reader360_or_later_scope():
    q09 = load(Q09)
    policy = q09["task_authority_policy"]
    b = q09["q09_boundaries"]

    assert policy["learner_visible_question_items_materialized_by_q09"] is False
    assert policy["learner_visible_prompt_templates_materialized_by_q09"] is False
    assert policy["new_question_grammar_authorized_by_q09"] is False

    for key in (
        "q06_sentence_semantics_modified",
        "q07_scene_semantics_modified",
        "q08_communicative_function_semantics_modified",
        "learner_visible_prompt_templates_materialized",
        "questionbank_items_materialized",
        "forms_materialized",
        "q10_numeric_form_parameters_materialized",
        "unit05_current360_materialized",
        "unit05_spoken360_materialized",
        "unit05_pattern360_materialized",
        "new_grammar_authority_created",
        "new_vocabulary_identity_created",
        "new_sentence_identity_created",
        "new_scene_identity_created",
        "new_communicative_function_identity_created",
        "be_interrogative_mastery_activated",
        "past_be_activated",
        "existential_there_be_activated",
        "present_continuous_mastery_activated",
        "a2_a2plus_unlocked",
    ):
        assert b[key] is False

    assert q09["acceptance"]["q10_items_materialized"] == 0
    assert q09["acceptance"]["q10_forms_materialized"] == 0
    assert q09["next_short_step"] == "A1FS-V1-U05Q10_Unit05QuestionBankAndFormMaterialization"
