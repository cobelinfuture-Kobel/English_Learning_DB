from product.a1fs_v1_2_1 import u04sp03_current360_spoken_production_pack_acceptance as sp03


def test_u04sp03_current360_spoken_production_packs_36_pattern_a_g() -> None:
    report = sp03.build_unit04_sp03_current360_spoken_production_pack_acceptance()
    assert report["status"] == sp03.STATUS
    assert report["surface_contract"] == {
        "surface_1_current360_narrative_episode_count": 360,
        "surface_1_current360_narrative_modified": False,
        "surface_2_spoken_pack_count": 36,
        "surface_3_production_pack_count": 36,
        "production_patterns": list("ABCDEFG"),
        "python_sentence_composer_used": False,
    }
    assert report["spoken_summary"]["spoken_pack_count"] == 36
    assert report["spoken_summary"]["spoken_micro_scene_count"] == 36
    assert report["spoken_summary"]["spoken_dialogue_turn_count"] == 144
    assert report["production_summary"]["production_pack_count"] == 36
    assert report["production_summary"]["production_micro_scene_count"] == 36
    assert report["production_summary"]["production_pattern_model_count"] == 252
    assert report["scope_safety"]["current360_narrative_modified"] is False
    assert report["scope_safety"]["q10_form01_20_modified"] is False
    assert report["scope_safety"]["a2_a2plus_unlocked"] is False
