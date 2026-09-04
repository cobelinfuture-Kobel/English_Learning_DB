import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
Q03_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u04_q03_place_relation_form_meaning_authority.json"
Q02_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u04_q02_vocabulary_authority.json"


def _q03():
    return json.loads(Q03_PATH.read_text(encoding="utf-8"))


def _q02():
    return json.loads(Q02_PATH.read_text(encoding="utf-8"))


def test_u04_q03_binds_exactly_to_merged_q02_and_keeps_a1_static_place_scope():
    data = _q03()
    assert data["status"] == "PASS_Q03_UNIT04_PLACE_RELATION_FORM_MEANING_AUTHORITY"
    assert data["unit_id"] == "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
    assert data["q02_merge_sha"] == "72405cd79888b4180c03c3653cb207c058008ee9"
    assert _q02()["acceptance"]["status"] == "PASS_Q02_UNIT04_VOCABULARY_AND_EXACT_SURFACE_ADMISSION"
    assert data["form_contract"]["target_semantic_domain"] == "STATIC_PLACE_SPATIAL_RELATION"
    assert data["form_contract"]["motion_semantics_materialized"] is False
    assert data["form_contract"]["a2_unlocked"] is False


def test_u04_q03_has_exactly_one_form_meaning_binding_for_each_q02_static_surface():
    q03 = _q03()
    q02 = _q02()
    relations = q03["relations"]
    q02_surfaces = q02["place_preposition_surface_authority"]["static_place_target_surfaces"]
    assert len(relations) == 8
    assert {row["surface"] for row in relations} == {row["surface"] for row in q02_surfaces}
    assert len({row["relation_id"] for row in relations}) == 8
    assert all(row["evp_level"] == "A1" for row in relations)
    assert all(row["static_relation"] is True for row in relations)


def test_u04_q03_exact_spatial_guideword_mapping_and_forms_are_preserved():
    data = _q03()
    mapping = {row["surface"]: row["evp_guideword"] for row in data["relations"]}
    assert mapping == {
        "in": "INSIDE",
        "inside": "CONTAINER",
        "on": "SURFACE",
        "near": "DISTANCE",
        "at": "PLACE",
        "under": "LOWER POSITION",
        "behind": "BACK",
        "between": "SPACE",
    }
    forms = {row["surface"]: row["form_realization"] for row in data["relations"]}
    assert forms == {
        "in": "in + NP",
        "inside": "inside + NP",
        "on": "on + NP",
        "near": "near + NP",
        "at": "at + NP",
        "under": "under + NP",
        "behind": "behind + NP",
        "between": "between + NP1 + and + NP2",
    }


def test_u04_q03_np_complements_and_landmark_cardinality_are_fail_closed():
    data = _q03()
    relations = {row["surface"]: row for row in data["relations"]}
    single = {"in", "inside", "on", "near", "at", "under", "behind"}
    for surface in single:
        assert relations[surface]["reference_landmark_cardinality"] == "ONE"
        assert relations[surface]["complement_requirement"] == "ONE_NOUN_PHRASE"
    between = relations["between"]
    assert between["reference_landmark_cardinality"] == "EXACTLY_TWO_DISTINCT"
    assert between["complement_requirement"] == "TWO_DISTINCT_LANDMARK_REFERENTS"
    assert between["form_realization"] == "between + NP1 + and + NP2"
    scene = data["scene_answerability_constraints_for_downstream"]
    assert set(scene["single_landmark_relations"]) == single
    assert scene["two_landmark_relation"] == "between"
    assert scene["between_requires_two_distinct_reference_landmarks"] is True


def test_u04_q03_rejects_same_surface_nonspatial_or_wrong_senses():
    data = _q03()
    blocked = {(row["surface"], row["sense"], row["evp_level"]) for row in data["semantic_disambiguation_gate"]["blocked_false_positive_senses"]}
    assert ("under", "LESS THAN", "A2") in blocked
    assert ("between", "AMOUNT", "A2") in blocked
    assert ("at", "AMOUNT", "B2") in blocked
    assert ("on", "CONNECTED", "A1") in blocked
    assert ("on", "DIRECTIONS", "A2") in blocked
    assert ("in", "ARRANGEMENT", "B1") in blocked
    assert ("in", "PART OF", "A2") in blocked
    domains = set(data["semantic_disambiguation_gate"]["blocked_semantic_domains"])
    assert "TIME" in domains
    assert "MOTION_OR_PATH_IN_Q03" in domains


def test_u04_q03_explicitly_gates_in_inside_and_at_in_overlap():
    data = _q03()
    policy = data["semantic_overlap_and_answerability_policy"]
    assert policy["required"] is True
    assert policy["in_inside_overlap"]["surfaces"] == ["in", "inside"]
    assert policy["in_inside_overlap"]["classification"] == "SEMANTIC_OVERLAP"
    assert policy["at_in_viewpoint_overlap"]["surfaces"] == ["at", "in"]
    assert policy["at_in_viewpoint_overlap"]["classification"] == "VIEWPOINT_DEPENDENT_OVERLAP"
    assert "without asserting exact interior or surface geometry" in next(
        row["meaning"] for row in data["relations"] if row["surface"] == "at"
    )


def test_u04_q03_near_is_nonexclusive_and_single_answer_items_must_be_unique():
    data = _q03()
    policy = data["semantic_overlap_and_answerability_policy"]
    near = policy["near_overlay"]
    assert near["classification"] == "NONEXCLUSIVE_PROXIMITY_OVERLAY"
    assert set(near["may_cooccur_with"]) == {"behind", "between", "under", "on", "at"}
    assert "invalid as a single-answer" in policy["single_answer_rule"]
    assert "enough geometry" in policy["picture_rule"]
    scene = data["scene_answerability_constraints_for_downstream"]
    assert scene["relation_must_be_visually_or_textually_assertable"] is True
    assert scene["ambiguous_multiple_true_relations_must_not_be_used_for_single_answer_items"] is True


def test_u04_q03_preserves_directional_and_multiword_support_boundaries():
    data = _q03()
    boundary = data["deferred_and_support_boundary"]
    assert boundary["a1_directional_surfaces_still_deferred"] == ["from", "into", "to"]
    assert boundary["yle_safe_multiword_support_not_promoted_to_q03_target"] == ["next to", "in front of"]
    assert {row["surface"] for row in data["relations"]}.isdisjoint({"from", "into", "to", "next to", "in front of"})


def test_u04_q03_delta_changes_semantic_binding_only():
    data = _q03()
    delta = data["delta_vs_unit03"]
    assert delta["prior_cumulative_sentence_assets"] == 26514
    assert delta["prior_cumulative_chunk_surfaces"] == 50
    assert delta["prior_cumulative_core_pattern_families"] == 7
    assert delta["prior_cumulative_exact_sentence_frames"] == 15
    assert delta["unit04_q03_form_meaning_relations"] == 8
    assert delta["unit04_q03_single_landmark_relations"] == 7
    assert delta["unit04_q03_two_landmark_relations"] == 1
    assert delta["unit04_q03_new_machine_readable_semantic_bindings"] == 8
    assert delta["unit04_q03_semantic_overlap_gates"] == 3
    assert delta["unit04_new_global_vocabulary_identities"] == 0
    assert delta["sentence_asset_delta"] == "NOT_YET_MATERIALIZED_Q06"
    assert delta["chunk_delta"] == "NOT_YET_MATERIALIZED_Q04"


def test_u04_q03_preserves_q04_to_q10_materialization_boundaries():
    data = _q03()
    assert data["q03_boundaries"] == {
        "chunk_inventory_materialized": False,
        "sentence_frames_materialized": False,
        "sentence_assets_materialized": False,
        "scenes_materialized": False,
        "communicative_functions_materialized": False,
        "questionbank_materialized": False,
        "forms_materialized": False,
        "motion_directional_surfaces_activated": False,
        "a2_unlocked": False,
    }
    assert data["acceptance"]["semantic_overlap_gate_count"] == 3
    assert data["acceptance"]["single_answer_ambiguity_gate_required"] is True
    assert data["next_short_step"] == "A1FS-V1-U04Q04_Unit04PlaceChunkAuthorityAndCumulativeDedup"
