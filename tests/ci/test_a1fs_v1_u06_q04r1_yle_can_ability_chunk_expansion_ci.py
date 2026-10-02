from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q04r1_yle_can_ability_chunk_expansion.json"
Q04 = ROOT / "ulga" / "contracts" / "a1fs_v1_u06_q04_can_ability_chunk_authority.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _norm(value: str) -> str:
    return " ".join(value.casefold().split())


def test_u06_q04r1_yle_can_ability_expansion() -> None:
    data = _load(ARTIFACT)
    q04 = _load(Q04)

    assert data["status"] == "PASS_A1FS_V1_U06Q04R1_YLE_PREA1_A1_CAN_ABILITY_EXPANSION"
    assert data["unit_number"] == 6
    assert data["unit_id"] == "GRAMMAR_CAN_STATEMENT"
    assert data["source_main_sha"] == "aeeddb374a73e3a1b0ebf43c130e66ed8e2f8e87"
    assert q04["status"] == "PASS_A1FS_V1_U06Q04_CAN_ABILITY_CHUNK_AUTHORITY_AND_CUMULATIVE_DEDUP"

    source = data["official_cambridge_source"]
    counts = source["recovery_counts"]
    assert counts == {
        "starters_irregular": 43,
        "starters_regular": 37,
        "starters_total": 80,
        "movers_irregular": 24,
        "movers_regular": 38,
        "movers_new_total": 62,
        "recovered_source_entry_total": 142,
    }
    inv = source["recovered_inventory"]
    assert sum(len(inv[k]) for k in inv) == 142
    assert source["source_scope_used"] == ["Pre A1 Starters", "A1 Movers"]
    assert source["source_scope_excluded"] == ["A2 Flyers"]

    triage = data["ability_semantic_triage"]
    assert triage["direct_ability_source_entry_count"] == 84
    assert triage["contextual_ability_only_source_entry_count"] == 23
    assert triage["excluded_from_ability_target_source_entry_count"] == 35
    assert 84 + 23 + 35 == 142
    all_source = set(sum(inv.values(), []))
    triaged = (
        set(triage["direct_ability_source_entries"])
        | set(triage["contextual_ability_only_source_entries"])
        | set(triage["excluded_from_ability_target_source_entries"])
    )
    assert triaged == all_source
    assert not (
        set(triage["direct_ability_source_entries"])
        & set(triage["contextual_ability_only_source_entries"])
    )

    bridge = data["canonical_vocabulary_bridge"]
    assert bridge["normalized_single_word_ability_candidate_count"] == 78
    assert bridge["admitted_single_word_verb_count"] == 60
    assert bridge["admitted_from_prea1_count"] == 42
    assert bridge["admitted_from_a1_movers_count"] == 18
    assert bridge["deferred_single_word_count"] == 18
    assert len(bridge["admitted_single_word_verbs"]) == 60
    assert len({row["surface"] for row in bridge["deferred_single_word_verbs"]}) == 18
    assert "video" in {row["surface"] for row in bridge["deferred_single_word_verbs"]}
    assert "put" in {row["surface"] for row in bridge["deferred_single_word_verbs"]}
    assert bridge["a2_lexical_bridge_does_not_unlock_a2_grammar"] is True

    exp = data["q04r1_chunk_expansion"]
    assert exp["subject_can"]["surfaces"] == [
        "I can", "you can", "he can", "she can", "it can", "we can", "they can"
    ]
    assert exp["subject_can"]["surface_count"] == 7

    prior_verbs = {_norm(x) for x in exp["can_base_verb"]["prior_surfaces"]}
    new_verbs = {_norm(x) for x in exp["can_base_verb"]["newly_admitted_surfaces"]}
    assert len(prior_verbs) == 14
    assert len(new_verbs) == 48
    assert prior_verbs.isdisjoint(new_verbs)
    assert exp["can_base_verb"]["total_surface_count_after_r1"] == 62

    prior_func = {_norm(x) for x in exp["non_scene_functional_chunks"]["prior_exact_overlap_surfaces"]}
    new_func = {_norm(x) for x in exp["non_scene_functional_chunks"]["newly_admitted_surfaces"]}
    assert len(prior_func) == 2
    assert len(new_func) == 28
    assert prior_func.isdisjoint(new_func)
    assert exp["non_scene_functional_chunks"]["total_surface_count_after_r1"] == 41
    assert exp["non_scene_functional_chunks"]["q07_scene_derived_label_prohibited"] is True

    prior_q04 = {
        _norm(surface)
        for group in q04["chunk_groups"]
        for surface in group["surfaces"]
    }
    assert len(prior_q04) == 34
    r1_new = new_verbs | new_func
    assert len(r1_new) == 76
    assert prior_q04.isdisjoint(r1_new)

    dedup = data["cumulative_dedup"]
    assert dedup["predecessor_u01_u05_distinct_surfaces"] == 156
    assert dedup["q04_unit06_surfaces_before_r1"] == 34
    assert dedup["q04r1_new_can_base_verb_surfaces"] == 48
    assert dedup["q04r1_new_functional_surfaces"] == 28
    assert dedup["q04r1_new_surface_delta"] == 76
    assert dedup["unit06_distinct_surfaces_after_r1"] == 110
    assert dedup["course_cumulative_distinct_surfaces_after_r1"] == 266
    assert dedup["within_r1_duplicate_count"] == 0
    assert dedup["prior_vs_r1_overlap_count"] == 0

    multi = data["multiword_source_dispositions"]
    assert set(multi["admitted_source_backed_functional_surfaces"]) == {
        "can take a photo", "can take a picture", "can get dressed",
        "can get undressed", "can dress up",
    }
    assert {row["source_entry"] for row in multi["deferred_source_entries"]} == {
        "pick up", "put on", "take off (i.e. get undressed)"
    }

    scene = data["scene_functional_boundary"]
    assert scene["unit06_native_scene_authority_slot"] == "Q07"
    assert scene["current_status"] == "DEFERRED_UNTIL_Q07_SCENE_AUTHORITY"
    assert scene["q04r1_non_scene_functional_chunks_are_not_scene_derived"] is True
    assert scene["post_q07_backfill_required"] is True

    acceptance = data["acceptance"]
    assert acceptance["official_starters_movers_source_entries_recovered"] == "142/142"
    assert acceptance["seven_subject_can_chunks"] == "7/7"
    assert acceptance["q04r1_new_surface_delta"] == 76
    assert acceptance["unit06_distinct_chunk_surfaces_after_r1"] == 110
    assert acceptance["course_cumulative_distinct_chunk_surfaces_after_r1"] == 266
    assert acceptance["a2_grammar_unlocked"] is False

    assert data["next_short_step"] == "A1FS-V1-U06Q05_Unit06CoreSentenceFrameAuthority"
