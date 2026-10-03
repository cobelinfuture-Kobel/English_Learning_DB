from collections import Counter
from functools import lru_cache

from product.a1fs_v1_2_1 import u06r360p01_natural360_source_projection as p01

@lru_cache(maxsize=1)
def report():
    return p01.build_unit06_natural360_source_projection()

def test_u06_r360_p01_locks_reader360_far_route_and_pauses_premature_pdf():
    r=report()
    assert r["status"]==p01.STATUS
    assert r["route_lock"]["q10_role"]=="PRE_READER360_COVERAGE_BASELINE_ONLY"
    assert r["route_lock"]["q10r1_role"]=="PRE_READER360_LEARNER_PRESENTATION_ACCEPTANCE_ONLY"
    assert r["route_lock"]["old_q10r2_pdf_route_paused"] is True
    assert r["route_lock"]["final_forms_must_follow_reader360_and_far"] is True
    assert r["source_authorities"]["q10_questionbank_item_count"]==300
    assert r["source_authorities"]["q10_form_count"]==10
    assert r["source_authorities"]["q10r1_activity_count"]==300

def test_u06_r360_p01_uses_17_q07_scenes_and_all_182_chunks_exactly_once_in_cluster_authority():
    r=report(); clusters=r["source_clusters"]
    refs=[ref for c in clusters for ref in c["source_scene_refs"]]
    chunks=[x["normalized_surface"] for c in clusters for x in c["functional_chunks"]]
    assert len(refs)==17 and len(set(refs))==17
    assert len(chunks)==182 and len(set(chunks))==182
    assert r["coverage"]["source_scene_assigned_count"]==17
    assert r["coverage"]["distinct_functional_chunk_count"]==182
    assert r["coverage"]["distinct_functional_chunk_slot_coverage"]=="182/182"

def test_u06_r360_p01_adapts_unit05_cluster_assumption_to_unit06_source_shape():
    r=report(); clusters=r["source_clusters"]
    assert len(clusters)==12
    assert r["coverage"]["family_cluster_count"]==11
    assert r["coverage"]["controlled_baseline_cluster_count"]==1
    assert r["coverage"]["cluster_kind_counts"]=={
        "SCENE_FAMILY_CHUNK_RESERVOIR":11,
        "Q04R1_CONTROLLED_CHUNK_RESERVOIR":1,
    }
    controlled=[c for c in clusters if c["cluster_kind"]=="Q04R1_CONTROLLED_CHUNK_RESERVOIR"]
    assert len(controlled)==1
    assert controlled[0]["functional_chunk_count"]==25
    assert controlled[0]["source_scene_count"]==0

def test_u06_r360_p01_materializes_exact_360_authoring_slots_without_learner_english():
    r=report(); slots=r["episode_authoring_slots"]
    assert len(slots)==360
    assert r["coverage"]["episode_slot_count"]==360
    assert r["coverage"]["episodes_per_cluster"]==30
    assert r["coverage"]["discourse_family_count"]==10
    assert r["coverage"]["variation_pass_count"]==3
    assert len({x["episode_slot_id"] for x in slots})==360
    assert len({x["target_current360_episode_id"] for x in slots})==360
    assert set(Counter(x["cluster_id"] for x in slots).values())=={30}
    assert len({x["cluster_id"] for x in slots})==12
    forbidden={"passage","dialogue","dialogue_turns","learner_text","learner_sentence","pattern_families"}
    for row in slots:
        assert not (forbidden & set(row))
        assert row["required_functional_chunk_surfaces"]
        assert row["authoring_constraints"]["author"]=="GPT-5.6 Sol"
        assert row["authoring_constraints"]["new_canonical_sentence_identity_created"] is False
        assert row["authoring_constraints"]["new_global_scene_identity_created"] is False

def test_u06_r360_p01_covers_all_62_q07r1_source_verbs_and_q08_q09_dimensions():
    r=report()
    assert r["coverage"]["q07r1_source_verb_coverage"]=="62/62"
    assert r["coverage"]["communicative_function_coverage"]=="6/6"
    assert r["coverage"]["task_family_coverage"]=="10/10"
    assert r["source_authorities"]["q08_communicative_function_count"]==6
    assert r["source_authorities"]["q09_task_family_count"]==10

def test_u06_r360_p01_all_chunks_are_required_by_at_least_one_authoring_slot():
    r=report()
    cluster_chunks={x["normalized_surface"] for c in r["source_clusters"] for x in c["functional_chunks"]}
    slot_chunks={x for s in r["episode_authoring_slots"] for x in s["required_functional_chunk_surfaces"]}
    assert len(cluster_chunks)==182
    assert slot_chunks==cluster_chunks

def test_u06_r360_p01_keeps_all_future_scope_closed():
    r=report()
    assert all(value is False for value in r["scope_safety"].values())
    a=r["authoring_contract"]
    assert a["python_may_compose_learner_facing_english"] is False
    assert a["new_canonical_sentence_authority_created"] is False
    assert a["new_global_scene_identity_created"] is False
    assert a["can_interrogative_mastery_unlocked"] is False
    assert a["can_negative_mastery_unlocked"] is False
    assert a["permission_request_offer_possibility_can_unlocked"] is False
    assert a["a2_a2plus_unlocked"] is False
    assert r["next_short_step"]==p01.NEXT_SHORT_STEP
