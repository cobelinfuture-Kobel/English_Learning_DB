from __future__ import annotations

import json
from pathlib import Path

from ulga.builders import build_a1fs_v1_u02ch02_unit01_unit02_cumulative_chunk_coverage_recheck as u02ch02
from ulga.builders import build_a1fs_v1_u05q04_scene_functional_chunk_usage as scene_usage_builder


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q04_be_chunk_authority.json"
Q02 = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q02_vocabulary_carrier_authority.json"
Q03 = ROOT / "ulga" / "contracts" / "a1fs_v1_u05_q03_be_form_meaning_auxiliary_boundary_authority.json"
U04_Q04 = ROOT / "ulga" / "contracts" / "a1fs_v1_u04_q04_place_chunk_authority.json"
SCENE_USAGE = ROOT / "ulga" / "reports" / "a1fs_v1_u05_q04_scene_functional_chunk_usage.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def _u01_u02_surfaces() -> set[str]:
    u01 = {_norm(row["surface"]) for row in u02ch02.unit01_rows()}
    u02 = {_norm(row["surface"]) for row in u02ch02.unit02_rows()}
    assert len(u01) == 24
    assert len(u02) == 26
    assert not (u01 & u02)
    return u01 | u02


def _u04_new_surfaces(u04: dict) -> set[str]:
    target = {
        _norm(surface)
        for group in u04["target_relation_chunk_groups"]
        for surface in group["new_surfaces"]
    }
    support = {
        _norm(surface)
        for group in u04["yle_safe_support_chunk_groups"]
        for surface in group["new_surfaces"]
    }
    assert len(target) == 32
    assert len(support) == 8
    assert not (target & support)
    return target | support


def test_u05_q04_be_chunk_authority_and_cumulative_dedup() -> None:
    data = _load(ARTIFACT)
    q02 = _load(Q02)
    q03 = _load(Q03)
    u04 = _load(U04_Q04)

    assert data["status"] == "PASS_A1FS_V1_U05Q04_BE_CHUNK_AUTHORITY_AND_CUMULATIVE_DEDUP"
    assert data["unit_number"] == 5
    assert data["unit_id"] == "GRAMMAR_BE_VERB_BASIC"
    assert q02["status"] == "PASS_A1FS_V1_U05Q02_VOCABULARY_AUTHORITY_AND_REUSABLE_CARRIER_ADMISSION"
    assert q03["status"] == "PASS_A1FS_V1_U05Q03_BE_FORM_MEANING_AND_AUXILIARY_BOUNDARY_AUTHORITY"
    assert u04["status"] == "PASS_Q04_UNIT04_PLACE_CHUNK_AUTHORITY_AND_CUMULATIVE_DEDUP"

    prior_50 = _u01_u02_surfaces()
    u04_new = _u04_new_surfaces(u04)
    prior_90 = prior_50 | u04_new
    assert len(prior_50) == 50
    assert len(prior_90) == 90

    groups = {row["group_id"]: row for row in data["chunk_groups"]}
    assert set(groups) == {
        "U05-CH-G01-SUBJECT-BE-FULL",
        "U05-CH-G02-AFFIRMATIVE-CONTRACTION",
        "U05-CH-G03-NEGATIVE-BE-FULL",
        "U05-CH-G04-NEGATIVE-BE-CONTRACTED",
        "U05-CH-G05-NP-ROLE-COMPLEMENT",
        "U05-CH-G06-NP-PERSON-COMPLEMENT",
        "U05-CH-G07-ADJECTIVE-COMPLEMENT",
        "U05-CH-G08-AGE-STATE-COMPLEMENT",
        "U05-CH-G09-STATIC-PLACE-COMPLEMENT",
    }

    all_new = [
        surface
        for group in data["chunk_groups"]
        for surface in group["surfaces"]
    ]
    normalized_new = {_norm(surface) for surface in all_new}
    assert len(all_new) == 66
    assert len(normalized_new) == 66
    assert prior_90.isdisjoint(normalized_new)

    assert groups["U05-CH-G01-SUBJECT-BE-FULL"]["surfaces"] == [
        "I am", "you are", "he is", "she is", "it is", "we are", "they are"
    ]
    assert groups["U05-CH-G02-AFFIRMATIVE-CONTRACTION"]["surfaces"] == [
        "I'm", "you're", "he's", "she's", "it's", "we're", "they're"
    ]
    assert groups["U05-CH-G03-NEGATIVE-BE-FULL"]["surfaces"] == [
        "I am not", "you are not", "he is not", "she is not",
        "it is not", "we are not", "they are not"
    ]
    assert set(groups["U05-CH-G04-NEGATIVE-BE-CONTRACTED"]["surfaces"]) == {
        "I'm not",
        "you're not", "you aren't",
        "he's not", "he isn't",
        "she's not", "she isn't",
        "it's not", "it isn't",
        "we're not", "we aren't",
        "they're not", "they aren't",
    }

    coverage = data["coverage"]
    assert coverage == {
        "subject_be_full_form_chunks": 7,
        "affirmative_contraction_support_chunks": 7,
        "negative_full_form_chunks": 7,
        "negative_contracted_chunks": 13,
        "noun_phrase_complement_chunks": 10,
        "adjective_complement_chunks": 8,
        "age_state_complement_chunks": 8,
        "static_place_complement_chunks": 6,
        "total_new_surface_count": 66,
    }

    q02_admitted = {
        row["surface"].casefold()
        for row in q02["matrix"]
        if not row["unit05_admission_status"].startswith("BLOCKED_")
        and not row["unit05_admission_status"].startswith("REVIEW_REQUIRED")
    }
    used = data["source_carrier_bindings"]["used_q02_target_surfaces"]
    for surfaces in used.values():
        for surface in surfaces:
            assert surface.casefold() in q02_admitted

    assert set(data["predecessor_place_reuse"]["reused_place_complement_surfaces"]) == {
        "at school", "at home", "in the classroom"
    }
    u04_place_pool = {
        _norm(surface)
        for group in u04["target_relation_chunk_groups"]
        for surface in [*group["prior_exact_reuse"], *group["new_surfaces"]]
    }
    assert {
        "at school", "at home", "in the classroom"
    } <= u04_place_pool

    q03_aux = q03["auxiliary_be_boundary"]
    assert q03_aux["direct_unit05_target"] is False
    assert q03_aux["unit05_mastery_credit"] is False
    assert data["auxiliary_boundary"]["target_chunk_surfaces_created"] == 0
    assert data["auxiliary_boundary"]["q03_egp_row_id"] == q03_aux["egp_row_id"]
    for blocked in ["is playing", "are reading", "am writing"]:
        assert _norm(blocked) not in normalized_new

    for blocked in data["blocked_or_deferred_forms"]:
        assert _norm(blocked) not in normalized_new

    dedup = data["dedup_result"]
    assert dedup["prior_distinct_surfaces"] == 90
    assert dedup["unit05_new_surfaces"] == 66
    assert dedup["within_unit05_duplicate_count"] == 0
    assert dedup["prior_vs_unit05_overlap_count"] == 0
    assert dedup["cumulative_distinct_surfaces"] == 156
    assert dedup["new_global_canonical_chunk_identities"] == 0

    delta = data["delta_vs_unit04"]
    assert delta["prior_cumulative_chunk_surfaces"] == 90
    assert delta["unit05_new_morphology_chunk_surfaces"] == 34
    assert delta["unit05_new_complement_chunk_surfaces"] == 32
    assert delta["unit05_new_chunk_surfaces_total"] == 66
    assert delta["cumulative_chunk_surfaces_after_unit05_q04"] == 156
    assert delta["prior_cumulative_sentence_assets"] == 26610

    assert data["q04_boundaries"] == {
        "sentence_frames_materialized": False,
        "sentence_assets_materialized": False,
        "scenes_materialized": False,
        "communicative_functions_materialized": False,
        "questionbank_materialized": False,
        "forms_materialized": False,
        "be_interrogatives_activated": False,
        "past_be_activated": False,
        "existential_there_be_activated": False,
        "present_continuous_mastery_activated": False,
        "a2_unlocked": False,
        "scene_derived_sentence_assets_materialized": False,
        "scene_candidates_auto_promoted_to_chunk_authority": False,
    }

    policy = data["functional_chunk_policy"]
    assert policy["exact_66_surfaces_are_reusable_seed_floor_not_exhaustive_ceiling"] is True
    assert policy["scene_derived_functional_candidates_may_expand_q05_q06_carrier_reservoir"] is True
    assert policy["extracted_functional_candidate_count"] == 874
    assert policy["extracted_occurrence_count"] == 2246
    assert policy["covered_micro_scenes"] == "36/36"
    assert policy["candidate_not_auto_promoted_to_chunk_identity"] is True
    assert policy["q02_lexical_gate_required_before_q05_q06_promotion"] is True
    assert policy["q03_grammar_gate_required"] is True

    ledger = _load(SCENE_USAGE)
    rebuilt = scene_usage_builder.build_usage_ledger()
    assert ledger["status"] == "PASS_U05_Q04_SCENE_DERIVED_FUNCTIONAL_CHUNK_EXTRACTION"
    assert rebuilt["summary"] == ledger["summary"]
    assert [row["functional_chunk_id"] for row in rebuilt["functional_candidates"]] == [
        row["functional_chunk_id"] for row in ledger["functional_candidates"]
    ]
    assert [row["normalized_surface"] for row in rebuilt["functional_candidates"]] == [
        row["normalized_surface"] for row in ledger["functional_candidates"]
    ]
    summary = ledger["summary"]
    assert summary["reader_episode_count"] == 360
    assert summary["micro_scene_count"] == 36
    assert summary["micro_scenes_with_extracted_candidate_count"] == 36
    assert summary["extracted_occurrence_count"] == 2246
    assert summary["unique_functional_candidate_count"] == 874
    assert summary["current360_occurrence_count"] == 924
    assert summary["spoken360_occurrence_count"] == 1322
    assert summary["unique_by_class"] == {
        "STATIC_PLACE_FUNCTIONAL": 745,
        "NEGATIVE_BE_FUNCTIONAL": 2,
        "COPULAR_COMPLEMENT_FUNCTIONAL": 127,
    }
    assert summary["high_utility_candidate_count"] == 111
    assert summary["repeated_candidate_count"] == 279
    assert summary["single_attestation_candidate_count"] == 484
    assert summary["exact_q04_seed_surface_count"] == 66
    assert summary["exact_q04_seed_observed_count"] == 15
    assert summary["exact_q04_seed_unobserved_count"] == 51
    assert summary["candidates_observed_in_both_layers"] == 149
    assert ledger["downstream_usage_recording_contract"]["required"] is True
    assert ledger["downstream_usage_recording_contract"]["actual_q05_q06_usage_not_yet_materialized"] is True
    assert ledger["claim_boundaries"]["scene_candidates_added_to_exact_chunk_denominator"] == 0
    assert ledger["claim_boundaries"]["cumulative_exact_chunk_surface_count"] == 156

    assert data["next_short_step"] == "A1FS-V1-U05Q05_Unit05CoreSentenceFrameAuthority"
