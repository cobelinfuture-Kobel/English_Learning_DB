import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
Q04_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u04_q04_place_chunk_authority.json"
Q03_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u04_q03_place_relation_form_meaning_authority.json"


def _q04():
    return json.loads(Q04_PATH.read_text(encoding="utf-8"))


def _q03():
    return json.loads(Q03_PATH.read_text(encoding="utf-8"))


def _norm(surface):
    return " ".join(surface.casefold().split())


def _new_target_surfaces(data):
    return [surface for group in data["target_relation_chunk_groups"] for surface in group["new_surfaces"]]


def _new_support_surfaces(data):
    return [surface for group in data["yle_safe_support_chunk_groups"] for surface in group["new_surfaces"]]


def test_u04_q04_binds_to_merged_q03_and_preserves_static_place_scope():
    data = _q04()
    assert data["status"] == "PASS_Q04_UNIT04_PLACE_CHUNK_AUTHORITY_AND_CUMULATIVE_DEDUP"
    assert data["unit_id"] == "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
    assert data["q03_merge_sha"] == "660d3bcf57feec6ac1538783fd8ebe48cc91f336"
    assert _q03()["acceptance"]["status"] == "PASS_Q03_UNIT04_PLACE_RELATION_FORM_MEANING_AUTHORITY"
    assert data["counting_policy"]["prior_cumulative_chunks_are_reusable_floor_not_ceiling"] is True


def test_u04_q04_prior_baseline_is_exact_unit03_50_with_five_place_reuse_surfaces():
    data = _q04()
    prior = data["prior_chunk_baseline"]
    assert prior["source_sha256"] == "45cda8023e49bd99dd1719d5697241c20ba219f4cf66dfe09bd253413e41cd18"
    assert prior["cumulative_distinct_surface_rows"] == 50
    assert prior["direct_or_instructional_rows"] == 49
    assert prior["receptive_only_rows"] == 1
    assert prior["unit03_native_rows"] == 0
    reuse = {(row["surface"], row["relation"]) for row in prior["prior_exact_place_chunk_reuse"]}
    assert reuse == {
        ("in the bag", "in"),
        ("in the classroom", "in"),
        ("near the door", "near"),
        ("on the desk", "on"),
        ("at the park", "at"),
    }


def test_u04_q04_covers_all_eight_q03_target_relations_with_exact_counts():
    data = _q04()
    groups = {group["relation_surface"]: group for group in data["target_relation_chunk_groups"]}
    assert set(groups) == {"in", "inside", "on", "near", "at", "under", "behind", "between"}
    assert all(len(group["new_surfaces"]) == 4 for group in groups.values())
    assert sum(len(group["new_surfaces"]) for group in groups.values()) == 32
    assert data["relation_coverage"] == {
        "in": {"prior_exact_reuse": 2, "unit04_new_target": 4, "target_pool_total": 6},
        "inside": {"prior_exact_reuse": 0, "unit04_new_target": 4, "target_pool_total": 4},
        "on": {"prior_exact_reuse": 1, "unit04_new_target": 4, "target_pool_total": 5},
        "near": {"prior_exact_reuse": 1, "unit04_new_target": 4, "target_pool_total": 5},
        "at": {"prior_exact_reuse": 1, "unit04_new_target": 4, "target_pool_total": 5},
        "under": {"prior_exact_reuse": 0, "unit04_new_target": 4, "target_pool_total": 4},
        "behind": {"prior_exact_reuse": 0, "unit04_new_target": 4, "target_pool_total": 4},
        "between": {"prior_exact_reuse": 0, "unit04_new_target": 4, "target_pool_total": 4},
    }
    assert sum(row["target_pool_total"] for row in data["relation_coverage"].values()) == 37


def test_u04_q04_between_chunks_obey_two_distinct_landmark_surface_shape():
    data = _q04()
    between = next(group for group in data["target_relation_chunk_groups"] if group["relation_surface"] == "between")
    assert between["two_distinct_landmarks_required"] is True
    assert len(between["new_surfaces"]) == 4
    assert all(surface.startswith("between the ") and " and " in surface for surface in between["new_surfaces"])


def test_u04_q04_yle_safe_support_is_explicitly_support_only_not_q03_target_expansion():
    data = _q04()
    support = {group["support_pattern"]: group for group in data["yle_safe_support_chunk_groups"]}
    assert set(support) == {"next to", "in front of"}
    assert support["next to"]["parent_canonical_chunk_id"] == "EVP_CHUNK_000149"
    assert support["in front of"]["parent_canonical_chunk_id"] == "EVP_CHUNK_001596"
    assert all(group["yle_stage"] == "PRE_A1_STARTERS" for group in support.values())
    assert all(group["evp_level"] == "A2" for group in support.values())
    assert all(group["q03_target_relation"] is False for group in support.values())
    assert sum(len(group["new_surfaces"]) for group in support.values()) == 8
    assert data["counting_policy"]["support_chunks_do_not_expand_q03_simple_preposition_target"] is True


def test_u04_q04_exercises_all_five_q02_yle_extensions_in_real_chunks():
    data = _q04()
    all_new = _new_target_surfaces(data) + _new_support_surfaces(data)
    required = data["carrier_authority"]["yle_extension_carriers_that_must_be_exercised"]
    assert required == ["playground", "bus stop", "library", "market", "sports centre"]
    for carrier in required:
        assert any(carrier in surface for surface in all_new)
    assert data["carrier_authority"]["new_global_vocabulary_identity_count"] == 0


def test_u04_q04_new_surfaces_are_exact_unique_and_do_not_readd_declared_prior_place_chunks():
    data = _q04()
    target = _new_target_surfaces(data)
    support = _new_support_surfaces(data)
    all_new = target + support
    assert len(target) == 32
    assert len(support) == 8
    assert len(all_new) == 40
    assert len({_norm(surface) for surface in all_new}) == 40
    prior_place = {_norm(row["surface"]) for row in data["prior_chunk_baseline"]["prior_exact_place_chunk_reuse"]}
    assert prior_place.isdisjoint({_norm(surface) for surface in all_new})
    dedup = data["dedup_result"]
    assert dedup["within_unit04_duplicate_count"] == 0
    assert dedup["prior_vs_unit04_overlap_count"] == 0
    assert dedup["cumulative_distinct_surfaces"] == 90


def test_u04_q04_does_not_activate_directional_or_a2_target_grammar():
    data = _q04()
    all_target = {_norm(surface) for surface in _new_target_surfaces(data)}
    assert all(not surface.startswith("from ") for surface in all_target)
    assert all(not surface.startswith("into ") for surface in all_target)
    assert all(not surface.startswith("to ") for surface in all_target)
    assert all(not surface.startswith("next to ") for surface in all_target)
    assert all(not surface.startswith("in front of ") for surface in all_target)
    assert data["q04_boundaries"]["motion_directional_surfaces_activated"] is False
    assert data["q04_boundaries"]["a2_unlocked"] is False


def test_u04_q04_delta_vs_unit03_is_explicit_and_noninflated():
    data = _q04()
    delta = data["delta_vs_unit03"]
    assert delta["prior_cumulative_chunk_surfaces"] == 50
    assert delta["prior_exact_place_relation_chunk_reuse"] == 5
    assert delta["unit04_new_target_chunk_surfaces"] == 32
    assert delta["unit04_new_yle_support_chunk_surfaces"] == 8
    assert delta["unit04_new_chunk_surfaces_total"] == 40
    assert delta["unit04_new_global_canonical_chunk_identities"] == 0
    assert delta["unit04_target_place_chunk_pool_after_reuse"] == 37
    assert delta["unit04_place_support_chunk_pool"] == 8
    assert delta["unit04_place_focused_chunk_pool_total"] == 45
    assert delta["cumulative_chunk_surfaces_after_unit04_q04"] == 90
    assert delta["prior_cumulative_sentence_assets"] == 26514
    assert delta["sentence_asset_delta"] == "NOT_YET_MATERIALIZED_Q06"


def test_u04_q04_preserves_q05_to_q10_materialization_boundaries():
    data = _q04()
    assert data["q04_boundaries"] == {
        "sentence_frames_materialized": False,
        "sentence_assets_materialized": False,
        "scenes_materialized": False,
        "communicative_functions_materialized": False,
        "questionbank_materialized": False,
        "forms_materialized": False,
        "motion_directional_surfaces_activated": False,
        "a2_unlocked": False,
    }
    assert data["acceptance"]["new_target_chunk_surface_count"] == 32
    assert data["acceptance"]["new_support_chunk_surface_count"] == 8
    assert data["acceptance"]["cumulative_distinct_chunk_surface_count"] == 90
    assert data["next_short_step"] == "A1FS-V1-U04Q05_Unit04CoreSentenceFrameAuthority"
