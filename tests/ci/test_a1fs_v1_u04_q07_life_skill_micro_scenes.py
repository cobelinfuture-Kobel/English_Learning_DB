import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
Q03 = ROOT / "ulga/contracts/a1fs_v1_u04_q03_place_relation_form_meaning_authority.json"
Q06 = ROOT / "ulga/contracts/a1fs_v1_u04_q06_sentence_assets.json"
Q07 = ROOT / "ulga/contracts/a1fs_v1_u04_q07_life_skill_micro_scenes.json"
U03_ACCEPTANCE = ROOT / "ulga/contracts/a1fs_v1_unit03_production_acceptance_manifest.json"

GOVERNED_SCENE_FAMILIES = {
    "SCHOOL_CLASSROOM_LEARNING",
    "HOME_BEDROOM_LIVING",
    "BATHROOM_SELF_CARE",
    "KITCHEN_DINING",
    "FOOD_CAFE_PICNIC",
    "FAMILY_PEOPLE_SOCIAL",
    "BODY_APPEARANCE",
    "CLOTHING_PERSONAL_ITEMS",
    "PETS_FARM_ZOO",
    "PARK_GARDEN_NATURE",
    "SPORTS_PLAY",
    "MUSIC_DANCE",
    "MEDIA_ENTERTAINMENT_TECH",
    "TOWN_PUBLIC_PLACES",
    "SHOP_MONEY_SERVICES",
    "TRANSPORT_TRAVEL",
    "COMMUNICATION_WRITING",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def expected_scene_id(row):
    key = "|".join(
        [
            row["bound_sentence_id"],
            row["scene_family"],
            row["medium_setting"],
            row["small_micro_scene_event"],
            row["relation_surface"],
            *row["reference_landmarks"],
        ]
    )
    return "U04-SCENE-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:20].upper()


def test_u04_q07_materializes_all_q06_context_bound_sentence_bindings():
    q06 = load(Q06)
    q07 = load(Q07)
    scenes = q07["micro_scenes"]

    assert q07["status"] == "PASS_Q07_UNIT04_LIFE_SKILL_MICRO_SCENE_MATERIALIZATION_AND_SENTENCE_BINDING"
    assert len(scenes) == 96
    assert q07["coverage"]["unit04_scene_instance_count"] == 96

    q06_ids = [row["sentence_id"] for row in q06["assets"]]
    bound_ids = [row["bound_sentence_id"] for row in scenes]
    assert len(bound_ids) == len(set(bound_ids)) == 96
    assert set(bound_ids) == set(q06_ids)
    assert q07["coverage"]["q06_unbound_sentence_count"] == 0
    assert q07["acceptance"]["q06_sentence_bindings"] == "96/96"


def test_u04_q07_scene_rows_are_exactly_bound_to_q06_semantics():
    q06 = load(Q06)
    q07 = load(Q07)
    q06_by_id = {row["sentence_id"]: row for row in q06["assets"]}

    for scene in q07["micro_scenes"]:
        source = q06_by_id[scene["bound_sentence_id"]]
        assert scene["bound_sentence_text"] == source["text"]
        assert scene["located_entity_surface"] == source["subject_np_surface"]
        assert scene["located_entity_lemma"] == source["subject_lemma"]
        assert scene["relation_surface"] == source["relation_surface"]
        assert scene["relation_id"] == source["relation_id"]
        assert scene["generation_role"] == source["generation_role"]
        assert scene["place_chunk_surface"] == source["place_chunk_surface"]
        assert scene["answerability_guard"]["scene_binds_truth_of_bound_sentence"] is True
        assert scene["answerability_guard"]["unbound_direct_assessment_allowed"] is False
        assert scene["answerability_guard"]["scene_bound_context_use_allowed"] is True
        assert scene["a2_unlocked"] is False


def test_u04_q07_scene_ids_and_semantic_fingerprints_are_unique():
    q07 = load(Q07)
    scenes = q07["micro_scenes"]

    ids = [row["scene_ref_id"] for row in scenes]
    assert len(ids) == len(set(ids)) == 96
    for row in scenes:
        assert row["scene_ref_id"] == expected_scene_id(row)

    fingerprints = [
        (
            row["scene_family"],
            row["medium_setting"],
            row["small_micro_scene_event"],
            row["located_entity_surface"],
            row["relation_surface"],
            tuple(row["reference_landmarks"]),
        )
        for row in scenes
    ]
    assert len(fingerprints) == len(set(fingerprints)) == 96
    assert q07["scene_diversity"]["micro_scene_semantic_fingerprint_duplicate_count"] == 0
    assert q07["scene_diversity"]["scene_sentence_semantic_mismatch_count"] == 0


def test_u04_q07_geometry_preserves_q03_between_and_static_place_guards():
    q03 = load(Q03)
    q07 = load(Q07)
    scenes = q07["micro_scenes"]
    q03_targets = {row["surface"] for row in q03["relations"]}

    assert q03_targets == {"in", "inside", "on", "near", "at", "under", "behind", "between"}

    for row in scenes:
        relation = row["relation_surface"]
        landmarks = row["reference_landmarks"]
        assert relation not in {"from", "into", "to"}
        assert row["visual_truth_spec"]["relation_truth_must_be_visible"] is True
        assert row["visual_truth_spec"]["target_and_landmarks_must_be_visible"] is True
        assert row["visual_truth_spec"]["single_answer_relation_selection_sufficient_by_itself"] is False

        if relation == "between":
            assert len(landmarks) == 2
            assert landmarks[0] != landmarks[1]
        else:
            assert len(landmarks) == 1

        if row["generation_role"] == "TARGET_RELATION":
            assert relation in {"inside", "under", "behind", "between"}
            assert relation in q03_targets
        else:
            assert relation in {"next to", "in front of"}
            assert relation not in q03_targets


def test_u04_q07_keeps_all_six_q06_relation_supplies_balanced():
    q06 = load(Q06)
    q07 = load(Q07)
    q06_counts = Counter(row["relation_surface"] for row in q06["assets"])
    q07_counts = Counter(row["relation_surface"] for row in q07["micro_scenes"])

    assert q07_counts == q06_counts == {
        "inside": 16,
        "under": 16,
        "behind": 16,
        "between": 16,
        "next to": 16,
        "in front of": 16,
    }
    assert q07["coverage"]["target_relation_scene_count"] == 64
    assert q07["coverage"]["support_relation_scene_count"] == 32


def test_u04_q07_reuses_governed_scene_family_ontology_without_second_global_library():
    q07 = load(Q07)
    u03 = load(U03_ACCEPTANCE)
    prior = q07["prior_scene_authority"]

    assert set(prior["governed_scene_families"]) == GOVERNED_SCENE_FAMILIES
    assert prior["governed_scene_family_count"] == 17
    assert "CONTEXT_DEPENDENT" not in GOVERNED_SCENE_FAMILIES
    assert u03["acceptance"]["reading_writing"]["scenes"]["required_scene_families"] == 17
    assert u03["acceptance"]["reading_writing"]["scenes"]["covered_scene_families"] == 17

    assert prior["new_global_scene_family_count"] == 0
    assert prior["new_global_canonical_scene_identity_count"] == 0
    assert q07["q07_boundaries"]["global_canonical_scene_library_rewritten"] is False

    for row in q07["micro_scenes"]:
        assert row["scene_family"] in GOVERNED_SCENE_FAMILIES
        assert row["canonical_scene_scope"] == "UNIT04_LOCAL_AUTHORITATIVE_INSTANCE"


def test_u04_q07_used_families_have_multiple_real_event_variants():
    q07 = load(Q07)
    scenes = q07["micro_scenes"]
    by_family = defaultdict(list)
    for row in scenes:
        by_family[row["scene_family"]].append(row)

    for family, rows in by_family.items():
        events = {row["small_micro_scene_event"] for row in rows}
        sources = {row["bound_sentence_id"] for row in rows}
        assert len(events) >= 2
        assert len(sources) == len(rows)
        report = q07["scene_diversity"]["family_usage"][family]
        assert report["usage_count"] == len(rows)
        assert report["distinct_event_variants"] == len(events)
        assert report["distinct_q06_sources"] == len(sources)

    assert q07["scene_diversity"]["all_unit04_used_families_have_multiple_event_variants"] is True


def test_u04_q07_reuse_supply_completes_all_eight_q03_target_relations_without_regeneration():
    q06 = load(Q06)
    q07 = load(Q07)
    reuse = q07["prior_relation_scene_reuse"]

    assert reuse["prior_sentence_supply_total"] == 37
    assert reuse["new_scene_instance_count_for_these_relations"] == 0
    assert reuse["fabricated_prior_scene_ref_count"] == 0
    assert {
        relation: row["prior_unit03_sentence_supply"]
        for relation, row in reuse["relations"].items()
    } == q06["reuse_supply"]["unit03_raw_predicative_place_relation_reuse_counts"]

    assert q07["coverage"]["q03_target_relation_capability_count"] == 8
    assert q07["acceptance"]["q03_target_relation_capability"] == "8/8"


def test_u04_q07_carries_forward_overlap_answerability_gates():
    q07 = load(Q07)
    overlap = q07["semantic_overlap_carry_forward"]

    assert "inside" in overlap["in_inside"]
    assert "near" in overlap["near_overlay"].casefold()
    assert "next to" in overlap["next_to_near"].casefold()
    assert "at" in overlap["at_in"].casefold()
    assert "distinct" in overlap["between"].casefold()

    for row in q07["micro_scenes"]:
        assert row["answerability_guard"]["overlap_sensitive_relation_selection_requires_downstream_unique_cue"] is True


def test_u04_q07_boundaries_and_next_step():
    q07 = load(Q07)
    assert q07["q07_boundaries"] == {
        "global_canonical_scene_library_rewritten": False,
        "communicative_functions_materialized": False,
        "questionbank_materialized": False,
        "forms_materialized": False,
        "directional_from_into_to_activated": False,
        "a2_unlocked": False,
    }
    assert q07["next_short_step"] == "A1FS-V1-U04Q08_Unit04CommunicativeFunctionAuthority"
