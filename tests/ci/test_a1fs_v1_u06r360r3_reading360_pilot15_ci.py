from product.a1fs_v1_2_1 import u06r360r3_reading360_pilot15 as pilot


def report():
    return pilot.build_report()


def test_u06_reading360_r3_pilot_r2_exact_scope_and_families():
    r = report()
    assert r["status"] == pilot.STATUS
    assert r["entry_count"] == 15
    assert r["family_count"] == 15
    assert r["unique_source_episode_count"] == 15
    assert r["target_lineage_exact"] is True
    assert r["full360_materialized"] is False
    assert r["writing360_modified"] is False
    assert r["spoken360_modified"] is False
    assert r["pattern360_modified"] is False
    assert r["a2_a2plus_unlocked"] is False


def test_u06_reading360_r3_pilot_r2_natural_sentence_distribution():
    r = report()
    assert r["sentence_distribution"] == {6: 5, 7: 5, 8: 5}


def test_u06_reading360_r3_pilot_r2_lexical_and_number_diversity():
    r = report()
    assert r["unique_primary_object_count"] >= 13
    assert r["unique_primary_place_count"] >= 10
    assert r["object_bundle_duplicate_count"] == 0
    assert r["number_bearing_entry_count"] == 5
    assert r["number_surface_counts"] == {"one": 1, "three": 2, "two": 2}


def test_u06_reading360_r3_pilot_r2_regular_plural_only():
    r = report()
    assert r["irregular_plural_count"] == 0
    assert set(r["declared_regular_plural_surfaces"]) == {
        "balls","books","cards","cups","hands","numbers","shoes","students","tasks"
    }


def test_u06_reading360_r3_pilot_r2_keeps_unit01_to06_grammar_ceiling():
    r = report()
    assert r["unit01_to_unit06_grammar_ceiling"] is True
    assert r["human_review_required"] is True
