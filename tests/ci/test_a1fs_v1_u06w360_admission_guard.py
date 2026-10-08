from product.a1fs_v1_2_1.u06w360_admission_guard import validate

def test_u06_writing360_pilot15_and_full360_admission_gate():
    result=validate()
    assert result["approved"]>=15
    assert result["pilot_operation_counts"]=={
        "COPY_AND_CHANGE":4,"TABLE_TO_SENTENCES":4,
        "SENTENCE_PLAN":4,"GUIDED_MINI_TEXT":3,
    }
    assert result["status"] in {
        "PASS_WRITING360_PILOT15_ADMISSION_GUARD",
        "PASS_WRITING360_FULL360_EVIDENCE_SCHEMA",
        "PASS_WRITING360_SOURCE_PURPOSE_MAPPING_GATE",
    }
    if not result["full360_admitted"]:
        assert result["approved"]==15
        assert result["not_yet_admitted"]==345


def test_u06_writing360_source_to_purpose_mapping_no_false_admission():
    result = validate()
    assert result["status"] == "PASS_WRITING360_SOURCE_PURPOSE_MAPPING_GATE"
    assert result["mapped_source_count"] == 360
    assert sum(result["operation_counts"].values()) == 360
    assert result["approved"] == 15
    assert result["not_yet_admitted"] == 345
    assert result["full360_admitted"] is False
