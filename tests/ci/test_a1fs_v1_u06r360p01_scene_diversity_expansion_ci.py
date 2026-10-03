from functools import lru_cache
import json
from pathlib import Path

from product.a1fs_v1_2_1 import u06r360p01_scene_diversity_expansion as p01r1
from product.a1fs_v1_2_1 import u06r360p01_natural360_source_projection as p01

ROOT=Path(__file__).resolve().parents[2]
REUSABLE=ROOT/"ulga/contracts/a1fs_v1_reusable_unit_production_contract.json"

@lru_cache(maxsize=1)
def report():
    return p01r1.build_unit06_scene_diversity_expansion()

def test_u06_scene_diversity_is_strictly_greater_than_unit05_and_uses_default_increment():
    r=report()
    assert r["status"]==p01r1.STATUS
    assert r["predecessor_distinct_scene_instance_count"]>0
    assert r["current_distinct_scene_instance_count"]>r["predecessor_distinct_scene_instance_count"]
    assert r["coverage"]["scene_growth_over_predecessor"]==24
    assert r["current_distinct_scene_instance_count"]==r["predecessor_distinct_scene_instance_count"]+24
    assert r["successor_required_minimum_scene_instance_count"]==r["current_distinct_scene_instance_count"]+1
    assert r["successor_default_target_scene_instance_count"]==r["current_distinct_scene_instance_count"]+24

def test_u06_scene_diversity_preserves_all_182_chunks_62_verbs_and_12_scene_families():
    r=report(); scenes=r["reader360_local_scene_instances"]
    assert r["coverage"]["functional_chunk_scene_coverage"]=="182/182"
    assert r["coverage"]["source_verb_scene_coverage"]=="62/62"
    assert r["coverage"]["scene_family_count"]==12
    assert len({x["functional_chunk_surface"] for x in scenes})==182
    assert len({x["base_verb"] for x in scenes})==62
    assert len({x["scene_family"] for x in scenes})==12
    assert all(value>0 for value in r["coverage"]["scene_family_counts"].values())

def test_u06_scene_instances_are_semantically_distinct_not_name_only_variants():
    r=report(); scenes=r["reader360_local_scene_instances"]
    assert len(scenes)==r["current_distinct_scene_instance_count"]
    assert len({x["scene_instance_id"] for x in scenes})==len(scenes)
    assert len({x["semantic_scene_key_sha256"] for x in scenes})==len(scenes)
    assert r["semantic_distinctness"]["selected_semantic_key_distinct_count"]==len(scenes)
    assert r["semantic_distinctness"]["person_name_only_variation_counted_as_distinct"] is False
    assert r["semantic_distinctness"]["pronoun_only_variation_counted_as_distinct"] is False
    for row in scenes:
        assert row["authoring_model"]=="GPT-5.6 Sol"
        assert row["scene_instance_scope"]=="READER360_LOCAL_SCENE_INSTANCE"
        assert row["scene_diversity_policy_id"]==p01r1.SCENE_DIVERSITY_POLICY_ID
        assert row["learner_facing_english_materialized"] is False

def test_u06_scene_diversity_is_bound_to_all_360_future_current360_slots():
    r=report(); bindings=r["reader360_authoring_slot_scene_bindings"]
    assert len(bindings)==360
    assert r["coverage"]["reader360_authoring_slot_scene_binding_count"]==360
    assert len({x["episode_slot_id"] for x in bindings})==360
    assert len({x["target_current360_episode_id"] for x in bindings})==360
    ids={x["scene_instance_id"] for x in r["reader360_local_scene_instances"]}
    assert all(x["primary_scene_instance_id"] in ids for x in bindings)
    assert all(x["learner_facing_episode_not_materialized"] is True for x in bindings)

def test_reusable_contract_marks_monotonic_scene_rule_for_future_units():
    c=json.loads(REUSABLE.read_text(encoding="utf-8"))
    p=c["common_contract"]["scene_diversity"]
    assert p["policy_id"]==p01r1.SCENE_DIVERSITY_POLICY_ID
    assert p["hard_progression_rule"]=="CURRENT_UNIT_DISTINCT_SCENE_INSTANCE_COUNT_GT_PREDECESSOR_UNIT_DISTINCT_SCENE_INSTANCE_COUNT"
    assert p["default_minimum_increment"]==24
    assert p["reader360_episode_count_may_remain_constant"]==360
    assert p["reader360_scene_reservoir_may_exceed_episode_count"] is True
    assert p["scene_family_taxonomy_growth_required"] is False
    assert "scene_diversity_authority_for_successor" in p["successor_handoff_required_fields"]
    assert "current_distinct_scene_instance_count" in p["successor_handoff_required_fields"]
    assert "successor_required_minimum_scene_instance_count" in p["successor_handoff_required_fields"]

def test_u06_p01_now_routes_through_scene_diversity_before_current360():
    r=p01.build_unit06_natural360_source_projection()
    assert r["next_short_step"]==p01r1.TASK_ID
    route=r["route_lock"]["approved_route"]
    assert route.index("U06_READER360_SCENE_DIVERSITY_EXPANSION")<route.index("U06_CURRENT360")

def test_u06_scene_diversity_keeps_future_scope_closed():
    r=report()
    assert all(value is False for value in r["scope_safety"].values())
    assert r["authoring_contract"]["python_may_author_learner_facing_english"] is False
    assert r["authoring_contract"]["semantic_scene_count_must_increase_over_predecessor"] is True
    assert r["next_short_step"]==p01r1.NEXT_SHORT_STEP
