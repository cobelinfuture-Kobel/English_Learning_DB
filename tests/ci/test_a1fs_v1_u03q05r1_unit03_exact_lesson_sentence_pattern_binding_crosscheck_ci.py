from ulga.builders import build_a1fs_v1_u03q05r1_unit03_exact_lesson_sentence_pattern_binding_crosscheck as builder


def _report():
    value = builder.build_report()
    builder.validate(value)
    return value


def test_u03q05r1_lesson_has_no_explicit_sentence_pattern_resource_binding():
    lesson = _report()["lesson_binding"]
    assert lesson["lesson_id"] == "KLSN-WF02-L02"
    assert lesson["requirement_node_id"] == "REF:WRITING:A1W-08"
    assert lesson["lesson_target"] == "subject/object reference"
    assert lesson["grammar_resource_ids"] == ["KPOP-GR-014", "KPOP-GR-015"]
    assert lesson["explicit_sentence_pattern_resource_ids"] == []
    assert lesson["unit03_exact_canonical_sentence_pattern_binding_ids"] == []
    assert lesson["production_shape"] == "TWO_CONNECTED_SENTENCES_ONE_CHILD_ONE_TOY_PRONOUN_CLEAR"
    assert lesson["notice_example_surfaces"] == ["Ben has a kite.", "He likes it."]
    assert lesson["source_provides_complete_target_sentence"] is False
    assert lesson["source_allows_automatic_sentence_generation"] is False
    assert lesson["source_requires_separately_reviewed_example"] is True
    assert lesson["binding_result"] == "NO_EXPLICIT_UNIT03_SENTENCE_PATTERN_RESOURCE_BINDING"


def test_u03q05r1_subject_pronoun_rule_primitive_is_not_sentence_pattern_authority():
    rule = _report()["subject_pronoun_rule_primitive"]
    assert rule["rule_id"] == "SUBJECT_PRONOUN_CLOSED_LIST_BEFORE_VERB"
    assert rule["core_pattern"] == "subject pronoun + finite verb"
    assert rule["verified"] is False
    assert rule["batch_candidate_only"] is True
    assert rule["coverage_claim_allowed"] is False
    assert rule["sentence_pattern_authority"] is False
    assert rule["may_materialize_unit03_q5_pattern"] is False


def test_u03q05r1_global_sp000001_surface_overlap_is_not_exact_lesson_binding():
    diagnostic = _report()["global_pattern_overlap_diagnostic"]
    assert diagnostic == {
        "source_record_id": "SP_000001",
        "canonical_pattern": "I am {adjective/noun_phrase}.",
        "example_surface": "I am happy.",
        "same_example_surface_present_in_rule_primitive": True,
        "lesson_explicit_binding": False,
        "unit03_q5_admitted": False,
        "reason": "GLOBAL_PATTERN_OR_RULE_EXAMPLE_OVERLAP_IS_NOT_EXACT_LESSON_BINDING",
    }


def test_u03q05r1_keeps_q5_cumulative_denominators_at_unit02_authority():
    value = _report()
    families = value["q5_pattern_family_coverage"]
    frames = value["q5_exact_frame_coverage"]
    assert families["unit01_unit02_inherited_family_count"] == 7
    assert families["unit03_new_canonical_pattern_family_count"] == 0
    assert families["cumulative_pattern_family_count"] == 7
    assert len(families["inherited_families"]) == 7
    assert families["unit03_new_families"] == []
    assert frames["unit01_unit02_inherited_exact_frame_count"] == 15
    assert frames["unit03_new_exact_frame_count"] == 0
    assert frames["cumulative_exact_frame_count"] == 15
    assert len(frames["inherited_exact_frames"]) == 15
    assert frames["unit03_new_exact_frames"] == []


def test_u03q05r1_does_not_generalize_pronoun_substitution_or_create_downstream_assets():
    value = _report()
    decision = value["admission_decision"]
    assert decision == {
        "unit03_native_sentence_pattern_family_count": 0,
        "unit03_native_exact_frame_count": 0,
        "pronoun_substitution_creates_new_pattern_family": False,
        "generalize_i_patterns_across_pronouns_without_explicit_authority": False,
        "learner_generated_or_notice_example_promoted_to_pattern_authority": False,
    }
    assert value["claim_boundaries"] == {
        "canonical_sentence_pattern_authority_mutated": False,
        "grammar_rule_authority_mutated": False,
        "sentence_assets_created": False,
        "questionbank_items_created": False,
        "canonical_scene_authority_mutated": False,
        "runtime_or_learner_state_mutated": False,
        "a2_unlocked": False,
    }
    assert value["next_scope"] == {
        "scope_status": "OUTSIDE_APPROVED_Q5_SCOPE",
        "next_short_step": "A1FS-V1-U03Q06R1_Unit03CumulativeSentenceAssetCoverageProjection",
    }
