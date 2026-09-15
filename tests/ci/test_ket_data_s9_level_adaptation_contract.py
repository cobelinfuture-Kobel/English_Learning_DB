from builders.build_ket_data_s9_level_adaptation_contract import materialize
from validators.validate_ket_data_s9_level_adaptation_contract import STATUS, validate


def test_s9_level_adaptation_contract_validates():
    result = validate()
    assert result["status"] == STATUS
    assert result["canonical_mechanic_profile_count"] == 14
    assert result["source_exact_item_count_covered"] == 1360
    assert result["adaptable_down_profile_count"] == 14
    assert result["native_level"] == "A2_KET"
    assert result["min_adapted_level"] == "A1"
    assert result["learner_facing_task_count"] == 0
    assert result["question_bank_item_count"] == 0
    assert result["new_a2_content_count"] == 0


def test_s9_guided_message_preserves_mechanic_and_adapts_response_demand():
    out = materialize()
    guided = next(x for x in out["adaptation_records"] if x["semantic_profile_id"] == "KET_S2_TASK_006")
    assert guided["task_family"] == "GUIDED_MESSAGE"
    assert guided["response_mode"] == "TEXT_ENTRY"
    assert guided["stimulus_modality"] == "TEXT"
    assert guided["assessment_capabilities"] == ["WRITE_TO_MULTIPLE_CONTENT_POINTS"]
    assert guided["native_response_format"] == "25_PLUS_WORD_MESSAGE"
    assert guided["NATIVE_LEVEL"] == "A2_KET"
    assert guided["ADAPTABLE_DOWN"] is True
    assert guided["MIN_ADAPTED_LEVEL"] == "A1"
    assert guided["concrete_level_projection"]["A1"]["response_expectation"] == "2_SENTENCES"
    assert guided["concrete_level_projection"]["A1_plus"]["response_expectation"] == "3_SENTENCES"
    assert guided["concrete_level_projection"]["A2_KET"]["response_expectation"] == "25_PLUS_WORD_MESSAGE"


def test_s9_covers_all_current_ket_canonical_mechanics_without_generating_tasks():
    out = materialize()
    rows = out["adaptation_records"]
    assert len(rows) == 14
    assert sum(x["source_exact_item_count"] for x in rows) == 1360
    assert all(x["authority_scope"] == "CURRENT_KET_CANONICAL_MECHANIC" for x in rows)
    assert all(x["adapted_output_origin"] == "A1FS_DERIVED" for x in rows)
    assert all(x["current_ket_canonical_promotion_allowed"] is False for x in rows)
    assert all(x["learner_facing_task_materialized"] is False for x in rows)
    assert all(x["question_bank_item_materialized"] is False for x in rows)
    assert sum(x["concrete_level_projection"] is not None for x in rows) == 1


def test_s9_is_deterministic():
    assert materialize() == materialize()
