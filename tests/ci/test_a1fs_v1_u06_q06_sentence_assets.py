from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from ulga.builders import build_a1fs_v1_u06_q06_sentence_assets as builder

ROOT = Path(__file__).resolve().parents[2]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def report():
    return builder.build_report()


def test_q06_uses_gpt56_explicit_authored_seed_not_python_english_generation():
    r = report()
    g = r["generation_authority"]
    seed = load("ulga/reports/a1fs_v1_u06_q06_authored_sentence_seed.json")
    assert g["learner_english_authoring_mode"] == "GPT-5.6_SOL_EXPLICIT_AUTHORED_AND_REVIEWED_SEED"
    assert g["python_builder_english_generation_allowed"] is False
    assert g["candidate_generation_policy"] == "EXPLICIT_REVIEWED_SENTENCE_ROWS_NOT_CARTESIAN_AUTOGENERATION"
    assert seed["authoring_model"] == "GPT-5.6 Sol"
    assert seed["python_builder_may_author_learner_english"] is False
    assert len(seed["candidates"]) == 135


def test_q02_q03_q04r1_q05_current_authority_alignment():
    r = report()
    q02 = load("ulga/contracts/a1fs_v1_u06_q02_vocabulary_carrier_authority.json")
    q03 = load("ulga/contracts/a1fs_v1_u06_q03_can_form_meaning_boundary_authority.json")
    q04 = load("ulga/contracts/a1fs_v1_u06_q04r1_yle_can_ability_chunk_expansion.json")
    q05 = load("ulga/contracts/a1fs_v1_u06_q05_core_sentence_frame_authority.json")
    assert q02["summary"]["admitted_identity_count"] == 91
    assert q03["status"] == "PASS_A1FS_V1_U06Q03_CAN_FORM_MEANING_BOUNDARY_AUTHORITY"
    assert q04["acceptance"]["course_cumulative_distinct_chunk_surfaces_after_r1"] == 266
    assert q04["q04r1_chunk_expansion"]["can_base_verb"]["total_surface_count_after_r1"] == 62
    assert q04["q04r1_chunk_expansion"]["non_scene_functional_chunks"]["total_surface_count_after_r1"] == 41
    assert q05["q06_primary_generation_routing"]["predecessor_sentence_pool_for_dedup"] == 27371
    assert q05["q06_primary_generation_routing"]["exact_and_normalized_sentence_dedup_required"] is True
    assert q05["q06_primary_generation_routing"]["semantic_pedagogical_admission_required"] is True
    assert r["generation_authority"]["q05_frame_ids"] == [
        "U06-CF-ABILITY-INTRANSITIVE",
        "U06-CF-ABILITY-OBJECT",
        "U06-CF-ABILITY-PREDICATE-TAIL",
    ]


def test_semantic_review_counts_and_deferred_sense_gate():
    r = report()
    s = r["semantic_review"]
    assert s["review_model"] == "GPT-5.6 Sol"
    assert (s["reviewed_candidate_count"], s["approved_count"], s["context_bound_approved_count"]) == (135, 80, 49)
    assert (s["deferred_count"], s["rejected_count"], s["usable_count"]) == (6, 0, 129)
    excluded = r["excluded_candidates"]
    assert len(excluded) == 6
    assert {row["base_verb"] for row in excluded} == {"change", "do", "give", "go", "study", "tell"}
    assert all(row["decision"] == "DEFER" for row in excluded)
    assert all(row["q07_resolution_required"] is True for row in excluded)


def test_materialized_assets_are_unique_and_cover_all_three_q05_frames():
    r = report()
    rows = r["new_sentence_assets"]
    assert len(rows) == 129
    assert len(r["reuse_bindings"]) == 0
    assert len({row["sentence_id"] for row in rows}) == 129
    assert len({row["normalized_text"] for row in rows}) == 129
    counts = Counter(row["frame_id"] for row in rows)
    assert dict(sorted(counts.items())) == r["coverage"]["frame_counts"]
    assert dict(sorted(counts.items())) == {
        "U06-CF-ABILITY-INTRANSITIVE": 24,
        "U06-CF-ABILITY-OBJECT": 28,
        "U06-CF-ABILITY-PREDICATE-TAIL": 77,
    }


def test_subject_paradigm_and_context_binding_are_covered():
    rows = report()["new_sentence_assets"]
    counts = Counter(row["subject_class"] for row in rows)
    assert dict(sorted(counts.items())) == {
        "ADMITTED_PERSON_OR_ROLE_NOUN_PHRASE": 34,
        "I": 32,
        "he": 13,
        "it": 2,
        "she": 14,
        "they": 11,
        "we": 12,
        "you": 11,
    }
    for subject in ("I", "you", "he", "she", "it", "we", "they", "ADMITTED_PERSON_OR_ROLE_NOUN_PHRASE"):
        assert counts[subject] > 0
    contextual = [row for row in rows if row["semantic_admission_class"] == "CONTEXT_BOUND_APPROVE"]
    assert len(contextual) == 49
    assert all(row["requires_context_binding"] is True for row in contextual)
    assert all(row["direct_unit06_assessment_allowed"] is False for row in contextual)


def test_q04r1_lexical_and_functional_coverage_is_explicit():
    c = report()["coverage"]
    assert c["q04r1_can_base_verb_surface_count"] == 62
    assert c["q06_sentence_admitted_can_base_verb_surface_count"] == 56
    assert c["q06_sentence_deferred_can_base_verb_surface_count"] == 6
    assert set(c["deferred_can_base_verbs"]) == {"change", "do", "give", "go", "study", "tell"}
    assert c["q04r1_functional_chunk_surface_count"] == 41
    assert c["q06_sentence_admitted_functional_chunk_surface_count"] == 39
    assert c["q06_sentence_deferred_functional_chunk_surface_count"] == 2
    assert set(c["deferred_functional_chunks"]) == {"can go to school", "can study at school"}


def test_predecessor_dedup_claim_is_bounded_and_private_safe():
    d = report()["predecessor_dedup_receipt"]
    assert d["predecessor_asset_row_count"] == 27371
    assert d["q05_exact_and_normalized_dedup_required"] is True
    assert d["proof_mode"] == "CURRENT_COURSE_PATTERN_FAMILY_DISJOINTNESS_PLUS_CANDIDATE_EXACT_NORMALIZED_IDENTITY_CHECK"
    assert d["prior_course_pattern_family_count"] == 8
    assert d["unit06_newly_unlocked_family"] == "family:ability_can"
    assert d["all_usable_candidates_modal_can_family"] is True
    assert d["full_private_predecessor_sentence_body_replay_performed"] is False
    assert d["private_u01_u03_sentence_bodies_committed"] is False
    assert d["exact_or_normalized_predecessor_collision_count"] == 0


def test_no_question_negative_nonability_or_later_grammar_leaks():
    r = report()
    for row in r["new_sentence_assets"]:
        text = row["text"]
        assert "?" not in text
        assert not re.search(r"\b(?:cannot|can't|can\s+not)\b", text, flags=re.I)
        assert not re.search(r"\bcan\s+to\b", text, flags=re.I)
        assert row["canonical_admission_status"] == "ADMITTED"
        assert row["counts_as_q03_target_evidence"] is True
        assert row["a2_unlocked"] is False
    b = r["q06_boundaries"]
    for key in (
        "scene_materialized", "communicative_functions_materialized", "questionbank_materialized",
        "forms_materialized", "reader360_materialized", "can_question_target_sentence_allowed",
        "can_negative_target_sentence_allowed", "non_ability_can_target_sentence_allowed",
        "a2_a2plus_grammar_unlocked",
    ):
        assert b[key] is False


def test_q06_acceptance_next_step_and_policy_bound_transition():
    r = report()
    a = r["acceptance"]
    assert a["authored_candidate_count"] == 135
    assert a["semantic_review_usable_count"] == 129
    assert a["unit06_new_admitted_sentence_asset_count"] == 129
    assert a["deferred_count"] == 6
    assert a["rejected_count"] == 0
    assert a["predecessor_dedup_denominator"] == 27371
    assert a["predecessor_collision_count"] == 0
    assert a["q04r1_can_base_verb_coverage"] == "56/62"
    assert a["q04r1_functional_chunk_coverage"] == "39/41"
    assert r["next_short_step"] == "A1FS-V1-U06Q07_Unit06LifeSkillMicroSceneMaterializationAndSentenceBinding"

    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    assert candidate["artifact_role"] == "CANDIDATE_JSON"
    assert candidate["producer_id"] == builder.TASK_ID
    assert candidate["level_scope"] == ["A1"]
    assert approved["artifact_role"] == "APPROVED_CANONICAL_JSON"
    assert approved["admission"]["status"] == "APPROVED"
    assert approved["admission"]["decision_ref"] == builder.DECISION_REF
    assert approved["payload"] == candidate["payload"]
    assert approved["content_governance"]["a2_unlocked"] is False
