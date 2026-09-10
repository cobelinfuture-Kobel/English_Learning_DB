from product.a1fs_v1_2_1 import u04formv3_direct_authoring_contract as contract


def test_u04formv3_contract_validates_locked_structure():
    report = contract.validate_contract()
    assert report["status"] == contract.STATUS
    assert report["form_count"] == 20
    assert report["questions_per_form"] == 40
    assert report["section_counts"] == {"A": 6, "B": 10, "C": 10, "D": 8, "E": 6}
    assert report["stage_form_ranges"] == {
        "GUIDED": [1, 2, 3, 4],
        "REDUCED_SUPPORT": [5, 6, 7, 8],
        "INDEPENDENT": [9, 10, 11, 12],
        "TRANSFER": [13, 14, 15, 16],
        "RETENTION": [17, 18, 19, 20],
    }


def test_u04formv3_forbids_python_learner_content_authoring():
    authoring = contract.AUTHORING_CONTRACT
    assert authoring["learner_content_author"] == "GPT-5.6_SOL_DIRECT_AUTHORING"
    assert authoring["python_may_author_learner_facing_english"] is False
    assert "prompt_composition" in authoring["python_forbidden_roles"]
    assert "stimulus_composition" in authoring["python_forbidden_roles"]
    assert "distractor_composition" in authoring["python_forbidden_roles"]
    assert "preposition_string_replacement" in authoring["python_forbidden_roles"]
    assert "wrong_sentence_synthesis" in authoring["python_forbidden_roles"]
    assert contract.PASSAGE_MUTATION_ALLOWED is False


def test_u04formv3_uses_six_coherent_current360_contexts_per_form():
    assert contract.CONTEXT_SLOTS_PER_FORM == 6
    assert contract.CONTEXT_SLOT_CONTRACT["A1"]["question_load"] == {"A": 3}
    assert contract.CONTEXT_SLOT_CONTRACT["A2"]["question_load"] == {"A": 3}
    assert contract.CONTEXT_SLOT_CONTRACT["BC1"]["question_load"] == {"B": 5, "C": 5}
    assert contract.CONTEXT_SLOT_CONTRACT["BC2"]["question_load"] == {"B": 5, "C": 5}
    assert contract.CONTEXT_SLOT_CONTRACT["DE1"]["question_load"] == {"D": 4, "E": 3}
    assert contract.CONTEXT_SLOT_CONTRACT["DE2"]["question_load"] == {"D": 4, "E": 3}
    assert contract.CROSS_FORM_EPISODE_REUSE_ALLOWED is False
    assert contract.PASSAGE_DISPLAY_POLICY == "DISPLAY_EXACT_CURRENT360_PASSAGE_ONCE_PER_SECTION_CONTEXT"


def test_u04formv3_stage_family_quotas_fill_each_section():
    for stage in contract.STAGE_ORDER:
        assert tuple(contract.STAGE_FAMILY_QUOTAS[stage]) == contract.SECTION_ORDER
        for section in contract.SECTION_ORDER:
            assert sum(contract.STAGE_FAMILY_QUOTAS[stage][section].values()) == contract.SECTION_COUNTS[section]
    assert contract.ANSWER_DIVERSITY_CONTRACT["identical_40_task_family_sequence_across_forms_allowed"] is False
    assert contract.ANSWER_DIVERSITY_CONTRACT["python_may_shuffle_answers_after_authoring"] is False


def test_u04formv3_closes_observed_semantic_failure_modes():
    quality = contract.SEMANTIC_QUALITY_CONTRACT
    assert quality["masked_duplicate_answer_leakage_allowed"] is False
    assert quality["reading_detail_answer_recoverable_from_passage_allowed"] is True
    assert quality["blank_or_reconstruction_answer_may_remain_verbatim_visible_elsewhere"] is False
    assert quality["error_correction_wrong_sentence_must_be_grammatical"] is True
    assert quality["error_correction_wrong_sentence_must_be_semantically_plausible"] is True
    assert quality["mechanical_preposition_replacement_allowed"] is False
    assert quality["learner_internal_engineering_language_allowed"] is False
    assert "grammar level" in contract.LEARNER_LANGUAGE_FORBIDDEN_PHRASES


def test_u04formv3_keeps_a1_and_defers_runtime_cutover():
    assert contract.CAMBRIDGE_BOUNDARY["grammar_ceiling"] == "A1"
    assert contract.CAMBRIDGE_BOUNDARY["a2_a2plus_unlocked"] is False
    assert contract.CAMBRIDGE_BOUNDARY["listening_modified"] is False
    assert contract.ACTIVATION_CONTRACT["pilot_forms"] == (1, 2, 3, 4)
    assert contract.ACTIVATION_CONTRACT["formv3_pilot_active_runtime"] is False
    assert contract.ACTIVATION_CONTRACT["current_fsv2_runtime_remains_active_until_successor_acceptance"] is True
    assert contract.ACTIVATION_CONTRACT["parallel_form_runtime_allowed"] is False
