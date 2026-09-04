import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "ulga/contracts/a1fs_v1_u04_q01_place_prepositions_scope_admission.json"


def _contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_u04_q01_exact_unit_and_three_canonical_egp_rows():
    data = _contract()
    assert data["status"] == "CURRENT_UNIT_Q01_AUTHORITY_ADMITTED"
    assert data["unit_number"] == 4
    assert data["unit_id"] == "GRAMMAR_BASIC_PREPOSITIONS_PLACE"
    rows = data["canonical_mapping"]["target_kps"]
    assert [row["kp"] for row in rows] == ["KP023", "KP024", "KP025"]
    assert {row["egp_row_id"] for row in rows} == {
        "1741163711829x722500780296901000",
        "1741163713112x603850914179882600",
        "1741163713112x806003192035927200",
    }


def test_u04_q01_is_place_spatial_only_and_filters_non_place_semantics():
    data = _contract()
    spec = data["project_specialization"]
    assert spec["semantic_domain"] == "PLACE_SPATIAL_RELATIONS_ONLY"
    assert set(spec["false_positive_semantics"]) == {
        "TIME",
        "ABSTRACT_RELATION",
        "RECIPIENT",
        "PURPOSE_OR_BENEFICIARY",
        "ACCOMPANIMENT",
    }
    assert data["acceptance"]["place_semantic_specialization_required"] is True
    assert data["acceptance"]["time_and_abstract_false_positive_filter_required"] is True


def test_u04_q01_cumulative_baseline_matches_accepted_unit01_to_unit03_assets():
    data = _contract()
    baseline = data["cumulative_baseline_after_unit03"]
    sentences = baseline["sentence_assets"]
    assert sentences["unit01_admitted"] == 3805
    assert sentences["unit02_new_admitted"] == 3726
    assert sentences["unit03_new_admitted"] == 18983
    assert 3805 + 3726 + 18983 == 26514
    assert sentences["cumulative_distinct"] == 26514
    assert sentences["reuse_policy"] == "REUSABLE_BASE_NOT_CLOSED_GENERATION_UNIVERSE"
    assert baseline["chunk_surfaces_cumulative"] == 50
    assert baseline["core_pattern_families_cumulative"] == 7
    assert baseline["exact_sentence_frames_cumulative"] == 15
    assert baseline["unit01_bindable_scenes"] == 31
    assert baseline["unit02_scene_families"] == 17


def test_u04_q01_reuses_only_proven_place_relation_surface_seeds():
    data = _contract()
    seeds = data["reuse_new_not_yet_allowed"]["REUSE"]["place_relation_frame_seeds"]
    assert {(x["source_frame_id"], x["surface"], x["relation"]) for x in seeds} == {
        ("U01-F03", "in", "IN"),
        ("U01-F04", "near", "NEAR"),
        ("U01-F05", "on", "ON"),
    }
    admitted_seed_surfaces = {x["surface"] for x in seeds}
    assert "under" not in admitted_seed_surfaces
    assert "next to" not in admitted_seed_surfaces


def test_u04_q01_keeps_new_language_expansion_open_for_life_skill_breadth():
    data = _contract()
    new = data["reuse_new_not_yet_allowed"]["NEW"]
    assert new["prior_assets_are_not_closed_generation_universe"] is True
    assert new["new_vocabulary_admission"].startswith("REQUIRED_WHEN_Q02")
    assert new["new_chunk_admission"].startswith("REQUIRED_WHEN_Q04")
    assert new["new_core_sentence_or_frame_admission"].startswith("REQUIRED_WHEN_Q05_Q06")
    assert new["new_scene_admission"].startswith("REQUIRED_WHEN_Q07")
    assert data["acceptance"]["prior_assets_are_floor_not_ceiling"] is True


def test_u04_q01_blocks_later_level_and_complex_preposition_expansion():
    data = _contract()
    blocked = data["reuse_new_not_yet_allowed"]["NOT_YET_ALLOWED"]
    assert blocked["a2_unlocked"] is False
    assert set(blocked["later_level_preposition_structures"]) == {
        "JUST_PLUS_PREPOSITION",
        "COMPLEX_PREPOSITION_PRODUCTIVE_CATEGORY",
        "INCREASING_RANGE_OF_SIMPLE_PREPOSITIONS",
        "PREPOSITION_PLUS_ING_COMPLEMENT",
        "PREPOSITION_STRANDING",
    }
    assert blocked["complex_multiword_place_prepositions"].startswith("NOT_ADMITTED_BY_Q01")
    assert blocked["later_unit_grammar_as_convenience"] is False


def test_u04_q01_does_not_prematurely_materialize_q02_to_q10_content():
    data = _contract()
    boundaries = data["q01_boundaries"]
    assert boundaries == {
        "exact_preposition_surface_inventory_frozen": False,
        "q02_vocabulary_materialized": False,
        "q04_chunk_inventory_materialized": False,
        "sentence_assets_materialized": False,
        "learner_content_materialized": False,
        "questionbank_materialized": False,
        "forms_materialized": False,
        "a2_unlocked": False,
    }
    assert data["next_short_step"] == "A1FS-V1-U04Q02_Unit04VocabularyAuthorityAndExactSurfaceAdmission"
