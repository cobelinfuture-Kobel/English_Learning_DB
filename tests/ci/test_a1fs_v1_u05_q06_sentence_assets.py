from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from ulga.builders import build_a1fs_v1_u05_q06_sentence_assets as builder

ROOT = Path(__file__).resolve().parents[2]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def report():
    return builder.build_report()


def usable(r):
    return [*r["reuse_bindings"], *r["new_sentence_assets"]]


def test_q06_is_unit_local_and_reader360_is_not_generation_authority():
    r = report()
    g = r["generation_authority"]
    assert g["unit_local_only"] is True
    assert g["direct_q02_carrier_count"] == 94
    assert g["reader360_generation_authority_used"] is False
    assert g["unit04_current360_used_as_generation_authority"] is False
    assert g["unit04_spoken360_used_as_generation_authority"] is False
    assert g["unit04_pattern360_used_as_generation_authority"] is False
    assert g["unit05_reader360_materialized"] is False
    assert g["scene_functional_candidate_promoted_count"] == 0
    assert g["functional_candidate_usage_ledger_entry_count"] == 0


def test_q02_q03_q04_q05_current_authority_alignment():
    r = report()
    q02 = load("ulga/contracts/a1fs_v1_u05_q02_vocabulary_carrier_authority.json")
    q03 = load("ulga/contracts/a1fs_v1_u05_q03_be_form_meaning_auxiliary_boundary_authority.json")
    q04 = load("ulga/contracts/a1fs_v1_u05_q04_be_chunk_authority.json")
    q05 = load("ulga/contracts/a1fs_v1_u05_q05_core_sentence_frame_authority.json")
    assert q02["summary"]["overall"]["admitted_identity_count"] == 106
    allowed = {c for frame in q05["unit05_operational_frames"] for c in frame["q02_carrier_classes"]}
    direct = [
        row for row in q02["matrix"]
        if row["carrier_class"] in allowed
        and row["unit05_role"] == "TARGET_CARRIER"
        and row["unit05_admission_status"].startswith("ADMITTED")
    ]
    assert len(direct) == 94
    assert q03["acceptance"]["subject_agreement_rows"] == 9
    assert q03["acceptance"]["interrogatives_materialized"] is False
    assert q03["acceptance"]["past_be_materialized"] is False
    assert q03["acceptance"]["existential_there_be_materialized"] is False
    assert q03["acceptance"]["present_continuous_mastery_materialized"] is False
    assert q04["acceptance"]["new_surface_count"] == 66
    assert q04["acceptance"]["cumulative_distinct_chunk_surface_count"] == 156
    assert [row["frame_id"] for row in q05["unit05_operational_frames"]] == r["generation_authority"]["q05_frame_ids"]
    assert q05["q06_primary_generation_routing"]["predecessor_sentence_pool_for_dedup"] == 26610


def test_full_predecessor_dedup_receipt_is_complete_and_private_safe():
    d = report()["predecessor_dedup_receipt"]
    assert d["full_replay_performed"] is True
    assert d["source_rows"] == {"U01":3805,"U02":3726,"U03":18983,"U04":96}
    assert sum(d["source_rows"].values()) == 26610
    assert d["candidate_collision_count"] == 100
    assert d["candidate_exact_collision_count"] == 54
    assert d["candidate_normalized_only_collision_count"] == 46
    assert d["candidate_collision_by_unit"] == {"U01":2,"U02":0,"U03":98,"U04":0}
    assert d["semantically_approved_reuse_count"] == 94
    assert d["approved_reuse_exact_count"] == 52
    assert d["approved_reuse_normalized_only_count"] == 42
    assert d["new_after_full_dedup_and_semantic_admission_count"] == 761
    assert d["private_source_evidence"]["U01"]["private_sentence_bodies_committed"] is False
    assert d["private_source_evidence"]["U01"]["private_sentence_fingerprints_committed"] is False
    assert d["private_source_evidence"]["U03"]["private_sentence_bodies_committed"] is False
    assert d["private_source_evidence"]["U03"]["private_sentence_fingerprints_committed"] is False
    assert d["private_source_evidence"]["U03"]["dedup_only_not_semantic_authority"] is True
    assert d["repository_reconstructable_sources"]["U04"]["exact_or_normalized_collision_count"] == 0


def test_gpt56_semantic_review_counts_and_low_quality_guard():
    r = report()
    s = r["semantic_review"]
    assert s["review_model"] == "GPT-5.6 Sol"
    assert (s["reviewed_candidate_count"],s["approved_count"],s["context_bound_approved_count"]) == (884,377,478)
    assert (s["deferred_count"],s["rejected_count"],s["usable_count"]) == (12,17,855)
    excluded = r["excluded_candidates"]
    assert Counter(row["decision"] for row in excluded) == {"DEFER":12,"REJECT":17}
    assert {row["reason_code"] for row in excluded if row["decision"] == "DEFER"} == {"TRIVIAL_PERSON_IDENTITY_LOW_PEDAGOGICAL_UTILITY"}
    assert {row["reason_code"] for row in excluded if row["decision"] == "REJECT"} == {"HUMAN_PERSON_NEGATION_NOT_A1_PEDAGOGICALLY_NATURAL"}
    assert all(row["frame_id"].startswith("U05-BF-NP-") for row in excluded)


def test_materialized_assets_are_unique_and_all_six_frames_are_covered():
    r = report()
    rows = usable(r)
    assert len(rows) == 855
    assert len(r["reuse_bindings"]) == 94
    assert len(r["new_sentence_assets"]) == 761
    assert len({row["normalized_text"] for row in rows}) == 855
    assert len({row["sentence_id"] for row in r["new_sentence_assets"]}) == 761
    counts = Counter(row["frame_id"] for row in rows)
    assert dict(sorted(counts.items())) == r["coverage"]["frame_counts"]
    assert set(counts) == {
        "U05-BF-NP-AFF","U05-BF-ADJ-AFF","U05-BF-PLACE-AFF",
        "U05-BF-NP-NEG","U05-BF-ADJ-NEG","U05-BF-PLACE-NEG",
    }
    assert all(count > 0 for count in counts.values())
    subject_counts = Counter(row["subject_class"] for row in rows)
    assert set(subject_counts) == {
        "I","you","he","she","it","we","they",
        "ADMITTED_SINGULAR_NOUN_PHRASE","ADMITTED_PLURAL_NOUN_PHRASE",
    }
    assert all(count > 0 for count in subject_counts.values())


def test_contraction_policy_and_place_relation_scope():
    rows = usable(report())
    direct_relations = {"in","inside","on","near","at","under","behind","between"}
    place = [row for row in rows if "-PLACE-" in row["frame_id"]]
    assert {row["relation_surface"] for row in place} == direct_relations
    assert all(row["semantic_admission_class"] == "CONTEXT_BOUND_APPROVE" for row in place)
    assert all(row["requires_context_binding"] is True for row in place)
    assert not any(row["relation_surface"] in {"next to","in front of"} for row in place)
    affirmative_contracted = [row for row in rows if row["polarity"] == "AFFIRMATIVE" and row["surface_variant"] == "CONTRACTED"]
    assert affirmative_contracted
    assert all(row["subject_class"] in {"I","you","he","she","it","we","they"} for row in affirmative_contracted)
    for frame in {"U05-BF-NP-NEG","U05-BF-ADJ-NEG","U05-BF-PLACE-NEG"}:
        variants = {row["surface_variant"] for row in rows if row["frame_id"] == frame}
        assert "FULL" in variants and "CONTRACTED" in variants


def test_no_later_grammar_leaks_and_boundaries_remain_locked():
    r = report()
    texts = [row["text"] for row in usable(r)]
    assert all("?" not in text for text in texts)
    assert all(not re.search(r"\b(?:was|were)\b", text, flags=re.I) for text in texts)
    assert all(not re.search(r"\bthere\s+(?:is|are)\b", text, flags=re.I) for text in texts)
    assert all(not re.search(r"\b(?:am|is|are)\s+[A-Za-z]+ing\b", text) for text in texts)
    b = r["q06_boundaries"]
    for key in (
        "unit04_reader360_used_as_unit05_authority","unit05_reader360_materialized","scene_materialized",
        "communicative_functions_materialized","questionbank_materialized","forms_materialized",
        "be_interrogative_target_sentence_allowed","past_be_target_sentence_allowed",
        "existential_there_be_target_sentence_allowed","present_continuous_target_sentence_allowed",
        "a2_a2plus_unlocked",
    ):
        assert b[key] is False


def test_q06_acceptance_and_next_step():
    r = report()
    a = r["acceptance"]
    assert a["surface_candidate_count"] == 884
    assert a["semantic_review_usable_count"] == 855
    assert a["validated_predecessor_reuse_binding_count"] == 94
    assert a["unit05_new_admitted_sentence_asset_count"] == 761
    assert a["deferred_count"] == 12
    assert a["rejected_count"] == 17
    assert a["full_predecessor_dedup_row_count"] == 26610
    assert a["full_predecessor_collision_count"] == 100
    assert a["usable_unique_normalized_text_count"] == 855
    assert a["status"] == "PASS_A1FS_V1_U05Q06_SENTENCE_ASSET_PRODUCTION_AND_SEMANTIC_ADMISSION"
    assert r["next_short_step"] == "A1FS-V1-U05Q07_Unit05LifeSkillMicroSceneMaterializationAndSentenceBinding"
