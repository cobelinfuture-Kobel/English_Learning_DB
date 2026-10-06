from product.a1fs_v1_2_1 import u06r360r3_reading360_pilot15 as pilot


def report():
    return pilot.build_report()


def test_u06_reading360_r3_pilot_has_exact_15_families():
    r = report()
    assert r["status"] == pilot.STATUS
    assert r["entry_count"] == 15
    assert r["family_count"] == 15
    assert r["family_coverage"] == "15/15"
    assert r["unique_source_episode_count"] == 15
    assert r["unique_text_count"] == 15


def test_u06_reading360_r3_pilot_has_natural_6_7_8_distribution():
    r = report()
    assert r["sentence_distribution"] == {6: 5, 7: 5, 8: 5}
    assert r["sentence_min"] == 6
    assert r["sentence_max"] == 8


def test_u06_reading360_r3_pilot_preserves_authority_and_scope():
    r = report()
    assert r["unit01_to_unit06_grammar_ceiling"] is True
    assert r["target_lineage_exact"] is True
    assert r["ket_flyers_lowered_text_type_policy"] is True
    assert r["ielts_inspired_real_life_policy"] is True
    assert r["full360_materialized"] is False
    assert r["writing360_modified"] is False
    assert r["spoken360_modified"] is False
    assert r["pattern360_modified"] is False
    assert r["a2_a2plus_unlocked"] is False
    assert r["human_review_required"] is True


def test_u06_reading360_r3_pilot_has_real_format_shell_diversity():
    r = report()
    assert r["format_shell_variant_count"] >= 10
