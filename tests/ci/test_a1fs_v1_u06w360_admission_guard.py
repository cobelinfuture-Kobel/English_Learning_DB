from product.a1fs_v1_2_1.u06w360_admission_guard import validate

def test_u06_writing360_source_coverage_and_gpt6_authoring():
    result=validate()
    assert result["status"]=="PASS_WRITING360_GPT6_BATCHES_PARTIAL_ADMISSION_GATE"
    assert result["source_mapped"]==360
    assert result["operator_approved_pilot"]==15
    assert result["gpt6_authored_self_reviewed"]>=135
    assert result["pending_authoring"]==345-result["gpt6_authored_self_reviewed"]
    assert result["full360_admitted"] is False

def test_u06_writing360_episode_specific_operation_distribution():
    result=validate()
    assert result["operation_distribution"]=={
        "COPY_AND_CHANGE":23,
        "TABLE_TO_SENTENCES":88,
        "SENTENCE_PLAN":118,
        "GUIDED_MINI_TEXT":131,
    }
    assert result["batch_count"]>=9
