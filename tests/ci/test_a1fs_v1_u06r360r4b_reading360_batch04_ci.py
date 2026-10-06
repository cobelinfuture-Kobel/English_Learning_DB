from product.a1fs_v1_2_1 import u06r360r4b_reading360_batch04 as batch

def test_u06_r4b_batch04_exact_scope_and_density():
    r=batch.build_report()
    assert r["status"]==batch.STATUS
    assert r["entry_count"]==60
    assert r["sentence_distribution"]=={6:20,7:20,8:20}
    assert r["ready_episode_count"]==0
    assert r["exact_paragraph_duplicate_count"]==0

def test_u06_r4b_batch04_lineage_grammar_family_and_cumulative_progress():
    r=batch.build_report()
    assert r["target_lineage_exact"] is True
    assert r["grammar_ceiling_pass"] is True
    assert r["family_purpose_pass"] is True
    assert r["human_semantic_review_pass"] is True
    assert r["cumulative_authored_count"]==240
    assert r["full360_final_accepted"] is False

def test_u06_r4b_batch04_family_counts():
    assert batch.build_report()["family_counts"]==batch.EXPECTED_FAMILY_COUNTS
