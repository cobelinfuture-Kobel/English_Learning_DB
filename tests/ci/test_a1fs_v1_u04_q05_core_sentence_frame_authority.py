import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
Q05_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u04_q05_core_sentence_frame_authority.json"
Q04_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u04_q04_place_chunk_authority.json"


def _q05():
    return json.loads(Q05_PATH.read_text(encoding="utf-8"))


def _q04():
    return json.loads(Q04_PATH.read_text(encoding="utf-8"))


def test_u04_q05_binds_to_merged_q04_and_preserves_a1_static_place_scope():
    data = _q05()
    assert data["status"] == "PASS_Q05_UNIT04_CORE_SENTENCE_FRAME_AUTHORITY"
    assert data["unit_id"] == "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
    assert data["q04_merge_sha"] == "b66bc99960764c0f09b7bc716309e13dbfa9c4d4"
    assert _q04()["acceptance"]["status"] == "PASS_Q04_UNIT04_PLACE_CHUNK_AUTHORITY_AND_CUMULATIVE_DEDUP"
    assert data["q05_boundaries"]["motion_directional_surfaces_activated"] is False
    assert data["q05_boundaries"]["a2_unlocked"] is False


def test_u04_q05_prior_pattern_and_frame_baseline_matches_unit03_handoff():
    data = _q05()
    prior = data["prior_frame_baseline"]
    assert prior["source_sha256"] == "3f9bf777ee75d3771b7e30df0b5ae3899238550797d0a4948ce1ae56b8250904"
    assert prior["cumulative_pattern_family_count"] == 7
    assert prior["cumulative_exact_frame_count"] == 15
    assert prior["unit03_new_pattern_family_count"] == 0
    assert prior["unit03_new_exact_frame_count"] == 0
    reuse = {row["relation_surface"]: row["frame_id"] for row in prior["reused_unit04_target_frames"]}
    assert reuse == {"in": "U01-F03", "near": "U01-F04"}
    assert prior["generic_place_fallback"]["frame_id"] == "U01-F05"
    assert prior["generic_place_fallback"]["unit04_role"] == "INHERITED_FALLBACK_NOT_PRIMARY_Q06_ROUTE"


def test_u04_q05_does_not_invent_a_new_canonical_pattern_family():
    data = _q05()
    policy = data["pattern_family_policy"]
    assert policy["new_canonical_pattern_family_count"] == 0
    assert policy["cumulative_pattern_family_count"] == 7
    assert policy["relation_specific_operational_frames_do_not_create_new_canonical_pattern_families"] is True
    assert policy["pronoun_substitution_does_not_create_new_canonical_pattern_family"] is True


def test_u04_q05_new_exact_frames_are_six_target_plus_two_yle_support():
    data = _q05()
    frames = data["unit04_new_exact_frames"]
    assert len(frames) == 8
    target = {row["relation_surface"]: row for row in frames if row["frame_class"] == "TARGET_RELATION_SPECIFIC_OPERATIONAL_FRAME"}
    support = {row["support_pattern"]: row for row in frames if row["frame_class"] == "YLE_SAFE_SUPPORT_OPERATIONAL_FRAME"}
    assert set(target) == {"on", "at", "inside", "under", "behind", "between"}
    assert set(support) == {"next to", "in front of"}
    assert all(row["direct_generation_allowed"] is True for row in frames)
    assert support["next to"]["parent_canonical_chunk_id"] == "EVP_CHUNK_000149"
    assert support["in front of"]["parent_canonical_chunk_id"] == "EVP_CHUNK_001596"
    assert all(row["yle_stage"] == "PRE_A1_STARTERS" for row in support.values())
    assert all(row["q03_target_relation"] is False for row in support.values())


def test_u04_q05_between_frame_keeps_two_distinct_landmark_constraint():
    data = _q05()
    between = next(row for row in data["unit04_new_exact_frames"] if row.get("relation_surface") == "between")
    assert between["frame_id"] == "U04-RF-BETWEEN"
    assert between["template"] == "{ARTICLE_CAP} {THING} is between the {LANDMARK1} and the {LANDMARK2}."
    assert between["requires_two_distinct_landmarks"] is True
    assert between["q03_relation_id"] == "U04-REL-BETWEEN-TWO-LANDMARKS"


def test_u04_q05_primary_generation_routing_covers_eight_targets_once_without_generic_duplicate_route():
    data = _q05()
    routing = data["q06_primary_generation_routing"]
    assert routing["target_relations"] == {
        "in": "U01-F03",
        "near": "U01-F04",
        "on": "U04-RF-ON",
        "at": "U04-RF-AT",
        "inside": "U04-RF-INSIDE",
        "under": "U04-RF-UNDER",
        "behind": "U04-RF-BEHIND",
        "between": "U04-RF-BETWEEN",
    }
    assert routing["support_relations"] == {
        "next to": "U04-SF-NEXT-TO",
        "in front of": "U04-SF-IN-FRONT-OF",
    }
    assert len(set(routing["target_relations"].values())) == 8
    assert routing["generic_u01_f05_is_primary_route"] is False
    assert routing["q06_exact_and_normalized_sentence_dedup_required"] is True


def test_u04_q05_pronoun_carry_forward_is_context_bound_not_direct_pattern_invention():
    data = _q05()
    carry = data["pronoun_carry_forward_policy"]
    assert carry["unit03_source_sha256"] == "6a9d4e8a88cdbefbd8723fbe1217825eae21c51550eb31cc3005e42f77f71f9b"
    assert carry["reference_binding_required"] is True
    assert carry["direct_pronoun_frame_assessment_without_context_allowed"] is False
    evidence = {row["sentence_id"]: row["text"] for row in carry["sample_existing_admitted_evidence"]}
    assert evidence == {
        "U03-SENT-A9592EE938D229F1B3AA": "It is near the bus stop.",
        "U03-SENT-29C7F40FCBD97B18F9ED": "It is on the bed.",
        "U03-SENT-CFCE61A7943719ED7FC9": "She is in a classroom.",
    }
    assert "referent-aware context-bound transformation" in carry["policy"]


def test_u04_q05_frame_dedup_and_delta_are_explicit():
    data = _q05()
    counts = data["frame_dedup_and_counts"]
    assert counts == {
        "prior_exact_frames": 15,
        "prior_primary_reused_target_frames": 2,
        "new_target_exact_frames": 6,
        "new_support_exact_frames": 2,
        "new_exact_frames_total": 8,
        "within_new_exact_template_duplicate_count": 0,
        "exact_template_overlap_with_prior_15": 0,
        "cumulative_exact_frames": 23,
        "cumulative_pattern_families": 7,
    }
    delta = data["delta_vs_unit03"]
    assert delta["prior_cumulative_pattern_families"] == 7
    assert delta["unit04_new_canonical_pattern_families"] == 0
    assert delta["cumulative_pattern_families_after_q05"] == 7
    assert delta["prior_cumulative_exact_frames"] == 15
    assert delta["unit04_new_target_exact_frames"] == 6
    assert delta["unit04_new_yle_support_exact_frames"] == 2
    assert delta["unit04_new_exact_frames_total"] == 8
    assert delta["cumulative_exact_frames_after_q05"] == 23
    assert delta["cumulative_chunk_surfaces_after_q04"] == 90
    assert delta["prior_cumulative_sentence_assets"] == 26514


def test_u04_q05_preserves_q06_to_q10_materialization_boundaries():
    data = _q05()
    assert data["q05_boundaries"] == {
        "sentence_assets_materialized": False,
        "scenes_materialized": False,
        "communicative_functions_materialized": False,
        "questionbank_materialized": False,
        "forms_materialized": False,
        "motion_directional_surfaces_activated": False,
        "a2_unlocked": False,
    }
    assert data["acceptance"]["new_exact_frame_total"] == 8
    assert data["acceptance"]["cumulative_exact_frame_count"] == 23
    assert data["acceptance"]["q06_target_relation_route_count"] == 8
    assert data["acceptance"]["q06_support_relation_route_count"] == 2
    assert data["next_short_step"] == "A1FS-V1-U04Q06_Unit04SentenceAssetProductionAndSemanticAdmission"
