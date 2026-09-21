from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ulga.builders import build_a1fs_v1_u05_q06_sentence_assets as q06_builder
from ulga.builders import build_a1fs_v1_u05_q07_life_skill_micro_scenes as q07_builder

ROOT = Path(__file__).resolve().parents[2]
Q08 = ROOT / "ulga/contracts/a1fs_v1_u05_q08_communicative_function_authority.json"
REUSABLE = ROOT / "ulga/contracts/a1fs_v1_reusable_unit_production_contract.json"

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


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_u05_q08_is_exact_communicative_function_authority_slot():
    q08 = load(Q08)
    reusable = load(REUSABLE)
    slot = next(row for row in reusable["authority_pipeline"]["required_slots"] if row["q"] == "Q08")
    assert slot["role"] == "COMMUNICATIVE_FUNCTION_AUTHORITY"
    assert q08["task_id"] == "A1FS-V1-U05Q08_Unit05CommunicativeFunctionAuthority"
    assert q08["authority_role"] == "Q08_COMMUNICATIVE_FUNCTION_AUTHORITY"
    assert q08["status"] == "PASS_A1FS_V1_U05Q08_COMMUNICATIVE_FUNCTION_AUTHORITY"
    assert q08["acceptance"]["status"] == q08["status"]


def test_u05_q08_function_inventory_is_unique_bounded_and_four_skill_compatible():
    q08 = load(Q08)
    functions = q08["communicative_functions"]
    ids = [row["function_id"] for row in functions]
    assert len(functions) == 7
    assert len(ids) == len(set(ids)) == 7
    assert set(ids) == EXPECTED_FUNCTION_IDS
    assert q08["coverage"]["communicative_function_count"] == 7
    assert q08["acceptance"]["communicative_function_authority"] == "7/7"

    skills = {skill for row in functions for skill in row["skill_compatibility"]}
    assert skills == {"READING", "WRITING", "LISTENING", "SPEAKING"}
    assert all(row["accepted_sentence_required"] is True for row in functions)
    assert all(row["accepted_scene_required_when_q06_context_bound"] is True for row in functions)
    assert all(row["creates_new_grammar_authority"] is False for row in functions)


def test_u05_q08_exactly_covers_all_six_q05_frames():
    q08 = load(Q08)
    matrix = q08["frame_function_compatibility"]
    assert set(q08["scope"]["q05_frame_ids"]) == EXPECTED_FRAMES
    assert set(matrix) == EXPECTED_FRAMES
    assert all(matrix[frame] for frame in EXPECTED_FRAMES)
    assert all(set(ids).issubset(EXPECTED_FUNCTION_IDS) for ids in matrix.values())
    assert q08["coverage"]["q05_frame_count"] == 6
    assert q08["coverage"]["q05_frame_function_coverage"] == "6/6"
    assert q08["acceptance"]["q05_frame_function_coverage"] == "6/6"


def test_u05_q08_all_855_q06_usable_sentences_have_function_coverage():
    q08 = load(Q08)
    q06 = q06_builder.build_report()
    rows = [*q06["reuse_bindings"], *q06["new_sentence_assets"]]
    matrix = q08["frame_function_compatibility"]

    assert len(rows) == 855
    covered = [row for row in rows if row["frame_id"] in matrix and matrix[row["frame_id"]]]
    assert len(covered) == 855
    assert q08["coverage"]["q06_usable_sentence_count"] == 855
    assert q08["coverage"]["q06_usable_sentence_function_coverage"] == "855/855"
    assert q08["acceptance"]["q06_usable_sentence_function_coverage"] == "855/855"

    context = [row for row in rows if row["requires_context_binding"] is True]
    standalone = [row for row in rows if row["requires_context_binding"] is False]
    assert len(context) == 478
    assert len(standalone) == 377
    assert all(matrix[row["frame_id"]] for row in context)
    assert all(matrix[row["frame_id"]] for row in standalone)
    assert q08["coverage"]["q07_context_required_sentence_function_coverage"] == "478/478"
    assert q08["coverage"]["q06_standalone_sentence_function_coverage"] == "377/377"


def test_u05_q08_preserves_all_q07_scene_truth_and_referent_guards():
    q08 = load(Q08)
    q07 = q07_builder.build_report()
    bindings = q07["sentence_scene_bindings"]
    scenes = q07["micro_scenes"]
    matrix = q08["frame_function_compatibility"]

    assert len(bindings) == 478
    assert all(row["frame_id"] in matrix and matrix[row["frame_id"]] for row in bindings)
    assert q08["sentence_and_scene_function_acceptance"]["q07_context_required_sentence_function_coverage_required"] == "478/478"
    assert q08["sentence_and_scene_function_acceptance"]["q07_scene_truth_remains_authoritative"] is True
    assert q08["sentence_and_scene_function_acceptance"]["q07_referent_binding_remains_authoritative"] is True
    assert q08["sentence_and_scene_function_acceptance"]["q07_negative_positive_contrast_guard_remains_authoritative"] is True
    assert q08["sentence_and_scene_function_acceptance"]["q07_single_answer_unique_cue_guard_remains_authoritative"] is True

    for scene in scenes:
        assert scene["answerability_guard"]["scene_binds_truth_of_all_bound_sentences"] is True
        assert scene["answerability_guard"]["learner_visible_target_sentence_used_as_scene_prompt"] is False
        if scene["subject_class"] in {"he", "she", "it", "they"}:
            assert scene["referent_binding_spec"]["required"] is True
        if scene["polarity"] == "NEGATIVE":
            assert scene["truth_evidence_spec"]["explicit_positive_alternative_required_for_negative"] is True
            assert scene["truth_evidence_spec"]["negation_proof_by_absence_allowed"] is False


def test_u05_q08_negative_function_is_bound_to_negative_frames_only():
    q08 = load(Q08)
    function = next(row for row in q08["communicative_functions"] if row["function_id"] == "U05-CF04_DENY_OR_CORRECT_BASIC_BE_INFORMATION")
    assert set(function["eligible_frame_ids"]) == {
        "U05-BF-NP-NEG",
        "U05-BF-ADJ-NEG",
        "U05-BF-PLACE-NEG",
    }
    assert function["negative_truth_requires_positive_contrast_evidence"] is True

    matrix = q08["frame_function_compatibility"]
    for frame in {"U05-BF-NP-NEG", "U05-BF-ADJ-NEG", "U05-BF-PLACE-NEG"}:
        assert function["function_id"] in matrix[frame]
    for frame in {"U05-BF-NP-AFF", "U05-BF-ADJ-AFF", "U05-BF-PLACE-AFF"}:
        assert function["function_id"] not in matrix[frame]


def test_u05_q08_information_seeking_and_checking_do_not_unlock_interrogative_mastery():
    q08 = load(Q08)
    funcs = {row["function_id"]: row for row in q08["communicative_functions"]}
    for function_id in {"U05-CF05_REQUEST_BASIC_BE_INFORMATION", "U05-CF06_CONFIRM_BASIC_BE_INFORMATION"}:
        row = funcs[function_id]
        assert row["exact_question_form_materialized_here"] is False
        assert row["be_interrogative_mastery_unlocked"] is False
        assert row["creates_new_grammar_authority"] is False

    policy = q08["function_realization_policy"]
    assert policy["new_question_grammar_authorized_by_q08"] is False
    assert policy["information_seeking_or_checking_function_does_not_unlock_be_interrogative_mastery"] is True
    assert q08["scope"]["be_interrogative_mastery_activated"] is False


def test_u05_q08_does_not_materialize_q09_q10_reader360_or_later_grammar():
    q08 = load(Q08)
    policy = q08["function_realization_policy"]
    boundaries = q08["q08_boundaries"]

    assert policy["communicative_function_ids_are_semantic_intent_authority_only"] is True
    assert policy["learner_visible_prompt_or_utterance_templates_materialized_by_q08"] is False
    assert policy["new_sentence_pattern_family_authorized_by_q08"] is False
    assert policy["new_vocabulary_identity_authorized_by_q08"] is False
    assert policy["new_scene_identity_authorized_by_q08"] is False

    for key in (
        "q06_sentence_semantics_modified",
        "q07_scene_semantics_modified",
        "learner_visible_prompts_materialized",
        "learner_visible_utterance_templates_materialized",
        "task_families_materialized",
        "questionbank_materialized",
        "forms_materialized",
        "unit05_current360_materialized",
        "unit05_spoken360_materialized",
        "unit05_pattern360_materialized",
        "be_interrogative_mastery_activated",
        "past_be_activated",
        "existential_there_be_activated",
        "present_continuous_mastery_activated",
        "a2_a2plus_unlocked",
    ):
        assert boundaries[key] is False

    assert q08["coverage"]["new_grammar_authority_count"] == 0
    assert q08["coverage"]["new_sentence_pattern_family_count"] == 0
    assert q08["coverage"]["new_vocabulary_identity_count"] == 0
    assert q08["coverage"]["new_scene_identity_count"] == 0
    assert q08["next_short_step"] == "A1FS-V1-U05Q09_Unit05TaskAndPedagogicalContract"
