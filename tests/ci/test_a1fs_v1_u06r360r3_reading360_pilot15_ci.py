from product.a1fs_v1_2_1 import u06r360r3_reading360_pilot15 as pilot


def report():
    return pilot.build_report()


def test_u06_pilot15_authoring_contract_scope_lineage_and_density():
    r = report()
    assert r["status"] == pilot.STATUS
    assert r["entry_count"] == 15
    assert r["family_count"] == 15
    assert r["unique_source_episode_count"] == 15
    assert r["sentence_distribution"] == {6: 5, 7: 5, 8: 5}
    assert r["target_lineage_exact"] is True
    assert r["full360_materialized"] is False
    assert r["writing360_modified"] is False
    assert r["spoken360_modified"] is False
    assert r["pattern360_modified"] is False
    assert r["a2_a2plus_unlocked"] is False


def test_u06_pilot15_authoring_contract_primary_carriers_are_direct_legal():
    r = report()
    assert r["unique_primary_object_count"] == 13
    assert r["unique_primary_place_count"] >= 10
    assert r["primary_objects_outside_direct_legal_reservoir"] == []
    assert r["max_direct_object_episode_presence"] <= 2
    assert r["direct_object_unique_surface_count"] >= 20


def test_u06_pilot15_authoring_contract_preserves_person_role_balance():
    r = report()
    assert r["person_role_unique_surface_count"] >= 9
    assert r["friend_occurrences"] <= 6
    assert r["friend_occurrence_share"] <= 0.36


def test_u06_pilot15_authoring_contract_preserves_lexical_breadth():
    r = report()
    assert r["adjective_unique_surface_count"] >= 10
    assert r["action_unique_surface_count"] >= 20
    assert r["noun_like_unique_surface_count"] >= 60


def test_u06_pilot15_authoring_contract_numbers_plurals_and_human_review_unlock():
    r = report()
    assert r["number_bearing_entry_count"] == 5
    assert r["number_surface_counts"] == {"one": 1, "three": 2, "two": 2}
    assert r["irregular_plural_count"] == 0
    assert r["object_bundle_duplicate_count"] == 0
    assert r["human_review_pass"] is True
    assert r["ready_occurrence_count"] == 0
    assert r["ready_closure_count"] == 0
    assert r["unique_final_sentence_count"] == 15
    assert r["exact_final_sentence_duplicate_count"] == 0
    assert r["full360_expansion_allowed"] is True


def test_u06_pilot15_formal_acceptance_and_priority_human_modes():
    r = report()
    assert r["formal_acceptance_criteria_count"] == 7
    assert r["formal_acceptance_pass_count"] == 7
    assert r["priority_human_review_mode_count"] == 8
    assert r["priority_human_review_pass_count"] == 8
    assert set(r["priority_human_review_modes"]) == {
        "PERSONAL_MESSAGE", "MINI_EMAIL", "SCHOOL_NOTICE", "MAP_ROUTE",
        "TWO_PERSON", "PAIR_SHARED", "SMALL_GROUP", "PROBLEM_SOLUTION",
    }
