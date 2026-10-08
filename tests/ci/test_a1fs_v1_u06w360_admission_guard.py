from product.a1fs_v1_2_1.u06w360_admission_guard import validate

def test_u06_writing360_pilot_and_gpt6_batch01_source_contract():
    result=validate()
    assert result["status"]=="PASS_WRITING360_GPT6_BATCH01_PARTIAL_ADMISSION_GATE"
    assert result["source_mapped"]==360
    assert result["operator_approved_pilot"]==15
    assert result["gpt6_authored_self_reviewed"]==15
    assert result["pending_authoring"]==330
    assert result["full360_admitted"] is False

def test_u06_writing360_operation_distribution_is_mapping_driven():
    result=validate()
    counts=result["operation_distribution"]
    assert set(counts)=={"COPY_AND_CHANGE","TABLE_TO_SENTENCES","SENTENCE_PLAN","GUIDED_MINI_TEXT"}
    assert sum(counts.values())==360
    assert counts=={"COPY_AND_CHANGE":23,"TABLE_TO_SENTENCES":88,
                    "SENTENCE_PLAN":118,"GUIDED_MINI_TEXT":131}
