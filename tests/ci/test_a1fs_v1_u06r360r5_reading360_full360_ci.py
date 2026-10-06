from product.a1fs_v1_2_1 import u06r360r5_reading360_full360 as full

def test_u06_r5_full360_exact_counts_and_density():
    r=full.build_report()
    assert r["status"]==full.STATUS
    assert r["entry_count"]==360
    assert r["exact_family_quota"]==full.EXPECTED_QUOTAS
    assert r["sentence_distribution"]=={6:120,7:120,8:120}

def test_u06_r5_full360_quality_gates():
    r=full.build_report()
    assert r["target_lineage_exact"] is True
    assert r["grammar_ceiling_pass"] is True
    assert r["family_purpose_structure_pass"] is True
    assert r["ready_episode_count"]==0
    assert r["exact_paragraph_duplicate_count"]==0
    assert r["human_pilot_approved"] is True
    assert r["full360_final_accepted"] is True
