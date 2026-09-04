import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
Q02_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u04_q02_vocabulary_authority.json"
Q01_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u04_q01_place_prepositions_scope_admission.json"


def _q02():
    return json.loads(Q02_PATH.read_text(encoding="utf-8"))


def _q01():
    return json.loads(Q01_PATH.read_text(encoding="utf-8"))


def test_u04_q02_binds_to_merged_q01_and_keeps_a1_place_scope():
    data = _q02()
    assert data["status"] == "PASS_Q02_UNIT04_VOCABULARY_AND_EXACT_SURFACE_ADMISSION"
    assert data["unit_id"] == "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
    assert data["q01_merge_sha"] == "441543281ec9f2ba7157b150a93d44034ba2992b"
    assert _q01()["acceptance"]["status"] == "PASS_Q01_UNIT04_EXACT_GRAMMAR_SCOPE_ADMISSION"
    assert data["q02_boundaries"]["a2_unlocked"] is False


def test_u04_q02_uses_evp_and_yle_as_separate_authority_axes():
    data = _q02()
    policy = data["counting_policy"]
    assert policy["evp_level_and_yle_stage_are_separate_axes"] is True
    assert policy["yle_pre_a1_or_a1_can_override_evp_only_blocking_for_learning_stage_eligibility"] is True
    yle = data["source_authority"]["cambridge_yle"]
    assert yle["role"] == "CHILD_LEARNING_STAGE_AUTHORITY"
    assert yle["official_wordlists"] == [
        "Pre A1 Starters wordlist",
        "A1 Movers wordlist",
        "A2 Flyers wordlist",
    ]
    assert "second vocabulary authority" in yle["canonical_identity_policy"]


def test_u04_q02_static_place_surface_inventory_is_exactly_eight_a1_senses():
    data = _q02()
    rows = data["place_preposition_surface_authority"]["static_place_target_surfaces"]
    assert len(rows) == 8
    assert {row["surface"] for row in rows} == {
        "at", "behind", "between", "in", "inside", "near", "on", "under"
    }
    assert all(row["level"] == "A1" for row in rows)
    assert {row["guideword"] for row in rows} == {
        "PLACE", "BACK", "SPACE", "INSIDE", "CONTAINER", "DISTANCE", "SURFACE", "LOWER POSITION"
    }


def test_u04_q02_delta_separates_exact_reuse_from_new_target_activation():
    data = _q02()
    rows = data["place_preposition_surface_authority"]["static_place_target_surfaces"]
    reuse = {row["surface"] for row in rows if row["unit04_status"] == "REUSE_EXACT_PRIOR_EXPOSURE"}
    new = {row["surface"] for row in rows if row["unit04_status"] == "NEW_ACTIVE_UNIT04_TARGET"}
    assert reuse == {"in", "near", "on", "at"}
    assert new == {"behind", "between", "inside", "under"}
    assert reuse.isdisjoint(new)
    delta = data["delta_vs_unit03"]
    assert delta["unit04_static_place_target_surfaces"] == 8
    assert delta["unit04_static_place_target_surfaces_reuse_exact"] == 4
    assert delta["unit04_static_place_target_surfaces_new_activation"] == 4


def test_u04_q02_defers_a1_directional_surfaces_instead_of_misclassifying_as_a2():
    data = _q02()
    rows = data["place_preposition_surface_authority"]["deferred_current_unit_a1_directional_surfaces"]
    assert {row["surface"] for row in rows} == {"from", "into", "to"}
    assert all(row["level"] == "A1" for row in rows)
    assert all(row["unit04_status"].startswith("DEFERRED_CURRENT_UNIT") for row in rows)
    assert data["acceptance"]["deferred_a1_directional_surface_count"] == 3


def test_u04_q02_expands_life_carriers_with_five_yle_pre_a1_a1_items_without_fake_global_growth():
    data = _q02()
    pool = data["life_skill_place_carrier_pool"]
    words = [word for values in pool["domains"].values() for word in values]
    assert len(words) == 29
    assert len(set(words)) == 29
    assert pool["selected_carrier_count"] == 29
    assert pool["prior_reuse_carrier_count"] == 24
    assert pool["yle_active_eligible_extension_count"] == 5
    assert pool["new_global_noun_identity_count"] == 0
    extensions = pool["provenance"]["yle_active_eligible_extensions"]
    assert {row["surface"] for row in extensions} == {
        "playground", "bus stop", "library", "market", "sports centre"
    }
    stages = {row["surface"]: row["yle_stage"] for row in extensions}
    assert stages["playground"] == "PRE_A1_STARTERS"
    assert {stages[x] for x in {"bus stop", "library", "market", "sports centre"}} == {"A1_MOVERS"}
    assert all(row["evp_level"] == "A2" for row in extensions)
    delta = data["delta_vs_unit03"]
    assert delta["unit04_selected_life_place_carriers"] == 29
    assert delta["unit04_selected_life_place_carriers_prior_reuse"] == 24
    assert delta["unit04_yle_active_eligible_carrier_extensions"] == 5
    assert delta["unit04_new_global_noun_identities"] == 0


def test_u04_q02_does_not_treat_prior_unit_denominators_as_vocabulary_ceiling():
    data = _q02()
    policy = data["counting_policy"]
    assert policy["prior_target_denominator_is_not_cumulative_vocabulary_universe"] is True
    assert policy["canonical_source_known_is_not_prior_learner_exposure"] is True
    assert policy["new_target_activation_may_reuse_an_existing_canonical_lexical_identity"] is True
    assert policy["unit04_delta_counts_target_activation_separately_from_global_identity_growth"] is True
    assert data["source_authority"]["prior_unit_reuse"]["unit02_morphology_noun_count"] == 162
    assert data["source_authority"]["prior_unit_reuse"]["unit03_support_resource_count"] == 40


def test_u04_q02_blocks_only_a2_flyers_place_examples_not_starters_or_movers():
    data = _q02()
    blocked = data["not_yet_allowed_life_place_examples"]
    assert blocked["count"] == 3
    assert {row["surface"] for row in blocked["examples"]} == {
        "airport", "office", "police station"
    }
    assert all(row["evp_level"] == "A2" for row in blocked["examples"])
    assert all(row["yle_stage"] == "A2_FLYERS" for row in blocked["examples"])
    extensions = data["life_skill_place_carrier_pool"]["provenance"]["yle_active_eligible_extensions"]
    assert {row["surface"] for row in extensions}.isdisjoint({row["surface"] for row in blocked["examples"]})
    multi = data["place_preposition_surface_authority"]["multiword_place_prepositions"]
    assert multi["status"] == "NOT_UNIT04_GRAMMAR_TARGET_IN_Q02"
    assert set(multi["examples"]) == {"next to", "in front of"}
    assert multi["yle_stage_evidence"] == "PRE_A1_STARTERS"


def test_u04_q02_preserves_q03_to_q10_materialization_boundaries():
    data = _q02()
    assert data["q02_boundaries"] == {
        "chunk_inventory_materialized": False,
        "sentence_frames_materialized": False,
        "sentence_assets_materialized": False,
        "scenes_materialized": False,
        "communicative_functions_materialized": False,
        "questionbank_materialized": False,
        "forms_materialized": False,
        "a2_unlocked": False,
    }
    delta = data["delta_vs_unit03"]
    assert delta["prior_cumulative_sentence_assets"] == 26514
    assert delta["prior_cumulative_chunk_surfaces"] == 50
    assert delta["prior_cumulative_core_pattern_families"] == 7
    assert delta["prior_cumulative_exact_sentence_frames"] == 15
    assert delta["unit04_not_yet_allowed_a2_flyers_place_examples"] == 3
    assert data["next_short_step"] == "A1FS-V1-U04Q03_Unit04PlaceRelationFormAndMeaningAuthority"
