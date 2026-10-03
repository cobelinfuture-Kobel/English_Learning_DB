from functools import lru_cache
import json
from pathlib import Path

from product.a1fs_v1_2_1 import u06r360p01_natural360_source_projection as p01
from product.a1fs_v1_2_1 import u06r360p02a_current360_representative_pilot as p02a

ROOT=Path(__file__).resolve().parents[2]

@lru_cache(maxsize=1)
def report():
    return p02a.build_report()

def test_u06_p02a_pilot_is_variable_length_and_not_five_sentence_locked():
    r=report()
    assert r["status"]==p02a.STATUS
    assert r["pilot_count"]==12
    assert r["sentence_count_min"]>=4
    assert r["sentence_count_max"]<=8
    assert len(r["sentence_count_distribution"])>=3
    assert r["sentence_count_distribution"].get("5",0)<12
    assert r["fixed_sentence_count"] is False

def test_u06_p02a_scene_first_support_and_no_chunk_stuffing():
    r=report()
    assert r["scene_first_support"] is True
    assert r["chunk_stuffing_forbidden"] is True
    assert r["support_sentence_requires_chunk_lineage"] is False
    assert r["full360_chunk_coverage_is_corpus_level"] is True
    assert r["target_chunk_count_min"]>=1
    assert r["target_chunk_count_max"]<=2

def test_u06_p02a_has_12_representative_scene_families_and_unique_passages():
    r=report()
    assert r["scene_family_count"]==12
    assert r["unique_paragraph_count"]==12
    assert len({x["paragraph"] for x in r["episodes"]})==12

def test_u06_p01_no_longer_forces_every_preassigned_chunk_into_each_episode():
    r=p01.build_unit06_natural360_source_projection()
    for slot in r["episode_authoring_slots"]:
        c=slot["authoring_constraints"]
        assert c["realize_every_required_chunk_naturally"] is False
        assert c["required_functional_chunk_surfaces_role"]=="CORPUS_COVERAGE_ROUTING_TARGET_NOT_EPISODE_MANDATE"
        assert c["scene_first_natural_support_over_chunk_stuffing"] is True
        assert c["full_182_chunk_coverage_required_at_corpus_level"] is True

def test_reusable_contract_carries_current360_naturalness_rule_to_future_units():
    c=json.loads((ROOT/"ulga/contracts/a1fs_v1_reusable_unit_production_contract.json").read_text(encoding="utf-8"))
    p=c["common_contract"]["reader360_current360"]
    assert p["policy_id"]=="A1FS_CURRENT360_NATURAL_PASSAGE_V1"
    assert p["natural_length_policy"]["fixed_sentence_count_forbidden"] is True
    assert p["support_policy"]["scene_first"] is True
    assert p["support_policy"]["cumulative_support_must_be_natural"] is True
    assert p["support_policy"]["chunk_stuffing_forbidden"] is True
    assert p["support_policy"]["per_episode_preassigned_chunk_surface_realization_required"] is False
    assert p["pilot_policy"]["representative_human_review_required_before_full360_promotion"] is True
