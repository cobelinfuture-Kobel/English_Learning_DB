from __future__ import annotations

from collections import Counter, defaultdict

from ulga.builders import build_a1fs_v1_u05_q06_sentence_assets as q06_builder
from ulga.builders import build_a1fs_v1_u05_q07_life_skill_micro_scenes as builder


def report():
    return builder.build_report()


def q06_identity(row):
    return str(row.get("sentence_id") or row.get("binding_id") or "")


def test_q07_binds_every_q06_context_required_sentence_and_only_those():
    q06 = q06_builder.build_report()
    r = report()
    q06_rows = [*q06["reuse_bindings"], *q06["new_sentence_assets"]]
    context_ids = {q06_identity(row) for row in q06_rows if row["requires_context_binding"] is True}
    standalone_ids = {q06_identity(row) for row in q06_rows if row["requires_context_binding"] is False}
    bound_ids = {row["q06_identity"] for row in r["sentence_scene_bindings"]}

    assert len(q06_rows) == 855
    assert len(context_ids) == 478
    assert len(standalone_ids) == 377
    assert len(bound_ids) == 478
    assert bound_ids == context_ids
    assert not (bound_ids & standalone_ids)
    assert r["coverage"]["q06_unbound_context_required_sentence_count"] == 0
    assert r["acceptance"]["q06_context_required_sentence_bindings"] == "478/478"


def test_q07_groups_surface_variants_by_semantic_truth_instead_of_duplicate_scenes():
    r = report()
    scenes = r["micro_scenes"]
    bindings = r["sentence_scene_bindings"]
    assert 0 < len(scenes) < len(bindings) == 478
    assert r["coverage"]["unit05_scene_instance_count"] == len(scenes)
    assert r["coverage"]["surface_variant_scene_reuse_count"] == 478 - len(scenes)

    by_scene = defaultdict(list)
    for row in bindings:
        by_scene[row["scene_ref_id"]].append(row)
    assert set(by_scene) == {row["scene_ref_id"] for row in scenes}
    assert any(len(rows) > 1 for rows in by_scene.values())

    scene_by_id = {row["scene_ref_id"]: row for row in scenes}
    for scene_id, rows in by_scene.items():
        scene = scene_by_id[scene_id]
        assert {row["frame_id"] for row in rows} == {scene["semantic_frame_id"]}
        assert {row["polarity"] for row in rows} == {scene["polarity"]}
        assert set(row["surface_variant"] for row in rows) == set(scene["surface_variants"])
        assert set(row["sentence_text"] for row in rows) == set(scene["bound_sentence_texts"])


def test_q07_reuses_only_governed_scene_family_ontology():
    r = report()
    prior = r["prior_scene_authority"]
    governed = set(prior["governed_scene_families"])
    assert len(governed) == prior["governed_scene_family_count"] == 17
    assert prior["new_global_scene_family_count"] == 0
    assert prior["new_global_canonical_scene_identity_count"] == 0
    assert 0 < r["coverage"]["used_scene_family_count"] <= 17
    assert {row["scene_family"] for row in r["micro_scenes"]}.issubset(governed)
    assert all(row["canonical_scene_scope"] == "UNIT05_LOCAL_AUTHORITATIVE_INSTANCE" for row in r["micro_scenes"])
    assert r["authority_refs"]["scene_family_ontology_role"] == "GOVERNED_FAMILY_ONTOLOGY_ONLY_NOT_UNIT05_CONTENT_AUTHORITY"


def test_q07_negative_truth_never_uses_absence_as_proof():
    r = report()
    negative = [row for row in r["micro_scenes"] if row["polarity"] == "NEGATIVE"]
    assert negative
    for scene in negative:
        truth = scene["truth_evidence_spec"]
        guard = scene["answerability_guard"]
        assert truth["explicit_positive_alternative_required_for_negative"] is True
        assert truth["negation_proof_by_absence_allowed"] is False
        assert truth["target_sentence_may_be_used_as_scene_prompt"] is False
        assert guard["negative_truth_requires_positive_contrast_evidence"] is True
        assert guard["learner_visible_target_sentence_used_as_scene_prompt"] is False


def test_q07_pronoun_context_rows_have_explicit_referent_anchor():
    r = report()
    pronoun_scenes = [row for row in r["micro_scenes"] if row["subject_class"] in {"he", "she", "it", "they"}]
    assert pronoun_scenes
    for scene in pronoun_scenes:
        ref = scene["referent_binding_spec"]
        assert ref["required"] is True
        assert ref["antecedent_must_appear_before_or_with_pronoun_use"] is True
        assert ref["anchor_label"]


def test_q07_place_scene_truth_keeps_only_q05_direct_relations():
    r = report()
    place = [row for row in r["micro_scenes"] if "-PLACE-" in row["semantic_frame_id"]]
    assert place
    assert {row["relation_surface"] for row in place} == {"in","inside","on","near","at","under","behind","between"}
    assert all(row["truth_evidence_spec"]["relation_surface"] in {"in","inside","on","near","at","under","behind","between"} for row in place)
    assert not any(row["relation_surface"] in {"next to","in front of"} for row in place)


def test_q07_coverage_counts_match_materialized_rows():
    r = report()
    scenes = r["micro_scenes"]
    bindings = r["sentence_scene_bindings"]
    c = r["coverage"]

    assert c["q06_usable_sentence_supply_count"] == 855
    assert c["q06_context_required_sentence_surface_count"] == 478
    assert c["q06_standalone_sentence_surface_count"] == 377
    assert c["sentence_scene_binding_count"] == 478
    assert sum(c["used_scene_family_counts"].values()) == len(scenes)
    assert sum(c["binding_frame_counts"].values()) == 478
    assert sum(c["binding_polarity_counts"].values()) == 478
    assert Counter(row["scene_family"] for row in scenes) == Counter(c["used_scene_family_counts"])
    assert Counter(row["frame_id"] for row in bindings) == Counter(c["binding_frame_counts"])
    assert Counter(row["polarity"] for row in bindings) == Counter(c["binding_polarity_counts"])


def test_q07_policy_bound_candidate_and_approved_transition():
    candidate = builder.build_candidate()
    approved = builder.admit_candidate(candidate)
    assert candidate["artifact_role"] == "CANDIDATE_JSON"
    assert candidate["producer_id"] == builder.TASK_ID
    assert candidate["level_scope"] == ["A1"]
    assert candidate["payload"]["coverage"]["sentence_scene_binding_count"] == 478
    assert approved["artifact_role"] == "APPROVED_CANONICAL_JSON"
    assert approved["admission"]["status"] == "APPROVED"
    assert approved["admission"]["decision_ref"] == builder.DECISION_REF
    assert approved["payload"] == candidate["payload"]
    assert approved["content_governance"]["a2_unlocked"] is False


def test_q07_boundaries_and_next_step():
    r = report()
    b = r["q07_boundaries"]
    for key in (
        "q06_sentence_assets_mutated",
        "unit04_scene_content_used_as_unit05_generation_authority",
        "unit04_reader360_used_as_unit05_authority",
        "global_canonical_scene_library_rewritten",
        "communicative_functions_materialized",
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
        assert b[key] is False
    assert r["next_short_step"] == "A1FS-V1-U05Q08_Unit05CommunicativeFunctionAuthority"
