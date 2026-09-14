from validators.validate_ket_data_s3_unified_assessment_taxonomy import validate

def test_ket_data_s3_unified_assessment_taxonomy():
    r=validate()
    assert r["status"]=="PASS_KET_DATA_S3_UNIFIED_FIVE_LAYER_ASSESSMENT_TAXONOMY"
    assert r["s2b_item_count"]==1452
    assert r["canonical_exam_item_count"]==1360
    assert r["supplementary_practice_item_count"]==92
    assert r["semantic_profile_count"]==24
    assert r["response_modes"]==["SELECT","MATCH","TEXT_ENTRY","STRUCTURED_ENTRY","ORDER","SPEAK"]
    assert all(v==1452 for v in r["five_layer_coverage"].values())
    assert r["practice_authority_promotion_count"]==0
    assert r["source_semantics_preserved"] is True
    assert r["all_1452_items_resolve_to_five_layers"] is True
