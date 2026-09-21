from __future__ import annotations

from collections import Counter
from pathlib import Path

from product.a1fs_v1_2_1 import u05r360p01_natural360_source_projection as p01


def report():
    return p01.build_unit05_natural360_source_projection()


def test_u05_r360_p01_locks_correct_post_q09_route_and_pauses_old_pdf_path():
    r = report()
    assert r["status"] == p01.STATUS
    assert r["route_lock"]["approved_route"] == [
        "U05_Q01_TO_Q09_CANONICAL_AUTHORITY",
        "U05_NATURAL360_RESERVOIR",
        "U05_CURRENT360",
        "U05_SPOKEN360",
        "U05_PATTERN360",
        "U05_CONTEXTUAL_ACTIVE_RUNTIME",
        "U05_20_FORMS_X_40",
        "U05_LEARNER_PDF_AFTER_RUNTIME_CUTOVER",
    ]
    assert r["route_lock"]["existing_q10_q10r1_q10r2_role"] == "PRE_CUTOVER_BASELINE_ONLY"
    assert r["route_lock"]["actual_pdf_path_paused_until_contextual_runtime_cutover"] is True
    assert r["source_authorities"]["q10_runtime_role"] == "PRE_CUTOVER_BASELINE_ONLY"
    assert r["source_authorities"]["q10_questionbank_item_count"] == 800
    assert r["source_authorities"]["q10_form_count"] == 20


def test_u05_r360_p01_uses_only_unit05_content_authority_and_unit04_alignment_only():
    r = report()
    alignment = r["unit04_alignment"]
    assert alignment["role"] == "ARCHITECTURE_AND_ACCEPTANCE_ALIGNMENT_ONLY"
    assert alignment["content_authority_consumed"] is False
    assert alignment["learner_sentence_consumed"] is False
    assert alignment["scene_content_consumed"] is False
    assert alignment["reader_entry_consumed"] is False

    source = Path(p01.__file__).read_text(encoding="utf-8")
    assert "from product.a1fs_v1_2_1 import u04" not in source
    assert "import u04neb02" not in source
    assert "import u04fsv2" not in source
    assert r["authoring_contract"]["source_content_authority"] == "UNIT05_Q06_Q07_Q08_Q09_ONLY"
    assert r["authoring_contract"]["unit04_content_authority_consumed"] is False


def test_u05_r360_p01_partitions_every_q07_scene_exactly_once_into_36_clusters():
    r = report()
    clusters = r["source_clusters"]
    assert len(clusters) == 36
    assert r["coverage"]["source_cluster_count"] == 36
    assert r["coverage"]["source_scene_count"] > 36
    assert r["coverage"]["source_scene_assigned_count"] == r["coverage"]["source_scene_count"]

    refs = [ref for cluster in clusters for ref in cluster["source_scene_refs"]]
    assert len(refs) == r["coverage"]["source_scene_count"]
    assert len(set(refs)) == len(refs)

    for cluster in clusters:
        assert cluster["source_scene_count"] == len(cluster["source_scene_refs"])
        assert cluster["source_scene_count"] == len(cluster["candidate_truth_facts"])
        assert cluster["source_scene_count"] > 0
        assert {row["scene_family"] for row in cluster["candidate_truth_facts"]} == {
            cluster["scene_family"]
        }
        assert {row["medium_setting"] for row in cluster["candidate_truth_facts"]} == {
            cluster["medium_setting"]
        }


def test_u05_r360_p01_materializes_exact_360_authoring_slots_not_learner_language():
    r = report()
    slots = r["episode_authoring_slots"]
    assert len(slots) == 360
    assert r["coverage"]["episode_slot_count"] == 360
    assert r["coverage"]["episodes_per_cluster"] == 10
    assert r["coverage"]["discourse_family_count"] == 10
    assert len({row["episode_slot_id"] for row in slots}) == 360
    assert len({row["target_current360_episode_id"] for row in slots}) == 360

    per_cluster = Counter(row["cluster_id"] for row in slots)
    assert set(per_cluster.values()) == {10}
    assert len(per_cluster) == 36

    forbidden_learner_fields = {
        "passage",
        "dialogue",
        "dialogue_turns",
        "learner_text",
        "learner_sentence",
        "pattern_families",
    }
    for row in slots:
        assert not (forbidden_learner_fields & set(row))
        assert row["authoring_constraints"]["author"] == "GPT-5.6 Sol"
        assert row["authoring_constraints"]["source_scene_lineage_required"] is True
        assert row["authoring_constraints"]["source_q06_lineage_required"] is True
        assert row["authoring_constraints"]["do_not_copy_unit04_learner_content"] is True


def test_u05_r360_p01_preserves_full_unit05_semantic_coverage_for_authoring():
    r = report()
    coverage = r["coverage"]
    assert coverage["frame_coverage"] == "6/6"
    assert coverage["polarity_coverage"] == "2/2"
    assert coverage["subject_class_coverage"] == "9/9"
    assert coverage["direct_place_relation_coverage"] == "8/8"
    assert coverage["communicative_function_coverage"] == "7/7"
    assert coverage["task_family_coverage"] == "10/10"

    source_families = set(coverage["source_scene_family_counts"])
    cluster_families = set(coverage["cluster_scene_family_counts"])
    assert cluster_families == source_families
    assert all(value > 0 for value in coverage["cluster_scene_family_counts"].values())


def test_u05_r360_p01_keeps_negative_truth_and_pronoun_referent_guards_in_source_truths():
    r = report()
    truths = [
        truth
        for cluster in r["source_clusters"]
        for truth in cluster["candidate_truth_facts"]
    ]
    negative = [row for row in truths if row["polarity"] == "NEGATIVE"]
    assert negative
    for row in negative:
        spec = row["truth_evidence_spec"]
        assert spec["explicit_positive_alternative_required_for_negative"] is True
        assert spec["negation_proof_by_absence_allowed"] is False

    pronouns = [
        row for row in truths
        if row["subject_class"] in {"he", "she", "it", "they"}
    ]
    assert pronouns
    for row in pronouns:
        ref = row["referent_binding_spec"]
        assert ref["required"] is True
        assert ref["antecedent_must_appear_before_or_with_pronoun_use"] is True


def test_u05_r360_p01_does_not_promote_old_q10_or_open_future_scope():
    r = report()
    safety = r["scope_safety"]
    assert all(value is False for value in safety.values())
    assert r["authoring_contract"]["be_interrogative_mastery_unlocked"] is False
    assert r["authoring_contract"]["past_be_unlocked"] is False
    assert r["authoring_contract"]["existential_there_be_unlocked"] is False
    assert r["authoring_contract"]["present_continuous_mastery_unlocked"] is False
    assert r["authoring_contract"]["a2_a2plus_unlocked"] is False
    assert r["next_short_step"] == p01.NEXT_SHORT_STEP
