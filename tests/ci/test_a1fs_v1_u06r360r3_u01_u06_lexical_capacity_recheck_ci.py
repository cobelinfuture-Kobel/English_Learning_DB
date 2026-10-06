from product.a1fs_v1_2_1 import u06r360r3_u01_u06_lexical_capacity_recheck as cap


def report():
    return cap.build_report()


def test_u06_reading360_lexical_capacity_direct_counts():
    r = report()["direct_legal_now"]
    assert r["noun_like"]["unique_surface_count"] == 202
    assert r["noun_like"]["regular_plural_allowed_count"] == 192
    assert r["noun_like"]["singular_only_irregular_plural_count"] == 8
    assert r["noun_like"]["singular_only_noncount_count"] == 2
    assert r["object_carrier_subset"]["count"] == 25
    assert r["place_carrier_subset"]["count"] == 29
    assert r["person_role_carrier_subset"]["count"] == 17
    assert r["adjective_surfaces"]["count"] == 25
    assert r["ability_action_verb_surfaces"]["count"] == 60
    assert r["number_surfaces_direct_proven"]["surfaces"] == ["one", "two", "three"]


def test_u06_reading360_lexical_capacity_plural_boundary():
    r = report()["direct_legal_now"]
    assert r["noun_like"]["singular_only_irregular_plural_surfaces"] == [
        "child", "fish", "foot", "man", "person", "sheep", "tooth", "woman"
    ]
    assert r["noun_like"]["singular_only_noncount_surfaces"] == ["homework", "music"]
    assert r["object_carrier_subset"]["all_regular_plural_allowed"] is True
    assert r["place_carrier_subset"]["all_regular_plural_allowed"] is True
    assert r["person_role_carrier_subset"]["irregular_plural_singular_only"] == [
        "child", "man", "person", "woman"
    ]


def test_u06_reading360_lexical_capacity_a1_candidate_ceiling():
    a1 = report()["a1_candidate_ceiling"]
    assert a1["sense_rows"] == 784
    assert a1["unique_base_words"] == 643
    assert a1["noun"] == {"sense_rows": 322, "unique_base_words": 304}
    assert a1["verb"] == {"sense_rows": 107, "unique_base_words": 85}
    assert a1["adjective"] == {"sense_rows": 93, "unique_base_words": 76}
    assert a1["number_words"]["count"] == 20


def test_u06_reading360_lexical_capacity_scope_stays_frozen():
    r = report()
    assert r["scope"]["reading360_full_materialized"] is False
    assert r["scope"]["writing360_modified"] is False
    assert r["scope"]["spoken360_modified"] is False
    assert r["scope"]["pattern360_modified"] is False
    assert r["scope"]["irregular_plural_unlocked"] is False
    assert r["scope"]["a2_a2plus_grammar_unlocked"] is False
    assert r["yle_evidence"]["unit06_q04r1"]["flyers_entries_admitted"] == 0
