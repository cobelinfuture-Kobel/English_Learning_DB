from product.a1fs_v1_2_1.u06w360_admission_guard import validate

def test_u06_writing360_source_coverage_and_gpt6_authoring():
    result=validate()
    assert result["status"]=="PASS_WRITING360_GPT6_BATCHES_PARTIAL_ADMISSION_GATE"
    assert result["source_mapped"]==360
    assert result["operator_approved_pilot"]==15
    assert result["gpt6_authored_self_reviewed"]>=225
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
    assert result["batch_count"]>=15

def test_u06_writing360_full_authoring_complete_but_admission_held():
    from product.a1fs_v1_2_1.u06w360_admission_guard import read, PILOT, DATA
    result=validate()
    assert result["gpt6_authored_self_reviewed"]==345
    assert result["pending_authoring"]==0
    assert result["full360_authoring_complete"] is True
    assert result["full360_admission_decision"]=="HOLD_FULL360_NOT_ADMITTED"
    assert result["full360_admitted"] is False
    pilot=read(PILOT)
    assert pilot["pilot_validation"]["human_accepted_items"]==15
    batch=read(DATA/"unit06_writing360_gpt6_batch01_e002_e016.json")
    e009=next(e for e in batch["entries"] if e["writing_entry_id"]=="U06-WRITE-E009")
    assert e009["model_answer"][0]=="Tom is at the door at home in the morning."
    assert e009["learner_page"]["worked_example"]["complete_sentence"]==e009["model_answer"][0]
    assert e009["teacher_only"]["model_answer"]==e009["model_answer"]

