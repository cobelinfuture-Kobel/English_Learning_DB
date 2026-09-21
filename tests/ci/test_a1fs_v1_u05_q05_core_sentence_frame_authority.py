import json
from pathlib import Path

from ulga.builders import (
    build_a1fs_v1_u02sp02_unit01_unit02_exact_sentence_frame_coverage_recheck as u02sp02,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
Q05_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u05_q05_core_sentence_frame_authority.json"
Q03_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u05_q03_be_form_meaning_auxiliary_boundary_authority.json"
Q04_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u05_q04_be_chunk_authority.json"
U04_Q05_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u04_q05_core_sentence_frame_authority.json"
PATTERN_PATH = REPO_ROOT / "ulga/graph/sentence_patterns.json"
SCENE_USAGE_PATH = REPO_ROOT / "ulga/reports/a1fs_v1_u05_q04_scene_functional_chunk_usage.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _norm(value: str) -> str:
    return " ".join(str(value).casefold().split())


def _q05():
    return _load(Q05_PATH)


def _q03():
    return _load(Q03_PATH)


def _q04():
    return _load(Q04_PATH)


def _u04_q05():
    return _load(U04_Q05_PATH)


def _sp_index():
    rows = _load(PATTERN_PATH)
    return {
        row["authority_source"]["source_record_id"]: row
        for row in rows
        if row.get("authority_source", {}).get("source_record_id")
    }


def test_u05_q05_current_main_preflight_requires_no_private_unit04_or_reader360_upload():
    data = _q05()
    baseline = data["prior_frame_baseline"]
    reconstruction = baseline["current_main_reconstruction"]

    assert data["status"] == "PASS_A1FS_V1_U05Q05_UNIT05_CORE_SENTENCE_FRAME_AUTHORITY"
    assert data["unit_id"] == "GRAMMAR_BE_VERB_BASIC"
    assert baseline["unit01_exact_frame_count"] == 11
    assert baseline["unit02_new_exact_frame_count"] == 4
    assert baseline["unit03_new_exact_frame_count"] == 0
    assert baseline["unit04_new_exact_frame_count"] == 8
    assert baseline["prior_cumulative_exact_frame_count"] == 23
    assert reconstruction["all_23_prior_exact_frames_reconstructable_from_current_main"] is True
    assert reconstruction["private_unit04_or_reader360_archive_required_for_q05_frame_dedup"] is False
    assert data["acceptance"]["private_authority_upload_required"] is False


def test_u05_q05_unlocks_existing_global_identity_be_family_without_mutating_global_pattern_authority():
    data = _q05()
    binding = data["global_pattern_authority_binding"]
    row = _sp_index()["SP_000001"]
    metadata = row["metadata"]

    assert row["label"] == "I am {adjective/noun_phrase}."
    assert metadata["canonical_pattern"] == binding["canonical_pattern"]
    assert metadata["pattern_family_id"] == binding["pattern_family_id"] == "family:identity_be"
    assert metadata["review_status"] == "accepted"
    assert metadata["generator_allowed"] is True
    assert binding["new_global_pattern_identity_created"] is False

    policy = data["pattern_family_policy"]
    assert policy["prior_cumulative_course_pattern_family_count"] == 7
    assert policy["newly_unlocked_existing_global_pattern_family_count"] == 1
    assert policy["newly_unlocked_existing_global_pattern_family_ids"] == ["family:identity_be"]
    assert policy["new_global_pattern_identity_count"] == 0
    assert policy["cumulative_course_pattern_family_count"] == 8
    assert data["q05_boundaries"]["global_sentence_pattern_authority_mutated"] is False


def test_u05_q05_materializes_exactly_the_six_q03_allowed_direct_frame_families():
    data = _q05()
    frames = data["unit05_operational_frames"]
    q03_allowed = _q03()["downstream_constraints"]["q05"]["allowed_frame_families"]

    assert len(frames) == 6
    assert {row["q03_allowed_frame_family"] for row in frames} == set(q03_allowed)
    assert {row["polarity"] for row in frames} == {"AFFIRMATIVE", "NEGATIVE"}
    assert {row["frame_id"] for row in frames} == {
        "U05-BF-NP-AFF",
        "U05-BF-ADJ-AFF",
        "U05-BF-PLACE-AFF",
        "U05-BF-NP-NEG",
        "U05-BF-ADJ-NEG",
        "U05-BF-PLACE-NEG",
    }
    assert all(row["direct_generation_allowed"] is True for row in frames)

    assert {row["template"] for row in frames} == {
        "{SUBJECT} {BE_PRESENT} {NOUN_PHRASE_COMPLEMENT}.",
        "{SUBJECT} {BE_PRESENT} {ADJECTIVE_COMPLEMENT}.",
        "{SUBJECT} {BE_PRESENT} {STATIC_PLACE_PP_COMPLEMENT}.",
        "{SUBJECT} {BE_PRESENT_NEGATIVE} {NOUN_PHRASE_COMPLEMENT}.",
        "{SUBJECT} {BE_PRESENT_NEGATIVE} {ADJECTIVE_COMPLEMENT}.",
        "{SUBJECT} {BE_PRESENT_NEGATIVE} {STATIC_PLACE_PP_COMPLEMENT}.",
    }


def test_u05_q05_subject_be_resolution_matches_q03_full_paradigm_and_negative_contract():
    data = _q05()
    q03 = _q03()
    aff = data["subject_be_resolution"]["affirmative_full"]
    neg = data["subject_be_resolution"]["negative_resolution"]

    q03_aff = {
        row["subject_class"]: (row["affirmative_full"], row["be_form"])
        for row in q03["subject_be_agreement"]
    }
    q05_aff = {
        row["subject_class"]: (row["affirmative_prefix"], row["be_surface"])
        for row in aff
    }
    assert q05_aff == q03_aff
    assert len(q05_aff) == 9

    q03_neg = {
        row["subject_class"]: (
            row["full"],
            tuple(row["allowed_contractions"]),
            tuple(row["blocked_forms"]),
        )
        for row in q03["negative_be_contract"]["paradigms"]
    }
    q05_neg = {
        row["subject_class"]: (
            row["full_prefix"],
            tuple(row["allowed_contracted_prefixes"]),
            tuple(row["blocked_prefixes"]),
        )
        for row in neg
    }
    assert q05_neg == q03_neg
    assert data["subject_be_resolution"]["affirmative_contraction_policy"]["core_mastery_required"] is False
    assert data["subject_be_resolution"]["affirmative_contraction_policy"]["noun_subject_contraction_allowed"] is False


def test_u05_q05_place_complement_reuses_unit04_relation_routes_without_reopening_relation_semantics():
    data = _q05()
    place = data["complement_constraints"]["static_place_pp"]
    u04 = _u04_q05()["q06_primary_generation_routing"]

    assert place["direct_target_relations"] == [
        "in", "inside", "on", "near", "at", "under", "behind", "between"
    ]
    assert place["predecessor_primary_frame_routes"] == u04["target_relations"]
    assert place["support_relations_not_unit05_direct_target"] == ["next to", "in front of"]
    assert place["reopen_unit04_relation_semantics"] is False


def test_u05_q05_exact_frame_dedup_is_fully_provable_from_current_main():
    data = _q05()
    u04 = _u04_q05()

    prior_templates = [row["template"] for row in u02sp02.unit01_exact_frames()]
    prior_templates.extend(u02sp02.UNIT02_NEW_CANONICAL_PATTERNS.values())
    prior_templates.extend(row["template"] for row in u04["unit04_new_exact_frames"])
    assert len(prior_templates) == 23
    assert len({_norm(value) for value in prior_templates}) == 23

    new_templates = [row["template"] for row in data["unit05_operational_frames"]]
    assert len(new_templates) == 6
    assert len({_norm(value) for value in new_templates}) == 6
    assert {_norm(value) for value in prior_templates}.isdisjoint(
        {_norm(value) for value in new_templates}
    )

    counts = data["frame_dedup_and_counts"]
    assert counts["prior_exact_frames"] == 23
    assert counts["new_exact_operational_frames"] == 6
    assert counts["within_new_exact_template_duplicate_count"] == 0
    assert counts["exact_template_overlap_with_prior_23"] == 0
    assert counts["cumulative_exact_frames"] == 29


def test_u05_q05_binds_q04_chunks_and_scene_reservoir_without_promoting_scene_sentences_to_frames():
    data = _q05()
    q04 = _q04()
    scene = _load(SCENE_USAGE_PATH)
    evidence = data["scene_functional_evidence_projection"]

    assert q04["acceptance"]["cumulative_distinct_chunk_surface_count"] == 156
    assert data["acceptance"]["q04_cumulative_chunk_surface_count"] == 156
    assert evidence["unique_functional_candidate_count"] == scene["summary"]["unique_functional_candidate_count"] == 874
    assert evidence["occurrence_count"] == scene["summary"]["extracted_occurrence_count"] == 2246
    assert evidence["micro_scene_coverage"] == "36/36"
    assert evidence["class_counts"] == {
        "STATIC_PLACE_FUNCTIONAL": 745,
        "COPULAR_COMPLEMENT_FUNCTIONAL": 127,
        "NEGATIVE_BE_FUNCTIONAL": 2,
    }
    assert evidence["individual_functional_candidate_promoted_to_q05_frame_authority_count"] == 0
    assert evidence["q05_actual_functional_candidate_usage_record_count"] == 0
    assert evidence["q06_actual_usage_ledger_required_when_candidate_consumed"] is True


def test_u05_q05_keeps_auxiliary_be_and_later_grammar_out_of_direct_target_frames():
    data = _q05()
    boundary = data["auxiliary_be_boundary"]
    routing = data["q06_primary_generation_routing"]

    assert boundary["boundary_only"] is True
    assert boundary["direct_target_frame_count"] == 0
    assert boundary["be_plus_ing_target_frame_allowed"] is False
    assert boundary["present_continuous_mastery_credit"] is False

    assert routing["auxiliary_be_target_sentence_allowed"] is False
    assert routing["be_interrogative_target_sentence_allowed"] is False
    assert routing["past_be_target_sentence_allowed"] is False
    assert routing["existential_there_be_target_sentence_allowed"] is False
    assert routing["next_unit_grammar_allowed"] is False


def test_u05_q05_delta_boundaries_and_next_step_are_explicit():
    data = _q05()
    counts = data["frame_dedup_and_counts"]
    acceptance = data["acceptance"]

    assert counts == {
        "prior_exact_frames": 23,
        "new_exact_operational_frames": 6,
        "within_new_exact_template_duplicate_count": 0,
        "exact_template_overlap_with_prior_23": 0,
        "cumulative_exact_frames": 29,
        "prior_cumulative_course_pattern_families": 7,
        "newly_unlocked_existing_global_pattern_families": 1,
        "cumulative_course_pattern_families": 8,
        "new_global_pattern_identities": 0,
    }
    assert acceptance["new_exact_operational_frame_count"] == 6
    assert acceptance["cumulative_exact_frame_count"] == 29
    assert acceptance["allowed_q03_frame_family_count"] == 6
    assert acceptance["q03_subject_agreement_row_count"] == 9
    assert acceptance["direct_static_place_relation_count"] == 8
    assert acceptance["cumulative_course_pattern_family_count"] == 8
    assert acceptance["new_global_pattern_identity_count"] == 0
    assert acceptance["auxiliary_be_target_frame_count"] == 0

    assert data["q05_boundaries"] == {
        "sentence_assets_materialized": False,
        "scene_bindings_materialized": False,
        "communicative_functions_materialized": False,
        "questionbank_materialized": False,
        "forms_materialized": False,
        "global_sentence_pattern_authority_mutated": False,
        "reader360_regenerated": False,
        "private_unit04_or_reader360_input_required": False,
        "be_interrogatives_activated": False,
        "past_be_activated": False,
        "existential_there_be_activated": False,
        "present_continuous_mastery_activated": False,
        "a2_a2plus_unlocked": False,
    }
    assert data["next_short_step"] == "A1FS-V1-U05Q06_Unit05SentenceAssetProductionAndSemanticAdmission"
